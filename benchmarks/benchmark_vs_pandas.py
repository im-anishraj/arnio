"""
Reproducible benchmark: arnio vs pandas
Run: python benchmarks/benchmark_vs_pandas.py
"""
import time
import tracemalloc
import pandas as pd
import arnio as ar

CSV_FILE = "benchmarks/benchmark_1m.csv"
RUNS = 3

def benchmark_pandas(path):
    tracemalloc.start()
    t0 = time.perf_counter()
    
    df = pd.read_csv(path)
    df.columns = df.columns.str.strip()
    df = df.dropna()
    df = df.drop_duplicates()
    for col in df.select_dtypes(include="object").columns:
        df[col] = df[col].str.strip().str.lower()
    
    elapsed = time.perf_counter() - t0
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return elapsed, peak / 1024 / 1024

def benchmark_arnio(path):
    tracemalloc.start()
    t0 = time.perf_counter()
    
    frame = ar.read_csv(path)
    clean = ar.pipeline(frame, [
        ("strip_whitespace",),
        ("normalize_case", {"case_type": "lower"}),
        ("drop_nulls",),
        ("drop_duplicates",),
    ])
    df = ar.to_pandas(clean)
    
    elapsed = time.perf_counter() - t0
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return elapsed, peak / 1024 / 1024

if __name__ == "__main__":
    print(f"{'Metric':<20} {'pandas':>12} {'arnio':>12}")
    print("-" * 46)
    
    pd_times, ar_times = [], []
    pd_rams, ar_rams = [], []
    
    for i in range(RUNS):
        pt, pr = benchmark_pandas(CSV_FILE)
        at, ar_r = benchmark_arnio(CSV_FILE)
        pd_times.append(pt); ar_times.append(at)
        pd_rams.append(pr); ar_rams.append(ar_r)
    
    avg = lambda x: sum(x) / len(x)
    print(f"{'Exec Time (avg)':<20} {avg(pd_times):>11.2f}s {avg(ar_times):>11.2f}s")
    print(f"{'Peak RAM':<20} {avg(pd_rams):>10.0f}MB {avg(ar_rams):>10.0f}MB")
    print(f"\nSpeed: {avg(pd_times)/avg(ar_times):.1f}x | RAM: {(1 - avg(ar_rams)/avg(pd_rams))*100:.0f}% reduction")
