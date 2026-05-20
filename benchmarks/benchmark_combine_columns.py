"""
Reproducible Benchmark: combine_columns performance.
Run from repo root: python benchmarks/benchmark_combine_columns.py
"""

import os
import time
import tracemalloc

import arnio as ar

DRY_RUN = os.getenv("ARNIO_BENCHMARK_DRY_RUN") == "1"
ROWS = 10 if DRY_RUN else 100_000
RUNS = 1 if DRY_RUN else 3


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
    import numpy as np
    import pandas as pd

    print(f"Generating synthetic dataset with {ROWS:,} rows...")
    rng = np.random.default_rng(42)
    df = pd.DataFrame(
        {
            "name": [f"Name_{i}" for i in rng.integers(0, 1000, size=ROWS)],
            "city": [f"City_{i}" for i in rng.integers(0, 100, size=ROWS)],
            "age": rng.integers(18, 90, size=ROWS).astype(str),
            "score": rng.random(size=ROWS).astype(str),
        }
    )

    # Introduce some nulls to make it realistic
    for col in df.columns:
        null_indices = rng.choice(ROWS, size=ROWS // 20, replace=False)
        df.loc[null_indices, col] = None

    frame = ar.from_pandas(df)
    subset = ["name", "city", "age", "score"]

    native_times, native_rams = [], []
    for _ in range(RUNS):
        t, r = benchmark_combine_native(frame, subset)
        native_times.append(t)
        native_rams.append(r)

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
