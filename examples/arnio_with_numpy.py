"""
Arnio + NumPy example

Goal:
Clean numeric data using Arnio, then perform computations with NumPy.
"""

try:
    import arnio as ar
except ImportError as e:
    raise ImportError(
        "Arnio is required for this example. Install it with: pip install arnio"
    ) from e

try:
    import numpy as np
except ImportError as e:
    raise ImportError(
        "NumPy is required for this example. Install it with: pip install numpy"
    ) from e

try:
    import pandas as pd
except ImportError as e:
    raise ImportError(
        "pandas is required for this example. Install it with: pip install pandas"
    ) from e


def main():
    # --------------------------------------------------
    # Step 1: Create messy numeric data
    # --------------------------------------------------
    df = pd.DataFrame({"values": ["10", "20", "bad", "30", None, "1000"]})

    print("Original Data:\n", df)
    print("-" * 40)

    # --------------------------------------------------
    # Step 2: Clean data using Arnio pipeline
    # --------------------------------------------------
    frame = ar.from_pandas(df)

    cleaned = ar.pipeline(
        frame,
        [
            ("drop_nulls",),
            ("strip_whitespace",),
        ],
    )

    clean_df = ar.to_pandas(cleaned)

    # Convert values to numeric and drop invalid entries
    clean_df["values"] = pd.to_numeric(clean_df["values"], errors="coerce")
    clean_df = clean_df.dropna()

    # Use Arnio's built-in clip_numeric helper
    frame = ar.from_pandas(clean_df)
    frame = ar.clip_numeric(frame, lower=0, upper=100)
    clean_df = ar.to_pandas(frame)

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
