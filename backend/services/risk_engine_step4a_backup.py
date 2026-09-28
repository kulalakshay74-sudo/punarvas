"""
PUNARVAS Hazard-Specific Risk Engine

Calculates a 0-100 risk score using different factor weights
depending on the selected disaster hazard.
"""


HAZARD_WEIGHTS = {
    "Flood": {
        "HazardExposure": 0.35,
        "PopulationVulnerability": 0.20,
        "InfrastructureExposure": 0.20,
        "AccessibilityRisk": 0.15,
        "TerrainRisk": 0.10,
    },

    "Landslide": {
        "HazardExposure": 0.20,
        "PopulationVulnerability": 0.15,
        "InfrastructureExposure": 0.15,
        "AccessibilityRisk": 0.15,
        "TerrainRisk": 0.35,
    },

    "Coastal Erosion": {
        "HazardExposure": 0.35,
        "PopulationVulnerability": 0.25,
        "InfrastructureExposure": 0.25,
        "AccessibilityRisk": 0.10,
        "TerrainRisk": 0.05,
    },

    "Cloudburst": {
        "HazardExposure": 0.30,
        "PopulationVulnerability": 0.20,
        "InfrastructureExposure": 0.20,
        "AccessibilityRisk": 0.20,
        "TerrainRisk": 0.10,
    },
}


RISK_THRESHOLDS = {
    "Critical": 75,
    "High": 60,
    "Moderate": 40,
}


def normalize_hazard(hazard: str) -> str:
    """
    Convert different spellings into the supported hazard names.
    """

    if not hazard:
        return "Flood"

    hazard = hazard.strip().lower()

    aliases = {
        "flood": "Flood",
        "floods": "Flood",

        "landslide": "Landslide",
        "landslides": "Landslide",

        "coastal erosion": "Coastal Erosion",
        "coastal": "Coastal Erosion",
        "erosion": "Coastal Erosion",

        "cloudburst": "Cloudburst",
        "cloud burst": "Cloudburst",
    }

    return aliases.get(hazard, "Flood")


def calculate_risk(
    hazard_exposure,
    population_vulnerability,
    infrastructure_exposure,
    accessibility_risk,
    terrain_risk,
    hazard="Flood",
):
    """
    Calculate hazard-specific risk score.
    """

    hazard = normalize_hazard(hazard)

    weights = HAZARD_WEIGHTS[hazard]

    score = (
        hazard_exposure * weights["HazardExposure"]
        + population_vulnerability * weights["PopulationVulnerability"]
        + infrastructure_exposure * weights["InfrastructureExposure"]
        + accessibility_risk * weights["AccessibilityRisk"]
        + terrain_risk * weights["TerrainRisk"]
    )

    score = round(float(score), 2)

    if score >= RISK_THRESHOLDS["Critical"]:
        category = "Critical"
    elif score >= RISK_THRESHOLDS["High"]:
        category = "High"
    elif score >= RISK_THRESHOLDS["Moderate"]:
        category = "Moderate"
    else:
        category = "Low"

    return {
        "RiskScore": score,
        "RiskCategory": category,
        "Hazard": hazard,
        "Weights": weights,
    }


def get_hazard_explanation(hazard):
    """
    Returns an explanation of why particular factors
    matter more for each hazard.
    """

    hazard = normalize_hazard(hazard)

    explanations = {
        "Flood": (
            "Flood risk emphasizes hazard exposure, infrastructure exposure, "
            "and accessibility because inundation can damage infrastructure "
            "and restrict movement."
        ),

        "Landslide": (
            "Landslide risk gives higher importance to terrain conditions "
            "because unstable or steep terrain can increase landslide danger."
        ),

        "Coastal Erosion": (
            "Coastal erosion risk emphasizes hazard exposure, population "
            "vulnerability, and infrastructure exposure because settlements "
            "near vulnerable coastal zones may face progressive land loss."
        ),

        "Cloudburst": (
            "Cloudburst risk emphasizes hazard exposure, infrastructure, "
            "and accessibility because intense rainfall can rapidly disrupt "
            "roads, drainage, and settlements."
        ),
    }

    return explanations[hazard]
