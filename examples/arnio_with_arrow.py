"""
Arnio + Arrow example

Goal:
Clean data using Arnio, then convert to pyarrow.Table
for use with Arrow-native tools.
"""

try:
    import arnio as ar
except ImportError as e:
    raise ImportError(
        "Arnio is required for this example. Install it with: pip install arnio"
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
            "price": [1.5, 0.75, 2.0, 3.0],
            "quantity": [100, 200, 150, None],
            "in_stock": [True, False, True, True],
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

    # --------------------------------------------------
    # Step 3: Export to Arrow
    # --------------------------------------------------
    table = ar.to_arrow(cleaned)

    print("Arrow Table:")
    print(table)
    print("-" * 40)

    print(f"Schema: {table.schema}")
    print(f"Rows: {table.num_rows}, Columns: {table.num_columns}")

    # Convert back to pandas for display
    result = table.to_pandas()
    print("\nRound-tripped through Arrow:")
    print(result)


if __name__ == "__main__":
    main()
