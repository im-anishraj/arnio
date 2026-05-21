"""
Reproducible benchmark: arnio vs pandas
Run: python benchmarks/benchmark_vs_pandas.py
"""

import argparse
import json
import os
import subprocess
import sys
import time
import tracemalloc
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
from pandas.testing import assert_frame_equal

import arnio as ar

CSV_FILE = "benchmarks/benchmark_1m.csv"
WIDE_CSV_FILE = "benchmarks/benchmark_wide.csv"
MULTILINE_CSV_FILE = "benchmarks/benchmark_multiline.csv"
SPARSE_NULLS_FILE = "benchmarks/benchmark_sparse_nulls.csv"
DENSE_NULLS_FILE = "benchmarks/benchmark_sparse_nulls_dense.csv"
DRY_RUN = os.getenv("ARNIO_BENCHMARK_DRY_RUN") == "1"
RUNS = 1 if DRY_RUN else 3

BASELINE_FILE = "benchmarks/baseline.json"
REGRESSION_THRESHOLD = 5  # Percent


@dataclass(frozen=True)
class BenchmarkCase:
    name: str
    path: str


ALL_BENCHMARKS = (
    BenchmarkCase("Tall CSV (1,000,000 rows x 12 columns)", CSV_FILE),
    BenchmarkCase("Wide CSV (5,000 rows x 256 columns)", WIDE_CSV_FILE),
    BenchmarkCase("Multiline CSV (100,000 rows x 4 columns)", MULTILINE_CSV_FILE),
    BenchmarkCase(
        "Sparse-null CSV (1,000,000 rows x 6 columns, 1% nulls)", SPARSE_NULLS_FILE
    ),
    BenchmarkCase(
        "Dense-null CSV (1,000,000 rows x 6 columns, 20% nulls)", DENSE_NULLS_FILE
    ),
)
BENCHMARKS = ALL_BENCHMARKS[:1] if DRY_RUN else ALL_BENCHMARKS


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


def verify_correctness(path):
    ensure_dataset_exists(path)

    # Pandas pipeline
    df_pd = pd.read_csv(path)
    df_pd.columns = df_pd.columns.str.strip()
    for col in df_pd.select_dtypes(include=["object", "string"]).columns:
        df_pd[col] = df_pd[col].apply(
            lambda x: x.strip().lower() if isinstance(x, str) else x
        )
    df_pd = df_pd.dropna()
    df_pd = df_pd.drop_duplicates()
    df_pd = df_pd.reset_index(drop=True)

    # Arnio pipeline
    frame_ar = ar.read_csv(path)
    clean_ar = ar.pipeline(
        frame_ar,
        [
            ("strip_whitespace",),
            ("normalize_case", {"case_type": "lower"}),
            ("drop_nulls",),
            ("drop_duplicates",),
        ],
    )
    df_ar = ar.to_pandas(clean_ar).reset_index(drop=True)

    # Note: Column order and dtypes might have slight expected variations,
    # but values should match strictly. We use check_dtype=False for robust comparison.
    assert_frame_equal(df_pd, df_ar, check_dtype=False)
    print(f"Correctness verification passed for {path}")


def benchmark_pandas(path):
    ensure_dataset_exists(path)
    tracemalloc.start()
    t_start = time.perf_counter()
    rss_samples = []
    start_rss = get_process_rss_mb()
    if start_rss is not None:
        rss_samples.append(start_rss)

    t0 = time.perf_counter()
    df = pd.read_csv(path)
    t_read_csv = time.perf_counter() - t0

    rss = get_process_rss_mb()
    if rss is not None:
        rss_samples.append(rss)

    t0 = time.perf_counter()
    df.columns = df.columns.str.strip()
    for col in df.select_dtypes(include=["object", "string"]).columns:
        df[col] = df[col].apply(
            lambda x: x.strip().lower() if isinstance(x, str) else x
        )
    t_clean_strings = time.perf_counter() - t0

    t0 = time.perf_counter()
    df = df.dropna()
    t_drop_nulls = time.perf_counter() - t0

    t0 = time.perf_counter()
    df = df.drop_duplicates()
    t_drop_duplicates = time.perf_counter() - t0

    rss = get_process_rss_mb()
    if rss is not None:
        rss_samples.append(rss)

    elapsed = time.perf_counter() - t_start
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    peak_rss = max(rss_samples) if rss_samples else None

    ops = {
        "read_csv": t_read_csv,
        "clean_strings": t_clean_strings,
        "drop_nulls": t_drop_nulls,
        "drop_duplicates": t_drop_duplicates,
        "to_pandas": 0.0,  # N/A for pandas
    }
    return elapsed, peak / 1024 / 1024, peak_rss, ops


def benchmark_arnio(path):
    ensure_dataset_exists(path)
    tracemalloc.start()
    t_start = time.perf_counter()
    rss_samples = []
    start_rss = get_process_rss_mb()
    if start_rss is not None:
        rss_samples.append(start_rss)

    t0 = time.perf_counter()
    frame = ar.read_csv(path)
    t_read_csv = time.perf_counter() - t0

    rss = get_process_rss_mb()
    if rss is not None:
        rss_samples.append(rss)

    t0 = time.perf_counter()
    # To benchmark operations individually, we do them one by one
    frame1 = ar.strip_whitespace(frame)
    frame2 = ar.normalize_case(frame1, case_type="lower")
    t_clean_strings = time.perf_counter() - t0

    t0 = time.perf_counter()
    frame3 = ar.drop_nulls(frame2)
    t_drop_nulls = time.perf_counter() - t0

    t0 = time.perf_counter()
    frame4 = ar.drop_duplicates(frame3)
    t_drop_duplicates = time.perf_counter() - t0

    rss = get_process_rss_mb()
    if rss is not None:
        rss_samples.append(rss)

    t0 = time.perf_counter()
    _ = ar.to_pandas(frame4)
    t_to_pandas = time.perf_counter() - t0

    rss = get_process_rss_mb()
    if rss is not None:
        rss_samples.append(rss)

    elapsed = time.perf_counter() - t_start
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    peak_rss = max(rss_samples) if rss_samples else None

    ops = {
        "read_csv": t_read_csv,
        "clean_strings": t_clean_strings,
        "drop_nulls": t_drop_nulls,
        "drop_duplicates": t_drop_duplicates,
        "to_pandas": t_to_pandas,
    }
    return elapsed, peak / 1024 / 1024, peak_rss, ops


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


def load_baseline():
    try:
        with open(BASELINE_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}


def calculate_regression(current, baseline):
    return (
        (current - baseline) / baseline
    ) * 100  # How much slower current benchmark is compared to baseline


def run_case(case, skip_correctness=False):
    baseline_data = load_baseline()

    print(case.name)

    if not skip_correctness:
        # Verify correctness in parent process before benchmark runs.
        # Parity failure should fail the benchmark/run instead of continuing silently.
        verify_correctness(case.path)

    print(f"{'Metric':<20} {'pandas':>12} {'arnio':>12} {'speedup':>10}")
    print("-" * 57)

    pd_times, ar_times = [], []
    pd_trace_rams, ar_trace_rams = [], []
    pd_rss_rams, ar_rss_rams = [], []

    pd_ops_list = {
        k: []
        for k in [
            "read_csv",
            "clean_strings",
            "drop_nulls",
            "drop_duplicates",
            "to_pandas",
        ]
    }
    ar_ops_list = {
        k: []
        for k in [
            "read_csv",
            "clean_strings",
            "drop_nulls",
            "drop_duplicates",
            "to_pandas",
        ]
    }

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

        for k in pd_ops_list:
            if k in pd_result.get("ops", {}):
                pd_ops_list[k].append(pd_result["ops"][k])
            if k in ar_result.get("ops", {}):
                ar_ops_list[k].append(ar_result["ops"][k])

    for op in [
        "read_csv",
        "clean_strings",
        "drop_nulls",
        "drop_duplicates",
        "to_pandas",
    ]:
        if pd_ops_list[op] and ar_ops_list[op]:
            p_avg = avg(pd_ops_list[op])
            a_avg = avg(ar_ops_list[op])
            speedup = (
                f"{p_avg/a_avg:.1f}x" if a_avg > 0 and op != "to_pandas" else "N/A"
            )
            p_str = f"{p_avg:>11.2f}s" if op != "to_pandas" else f"{'N/A':>12}"
            print(f"{op:<20} {p_str} {a_avg:>11.2f}s {speedup:>10}")

    print("-" * 57)

    print(
        f"{'Exec Time (Total)':<20} {avg(pd_times):>11.2f}s {avg(ar_times):>11.2f}s {(avg(pd_times)/avg(ar_times)):>9.1f}x"
    )
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

    baseline_case = baseline_data.get(case.name)

    if baseline_case:
        baseline_time = baseline_case["arnio_exec_time"]
        current_time = avg(ar_times)

        regression = calculate_regression(current_time, baseline_time)

        if regression > REGRESSION_THRESHOLD:
            print(
                f"WARNING: Regression detected:"
                f"{regression:.1f}% slower than baseline "
                f"(threshold: {REGRESSION_THRESHOLD}%)"
            )
    else:
        print("No baseline found for regression comparison.")

    print()


def run_child(engine, case_path):
    if engine == "pandas":
        elapsed, peak_trace_mb, peak_rss_mb, ops = benchmark_pandas(case_path)
    elif engine == "arnio":
        elapsed, peak_trace_mb, peak_rss_mb, ops = benchmark_arnio(case_path)
    else:
        raise ValueError(f"Unknown engine: {engine}")

    payload = {
        "elapsed": elapsed,
        "peak_trace_mb": peak_trace_mb,
        "peak_rss_mb": peak_rss_mb,
        "ops": ops,
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
