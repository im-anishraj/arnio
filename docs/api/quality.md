# Data Quality — `arnio.quality`

Data quality profiling, cleaning suggestions, and automatic cleaning.

## `profile`

```python
arnio.profile(frame, *, sample_size=5) -> DataQualityReport
```

Profile data quality for an `ArFrame`. Returns a comprehensive report with null counts, uniqueness, basic stats, semantic hints, and safe cleaning suggestions.

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `frame` | `ArFrame` | *required* | Input frame to inspect. |
| `sample_size` | `int` | `5` | Number of non-null sample values per column. |

### Returns

`DataQualityReport` — Full quality report.

### Example

```python
import arnio as ar

frame = ar.read_csv("raw.csv")
report = ar.profile(frame)

# Access summary
print(report.summary())

# Check specific columns
for name, col in report.columns.items():
    print(f"{name}: {col.null_count} nulls, {col.unique_count} unique")
    if col.warnings:
        print(f"  Warnings: {col.warnings}")
```

---

## `suggest_cleaning`

```python
arnio.suggest_cleaning(frame_or_report) -> list[tuple[str, dict]]
```

Suggest safe built-in cleaning steps. Returns pipeline-compatible step tuples.

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `frame_or_report` | `ArFrame \| DataQualityReport` | *required* | Frame to profile or existing report. |

### Returns

`list[tuple[str, dict]]` — Pipeline-compatible cleaning suggestions.

### Example

```python
suggestions = ar.suggest_cleaning(frame)
# [("strip_whitespace", {"subset": ["name"]}), ("drop_duplicates", {"keep": "first"})]

# Apply suggestions directly
clean = ar.pipeline(frame, suggestions)
```

---

## `auto_clean`

```python
arnio.auto_clean(frame, *, mode="safe", return_report=False) -> ArFrame | tuple[ArFrame, DataQualityReport]
```

Apply built-in automatic cleaning based on data quality profiling.

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `frame` | `ArFrame` | *required* | Input frame. |
| `mode` | `str` | `"safe"` | `"safe"` applies only low-risk cleanup (whitespace). `"strict"` also applies casts and duplicate removal. |
| `return_report` | `bool` | `False` | Whether to return the pre-cleaning quality report. |

### Returns

- `ArFrame` if `return_report=False`
- `tuple[ArFrame, DataQualityReport]` if `return_report=True`

### Example

```python
import arnio as ar

# Safe mode (default) - only whitespace trimming
clean = ar.auto_clean(frame)

# Strict mode - full auto-cleaning
clean, report = ar.auto_clean(frame, mode="strict", return_report=True)
print(f"Cleaned {report.issue_count} issues")
```

---

## `DataQualityReport`

| Property/Method | Type | Description |
|----------------|------|-------------|
| `row_count` | `int` | Total rows. |
| `column_count` | `int` | Total columns. |
| `memory_usage` | `int` | Memory usage in bytes. |
| `duplicate_rows` | `int` | Number of duplicate rows. |
| `duplicate_ratio` | `float` | Ratio of duplicates. |
| `columns` | `dict[str, ColumnProfile]` | Per-column profiles. |
| `suggestions` | `list[tuple]` | Suggested cleaning steps. |
| `to_dict()` | `dict` | JSON-friendly representation. |
| `summary()` | `dict` | Compact summary. |
| `to_pandas()` | `pd.DataFrame` | One row per column. |

## `ColumnProfile`

| Field | Type | Description |
|-------|------|-------------|
| `name` | `str` | Column name. |
| `dtype` | `str` | Detected dtype. |
| `semantic_type` | `str` | Semantic category: `"email"`, `"url"`, `"numeric"`, `"categorical"`, etc. |
| `row_count` | `int` | Total rows. |
| `null_count` | `int` | Null count. |
| `null_ratio` | `float` | Null ratio (0.0–1.0). |
| `unique_count` | `int` | Unique value count. |
| `unique_ratio` | `float` | Unique ratio. |
| `empty_string_count` | `int` | Empty string count. |
| `whitespace_count` | `int` | Leading/trailing whitespace count. |
| `suggested_dtype` | `str \| None` | Suggested alternative dtype. |
| `min` / `max` / `mean` | `Any` | Basic stats (numeric columns). |
| `sample_values` | `list` | Sample non-null values. |
| `warnings` | `list[str]` | Warnings like `"contains_nulls"`, `"leading_or_trailing_whitespace"`. |
