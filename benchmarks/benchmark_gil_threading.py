"""
GIL release benchmark: single-threaded vs multi-threaded performance.
Demonstrates that GIL is released during long C++ operations.

Run: python benchmarks/benchmark_gil_threading.py
"""

import os
import threading
import time
from pathlib import Path

import arnio as ar

CSV_FILE = "benchmarks/benchmark_1m.csv"
DRY_RUN = os.getenv("ARNIO_BENCHMARK_DRY_RUN") == "1"
FALLBACK_ROWS = 10 if DRY_RUN else 500_000


def ensure_or_generate(path, tmp_path):
    if Path(path).exists() and not DRY_RUN:
        return path
    print(f"[info] {path} not found, generating {FALLBACK_ROWS} rows...")
    lines = ["id,name,value,category"]
    for i in range(FALLBACK_ROWS):
        lines.append(f"{i},  name_{i}  ,{i * 1.5},cat_{i % 10}")
    Path(tmp_path).write_text("\n".join(lines))
    return tmp_path


def run_single_threaded(path, n=4):
    """Run n read+clean ops sequentially."""
    t0 = time.perf_counter()
    for _ in range(n):
        frame = ar.read_csv(path)
        ar.drop_nulls(frame)
        ar.drop_duplicates(frame)
        ar.strip_whitespace(frame)
    return time.perf_counter() - t0


def run_multi_threaded(path, n=4):
    """Run n read+clean ops concurrently across threads."""

    def task():
        frame = ar.read_csv(path)
        ar.drop_nulls(frame)
        ar.drop_duplicates(frame)
        ar.strip_whitespace(frame)

    t0 = time.perf_counter()
    threads = [threading.Thread(target=task) for _ in range(n)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    return time.perf_counter() - t0


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="GIL release benchmark: single-threaded vs multi-threaded CSV performance."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Use a tiny dataset (equivalent to ARNIO_BENCHMARK_DRY_RUN=1).",
    )
    args = parser.parse_args()
    if args.dry_run:
        os.environ["ARNIO_BENCHMARK_DRY_RUN"] = "1"
        DRY_RUN = True
        FALLBACK_ROWS = 10

    path = ensure_or_generate(CSV_FILE, "benchmarks/benchmark_gil_temp.csv")
    N = 4
    print(f"\nGIL Release Threading Benchmark ({N} concurrent operations)")
    print("=" * 52)
    single = run_single_threaded(path, N)
    print(f"Single-threaded ({N} sequential ops): {single:.2f}s")
    multi = run_multi_threaded(path, N)
    print(f"Multi-threaded  ({N} concurrent ops): {multi:.2f}s")
    speedup = single / multi
    print(f"\nSpeedup: {speedup:.2f}x")
    if speedup > 1.3:
        print("GIL is being released correctly (concurrent ops faster than sequential)")
    else:
        print("Note: Speedup may vary based on system load and CSV size")
