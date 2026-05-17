"""
Reproducible benchmark: arnio vs pandas
Run: python benchmarks/benchmark_vs_pandas.py
"""

import argparse
import json
import subprocess
import sys
import time
import tracemalloc
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

import arnio as ar

CSV_FILE = "benchmarks/benchmark_1m.csv"
WIDE_CSV_FILE = "benchmarks/benchmark_wide.csv"
RUNS = 3


@dataclass(frozen=True)
class BenchmarkCase:
    name: str
    path: str


BENCHMARKS = (
    BenchmarkCase("Tall CSV (1,000,000 rows x 12 columns)", CSV_FILE),
    BenchmarkCase("Wide CSV (5,000 rows x 256 columns)", WIDE_CSV_FILE),
)


_PSUTIL_PROCESS = None
_PSUTIL_PROBED = False


def _get_psutil_process():
    global _PSUTIL_PROCESS
    global _PSUTIL_PROBED

    if _PSUTIL_PROBED:
        return _PSUTIL_PROCESS

    _PSUTIL_PROBED = True
    try:
        import psutil

        _PSUTIL_PROCESS = psutil.Process()
        return _PSUTIL_PROCESS
    except Exception:
        return None


def detect_rss_source():
    if _get_psutil_process() is not None:
        return "psutil"
    try:
        import resource

        _ = resource.RUSAGE_SELF
        return "resource"
    except Exception:
        return "unavailable"


def get_process_rss_mb():
    process = _get_psutil_process()
    if process is not None:
        return process.memory_info().rss / 1024 / 1024

    try:
        import resource

        rss_kb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        if sys.platform == "darwin":
            return rss_kb / 1024 / 1024
        return rss_kb / 1024
    except Exception:
        return None


def ensure_dataset_exists(path):
    if not Path(path).exists():
        raise FileNotFoundError(
            f"Missing benchmark dataset: {path}. "
            "Run `python benchmarks/generate_data.py` first."
        )


def benchmark_pandas(path):
    ensure_dataset_exists(path)
    tracemalloc.start()
    t0 = time.perf_counter()
    rss_samples = []
    start_rss = get_process_rss_mb()
    if start_rss is not None:
        rss_samples.append(start_rss)

    df = pd.read_csv(path)
    rss = get_process_rss_mb()
    if rss is not None:
        rss_samples.append(rss)
    df.columns = df.columns.str.strip()
    df = df.dropna()
    df = df.drop_duplicates()
    for col in df.select_dtypes(include=["object", "string"]).columns:
        df[col] = df[col].astype(str).str.strip().str.lower()
    rss = get_process_rss_mb()
    if rss is not None:
        rss_samples.append(rss)

    elapsed = time.perf_counter() - t0
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    peak_rss = max(rss_samples) if rss_samples else None
    return elapsed, peak / 1024 / 1024, peak_rss


def benchmark_arnio(path):
    ensure_dataset_exists(path)
    tracemalloc.start()
    t0 = time.perf_counter()
    rss_samples = []
    start_rss = get_process_rss_mb()
    if start_rss is not None:
        rss_samples.append(start_rss)

    frame = ar.read_csv(path)
    rss = get_process_rss_mb()
    if rss is not None:
        rss_samples.append(rss)
    clean = ar.pipeline(
        frame,
        [
            ("strip_whitespace",),
            ("normalize_case", {"case_type": "lower"}),
            ("drop_nulls",),
            ("drop_duplicates",),
        ],
    )
    rss = get_process_rss_mb()
    if rss is not None:
        rss_samples.append(rss)
    ar.to_pandas(clean)
    rss = get_process_rss_mb()
    if rss is not None:
        rss_samples.append(rss)

    elapsed = time.perf_counter() - t0
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    peak_rss = max(rss_samples) if rss_samples else None
    return elapsed, peak / 1024 / 1024, peak_rss


def avg(values):
    return sum(values) / len(values)


def run_subprocess(engine, path):
    cmd = [
        sys.executable,
        str(Path(__file__).resolve()),
        "--engine",
        engine,
        "--case",
        path,
        "--json",
    ]
    completed = subprocess.run(
        cmd,
        check=True,
        capture_output=True,
        text=True,
    )
    output = completed.stdout.strip()
    if not output:
        raise RuntimeError(f"No output from benchmark subprocess ({engine}).")
    return json.loads(output)


def run_case(case):
    print(case.name)
    print(f"{'Metric':<20} {'pandas':>12} {'arnio':>12}")
    print("-" * 46)

    pd_times, ar_times = [], []
    pd_trace_rams, ar_trace_rams = [], []
    pd_rss_rams, ar_rss_rams = [], []

    for i in range(RUNS):
        pd_result = run_subprocess("pandas", case.path)
        ar_result = run_subprocess("arnio", case.path)
        pt, pr_trace, pr_rss = (
            pd_result["elapsed"],
            pd_result["peak_trace_mb"],
            pd_result.get("peak_rss_mb"),
        )
        at, ar_trace, ar_rss = (
            ar_result["elapsed"],
            ar_result["peak_trace_mb"],
            ar_result.get("peak_rss_mb"),
        )
        pd_times.append(pt)
        ar_times.append(at)
        pd_trace_rams.append(pr_trace)
        ar_trace_rams.append(ar_trace)
        if pr_rss is not None:
            pd_rss_rams.append(pr_rss)
        if ar_rss is not None:
            ar_rss_rams.append(ar_rss)

    print(f"{'Exec Time (avg)':<20} {avg(pd_times):>11.2f}s {avg(ar_times):>11.2f}s")
    if pd_rss_rams and ar_rss_rams:
        pd_rss_avg = avg(pd_rss_rams)
        ar_rss_avg = avg(ar_rss_rams)
        print(f"{'Peak RSS (process)':<20} {pd_rss_avg:>10.0f}MB {ar_rss_avg:>10.0f}MB")
    else:
        pd_rss_avg = None
        ar_rss_avg = None
        print(f"{'Peak RSS (process)':<20} {'n/a':>12} {'n/a':>12}")
    print(
        f"{'Peak Python (trace)':<20} {avg(pd_trace_rams):>10.0f}MB {avg(ar_trace_rams):>10.0f}MB"
    )
    if pd_rss_avg and ar_rss_avg:
        ram_reduction = (1 - (ar_rss_avg / pd_rss_avg)) * 100
        print(
            f"\nSpeed: {avg(pd_times)/avg(ar_times):.1f}x | RAM: {ram_reduction:.0f}% reduction (RSS)"
        )
    else:
        print(f"\nSpeed: {avg(pd_times)/avg(ar_times):.1f}x")
    print()


def run_child(engine, case_path):
    if engine == "pandas":
        elapsed, peak_trace_mb, peak_rss_mb = benchmark_pandas(case_path)
    elif engine == "arnio":
        elapsed, peak_trace_mb, peak_rss_mb = benchmark_arnio(case_path)
    else:
        raise ValueError(f"Unknown engine: {engine}")

    payload = {
        "elapsed": elapsed,
        "peak_trace_mb": peak_trace_mb,
        "peak_rss_mb": peak_rss_mb,
    }
    print(json.dumps(payload))


def parse_args():
    parser = argparse.ArgumentParser(description="Run Arnio vs pandas benchmarks")
    parser.add_argument(
        "--engine", choices=["pandas", "arnio"], help="Benchmark engine"
    )
    parser.add_argument("--case", help="CSV path for a single benchmark run")
    parser.add_argument("--json", action="store_true", help="Emit JSON result")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    if args.engine and args.case:
        if not args.json:
            raise SystemExit("Child mode requires --json output.")
        run_child(args.engine, args.case)
        raise SystemExit(0)

    rss_source = detect_rss_source()
    if rss_source == "resource":
        print(
            "Note: Peak RSS uses resource.getrusage; units are KB on Linux and bytes on macOS."
        )
    elif rss_source == "unavailable":
        print("Note: Peak RSS unavailable (install psutil for process RSS).")
    for benchmark_case in BENCHMARKS:
        run_case(benchmark_case)
