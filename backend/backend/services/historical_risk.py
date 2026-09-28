"""
PUNARVAS historical-risk data layer.

This module uses documented historical disaster inventories, not the
synthetic feature-engineering values used for village-level demo analysis.

Current bundled source:
- ISRO/NRSC Landslide Atlas of India, 1998-2022.
  ~80,000 mapped landslides; state totals are taken from Table 2.

The returned "HistoricalIndex" is a relative occurrence index (0-100)
derived from the official state inventory counts. It is NOT a probability
of future disaster and "Low" means low relative occurrence within the
bundled inventory, not "safe".
"""

from pathlib import Path
import csv

BASE_DIR = Path(__file__).resolve().parents[1]
LANDSLIDE_FILE = BASE_DIR / "data" / "historical" / "landslide_state_inventory.csv"

def load_landslide_history():
    with LANDSLIDE_FILE.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))

def get_historical_risk(hazard: str):
    h = hazard.strip().lower()

    if h == "landslide":
        rows = load_landslide_history()
        return {
            "hazard": "Landslide",
            "layer_type": "historical_inventory",
            "period": "1998-2022",
            "source": "ISRO / NRSC Landslide Atlas of India",
            "source_url": "https://www.isro.gov.in/Landslide_Atlas_India.html",
            "coverage_note": (
                "The ISRO inventory covers landslide-vulnerable regions "
                "in 17 states and 2 UTs. States outside this inventory are "
                "not automatically safe."
            ),
            "states": [
                {
                    "state": r["State"],
                    "historical_count": int(r["LandslideCount_1998_2022"]),
                    "historical_index": float(r["HistoricalIndex"]),
                    "category": r["HistoricalCategory"],
                }
                for r in rows
            ],
        }

    if h == "flood":
        return {
            "hazard": "Flood",
            "layer_type": "historical_source_pending",
            "period": "1901-2020 / 1967-2023 depending on source",
            "source": "India Flood Atlas / India Flood Inventory",
            "source_url": "https://github.com/wcl-iitgn/india-flood-atlas-data",
            "coverage_note": (
                "Use the India Flood Atlas long-term state risk data or "
                "the IFI-Impacts inventory. The frontend integration is "
                "prepared for this source, but no flood values are hard-coded."
            ),
            "states": [],
        }

    return {
        "hazard": hazard,
        "layer_type": "not_available",
        "period": None,
        "source": None,
        "source_url": None,
        "coverage_note": (
            "A comparable India-wide historical inventory is not bundled "
            "for this hazard yet."
        ),
        "states": [],
    }
