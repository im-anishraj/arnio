"""
Reproducible Benchmark: strip_whitespace string allocation behavior.
Run from repo root: python benchmarks/benchmark_strip_whitespace.py
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


def benchmark_strip_whitespace(frame):
    tracemalloc.start()
    t0 = time.perf_counter()

    ar.strip_whitespace(frame)

    elapsed = time.perf_counter() - t0
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return elapsed, peak / 1024 / 1024


if __name__ == "__main__":
    generate(rows=ROWS, path="benchmarks/benchmark_strip_whitespace.csv")
    frame = ar.read_csv("benchmarks/benchmark_strip_whitespace.csv")

    times, rams = [], []
    for _ in range(RUNS):
        t, r = benchmark_strip_whitespace(frame)
        times.append(t)
        rams.append(r)

    def avg(x):
        return sum(x) / len(x)

    print(f"strip_whitespace - {ROWS:,} rows, {RUNS} runs")
    print(f"{'Metric':<20} {'avg':>12}")
    print("-" * 34)
    print(f"{'Exec Time':<20} {avg(times):>11.4f}s")
    print(f"{'Peak RAM':<20} {avg(rams):>10.2f}MB")
