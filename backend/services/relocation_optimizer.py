import math
import pandas as pd


def haversine_km(lat1, lon1, lat2, lon2):
    """
    Calculate approximate distance between two geographic coordinates.
    """

    earth_radius = 6371.0

    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)

    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat1_rad)
        * math.cos(lat2_rad)
        * math.sin(delta_lon / 2) ** 2
    )

    c = 2 * math.atan2(
        math.sqrt(a),
        math.sqrt(1 - a)
    )

    return earth_radius * c


def get_risk_category(risk_score):
    """
    Convert a 0-100 risk score into a category.
    """

    if risk_score >= 75:
        return "Critical"

    if risk_score >= 60:
        return "High"

    if risk_score >= 40:
        return "Moderate"

    return "Low"


def optimize_relocation(
    source_village,
    target_population,
    budget,
    source_risk_score=0.0,
    source_risk_category=None,
    villages_file="sample_villages.csv",
    sites_file="safe_sites.csv",
):
    """
    Find the best relocation site using:

    - Safety
    - Distance
    - Cost
    - Available capacity
    - Total budget

    source_risk_score is supplied by the PUNARVAS
    disaster-risk analysis engine.
    """

    villages = pd.read_csv(villages_file)
    sites = pd.read_csv(sites_file)

    # ---------------------------------------------------------
    # FIND SOURCE VILLAGE
    # ---------------------------------------------------------

    source = villages[
        villages["Village"].astype(str).str.lower()
        == str(source_village).lower()
    ]

    if source.empty:
        raise ValueError(
            f"Village '{source_village}' was not found."
        )

    source = source.iloc[0]

    source_lat = float(source["Latitude"])
    source_lon = float(source["Longitude"])

    source_population = int(source["Population"])

    # ---------------------------------------------------------
    # VALIDATE INPUTS
    # ---------------------------------------------------------

    if target_population <= 0:
        raise ValueError(
            "Target population must be greater than zero."
        )

    if target_population > source_population:
        raise ValueError(
            f"Target population cannot exceed the village population "
            f"({source_population})."
        )

    if budget <= 0:
        raise ValueError(
            "Budget must be greater than zero."
        )

    # ---------------------------------------------------------
    # RISK INFORMATION
    # ---------------------------------------------------------

    source_risk_score = float(source_risk_score)

    if source_risk_category is None:
        source_risk_category = get_risk_category(
            source_risk_score
        )

    candidates = []

    # ---------------------------------------------------------
    # EVALUATE EVERY SAFE SITE
    # ---------------------------------------------------------

    for _, site in sites.iterrows():

        site_lat = float(site["Latitude"])
        site_lon = float(site["Longitude"])

        distance = haversine_km(
            source_lat,
            source_lon,
            site_lat,
            site_lon,
        )

        capacity = int(site["Capacity"])
        safety = float(site["SafetyScore"])
        cost_per_person = float(site["CostPerPerson"])

        total_cost = (
            target_population
            * cost_per_person
        )

        # -----------------------------------------------------
        # CAPACITY CONSTRAINT
        # -----------------------------------------------------

        if capacity < target_population:
            continue

        # -----------------------------------------------------
        # BUDGET CONSTRAINT
        # -----------------------------------------------------

        if total_cost > budget:
            continue

        # -----------------------------------------------------
        # DISTANCE SCORE
        # -----------------------------------------------------

        distance_factor = min(
            distance,
            100.0
        )

        # -----------------------------------------------------
        # SAFETY RISK
        # -----------------------------------------------------

        safety_risk = 100.0 - safety

        # -----------------------------------------------------
        # COST SCORE
        # -----------------------------------------------------

        cost_factor = min(
            (cost_per_person / 25000.0) * 100.0,
            100.0
        )

        # -----------------------------------------------------
        # OPTIMIZATION SCORE
        # -----------------------------------------------------
        #
        # Lower score = better site
        #
        # Safety       = 45%
        # Distance     = 25%
        # Cost         = 30%
        #

        optimization_score = (
            safety_risk * 0.45
            + distance_factor * 0.25
            + cost_factor * 0.30
        )

        candidates.append(
            {
                "site": str(site["Site"]),
                "latitude": site_lat,
                "longitude": site_lon,
                "capacity": capacity,
                "safety_score": safety,
                "distance_km": round(
                    distance,
                    2
                ),
                "cost_per_person": cost_per_person,
                "total_cost": round(
                    total_cost,
                    2
                ),
                "optimization_score": round(
                    optimization_score,
                    2
                ),
            }
        )

    # ---------------------------------------------------------
    # NO FEASIBLE SITE
    # ---------------------------------------------------------

    if not candidates:
        return {
            "status": "no_feasible_solution",
            "message": (
                "No relocation site satisfies the "
                "population capacity and budget constraints."
            ),
            "source_village": source_village,
            "source_risk_score": source_risk_score,
            "source_risk_category": source_risk_category,
            "target_population": target_population,
            "budget": budget,
            "candidates": [],
        }

    # ---------------------------------------------------------
    # RANK SITES
    # ---------------------------------------------------------

    candidates.sort(
        key=lambda x: x["optimization_score"]
    )

    best = candidates[0]

    remaining_budget = (
        budget - best["total_cost"]
    )

    # ---------------------------------------------------------
    # FINAL RESULT
    # ---------------------------------------------------------

    return {
        "status": "success",

        "source_village": source_village,

        "source_risk_score": round(
            source_risk_score,
            2
        ),

        "source_risk_category":
            source_risk_category,

        "target_population":
            target_population,

        "budget":
            budget,

        "recommended_site":
            best,

        "remaining_budget":
            round(
                remaining_budget,
                2
            ),

        "evaluated_sites":
            candidates,
    }
