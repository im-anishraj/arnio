"""
Arnio + NumPy example

Goal:
Clean numeric data using Arnio, then perform computations with NumPy.
"""

import numpy as np
import pandas as pd

# Try importing Arnio
try:
    import arnio as ar
    ARNIO_AVAILABLE = True
except Exception:
    ARNIO_AVAILABLE = False

def main():
    # --------------------------------------------------
    # Step 1: Create messy numeric data
    # --------------------------------------------------
    df = pd.DataFrame({
        "values": ["10", "20", "bad", "30", None, "1000"]
    })

    print("Original Data:\n", df)
    print("-" * 40)

    # --------------------------------------------------
    # Step 2: Clean data
    # --------------------------------------------------
    if ARNIO_AVAILABLE:
        frame = ar.from_pandas(df)

        cleaned = ar.pipeline(
            frame,
            [
                ("drop_nulls",),
                ("strip_whitespace",),
                ("cast_types", {"mapping": {"values": "float64"}}),
                ("clip_numeric", {"lower": 0, "upper": 100}),
            ],
        )

        clean_df = ar.to_pandas(cleaned)

    else:
        # Fallback cleaning (safe and explicit)
        clean_df = df.dropna().copy()
        clean_df["values"] = pd.to_numeric(
            clean_df["values"], errors="coerce"
        )
        clean_df = clean_df.dropna()
        clean_df["values"] = clean_df["values"].clip(0, 100)

    print("Cleaned Data:\n", clean_df)
    print("-" * 40)

    # --------------------------------------------------
    # Step 3: NumPy computation
    # --------------------------------------------------
    arr = clean_df["values"].to_numpy(dtype=float)

    print("NumPy Array:", arr)
    print("Mean:", np.mean(arr))
    print("Std Dev:", np.std(arr))


if __name__ == "__main__":
    main()