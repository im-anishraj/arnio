<div align="center">

<br>

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="final-icon-dark.svg">
  <img alt="Arnio" src="final-icon-light.svg" width="280">
</picture>

<br><br>

### Fast data preparation for the Python data stack.

<br>

**Arnio** is a compiled C++ data preparation engine for messy CSV and pandas workflows.<br>
It parses, infers types, strips whitespace, deduplicates, validates, and profiles data —<br>
then hands clean results back to the tools you already use.<br>
Use Arnio _before_ and _alongside_ pandas, NumPy, scikit-learn, DuckDB, and Arrow.

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

Colab install smoke test: **[COLAB_SMOKE_TEST.md](COLAB_SMOKE_TEST.md)**

<br>

<a href="#-quickstart">Quickstart</a>&ensp;·&ensp;<a href="#-integrations">Integrations</a>&ensp;·&ensp;<a href="#-why-arnio-exists">Why Arnio</a>&ensp;·&ensp;<a href="#%EF%B8%8F-architecture">Architecture</a>&ensp;·&ensp;<a href="#-benchmarks">Benchmarks</a>&ensp;·&ensp;<a href="#-community">Community</a>&ensp;·&ensp;<a href="#-contribute">Contribute</a>

</div>

<br>

---

<br>

## ⚡ Quickstart

A simple workflow in just a few steps.

> New to Arnio? Start with the pandas workflow example below before exploring advanced pipelines.

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

# Use copy=True when you need defensive pandas-owned buffers
safe_df = ar.to_pandas(clean, copy=True)
```

Already have a pandas `DataFrame`? Use Arnio in-place in your existing pandas
workflow:

```python
import pandas as pd
import arnio as ar

df = pd.read_csv("messy_sales_data.csv")

clean_df = df.arnio.clean([
    ("strip_whitespace",),
    ("normalize_case", {"case_type": "lower"}),
    ("drop_duplicates",),
])

report = clean_df.arnio.profile()
```

### Select specific columns

Use `select_columns()` to create a new `ArFrame` with only the required columns before converting to pandas.

```python
selected = frame.select_columns(["name", "revenue"])

print(selected.columns)
# ['name', 'revenue']
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
<summary><b>👀 Preview rows without pandas conversion or full-column Python list materialization</b></summary>
<br>

`preview()` reads only the first `n` rows directly from the C++ frame — no pandas conversion triggered.

```python
frame = ar.read_csv("huge_file.csv")

print(frame.preview())      # first 5 rows (default)
print(frame.preview(n=10))  # first 10 rows
```

Raises `ValueError` for invalid `n` (zero, negative, or non-integer).
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

## 🔗 Integrations

Arnio is designed to make the rest of the Python data stack more productive,
not to replace it.

| Workflow | How Arnio helps |
|:---|:---|
| **pandas** | Clean, validate, and profile messy `DataFrame`s through `df.arnio`. |
| **NumPy** | Prepare typed numeric data before array/modeling workflows. |
| **scikit-learn** | Use Arnio cleaning as a preprocessing layer before model training. |
| **DuckDB / Arrow** | Validate and prepare data before analytics and columnar exchange. |
| **notebooks** | Inspect quality issues and cleaning suggestions before analysis. |

### Pandas accessor

```python
df = pd.read_csv("raw_customers.csv")

clean_df = df.arnio.clean(drop_duplicates=True)
quality = clean_df.arnio.profile()
validation = clean_df.arnio.validate({
    "email": ar.Email(nullable=False),
    "age": ar.Int64(nullable=True, min=0),
})
```

This keeps pandas as the analysis tool while Arnio handles the preparation,
quality, and validation layer.

> Product direction: **[PROJECT_DIRECTION.md](PROJECT_DIRECTION.md)**

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

**Arnio intercepts this entire pattern.** It moves the preparation layer into a predictable pipeline, accelerates supported operations in C++, and gives you clean data for pandas, NumPy, scikit-learn, DuckDB, or notebooks.

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
| **Zero-copy bridge** | `to_pandas()` exposes C++ memory directly via NumPy's buffer protocol where supported. Numeric columns preserve the fast zero-copy path by default, while `copy=True` requests defensive pandas-owned buffers. |
| **Step registry** | Pipeline steps map to C++ function pointers. Adding a new cleaning primitive is a single function + one registry entry. |

> Full architecture documentation: **[ARCHITECTURE.md](ARCHITECTURE.md)**

<br>

---

<br>

## 🏎️ Benchmarks

> **Reference environment**: Ubuntu, Python 3.12, synthetic messy CSV inputs.<br>
> **Reproduce**: `make benchmark` — generates deterministic tall and wide datasets and runs both engines.

To reproduce the published numbers from a fresh checkout:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -e .
python benchmarks/generate_data.py
python benchmarks/benchmark_vs_pandas.py
```

`benchmarks/generate_data.py` uses deterministic NumPy seeds, so every run creates the same `benchmarks/benchmark_1m.csv` tall input and `benchmarks/benchmark_wide.csv` wide input. The benchmark then executes three pandas runs and three arnio runs for each case, printing average wall-clock time from `time.perf_counter()` and peak Python allocation from `tracemalloc`. For cleaner comparisons, close other memory-heavy processes and run the script from the repository root after installing the same Python, pandas, NumPy, compiler, and arnio commit you want to compare.

Expected output format:

```text
Tall CSV (1,000,000 rows x 12 columns)
Metric                     pandas        arnio
────────────────────────────────────────────
Exec Time (avg)       4.73s         5.75s
Peak RAM               211MB         212MB
Speed: 0.8x | RAM: -1% reduction

Wide CSV (5,000 rows x 256 columns)
Metric                     pandas        arnio
────────────────────────────────────────────
Exec Time (avg)       ...s          ...s
Peak RAM              ...MB         ...MB
Speed: ...x | RAM: ...% reduction
```

Small differences are expected across CPUs, operating systems, compilers, Python builds, and pandas/NumPy versions. If you share benchmark results in an issue or PR, include your OS, Python version, CPU model, pandas/NumPy versions, arnio commit, and the full command output so maintainers can compare like for like.

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

### 🧠 Auto Clean Memory Benchmark

To measure the peak memory and execution time of the `auto_clean` pipeline using realistic dataset sizes:

```bash
python benchmarks/benchmark_auto_clean_memory.py --rows 100000
```

This script generates a reproducible synthetic dataset with mixed column types (strings, ints, floats, booleans, nulls, and duplicates) and measures:
- `ar.read_csv` performance
- `ar.auto_clean(mode="safe")` performance (low-risk cleanup like whitespace trimming)
- `ar.auto_clean(mode="strict")` performance (includes type casting and deduplication)

The dataset is regenerated deterministically unless `--reuse-file` is provided.
Each `auto_clean` benchmark run reloads the dataset to avoid mutation or caching effects between runs.

Options:
- `--repeat N` runs each operation multiple times and reports average (and min/max range).
- `--seed N` changes the deterministic dataset seed.
- `--reuse-file` reuses an existing dataset file instead of regenerating it.
- `--keep-file` keeps the generated CSV (otherwise it is removed at the end).

Expected output format:

```text
Operation                    Time(s)     Peak Py(MiB)
--------------------------------------------------------------------
ar.read_csv           0.042 (0.041-0.044)    4.52 (4.50-4.60)
ar.auto_clean(safe)   0.012 (0.011-0.013)    0.15 (0.14-0.16)
ar.auto_clean(strict) 0.035 (0.034-0.036)    1.20 (1.18-1.22)
--------------------------------------------------------------------
Total avg (Read+Strict)       0.077             4.52
```
<br>

---

<br>

## 🧰 Cleaning primitives

<<<<<<< HEAD
Most operations below run natively in C++. Currently, `filter_rows` and `replace_values` run via the Python (pandas) backend and may be optimized in C++ later.
=======
Every operation below runs natively in C++. No Python loops.
>>>>>>> 4c4832f (feat: add Date schema field)

| Primitive | What it does | Example |
|:---|:---|:---|
| `drop_nulls` | Remove rows with null/empty values | `ar.drop_nulls(frame, subset=["age"])` |
| `keep_rows_with_nulls` | Keep only rows that contain at least one null | `ar.keep_rows_with_nulls(frame, subset=["age"])` |
| `validate_columns_exist` | Fail early when required columns are missing | `ar.validate_columns_exist(frame, ["age"])` |
| `filter_rows` | Filter rows using comparison operators | `ar.filter_rows(frame, column="age", op=">", value=18)` |
| `fill_nulls` | Replace nulls with a scalar | `ar.fill_nulls(frame, 0, subset=["revenue"])` |
| `drop_duplicates` | Deduplicate rows (first/last/none) | `ar.drop_duplicates(frame, keep="first")` |
| `drop_constant_columns` | Remove columns with only one unique value | `ar.drop_constant_columns(frame)` |
| `clip_numeric` | Clip numeric values to lower and/or upper bounds | `ar.clip_numeric(frame, lower=0, upper=100)` |
| `strip_whitespace` | Trim leading/trailing spaces from strings | `ar.strip_whitespace(frame)` |
| `normalize_case` | Force lower/upper/title case | `ar.normalize_case(frame, case_type="title")` |
| `rename_columns` | Rename columns via mapping | `ar.rename_columns(frame, {"old": "new"})` |
| `cast_types` | Cast column types | `ar.cast_types(frame, {"age": "int64"})` |
| `round_numeric_columns` | Round numeric columns (non-numeric columns in subset ignored safely) | `ar.round_numeric_columns(frame, decimals=2)` |
| `replace_values` | Replace values using a mapping (column or whole-frame). Handles `None`/`NaN`. | `ar.replace_values(frame, {"active": "A", "inactive": "I"}, column="status")` |
| `clean` | Convenience shorthand | `ar.clean(frame, drop_nulls=True)` |
| `safe_divide_columns` | Divide one column by another, handling zero/null denominators | `ar.safe_divide_columns(frame, numerator="revenue", denominator="cost", output_column="ratio")` |
| `trim_column_names` | Strip leading/trailing whitespace from column names | `ar.trim_column_names(frame)` |

#### `ArFrame.select_dtypes` — type-based column selection

Returns a **new `ArFrame`** containing only the columns whose dtype matches the filter. Raises `ValueError` if no columns match.

```python
frame = ar.read_csv("data.csv")

# Keep only numeric columns
numeric = frame.select_dtypes(include=["int64", "float64"])

# Drop string columns
without_strings = frame.select_dtypes(exclude="string")
```

**Valid dtype strings:** `"int64"`, `"float64"`, `"string"`, `"bool"`, `"null"`

- At least one of `include` or `exclude` must be given — raises `ValueError` otherwise.
- `include` and `exclude` must not overlap — raises `ValueError` if they share a dtype.
- Unknown dtype strings raise `ValueError` with a list of valid options.
- Raises `ValueError` when no columns match (never returns an empty frame silently).
- Column order in the result always matches the original frame.

Or compose them all into a **pipeline**:

```python
clean = ar.pipeline(frame, [
    ("validate_columns_exist", {"columns": ["name", "city", "revenue"]}),
    ("strip_whitespace",),
    ("normalize_case", {"case_type": "lower"}),
    ("fill_nulls", {"value": "unknown", "subset": ["city"]}),
    ("drop_duplicates", {"keep": "first"}),
])
```

### 🔁 Replace values

Use `replace_values` to substitute values using a mapping. It works as a pipeline step (Python backend) and can operate on a single column or the whole frame when `column` is omitted. It also understands null semantics: using `None` (or `np.nan`) as a mapping key targets existing nulls, and mapping a value to `None` creates real nulls.

Column-specific example:

```python
clean = ar.pipeline(frame, [
    ("replace_values", {"mapping": {"active": "A", "inactive": "I"}, "column": "status"}),
])
```

Whole-frame example (no `column`):

```python
clean = ar.pipeline(frame, [
    ("replace_values", {"mapping": {None: "MISSING", "active": "A", "inactive": "I"}}),
])
```

Direct API:

```python
frame2 = ar.replace_values(frame, {"active": "A", "inactive": "I"})
```

### 🔎 Filter rows inside pipelines

Use `filter_rows` to keep only rows matching a condition.

```python
clean = ar.pipeline(frame, [
    ("filter_rows", {
        "column": "revenue",
        "op": ">=",
        "value": 1000
    }),
])
```

Supported operators:

- `>`
- `<`
- `>=`
- `<=`
- `==`
- `!=`

Works with:

- integers
- floats
- strings
- booleans

### 🔎 Isolate rows with null values

Use `keep_rows_with_nulls` to audit incomplete data — keep only rows that have at least one null.

```python
frame = ar.read_csv("data.csv")

# Keep all rows that have at least one null anywhere
nulls = ar.keep_rows_with_nulls(frame)

# Keep rows where specifically 'age' or 'score' is null
nulls = ar.keep_rows_with_nulls(frame, subset=["age", "score"])

# Works inside a pipeline too
result = ar.pipeline(frame, [
    ("keep_rows_with_nulls", {"subset": ["age"]}),
])
```

Useful for data auditing — inspect what's missing before deciding how to fill or drop.

<br>
### 🔢 Safe column division

Divide one column by another while handling division by zero and null denominators explicitly:

```python
result = ar.safe_divide_columns(
    frame,
    numerator="revenue",
    denominator="cost",
    output_column="ratio",
    fill_value=0.0,  # used when denominator is zero or null
)
```

> When the denominator is **zero or null**, the result is replaced with `fill_value` (default `0.0`) instead of raising an error or producing `NaN`/`Inf`.

---

<br>

## 📊 Pandas Dtype Support Matrix

This table helps users understand which pandas dtypes and workflows are fully supported, partially supported, unsupported, or planned.

If a dtype is partially supported, users may need conversion before processing. Unsupported dtypes should raise clear errors where applicable.

| Pandas Dtype | Support Status | Notes |
|---|---|---|
| `int64` | ✅ Supported | Fully supported with native C++ columnar storage |
| `float64` | ✅ Supported | Fully supported with zero-copy conversion where possible |
| `bool` | ✅ Supported | Native supported boolean type |
| `string` | ✅ Supported | Recommended over `object` dtype for text workflows |
| `datetime64[ns]` | ❌ Unsupported | No native datetime parsing or conversion support yet |
| `category` | ⚠️ Limited | Converted to string/object during processing |
| `object` (mixed columns) | ⚠️ Limited | Mixed object columns may coerce to string and reduce type inference reliability |
| nullable pandas dtypes (`Int64`, `boolean`) | ⚠️ Limited | Supported through pandas extension dtypes with null-mask handling |
| `timedelta64[ns]` | ❌ Unsupported | Not currently supported |

### Notes

- Numeric columns are optimized for zero-copy conversion between C++ and pandas where supported.
- Pass `copy=True` to `to_pandas()` when downstream pandas code needs defensive pandas-owned column buffers.
- Boolean conversion is already copied by the binding because `std::vector<bool>` cannot be exposed as a zero-copy NumPy buffer in the current implementation.
- Columns with null masks may require copies so pandas can apply nullable values safely.
- String columns require Python string object creation during `to_pandas()` conversion.
- Mixed `object` columns may reduce type inference accuracy and may require preprocessing.
- Unsupported dtypes should raise clear user-facing errors instead of silent failures.
> **Note:** pandas DataFrame indexes are currently not preserved during `from_pandas()` conversion. Converted frames receive a default `RangeIndex` when converted back via `to_pandas()`.

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
    # CountryCode expects uppercase ISO alpha-2 values, for example IN, US, GB.
    "country": ar.CountryCode(nullable=False),
    "username": ar.String(min_length=3, max_length=20),
    "revenue": ar.Float64(nullable=True, min=0),
    "created_at": ar.Date(nullable=False),
})

result = ar.validate(frame, schema)
if not result.passed:
    summary = result.summary()
    print(summary["issues_by_rule"])
    print(summary["issues_by_column"])
    print(summary["issues_by_column_and_rule"])
    print(result.to_pandas())
    print(result.to_markdown(max_issues=10))
```

`ValidationResult.to_markdown()` is useful in CI logs, GitHub comments, or data quality reports because it renders a compact validation summary plus a GitHub-friendly issue table.

For multi-column uniqueness (composite keys):

```python
schema = ar.Schema({
    "user_id": ar.Int64(nullable=False),
    "course_id": ar.Int64(nullable=False),
}, unique=["user_id", "course_id"])

result = ar.validate(frame, schema)
```
Severity counts are not included in `summary()` yet because `ValidationIssue` does not currently carry severity information.

Date fields use the `YYYY-MM-DD` format and reject invalid calendar dates.

For low-risk automatic cleanup:

```python
clean, report = ar.auto_clean(frame, mode="strict", return_report=True)
```

This is the layer pandas does not try to own: profiling, data contracts, row-level validation issues, and safe cleaning suggestions for messy incoming datasets.

<br>

---

Use this workflow when you receive a small messy dataset and want to inspect what Arnio will change before applying it.

```python
import arnio as ar
import pandas as pd

raw = pd.DataFrame(
    {
        "order_id": [1001, 1002, 1002, 1003, 1004],
        "customer": [" Ishan ", " Prasoon ", " Prasoon ", " Pranay ", " Dhruv "],
        "city": [" Paris ", "London", "London", " New York ", " Tokyo "],
    }
)

frame = ar.from_pandas(raw)

report = ar.profile(frame)
summary = report.summary()
print(summary)

suggestions = ar.suggest_cleaning(frame)
print(suggestions)
# [('strip_whitespace', {'subset': ['customer', 'city']}), ('drop_duplicates', {'keep': 'first'})]

safe = ar.auto_clean(frame)
strict = ar.auto_clean(frame, mode="strict")
```

Messy input:

| order_id | customer | city |
|:--|:--|:--|
| 1001 | ` Ishan ` | ` Paris ` |
| 1002 | ` Prasoon ` | `London` |
| 1002 | ` Prasoon ` | `London` |
| 1003 | ` Pranay ` | ` New York ` |
| 1004 | ` Dhruv ` | ` Tokyo ` |

Expected cleaned output with `mode="strict"`:

| order_id | customer | city |
|:--|:--|:--|
| 1001 | Ishan | Paris |
| 1002 | Prasoon | London |
| 1003 | Pranay | New York |
| 1004 | Dhruv | Tokyo |

`mode="safe"` only trims whitespace. Use `mode="strict"` when you also want deterministic built-in cleanup such as exact duplicate removal.

See [examples/auto_clean_tutorial.py](examples/auto_clean_tutorial.py) for a runnable version of this walkthrough.

<br>

## Data Quality Reports

Arnio provides detailed profiling for datasets via `ar.profile()`. To generate the report shown in these examples, the following code was used:

```python
import arnio as ar
import pandas as pd

# Sample dataset used for these examples
data = {
    "user_id": [101, 102, 103, 104],
    "email": ["test@arnio.ai", "invalid-email", None, "test@arnio.ai"],
    "score": [85.5, 90.0, None, 88.2]
}
df = ar.from_pandas(pd.DataFrame(data))
# Bounded profiling for large datasets (controls how many sample values are kept)
report = ar.profile(df, sample_size=5)
```

### 1. Terminal Representation (Simplified Example)
*A simplified view of the standard string representation of the report object:*

```text
DataQualityReport(
    row_count=4,
    column_count=3,
    memory_usage=733,
    duplicate_rows=0,
    columns={
        'user_id': ColumnProfile(dtype='int64', semantic_type='identifier', unique_count=4),
        'email': ColumnProfile(dtype='string', semantic_type='categorical', null_count=1, unique_ratio=0.666667),
        'score': ColumnProfile(dtype='float64', semantic_type='numeric', mean=87.9, min=85.5, max=90.0)
    }
)
```

### 2. JSON Format (Excerpts from .to_dict())
*Key fields from the structured JSON export for integration with APIs or dashboards:*

```json
{
  "row_count": 4,
  "column_count": 3,
  "memory_usage": 733,
  "duplicate_rows": 0,
  "duplicate_ratio": 0.0,
  "columns": {
    "user_id": {
      "dtype": "int64",
      "semantic_type": "identifier",
      "null_count": 0,
      "unique_ratio": 1.0
    },
    "email": {
      "dtype": "string",
      "semantic_type": "categorical",
      "null_count": 1,
      "unique_ratio": 0.666667,
      "warnings": ["contains_nulls"]
    },
    "score": {
      "dtype": "float64",
      "semantic_type": "numeric",
      "null_count": 1,
      "mean": 87.9,
      "min": 85.5,
      "max": 90.0,
      "warnings": ["contains_nulls"]
    }
  }
}
```

### 3. Example Summary Table
*A manually formatted Markdown table representing the core metrics:*

| Metric | Value |
| :--- | :--- |
| **Row Count** | 4 |
| **Column Count** | 3 |
| **Memory Usage** | 733 bytes |
| **Duplicates** | 0 (0.0%) |
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

### 💖 Contributors

Thanks to everyone who contributes to Arnio and helps improve the project.

- [View all contributors](https://github.com/im-anishraj/arnio/graphs/contributors)
- [Contribution Guide](.github/CONTRIBUTING.md)
- [GitHub Discussions](https://github.com/im-anishraj/arnio/discussions)

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
