"""
Benchmark: pipeline clone overhead — unmodified column move optimization
=========================================================================
Measures the wall-clock time and peak Python-heap allocation for a 5-step
cleaning pipeline on a wide frame (2 string cols + 18 numeric cols).

Before the optimization, every cleaning step deep-copied ALL 20 columns
even though only the 2 string columns were modified.  After the fix,
strip_whitespace and normalize_case move unmodified columns in O(1)
instead of O(n).

Run::

    python benchmarks/benchmark_pipeline_clone.py

Optional flags::

    --rows   N   Number of rows (default: 500_000)
    --runs   N   Repetitions (default: 5)
"""

from __future__ import annotations

import argparse
import time
import tracemalloc

import numpy as np
import pandas as pd

import arnio as ar
from arnio.convert import from_pandas

STEPS = [
    ("strip_whitespace",),
    ("normalize_case", {"case_type": "lower"}),
    ("strip_whitespace",),
    ("normalize_case", {"case_type": "upper"}),
    ("strip_whitespace",),
]


def _make_frame(n_rows: int) -> ar.ArFrame:
    """2 string columns + 18 int64 columns = 20 columns total."""
    rng = np.random.default_rng(42)
    df = pd.DataFrame(
        {
            "name": [f"  User_{i}  " for i in range(n_rows)],
            "city": [f"  City_{i % 100}  " for i in range(n_rows)],
            **{
                f"col_{i}": rng.integers(0, 1000, size=n_rows).tolist()
                for i in range(18)
            },
        }
    )
    return from_pandas(df)


def run(n_rows: int = 500_000, runs: int = 5) -> None:
    print(f"Building frame: {n_rows:,} rows × 20 cols (2 string + 18 int64) …")
    frame = _make_frame(n_rows)
    print(f"Frame memory: {frame.memory_usage() / 1024 / 1024:.1f} MB\n")

    times: list[float] = []
    peaks: list[float] = []

    for i in range(runs):
        tracemalloc.start()
        t0 = time.perf_counter()
        ar.pipeline(frame, STEPS)
        elapsed = time.perf_counter() - t0
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        times.append(elapsed)
        peaks.append(peak / 1024 / 1024)
        print(f"  run {i + 1}/{runs}  {elapsed * 1000:.1f} ms  peak={peaks[-1]:.1f} MB")

    avg_t = sum(times) / runs * 1000
    avg_p = sum(peaks) / runs

    print()
    print(f"{'':=<55}")
    print(f"  Rows:   {n_rows:>12,}")
    print(f"  Cols:   {'20 (2 string + 18 int64)':>12}")
    print(f"  Steps:  {len(STEPS):>12}")
    print(f"  Runs:   {runs:>12}")
    print(f"{'':=<55}")
    print(f"  Avg time : {avg_t:>10.1f} ms")
    print(f"  Avg peak : {avg_p:>10.1f} MB")
    print(f"{'':=<55}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Benchmark pipeline clone overhead optimization"
    )
    parser.add_argument("--rows", type=int, default=500_000, help="Number of rows")
    parser.add_argument("--runs", type=int, default=5, help="Repetitions")
    args = parser.parse_args()
    run(n_rows=args.rows, runs=args.runs)
