"""
Basic Usage Example for Arnio
-----------------------------
This script demonstrates the core functionality of Arnio:
reading a CSV file, defining a cleaning pipeline, and converting the result
to a pandas DataFrame.
"""

import os

import arnio as ar


def main():
    # 1. Create a sample CSV file
    sample_csv = "sample_messy_data.csv"
    with open(sample_csv, "w") as f:
        f.write("name,age,city\n")
        f.write("  Alice  ,30,New York\n")
        f.write("Bob,,\n")  # Missing age and city
        f.write("Charlie,35,  London  \n")
        f.write("Alice,30,New York\n")  # Duplicate

    print(f"Created sample file: {sample_csv}")

    # 2. Load the raw file using the C++ core
    frame = ar.read_csv(sample_csv)
    print("\n--- Raw Data Schema ---")
    print(frame.dtypes)

    # 3. Define a strict, readable cleaning pipeline
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

    # 4. Export to a clean pandas DataFrame
    df = ar.to_pandas(clean_frame)
    print("\n--- Cleaned Pandas DataFrame ---")
    print(df)

    # Cleanup
    os.remove(sample_csv)


if __name__ == "__main__":
    main()
