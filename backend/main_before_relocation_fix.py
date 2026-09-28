from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware

import pandas as pd
import io

from services.risk_engine import (
    calculate_risk,
    normalize_hazard,
    get_hazard_explanation,
)

from services.feature_engine import calculate_features

from services.relocation_optimizer import optimize_relocation


app = FastAPI(
    title="PUNARVAS API",
    description="AI-driven disaster risk and relocation planning platform",
    version="1.0.0",
)


# =========================================================
# CORS
# =========================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================================================
# BASIC ROUTES
# =========================================================

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


# =========================================================
# PROCESS ONE VILLAGE
# =========================================================

def process_village(row, hazard):
    """
    Process one village.

    If raw geographic/environmental fields are available,
    automatically calculate the five risk factors.

    Otherwise, use the already-calculated risk factors
    supplied by the old CSV format.
    """

    raw_columns = [
        "Elevation",
        "RoadDistance",
        "Rainfall",
        "DistanceFromRiver",
        "DistanceFromCoast",
        "Slope",
        "Infrastructure",
    ]

    has_raw_data = all(
        column in row.index
        for column in raw_columns
    )

    village = row.to_dict()

    # -----------------------------------------------------
    # NEW RAW-DATA MODE
    # -----------------------------------------------------

    if has_raw_data:

        calculated_features = calculate_features(
            row,
            hazard,
        )

    # -----------------------------------------------------
    # OLD PRE-CALCULATED MODE
    # -----------------------------------------------------

    else:

        required_old_columns = [
            "HazardExposure",
            "PopulationVulnerability",
            "InfrastructureExposure",
            "AccessibilityRisk",
            "TerrainRisk",
        ]

        missing = [
            column
            for column in required_old_columns
            if column not in row.index
        ]

        if missing:

            raise ValueError(
                "CSV must contain either raw geographic "
                "fields or pre-calculated risk factors. "
                f"Missing: {missing}"
            )

        calculated_features = {
            "HazardExposure": float(
                row["HazardExposure"]
            ),
            "PopulationVulnerability": float(
                row["PopulationVulnerability"]
            ),
            "InfrastructureExposure": float(
                row["InfrastructureExposure"]
            ),
            "AccessibilityRisk": float(
                row["AccessibilityRisk"]
            ),
            "TerrainRisk": float(
                row["TerrainRisk"]
            ),
        }

    # -----------------------------------------------------
    # HAZARD-SPECIFIC RISK ENGINE
    # -----------------------------------------------------

    risk_result = calculate_risk(
        hazard_exposure=calculated_features[
            "HazardExposure"
        ],

        population_vulnerability=calculated_features[
            "PopulationVulnerability"
        ],

        infrastructure_exposure=calculated_features[
            "InfrastructureExposure"
        ],

        accessibility_risk=calculated_features[
            "AccessibilityRisk"
        ],

        terrain_risk=calculated_features[
            "TerrainRisk"
        ],

        hazard=hazard,
    )

    # Add calculated factors to response
    village.update(calculated_features)

    # Add final risk
    village["RiskScore"] = risk_result[
        "RiskScore"
    ]

    village["RiskCategory"] = risk_result[
        "RiskCategory"
    ]

    return village


# =========================================================
# ANALYZE CSV
# =========================================================

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

    # -----------------------------------------------------
    # BASIC REQUIRED COLUMNS
    # -----------------------------------------------------

    basic_columns = [
        "Village",
        "Latitude",
        "Longitude",
        "Population",
    ]

    missing_basic = [
        column
        for column in basic_columns
        if column not in df.columns
    ]

    if missing_basic:

        raise HTTPException(
            status_code=400,
            detail={
                "message": "CSV is missing required basic columns.",
                "missing_columns": missing_basic,
                "required_columns": basic_columns,
            },
        )

    # -----------------------------------------------------
    # PROCESS VILLAGES
    # -----------------------------------------------------

    villages = []

    try:

        for _, row in df.iterrows():

            village = process_village(
                row,
                hazard,
            )

            villages.append(village)

    except Exception as e:

        raise HTTPException(
            status_code=400,
            detail=f"Risk calculation failed: {str(e)}",
        )

    # -----------------------------------------------------
    # SUMMARY
    # -----------------------------------------------------

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

        "critical": categories.count(
            "Critical"
        ),

        "high": categories.count(
            "High"
        ),

        "moderate": categories.count(
            "Moderate"
        ),

        "low": categories.count(
            "Low"
        ),
    }

    # -----------------------------------------------------
    # RETURN RESULT
    # -----------------------------------------------------

    weights = calculate_risk(
        50,
        50,
        50,
        50,
        50,
        hazard,
    )["Weights"]

    return {
        "project": "PUNARVAS",

        "filename": file.filename,

        "hazard": hazard,

        "analysis_mode": (
            "automatic_feature_engineering"
        ),

        "hazard_explanation": (
            get_hazard_explanation(hazard)
        ),

        "weights": weights,

        "summary": summary,

        "villages": villages,
    }


# =========================================================
# TEST RISK
# =========================================================

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


# =========================================================
# RELOCATION OPTIMIZATION
# =========================================================

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
            detail=(
                "Target population must be greater than zero."
            ),
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
