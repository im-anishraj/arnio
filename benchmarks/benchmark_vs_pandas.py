"""
Reproducible benchmark: arnio vs pandas
Run: python benchmarks/benchmark_vs_pandas.py
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
    t0 = time.perf_counter()

    df = pd.read_csv(path)
    df.columns = df.columns.str.strip()
    df = df.dropna()
    df = df.drop_duplicates()
    for col in df.select_dtypes(include=["object", "string"]).columns:
        df[col] = df[col].astype(str).str.strip().str.lower()

    elapsed = time.perf_counter() - t0
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return elapsed, peak / 1024 / 1024


def benchmark_arnio(path):
    
    ensure_dataset_exists(path)
    tracemalloc.start()
    t0 = time.perf_counter()

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

    elapsed = time.perf_counter() - t0
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return elapsed, peak / 1024 / 1024


def avg(values):
    return sum(values) / len(values)


def run_case(case):
    print(case.name)
    print(f"{'Metric':<20} {'pandas':>12} {'arnio':>12}")
    print("-" * 46)

    pd_times, ar_times = [], []
    pd_rams, ar_rams = [], []

    for i in range(RUNS):
        pt, pr = benchmark_pandas(case.path)
        at, ar_r = benchmark_arnio(case.path)
        pd_times.append(pt)
        ar_times.append(at)
        pd_rams.append(pr)
        ar_rams.append(ar_r)

    print(f"{'Exec Time (avg)':<20} {avg(pd_times):>11.2f}s {avg(ar_times):>11.2f}s")
    print(f"{'Peak RAM':<20} {avg(pd_rams):>10.0f}MB {avg(ar_rams):>10.0f}MB")
    print(
        f"\nSpeed: {avg(pd_times)/avg(ar_times):.1f}x | RAM: {(1 - avg(ar_rams)/avg(pd_rams))*100:.0f}% reduction"
    )
    print()


if __name__ == "__main__":
    for benchmark_case in BENCHMARKS:
        run_case(benchmark_case)
