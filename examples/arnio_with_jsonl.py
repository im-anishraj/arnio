"""JSONL Data Loading and Pipeline Processing Example for Arnio.

--------------------------------------------------------------
This script demonstrates how to load a JSONL file, define a data-cleaning pipeline
(including whitespace stripping, duplicate dropping, and null-value filling),
and convert the final result into a clean pandas DataFrame.
"""

import json
import os

import arnio as ar


def main():
    # 1. Create a sample JSONL file with messy records
    sample_jsonl = "sample_messy_data.jsonl"
    records = [
        {"name": "  Alice  ", "age": 30, "city": "New York"},
        {"name": "Bob", "age": None, "city": None},  # Missing values
        {"name": "Charlie", "age": 35, "city": "  London  "},
        {"name": "Alice", "age": 30, "city": "New York"},  # Duplicate record
    ]

    with open(sample_jsonl, "w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record) + "\n")

    print(f"Created sample JSONL file: {sample_jsonl}")

    # 2. Load the JSONL file using Arnio C++ accelerated reader
    frame = ar.read_jsonl(sample_jsonl)
    print("\n--- Raw Data Schema ---")
    print(frame.dtypes)

    # 3. Define and run a strict cleaning pipeline
    clean_frame = ar.pipeline(
        frame,
        [
            ("strip_whitespace",),
            ("normalize_case", {"case_type": "title"}),
            ("fill_nulls", {"value": 0, "subset": ["age"]}),
            ("fill_nulls", {"value": "Unknown", "subset": ["city"]}),
            ("drop_duplicates",),
        ],
    )

    # 4. Export the clean dataset to a pandas DataFrame
    df = ar.to_pandas(clean_frame)
    print("\n--- Cleaned Pandas DataFrame ---")
    print(df)

    # Cleanup temporary file
    if os.path.exists(sample_jsonl):
        os.remove(sample_jsonl)
        print(f"\nRemoved temporary file: {sample_jsonl}")


if __name__ == "__main__":
    main()
