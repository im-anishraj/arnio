"""
Reproducible Benchmark: combine_columns performance.
Run from repo root: python benchmarks/benchmark_combine_columns.py
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

import time
import tracemalloc

from generate_data import generate

import arnio as ar

ROWS = 100_000
RUNS = 3


def benchmark_combine_native(frame, subset):
    tracemalloc.start()
    t0 = time.perf_counter()

    ar.combine_columns(frame, subset=subset, separator="-", output_column="combined")

    elapsed = time.perf_counter() - t0
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return elapsed, peak / 1024 / 1024


def benchmark_combine_pandas(df, subset):
    tracemalloc.start()
    t0 = time.perf_counter()

    import pandas as pd

    ref = df.copy()
    combined = ref[subset].astype("string").fillna("").agg("-".join, axis=1)
    null_mask = ref[subset].isna().all(axis=1)
    combined = combined.mask(null_mask, pd.NA)
    ref["combined"] = combined

    elapsed = time.perf_counter() - t0
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return elapsed, peak / 1024 / 1024


if __name__ == "__main__":
    generate(rows=ROWS, path="benchmarks/benchmark_combine_columns.csv")

    import pandas as pd

    df = pd.read_csv("benchmarks/benchmark_combine_columns.csv")
    frame = ar.from_pandas(df)

    # We will pick a few columns to combine
    subset = ["name", "city", "age"]

    native_times, native_rams = [], []
    for _ in range(RUNS):
        # We catch exceptions just in case it fails during benchmarking
        try:
            t, r = benchmark_combine_native(frame, subset)
            native_times.append(t)
            native_rams.append(r)
        except Exception as e:
            print(f"Native failed: {e}")
            sys.exit(1)

    pandas_times, pandas_rams = [], []
    for _ in range(RUNS):
        t, r = benchmark_combine_pandas(df, subset)
        pandas_times.append(t)
        pandas_rams.append(r)

    def avg(x):
        return sum(x) / len(x) if x else float("inf")

    print(f"combine_columns - {ROWS:,} rows, {RUNS} runs, {len(subset)} columns")
    print(f"{'Metric':<20} {'native':>12} {'pandas':>12}")
    print("-" * 46)
    print(f"{'Exec Time':<20} {avg(native_times):>11.4f}s {avg(pandas_times):>11.4f}s")
    print(f"{'Peak RAM':<20} {avg(native_rams):>10.2f}MB {avg(pandas_rams):>10.2f}MB")
    print(f"Speedup: {avg(pandas_times) / avg(native_times):.1f}x")
