"""
Arnio + DuckDB example

Goal:
Clean data using Arnio, then query it using DuckDB's
in-memory SQL engine.
"""

try:
    import arnio as ar
except ImportError as e:
    raise ImportError(
        "Arnio is required for this example. Install it with: pip install arnio"
    ) from e

try:
    import duckdb
except ImportError as e:
    raise ImportError(
        "DuckDB is required for this example. Install it with: pip install duckdb"
    ) from e

try:
    import pandas as pd
except ImportError as e:
    raise ImportError(
        "pandas is required for this example. Install it with: pip install pandas"
    ) from e


def main():
    # --------------------------------------------------
    # Step 1: Create messy dataset
    # --------------------------------------------------
    df = pd.DataFrame(
        {
            "product": [" Apple ", "Banana", "CHERRY", None],
            "price": ["1.5", "0.75", "bad", "2.0"],
            "quantity": ["100", "200", "150", None],
        }
    )

    print("Original Data:")
    print(df)
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
            ("normalize_case", {"case_type": "lower"}),
        ],
    )

    clean_df = ar.to_pandas(cleaned)

    # coerce non-numeric strings to NaN and drop them
    clean_df["price"] = pd.to_numeric(clean_df["price"], errors="coerce")
    clean_df["quantity"] = pd.to_numeric(clean_df["quantity"], errors="coerce")
    clean_df = clean_df.dropna()

    print("Cleaned Data:")
    print(clean_df)
    print("-" * 40)

    # --------------------------------------------------
    # Step 3: Query with DuckDB
    # --------------------------------------------------
    result = duckdb.query(
        "SELECT product, price, quantity, price * quantity AS total_value "
        "FROM clean_df "
        "ORDER BY total_value DESC"
    ).df()

    print("DuckDB Query Result (sorted by total value):")
    print(result)


if __name__ == "__main__":
    main()
