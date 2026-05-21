# Arnio API Reference

A technical reference guide to the public classes and functions within the **Arnio** library.

## Arnio API Reference Index

| Category              | Components                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| :-------------------- | :-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Core Class**        | [**`ArFrame`**](#arframe) � Properties: [`shape`](#shape), [`columns`](#columns), [`dtypes`](#dtypes) � [`is_empty`](#is_empty) � Methods: [`memory_usage`](#memory_usage), [`preview`](#preview), [`select_columns`](#select_columns), [`select_dtypes`](#select_dtypes)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| **I/O**               | [`read_csv`](#read_csv) � [`scan_csv`](#scan_csv) � [`write_csv`](#write_csv) � [`sniff_delimiter`](#sniff_delimiter)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| **Cleaning**          | [`cast_types`](#cast_types) � [`clean`](#clean) � [`clip_numeric`](#clip_numeric) � [`combine_columns`](#combine_columns) � [`drop_columns`](#drop_columns) � [`drop_constant_columns`](#drop_constant_columns) � [`drop_duplicates`](#drop_duplicates) � [`drop_nulls`](#drop_nulls) � [`fill_nulls`](#fill_nulls) � [`filter_rows`](#filter_rows) � [`keep_rows_with_nulls`](#keep_rows_with_nulls) � [`normalize_case`](#normalize_case) � [`normalize_unicode`](#normalize_unicode) � [`rename_columns`](#rename_columns) � [`replace_values`](#replace_values) � [`round_numeric_columns`](#round_numeric_columns) � [`safe_divide_columns`](#safe_divide_columns) � [`strip_whitespace`](#strip_whitespace) � [`trim_column_names`](#trim_column_names) � [`validate_columns_exist`](#validate_columns_exist) |
| **Conversion**        | [`from_pandas`](#from_pandas) � [`to_pandas`](#to_pandas)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| **Integration**       | [`ArnioPandasAccessor`](#arniopandasaccessor)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| **Pipeline**          | [`pipeline`](#pipeline) � [`register_step`](#register_step)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| **Data Quality**      | [`profile`](#profile) • [`suggest_cleaning`](#suggest_cleaning) • [`auto_clean`](#auto_clean) • [`check_quality_gates`](#check_quality_gates) • [`DataQualityReport`](#dataqualityreport) • [`ColumnProfile`](#columnprofile)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| **Schema Validation** | [`Schema`](#schema) • [`Field`](#field) • [`validate`](#validate) • [`ValidationResult`](#validationresult) • [`ValidationIssue`](#validationissue) • [`Int64`](#int64) • [`Float64`](#float64) • [`String`](#string) • [`Bool`](#bool) • [`Email`](#email) • [`URL`](#url) • [`CountryCode`](#countrycode) • [`DateTime`](#datetime)                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| **Custom Exceptions** | [`ArnioError`](#arnioerror) • [`CsvReadError`](#csvreaderror) • [`TypeCastError`](#typecasterror) • [`UnknownStepError`](#unknownsteperror)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |

---

## Prerequisites

```python
import arnio as ar

df = ar.read_csv("data.csv")
```

### ArFrame

| Property                            | Return Type       |
| :---------------------------------- | :---------------- |
| <a name="columns"></a>**columns**   | `list[str]`       |
| <a name="dtypes"></a>**dtypes**     | `dict[str, str]`  |
| <a name="shape"></a>**shape**       | `tuple[int, int]` |
| <a name="is_empty"></a>**is_empty** | `bool`            |

| Method                                            | Return Type                  |
| :------------------------------------------------ | :--------------------------- |
| <a name="memory_usage"></a>**memory_usage()**     | `int`                        |
| <a name="preview"></a>**preview()**               | `str`                        |
| <a name="select_columns"></a>**select_columns()** | `ArFrame`                    |
| <a name="select_dtypes"></a>**select_dtypes()**   | `ArFrame`                    |
| <a name="describe"></a>**describe()**             | `dict[str, dict[str, float]]`|

```python
print(f"Column Names: {df.columns}")
print(f"Data Types: {df.dtypes}")
print(f"Dataset Shape: {df.shape}")
print(f"Memory: {df.memory_usage()} bytes")
print(df.preview())
df = df.select_columns(columns=["id", "name"])
df = df.select_dtypes(include=["int64", "float64"])
print(df.describe())
```

---

### read_csv

Loads a CSV, TSV, or TXT file into an `ArFrame`.

```python
df = ar.read_csv("data.csv")
```

### scan_csv

Return schema (column names + inferred types) without loading data.

```python
schema = ar.scan_csv("large_dataset.csv")
```

### write_csv

Writes an `ArFrame` to a CSV file via the C++ backend.

```python
ar.write_csv(frame, "output.csv")
```

#### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `frame` | `ArFrame` | required | The data frame to write |
| `path` | `str \| os.PathLike[str]` | required | Destination file path. Supports `.csv`, `.txt`, `.tsv` |
| `delimiter` | `str` | `","` | Single character field separator |
| `write_header` | `bool` | `True` | Whether to write the column header row |
| `line_terminator` | `str` | `"\n"` | Line terminator between rows |

#### Raises

| Error | When |
|-------|------|
| `ValueError` | File extension is not `.csv`, `.txt`, or `.tsv` |
| `ValueError` | `delimiter` is not exactly one character |
| `RuntimeError` | File cannot be opened or written |

#### Examples

```python
# Default comma-separated
ar.write_csv(frame, "output.csv")

# Tab-separated
ar.write_csv(frame, "output.tsv", delimiter="\t")

# Without header row
ar.write_csv(frame, "output.csv", write_header=False)

# Windows line endings
ar.write_csv(frame, "output.csv", line_terminator="\r\n")
```

### sniff_delimiter

Sniffs and returns the field delimiter character from a CSV file.

```python
delimiter = ar.sniff_delimiter("data.csv")
```

#### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `path` | `str \| os.PathLike[str]` | required | Path to the CSV file |
| `encoding` | `str` | `"utf-8"` | File encoding |
| `sample_size` | `int` | `2048` | Number of bytes to sample from the start of the file for sniffing |

#### Returns

`str`
The detected delimiter (one of `","`, `";"`, `"\t"`, `"|"`).

#### Raises

| Error | When |
|-------|------|
| `TypeError` | `encoding` is not a string, or `sample_size` is not an integer |
| `ValueError` | `sample_size` is <= 0, the encoding is unknown, or the delimiter is ambiguous / tied |
| `CsvReadError` | The file is empty, or contains binary data (NUL bytes) |
| `FileNotFoundError` | The file does not exist |

#### Examples

```python
# Sniff comma-separated file
delim = ar.sniff_delimiter("comma.csv")  # returns ","

# Sniff semicolon-separated file with custom sample size
delim = ar.sniff_delimiter("semicolon.csv", sample_size=1024)  # returns ";"
```

---

### cast_types

Converts specific columns to a new data type using a mapping dictionary.

```python
df = ar.cast_types(df, {"id": "float64"})
```

### clean

A high-level wrapper that applies `strip_whitespace`, `drop_nulls`, and `drop_duplicates` in a single call.

```python
df = ar.clean(df)
```

### clip_numeric

Clip numeric values to lower and/or upper bounds.

```python
df = ar.clip_numeric(df, lower=0, upper=100)
```

### combine_columns

Combine multiple columns into a single output column.

```python
df = ar.combine_columns(df, separator=",", output_column="combined_col")
```

### drop_constant_columns

Removes columns with only one unique value.

```python
df = ar.drop_constant_columns(df)
```

### drop_columns

Removes the requested columns while preserving the order of the remaining ones.

```python
frame = ar.drop_columns(frame, ["debug_col"])
```

### drop_duplicates

Removes identical rows from the dataset.

```python
df = ar.drop_duplicates(df, keep="first")
```

### drop_nulls

Excludes rows containing empty or null fields

```python
df = ar.drop_nulls(df, subset=["email"])
```

### fill_nulls

Replaces null entry values with a designated static value.

```python
df = ar.fill_nulls(df, 0, subset=["score"])
```

### filter_rows

Subsets rows matching an evaluation operator constraint.

```python
df = ar.filter_rows(df, column="age", op=">", value=18)
```

### keep_rows_with_nulls

Keep only rows that contain at least one null/empty value.

```python
df = ar.keep_rows_with_nulls(df)
```

### normalize_case

Adjusts text casing for consistency.

```python
df = ar.normalize_case(df, case_type="title")
```

### normalize_unicode

Normalize Unicode text columns.

```python
df = ar.normalize_unicode(df, subset=["uni_col"], form="NFC")
```

### rename_columns

Modifies headers using a translation dictionary mapping old names to new names.

```python
df = ar.rename_columns(df, {"old": "new"})
```

### replace_values

Replace values based on a mapping dict.

```python
df = ar.replace_values(df, {"old_value": "new_value"}, column="name")
```

### round_numeric_columns

Round numeric columns.

```python
df = ar.round_numeric_columns(df, decimals=2)
```

### safe_divide_columns

Divide one column by another.

```python
df = ar.safe_divide_columns(
    df,
    numerator="revenue",
    denominator="cost",
    output_column="ratio"
)
```

### strip_whitespace

Trims extra spaces from the beginning and end of text entries.

```python
df = ar.strip_whitespace(df)
```

### trim_column_names

Trims leading and trailing whitespace from column names.

```python
df = ar.trim_column_names(df)
```

### validate_columns_exist

Fail early when required columns are missing.

```python
df = ar.validate_columns_exist(df, ["age"])
```

---

### from_pandas

Converts a `pandas.DataFrame` into an Arnio `ArFrame`.

### to_pandas

Converts an `ArFrame` into a `pandas.DataFrame`

```python
import pandas as pd

pdf = pd.DataFrame(data)

af = ar.from_pandas(pdf)
df = ar.to_pandas(af)
```

---

### ArnioPandasAccessor

Run Arnio preparation helpers from an existing pandas DataFrame.

---

### pipeline

Apply a sequence of cleaning steps to an `ArFrame`.

```python
ops = [
    ("strip_whitespace",),
    ("normalize_case", {"case_type": "title"}),
    ("fill_nulls", {"value": 0, "subset": ["revenue"]}),
    ("fill_nulls", {"value": "Unknown", "subset": ["name"]}),
    ("drop_duplicates",),
]
df = ar.pipeline(df, ops)
```

```python
clean, metadata = ar.pipeline(df, ops, return_metadata=True)
print(metadata["step_timings"])
```

### register_step

Extend the pipeline by adding your own custom Python functions.

```python
def custom_func(df, column):
    pass

ar.register_step("custom_func", custom_func)
```

---

### profile

Analyze an `ArFrame` and get a structural `DataQualityReport`.

Key options:
- `sample_size`: number of non-null sample values stored per column.
- `approx_top_values`: enable approximate top values for high-cardinality string columns.
- `approx_top_values_min_unique`: minimum unique count to trigger approximation.
- `approx_top_values_min_ratio`: minimum unique ratio to trigger approximation.
- `approx_top_values_sample_size`: sample size for top-value estimation.

When `approx_top_values` is enabled, `top_values` counts/ratios are computed on
the sample, and `top_values_is_approximate`, `top_values_sample_count`, and
`top_values_sample_ratio` are included in each `ColumnProfile`.

### suggest_cleaning

Examine a report or frame and get a list of recommended cleaning steps.

### auto_clean

Profile the data and immediately apply repairs.

### check_quality_gates

Compare two `DataQualityReport` objects and return a pass/fail
`QualityGateResult` for CI or monitoring workflows.

```python
baseline = ar.profile(ar.read_csv("baseline.csv"))
current = ar.profile(ar.read_csv("current.csv"))

result = ar.check_quality_gates(
    baseline,
    current,
    max_row_count_delta_ratio=0.10,
    max_null_ratio_delta=0.05,
)

print(result.passed)
print(result.to_markdown())
```

### DataQualityReport

Summary of structural data quality metrics.

#### Methods:
* **`to_html(file_path: str | None = None) -> str`**: Generates a self-contained, offline-friendly, beautiful HTML dashboard report of your dataset's metrics, columns, and cleaning suggestions. Dynamically escapes all data values to prevent XSS. If `file_path` is provided, writes the HTML output to a file.
* **`to_markdown() -> str`**: Returns a GitHub-friendly markdown representation of the report.
* **`summary() -> dict`**: Returns a high-signal dictionary representation of the report metrics.

### ColumnProfile

Detailed health check for a single column.

```python
report = ar.profile(df)
summary = report.summary()
suggestions = ar.suggest_cleaning(df)

# Export the report as a beautiful, self-contained HTML file
html_report = report.to_html(file_path="quality_report.html")

safe = ar.auto_clean(df)
print(ar.to_pandas(safe))
```

---

#### Schema

The top-level container for validation rules.

#### Field

Defines the specific constraints for a single column.

#### validate

The primary function used to check an `ArFrame` against a `Schema`. It returns a `ValidationResult`.

#### <a name="validationresult"></a>ValidationResult / <a name="validationissue"></a>ValidationIssue

The objects returned after calling `validate()`.

**Row index convention:** `ValidationIssue.row_index` is **1-based** and refers to
data rows only — the CSV header is not counted. So `row_index=1` means the first
data row, `row_index=2` means the second, and so on.

```python
# CSV content:
# name,age        ← header (not counted)
# Alice,30        ← row 1
# Bob,-1          ← row 2  ← row_index=2 will appear here for a min violation

result = ar.validate(frame, {"age": ar.Int64(min=0)})
print(result.issues[0].row_index)  # 2
```

#### Field Type Helpers

Each helper maps to a specific data type rule.

| Function                                  | Description                                     |
| :---------------------------------------- | :---------------------------------------------- |
| <a name="int64"></a>**Int64**             | Validates whole numbers.                        |
| <a name="float64"></a>**Float64**         | Validates decimal numbers.                      |
| <a name="string"></a>**String**           | Validates text.                                 |
| <a name="bool"></a>**Bool**               | Validates True/False boolean values.            |
| <a name="email"></a>**Email**             | Specialized String validator for email formats. |
| <a name="url"></a>**URL**                 | Specialized String validator for web links.     |
| <a name="countrycode"></a>**CountryCode** | Validates uppercase ISO alpha-2 country-code.   |
| <a name="datetime"></a>**DateTime**       | Validates string timestamps.                    |

---

```python
user_schema = ar.Schema({
    "id": ar.Int64(unique=True, nullable=False),
    "name": ar.String(nullable=False),
    "revenue": ar.Float64(min=180, max=1000)
})
result = ar.validate(df, user_schema)
```

---

### Custom Exceptions

| Error Name                                                               | Meaning                                                 |
| :----------------------------------------------------------------------- | :------------------------------------------------------ |
| <a name="arnioerror"></a>[**ArnioError**](#arnioerror)                   | Base exception for all Arnio errors.                    |
| <a name="csvreaderror"></a>[**CsvReadError**](#csvreaderror)             | Triggered when a CSV file cannot be read.               |
| <a name="typecasterror"></a>[**TypeCastError**](#typecasterror)          | Raised when cast_types encounters an incompatible type. |
| <a name="unknownsteperror"></a>[**UnknownStepError**](#unknownsteperror) | Triggered when a pipeline step name is not registered   |

---
