<div align="center">
  <h1>⚡ arnio</h1>
  <p><b>Fast CSV loading and cleaning for Python, powered by C++.</b></p>

  [![CI](https://github.com/im-anishraj/arnio/actions/workflows/ci.yml/badge.svg)](https://github.com/im-anishraj/arnio/actions/workflows/ci.yml)
  [![PyPI - Version](https://img.shields.io/pypi/v/arnio.svg)](https://pypi.org/project/arnio/)
  [![PyPI - Python Version](https://img.shields.io/pypi/pyversions/arnio.svg)](https://pypi.org/project/arnio/)
  [![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

  <p>
    <a href="#-why-arnio">Why Arnio?</a> •
    <a href="#-installation">Installation</a> •
    <a href="#-quickstart">Quickstart</a> •
    <a href="#-performance">Performance</a>
  </p>
</div>

<br/>

<p align="center">
  <img src="intro.gif" alt="arnio demo" width="700" style="border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);">
</p>

## 💡 Why arnio?

Data science in Python usually starts with the same messy chore: loading a massive CSV file, hunting down nulls, stripping whitespace, and normalizing column types. 

**arnio** handles the slowest, most repetitive part of working with tabular data by pushing the heavy lifting down to a highly optimized C++ core (via `pybind11`). It parses the CSV natively, runs a declarative cleaning pipeline, and only hands the data back to Python as a standard `pandas.DataFrame` when it's pristine.

- 🚀 **C++ Speed**: Significantly lower memory footprint and faster parsing than standard `pd.read_csv`.
- 🧹 **Declarative Pipelines**: Clean your data with a reproducible array of named steps. No scattered method chains.
- 🔍 **Zero-cost Previews**: Peek at schemas with `ar.scan_csv()` without loading the entire file.
- 🐼 **Pandas Native**: Arnio is designed as a *pre-processor*, seamlessly emitting `pd.DataFrame` so your downstream ML and analysis workflows remain unchanged.

---

## 📦 Installation

Arnio requires Python 3.9+ and is available on macOS, Linux, and Windows.

```bash
pip install arnio
```

---

## ⚡ Quickstart

### The Arnio Pipeline

```python
import arnio as ar

# 1. Load the raw file using the C++ backend
frame = ar.read_csv("customers.csv")

# 2. Run a blazing-fast cleaning pipeline
clean_frame = ar.pipeline(frame, [
    ("strip_whitespace",),
    ("normalize_case", {"case_type": "lower"}),
    ("drop_nulls",),
    ("drop_duplicates",),
])

# 3. Export to a clean pandas DataFrame!
df = ar.to_pandas(clean_frame)
```

---

## 🏎️ Performance

Arnio's memory-optimized columnar architecture ensures it scales effortlessly. 

**Benchmark: 1M-row CSV, 12 columns, mixed types.**

| Tool | Load Time | Peak Memory | Output |
| :--- | :--- | :--- | :--- |
| **pandas** | `~4.2s` | `~620 MB` | DataFrame |
| **arnio** | `~2.1s` | `~380 MB` | DataFrame |

*(Measured on an M2 MacBook Pro, Python 3.11. Approximately **2x faster** ingestion and **40% lower** peak memory.)*

---

## 🥊 Pandas vs. Arnio

Why not just write Pandas scripts? Because Arnio makes your ingestion explicit, safe, and easily portable across notebooks.

### ❌ The Pandas Way
```python
import pandas as pd

df = pd.read_csv("sales.csv")

# Ad-hoc cleaning scattered across your script
str_cols = df.select_dtypes(include="object").columns
df[str_cols] = df[str_cols].apply(lambda c: c.str.strip())
df = df.dropna()
df = df.drop_duplicates()
```

### ✅ The Arnio Way
```python
import arnio as ar

frame = ar.read_csv("sales.csv")

# Declarative, C++ powered pipeline
clean = ar.pipeline(frame, [
    ("strip_whitespace",),
    ("drop_nulls",),
    ("drop_duplicates",),
])

df = ar.to_pandas(clean)
```

---

## 🗺️ Roadmap

Arnio is under active development. The core C++ CSV parser and basic cleaning primitives are stable. Upcoming features include:

- [x] High-performance C++ parser core
- [x] Built-in primitives (`drop_nulls`, `strip_whitespace`, `normalize_case`)
- [x] Zero-copy Pandas conversion
- [ ] Chunked/streaming reads for out-of-core processing
- [ ] Advanced automatic type inference
- [ ] Schema enforcement contracts
- [ ] Parallelized C++ parsing

Feedback on priorities is welcome — feel free to open a [GitHub Issue](https://github.com/im-anishraj/arnio/issues)!

---

## 🤝 Contributing

Contributions are genuinely appreciated! Because Arnio is a hybrid C++/Python project, there is a lot of room to shape its architecture.

To build from source:

```bash
git clone https://github.com/im-anishraj/arnio.git
cd arnio
pip install -e ".[dev]"
pytest tests/ -v
```

Before submitting a PR, please ensure all tests pass and your code adheres to standard `clang-format` and `ruff` guidelines.

---

<div align="center">
  <p><b>Arnio</b> is released under the <a href="LICENSE">MIT License</a>.</p>
  <p><i>Built to make Python data work feel faster and cleaner — one CSV at a time.</i></p>
</div>
