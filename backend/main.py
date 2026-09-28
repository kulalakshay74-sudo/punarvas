from pathlib import Path
from datetime import datetime, timezone

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
import io
import pandas as pd

from services.risk_engine import normalize_hazard
from services.historical_risk import get_historical_risk
from services.relocation_optimizer import optimize_relocation
from services.multi_hazard import analyze_dataframe, assess_sites, HAZARDS

BASE_DIR = Path(__file__).resolve().parent
DEMO_VILLAGES_FILE = BASE_DIR / "raw_villages.csv"
SAFE_SITES_FILE = BASE_DIR / "safe_sites.csv"

app = FastAPI(
    title="PUNARVAS API",
    description="AI-driven GIS decision-support platform for PS 26191",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _read_csv_upload(contents: bytes):
    try:
        return pd.read_csv(io.BytesIO(contents))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Unable to read CSV: {exc}")


def _validate_villages(df):
    required = [
        "Village", "Latitude", "Longitude", "Population",
        "Elevation", "RoadDistance", "Rainfall",
        "DistanceFromRiver", "DistanceFromCoast", "Slope",
        "Infrastructure",
    ]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "CSV is missing required columns.",
                "missing_columns": missing,
                "required_columns": required,
            },
        )


@app.get("/")
def root():
    return {
        "project": "PUNARVAS",
        "problem_statement": "26191",
        "message": "GIS decision-support platform for proactive disaster relocation",
        "status": "running",
    }


@app.get("/health")
def health():
    return {"status": "healthy", "project": "PUNARVAS"}


@app.post("/api/analyze")
async def analyze_data(
    file: UploadFile = File(...),
):
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Please upload a CSV file.")

    df = _read_csv_upload(await file.read())
    _validate_villages(df)
    result = analyze_dataframe(df)
    result["filename"] = file.filename
    result["mode"] = "uploaded_village_data"
    return result


@app.get("/api/live-analysis")
def live_analysis():
    """Re-read the current village dataset and recalculate all decisions.

    This is the prototype's dynamic refresh mechanism: the same decision
    engine is rerun against the latest available dataset on every request.
    """
    try:
        df = pd.read_csv(DEMO_VILLAGES_FILE)
        _validate_villages(df)
        result = analyze_dataframe(df)
        result["mode"] = "live_dataset_refresh"
        result["data_source"] = "raw_villages.csv"
        return result
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Live refresh failed: {exc}")


@app.get("/api/red-zones")
def red_zones():
    result = live_analysis()
    zones = []
    for village in result["villages"]:
        if village["IsRedZone"]:
            zones.append({
                "village": village["Village"],
                "latitude": village["Latitude"],
                "longitude": village["Longitude"],
                "hazard_intensity": village["HazardIntensity"],
                "hazards": village["RedZoneHazards"],
                "priority": village["PriorityCategory"],
            })
    return {
        "updated_at": result["updated_at"],
        "threshold": result["red_zone_threshold"],
        "zones": zones,
    }


@app.get("/api/priorities")
def priorities():
    result = live_analysis()
    rows = []
    for village in result["villages"]:
        rows.append({
            "village": village["Village"],
            "population": village["Population"],
            "hazard_intensity": village["HazardIntensity"],
            "population_vulnerability": village["PopulationVulnerability"],
            "disaster_history": village["DisasterHistory"],
            "priority_score": village["PriorityScore"],
            "priority": village["PriorityCategory"],
        })
    rows.sort(key=lambda x: -x["priority_score"])
    return {"updated_at": result["updated_at"], "priorities": rows}


@app.get("/api/safe-sites")
def safe_sites(target_population: int = 0):
    try:
        sites = pd.read_csv(SAFE_SITES_FILE)
        return {
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "sites": assess_sites(sites, target_population),
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Safe-site assessment failed: {exc}")


@app.post("/api/relocate")
def relocate(
    source_village: str = Form(...),
    target_population: int = Form(...),
    budget: float = Form(...),
    hazard: str = Form("Flood"),
    risk_score: float = Form(0.0),
):
    hazard = normalize_hazard(hazard)
    if target_population <= 0:
        raise HTTPException(status_code=400, detail="Target population must be greater than zero.")
    if budget <= 0:
        raise HTTPException(status_code=400, detail="Budget must be greater than zero.")

    try:
        result = optimize_relocation(
            source_village=source_village,
            target_population=target_population,
            budget=budget,
            source_risk_score=risk_score,
        )
        result["hazard"] = hazard
        return result
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/api/historical-risk")
def historical_risk(hazard: str = "Landslide"):
    return get_historical_risk(hazard)


@app.get("/api/hazards")
def hazards():
    return {"hazards": HAZARDS}
