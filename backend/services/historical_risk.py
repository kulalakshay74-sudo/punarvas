from pathlib import Path
import pandas as pd


BASE_DIR = Path(__file__).resolve().parent.parent

HISTORICAL_DIR = (
    BASE_DIR
    / "data"
    / "historical"
)


LANDSLIDE_FILE = (
    HISTORICAL_DIR
    / "landslide_state_inventory.csv"
)


FLOOD_FILE = (
    HISTORICAL_DIR
    / "flood_state_history.csv"
)


STATE_ALIASES = {
    "jammu & kashmir": "Jammu and Kashmir",
    "jammu and kashmir": "Jammu and Kashmir",
    "orissa": "Odisha",
    "uttaranchal": "Uttarakhand",
    "pondicherry": "Puducherry",
    "andaman and nicobar":
        "Andaman and Nicobar Islands",
    "andaman & nicobar":
        "Andaman and Nicobar Islands",
}


def normalize_state_name(name):
    """
    Normalize state names so that historical datasets
    can be matched with the India GeoJSON.
    """

    name = str(name).strip()

    name = name.replace("\n", " ")

    name = " ".join(name.split())

    lookup = name.lower()

    return STATE_ALIASES.get(
        lookup,
        name
    )


def get_landslide_risk():

    if not LANDSLIDE_FILE.exists():

        return {
            "hazard": "Landslide",
            "layer_type": "historical_inventory",
            "period": "1998-2022",
            "source": "ISRO / NRSC Landslide Atlas of India",
            "source_url":
                "https://www.isro.gov.in/Landslide_Atlas_India.html",
            "coverage_note":
                "Historical landslide inventory. "
                "States outside the inventory are not "
                "automatically safe.",
            "states": [],
        }

    df = pd.read_csv(
        LANDSLIDE_FILE
    )

    states = []

    for _, row in df.iterrows():

        state = normalize_state_name(
            row["State"]
        )

        states.append(
            {
                "state": state,

                "historical_count":
                    int(
                        row[
                            "LandslideCount_1998_2022"
                        ]
                    ),

                "historical_index":
                    float(
                        row[
                            "HistoricalIndex"
                        ]
                    ),

                "category":
                    str(
                        row[
                            "HistoricalCategory"
                        ]
                    ),
            }
        )

    return {
        "hazard": "Landslide",

        "layer_type":
            "historical_inventory",

        "period":
            "1998-2022",

        "source":
            "ISRO / NRSC Landslide Atlas of India",

        "source_url":
            "https://www.isro.gov.in/Landslide_Atlas_India.html",

        "coverage_note":
            "The ISRO inventory covers "
            "landslide-vulnerable regions in "
            "17 states and 2 UTs. "
            "States outside this inventory are "
            "not automatically safe.",

        "states":
            states,
    }


def get_flood_risk():

    if not FLOOD_FILE.exists():

        return {
            "hazard": "Flood",

            "layer_type":
                "historical_inventory",

            "period":
                "1967-2023",

            "source":
                "India Flood Inventory-Impacts / IMD",

            "source_url":
                "https://zenodo.org/records/16994648",

            "coverage_note":
                "Historical flood events from the "
                "India Flood Inventory. "
                "Historical occurrence does not "
                "represent future probability.",

            "states": [],
        }

    df = pd.read_csv(
        FLOOD_FILE
    )

    states = []

    for _, row in df.iterrows():

        state = normalize_state_name(
            row["State"]
        )

        states.append(
            {
                "state": state,

                "historical_count":
                    int(
                        row[
                            "HistoricalFloodEvents"
                        ]
                    ),

                "years_affected":
                    int(
                        row[
                            "YearsAffected"
                        ]
                    ),

                "first_recorded_year":
                    int(
                        row[
                            "FirstRecordedYear"
                        ]
                    ),

                "last_recorded_year":
                    int(
                        row[
                            "LastRecordedYear"
                        ]
                    ),

                "historical_index":
                    float(
                        row[
                            "HistoricalIndex"
                        ]
                    ),

                "category":
                    str(
                        row[
                            "HistoricalCategory"
                        ]
                    ),
            }
        )

    return {
        "hazard": "Flood",

        "layer_type":
            "historical_inventory",

        "period":
            "1967-2023",

        "source":
            "India Flood Inventory-Impacts / IMD",

        "source_url":
            "https://zenodo.org/records/16994648",

        "coverage_note":
            "Historical flood events from "
            "1967-2023. The inventory is based "
            "on event records sourced from IMD. "
            "Historical occurrence is not the "
            "same as future flood probability.",

        "states":
            states,
    }


def get_historical_risk(
    hazard="Landslide"
):

    hazard = str(
        hazard
    ).strip().lower()

    if hazard == "landslide":

        return get_landslide_risk()

    if hazard == "flood":

        return get_flood_risk()

    if hazard in [
        "coastal erosion",
        "coastal",
        "erosion",
    ]:

        return {
            "hazard":
                "Coastal Erosion",

            "layer_type":
                "historical_source_pending",

            "period":
                "Pending verified integration",

            "source":
                "ISRO Shoreline Change Atlas",

            "source_url":
                "https://www.isro.gov.in/",

            "coverage_note":
                "Coastal historical data will "
                "be integrated from a verified "
                "shoreline-change source.",

            "states": [],
        }

    if hazard in [
        "cloudburst",
        "cloud burst",
    ]:

        return {
            "hazard":
                "Cloudburst",

            "layer_type":
                "historical_source_pending",

            "period":
                "Pending verified integration",

            "source":
                "Official disaster records",

            "coverage_note":
                "A verified historical cloudburst "
                "inventory will be integrated "
                "before displaying state-level "
                "values.",

            "states": [],
        }

    return {
        "hazard":
            hazard,

        "layer_type":
            "not_available",

        "period":
            None,

        "source":
            None,

        "states": [],
    }
