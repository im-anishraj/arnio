<div align="center">
  <picture align="center">
    <source media="(prefers-color-scheme: dark)" srcset="arnio.svg">
    <img alt="Arnio Logo" src="arnio.svg">
  </picture>
  <br />

  <b>Arnio</b> is an open-source C++ accelerated data preprocessing library<br />
  <i>for Python. Built for speed and memory efficiency — and actively being optimized during GSSoC 2026.</i>
  <br />

  <br />
  <p align="center">
    <!-- Package Stats -->
    <a href="https://pypi.org/project/arnio/"><img src="https://img.shields.io/pypi/v/arnio?style=for-the-badge&logo=pypi&logoColor=white&color=blue" alt="PyPI Latest Release"></a>
    <a href="https://pypi.org/project/arnio/"><img src="https://img.shields.io/pypi/pyversions/arnio?style=for-the-badge&logo=python&logoColor=white&color=black" alt="Python Versions"></a>
    <a href="https://pypi.org/project/arnio/"><img src="https://img.shields.io/pypi/dm/arnio?style=for-the-badge&logo=pypi&logoColor=white&color=blue" alt="PyPI Downloads"></a>
    <br>
    <!-- Health / Meta -->
    <a href="https://github.com/im-anishraj/arnio/actions/workflows/ci.yml"><img src="https://img.shields.io/github/actions/workflow/status/im-anishraj/arnio/ci.yml?branch=main&label=CI&style=for-the-badge&logo=github&color=2ea44f" alt="CI"></a>
    <a href="https://github.com/im-anishraj/arnio/actions/workflows/build_wheels.yml"><img src="https://img.shields.io/github/actions/workflow/status/im-anishraj/arnio/build_wheels.yml?branch=main&label=Wheels&style=for-the-badge&logo=github&color=2ea44f" alt="Build Wheels"></a>
    <a href="https://github.com/psf/black"><img src="https://img.shields.io/badge/code%20style-black-000000.svg?style=for-the-badge" alt="Code style: black"></a>
    <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-blue.svg?style=for-the-badge" alt="License"></a>
    <a href="https://gssoc.girlscript.tech/"><img src="https://img.shields.io/badge/GSSoC-2026-orange.svg?style=for-the-badge" alt="GSSoC"></a>
  </p>
  <br />
  <p>
    <a href="#-the-problem">The Problem</a> •
    <a href="#-the-solution-arnio">The Solution</a> •
    <a href="#-benchmarks-arnio-vs-pandas">Benchmarks</a> •
    <a href="#-getting-started">Quickstart</a>
  </p>
</div>

---

> **Pandas is incredible for analysis. It is notoriously slow and memory-hungry for ingesting and cleaning raw CSVs.** <br/>
> Arnio exists to do exactly one thing: intercept your messy CSVs, clean them natively in C++, and hand you a pristine Pandas DataFrame in half the time.

<p align="center">
  <img src="intro.gif" alt="arnio demo" width="80%" style="border-radius: 12px; border: 1px solid #30363D; box-shadow: 0 10px 30px rgba(0,0,0,0.5);">
</p>

## 🧨 The Problem

Every data project starts the same way. You load a CSV. It crashes your RAM. You load it again in chunks. You find random nulls, weird capitalization, and trailing whitespaces. You write a 15-line script chaining `.apply()`, `.dropna()`, and `.str.strip()`. You copy-paste this script into your next 5 Jupyter notebooks. 

It's slow. It's unreadable. It's error-prone.

## ✨ The Solution: Arnio

**Arnio** replaces your messy ingestion script with a high-performance, declarative pipeline powered by `pybind11` and C++. 

| ❌ The Old Way (Pandas) | ⚡ The Arnio Way |
| :--- | :--- |
| **Memory Spikes**: Python loads the entire raw string file before casting. | **C++ Native**: Parses and infers types directly into columnar memory. |
| **Spaghetti Code**: `.apply()` lambda functions scattered across cells. | **Declarative**: A strict, readable list of cleaning steps. |
| **Slow Execution**: Python loops over strings to strip whitespaces. | **Blazing Fast**: Cleaning primitives run at near metal speeds. |

---

## 🚀 Getting Started

If you have Python 3.9+, you are 5 seconds away from faster data pipelines.

```bash
pip install arnio
```

### The 3-Step Workflow

Drop Arnio into the very top of your Jupyter Notebook or Python script.

```python
import arnio as ar

# 1. Load the raw file using the C++ core (no Python overhead)
frame = ar.read_csv("messy_sales_data.csv")

# 2. Define a strict, readable cleaning pipeline
clean_frame = ar.pipeline(frame, [
    ("strip_whitespace",),
    ("normalize_case", {"case_type": "lower"}),
    ("fill_nulls", {"value": 0.0, "subset": ["revenue"]}),
    ("drop_nulls",),
    ("drop_duplicates",),
])

# 3. Export to a clean pandas DataFrame and start your analysis!
df = ar.to_pandas(clean_frame)

# -> Now, use `df` exactly like you always have.
```

---

## 🏎️ Benchmarks

> Tested on Ubuntu, Python 3.12, 1M row CSV.  
> Run `make benchmark` to reproduce on your machine.

| Metric | pandas | arnio v1.0.0 |
|--------|--------|--------------|
| Execution Time | 4.73s | 5.75s |
| Peak RAM | 211MB | 212MB |

**Current state:** arnio's C++ CSV reader matches pandas on memory.  
Speed parity is the active engineering goal for v0.2.0 — specifically  
`drop_duplicates` and `strip_whitespace` are unoptimized C++ and are  
the primary contributors to the gap.

**[Help close the gap →](https://github.com/im-anishraj/arnio/issues)**

<details>
<summary><b>🔍 Want to peek at a massive file without loading it?</b></summary>
<br>

Arnio lets you instantly scan a massive CSV to infer its schema without loading the data into memory.

```python
import arnio as ar

schema = ar.scan_csv("100GB_file.csv")
print(schema) 
# {'id': 'INT64', 'name': 'STRING', 'is_active': 'BOOL'}
```
</details>

---

## 🛠️ What's Inside?

Arnio ships with a growing library of hyper-optimized C++ cleaning primitives:

- `drop_nulls`: Rip out bad rows instantly.
- `fill_nulls`: Patch holes with scalar values.
- `drop_duplicates`: Deduplicate rows based on exact matches.
- `strip_whitespace`: Trim invisible spaces from string columns.
- `normalize_case`: Force `upper` or `lower` case instantly.
- `rename_columns` & `cast_types`: Shape your data exactly how you need it.

---

## 🤝 Contributing

Arnio is a GSSoC 2026 project. We welcome contributors of all levels.

- **No C++ required**: Add pipeline steps in pure Python
- **C++ contributors**: Help optimize `drop_duplicates` and `strip_whitespace`  
  — these are the current performance bottleneck
- **Docs & examples**: Always needed

[Read the Contribution Guide →](CONTRIBUTING.md) | 
[Browse open issues →](https://github.com/im-anishraj/arnio/issues)

---

## 🗺️ Roadmap

| Version | Focus | Status |
|---------|-------|--------|
| v1.0.0 | Stable release, cross-platform wheels, Google Colab support, CI/CD pipeline | ✅ Released |
| v0.2.0 | C++ pipeline optimization, speed parity with pandas | 🔨 Active |
| v0.3.0 | Chunked processing, Parquet/JSON support | 📋 Planned |

<div align="center">
<br>
<b>Stop fighting your data. Let Arnio clean it.</b>
<br><br>
</div>
