import pandas as pd
import numpy as np
from pathlib import Path


INPUT_FILE = Path(
    "data/historical/India_Flood_Inventory_v3.csv"
)

OUTPUT_FILE = Path(
    "data/historical/flood_state_history.csv"
)


STATE_ALIASES = {
    "jammu & kashmir": "Jammu and Kashmir",
    "jammu and kashmir": "Jammu and Kashmir",
    "jammu & kashmir,": "Jammu and Kashmir",
    "orissa": "Odisha",
    "uttaranchal": "Uttarakhand",
    "pondicherry": "Puducherry",
}


def normalize_state_name(name):
    name = str(name).strip()

    name = name.replace("\n", " ")
    name = " ".join(name.split())

    lookup = name.lower()

    if lookup in STATE_ALIASES:
        return STATE_ALIASES[lookup]

    return name


def split_states(value):
    """
    Split multi-state flood events.

    Example:
        'Maharashtra, Gujarat'
    becomes:
        ['Maharashtra', 'Gujarat']
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


def main():

    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Input file not found: {INPUT_FILE}"
        )

    print("Reading flood inventory...")

    df = pd.read_csv(INPUT_FILE)

    print(f"Original records: {len(df):,}")

    required_columns = [
        "UEI",
        "Start Date",
        "State",
    ]

    missing = [
        column
        for column in required_columns
        if column not in df.columns
    ]

    if missing:
        raise ValueError(
            f"Missing required columns: {missing}"
        )

    # Convert dates
    df["Start Date"] = pd.to_datetime(
        df["Start Date"],
        errors="coerce"
    )

    # Create one row per state involved in an event
    df["State_List"] = df["State"].apply(split_states)

    exploded = df.explode("State_List").copy()

    exploded["State"] = exploded["State_List"].apply(
        normalize_state_name
    )

    exploded = exploded[
        exploded["State"].notna()
        & (exploded["State"] != "")
    ]

    # An event may mention the same state more than once.
    # Count each UEI only once per state.
    exploded = exploded.drop_duplicates(
        subset=["UEI", "State"]
    )

    print(
        f"State-event records after splitting: "
        f"{len(exploded):,}"
    )

    # Number of unique historical flood events
    event_counts = (
        exploded
        .groupby("State")["UEI"]
        .nunique()
        .rename("HistoricalFloodEvents")
    )

    # Number of unique years with flood events
    years_affected = (
        exploded
        .dropna(subset=["Start Date"])
        .assign(
            Year=exploded["Start Date"].dt.year
        )
        .groupby("State")["Year"]
        .nunique()
        .rename("YearsAffected")
    )

    # Earliest and latest event year
    first_year = (
        exploded
        .dropna(subset=["Start Date"])
        .groupby("State")["Start Date"]
        .min()
        .dt.year
        .rename("FirstRecordedYear")
    )

    last_year = (
        exploded
        .dropna(subset=["Start Date"])
        .groupby("State")["Start Date"]
        .max()
        .dt.year
        .rename("LastRecordedYear")
    )

    result = pd.concat(
        [
            event_counts,
            years_affected,
            first_year,
            last_year,
        ],
        axis=1
    ).reset_index()

    result = result.rename(
        columns={
            "State": "State"
        }
    )

    result["HistoricalFloodEvents"] = (
        result["HistoricalFloodEvents"]
        .fillna(0)
        .astype(int)
    )

    result["YearsAffected"] = (
        result["YearsAffected"]
        .fillna(0)
        .astype(int)
    )

    # ---------------------------------------------------------
    # Historical occurrence index
    #
    # This is a RELATIVE historical occurrence measure.
    # It is NOT a probability of future flooding.
    #
    # Log scaling prevents states with very large event counts
    # from completely dominating the visualization.
    # ---------------------------------------------------------

    max_events = result[
        "HistoricalFloodEvents"
    ].max()

    if max_events > 0:

        result["HistoricalIndex"] = (
            np.log1p(
                result["HistoricalFloodEvents"]
            )
            /
            np.log1p(max_events)
            * 100
        )

    else:
        result["HistoricalIndex"] = 0

    result["HistoricalIndex"] = (
        result["HistoricalIndex"]
        .round(2)
    )

    def category(index):

        if index >= 75:
            return "Very High"

        if index >= 60:
            return "High"

        if index >= 40:
            return "Moderate"

        return "Lower occurrence"

    result["HistoricalCategory"] = (
        result["HistoricalIndex"]
        .apply(category)
    )

    result["SourcePeriod"] = "1967-2023"

    result = result.sort_values(
        "HistoricalFloodEvents",
        ascending=False
    )

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    result.to_csv(
        OUTPUT_FILE,
        index=False
    )

    print()
    print("Flood historical dataset created successfully.")
    print(f"Output: {OUTPUT_FILE}")
    print()
    print("Top 15 states by historical flood events:")
    print(
        result[
            [
                "State",
                "HistoricalFloodEvents",
                "YearsAffected",
                "HistoricalIndex",
                "HistoricalCategory",
            ]
        ]
        .head(15)
        .to_string(index=False)
    )

    print()
    print(
        "Total states represented:",
        len(result)
    )


if __name__ == "__main__":
    main()
