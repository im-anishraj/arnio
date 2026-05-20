"""
Benchmark: sparse-null workloads
=================================
Measures wall-clock time and peak heap for null-related operations at
varying null densities from sparse (0.1 %) to dense (20 %).

Each density generates a fresh deterministic CSV, then benchmarks four
operations in both arnio (C++ native where available) and pandas:

  * read_csv              — CSV parsing with null values in the input
  * drop_nulls            — remove rows containing any null
  * fill_nulls            — replace nulls with a scalar value
  * keep_rows_with_nulls  — keep only rows that contain nulls

Run::

    python benchmarks/benchmark_sparse_nulls.py

Optional flags::

    --rows   N   Number of rows (default: 1_000_000)
    --runs   N   Repetitions per density/operation (default: 5)
"""

from __future__ import annotations

import argparse
import os
import time
import tracemalloc
from pathlib import Path

import numpy as np
import pandas as pd

import arnio as ar

from generate_data import generate_sparse_nulls

# Five densities spanning sparse → dense
NULL_DENSITIES = [0.001, 0.005, 0.01, 0.05, 0.2]
DENSITY_LABELS = {
    0.001: "0.1 %",
    0.005: "0.5 %",
    0.01: "1 %",
    0.05: "5 %",
    0.2: "20 %",
}

TMP_DIR = Path("benchmarks")
FILL_VALUE = 0


# ---------------------------------------------------------------------------
# Benchmark helpers  (each returns (elapsed_seconds, peak_mib))
# ---------------------------------------------------------------------------


def _read_csv_arnio(path: str) -> tuple[float, float]:
    tracemalloc.start()
    t0 = time.perf_counter()
    _ = ar.read_csv(path)
    elapsed = time.perf_counter() - t0
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return elapsed, peak / 1024 / 1024


def _read_csv_pandas(path: str) -> tuple[float, float]:
    tracemalloc.start()
    t0 = time.perf_counter()
    _ = pd.read_csv(path)
    elapsed = time.perf_counter() - t0
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return elapsed, peak / 1024 / 1024


def _drop_nulls_arnio(path: str) -> tuple[float, float]:
    frame = ar.read_csv(path)
    tracemalloc.start()
    t0 = time.perf_counter()
    _ = ar.drop_nulls(frame)
    elapsed = time.perf_counter() - t0
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return elapsed, peak / 1024 / 1024


def _drop_nulls_pandas(path: str) -> tuple[float, float]:
    df = pd.read_csv(path)
    tracemalloc.start()
    t0 = time.perf_counter()
    _ = df.dropna()
    elapsed = time.perf_counter() - t0
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return elapsed, peak / 1024 / 1024


def _fill_nulls_arnio(path: str) -> tuple[float, float]:
    frame = ar.read_csv(path)
    tracemalloc.start()
    t0 = time.perf_counter()
    _ = ar.fill_nulls(frame, FILL_VALUE)
    elapsed = time.perf_counter() - t0
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return elapsed, peak / 1024 / 1024


def _fill_nulls_pandas(path: str) -> tuple[float, float]:
    df = pd.read_csv(path)
    tracemalloc.start()
    t0 = time.perf_counter()
    _ = df.fillna(FILL_VALUE)
    elapsed = time.perf_counter() - t0
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return elapsed, peak / 1024 / 1024


def _keep_nulls_arnio(path: str) -> tuple[float, float]:
    frame = ar.read_csv(path)
    tracemalloc.start()
    t0 = time.perf_counter()
    _ = ar.keep_rows_with_nulls(frame)
    elapsed = time.perf_counter() - t0
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return elapsed, peak / 1024 / 1024


def _keep_nulls_pandas(path: str) -> tuple[float, float]:
    df = pd.read_csv(path)
    tracemalloc.start()
    t0 = time.perf_counter()
    _ = df[df.isnull().any(axis=1)]
    elapsed = time.perf_counter() - t0
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return elapsed, peak / 1024 / 1024


# ---------------------------------------------------------------------------
# Per-operation runner
# ---------------------------------------------------------------------------


def _bench_op(
    arnio_fn, pandas_fn, path: str, runs: int
) -> tuple[list[float], list[float], list[float], list[float]]:
    ar_times: list[float] = []
    ar_peaks: list[float] = []
    pd_times: list[float] = []
    pd_peaks: list[float] = []
    for _ in range(runs):
        t, p = arnio_fn(path)
        ar_times.append(t)
        ar_peaks.append(p)
        t, p = pandas_fn(path)
        pd_times.append(t)
        pd_peaks.append(p)
    return ar_times, ar_peaks, pd_times, pd_peaks


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def run(rows: int = 1_000_000, runs: int = 5) -> None:
    print(f"Sparse-null benchmark: {rows:,} rows, {runs} run(s) per density")
    print()

    ops = [
        ("read_csv", _read_csv_arnio, _read_csv_pandas),
        ("drop_nulls", _drop_nulls_arnio, _drop_nulls_pandas),
        ("fill_nulls", _fill_nulls_arnio, _fill_nulls_pandas),
        ("keep_rows_with_nulls", _keep_nulls_arnio, _keep_nulls_pandas),
    ]
    speedup_col = 6 + max(len(op[0]) for op in ops) + 14 + 12
    header = (
        f"  {'Operation':<{max(len(op[0]) for op in ops)}}"
        f"  {'Density':>7}"
        f"  {'arnio (ms)':>10}"
        f"  {'pandas (ms)':>11}"
        f"  {'speedup':>8}"
        f"  {'arnio MB':>9}"
        f"  {'pandas MB':>10}"
    )
    sep = "  " + "-" * (len(header) - 2)

    for density in NULL_DENSITIES:
        path = str(TMP_DIR / f"benchmark_sparse_nulls_{density}.csv")
        generate_sparse_nulls(rows=rows, path=path, null_density=density)

        label = DENSITY_LABELS.get(density, f"{density:.1%}")
        print(f"  ── null density = {label} ──")
        print(header)
        print(sep)

        for op_name, arnio_fn, pandas_fn in ops:
            ar_t, ar_p, pd_t, pd_p = _bench_op(arnio_fn, pandas_fn, path, runs)
            avg_ar = sum(ar_t) / runs
            avg_pd = sum(pd_t) / runs
            avg_ar_mem = sum(ar_p) / runs
            avg_pd_mem = sum(pd_p) / runs

            if avg_ar > 0:
                speedup = avg_pd / avg_ar
                sp_str = f"{speedup:.1f}x"
            else:
                sp_str = "—"

            print(
                f"  {op_name:<{max(len(op[0]) for op in ops)}}"
                f"  {label:>7}"
                f"  {avg_ar * 1000:>10.1f}"
                f"  {avg_pd * 1000:>11.1f}"
                f"  {sp_str:>8}"
                f"  {avg_ar_mem:>9.1f}"
                f"  {avg_pd_mem:>10.1f}"
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
