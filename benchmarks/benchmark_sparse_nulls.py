"""
Benchmark: sparse-null workloads
=================================
Measures wall-clock time and peak heap for null-related operations
at varying null densities (sparse to dense).

Operations compared:
  - ar.drop_nulls  vs  pandas .dropna()
  - ar.fill_nulls  vs  pandas .fillna()

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
from arnio.convert import from_pandas

from generate_data import generate_sparse_nulls

NULL_DENSITIES = [0.001, 0.005, 0.01, 0.05, 0.2]

TMP_DIR = Path("benchmarks")


def _csv_path(density: float) -> str:
    pct = f"{density:.3f}".replace(".", "_")
    return str(TMP_DIR / f"benchmark_sparse_nulls_{pct}.csv")


def _bench_drop_nulls_arnio(path: str) -> tuple[float, float]:
    frame = ar.read_csv(path)
    tracemalloc.start()
    t0 = time.perf_counter()
    _ = ar.drop_nulls(frame)
    elapsed = time.perf_counter() - t0
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return elapsed, peak / 1024 / 1024


def _bench_drop_nulls_pandas(path: str) -> tuple[float, float]:
    df = pd.read_csv(path)
    tracemalloc.start()
    t0 = time.perf_counter()
    _ = df.dropna()
    elapsed = time.perf_counter() - t0
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return elapsed, peak / 1024 / 1024


def _bench_fill_nulls_arnio(path: str) -> tuple[float, float]:
    frame = ar.read_csv(path)
    tracemalloc.start()
    t0 = time.perf_counter()
    _ = ar.fill_nulls(frame, 0)
    elapsed = time.perf_counter() - t0
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return elapsed, peak / 1024 / 1024


def _bench_fill_nulls_pandas(path: str) -> tuple[float, float]:
    df = pd.read_csv(path)
    tracemalloc.start()
    t0 = time.perf_counter()
    _ = df.fillna(0)
    elapsed = time.perf_counter() - t0
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return elapsed, peak / 1024 / 1024


def run(rows: int = 1_000_000, runs: int = 5) -> None:
    print(f"Sparse-null benchmark: {rows:,} rows, {runs} run(s) per density\n")

    for density in NULL_DENSITIES:
        path = _csv_path(density)
        generate_sparse_nulls(rows=rows, path=path, null_density=density)

        arnios_dn: list[float] = []
        pandas_dn: list[float] = []
        arnios_fn: list[float] = []
        pandas_fn: list[float] = []

        for _ in range(runs):
            t, _ = _bench_drop_nulls_arnio(path)
            arnios_dn.append(t)
            t, _ = _bench_drop_nulls_pandas(path)
            pandas_dn.append(t)
            t, _ = _bench_fill_nulls_arnio(path)
            arnios_fn.append(t)
            t, _ = _bench_fill_nulls_pandas(path)
            pandas_fn.append(t)

        avg_arnio_dn = sum(arnios_dn) / runs
        avg_pandas_dn = sum(pandas_dn) / runs
        avg_arnio_fn = sum(arnios_fn) / runs
        avg_pandas_fn = sum(pandas_fn) / runs

        print(f"  Null density: {density:.1%}")
        print(f"    drop_nulls:  arnio={avg_arnio_dn * 1000:.1f} ms  "
              f"pandas={avg_pandas_dn * 1000:.1f} ms  "
              f"({avg_pandas_dn / avg_arnio_dn:.1f}x)")
        print(f"    fill_nulls:  arnio={avg_arnio_fn * 1000:.1f} ms  "
              f"pandas={avg_pandas_fn * 1000:.1f} ms  "
              f"({avg_pandas_fn / avg_arnio_fn:.1f}x)")
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
