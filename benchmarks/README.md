# 📊 Arnio Reproducible Benchmark Suite

This directory contains deterministic and reproducible benchmarks to compare the performance, memory utilization, and parsing efficiency of **Arnio** vs **pandas**.

---

## 🚀 Quoted Multiline CSV Parsing Benchmark (Issue #251)

Parsing CSV files with quoted multiline strings (e.g., cell values containing embedded newlines `\n` or `\r\n`) is a common source of performance bottlenecks. While pandas parses these via complex Python/C fallback logic or the C parser engine, Arnio parses them natively in C++ using a high-performance stateful parser.

This benchmark profiles:
* **Dataset**: 100,000 rows x 4 columns with complex, deterministically generated multiline comments and notes containing newlines, inner quotes, and varied string structures.
* **Operations**: Read CSV -> Strip Whitespace -> Lowercase -> Drop Nulls -> Drop Duplicates.
* **Metrics**: Wall-clock execution time (via `time.perf_counter()`) and peak memory footprint (via `tracemalloc` / `psutil` RSS).

---

## 🛠️ Step-by-Step Execution Guide

To ensure clean and comparable benchmark metrics, close other memory-heavy processes and run the benchmark from the repository root inside your virtual environment.

### Step 1: Install Dependencies
Install the package in editable mode to compile the latest C++ bindings locally:
```bash
pip install -e ".[dev]"
```

### Step 2: Generate Deterministic Datasets
Run the data generator to create deterministic tall, wide, multiline, and sparse-null CSV files with fixed random seeds:
```bash
python benchmarks/generate_data.py
```
This generates the following files:
* `benchmarks/benchmark_1m.csv` (Tall CSV: 1M rows x 12 columns)
* `benchmarks/benchmark_wide.csv` (Wide CSV: 5,000 rows x 256 columns)
* `benchmarks/benchmark_multiline.csv` (Multiline CSV: 100,000 rows x 4 columns)
* `benchmarks/benchmark_sparse_nulls.csv` (Sparse-null CSV: 1M rows x 6 columns, 1% nulls)
* `benchmarks/benchmark_sparse_nulls_dense.csv` (Dense-null CSV: 1M rows x 6 columns, 20% nulls)

### Step 3: Run the Benchmark Suite
Run the suite using the standard comparison script:
```bash
python benchmarks/benchmark_vs_pandas.py
```

### Focused benchmark: sparse-null workloads
Benchmark null-related operations (read_csv, drop_nulls, fill_nulls, keep_rows_with_nulls) across five null densities from 0.1% to 20%:
```bash
python benchmarks/benchmark_sparse_nulls.py --rows 1000000 --runs 5
```

---

## 🔍 How to Compare and Analyze Results

Reviewers can compare the printed outputs directly across three key categories:

1. **Correctness Verification**: The benchmark script automatically runs a strict correctness check (`assert_frame_equal`) ensuring that both pandas and Arnio pipelines produce identical values for each dataset.
2. **Speed Parity**: Compare the average elapsed time (seconds) for each step (e.g., `read_csv`, `clean_strings`, `drop_nulls`, `drop_duplicates`).
3. **Memory Footprint**: Compare the **Peak RSS** (Resident Set Size) and **Peak Traced Memory** (MB). Because Arnio uses columnar storage, it maintains a highly optimized memory footprint compared to pandas.

### System Information Log
When sharing benchmark results in an issue or PR comment, please copy the complete terminal log and include:
* **Operating System** (e.g., macOS Sequoia, Ubuntu 22.04, Windows 11)
* **Python version** (e.g., 3.11, 3.12)
* **CPU Model** (e.g., Apple M2 Max, AMD Ryzen 9 5900X)
* **pandas & NumPy versions**
