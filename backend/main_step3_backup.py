from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import io

from services.relocation_optimizer import optimize_relocation


app = FastAPI(
    title="PUNARVAS Disaster Relocation API",
    description="AI-assisted disaster risk assessment and relocation backend",
    version="2.0.0",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================================================
# BASIC ENDPOINTS
# =========================================================

@app.get("/")
def root():
    return {
        "project": "PUNARVAS",
        "status": "running",
        "version": "2.0.0",
        "message": "Disaster relocation intelligence API is active"
    }


@app.get("/health")
def health():
    return {
        "status": "healthy"
    }


# =========================================================
# RISK ENGINE
# =========================================================

def calculate_risk(row):

    hazard = float(row["HazardExposure"])
    population = float(row["PopulationVulnerability"])
    infrastructure = float(row["InfrastructureExposure"])
    accessibility = float(row["AccessibilityRisk"])
    terrain = float(row["TerrainRisk"])

    score = (
        hazard * 0.30
        + population * 0.25
        + infrastructure * 0.20
        + accessibility * 0.15
        + terrain * 0.10
    )

    return round(score, 2)


def risk_category(score):

    if score >= 75:
        return "Critical"

    elif score >= 60:
        return "High"

    elif score >= 40:
        return "Moderate"

    else:
        return "Low"


# =========================================================
# CSV ANALYSIS
# =========================================================

@app.post("/api/analyze")
async def analyze_file(file: UploadFile = File(...)):

    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=400,
            detail="Please upload a CSV file."
        )

    try:
        contents = await file.read()

        df = pd.read_csv(
            io.BytesIO(contents)
        )

    except Exception as e:

        raise HTTPException(
            status_code=400,
            detail=f"Unable to read CSV file: {str(e)}"
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
                "message": "Required columns are missing.",
                "missing_columns": missing_columns,
                "required_columns": required_columns,
            }
        )

    numeric_columns = [
        "Latitude",
        "Longitude",
        "Population",
        "HazardExposure",
        "PopulationVulnerability",
        "InfrastructureExposure",
        "AccessibilityRisk",
        "TerrainRisk",
    ]

    try:

        for column in numeric_columns:
            df[column] = pd.to_numeric(
                df[column]
            )

    except Exception as e:

        raise HTTPException(
            status_code=400,
            detail=f"Invalid numeric value in CSV: {str(e)}"
        )

    factor_columns = [
        "HazardExposure",
        "PopulationVulnerability",
        "InfrastructureExposure",
        "AccessibilityRisk",
        "TerrainRisk",
    ]

    for column in factor_columns:

        if (
            (df[column] < 0)
            | (df[column] > 100)
        ).any():

            raise HTTPException(
                status_code=400,
                detail=f"{column} values must be between 0 and 100."
            )

    df["RiskScore"] = df.apply(
        calculate_risk,
        axis=1
    )

    df["RiskCategory"] = df[
        "RiskScore"
    ].apply(
        risk_category
    )

    records = df.to_dict(
        orient="records"
    )

    return {
        "project": "PUNARVAS",
        "filename": file.filename,

        "summary": {
            "total_villages": len(df),
            "total_population": int(
                df["Population"].sum()
            ),
            "critical": int(
                (df["RiskCategory"] == "Critical").sum()
            ),
            "high": int(
                (df["RiskCategory"] == "High").sum()
            ),
            "moderate": int(
                (df["RiskCategory"] == "Moderate").sum()
            ),
            "low": int(
                (df["RiskCategory"] == "Low").sum()
            ),
        },

        "villages": records,
    }


# =========================================================
# RISK TEST
# =========================================================

@app.post("/api/test-risk")
def test_risk(data: dict):

    required_fields = [
        "HazardExposure",
        "PopulationVulnerability",
        "InfrastructureExposure",
        "AccessibilityRisk",
        "TerrainRisk",
    ]

    missing = [
        field
        for field in required_fields
        if field not in data
    ]

    if missing:

        raise HTTPException(
            status_code=400,
            detail={
                "message": "Missing risk factors",
                "missing": missing
            }
        )

    try:

        score = calculate_risk(data)

    except Exception as e:

        raise HTTPException(
            status_code=400,
            detail=str(e)
        )

    return {
        "risk_score": score,
        "risk_category": risk_category(score),

        "factors": {
            "hazard_exposure": data[
                "HazardExposure"
            ],

            "population_vulnerability": data[
                "PopulationVulnerability"
            ],

            "infrastructure_exposure": data[
                "InfrastructureExposure"
            ],

            "accessibility_risk": data[
                "AccessibilityRisk"
            ],

            "terrain_risk": data[
                "TerrainRisk"
            ],
        }
    }


# =========================================================
# RELOCATION OPTIMIZER
# =========================================================

@app.post("/api/relocate")
def relocate(data: dict):

    required_fields = [
        "source_village",
        "target_population",
        "budget",
    ]

    missing = [
        field
        for field in required_fields
        if field not in data
    ]

    if missing:

        raise HTTPException(
            status_code=400,
            detail={
                "message": "Missing relocation parameters.",
                "missing": missing
            }
        )

    try:

        result = optimize_relocation(
            source_village=data[
                "source_village"
            ],

            target_population=int(
                data["target_population"]
            ),

            budget=float(
                data["budget"]
            ),
        )

        return result

    except ValueError as e:

        raise HTTPException(
            status_code=400,
            detail=str(e)
        )

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=f"Relocation optimization failed: {str(e)}"
        )
