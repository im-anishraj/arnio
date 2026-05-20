"""
Benchmark: hash_pandas_object vs df.duplicated() for duplicate counting
========================================================================
Compares two approaches for counting duplicate rows inside profile():

  * **baseline** — df.duplicated().sum()  (current default in profile())
  * **candidate** — pd.util.hash_pandas_object + Series.duplicated()

Context (perf/#662):
  The candidate path was proposed as a faster alternative.  Local benchmarks
  showed ~1.5x speedup at 500k rows, but CI results were inconsistent
  (0.72x–1.58x across Python versions and OS configurations).  The hot-path
  change was therefore reverted; profile() continues to use df.duplicated().

  Run this script manually to measure both approaches on your hardware before
  re-enabling the candidate path.

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
    # Pre-convert once — profile() already has df in hand at this point.
    df = to_pandas(frame)
    print(f"Frame memory: {frame.memory_usage() / 1024 / 1024:.1f} MB\n")

    times_baseline: list[float] = []
    times_candidate: list[float] = []

    for i in range(runs):
        t0 = time.perf_counter()
        _ = int(df.duplicated().sum())
        times_baseline.append(time.perf_counter() - t0)

        t0 = time.perf_counter()
        hashes = pd.util.hash_pandas_object(df, index=False)
        _ = int(hashes.duplicated().sum())
        times_candidate.append(time.perf_counter() - t0)

        print(
            f"  run {i + 1}/{runs}  "
            f"baseline={times_baseline[-1] * 1000:.1f} ms  "
            f"candidate={times_candidate[-1] * 1000:.1f} ms"
        )

    avg_b = sum(times_baseline) / runs
    avg_c = sum(times_candidate) / runs
    speedup = avg_b / avg_c if avg_c > 0 else float("inf")

    print()
    print(f"{'':=<65}")
    print(f"  Rows:  {n_rows:>12,}")
    print(f"  Runs:  {runs:>12}")
    print(f"{'':=<65}")
    print(f"  {'Approach':<35} {'Avg time':>12}")
    print(f"  {'-'*35} {'-'*12}")
    print(f"  {'df.duplicated().sum()  [current]':<35} {avg_b * 1000:>10.1f} ms")
    print(f"  {'hash_pandas_object     [candidate]':<35} {avg_c * 1000:>10.1f} ms")
    print(f"{'':=<65}")
    print(
        f"  Speedup: {speedup:.2f}x  {'(+) candidate faster' if speedup > 1 else '(-) baseline faster'}"
    )
    print(f"{'':=<65}")

    # Verify correctness
    baseline_count = int(df.duplicated().sum())
    candidate_count = int(
        pd.util.hash_pandas_object(df, index=False).duplicated().sum()
    )
    match = "✓" if baseline_count == candidate_count else "✗ MISMATCH"
    print(f"\n  duplicate_rows = {baseline_count}  {match}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Benchmark hash_pandas_object vs df.duplicated() for duplicate counting"
    )
    parser.add_argument("--rows", type=int, default=500_000, help="Number of rows")
    parser.add_argument("--runs", type=int, default=5, help="Repetitions per approach")
    args = parser.parse_args()
    run(n_rows=args.rows, runs=args.runs)
