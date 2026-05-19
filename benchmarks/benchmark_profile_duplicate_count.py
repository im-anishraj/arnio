"""
Benchmark: hash_pandas_object vs df.duplicated() for duplicate counting
========================================================================
Measures the wall-clock time for counting duplicate rows inside profile()
using two approaches:

  * **current (baseline)** — df.duplicated().sum()
  * **proposed (new)**     — pd.util.hash_pandas_object + Series.duplicated()

This script documents the performance win from perf/#662.  It is NOT run
as part of the test suite because wall-clock comparisons are too noisy on
shared CI runners.

Run::

    python benchmarks/benchmark_profile_duplicate_count.py

Optional flags::

    --rows   N   Number of rows (default: 500_000)
    --runs   N   Repetitions per approach (default: 5)
"""

from __future__ import annotations

import argparse
import time

import numpy as np
import pandas as pd

import arnio as ar
from arnio.convert import to_pandas


def _make_frame(n_rows: int) -> ar.ArFrame:
    """Return an ArFrame with ~10% duplicate rows and mixed dtypes."""
    rng = np.random.default_rng(42)
    df = pd.DataFrame(
        {
            "int_col": rng.integers(0, int(n_rows * 0.9), size=n_rows).tolist(),
            "float_col": rng.uniform(0, 1000, size=n_rows).tolist(),
            "str_col": [f"s{i % int(n_rows * 0.1)}" for i in range(n_rows)],
        }
    )
    return ar.from_pandas(df)


def run(n_rows: int = 500_000, runs: int = 5) -> None:
    print(f"Building frame: {n_rows:,} rows × 3 columns (~10% duplicates) …")
    frame = _make_frame(n_rows)
    # Pre-convert once — profile() already has df in hand at this point
    df = to_pandas(frame)
    print(f"Frame memory: {frame.memory_usage() / 1024 / 1024:.1f} MB\n")

    times_baseline: list[float] = []
    times_new: list[float] = []

    for i in range(runs):
        t0 = time.perf_counter()
        _ = int(df.duplicated().sum())
        times_baseline.append(time.perf_counter() - t0)

        t0 = time.perf_counter()
        hashes = pd.util.hash_pandas_object(df, index=False)
        _ = int(hashes.duplicated().sum())
        times_new.append(time.perf_counter() - t0)

        print(
            f"  run {i + 1}/{runs}  "
            f"baseline={times_baseline[-1] * 1000:.1f} ms  "
            f"new={times_new[-1] * 1000:.1f} ms"
        )

    avg_b = sum(times_baseline) / runs
    avg_n = sum(times_new) / runs
    speedup = avg_b / avg_n if avg_n > 0 else float("inf")

    print()
    print(f"{'':=<60}")
    print(f"  Rows:  {n_rows:>12,}")
    print(f"  Runs:  {runs:>12}")
    print(f"{'':=<60}")
    print(f"  {'Approach':<30} {'Avg time':>12}")
    print(f"  {'-'*30} {'-'*12}")
    print(f"  {'df.duplicated().sum()':<30} {avg_b * 1000:>10.1f} ms")
    print(f"  {'hash_pandas_object path':<30} {avg_n * 1000:>10.1f} ms")
    print(f"{'':=<60}")
    print(f"  Speedup: {speedup:.2f}x")
    print(f"{'':=<60}")

    # Verify correctness
    baseline_count = int(df.duplicated().sum())
    new_count = int(pd.util.hash_pandas_object(df, index=False).duplicated().sum())
    assert (
        baseline_count == new_count
    ), f"Mismatch: baseline={baseline_count}, new={new_count}"
    print(f"\n  duplicate_rows = {new_count}  ✓ matches pandas baseline")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Benchmark hash_pandas_object vs df.duplicated() for duplicate counting"
    )
    parser.add_argument("--rows", type=int, default=500_000, help="Number of rows")
    parser.add_argument("--runs", type=int, default=5, help="Repetitions per approach")
    args = parser.parse_args()
    run(n_rows=args.rows, runs=args.runs)
