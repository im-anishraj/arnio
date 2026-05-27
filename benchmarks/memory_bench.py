"""
Standalone memory benchmark — no compiled arnio required.

Compares peak heap allocation for the two CsvReader.read() strategies:

  BEFORE: accumulate every raw row as a list[str] in memory during type
          inference (the old `raw_data` vector / sample-capped approach).

  AFTER : true two-pass streaming — first pass reads lines and infers
          types without storing anything; second pass streams into
          typed columns.

Run:
    python benchmarks/memory_bench.py
"""

import csv
import pathlib
import sys
import tempfile
import tracemalloc

# ---------------------------------------------------------------------------
# 1. Generate a synthetic CSV
# ---------------------------------------------------------------------------
ROWS = 500_000
COLS = 10


def generate_csv(path: pathlib.Path) -> int:
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow([f"col_{i}" for i in range(COLS)])
        for n in range(ROWS):
            w.writerow(
                [
                    n,
                    n * 1.5,
                    f"name_{n % 1000}",
                    n % 2 == 0,
                    n % 100,
                    f"cat_{n % 50}",
                    n * 3.14,
                    n % 7,
                    f"tag_{n % 200}",
                    n + 0.1,
                ]
            )
    return path.stat().st_size


# ---------------------------------------------------------------------------
# 2. "Before" strategy: buffer all raw rows in memory, then iterate
# ---------------------------------------------------------------------------
def strategy_before(path: pathlib.Path):
    """Mirrors the old implementation that stored raw_data: list[list[str]]."""
    raw_data = []
    with open(path, newline="", encoding="utf-8") as fh:
        reader = csv.reader(fh)
        header = next(reader)
        for row in reader:
            raw_data.append(row)  # full in-memory buffer

    # Simulate type inference pass over the cached buffer
    col_types = ["NULL"] * len(header)
    for row in raw_data:
        for ci, val in enumerate(row):
            if col_types[ci] == "NULL" and val:
                col_types[ci] = "string"

    # Simulate build-columns pass over the cached buffer
    columns = {h: [] for h in header}
    for row in raw_data:
        for ci, h in enumerate(header):
            columns[h].append(row[ci] if ci < len(row) else None)

    return columns


# ---------------------------------------------------------------------------
# 3. "After" strategy: two-pass streaming, nothing stored between passes
# ---------------------------------------------------------------------------
def strategy_after(path: pathlib.Path):
    """Mirrors the new streaming implementation."""
    # Pass 1 — infer types, no data cached
    col_types = {}
    with open(path, newline="", encoding="utf-8") as fh:
        reader = csv.reader(fh)
        header = next(reader)
        col_types = {h: "NULL" for h in header}
        for row in reader:
            for ci, h in enumerate(header):
                val = row[ci] if ci < len(row) else ""
                if col_types[h] == "NULL" and val:
                    col_types[h] = "string"

    # Pass 2 — stream rows directly into typed columns
    columns = {h: [] for h in header}
    with open(path, newline="", encoding="utf-8") as fh:
        reader = csv.reader(fh)
        next(reader)  # skip header
        for row in reader:
            for ci, h in enumerate(header):
                columns[h].append(row[ci] if ci < len(row) else None)

    return columns


# ---------------------------------------------------------------------------
# 4. Measurement
# ---------------------------------------------------------------------------
def measure_peak_mib(fn, *args) -> float:
    tracemalloc.start()
    fn(*args)
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return peak / 1024 / 1024


# ---------------------------------------------------------------------------
# 5. Main
# ---------------------------------------------------------------------------
def main():
    with tempfile.TemporaryDirectory() as tmpdir:
        csv_path = pathlib.Path(tmpdir) / "bench.csv"
        file_bytes = generate_csv(csv_path)
        file_mib = file_bytes / 1024 / 1024
        print(
            f"Generated CSV : {ROWS:,} rows × {COLS} cols  ({file_mib:.1f} MiB on disk)\n"
        )

        before_mib = measure_peak_mib(strategy_before, csv_path)
        after_mib = measure_peak_mib(strategy_after, csv_path)
        reduction = (before_mib - after_mib) / before_mib * 100

        print("Peak heap during read()")
        print(f"  Before (buffer-all)  : {before_mib:7.1f} MiB")
        print(f"  After  (streaming)   : {after_mib:7.1f} MiB")
        print(f"  Reduction            : {reduction:7.1f} %")
        print()

        import platform

        print(f"Platform : {platform.platform()}")
        print(f"Python   : {sys.version.split()[0]}")


if __name__ == "__main__":
    main()
