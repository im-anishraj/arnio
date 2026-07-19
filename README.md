<div align="center">
<img src="assets/arnio_banner.png" alt="Arnio: Data trust for Python" width="800">

Validate, clean, and profile DataFrames before everything else.

[![PyPI](https://img.shields.io/pypi/v/arnio)](https://pypi.org/project/arnio/)
[![Python](https://img.shields.io/pypi/pyversions/arnio)](https://pypi.org/project/arnio/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

</div>

---

## What is Arnio?

Arnio is the data trust layer for Python. It answers one question:

> **"Is this data trustworthy?"**

It answers through three verbs: **validate**, **clean**, and **profile**.

Think of it as **Pydantic for DataFrames**.

## Install

```bash
pip install arnio
```

## Quick Start

```python
import arnio as ar
import pandas as pd

df = pd.DataFrame({
    "email": ["alice@example.com", "not-an-email", None],
    "age": [25, -5, 200],
    "name": ["Alice", "Bob", "Charlie"],
})

# Profile — instant data quality overview
report = ar.profile(df)
print(report.quality_score)  # 0–100

# Validate — check against a schema
schema = ar.Schema({
    "email": ar.Email(nullable=False),
    "age": ar.Int(min=0, max=150),
    "name": ar.String(min_length=1),
})
result = ar.validate(df, schema)
print(result.passed)   # False
print(result.issues)   # Structured list of issues

# Clean — declarative cleaning pipeline
cleaned = ar.clean(df, [
    "strip_whitespace",
    "drop_duplicates",
    ("normalize_case", {"case": "lower"}),
])

# Suggest — intelligent cleaning suggestions
suggestions = ar.suggest(df)
```

## Three Core Verbs

| Verb         | Function                  | Purpose                                      |
| ------------ | ------------------------- | -------------------------------------------- |
| **Validate** | `ar.validate(df, schema)` | Check if data matches a contract             |
| **Clean**    | `ar.clean(df, steps)`     | Apply declarative cleaning operations        |
| **Profile**  | `ar.profile(df)`          | Measure data quality with scores and metrics |

## Schema Definition

Two ways to define the same schema:

```python
# Dict-based (dynamic, config-driven)
schema = ar.Schema({
    "email": ar.Email(nullable=False),
    "age": ar.Int(min=0, max=150),
    "name": ar.String(min_length=1),
})

# Class-based (IDE-friendly, inheritable)
class Customers(ar.Schema):
    email = ar.Email(nullable=False)
    age = ar.Int(min=0, max=150)
    name = ar.String(min_length=1)
```

### Available Field Types

| Type             | Description                            |
| ---------------- | -------------------------------------- |
| `ar.Int`         | Integer with optional min/max          |
| `ar.Float`       | Float with optional min/max            |
| `ar.String`      | String with optional length/pattern    |
| `ar.Bool`        | Boolean                                |
| `ar.Date`        | Date string with format validation     |
| `ar.DateTime`    | DateTime string with format validation |
| `ar.Email`       | Email address                          |
| `ar.URL`         | HTTP/HTTPS URL                         |
| `ar.PhoneNumber` | Phone number                           |
| `ar.IPAddress`   | IPv4 or IPv6 address                   |
| `ar.UUID`        | UUID string                            |
| `ar.Regex`       | Custom regex pattern                   |

## Cleaning Pipeline

```python
# One-shot cleaning
cleaned = ar.clean(df, [
    "strip_whitespace",
    "drop_duplicates",
    ("fill_nulls", {"column": "category", "value": "unknown"}),
    "slugify_column_names",
])

# Reusable pipeline
pipe = ar.Pipeline([
    "strip_whitespace",
    "drop_duplicates",
    ("normalize_case", {"case": "lower"}),
])
cleaned = pipe.run(df)

# Save/load for version control
yaml_str = pipe.to_yaml()
pipe = ar.Pipeline.from_yaml(yaml_str)
```

## Quality Gates (CI/CD)

```python
# In a test file or CI script
ar.check(df, schema)  # Raises ar.ValidationError on failure
```

## pandas Accessor

```python
import arnio  # Registers the accessor

df.arnio.profile()
df.arnio.validate(schema)
df.arnio.clean(["strip_whitespace"])
df.arnio.suggest()
df.arnio.is_valid(schema)  # Returns bool
```

## Works With

- **pandas** DataFrames (primary)
- **dict** / **list of dicts** (no pandas import needed for simple cases)
- **Polars** DataFrames (v2.1)

## What Arnio Does NOT Do

Arnio stays in its lane. It does not:

- Query or filter data (use pandas/Polars)
- Perform analytics (use pandas/Polars/DuckDB)
- Do feature engineering (use scikit-learn)
- Create visualizations (use matplotlib/Plotly)
- Manage file formats (use PyArrow)

## License

[MIT](LICENSE) — Anish Raj
