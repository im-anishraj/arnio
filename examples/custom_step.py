"""
Custom Step Example for Arnio
-----------------------------
This script shows how to register a pure-Python cleaning step
and use it seamlessly within an Arnio pipeline.
"""

import os

import pandas as pd

import arnio as ar


# 1. Define a pure-Python function that takes a DataFrame and returns a DataFrame
def remove_outliers(
    df: pd.DataFrame, column: str, threshold: float = 100.0
) -> pd.DataFrame:
    """Removes rows where the specified column exceeds the threshold."""
    print(f"[Custom Step] Removing outliers > {threshold} from '{column}'")
    # Using pandas operations
    if column in df.columns:
        # We need to handle potential NA values first, or dropna subset
        mask = pd.to_numeric(df[column], errors="coerce").fillna(0) <= threshold
        return df[mask].reset_index(drop=True)
    return df


def main():
    # 2. Register the custom step with Arnio
    ar.register_step("remove_outliers", remove_outliers)

    # 3. Create sample data
    sample_csv = "sample_outliers.csv"
    with open(sample_csv, "w") as f:
        f.write("id,value\n")
        f.write("1,50.5\n")
        f.write("2,99.9\n")
        f.write("3,1050.0\n")  # Outlier
        f.write("4,10.0\n")

    # 4. Load and run pipeline including the custom step
    frame = ar.read_csv(sample_csv)

    clean_frame = ar.pipeline(
        frame,
        [
            ("cast_types", {"value": "float64"}),
            ("remove_outliers", {"column": "value", "threshold": 100.0}),
        ],
    )

    df = ar.to_pandas(clean_frame)
    print("\n--- Cleaned Pandas DataFrame ---")
    print(df)

    # Cleanup
    os.remove(sample_csv)


if __name__ == "__main__":
    main()
