# Arnio API Reference

A technical reference guide to the public classes and functions within the **Arnio** library.

## Arnio API Reference Index

| Category              | Components                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| :-------------------- | :-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Core Class**        | [**`ArFrame`**](#arframe) • Properties: [`shape`](#shape), [`columns`](#columns), [`dtypes`](#dtypes) • [`is_empty`](#is_empty) • Methods: [`memory_usage`](#memory_usage), [`preview`](#preview), [`select_columns`](#select_columns), [`select_dtypes`](#select_dtypes)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| **I/O**               | [`read_csv`](#read_csv) • [`scan_csv`](#scan_csv)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| **Cleaning**          | [`cast_types`](#cast_types) • [`clean`](#clean) • [`clip_numeric`](#clip_numeric) • [`combine_columns`](#combine_columns) • [`drop_constant_columns`](#drop_constant_columns) • [`drop_duplicates`](#drop_duplicates) • [`drop_nulls`](#drop_nulls) • [`fill_nulls`](#fill_nulls) • [`filter_rows`](#filter_rows) • [`keep_rows_with_nulls`](#keep_rows_with_nulls) • [`normalize_case`](#normalize_case) • [`normalize_unicode`](#normalize_unicode) • [`rename_columns`](#rename_columns) • [`replace_values`](#replace_values) • [`round_numeric_columns`](#round_numeric_columns) • [`safe_divide_columns`](#safe_divide_columns) • [`strip_whitespace`](#strip_whitespace) • [`trim_column_names`](#trim_column_names) • [`validate_columns_exist`](#validate_columns_exist) |
| **Conversion**        | [`from_pandas`](#from_pandas) • [`to_pandas`](#to_pandas)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| **Integration**       | [`ArnioPandasAccessor`](#arniopandasaccessor)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| **Pipeline**          | [`pipeline`](#pipeline) • [`register_step`](#register_step)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| **Data Quality**      | [`profile`](#profile) • [`suggest_cleaning`](#suggest_cleaning) • [`auto_clean`](#auto_clean) • [`DataQualityReport`](#dataqualityreport) • [`ColumnProfile`](#columnprofile)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
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

| Method                                            | Return Type |
| :------------------------------------------------ | :---------- |
| <a name="memory_usage"></a>**memory_usage()**     | `int`       |
| <a name="preview"></a>**preview()**               | `str`       |
| <a name="select_columns"></a>**select_columns()** | `ArFrame`   |
| <a name="select_dtypes"></a>**select_dtypes()**   | `ArFrame`   |

```python
print(f"Column Names: {df.columns}")
print(f"Data Types: {df.dtypes}")
print(f"Dataset Shape: {df.shape}")
print(f"Memory: {df.memory_usage()} bytes")
print(df.preview())
df = df.select_columns(columns=["id", "name"])
df = df.select_dtypes(include=["int64", "float64"])
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

### suggest_cleaning

Examine a report or frame and get a list of recommended cleaning steps.

### auto_clean

Profile the data and immediately apply repairs.

### DataQualityReport

Summary of structural data quality metrics.

### ColumnProfile

Detailed health check for a single column.

```python
report = ar.profile(df)
summary = report.summary()
suggestions = ar.suggest_cleaning(df)

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
