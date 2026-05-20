"""
Benchmark: sparse-null workloads
=================================
Measures wall-clock time for null-related operations at varying null
densities from sparse (0.1 %) to dense (20 %).

Each density generates a fresh deterministic CSV, pre-loads data once,
then benchmarks four operations in both arnio and pandas:

  * read_csv              - CSV parsing with null values in the input
  * drop_nulls            - remove rows containing any null
  * fill_nulls            - replace nulls with a scalar value
  * keep_rows_with_nulls  - keep only rows that contain nulls

Note on memory
--------------
Peak Python heap (tracemalloc) is reported only for read_csv, where it
is meaningful.  For drop_nulls, fill_nulls, and keep_rows_with_nulls,
only wall-clock time is shown because tracemalloc does not capture
Arnio's native C++ allocations, and per-operation RSS is too noisy.

Run::

    python benchmarks/benchmark_sparse_nulls.py

Optional flags::

    --rows   N   Number of rows (default: 1_000_000)
    --runs   N   Repetitions per density/operation (default: 5)
"""

from __future__ import annotations

import argparse
import os
import sys
import time
import tracemalloc
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

import pandas as pd

import arnio as ar

from generate_data import generate_sparse_nulls

# Five densities spanning sparse -> dense
NULL_DENSITIES = [0.001, 0.005, 0.01, 0.05, 0.2]
DENSITY_LABELS = {
    0.001: "0.1 %",
    0.005: "0.5 %",
    0.01: "1 %",
    0.05: "5 %",
    0.2: "20 %",
}

DRY_RUN = os.getenv("ARNIO_BENCHMARK_DRY_RUN") == "1"
TMP_DIR = Path("benchmarks")
FILL_VALUE = 0

_OPS = ["read_csv", "drop_nulls", "fill_nulls", "keep_rows_with_nulls"]
OP_WIDTH = max(len(op) for op in _OPS)


# ---------------------------------------------------------------------------
# Timing helpers  (return elapsed seconds)
# ---------------------------------------------------------------------------


def _time(fn, *args):
    t0 = time.perf_counter()
    fn(*args)
    return time.perf_counter() - t0


# ---------------------------------------------------------------------------
# read_csv:  path-based (the read IS the operation)
# ---------------------------------------------------------------------------


def _read_csv_arnio(path: str) -> tuple[float, float]:
    tracemalloc.start()
    t0 = time.perf_counter()
    ar.read_csv(path)
    elapsed = time.perf_counter() - t0
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return elapsed, peak / 1024 / 1024


def _read_csv_pandas(path: str) -> tuple[float, float]:
    tracemalloc.start()
    t0 = time.perf_counter()
    pd.read_csv(path)
    elapsed = time.perf_counter() - t0
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return elapsed, peak / 1024 / 1024


# ---------------------------------------------------------------------------
# drop_nulls, fill_nulls, keep_rows_with_nulls:  data-based (pre-loaded)
#   Only wall-clock time - tracemalloc cannot capture Arnio C++
#   allocations so memory columns are omitted for these operations.
# ---------------------------------------------------------------------------


def _drop_nulls_arnio(frame):
    ar.drop_nulls(frame)


def _drop_nulls_pandas(df):
    df.dropna()


def _fill_nulls_arnio(frame):
    ar.fill_nulls(frame, FILL_VALUE)


def _fill_nulls_pandas(df):
    df.fillna(FILL_VALUE)


def _keep_nulls_arnio(frame):
    ar.keep_rows_with_nulls(frame)


def _keep_nulls_pandas(df):
    df[df.isnull().any(axis=1)]


# ---------------------------------------------------------------------------
# Per-operation runner
# ---------------------------------------------------------------------------


def _bench_read_csv(path: str, runs: int):
    """Benchmark read_csv with tracemalloc (Python heap only)."""
    ar_times: list[float] = []
    ar_peaks: list[float] = []
    pd_times: list[float] = []
    pd_peaks: list[float] = []
    for _ in range(runs):
        t, p = _read_csv_arnio(path)
        ar_times.append(t)
        ar_peaks.append(p)
        t, p = _read_csv_pandas(path)
        pd_times.append(t)
        pd_peaks.append(p)
    return ar_times, ar_peaks, pd_times, pd_peaks


def _bench_data(arnio_fn, pandas_fn, frame, df, runs: int):
    """Benchmark a data-based operation (pre-loaded frame/df, time only)."""
    ar_times: list[float] = []
    pd_times: list[float] = []
    for _ in range(runs):
        ar_times.append(_time(arnio_fn, frame))
        pd_times.append(_time(pandas_fn, df))
    return ar_times, pd_times


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def run(rows: int = 1_000_000, runs: int = 5) -> None:
    if DRY_RUN:
        rows = min(rows, 10)
        runs = min(runs, 1)
    print(f"Sparse-null benchmark: {rows:,} rows, {runs} run(s) per density")
    print()

    header_lines = [
        f"  {'Operation':<{OP_WIDTH}}  {'Density':>7}"
        f"  {'arnio (ms)':>10}  {'pandas (ms)':>11}  {'speedup':>8}",
        f"  {'':<{OP_WIDTH}}  {'':>7}"
        f"  {'PyHeap MB':>10}  {'PyHeap MB':>11}",
    ]
    sep = "  " + "-" * (len(header_lines[0]) - 2)

    for density in NULL_DENSITIES:
        path = str(TMP_DIR / f"benchmark_sparse_nulls_{density}.csv")
        generate_sparse_nulls(rows=rows, path=path, null_density=density)

        # Pre-load data once for all non-read operations
        frame = ar.read_csv(path) if rows > 0 else ar.read_csv(path)
        df = pd.read_csv(path)

        label = DENSITY_LABELS.get(density, f"{density:.1%}")
        print(f"  -- null density = {label} --")
        for hl in header_lines:
            print(hl)
        print(sep)

        # read_csv (path-based, includes Python heap)
        ar_t, ar_p, pd_t, pd_p = _bench_read_csv(path, runs)
        avg_ar = sum(ar_t) / runs
        avg_pd = sum(pd_t) / runs
        avg_ar_mem = sum(ar_p) / runs
        avg_pd_mem = sum(pd_p) / runs
        sp_str = f"{avg_pd / avg_ar:.1f}x" if avg_ar > 0 else "-"
        print(
            f"  {'read_csv':<{OP_WIDTH}}  {label:>7}"
            f"  {avg_ar * 1000:>10.1f}  {avg_pd * 1000:>11.1f}  {sp_str:>8}"
            f"  {avg_ar_mem:>9.1f}  {avg_pd_mem:>10.1f}"
        )

        # drop_nulls (data-based, time only)
        ar_t, pd_t = _bench_data(
            _drop_nulls_arnio, _drop_nulls_pandas, frame, df, runs
        )
        avg_ar = sum(ar_t) / runs
        avg_pd = sum(pd_t) / runs
        sp_str = f"{avg_pd / avg_ar:.1f}x" if avg_ar > 0 else "-"
        print(
            f"  {'drop_nulls':<{OP_WIDTH}}  {label:>7}"
            f"  {avg_ar * 1000:>10.1f}  {avg_pd * 1000:>11.1f}  {sp_str:>8}"
            f"  {'-':>9}  {'-':>10}"
        )

        # fill_nulls (data-based, time only)
        ar_t, pd_t = _bench_data(
            _fill_nulls_arnio, _fill_nulls_pandas, frame, df, runs
        )
        avg_ar = sum(ar_t) / runs
        avg_pd = sum(pd_t) / runs
        sp_str = f"{avg_pd / avg_ar:.1f}x" if avg_ar > 0 else "-"
        print(
            f"  {'fill_nulls':<{OP_WIDTH}}  {label:>7}"
            f"  {avg_ar * 1000:>10.1f}  {avg_pd * 1000:>11.1f}  {sp_str:>8}"
            f"  {'-':>9}  {'-':>10}"
        )

        # keep_rows_with_nulls (data-based, time only)
        ar_t, pd_t = _bench_data(
            _keep_nulls_arnio, _keep_nulls_pandas, frame, df, runs
        )
        avg_ar = sum(ar_t) / runs
        avg_pd = sum(pd_t) / runs
        sp_str = f"{avg_pd / avg_ar:.1f}x" if avg_ar > 0 else "-"
        print(
            f"  {'keep_rows_with_nulls':<{OP_WIDTH}}  {label:>7}"
            f"  {avg_ar * 1000:>10.1f}  {avg_pd * 1000:>11.1f}  {sp_str:>8}"
            f"  {'-':>9}  {'-':>10}"
        )

        print()
        os.remove(path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Benchmark sparse-null workloads: arnio vs pandas"
    )
    parser.add_argument("--rows", type=int, default=1_000_000, help="Number of rows")
    parser.add_argument("--runs", type=int, default=5, help="Repetitions per density")
    args = parser.parse_args()
    run(rows=args.rows, runs=args.runs)
