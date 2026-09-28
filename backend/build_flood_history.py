import pandas as pd
import numpy as np
from pathlib import Path


# ============================================================
# FILES
# ============================================================

INPUT_FILE = Path(
    "data/historical/India_Flood_Inventory_v3.csv"
)

OUTPUT_FILE = Path(
    "data/historical/flood_state_history.csv"
)


# ============================================================
# STATE NAME NORMALIZATION
# ============================================================

STATE_ALIASES = {
    "jammu & kashmir": "Jammu and Kashmir",
    "jammu and kashmir": "Jammu and Kashmir",
    "jammu & kashmir,": "Jammu and Kashmir",

    "orissa": "Odisha",

    "uttaranchal": "Uttarakhand",

    "pondicherry": "Puducherry",

    "andaman and nicobar": "Andaman and Nicobar Islands",

    "andaman & nicobar": "Andaman and Nicobar Islands",
}


def normalize_state_name(name):
    """
    Clean and standardize a state name.
    """

    if pd.isna(name):
        return ""

    name = str(name).strip()

    name = name.replace("\n", " ")

    name = " ".join(name.split())

    lookup = name.lower()

    if lookup in STATE_ALIASES:
        return STATE_ALIASES[lookup]

    return name


# ============================================================
# SPLIT MULTI-STATE EVENTS
# ============================================================

def split_states(value):
    """
    Convert a state field such as:

        Maharashtra, Gujarat

    into:

        Maharashtra
        Gujarat
    """

    if pd.isna(value):
        return []

    parts = str(value).split(",")

    states = []

    for part in parts:

        state = normalize_state_name(part)

        if state:
            states.append(state)

    return states


# ============================================================
# MAIN PROCESSING
# ============================================================

def main():

    print("=" * 60)
    print("PUNARVAS - Historical Flood Data Processor")
    print("=" * 60)

    # --------------------------------------------------------
    # Check input file
    # --------------------------------------------------------

    if not INPUT_FILE.exists():

        raise FileNotFoundError(
            f"\nInput file not found:\n{INPUT_FILE}\n"
        )

    print()
    print("Reading flood inventory...")

    df = pd.read_csv(INPUT_FILE)

    print(
        f"Original records: {len(df):,}"
    )

    # --------------------------------------------------------
    # Check required columns
    # --------------------------------------------------------

    required_columns = [
        "UEI",
        "Start Date",
        "State",
    ]

    missing_columns = []

    for column in required_columns:

        if column not in df.columns:
            missing_columns.append(column)

    if missing_columns:

        raise ValueError(
            "\nMissing required columns:\n"
            + "\n".join(
                f"- {column}"
                for column in missing_columns
            )
        )

    # --------------------------------------------------------
    # Convert dates
    # --------------------------------------------------------

    df["Start Date"] = pd.to_datetime(
        df["Start Date"],
        errors="coerce"
    )

    # --------------------------------------------------------
    # Split states
    # --------------------------------------------------------

    print()
    print("Processing multi-state flood events...")

    df["State_List"] = df["State"].apply(
        split_states
    )

    exploded = df.explode(
        "State_List"
    ).reset_index(drop=True)

    exploded["State"] = exploded[
        "State_List"
    ].apply(
        normalize_state_name
    )

    # --------------------------------------------------------
    # Remove empty states
    # --------------------------------------------------------

    exploded = exploded[
        exploded["State"].notna()
        & (exploded["State"] != "")
    ].copy()

    # --------------------------------------------------------
    # Each UEI + State should appear only once
    # --------------------------------------------------------

    exploded = exploded.drop_duplicates(
        subset=[
            "UEI",
            "State",
        ]
    ).reset_index(drop=True)

    print(
        "State-event records after splitting: "
        f"{len(exploded):,}"
    )

    # ========================================================
    # HISTORICAL EVENT COUNT
    # ========================================================

    event_counts = (
        exploded
        .groupby("State")["UEI"]
        .nunique()
        .rename(
            "HistoricalFloodEvents"
        )
    )

    # ========================================================
    # YEARS AFFECTED
    # ========================================================

    date_data = exploded[
        [
            "State",
            "Start Date",
        ]
    ].copy()

    date_data = date_data[
        date_data["Start Date"].notna()
    ].copy()

    date_data["Year"] = (
        date_data["Start Date"]
        .dt.year
    )

    years_affected = (
        date_data
        .groupby("State")["Year"]
        .nunique()
        .rename(
            "YearsAffected"
        )
    )

    # ========================================================
    # FIRST RECORDED YEAR
    # ========================================================

    first_year = (
        date_data
        .groupby("State")["Year"]
        .min()
        .rename(
            "FirstRecordedYear"
        )
    )

    # ========================================================
    # LAST RECORDED YEAR
    # ========================================================

    last_year = (
        date_data
        .groupby("State")["Year"]
        .max()
        .rename(
            "LastRecordedYear"
        )
    )

    # ========================================================
    # COMBINE RESULTS
    # ========================================================

    result = pd.concat(
        [
            event_counts,
            years_affected,
            first_year,
            last_year,
        ],
        axis=1
    ).reset_index()

    # --------------------------------------------------------
    # Clean missing values
    # --------------------------------------------------------

    result[
        "HistoricalFloodEvents"
    ] = (
        result[
            "HistoricalFloodEvents"
        ]
        .fillna(0)
        .astype(int)
    )

    result[
        "YearsAffected"
    ] = (
        result[
            "YearsAffected"
        ]
        .fillna(0)
        .astype(int)
    )

    result[
        "FirstRecordedYear"
    ] = (
        result[
            "FirstRecordedYear"
        ]
        .fillna(0)
        .astype(int)
    )

    result[
        "LastRecordedYear"
    ] = (
        result[
            "LastRecordedYear"
        ]
        .fillna(0)
        .astype(int)
    )

    # ========================================================
    # HISTORICAL OCCURRENCE INDEX
    # ========================================================

    max_events = result[
        "HistoricalFloodEvents"
    ].max()

    if max_events > 0:

        result[
            "HistoricalIndex"
        ] = (
            np.log1p(
                result[
                    "HistoricalFloodEvents"
                ]
            )
            /
            np.log1p(max_events)
            * 100
        )

    else:

        result[
            "HistoricalIndex"
        ] = 0.0

    result[
        "HistoricalIndex"
    ] = (
        result[
            "HistoricalIndex"
        ]
        .round(2)
    )

    # ========================================================
    # HISTORICAL CATEGORY
    # ========================================================

    def get_category(index):

        if index >= 75:
            return "Very High"

        elif index >= 60:
            return "High"

        elif index >= 40:
            return "Moderate"

        else:
            return "Lower occurrence"

    result[
        "HistoricalCategory"
    ] = (
        result[
            "HistoricalIndex"
        ]
        .apply(get_category)
    )

    # ========================================================
    # SOURCE PERIOD
    # ========================================================

    result[
        "SourcePeriod"
    ] = "1967-2023"

    # ========================================================
    # SORT
    # ========================================================

    result = result.sort_values(
        by="HistoricalFloodEvents",
        ascending=False
    ).reset_index(
        drop=True
    )

    # ========================================================
    # SAVE
    # ========================================================

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    result.to_csv(
        OUTPUT_FILE,
        index=False
    )

    # ========================================================
    # DISPLAY RESULTS
    # ========================================================

    print()
    print("=" * 60)
    print("SUCCESS")
    print("=" * 60)

    print()
    print(
        "Output file:"
    )

    print(
        OUTPUT_FILE
    )

    print()
    print(
        "Total states represented:",
        len(result)
    )

    print()
    print(
        "Top 15 states by historical flood events:"
    )

    print()

    display_columns = [
        "State",
        "HistoricalFloodEvents",
        "YearsAffected",
        "HistoricalIndex",
        "HistoricalCategory",
    ]

    print(
        result[
            display_columns
        ]
        .head(15)
        .to_string(
            index=False
        )
    )

    print()
    print("=" * 60)
    print(
        "Historical index is a relative occurrence measure."
    )
    print(
        "It is NOT a future flood probability."
    )
    print("=" * 60)


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    main()
