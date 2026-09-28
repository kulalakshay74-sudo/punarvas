import math
import pandas as pd


def haversine_km(lat1, lon1, lat2, lon2):
    """
    Calculate approximate distance between two geographic coordinates.
    """

    earth_radius = 6371.0

    lat1 = math.radians(lat1)
    lat2 = math.radians(lat2)

    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat1)
        * math.cos(lat2)
        * math.sin(delta_lon / 2) ** 2
    )

    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return earth_radius * c


def optimize_relocation(
    source_village,
    target_population,
    budget,
    villages_file="sample_villages.csv",
    sites_file="safe_sites.csv",
):
    """
    Find the best relocation site(s) using:

    - Safety
    - Distance
    - Cost
    - Available capacity
    - Total budget

    The optimizer first evaluates every feasible site and then
    allocates people using the lowest combined relocation score.
    """

    villages = pd.read_csv(villages_file)
    sites = pd.read_csv(sites_file)

    # Find source village
    source = villages[
        villages["Village"].str.lower()
        == source_village.lower()
    ]

    if source.empty:
        raise ValueError(
            f"Village '{source_village}' was not found."
        )

    source = source.iloc[0]

    source_lat = float(source["Latitude"])
    source_lon = float(source["Longitude"])

    source_population = int(source["Population"])

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

    candidates = []

    for _, site in sites.iterrows():

        distance = haversine_km(
            source_lat,
            source_lon,
            float(site["Latitude"]),
            float(site["Longitude"]),
        )

        capacity = int(site["Capacity"])
        safety = float(site["SafetyScore"])
        cost_per_person = float(site["CostPerPerson"])

        total_cost = target_population * cost_per_person

        # Reject sites that cannot accommodate the population
        if capacity < target_population:
            continue

        # Reject sites exceeding budget
        if total_cost > budget:
            continue

        # Convert distance to a 0-100 normalized risk factor.
        # Longer distance means greater relocation difficulty.
        distance_factor = min(distance / 100.0 * 100.0, 100.0)

        # Safety risk: 100 safety = 0 risk
        safety_risk = 100.0 - safety

        # Normalize cost relative to ₹25,000/person.
        cost_factor = min(
            cost_per_person / 25000.0 * 100.0,
            100.0
        )

        # Combined optimization score.
        #
        # Lower score = better relocation option.
        #
        # Safety:     45%
        # Distance:   25%
        # Cost:       30%
        optimization_score = (
            safety_risk * 0.45
            + distance_factor * 0.25
            + cost_factor * 0.30
        )

        candidates.append(
            {
                "site": site["Site"],
                "latitude": float(site["Latitude"]),
                "longitude": float(site["Longitude"]),
                "capacity": capacity,
                "safety_score": safety,
                "distance_km": round(distance, 2),
                "cost_per_person": cost_per_person,
                "total_cost": total_cost,
                "optimization_score": round(
                    optimization_score,
                    2
                ),
            }
        )

    if not candidates:
        return {
            "status": "no_feasible_solution",
            "message": (
                "No relocation site satisfies the "
                "population capacity and budget constraints."
            ),
            "source_village": source_village,
            "target_population": target_population,
            "budget": budget,
            "candidates": [],
        }

    # Best site = lowest optimization score
    candidates.sort(
        key=lambda x: x["optimization_score"]
    )

    best = candidates[0]

    remaining_budget = budget - best["total_cost"]

    return {
        "status": "success",
        "source_village": source_village,
        "source_risk_score": float(source["RiskScore"]),
        "source_risk_category": source["RiskCategory"],
        "target_population": target_population,
        "budget": budget,
        "recommended_site": best,
        "remaining_budget": round(
            remaining_budget,
            2
        ),
        "evaluated_sites": candidates,
    }
