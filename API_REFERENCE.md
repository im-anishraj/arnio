# Arnio API Reference

A guide to the classes and functions within the **Arnio** library.

---

## Arnio API Reference Index

| Category | Components |
| :--- | :--- |
| **Core Class** | [**`ArFrame`**](#arframe)  |
| **I/O** | [`read_csv`](#read_csv) • [`scan_csv`](#scan_csv) |
| **Cleaning** | [`cast_types`](#cast_types) • [`clean`](#clean) • [`clip_numeric`](#clip_numeric) • [`drop_constant_columns`](#drop_constant_columns) • [`drop_duplicates`](#drop_duplicates) • [`drop_nulls`](#drop_nulls) • [`fill_nulls`](#fill_nulls) • [`filter_rows`](#filter_rows) • [`normalize_case`](#normalize_case) • [`rename_columns`](#rename_columns) • [`round_numeric_columns`](#round_numeric_columns) • [`safe_divide_columns`](#safe_divide_columns) • [`strip_whitespace`](#strip_whitespace) |
| **Conversion** | [`from_pandas`](#from_pandas) • [`to_pandas`](#to_pandas) |
| **Pipeline** | [`pipeline`](#pipeline) • [`register_step`](#register_step) |
| **Data Quality** | [`profile`](#profile) • [`suggest_cleaning`](#suggest_cleaning) • [`auto_clean`](#auto_clean) • [`DataQualityReport`](#dataqualityreport) • [`ColumnProfile`](#columnprofile) |
| **Schema Validation** | [`Schema`](#schema) • [`Field`](#field) • [`validate`](#validate) • [`ValidationResult`](#validationresult) • [`ValidationIssue`](#validationissue) • [`Int64`](#int64) • [`Float64`](#float64) • [`String`](#string) • [`Bool`](#bool) • [`Email`](#email) • [`URL`](#url) |
| **Custom Exceptions** | [`ArnioError`](#arnioerror) • [`CsvReadError`](#csvreaderror) • [`TypeCastError`](#typecasterror) • [`UnknownStepError`](#unknownsteperror) |

---

## Documentation Details

## Core Class

### ArFrame
The `ArFrame` is the central data structure in Arnio. It acts as a lightweight, columnar container that wraps high-performance C++ logic, allowing for fast data manipulation within Python.

#### Usage Example
The following example demonstrates how to inspect an `ArFrame` after loading data.

```python
df = arnio.read_csv("data.csv")

# Inspecting properties
print(f"Dataset Shape: {df.shape}")
print(f"Column Names: {df.columns}")
print(f"Data Types: {df.dtypes}")
print(f"Memory: {df.memory_usage()} bytes")
```
## I/O (Input/Output)

#### Functions for reading and inspecting data files using the high-performance C++ backend.
---

### read_csv
Loads a CSV, TSV, or TXT file into an `ArFrame`.

```python
# Reading specific columns from a tab-separated file
df = ar.read_csv("data.tsv", delimiter="\t", usecols=["Name", "Age"])
```
---

### scan_csv
Retrieves the **Schema** (column names and data types) of a file without loading the actual data into memory. This is highly efficient for large files where you only need to check the data structure.

```python
schema = arnio.scan_csv("large_dataset.csv")
```

---

## Cleaning

Standard functions for tidying datasets and fixing structural inconsistencies.

---

### <a name="cast_types"></a>cast_types()
Converts specific columns to a new data type using a mapping dictionary.
```python
df = arnio.cast_types(df, {"score": "float64"})
```

### <a name="clean"></a>clean()
A high-level wrapper that applies `strip_whitespace`, `drop_nulls`, and `drop_duplicates` in a single call. This is the fastest way to perform basic data hygiene.
```python
df = arnio.clean(df)
```
### <a name="clip_numeric"></a>clip_numeric()
Clip numeric values to lower and/or upper bounds
```python
df = arnio.clip_numeric(df, lower=0, upper=100)
```

### <a name="drop_constant_columns"></a>drop_constant_columns()
Removes columns with only one unique value.
```python
df = arnio.drop_constant_columns(df)
```

### <a name="drop_duplicates"></a>drop_duplicates()
Removes identical rows from the dataset.
* **Options:** Use `keep="first"` or `"last"`. Set `keep=False` to remove all instances of a duplicate.
```python
df = arnio.drop_duplicates(df, keep="first")
```

### <a name="drop_nulls"></a>drop_nulls()
Deletes rows containing empty or "Null" values. You can provide a `subset` list to only check specific columns.
```python
df = arnio.drop_nulls(df, subset=["email"])
```

### <a name="fill_nulls"></a>fill_nulls()
Replaces empty spots in your data with a fixed value (e.g., replacing missing scores with `0`).
```python
df = arnio.fill_nulls(df, value=0, subset=["score"])
```

### <a name="filter_rows"></a>filter_rows()
Selects rows based on a mathematical condition.
* **Supported Operators:** `>`, `<`, `>=`, `<=`, `==`, `!=`.
```python
clean_df = arnio.filter_rows(df, "score", ">", 50.0)
```

### <a name="normalize_case"></a>normalize_case()
Adjusts text casing for consistency. Options include `"lower"`, `"upper"`, or `"title"`.
```python
df = arnio.normalize_case(df, column="city", mode="upper")
```

### <a name="rename_columns"></a>rename_columns()
Changes the names of your headers. Requires a dictionary: `{"old_name": "new_name"}`.
```python
df = arnio.rename_columns(df, {"USER_ID": "user_id"})
```

### <a name="round_numeric_columns"></a>round_numeric_columns()
Round numeric columns (non-numeric columns in subset ignored safely)
```python
df = arnio.round_numeric_columns(df, decimals=2)
```

### <a name="safe_divide_columns"></a>safe_divide_columns()
Divide one column by another, handles zero/null denominators.
```python
df = arnio.safe_divide_columns(df, "total_cost", "quantity", target="unit_price")
```

### <a name="strip_whitespace"></a>strip_whitespace()
Trims extra spaces from the beginning and end of text entries.
* **Note:** This is often the first step in cleaning raw CSV data.
```python
df = arnio.strip_whitespace(df)
```

---

## Conversion

Functions for interchanging data between Arnio and the **Pandas** library. This ensures compatibility with other data science tools.

---

### <a name="from_pandas"></a>from_pandas()
Converts a `pandas.DataFrame` into an Arnio `ArFrame`.

### <a name="to_pandas"></a>to_pandas()
Converts an `ArFrame` into a `pandas.DataFrame`

---

#### Usage Example:
```python
pdf = pd.DataFrame(data)

af = arnio.from_pandas(pdf)
df = arnio.to_pandas(af)
```

---

## Pipeline

The Pipeline module allows you to chain multiple cleaning operations into a single, automated execution flow.

---

### <a name="pipeline"></a>pipeline()
Applies a sequence of cleaning steps to an `ArFrame`.

```python
steps = [
    {"step": "strip_whitespace"},
    {"step": "drop_nulls", "subset": ["email"]},
    {"step": "normalize_case", "column": "city", "mode": "upper"}
]
df = arnio.pipeline(df, steps)
```

### <a name="register_step"></a>register_step()
Extends the pipeline by adding your own custom Python functions.

```python
def custom_func(df, column):
    pass
arnio.register_step("custom_func", custom_func)
```

---

## Data Quality

Tools for inspecting the "health" of your dataset and automatically fixing common inconsistencies.

---

### <a name="profile"></a>profile()
Analyzes an `ArFrame` and returns a comprehensive `DataQualityReport`.

### <a name="suggest_cleaning"></a>suggest_cleaning()
Examines a report or frame and returns a list of recommended cleaning steps.

### <a name="auto_clean"></a>auto_clean()
The "one-click" fix for data issues. It profiles the data and immediately applies repairs.

### <a name="dataqualityreport"></a>DataQualityReport
A full summary of the dataset's health.

### <a name="columnprofile"></a>ColumnProfile
A detailed health check for a single column.

---

#### Usage Example: Automatic Cleanup
```python
report = arnio.profile(df)
print(report.summary())

clean_df = arnio.auto_clean(df, mode="strict")
```

---

## Schema Validation

Schema validation allows you to define "Data Contracts". It ensures that your dataset follows strict rules before you use it for analysis.

---

#### <a name="schema"></a>Schema
The top-level container for your validation rules.

---

#### <a name="field"></a>Field
Defines the specific constraints for a single column.

---

#### <a name="validate"></a>validate
The primary function used to check an `ArFrame` against a `Schema`. It returns a `ValidationResult`.

---

#### <a name="validationresult"></a>ValidationResult / <a name="validationissue"></a>ValidationIssue
The objects returned after calling `validate()`. They provide details on whether the data passed or failed.

---

#### Field Type Helpers
Arnio provides shortcut functions to create specific types of fields quickly. Each helper maps to a specific data type rule.

| Function | Description |
| :--- | :--- |
| <a name="int64"></a>**Int64** | Validates whole numbers. Supports `min`, `max`, and `unique`. |
| <a name="float64"></a>**Float64** | Validates decimal numbers. Supports `min`, `max`, and `unique`. |
| <a name="string"></a>**String** | Validates text. Supports `pattern`, `min_length`, and `max_length`. |
| <a name="bool"></a>**Bool** | Validates True/False boolean values. |
| <a name="email"></a>**Email** | Specialized String validator for email formats. |
| <a name="url"></a>**URL** | Specialized String validator for web links. |

---

### Usage Example:
```python
user_schema = arnio.Schema({
    "user_id": arnio.Int64(unique=True, nullable=False),
    "email": arnio.Email(nullable=False),
    "age": arnio.Int64(min=18, max=100)
})

df = arnio.read_csv("users.csv")
result = arnio.validate(df, user_schema)
```
---

## Custom Exceptions

These custom exceptions help you identify exactly where a data processing task failed.

---

| Error Name | Meaning |
| :--- | :--- |
| <a name="arnioerror"></a>[**ArnioError**](#arnioerror) | Base exception for all Arnio errors. |
| <a name="csvreaderror"></a>[**CsvReadError**](#csvreaderror) | Triggered when a CSV file cannot be read. |
| <a name="typecasterror"></a>[**TypeCastError**](#typecasterror) | Raised when cast_types encounters an incompatible type. |
| <a name="unknownsteperror"></a>[**UnknownStepError**](#unknownsteperror) | Triggered when a pipeline step name is not registered|

---