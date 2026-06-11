"""
Microbenchmark for std::string_view overhead reduction.

This benchmark measures the performance improvement from using std::string_view
for read-only string parameters instead of const std::string& in the C++ cleaning module.

Instead of looping Python calls, this benchmark creates a large dataset (500,000 rows)
and measures a single execution, which properly stresses the C++ optimizations rather
than the Pybind11 boundary overhead.
"""

import time

import arnio


def benchmark_strip_whitespace():
    """Benchmark strip_whitespace function with a large dataset."""
    # Generate 500,000 rows of data with leading/trailing whitespace
    data = ["  hello world  "] * 500_000
    frame = arnio.from_dict({"col1": data})

    # Warmup run (without timing) to avoid JIT compilation overhead
    _ = arnio.strip_whitespace(frame)

    # Single execution measured with perf_counter
    start = time.perf_counter()
    _ = arnio.strip_whitespace(frame)
    end = time.perf_counter()

    elapsed = end - start
    return elapsed


def benchmark_normalize_case():
    """Benchmark normalize_case function with a large dataset."""
    # Generate 500,000 rows of data with mixed casing
    data = ["Hello World"] * 500_000
    frame = arnio.from_dict({"col1": data})

    # Warmup run (without timing)
    _ = arnio.normalize_case(frame)

    # Single execution measured with perf_counter
    start = time.perf_counter()
    result = arnio.normalize_case(frame)
    end = time.perf_counter()

    elapsed = end - start
    return elapsed


if __name__ == "__main__":
    print("=" * 60)
    print("std::string_view Overhead Microbenchmark")
    print("=" * 60)

    print("\nBenchmarking strip_whitespace (500,000 rows, single execution)...")
    strip_time = benchmark_strip_whitespace()
    print(f"  Total time: {strip_time:.4f} seconds")

    print("\nBenchmarking normalize_case (500,000 rows, single execution)...")
    normalize_time = benchmark_normalize_case()
    print(f"  Total time: {normalize_time:.4f} seconds")

    print("\n" + "=" * 60)
    print(f"Combined total time: {strip_time + normalize_time:.4f} seconds")
    print("=" * 60)
