# Arnio API Reference

A guide to the classes and functions within the **Arnio** library.

---

## Arnio API Reference Index

| Category | Components |
| :--- | :--- |
| **Core Class** | [**`ArFrame`**](#arframe) • Properties: [`shape`](#shape), [`columns`](#columns), [`dtypes`](#dtypes) • Methods: [`memory_usage`](#memory_usage), [`preview`](#preview), [`select_columns`](#select_columns) |
| **I/O** | [`read_csv`](#read_csv) • [`scan_csv`](#scan_csv) |
| **Cleaning** | [`cast_types`](#cast_types) • [`clean`](#clean) • [`clip_numeric`](#clip_numeric) • [`drop_constant_columns`](#drop_constant_columns) • [`drop_duplicates`](#drop_duplicates) • [`drop_nulls`](#drop_nulls) • [`fill_nulls`](#fill_nulls) • [`filter_rows`](#filter_rows) • [`normalize_case`](#normalize_case) • [`rename_columns`](#rename_columns) • [`round_numeric_columns`](#round_numeric_columns) • [`safe_divide_columns`](#safe_divide_columns) • [`strip_whitespace`](#strip_whitespace) • [`validate_columns_exist`](#validate_columns_exist)|
| **Conversion** | [`from_pandas`](#from_pandas) • [`to_pandas`](#to_pandas) |
| **Integration** | [`ArnioPandasAccessor`](#ArnioPandasAccessor) |
| **Pipeline** | [`pipeline`](#pipeline) • [`register_step`](#register_step) |
| **Data Quality** | [`profile`](#profile) • [`suggest_cleaning`](#suggest_cleaning) • [`auto_clean`](#auto_clean) • [`DataQualityReport`](#dataqualityreport) • [`ColumnProfile`](#columnprofile) |
| **Schema Validation** | [`Schema`](#schema) • [`Field`](#field) • [`validate`](#validate) • [`ValidationResult`](#validationresult) • [`ValidationIssue`](#validationissue) • [`Int64`](#int64) • [`Float64`](#float64) • [`String`](#string) • [`Bool`](#bool) • [`Email`](#email) • [`URL`](#url) |
| **Custom Exceptions** | [`ArnioError`](#arnioerror) • [`CsvReadError`](#csvreaderror) • [`TypeCastError`](#typecasterror) • [`UnknownStepError`](#unknownsteperror) |

---

## Documentation Details

## Core Class

### ArFrame
The `ArFrame` is the central data structure in Arnio. It acts as a lightweight, columnar container that wraps high-performance C++ logic, allowing for fast data manipulation within Python.

| Property | Type | Description |
| :--- | :--- | :--- |
| <a name="columns"></a>**columns** | `list[str]` | Returns the names of all columns in the dataset. |
| <a name="dtypes"></a>**dtypes** | `dict[str, str]` | A mapping of column names to their detected data types. |
| <a name="shape"></a>**shape** | `tuple[int, int]` | Returns a tuple representing the number of rows and columns `(rows, cols)`. |

#### Methods
| Method | Return Type | Description |
| :--- | :--- | :--- |
| <a name="memory_usage"></a>**memory_usage()** | `int` | Returns the total bytes consumed by the object in memory. |
| <a name="preview"></a>**preview()** | `str` | Return a lightweight string preview of the first ``n`` rows. |
| <a name="select_columns"></a>**select_columns()** | `ArFrame` | Return a new ArFrame with only the selected columns. |

#### Usage Example
The following example demonstrates how to inspect an `ArFrame` after loading data.

```python
df = arnio.read_csv("data.csv")

# Inspecting properties
print(f"Dataset Shape: {df.shape}")
print(f"Column Names: {df.columns}")
print(f"Data Types: {df.dtypes}")
print(f"Memory: {df.memory_usage()} bytes")
df_cols = df.select_columns(columns = ["id","name"])
print(df.preview())
```

---

## I/O (Input/Output)

Functions for reading and inspecting data files using the high-performance C++ backend.

---

### read_csv
Loads a CSV, TSV, or TXT file into an `ArFrame`.

```python
# Reading specific columns from a tab-separated file
df = arnio.read_csv("data.tsv", delimiter="\t", usecols=["Name", "Age"])
```
### scan_csv
Retrieves the **Schema** (column names and data types) of a file without loading the actual data into memory. This is highly efficient for large files where you only need to check the data structure.

```python
schema = arnio.scan_csv("large_dataset.csv")
```

---

## Cleaning

Standard functions for tidying datasets and fixing structural inconsistencies.

---

### cast_types
Converts specific columns to a new data type using a mapping dictionary.
```python
df = arnio.cast_types(df, {"score": "float64"})
```

### clean
A high-level wrapper that applies `strip_whitespace`, `drop_nulls`, and `drop_duplicates` in a single call. This is the fastest way to perform basic data cleaning.
```python
df = arnio.clean(df,drop_nulls=True)
```
### clip_numeric
Clip numeric values to lower and/or upper bounds
```python
df = arnio.clip_numeric(df, lower=0, upper=100)
```

### drop_constant_columns
Removes columns with only one unique value.
```python
df = arnio.drop_constant_columns(df)
```

### drop_duplicates
Removes identical rows from the dataset.
* **Options:** Use `keep="first"` or `"last"`. Set `keep=False` to remove all instances of a duplicate.
```python
df = arnio.drop_duplicates(df, keep="first")
```

### drop_nulls
Deletes rows containing empty or "Null" values. You can provide a `subset` list to only check specific columns.
```python
df = arnio.drop_nulls(df, subset=["email"])
```

### fill_nulls
Replaces empty spots in your data with a fixed value (e.g., replacing missing scores with `0`).
```python
df = arnio.fill_nulls(df, 0, subset=["score"])
```

### filter_rows
Selects rows based on a mathematical condition.
* **Supported Operators:** `>`, `<`, `>=`, `<=`, `==`, `!=`.
```python
clean_df = arnio.filter_rows(df,column="age", op=">", value=18)
```

### normalize_case
Adjusts text casing for consistency. Options include `"lower"`, `"upper"`, or `"title"`.
```python
df = arnio.normalize_case(df, case_type="title")
```

### rename_columns
Changes the names of your headers. Requires a dictionary: `{"old_name": "new_name"}`.
```python
df = arnio.rename_columns(df,{"old": "new"})
```

### round_numeric_columns
Round numeric columns (non-numeric columns in subset ignored safely)
```python
df = arnio.round_numeric_columns(df, decimals=2)
```

### safe_divide_columns
Divide one column by another, handles zero/null denominators.
```python
df = arnio.safe_divide_columns(df,numerator="revenue", denominator="cost", output_column="ratio")
```

### strip_whitespace
Trims extra spaces from the beginning and end of text entries.
* **Note:** This is often the first step in cleaning raw CSV data.
```python
df = arnio.strip_whitespace(df)
```

### validate_columns_exist
Fail early when required columns are missing.
```python
df = arnio.validate_columns_exist(df, ["age"])
```

---

## Conversion

Functions for interchanging data between Arnio and the **Pandas** library. This ensures compatibility with other data science tools.

---

### from_pandas()
Converts a `pandas.DataFrame` into an Arnio `ArFrame`.

### to_pandas()
Converts an `ArFrame` into a `pandas.DataFrame`

---

#### Usage Example:
```python
pdf = pd.DataFrame(data)

af = arnio.from_pandas(pdf)
df = arnio.to_pandas(af)
```

---

## Integration

### ArnioPandasAccessor
Run Arnio preparation helpers from an existing pandas DataFrame.

---

## Pipeline

The Pipeline module allows you to chain multiple cleaning operations into a single, automated execution flow.

---

### pipeline()
Applies a sequence of cleaning steps to an `ArFrame`.

```python
clean_df = arnio.pipeline(
        df,
        [
            ("strip_whitespace",),
            ("normalize_case", {"case_type": "title"}),
            ("fill_nulls", {"value": 0, "subset": ["age"]}),
            ("fill_nulls", {"value": "Unknown", "subset": ["city"]}),
            ("drop_duplicates",),
        ],
    )
```

### register_step()
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

### profile()
Analyzes an `ArFrame` and returns a comprehensive `DataQualityReport`.

### suggest_cleaning()
Examines a report or frame and returns a list of recommended cleaning steps.

### auto_clean()
The "one-click" fix for data issues. It profiles the data and immediately applies repairs.

### DataQualityReport
A full summary of the dataset's health.

### ColumnProfile
A detailed health check for a single column.

---

#### Usage Example: Automatic Cleanup
```python
report = arnio.profile(df)
summary = report.summary()
suggestions = arnio.suggest_cleaning(df)

safe = arnio.auto_clean(df)
print(arnio.to_pandas(safe))
```

---

## Schema Validation

Schema validation allows you to define "Data Contracts". It ensures that your dataset follows strict rules before you use it for analysis.

---

#### Schema
The top-level container for your validation rules.

#### Field
Defines the specific constraints for a single column.

#### validate
The primary function used to check an `ArFrame` against a `Schema`. It returns a `ValidationResult`.

#### ValidationResult / ValidationIssue
The objects returned after calling `validate()`. They provide details on whether the data passed or failed.

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
