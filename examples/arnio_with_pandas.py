"""
Arnio + pandas: Clean a messy CSV, then analyze with pandas.
-------------------------------------------------------------
This example shows how to use Arnio to clean raw data and then
hand the result off to pandas for analysis.

Run:
    python examples/arnio_with_pandas.py
"""

import io
import arnio as ar


def main():
    # 1. Synthetic messy CSV (inline, no external file needed)
    raw_csv = (
        "product,price,category\n"
        " Widget A ,12.5,electronics\n"
        "Widget B,,electronics\n"   # missing price
        " Widget A ,12.5,electronics\n"  # duplicate
        "Gadget C,8.0, TOOLS \n"
        "Gadget D,0.0,tools\n"  # zero price (valid)
    )

    # 2. Load raw data through Arnio's C++ core
    frame = ar.read_csv(io.StringIO(raw_csv))
    print("--- Raw Data ---")
    print(ar.to_pandas(frame))

    # 3. Clean with an Arnio pipeline
    clean_frame = ar.pipeline(
        frame,
        [
            ("strip_whitespace",),
            ("normalize_case", {"case_type": "title"}),
            ("fill_nulls", {"value": 0.0, "subset": ["price"]}),
            ("drop_duplicates",),
        ],
    )

    # 4. Convert to pandas for analysis
    df = ar.to_pandas(clean_frame)
    print("\n--- Cleaned DataFrame ---")
    print(df)

    # 5. Analyze with pandas
    print("\n--- Average price by category ---")
    summary = df.groupby("category")["price"].mean().reset_index()
    print(summary)


if __name__ == "__main__":
    main()
