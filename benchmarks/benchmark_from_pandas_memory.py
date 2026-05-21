import sys
import tracemalloc
import numpy as np
import pandas as pd

try:
    import arnio as ar
    HAS_ARNIO_CPP = True
except (ImportError, ModuleNotFoundError):
    HAS_ARNIO_CPP = False


def generate_large_frame(row_count: int) -> pd.DataFrame:
    np.random.seed(42)
    str_pool = ["alpha", "beta", "gamma", "delta", "epsilon"]
    return pd.DataFrame({
        "col_int":   np.random.randint(0, 10000, size=row_count),
        "col_float": np.random.randn(row_count),
        "col_bool":  np.random.choice([True, False], size=row_count),
        "col_str":   np.random.choice(str_pool, size=row_count),
    })


def measure_from_pandas(row_count: int):
    df =generate_large_frame(row_count)

    tracemalloc.start()
    _ = ar.from_pandas(df)
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    return peak / (1024 * 1024)


def measure_column_hotspot(row_count: int):
    """Measure per-column allocation to identify hotspot."""
    df = generate_large_frame(row_count)
    results = {}

    for col in df.columns:
        single_col_df = df[[col]]
        tracemalloc.start()
        _ = ar.from_pandas(single_col_df)
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        results[col] = peak / (1024 * 1024)

    return results


def run():
    if not HAS_ARNIO_CPP:
        print("Skipping: arnio C++ extension not available.")
        sys.exit(0)

    import os
    scales = [10] if os.getenv("ARNIO_BENCHMARK_DRY_RUN") == "1" else [10_000, 100_000, 1_000_000]

    print("=" * 60)
    print("BENCHMARK: from_pandas() peak memory")
    print("=" * 60)
    print(f"{'Row Count':<15} | {'Peak Memory (MB)':<20}")
    print("-" * 60)

    for scale in scales:
        peak = measure_from_pandas(scale)
        print(f"{scale:<15,} | {peak:<20.4f}")

    print()
    print("=" * 60)
    print("HOTSPOT: per-column peak memory at 100k rows")
    print("=" * 60)
    hotspot = measure_column_hotspot(100_000)
    for col, mb in hotspot.items():
        print(f"  {col:<15}: {mb:.4f} MB")
    print("=" * 60)


if __name__ == "__main__":
    run()