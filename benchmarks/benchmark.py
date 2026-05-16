"""
Reproducible memory benchmark for arnio.auto_clean
Run: python benchmarks/benchmark.py --rows 100000
"""

import argparse
import math
import os
import time
import tracemalloc
from typing import Any

import numpy as np
import pandas as pd

import arnio as ar


def generate_synthetic_data(*, rows: int, path: str, seed: int) -> None:
    """Generate deterministic synthetic dataset with mixed column types."""
    print(f"Generating {rows:,} rows of synthetic data...")
    rng = np.random.default_rng(seed)
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)

    age = rng.integers(18, 80, rows).astype(object)
    age[rng.random(rows) < 0.1] = None

    salary = rng.uniform(30000, 150000, rows).round(2).astype(object)
    salary[rng.random(rows) < 0.05] = None

    data = {
        "id": rng.integers(1, 1000000, rows),
        "name": rng.choice(
            ["  Ishan", "PRANAY  ", " prasoon", "DHRUV ", " rishit  ", None],
            rows,
        ),
        "age": age,
        "salary": salary,
        "city": rng.choice(["  New York  ", "London", "  PARIS", "tokyo  ", None], rows),
        "active": rng.choice(["True", "False", "TRUE", "FALSE", "yes", "no", None], rows),
        "score": rng.uniform(0, 100, rows).round(2),
        "category": rng.choice([" A ", "B", " C ", "D", None], rows),
        "is_member": rng.choice([1, 0, None], rows),
        "notes": rng.choice(["Needs review", "Valid", "  Pending  ", None], rows),
    }

    df = pd.DataFrame(data)

    if rows > 100:
        duplicate_count = max(1, rows // 20)
        source_indices = rng.integers(0, max(1, rows // 10), size=duplicate_count)
        target_indices = rng.integers(0, rows, size=duplicate_count)
        df.iloc[target_indices] = df.iloc[source_indices].to_numpy()

    df.to_csv(path, index=False)
    print(f"Dataset saved to {path} ({len(df):,} rows)")


def _run_once(func: Any, *args: Any, **kwargs: Any) -> tuple[float, float, Any]:
    tracemalloc.start()
    t0 = time.perf_counter()
    
    result = func(*args, **kwargs)
    
    elapsed = time.perf_counter() - t0
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    return elapsed, peak / 1024 / 1024, result


def run_benchmark(
    name: str,
    func: Any,
    *args: Any,
    repeat: int,
    warmup: bool,
    **kwargs: Any,
) -> dict[str, Any]:
    """Run a function and measure its peak python allocations and execution time."""
    if warmup:
        _run_once(func, *args, **kwargs)

    times: list[float] = []
    peaks: list[float] = []
    result: Any = None

    for _ in range(repeat):
        elapsed, peak_mb, result = _run_once(func, *args, **kwargs)
        times.append(elapsed)
        peaks.append(peak_mb)

    return {"name": name, "times": times, "peaks": peaks, "result": result}


def _format_stats(values: list[float], *, decimals: int) -> str:
    if not values:
        return "-"
    vmin = min(values)
    vmax = max(values)
    avg = sum(values) / len(values)
    if math.isclose(vmin, vmax):
        return f"{avg:.{decimals}f}"
    return f"{avg:.{decimals}f} ({vmin:.{decimals}f}-{vmax:.{decimals}f})"


def main():
    parser = argparse.ArgumentParser(description="arnio.auto_clean memory benchmark")
    parser.add_argument("--rows", type=int, default=100000, help="Number of rows to generate")
    parser.add_argument("--seed", type=int, default=42, help="Seed for deterministic dataset generation")
    parser.add_argument("--repeat", type=int, default=3, help="Number of timed runs per operation")
    parser.add_argument("--file", type=str, default="", help="Path to CSV file (optional)")
    parser.add_argument(
        "--reuse-file",
        action="store_true",
        help="Reuse the CSV file if it already exists",
    )
    parser.add_argument(
        "--no-warmup",
        action="store_true",
        help="Disable warmup run before timed runs",
    )
    parser.add_argument("--keep-file", action="store_true", help="Keep the generated CSV file after benchmark")
    args = parser.parse_args()

    csv_path = (
        args.file
        if args.file
        else f"benchmarks/auto_clean_{args.rows}_seed{args.seed}.csv"
    )
    warmup = not args.no_warmup

    generated = False
    if os.path.exists(csv_path) and args.reuse_file:
        print(f"Using existing dataset: {csv_path}")
    else:
        if os.path.exists(csv_path):
            print(f"Overwriting existing dataset: {csv_path}")
        generate_synthetic_data(rows=args.rows, path=csv_path, seed=args.seed)
        generated = True

    print("\nStarting Benchmarks...")
    print(f"Rows: {args.rows:,} | Seed: {args.seed} | Repeat: {args.repeat} | File: {csv_path}")
    print(f"{'Operation':<22} {'Time(s)':>20} {'Peak Py(MiB)':>16}")
    print("-" * 60)

    read_bench = run_benchmark(
        "ar.read_csv",
        ar.read_csv,
        csv_path,
        repeat=args.repeat,
        warmup=warmup,
    )
    frame = read_bench["result"]
    print(
        f"{read_bench['name']:<22} {_format_stats(read_bench['times'], decimals=3):>20} {_format_stats(read_bench['peaks'], decimals=2):>16}"
    )

    safe_bench = run_benchmark(
        "ar.auto_clean(safe)",
        ar.auto_clean,
        frame,
        mode="safe",
        repeat=args.repeat,
        warmup=warmup,
    )
    print(
        f"{safe_bench['name']:<22} {_format_stats(safe_bench['times'], decimals=3):>20} {_format_stats(safe_bench['peaks'], decimals=2):>16}"
    )

    strict_bench = run_benchmark(
        "ar.auto_clean(strict)",
        ar.auto_clean,
        frame,
        mode="strict",
        repeat=args.repeat,
        warmup=warmup,
    )
    print(
        f"{strict_bench['name']:<22} {_format_stats(strict_bench['times'], decimals=3):>20} {_format_stats(strict_bench['peaks'], decimals=2):>16}"
    )

    print("-" * 60)
    total_time_avg = (sum(read_bench["times"]) / len(read_bench["times"])) + (
        sum(strict_bench["times"]) / len(strict_bench["times"])
    )
    max_peak_avg = max(
        sum(read_bench["peaks"]) / len(read_bench["peaks"]),
        sum(strict_bench["peaks"]) / len(strict_bench["peaks"]),
    )
    print(f"{'Total avg (Read+Strict)':<22} {total_time_avg:>20.3f} {max_peak_avg:>16.2f}")

    if generated and not args.keep_file and os.path.exists(csv_path):
        os.remove(csv_path)
        print(f"\nRemoved temporary file {csv_path}")


if __name__ == "__main__":
    main()
