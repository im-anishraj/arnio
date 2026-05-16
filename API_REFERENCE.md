# Arnio API Reference

A technical reference guide to the public classes and functions within the **Arnio** library.

---

## Arnio API Reference Index

| Category | Components |
| :--- | :--- |
| **Core Class** | [**`ArFrame`**](#arframe) • Properties: [`shape`](#shape), [`columns`](#columns), [`dtypes`](#dtypes) • [`is_empty`](#is_empty) • Methods: [`memory_usage`](#memory_usage), [`preview`](#preview), [`select_columns`](#select_columns) |
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

### ArFrame
Columnar container wrapping C++ backend structures for execution in Python.

| Property | Type | Description |
| :--- | :--- | :--- |
| <a name="columns"></a>**columns** | `list[str]` | Returns the names of all columns in the dataset. |
| <a name="dtypes"></a>**dtypes** | `dict[str, str]` | A mapping of column names to their detected data types. |
| <a name="shape"></a>**shape** | `tuple[int, int]` | Returns a tuple representing the number of rows and columns `(rows, cols)`. |
| <a name="is_empty"></a>**is_empty** | `bool` | Check if frame has zero rows. |

| Method | Return Type | Description |
| :--- | :--- | :--- |
| <a name="memory_usage"></a>**memory_usage()** | `int` | Returns the total bytes consumed by the object in memory. |
| <a name="preview"></a>**preview()** | `str` | Return a lightweight string preview of the first ``n`` rows. |
| <a name="select_columns"></a>**select_columns()** | `ArFrame` | Return a new ArFrame with only the selected columns. |

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

### read_csv
Loads a CSV, TSV, or TXT file into an `ArFrame`.

```python
# Reading specific columns from a tab-separated file
df = arnio.read_csv("data.tsv", delimiter="\t", usecols=["Name", "Age"])
```
### scan_csv
Return schema (column names + inferred types) without loading data.

```python
schema = arnio.scan_csv("large_dataset.csv")
```

---

### cast_types
Converts specific columns to a new data type using a mapping dictionary.
```python
df = arnio.cast_types(df, {"score": "float64"})
```

### clean
A high-level wrapper that applies `strip_whitespace`, `drop_nulls`, and `drop_duplicates` in a single call.
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
Excludes rows containing empty or null fields
```python
df = arnio.drop_nulls(df, subset=["email"])
```

### fill_nulls
Replaces null entry values with a designated static value.
```python
df = arnio.fill_nulls(df, 0, subset=["score"])
```

### filter_rows
Subsets rows matching an evaluation operator constraint.
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
Modifies headers using a translation dictionary mapping old names to new names.
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

### from_pandas()
Converts a `pandas.DataFrame` into an Arnio `ArFrame`.

### to_pandas()
Converts an `ArFrame` into a `pandas.DataFrame`

```python
pdf = pd.DataFrame(data)

af = arnio.from_pandas(pdf)
df = arnio.to_pandas(af)
```

---

### ArnioPandasAccessor
Run Arnio preparation helpers from an existing pandas DataFrame.

---

### pipeline()
Applies a sequence of cleaning steps to an `ArFrame`.

```python
ops = [
    ("strip_whitespace",),
    ("normalize_case", {"case_type": "title"}),
    ("fill_nulls", {"value": 0, "subset": ["revenue"]}),
    ("fill_nulls", {"value": "Unknown", "subset": ["name"]}),
    ("drop_duplicates",),
]
clean_df = arnio.pipeline(df, ops)
```

### register_step()
Extends the pipeline by adding your own custom Python functions.

```python
def custom_func(df, column):
    pass
arnio.register_step("custom_func", custom_func)
```

---

### profile()
Analyzes an `ArFrame` and generates a structural `DataQualityReport`.

### suggest_cleaning()
Examines a report or frame and returns a list of recommended cleaning steps.

### auto_clean()
It profiles the data and immediately applies repairs.

### DataQualityReport
Summary of structural data quality metrics.

### ColumnProfile
A detailed health check for a single column.

```python
report = arnio.profile(df)
summary = report.summary()
suggestions = arnio.suggest_cleaning(df)

safe = arnio.auto_clean(df)
print(arnio.to_pandas(safe))
```

---

#### Schema
The top-level container for validation rules.

#### Field
Defines the specific constraints for a single column.

#### validate
The primary function used to check an `ArFrame` against a `Schema`. It returns a `ValidationResult`.

#### <a name="validationresult"></a>ValidationResult / <a name="validationissue"></a>ValidationIssue
The objects returned after calling `validate()`. They provide details on whether the data passed or failed.

#### Field Type Helpers
Shortcut functions to create specific types of fields quickly. Each helper maps to a specific data type rule.

| Function | Description |
| :--- | :--- |
| <a name="int64"></a>**Int64** | Validates whole numbers. Supports `min`, `max`, and `unique`. |
| <a name="float64"></a>**Float64** | Validates decimal numbers. Supports `min`, `max`, and `unique`. |
| <a name="string"></a>**String** | Validates text. Supports `pattern`, `min_length`, and `max_length`. |
| <a name="bool"></a>**Bool** | Validates True/False boolean values. |
| <a name="email"></a>**Email** | Specialized String validator for email formats. |
| <a name="url"></a>**URL** | Specialized String validator for web links. |

---

```python
user_schema = arnio.Schema({
    "id": arnio.Int64(unique=True, nullable=False),
    "name": arnio.String(nullable=False),
    "revenue": arnio.Float64(min=180, max=1000)
})
result = arnio.validate(df, user_schema)
```
---

### Custom Exceptions

| Error Name | Meaning |
| :--- | :--- |
| <a name="arnioerror"></a>[**ArnioError**](#arnioerror) | Base exception for all Arnio errors. |
| <a name="csvreaderror"></a>[**CsvReadError**](#csvreaderror) | Triggered when a CSV file cannot be read. |
| <a name="typecasterror"></a>[**TypeCastError**](#typecasterror) | Raised when cast_types encounters an incompatible type. |
| <a name="unknownsteperror"></a>[**UnknownStepError**](#unknownsteperror) | Triggered when a pipeline step name is not registered|

---
