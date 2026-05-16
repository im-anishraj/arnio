"""
Reproducible benchmark: arnio vs pandas

Run:
python benchmarks/benchmark_vs_pandas.py
"""

import time
import tracemalloc
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

import arnio as ar

CSV_FILE = "benchmarks/benchmark_1m.csv"
WIDE_CSV_FILE = "benchmarks/benchmark_wide.csv"
MULTILINE_CSV_FILE = "benchmarks/benchmark_multiline.csv"

RUNS = 3

ENVIRONMENT_NOTES = """
Benchmark Environment:
- Comparison: arnio vs pandas
- Deterministic datasets with fixed RNG seeds
- Same dataset shapes across runs
- Recommended:
    python benchmarks/generate_data.py
    python benchmarks/benchmark_vs_pandas.py
"""


@dataclass(frozen=True)
class BenchmarkCase:
    name: str
    path: str


BENCHMARKS = (
    BenchmarkCase(
        "Tall CSV (1,000,000 rows x 12 columns)",
        CSV_FILE,
    ),
    BenchmarkCase(
        "Wide CSV (5,000 rows x 256 columns)",
        WIDE_CSV_FILE,
    ),
    BenchmarkCase(
        "Quoted Multiline CSV",
        MULTILINE_CSV_FILE,
    ),
)


def ensure_dataset_exists(path):
    if not Path(path).exists():
        raise FileNotFoundError(
            f"Missing benchmark dataset: {path}\n"
            "Run: python benchmarks/generate_data.py"
        )


def benchmark_pandas(path):
    ensure_dataset_exists(path)

    tracemalloc.start()
    start = time.perf_counter()

    df = pd.read_csv(path)

    df.columns = df.columns.str.strip()

    df = df.dropna()
    df = df.drop_duplicates()

    for col in df.select_dtypes(include=["object", "string"]).columns:
        df[col] = df[col].astype(str).str.strip().str.lower()

    elapsed = time.perf_counter() - start
    _, peak = tracemalloc.get_traced_memory()

    tracemalloc.stop()

    return elapsed, peak / 1024 / 1024


def benchmark_arnio(path):
    ensure_dataset_exists(path)

    tracemalloc.start()
    start = time.perf_counter()

    frame = ar.read_csv(path)

    clean = ar.pipeline(
        frame,
        [
            ("strip_whitespace",),
            ("normalize_case", {"case_type": "lower"}),
            ("drop_nulls",),
            ("drop_duplicates",),
        ],
    )

    ar.to_pandas(clean)

    elapsed = time.perf_counter() - start
    _, peak = tracemalloc.get_traced_memory()

    tracemalloc.stop()

    return elapsed, peak / 1024 / 1024


def avg(values):
    return sum(values) / len(values)


def run_case(case):
    print("=" * 72)
    print(case.name)
    print("=" * 72)

    print(f"{'Metric':<20} {'pandas':>12} {'arnio':>12}")
    print("-" * 48)

    pandas_times = []
    arnio_times = []

    pandas_memory = []
    arnio_memory = []

    for _ in range(RUNS):
        pandas_time, pandas_ram = benchmark_pandas(case.path)
        arnio_time, arnio_ram = benchmark_arnio(case.path)

        pandas_times.append(pandas_time)
        arnio_times.append(arnio_time)

        pandas_memory.append(pandas_ram)
        arnio_memory.append(arnio_ram)

    avg_pandas_time = avg(pandas_times)
    avg_arnio_time = avg(arnio_times)

    avg_pandas_ram = avg(pandas_memory)
    avg_arnio_ram = avg(arnio_memory)

    print(
        f"{'Exec Time (avg)':<20}"
        f"{avg_pandas_time:>11.2f}s"
        f"{avg_arnio_time:>11.2f}s"
    )

    print(
        f"{'Peak RAM':<20}"
        f"{avg_pandas_ram:>10.0f}MB"
        f"{avg_arnio_ram:>10.0f}MB"
    )

    speedup = avg_pandas_time / avg_arnio_time
    ram_reduction = (
        (1 - (avg_arnio_ram / avg_pandas_ram)) * 100
        if avg_pandas_ram
        else 0
    )

    print(
        f"\nSpeed: {speedup:.1f}x"
        f" | RAM Reduction: {ram_reduction:.0f}%"
    )

    print()


if __name__ == "__main__":
    print(ENVIRONMENT_NOTES)

    for benchmark_case in BENCHMARKS:
        run_case(benchmark_case)
