"""
Benchmark: native clip_numeric vs pandas round-trip
====================================================
Measures the wall-clock time and peak Python-heap allocation for clipping
a large numeric frame using:

  * **arnio (native)**  — the C++ hot-path introduced in this PR
  * **pandas baseline** — the old implementation (to_pandas → .clip() → from_pandas)

Run::

    python benchmarks/benchmark_clip_numeric.py

Optional flags::

    --rows   N   Number of rows (default: 1_000_000)
    --runs   N   Repetitions per engine (default: 5)
"""

from __future__ import annotations

import argparse
import time
import tracemalloc

import numpy as np
import pandas as pd

import arnio as ar
from arnio.convert import from_pandas, to_pandas

LOWER = -100.0
UPPER = 100.0


# ---------------------------------------------------------------------------
# Dataset builder
# ---------------------------------------------------------------------------


def _make_frame(n_rows: int) -> ar.ArFrame:
    """Return an ArFrame with two numeric columns and one string column."""
    rng = np.random.default_rng(0)
    df = pd.DataFrame(
        {
            "int_col": rng.integers(-500, 500, size=n_rows).tolist(),
            "float_col": rng.uniform(-500.0, 500.0, size=n_rows).tolist(),
            "label": ["arnio"] * n_rows,
        }
    )
    # Scatter ~1 % nulls into numeric columns
    null_idx = rng.integers(0, n_rows, size=n_rows // 100)
    for idx in null_idx:
        df.at[int(idx), "int_col"] = None
    null_idx2 = rng.integers(0, n_rows, size=n_rows // 100)
    for idx in null_idx2:
        df.at[int(idx), "float_col"] = None
    return from_pandas(df)


# ---------------------------------------------------------------------------
# Benchmark helpers
# ---------------------------------------------------------------------------


def _bench_native(frame: ar.ArFrame) -> tuple[float, float]:
    """Time the native C++ clip_numeric path."""
    tracemalloc.start()
    t0 = time.perf_counter()
    _ = ar.clip_numeric(frame, lower=LOWER, upper=UPPER)
    elapsed = time.perf_counter() - t0
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return elapsed, peak / 1024 / 1024


def _bench_pandas_roundtrip(frame: ar.ArFrame) -> tuple[float, float]:
    """Time the old pandas round-trip path (to_pandas → clip → from_pandas)."""
    tracemalloc.start()
    t0 = time.perf_counter()
    df = to_pandas(frame)
    clipped = df.copy()
    numeric_cols = [
        c
        for c in df.columns
        if pd.api.types.is_numeric_dtype(df[c])
        and not pd.api.types.is_bool_dtype(df[c])
    ]
    clipped[numeric_cols] = clipped[numeric_cols].clip(lower=LOWER, upper=UPPER)
    _ = from_pandas(clipped)
    elapsed = time.perf_counter() - t0
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return elapsed, peak / 1024 / 1024


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def run(n_rows: int = 1_000_000, runs: int = 5) -> None:
    print(f"Building frame: {n_rows:,} rows × 3 columns (2 numeric + 1 string) …")
    frame = _make_frame(n_rows)
    print(f"Frame memory: {frame.memory_usage() / 1024 / 1024:.1f} MB\n")

    native_times: list[float] = []
    native_peaks: list[float] = []
    pandas_times: list[float] = []
    pandas_peaks: list[float] = []

    for i in range(runs):
        nt, np_ = _bench_native(frame)
        pt, pp = _bench_pandas_roundtrip(frame)
        native_times.append(nt)
        native_peaks.append(np_)
        pandas_times.append(pt)
        pandas_peaks.append(pp)
        print(
            f"  run {i + 1}/{runs}  native={nt * 1000:.1f} ms  "
            f"pandas={pt * 1000:.1f} ms"
        )

    avg_native = sum(native_times) / runs
    avg_pandas = sum(pandas_times) / runs
    avg_native_peak = sum(native_peaks) / runs
    avg_pandas_peak = sum(pandas_peaks) / runs
    speedup = avg_pandas / avg_native if avg_native > 0 else float("inf")
    mem_reduction = (
        (1 - avg_native_peak / avg_pandas_peak) * 100 if avg_pandas_peak > 0 else 0.0
    )

    print()
    print(f"{'':=<55}")
    print(f"  Rows:              {n_rows:>12,}")
    print(f"  Runs:              {runs:>12}")
    print(f"{'':=<55}")
    print(f"  {'Engine':<20} {'Avg time':>12}  {'Peak heap':>12}")
    print(f"  {'-'*20} {'-'*12}  {'-'*12}")
    print(
        f"  {'arnio (native)':<20} {avg_native * 1000:>10.1f} ms  {avg_native_peak:>10.1f} MB"
    )
    print(
        f"  {'pandas round-trip':<20} {avg_pandas * 1000:>10.1f} ms  {avg_pandas_peak:>10.1f} MB"
    )
    print(f"{'':=<55}")
    print(f"  Speedup:           {speedup:>11.2f}x")
    print(f"  Heap reduction:    {mem_reduction:>10.1f} %")
    print(f"{'':=<55}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Benchmark native clip_numeric vs pandas"
    )
    parser.add_argument("--rows", type=int, default=1_000_000, help="Number of rows")
    parser.add_argument("--runs", type=int, default=5, help="Repetitions per engine")
    args = parser.parse_args()
    run(n_rows=args.rows, runs=args.runs)
