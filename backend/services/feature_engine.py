"""
PUNARVAS Feature Engineering Engine

Converts raw geographic, population and environmental
data into normalized disaster-risk factors from 0-100.

These are transparent demo rules intended for the MVP.
They are NOT scientifically validated disaster predictions.
"""

import math


def clamp(value, minimum=0, maximum=100):
    """Keep a value between minimum and maximum."""

    return max(minimum, min(maximum, value))


def normalize_inverse(value, safe_value, dangerous_value):
    """
    Convert a measurement where LOWER values are safer
    and HIGHER values are more dangerous.

    Example:
        Road distance:
        1 km  -> lower risk
        50 km -> higher risk
    """

    if dangerous_value == safe_value:
        return 50.0

    score = (
        (value - safe_value)
        / (dangerous_value - safe_value)
    ) * 100

    return clamp(score)


def normalize_direct(value, safe_value, dangerous_value):
    """
    Convert a measurement where HIGHER values mean
    greater risk.

    Example:
        rainfall:
        low rainfall -> low risk
        high rainfall -> high risk
    """

    if dangerous_value == safe_value:
        return 50.0

    score = (
        (value - safe_value)
        / (dangerous_value - safe_value)
    ) * 100

    return clamp(score)



def proximity_risk(value, safe_distance, dangerous_distance):
    """Convert distance-to-hazard into risk: closer means higher risk."""
    if dangerous_distance == safe_distance:
        return 50.0
    score = ((safe_distance - float(value)) / (safe_distance - dangerous_distance)) * 100
    return clamp(score)

def population_vulnerability(population):
    """
    Estimate population vulnerability.

    Larger populations mean more people potentially
    affected and therefore greater vulnerability.

    This is normalized for the demo.
    """

    # 100 people or less -> low
    # 5000+ people -> very high
    score = (
        (population - 100)
        / (5000 - 100)
    ) * 100

    return clamp(score)


def infrastructure_exposure(infrastructure):
    """
    Infrastructure exposure is supplied as a raw
    0-100 infrastructure vulnerability value.
    """

    return clamp(float(infrastructure))


def accessibility_risk(road_distance):
    """
    Estimate accessibility risk using distance to
    the nearest major road.

    Greater road distance = greater accessibility risk.
    """

    return normalize_inverse(
        float(road_distance),
        safe_value=1,
        dangerous_value=50,
    )


def terrain_risk(elevation, slope):
    """
    Estimate terrain risk using elevation and slope.

    Slope has greater influence because steep terrain
    can increase landslide-related risk.

    Elevation contributes a smaller amount.
    """

    slope_score = normalize_direct(
        float(slope),
        safe_value=2,
        dangerous_value=45,
    )

    # For the MVP, elevation is treated as a contextual
    # terrain factor rather than a universal danger signal.
    elevation_score = normalize_inverse(
        float(elevation),
        safe_value=100,
        dangerous_value=1000,
    )

    score = (
        slope_score * 0.75
        + elevation_score * 0.25
    )

    return round(clamp(score), 2)


def flood_hazard_exposure(
    rainfall,
    distance_from_river,
    elevation,
):
    """
    Estimate flood hazard exposure.

    Higher rainfall, shorter distance from a river,
    and lower elevation increase the estimated exposure.
    """

    rainfall_score = normalize_direct(
        float(rainfall),
        safe_value=500,
        dangerous_value=4000,
    )

    river_score = proximity_risk(
        float(distance_from_river),
        safe_distance=20,
        dangerous_distance=0.5,
    )

    elevation_score = normalize_inverse(
        float(elevation),
        safe_value=50,
        dangerous_value=1000,
    )

    score = (
        rainfall_score * 0.45
        + river_score * 0.40
        + elevation_score * 0.15
    )

    return round(clamp(score), 2)


def landslide_hazard_exposure(
    rainfall,
    slope,
    elevation,
):
    """
    Estimate landslide hazard exposure.

    Slope and rainfall are given greater importance.
    """

    rainfall_score = normalize_direct(
        float(rainfall),
        safe_value=500,
        dangerous_value=4000,
    )

    slope_score = normalize_direct(
        float(slope),
        safe_value=2,
        dangerous_value=45,
    )

    elevation_score = normalize_direct(
        float(elevation),
        safe_value=50,
        dangerous_value=1200,
    )

    score = (
        rainfall_score * 0.35
        + slope_score * 0.50
        + elevation_score * 0.15
    )

    return round(clamp(score), 2)


def coastal_erosion_exposure(
    distance_from_coast,
    rainfall,
):
    """
    Estimate coastal erosion exposure.

    Settlements closer to the coast receive higher
    estimated exposure.
    """

    coast_score = proximity_risk(
        float(distance_from_coast),
        safe_distance=100,
        dangerous_distance=0,
    )

    rainfall_score = normalize_direct(
        float(rainfall),
        safe_value=500,
        dangerous_value=4000,
    )

    score = (
        coast_score * 0.75
        + rainfall_score * 0.25
    )

    return round(clamp(score), 2)


def cloudburst_exposure(
    rainfall,
    distance_from_river,
    road_distance,
):
    """
    Estimate cloudburst exposure.

    Very intense rainfall combined with proximity to
    drainage/water channels and poor accessibility
    increases estimated exposure.
    """

    rainfall_score = normalize_direct(
        float(rainfall),
        safe_value=500,
        dangerous_value=5000,
    )

    river_score = proximity_risk(
        float(distance_from_river),
        safe_distance=20,
        dangerous_distance=0.5,
    )

    road_score = normalize_inverse(
        float(road_distance),
        safe_value=1,
        dangerous_value=50,
    )

    score = (
        rainfall_score * 0.55
        + river_score * 0.25
        + road_score * 0.20
    )

    return round(clamp(score), 2)


def calculate_features(row, hazard):
    """
    Convert one raw village record into the five
    risk factors required by the PUNARVAS risk engine.
    """

    hazard = hazard.strip().lower()

    population = float(row["Population"])
    elevation = float(row["Elevation"])
    road_distance = float(row["RoadDistance"])
    rainfall = float(row["Rainfall"])
    distance_from_river = float(row["DistanceFromRiver"])
    distance_from_coast = float(row["DistanceFromCoast"])
    slope = float(row["Slope"])
    infrastructure = float(row["Infrastructure"])

    # -----------------------------------------------
    # Population vulnerability
    # -----------------------------------------------

    population_score = population_vulnerability(
        population
    )

    # -----------------------------------------------
    # Infrastructure exposure
    # -----------------------------------------------

    infrastructure_score = infrastructure_exposure(
        infrastructure
    )

    # -----------------------------------------------
    # Accessibility risk
    # -----------------------------------------------

    accessibility_score = accessibility_risk(
        road_distance
    )

    # -----------------------------------------------
    # Terrain risk
    # -----------------------------------------------

    terrain_score = terrain_risk(
        elevation,
        slope
    )

    # -----------------------------------------------
    # Hazard-specific exposure
    # -----------------------------------------------

    if hazard == "flood":

        hazard_score = flood_hazard_exposure(
            rainfall,
            distance_from_river,
            elevation,
        )

    elif hazard == "landslide":

        hazard_score = landslide_hazard_exposure(
            rainfall,
            slope,
            elevation,
        )

    elif hazard in [
        "coastal erosion",
        "coastal",
        "erosion",
    ]:

        hazard_score = coastal_erosion_exposure(
            distance_from_coast,
            rainfall,
        )

    elif hazard in [
        "cloudburst",
        "cloud burst",
    ]:

        hazard_score = cloudburst_exposure(
            rainfall,
            distance_from_river,
            road_distance,
        )

    else:

        # Default to a general hazard exposure estimate.
        hazard_score = flood_hazard_exposure(
            rainfall,
            distance_from_river,
            elevation,
        )

    return {
        "HazardExposure": round(hazard_score, 2),
        "PopulationVulnerability": round(
            population_score,
            2
        ),
        "InfrastructureExposure": round(
            infrastructure_score,
            2
        ),
        "AccessibilityRisk": round(
            accessibility_score,
            2
        ),
        "TerrainRisk": round(
            terrain_score,
            2
        ),
    }
