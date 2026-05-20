"""
Benchmark: CSV numeric parse with std::from_chars
==================================================
Measures CSV read speed and memory for numeric-heavy data.

Since the C++ parser now uses `std::from_chars` instead of
`std::istringstream` / `std::stoll` / `std::stod`, numeric-heavy
CSV files should parse faster. This benchmark compares arnio's
read_csv against a pandas baseline on large integer/float datasets.

Run::

    python benchmarks/benchmark_numeric_parse.py

Optional flags::

    --rows   N   Number of rows per column (default: 500_000)
    --runs   N   Repetitions per engine (default: 5)
"""

from __future__ import annotations

import argparse
import csv
import os
import tempfile
import time
import tracemalloc
from pathlib import Path

import numpy as np
import pandas as pd

import arnio as ar

DRY_RUN = os.getenv("ARNIO_BENCHMARK_DRY_RUN") == "1"


def _write_csv(path: Path, n_rows: int) -> None:
    """Write a CSV with int and float columns (no nulls for simplicity)."""
    rng = np.random.default_rng(42)
    ints = rng.integers(-10_000, 10_000, size=n_rows).tolist()
    floats_series = rng.uniform(-1e6, 1e6, size=n_rows).tolist()

    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["int_col", "float_col"])
        for i, f_ in zip(ints, floats_series):
            writer.writerow([str(i), str(f_)])


def _bench_arnio(path: str) -> tuple[float, float]:
    """Time arnio CSV read."""
    tracemalloc.start()
    t0 = time.perf_counter()
    _ = ar.read_csv(path)
    elapsed = time.perf_counter() - t0
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return elapsed, peak / 1024 / 1024


def _bench_pandas(path: str) -> tuple[float, float]:
    """Time pandas CSV read."""
    tracemalloc.start()
    t0 = time.perf_counter()
    _ = pd.read_csv(path)
    elapsed = time.perf_counter() - t0
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return elapsed, peak / 1024 / 1024


def run(n_rows: int = 500_000, runs: int = 5) -> None:
    if DRY_RUN:
        runs = 1

    print(f"Generating {n_rows:,} rows x 2 columns numeric CSV ...")
    with tempfile.TemporaryDirectory() as tmp:
        csv_path = Path(tmp) / "numeric.csv"
        _write_csv(csv_path, n_rows)
        path_str = str(csv_path)

        arn_times: list[float] = []
        arn_peaks: list[float] = []
        pd_times: list[float] = []
        pd_peaks: list[float] = []

        for i in range(runs):
            at, ap = _bench_arnio(path_str)
            pt, pp = _bench_pandas(path_str)
            arn_times.append(at)
            arn_peaks.append(ap)
            pd_times.append(pt)
            pd_peaks.append(pp)
            print(
                f"  run {i + 1}/{runs}  arnio={at * 1000:.1f} ms  "
                f"pandas={pt * 1000:.1f} ms"
            )

        avg_arn = sum(arn_times) / runs
        avg_pd = sum(pd_times) / runs
        avg_arn_peak = sum(arn_peaks) / runs
        avg_pd_peak = sum(pd_peaks) / runs
        speedup = avg_pd / avg_arn if avg_arn > 0 else float("inf")
        mem_reduction = (
            (1 - avg_arn_peak / avg_pd_peak) * 100 if avg_pd_peak > 0 else 0.0
        )

        print()
        print(f"{'':=<55}")
        print(f"  Rows:              {n_rows:>12,}")
        print(f"  Runs:              {runs:>12}")
        print(f"{'':=<55}")
        print(f"  {'Engine':<20} {'Avg time':>12}  {'Peak heap':>12}")
        print(f"  {'-'*20} {'-'*12}  {'-'*12}")
        print(f"  {'arnio':<20} {avg_arn * 1000:>10.1f} ms  {avg_arn_peak:>10.1f} MB")
        print(f"  {'pandas':<20} {avg_pd * 1000:>10.1f} ms  {avg_pd_peak:>10.1f} MB")
        print(f"{'':=<55}")
        print(f"  Speedup vs pandas: {speedup:>10.2f}x")
        print(f"  Heap reduction:    {mem_reduction:>10.1f} %")
        print(f"{'':=<55}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Benchmark arnio numeric CSV parse vs pandas"
    )
    parser.add_argument("--rows", type=int, default=500_000, help="Number of rows")
    parser.add_argument("--runs", type=int, default=5, help="Repetitions per engine")
    args = parser.parse_args()
    run(n_rows=args.rows, runs=args.runs)
