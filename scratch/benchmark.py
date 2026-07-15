import time
import tracemalloc
import pandas as pd
import arnio as ar
import gc
import sys

def generate_data(rows: int) -> pd.DataFrame:
    # A mix of types, missing values, duplicates, and huge strings to push the boundaries
    names = ["Alice", "Bob", "Charlie", "David", "Eve", "  Frank  ", "George", None]
    domains = ["example.com", "test.org", "invalid-domain", None]
    
    # Repeat the basic building blocks
    df = pd.DataFrame({
        "id": range(rows),
        "name": (names * (rows // len(names) + 1))[:rows],
        "email": [(f"user{i}@" + domains[i % len(domains)]) if domains[i % len(domains)] else None for i in range(rows)],
        "age": [20 + (i % 50) for i in range(rows)],
        "score": [float(i % 100) for i in range(rows)],
    })
    return df

schema = ar.Schema({
    "id": ar.Int(min=0),
    "name": ar.String(max_length=10, nullable=True),
    "email": ar.Email(nullable=True),
    "age": ar.Int(min=18, max=100),
    "score": ar.Float(min=0.0, max=100.0)
})

pipeline = ar.Pipeline([
    "strip_whitespace",
    ("normalize_case", {"columns": ["email"], "case": "lower"}),
    ("fill_nulls", {"column": "name", "value": "Unknown"})
])

def run_benchmark(rows: int):
    print(f"\n--- Benchmarking {rows:,} rows ---")
    df = generate_data(rows)
    
    gc.collect()
    tracemalloc.start()
    t0 = time.perf_counter()
    
    report = ar.profile(df)
    
    t1 = time.perf_counter()
    current, peak_profile = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    print(f"Profile: {t1 - t0:.4f}s, Peak RAM Allocation: {peak_profile / 1024 / 1024:.2f} MB")
    
    gc.collect()
    tracemalloc.start()
    t0 = time.perf_counter()
    
    result = ar.validate(df, schema)
    
    t1 = time.perf_counter()
    current, peak_validate = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    print(f"Validate: {t1 - t0:.4f}s, Peak RAM Allocation: {peak_validate / 1024 / 1024:.2f} MB, Issues: {len(result.issues)}")
    
    gc.collect()
    tracemalloc.start()
    t0 = time.perf_counter()
    
    cleaned = pipeline.run(df)
    
    t1 = time.perf_counter()
    current, peak_clean = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    print(f"Clean: {t1 - t0:.4f}s, Peak RAM Allocation: {peak_clean / 1024 / 1024:.2f} MB")

if __name__ == "__main__":
    for size in [10_000, 100_000, 1_000_000, 5_000_000, 10_000_000]:
        run_benchmark(size)
