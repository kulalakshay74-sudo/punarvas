from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware

import pandas as pd
import io
import os

from services.risk_engine import (
    calculate_risk,
    normalize_hazard,
    get_hazard_explanation,
)

from services.relocation_optimizer import optimize_relocation


app = FastAPI(
    title="PUNARVAS API",
    description="AI-driven disaster risk and relocation planning platform",
    version="1.0.0",
)


# ---------------------------------------------------------
# CORS
# ---------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------
# Basic routes
# ---------------------------------------------------------

@app.get("/")
def root():
    return {
        "project": "PUNARVAS",
        "message": "Disaster Risk and Relocation Planning API",
        "status": "running",
    }


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "project": "PUNARVAS",
    }


# ---------------------------------------------------------
# Risk calculation helper
# ---------------------------------------------------------

def process_village(row, hazard):
    """
    Calculate risk for one village.
    """

    result = calculate_risk(
        hazard_exposure=float(row["HazardExposure"]),
        population_vulnerability=float(
            row["PopulationVulnerability"]
        ),
        infrastructure_exposure=float(
            row["InfrastructureExposure"]
        ),
        accessibility_risk=float(
            row["AccessibilityRisk"]
        ),
        terrain_risk=float(row["TerrainRisk"]),
        hazard=hazard,
    )

    village = row.to_dict()

    village["RiskScore"] = result["RiskScore"]
    village["RiskCategory"] = result["RiskCategory"]

    return village


# ---------------------------------------------------------
# Analyze uploaded CSV
# ---------------------------------------------------------

@app.post("/api/analyze")
async def analyze_data(
    file: UploadFile = File(...),
    hazard: str = Form("Flood"),
):

    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="No file selected.",
        )

    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=400,
            detail="Currently only CSV files are supported.",
        )

    hazard = normalize_hazard(hazard)

    try:

        contents = await file.read()

        df = pd.read_csv(
            io.BytesIO(contents)
        )

    except Exception as e:

        raise HTTPException(
            status_code=400,
            detail=f"Unable to read CSV: {str(e)}",
        )

    required_columns = [
        "Village",
        "Latitude",
        "Longitude",
        "Population",
        "HazardExposure",
        "PopulationVulnerability",
        "InfrastructureExposure",
        "AccessibilityRisk",
        "TerrainRisk",
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in df.columns
    ]

    if missing_columns:

        raise HTTPException(
            status_code=400,
            detail={
                "message": "CSV is missing required columns.",
                "missing_columns": missing_columns,
                "required_columns": required_columns,
            },
        )

    villages = []

    for _, row in df.iterrows():

        village = process_village(
            row,
            hazard,
        )

        villages.append(village)

    total_population = int(
        df["Population"].sum()
    )

    categories = [
        village["RiskCategory"]
        for village in villages
    ]

    summary = {
        "total_villages": len(villages),
        "total_population": total_population,
        "critical": categories.count("Critical"),
        "high": categories.count("High"),
        "moderate": categories.count("Moderate"),
        "low": categories.count("Low"),
    }

    return {
        "project": "PUNARVAS",
        "filename": file.filename,
        "hazard": hazard,
        "hazard_explanation": get_hazard_explanation(
            hazard
        ),
        "weights": calculate_risk(
            50,
            50,
            50,
            50,
            50,
            hazard,
        )["Weights"],
        "summary": summary,
        "villages": villages,
    }


# ---------------------------------------------------------
# Test risk endpoint
# ---------------------------------------------------------

@app.get("/api/test-risk")
def test_risk(
    hazard: str = "Flood",
    hazard_exposure: float = 50,
    population_vulnerability: float = 50,
    infrastructure_exposure: float = 50,
    accessibility_risk: float = 50,
    terrain_risk: float = 50,
):

    result = calculate_risk(
        hazard_exposure,
        population_vulnerability,
        infrastructure_exposure,
        accessibility_risk,
        terrain_risk,
        hazard,
    )

    return result


# ---------------------------------------------------------
# Relocation optimization
# ---------------------------------------------------------

@app.post("/api/relocate")
def relocate(
    source_village: str = Form(...),
    target_population: int = Form(...),
    budget: float = Form(...),
    hazard: str = Form("Flood"),
):

    hazard = normalize_hazard(hazard)

    if target_population <= 0:
        raise HTTPException(
            status_code=400,
            detail="Target population must be greater than zero.",
        )

    if budget <= 0:
        raise HTTPException(
            status_code=400,
            detail="Budget must be greater than zero.",
        )

    try:

        result = optimize_relocation(
            source_village=source_village,
            target_population=target_population,
            budget=budget,
        )

    except Exception as e:

        raise HTTPException(
            status_code=400,
            detail=str(e),
        )

    result["hazard"] = hazard

    return result
