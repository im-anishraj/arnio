<div align="center">

<br>

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="final-icon-dark.svg">
  <img alt="Arnio" src="final-icon-light.svg" width="280">
</picture>

<br><br>

### Your CSV hits C++ before Python even wakes up.

<br>

**Arnio** is a compiled C++ data cleaning engine that slots in _before_ pandas.<br>
It parses, infers types, strips whitespace, deduplicates, and normalizes —<br>
all natively, in columnar memory — then hands you a pristine `DataFrame`.<br>
No `.apply()`. No lambda chains. No spaghetti.

<br>

<a href="https://pypi.org/project/arnio/"><img src="https://img.shields.io/pypi/v/arnio?style=flat-square&logo=pypi&logoColor=white&labelColor=0d1117&color=3572A5" alt="PyPI"></a>&nbsp;
<a href="https://pypi.org/project/arnio/"><img src="https://img.shields.io/pypi/pyversions/arnio?style=flat-square&logo=python&logoColor=white&labelColor=0d1117&color=3572A5" alt="Python"></a>&nbsp;
<a href="https://github.com/im-anishraj/arnio/actions/workflows/ci.yml"><img src="https://img.shields.io/github/actions/workflow/status/im-anishraj/arnio/ci.yml?branch=main&label=CI&style=flat-square&logo=github&labelColor=0d1117&color=2ea44f" alt="CI"></a>&nbsp;
<a href="https://codecov.io/gh/im-anishraj/arnio"><img src="https://img.shields.io/codecov/c/github/im-anishraj/arnio?style=flat-square&logo=codecov&labelColor=0d1117&color=2ea44f" alt="Coverage"></a>&nbsp;
<a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue?style=flat-square&labelColor=0d1117" alt="MIT"></a>&nbsp;
<a href="https://gssoc.girlscript.tech/"><img src="https://img.shields.io/badge/GSSoC-2026-ff6b35?style=flat-square&labelColor=0d1117" alt="GSSoC 2026"></a>
[![PyPI Downloads](https://static.pepy.tech/personalized-badge/arnio?period=total&units=INTERNATIONAL_SYSTEM&left_color=BLACK&right_color=GREEN&left_text=downloads)](https://pepy.tech/projects/arnio)

<br><br>

```bash
pip install arnio
```

<br>

<a href="#-quickstart">Quickstart</a>&ensp;·&ensp;<a href="#-why-arnio-exists">Why Arnio</a>&ensp;·&ensp;<a href="#%EF%B8%8F-architecture">Architecture</a>&ensp;·&ensp;<a href="#-benchmarks">Benchmarks</a>&ensp;·&ensp;<a href="#-contribute">Contribute</a>

</div>

<br>

---

<br>

## ⚡ Quickstart

Three lines. That's the entire workflow.

```python
import arnio as ar

# Load CSV directly through C++ — no Python parsing overhead
frame = ar.read_csv("messy_sales_data.csv")

# Declare what clean data looks like — arnio handles the rest
clean = ar.pipeline(frame, [
    ("strip_whitespace",),
    ("normalize_case", {"case_type": "lower"}),
    ("fill_nulls", {"value": 0.0, "subset": ["revenue"]}),
    ("drop_nulls",),
    ("drop_duplicates",),
])

# Out comes a standard pandas DataFrame — use it like you always have
df = ar.to_pandas(clean)
```

> Every step above executes in C++. Your Python code is a _configuration_ — not the execution engine.

<br>

<details>
<summary><b>📸 Peek at a 100 GB file without loading it</b></summary>
<br>

`scan_csv` reads only the header + a sample to infer the schema. Zero data loaded.

```python
schema = ar.scan_csv("100GB_file.csv")
# {'id': 'int64', 'name': 'string', 'is_active': 'bool', 'revenue': 'float64'}
```

Useful for exploring datasets before committing memory.
</details>

<details>
<summary><b>🧩 Add custom steps without touching C++</b></summary>
<br>

Register any Python function as a pipeline step. It receives a `DataFrame`, returns a `DataFrame`.

```python
def remove_outliers(df, column="revenue", threshold=100_000):
    return df[df[column] <= threshold]

ar.register_step("remove_outliers", remove_outliers)

# Now use it in any pipeline alongside native C++ steps
clean = ar.pipeline(frame, [
    ("strip_whitespace",),
    ("remove_outliers", {"column": "revenue", "threshold": 50000}),
    ("drop_duplicates",),
])
```

Custom steps run through a pandas↔ArFrame conversion bridge. Prototype in Python, then optionally migrate hot paths to C++ for full speed.
</details>

<br>

---

<br>

## 🔍 Why Arnio exists

Every data project starts the same way:

```python
df = pd.read_csv("data.csv")              # 💥 RAM spike — entire file as raw strings
df.columns = df.columns.str.strip()        # Why is this not automatic?
df["name"] = df["name"].str.strip()        # Python loop over every cell
df["name"] = df["name"].str.lower()        # Another Python loop
df = df.dropna()                           # Another pass
df = df.drop_duplicates()                  # Another pass
```

Six lines. Four full-data passes. All in interpreted Python. This is fine for a Jupyter demo — but it doesn't scale, it doesn't compose, and it definitely doesn't belong in production.

**Arnio intercepts this entire pattern.** It moves the heavy lifting to C++, replaces imperative chains with a declarative pipeline, and gives you a clean `DataFrame` in one shot.

<table>
<tr>
<td width="50%">

### Without Arnio
```python
df = pd.read_csv(path)
df.columns = df.columns.str.strip()
for col in str_cols:
    df[col] = df[col].str.strip()
    df[col] = df[col].str.lower()
df = df.dropna(subset=["revenue"])
df = df.drop_duplicates()
# 6+ lines, multiple passes, pure Python
```

</td>
<td width="50%">

### With Arnio
```python
frame = ar.read_csv(path)
df = ar.to_pandas(ar.pipeline(frame, [
    ("strip_whitespace",),
    ("normalize_case", {"case_type": "lower"}),
    ("drop_nulls", {"subset": ["revenue"]}),
    ("drop_duplicates",),
]))
# Declarative. Single pipeline. C++ execution.
```

</td>
</tr>
</table>

<br>

---

<br>

## 🏗️ Architecture

Arnio is not a pandas wrapper. It's a separate runtime with its own data model.

```text
┌──────────────────────────────────────────────────────────────┐
│  Your Python Code                                            │
│  frame = ar.read_csv("data.csv")                             │
│  clean = ar.pipeline(frame, [...])                           │
│  df = ar.to_pandas(clean)                                    │
└────────────────────────┬─────────────────────────────────────┘
                         │  pybind11 boundary
┌────────────────────────▼─────────────────────────────────────┐
│  C++ Runtime  (_arnio_cpp)                                   │
│                                                              │
│  ┌─────────────┐  ┌─────────────────┐  ┌──────────────────┐ │
│  │  CsvReader   │  │  Frame/Column   │  │  Cleaning Engine │ │
│  │  • RFC 4180  │  │  • Columnar     │  │  • drop_nulls    │ │
│  │  • BOM strip │  │  • std::variant │  │  • fill_nulls    │ │
│  │  • Type      │  │  • Bool null    │  │  • drop_dupes    │ │
│  │    inference │  │    masks        │  │  • strip_ws      │ │
│  │  • Quoted    │  │  • O(1) column  │  │  • normalize     │ │
│  │    fields    │  │    lookup       │  │  • rename/cast   │ │
│  └─────────────┘  └─────────────────┘  └──────────────────┘ │
│                                                              │
│  to_pandas() ──→ zero-copy NumPy buffer (numerics/bools)     │
└──────────────────────────────────────────────────────────────┘
```

### Design decisions that matter

| Decision | What it means |
|:---|:---|
| **Columnar storage** | Data lives in typed `std::vector`s — `vector<int64_t>`, `vector<double>`, `vector<string>` — not rows of variants. Cache-friendly and SIMD-ready. |
| **Boolean null masks** | Nulls are tracked in a separate `vector<bool>`, keeping data vectors dense. No sentinel values, no NaN tricks. |
| **Two-pass CSV read** | Pass 1 infers types across all rows. Pass 2 parses values directly into the correct typed column. No string→object→cast overhead. |
| **Zero-copy bridge** | `to_pandas()` exposes C++ memory directly via NumPy's buffer protocol. Numeric and boolean columns cross the boundary without copying. |
| **Step registry** | Pipeline steps map to C++ function pointers. Adding a new cleaning primitive is a single function + one registry entry. |

> Full architecture documentation: **[ARCHITECTURE.md](ARCHITECTURE.md)**

<br>

---

<br>

## 🏎️ Benchmarks

> **Setup**: Ubuntu, Python 3.12, 1M rows × 12 columns, synthetic messy CSV.<br>
> **Reproduce**: `make benchmark` — generates data and runs both engines.

```text
                     pandas         arnio
────────────────────────────────────────────
Exec Time (avg)       4.73s         5.75s
Peak RAM               211MB         212MB
API Clarity         Imperative    Declarative
```

**Arnio is near memory parity in the reference benchmark** while replacing ad-hoc Python string loops with a compiled, declarative pipeline. Validate memory and speed on your own workload. The execution time gap is a known, active optimization target — the current `drop_duplicates` and `strip_whitespace` implementations use unoptimized row-key serialization.

<table>
<tr>
<td>✅ <b>What's already won</b></td>
<td>🎯 <b>What's being optimized</b></td>
</tr>
<tr>
<td>

- Native C++ parsing eliminates Python memory spikes
- Columnar storage matches pandas' internal efficiency
- Declarative API eliminates `.apply()` spaghetti
- Zero-copy bridge for numeric conversions

</td>
<td>

- `drop_duplicates` — replace string serialization with hash-based comparisons
- `strip_whitespace` — in-place mutation instead of copy-on-write
- Parallel column processing via `std::thread`
- **[Help close the gap →](https://github.com/im-anishraj/arnio/issues)**

</td>
</tr>
</table>

<br>

---

<br>

## 🧰 Cleaning primitives

Every operation below runs natively in C++. No Python loops.

| Primitive | What it does | Example |
|:---|:---|:---|
| `drop_nulls` | Remove rows with null/empty values | `ar.drop_nulls(frame, subset=["age"])` |
| `fill_nulls` | Replace nulls with a scalar | `ar.fill_nulls(frame, 0, subset=["revenue"])` |
| `drop_duplicates` | Deduplicate rows (first/last/none) | `ar.drop_duplicates(frame, keep="first")` |
| `strip_whitespace` | Trim leading/trailing spaces from strings | `ar.strip_whitespace(frame)` |
| `normalize_case` | Force lower/upper/title case | `ar.normalize_case(frame, case_type="title")` |
| `rename_columns` | Rename columns via mapping | `ar.rename_columns(frame, {"old": "new"})` |
| `cast_types` | Cast column types | `ar.cast_types(frame, {"age": "int64"})` |
| `clean` | Convenience shorthand | `ar.clean(frame, drop_nulls=True)` |

Or compose them all into a **pipeline**:

```python
clean = ar.pipeline(frame, [
    ("strip_whitespace",),
    ("normalize_case", {"case_type": "lower"}),
    ("fill_nulls", {"value": "unknown", "subset": ["city"]}),
    ("drop_duplicates", {"keep": "first"}),
])
```

<br>

---

<br>

## 🧠 Data quality engine

Arnio now includes built-in dataset understanding before you analyze in pandas.

```python
report = ar.profile(frame)
print(report.summary())

suggestions = ar.suggest_cleaning(frame)
clean = ar.pipeline(frame, suggestions)
```

For production data contracts:

```python
schema = ar.Schema({
    "id": ar.Int64(nullable=False, unique=True),
    "email": ar.Email(nullable=False),
    "revenue": ar.Float64(nullable=True, min=0),
})

result = ar.validate(frame, schema)
if not result.passed:
    print(result.to_pandas())
```

For low-risk automatic cleanup:

```python
clean, report = ar.auto_clean(frame, mode="strict", return_report=True)
```

This is the layer pandas does not try to own: profiling, data contracts, row-level validation issues, and safe cleaning suggestions for messy incoming datasets.

<br>

---

<br>

## 🗺️ Roadmap

| Version | Focus | Status |
|:---:|:---|:---:|
| **v1.0** | Stable release · cross-platform wheels · CI/CD · PyPI publishing · Google Colab support | ✅ Shipped |
| **v0.2** | C++ pipeline optimization · speed parity with pandas · hash-based deduplication | 🔨 Active |
| **v0.3** | Chunked / streaming processing · Parquet & JSON readers | 📋 Planned |
| **v0.4** | Parallel column processing · SIMD string operations | 💭 Exploring |

<br>

---

<br>

## 🤝 Contribute

Arnio is a **[GSSoC 2026](https://gssoc.girlscript.tech/)** project with a structured contributor backlog across beginner, intermediate, and advanced tracks.

### You don't need C++ to contribute

Most new features are pure Python pipeline steps:

```python
# 1. Write a function that takes a DataFrame and returns a DataFrame
def remove_special_chars(df, columns=None):
    cols = columns or df.select_dtypes("object").columns
    for col in cols:
        df[col] = df[col].str.replace(r"[^a-zA-Z0-9\s]", "", regex=True)
    return df

# 2. Register it
ar.register_step("remove_special_chars", remove_special_chars)

# 3. Write tests, open a PR. That's it.
```

### If you do know C++

The biggest performance wins are in:
- **`drop_duplicates`** — replacing `std::ostringstream` row serialization with proper hash-based comparisons
- **`strip_whitespace`** — converting from copy-on-write to in-place mutation
- **Parallel column processing** — `std::thread` across independent columns

### Getting started

```bash
# macOS / Linux
git clone https://github.com/im-anishraj/arnio.git && cd arnio
make install   # pip install -e ".[dev]" + pre-commit
make test      # pytest with coverage
make lint      # ruff + black

# Windows
pip install -e ".[dev]"
pre-commit install
pytest tests/ -v
```

> **PR titles must follow [Conventional Commits](https://www.conventionalcommits.org/)** — `feat:`, `fix:`, `docs:`, `chore:`. Our release pipeline auto-generates changelogs from these.

For GSSoC contributors, please read **[GSSOC_GUIDE.md](GSSOC_GUIDE.md)** before asking to be assigned. It explains issue claiming, contribution levels, review expectations, and what maintainers look for in a strong PR.

<p align="center">
<a href=".github/CONTRIBUTING.md"><b>📖 Full Contributing Guide</b></a>&ensp;·&ensp;
<a href="GSSOC_GUIDE.md"><b>GSSoC Guide</b></a>&ensp;·&ensp;
<a href="https://github.com/im-anishraj/arnio/issues"><b>🐛 Open Issues</b></a>&ensp;·&ensp;
<a href="https://github.com/im-anishraj/arnio/discussions"><b>💬 Discussions</b></a>
</p>

<br>

---

<br>

## 📐 Project structure

```text
arnio/
├── cpp/
│   ├── include/arnio/      # C++ headers — types, column, frame, csv_reader, cleaning
│   └── src/                 # C++ implementations (~30 KB of compiled logic)
├── bindings/
│   └── bind_arnio.cpp       # pybind11 module — the Python↔C++ bridge
├── arnio/
│   ├── __init__.py          # Public API surface
│   ├── io.py                # read_csv, scan_csv
│   ├── cleaning.py          # Python wrappers for C++ cleaning functions
│   ├── pipeline.py          # Step registry + pipeline executor
│   ├── convert.py           # to_pandas (zero-copy), from_pandas
│   ├── frame.py             # ArFrame — lightweight C++ Frame wrapper
│   └── exceptions.py        # ArnioError, UnknownStepError, CsvReadError, TypeCastError
├── tests/                   # pytest suite — CSV, cleaning, pipeline, conversions
├── benchmarks/              # Reproducible arnio vs pandas benchmark
├── examples/                # basic_usage.py, custom_step.py
└── website/                 # Project website — arnio.vercel.app
```

<br>

---

<br>

<div align="center">

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="final-icon-dark.svg">
  <img alt="Arnio" src="final-icon-light.svg" width="80">
</picture>

<br><br>

**Stop writing cleaning scripts. Declare clean data.**

<br>

<a href="https://pypi.org/project/arnio/"><img src="https://img.shields.io/pypi/dm/arnio?style=flat-square&logo=pypi&logoColor=white&labelColor=0d1117&color=3572A5&label=installs" alt="Downloads"></a>&ensp;
<a href="https://github.com/im-anishraj/arnio/stargazers"><img src="https://img.shields.io/github/stars/im-anishraj/arnio?style=flat-square&logo=github&labelColor=0d1117&color=e3b341&label=stars" alt="Stars"></a>&ensp;
<a href="https://github.com/im-anishraj/arnio/network/members"><img src="https://img.shields.io/github/forks/im-anishraj/arnio?style=flat-square&logo=github&labelColor=0d1117&color=8b949e&label=forks" alt="Forks"></a>&ensp;
<a href="https://arnio.vercel.app/"><img src="https://img.shields.io/badge/website-arnio.vercel.app-blue?style=flat-square&labelColor=0d1117" alt="Website"></a>

<br>

<sub>Built with C++ and pybind11 · Licensed under MIT · Maintained by <a href="https://github.com/im-anishraj">@im-anishraj</a></sub>

</div>
