"""PUNARVAS PS 26191 multi-hazard decision engine.

Prototype implementation of the four requirements in PS 26191:
- dynamic multi-hazard Red Zones
- safer-site suitability and carrying capacity
- habitation relocation priority
- actionable authority output

The calculations are transparent prototype scoring rules and are not
scientifically validated hazard forecasts.
"""

from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from services.feature_engine import calculate_features
from services.risk_engine import calculate_risk

HAZARDS = ["Flood", "Landslide", "Coastal Erosion", "Cloudburst"]

# These thresholds are implementation settings for the prototype.
RED_ZONE_THRESHOLD = 60.0
IMMEDIATE_THRESHOLD = 75.0
SHORT_TERM_THRESHOLD = 50.0


def _number(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _history_score(row):
    """Use supplied disaster-history score; 0 means no history supplied."""
    if "DisasterHistory" in row.index:
        return max(0.0, min(100.0, _number(row["DisasterHistory"])))
    if "HistoricalRisk" in row.index:
        return max(0.0, min(100.0, _number(row["HistoricalRisk"])))
    return 0.0


def _vulnerability_score(row, fallback):
    if "PopulationVulnerability" in row.index:
        return max(0.0, min(100.0, _number(row["PopulationVulnerability"])))
    return float(fallback)


def _priority_category(score):
    if score >= IMMEDIATE_THRESHOLD:
        return "Immediate"
    if score >= SHORT_TERM_THRESHOLD:
        return "Short-term"
    return "Medium-term"


def analyze_village(row):
    """Calculate all four hazard intensities and relocation priority."""
    village = row.to_dict()

    hazard_scores = {}
    hazard_categories = {}

    # Feature engineering is run separately for each hazard so the
    # hazard intensity is genuinely multi-hazard rather than a label.
    for hazard in HAZARDS:
        features = calculate_features(row, hazard)
        result = calculate_risk(
            features["HazardExposure"],
            features["PopulationVulnerability"],
            features["InfrastructureExposure"],
            features["AccessibilityRisk"],
            features["TerrainRisk"],
            hazard,
        )
        hazard_scores[hazard] = float(features["HazardExposure"])
        hazard_categories[hazard] = result["RiskCategory"]

    vulnerability = _vulnerability_score(
        row,
        calculate_features(row, "Flood")["PopulationVulnerability"],
    )
    history = _history_score(row)

    # The problem statement asks the priority decision to integrate
    # hazard intensity, population vulnerability and disaster history.
    # Equal weighting keeps the prototype transparent.
    hazard_intensity = max(hazard_scores.values())
    priority_score = round(
        (hazard_intensity + vulnerability + history) / 3.0,
        2,
    )

    red_hazards = [
        hazard
        for hazard, score in hazard_scores.items()
        if score >= RED_ZONE_THRESHOLD
    ]

    village["HazardIntensity"] = round(hazard_intensity, 2)
    village["PopulationVulnerability"] = round(vulnerability, 2)
    village["DisasterHistory"] = round(history, 2)
    village["PriorityScore"] = priority_score
    village["PriorityCategory"] = _priority_category(priority_score)
    village["IsRedZone"] = bool(red_hazards)
    village["RedZoneHazards"] = red_hazards
    village["HazardScores"] = {
        hazard: round(score, 2)
        for hazard, score in hazard_scores.items()
    }
    village["HazardCategories"] = hazard_categories

    return village


def analyze_dataframe(df):
    villages = [analyze_village(row) for _, row in df.iterrows()]

    red_zones = [v for v in villages if v["IsRedZone"]]

    priority_counts = {
        "Immediate": sum(v["PriorityCategory"] == "Immediate" for v in villages),
        "Short-term": sum(v["PriorityCategory"] == "Short-term" for v in villages),
        "Medium-term": sum(v["PriorityCategory"] == "Medium-term" for v in villages),
    }

    return {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "hazards": HAZARDS,
        "red_zone_threshold": RED_ZONE_THRESHOLD,
        "priority_thresholds": {
            "immediate": IMMEDIATE_THRESHOLD,
            "short_term": SHORT_TERM_THRESHOLD,
        },
        "summary": {
            "total_villages": len(villages),
            "total_population": int(df["Population"].sum()),
            "red_zones": len(red_zones),
            "immediate": priority_counts["Immediate"],
            "short_term": priority_counts["Short-term"],
            "medium_term": priority_counts["Medium-term"],
        },
        "villages": villages,
    }


def load_demo_villages(csv_path: Path):
    df = pd.read_csv(csv_path)
    required = ["Village", "Latitude", "Longitude", "Population"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Village dataset is missing: {missing}")
    return df


def assess_sites(sites_df, target_population=None):
    """Return suitability and carrying-capacity assessment for each safer site."""
    sites = []
    for _, row in sites_df.iterrows():
        capacity = int(_number(row.get("Capacity", 0)))
        safety = round(_number(row.get("SafetyScore", 0)), 2)
        required = int(target_population or 0)
        available = max(capacity - required, 0)

        if required <= 0:
            capacity_status = "Available"
        elif capacity >= required:
            capacity_status = "Sufficient"
        else:
            capacity_status = "Insufficient"

        sites.append({
            "site": str(row.get("Site", "Unknown")),
            "latitude": _number(row.get("Latitude")),
            "longitude": _number(row.get("Longitude")),
            "suitability_score": safety,
            "carrying_capacity": capacity,
            "available_capacity": available,
            "capacity_status": capacity_status,
            "cost_per_person": _number(row.get("CostPerPerson", 0)),
        })

    sites.sort(key=lambda x: (-x["suitability_score"], -x["carrying_capacity"]))
    return sites
