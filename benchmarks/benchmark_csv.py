import csv
import tempfile
import time
from pathlib import Path

import arnio


def generate_test_csv(filename, num_rows=200000, num_cols=10):
    filename = Path(filename)
    if not filename.exists():
        print(f"Generating test CSV with {num_rows} rows...")
        with filename.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            header = [f"col_{i}" for i in range(num_cols)]
            writer.writerow(header)
            for i in range(num_rows):
                row = [
                    f"value_{i}_{j}" if j % 2 == 0 else str(i * j)
                    for j in range(num_cols)
                ]
                writer.writerow(row)
        print("Generated.")


def run_benchmark(filename):
    print("Benchmarking arnio.read_csv()...")
    start_time = time.perf_counter()
    df = arnio.read_csv(filename)
    end_time = time.perf_counter()
    duration = end_time - start_time
    print(f"Time taken to read {filename}: {duration:.4f} seconds")
    print(f"Shape: ({len(df)}, {len(df.columns) if hasattr(df, 'columns') else '?'})")
    return duration


if __name__ == "__main__":
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir) / "large_benchmark.csv"
        generate_test_csv(test_file)
        run_benchmark(test_file)
