import sys
import time
import tracemalloc

import numpy as np
import pandas as pd

# Safe import guard for hybrid C++ binary extensions
try:
    import arnio as ar

    HAS_ARNIO_CPP = True
except (ImportError, ModuleNotFoundError):
    HAS_ARNIO_CPP = False


def generate_mock_data(row_count, dtype_type):
    """Generates deterministic data for benchmarking based on type."""
    np.random.seed(42)
    if dtype_type == "numeric":
        return pd.DataFrame(
            {
                "col_int": np.random.randint(0, 10000, size=row_count),
                "col_float": np.random.randn(row_count),
            }
        )
    elif dtype_type == "bool":
        return pd.DataFrame(
            {
                "col_bool1": np.random.choice([True, False], size=row_count),
                "col_bool2": np.random.choice([True, False], size=row_count),
            }
        )
    elif dtype_type == "string":
        str_pool = ["apple", "banana", "cherry", "date", "elderberry"]
        return pd.DataFrame(
            {
                "col_str1": np.random.choice(str_pool, size=row_count),
                "col_str2": np.random.choice(str_pool, size=row_count),
            }
        )


def profile_conversion_path(row_count, dtype_type):
    df_base = generate_mock_data(row_count, dtype_type)

    # Production path utilizing correct ar.to_pandas(arnio_frame) API
    try:
        arnio_frame = ar.from_pandas(df_base)
    except AttributeError:
        arnio_frame = ar.Frame(df_base)

    tracemalloc.start()
    start_time = time.perf_counter()

    # Corrected to use the global public API instead of the instance method
    res_df = ar.to_pandas(arnio_frame)
    _ = len(res_df)

    end_time = time.perf_counter()
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    runtime_ms = (end_time - start_time) * 1000
    peak_mem_mb = peak / (1024 * 1024)

    return runtime_ms, peak_mem_mb


def run_all_benchmarks():
    # If binary C++ extensions are missing locally, print explicit skip error and exit safely
    if not HAS_ARNIO_CPP:
        print("=" * 70)
        print("ERROR: Cannot execute arnio performance benchmarks.")
        print("REASON: Core C++ binary extensions (_arnio_cpp) are missing locally.")
        print("Please build the repository with 'pip install -e .' before running.")
        print("=" * 70)
        sys.exit(1)

    scales = [10000, 100000, 1000000]  # 10k, 100k, 1M rows
    dtypes = ["numeric", "bool", "string"]

    print("=" * 70)
    print("ARNIO PERFORMANCE BENCHMARK: .to_pandas() CONVERSION OVERHEAD")
    print("=" * 70)
    print(
        f"{'Data Type':<15} | {'Row Count':<12} | {'Time (ms)':<12} | {'Peak Memory (MB)':<15}"
    )
    print("-" * 70)

    for dtype in dtypes:
        for scale in scales:
            try:
                runtime, memory = profile_conversion_path(scale, dtype)
                print(
                    f"{dtype:<15} | {scale:<12,} | {runtime:<12.2f} | {memory:<15.4f}"
                )
            except Exception as e:
                print(f"{dtype:<15} | {scale:<12,} | ERROR: {str(e)}")

    print("=" * 70)


if __name__ == "__main__":
    run_all_benchmarks()
