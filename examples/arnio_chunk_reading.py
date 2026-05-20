"""Example demonstrating memory-efficient chunked CSV reading with Arnio."""

import tempfile

import arnio as ar


def main() -> None:
    # 1. Create a sample CSV file
    data = (
        "id,name,salary,department\n"
        "1,Alice,85000,Engineering\n"
        "2,Bob,92000,Product\n"
        "3,Charlie,78000,Design\n"
        "4,Diana,95000,Engineering\n"
        "5,Evan,88000,Marketing\n"
    )

    with tempfile.NamedTemporaryFile("w", delete=False, suffix=".csv") as temp_file:
        temp_file.write(data)
        temp_path = temp_file.name

    print("Created temporary sample CSV file.")

    # 2. Read the CSV iteratively in chunks of 2 rows
    print("\nReading CSV iteratively in chunks:")
    chunks = ar.read_csv_chunked(temp_path, chunksize=2)

    for idx, chunk in enumerate(chunks):
        print(f"\n--- Chunk {idx + 1} ---")
        # Convert ArnFrame chunk to a pandas DataFrame for processing/viewing
        df = ar.to_pandas(chunk)
        print(df)

        # Perform cleaning/filtering on the chunk
        cleaned = ar.strip_whitespace(chunk, columns=["name", "department"])
        cleaned_df = ar.to_pandas(cleaned)
        print(f"Cleaned Chunk {idx + 1}:")
        print(cleaned_df)


if __name__ == "__main__":
    main()
