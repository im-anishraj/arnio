# Arnio API Reference

A technical reference guide to the public classes and functions within the **Arnio** library.

## Arnio API Reference Index

| Category              | Components                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| :-------------------- | :-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Core Class**        | [**`ArFrame`**](#arframe), Properties: [`shape`](#shape), [`columns`](#columns), [`dtypes`](#dtypes), [`is_empty`](#is_empty), Methods: [`memory_usage`](#memory_usage), [`preview`](#preview), [`select_columns`](#select_columns), [`select_dtypes`](#select_dtypes)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| **I/O** | [`read_csv`](#read_csv), [`scan_csv`](#scan_csv), [`write_csv`](#write_csv), [`write_json`](#write_json), [`write_jsonl`](#write_jsonl), [`sniff_delimiter`](#sniff_delimiter)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| **Cleaning**          | [`cast_types`](#cast_types), [`clean`](#clean), [`clip_numeric`](#clip_numeric), [`combine_columns`](#combine_columns), [`drop_columns`](#drop_columns), [`drop_constant_columns`](#drop_constant_columns), [`drop_duplicates`](#drop_duplicates), [`drop_nulls`](#drop_nulls), [`fill_nulls`](#fill_nulls), [`filter_rows`](#filter_rows), [`keep_rows_with_nulls`](#keep_rows_with_nulls), [`normalize_case`](#normalize_case), [`normalize_unicode`](#normalize_unicode), [`rename_columns`](#rename_columns), [`replace_values`](#replace_values), [`round_numeric_columns`](#round_numeric_columns), [`safe_divide_columns`](#safe_divide_columns), [`strip_whitespace`](#strip_whitespace), [`trim_column_names`](#trim_column_names), [`validate_columns_exist`](#validate_columns_exist) |
| **Conversion**        | [`from_pandas`](#from_pandas), [`to_pandas`](#to_pandas), [`from_arrow`](#from_arrow)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| **Integration**       | [`ArnioPandasAccessor`](#arniopandasaccessor)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| **Pipeline**          | [`pipeline`](#pipeline), [`register_step`](#register_step)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| **Data Quality**      | [`profile`](#profile) • [`suggest_cleaning`](#suggest_cleaning) • [`auto_clean`](#auto_clean) • [`check_quality_gates`](#check_quality_gates) • [`DataQualityReport`](#dataqualityreport) • [`ColumnProfile`](#columnprofile)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| **Schema Validation** | [`Schema`](#schema) • [`Field`](#field) • [`validate`](#validate) • [`ValidationResult`](#validationresult) • [`ValidationIssue`](#validationissue) • [`Int64`](#int64) • [`Float64`](#float64) • [`String`](#string) • [`Bool`](#bool) • [`Email`](#email) • [`URL`](#url) • [`CountryCode`](#countrycode) • [`DateTime`](#datetime)                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| **Custom Exceptions** | [`ArnioError`](#arnioerror) • [`CsvReadError`](#csvreaderror) • [`TypeCastError`](#typecasterror) • [`UnknownStepError`](#unknownsteperror)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |

---

## Current Public Export Index

This index is audited against `arnio.__all__` on current `main`.

| Category | Public exports |
| :------- | :------------- |
| **Core Class** | [`ArFrame`](#arframe), [`ColumnSummary`](#columnsummary) |
| **I/O** | [`read_csv`](#read_csv), [`read_csv_chunked`](#read_csv_chunked), [`read_jsonl`](#read_jsonl), [`read_jsonl_chunked`](#read_jsonl_chunked), [`read_parquet`](#read_parquet), [`scan_csv`](#scan_csv), [`sniff_delimiter`](#sniff_delimiter), [`write_csv`](#write_csv), [`write_json`](#write_json), [`write_parquet`](#write_parquet) |
| **Cleaning** | [`cast_types`](#cast_types), [`CastFailure`](#castfailure), [`CastReport`](#castreport), [`clean`](#clean), [`CleaningSuggestion`](#cleaningsuggestion), [`clean_column_names`](#clean_column_names), [`clip_numeric`](#clip_numeric), [`coalesce_columns`](#coalesce_columns), [`combine_columns`](#combine_columns), [`drop_columns`](#drop_columns), [`drop_columns_matching`](#drop_columns_matching), [`drop_constant_columns`](#drop_constant_columns), [`drop_duplicates`](#drop_duplicates), [`drop_empty_columns`](#drop_empty_columns), [`drop_nulls`](#drop_nulls), [`fill_nulls`](#fill_nulls), [`filter_rows`](#filter_rows), [`find_fuzzy_duplicates`](#find_fuzzy_duplicates), [`keep_rows_with_nulls`](#keep_rows_with_nulls), [`normalize_case`](#normalize_case), [`normalize_minmax`](#normalize_minmax), [`normalize_unicode`](#normalize_unicode), [`normalize_whitespace`](#normalize_whitespace), [`parse_bool_strings`](#parse_bool_strings), [`rename_columns`](#rename_columns), [`rename_columns_matching`](#rename_columns_matching), [`replace_values`](#replace_values), [`round_numeric_columns`](#round_numeric_columns), [`safe_divide_columns`](#safe_divide_columns), [`slugify_column_names`](#slugify_column_names), [`standardize_missing_tokens`](#standardize_missing_tokens), [`strip_whitespace`](#strip_whitespace), [`trim_column_names`](#trim_column_names), [`validate_columns_exist`](#validate_columns_exist), [`winsorize_outliers`](#winsorize_outliers) |
| **Conversion** | [`from_dict`](#from_dict), [`from_pandas`](#from_pandas), [`from_polars`](#from_polars), [`from_records`](#from_records), [`to_arrow`](#to_arrow), [`to_pandas`](#to_pandas), [`to_polars`](#to_polars) |
| **Integration** | [`ArnioPandasAccessor`](#arniopandasaccessor), [`encode_categorical`](#encode_categorical), [`register_duckdb`](#register_duckdb) |
| **Pipeline** | [`pipeline`](#pipeline), [`register_step`](#register_step), [`unregister_step`](#unregister_step), [`get_builtin_step_signatures`](#get_builtin_step_signatures), [`list_steps`](#list_steps), [`PipelineContext`](#pipelinecontext), [`LineageReport`](#lineagereport), [`reset_steps`](#reset_steps), [`save_pipeline`](#save_pipeline), [`load_pipeline`](#load_pipeline) |
| **Data Quality** | [`profile`](#profile), [`compare_profiles`](#compare_profiles), [`check_quality_gates`](#check_quality_gates), [`suggest_cleaning`](#suggest_cleaning), [`auto_clean`](#auto_clean), [`ColumnProfile`](#columnprofile), [`DataQualityReport`](#dataqualityreport), [`CleanStepRecord`](#cleansteprecord), [`CleanExplanation`](#cleanexplanation), [`ProfileComparison`](#profilecomparison), [`QualityGateIssue`](#qualitygateissue), [`QualityGateResult`](#qualitygateresult) |
| **Schema Validation** | [`Schema`](#schema), [`SchemaDiff`](#schemadiff), [`SchemaDiffEntry`](#schemadiffentry), [`Field`](#field), [`ValidationIssue`](#validationissue), [`ValidationResult`](#validationresult), [`validate`](#validate), [`diff_schema`](#diff_schema), [`Int64`](#int64), [`Float64`](#float64), [`String`](#string), [`CountryCode`](#countrycode), [`CurrencyCode`](#currencycode), [`LanguageCode`](#languagecode), [`TimeZone`](#timezone), [`Bool`](#bool), [`Email`](#email), [`URL`](#url), [`PhoneNumber`](#phonenumber), [`DateTime`](#datetime), [`normalize_unicode`](#normalize_unicode), [`Regex`](#regex), [`Custom`](#custom), [`register_validator`](#register_validator), [`Date`](#date), [`schema_from_yaml`](#schema_from_yaml), [`schema_to_dict`](#schema_to_dict), [`schema_to_yaml`](#schema_to_yaml) |
| **Custom Exceptions** | [`UnknownStepError`](#unknownsteperror), [`ArnioError`](#arnioerror), [`CsvReadError`](#csvreaderror), [`JsonlReadError`](#jsonlreaderror), [`RemoteReadError`](#remotereaderror), [`TypeCastError`](#typecasterror), [`PipelineStepError`](#pipelinesteperror), [`SchemaValidationError`](#schemavalidationerror), [`PipelineSerializationError`](#pipelineserializationerror) |

## Documentation Coverage Check

Run this static comparison from the repository root after updating public exports:

```bash
python -c "import ast, pathlib, re; tree=ast.parse(pathlib.Path('arnio/__init__.py').read_text(encoding='utf-8')); exports=[]; [exports.extend(e.value for e in node.value.elts if isinstance(e, ast.Constant) and isinstance(e.value, str)) for node in tree.body if isinstance(node, ast.Assign) for target in node.targets if isinstance(target, ast.Name) and target.id == '__all__']; doc=pathlib.Path('API_REFERENCE.md').read_text(encoding='utf-8'); missing=[name for name in exports if re.search(r'(?<![A-Za-z0-9_])'+re.escape(name)+r'(?![A-Za-z0-9_])', doc) is None]; print(f'public exports: {len(exports)}'); print(f'missing from API_REFERENCE.md: {len(missing)}'); print('missing names: ' + (', '.join(missing) if missing else 'none'))"
```

Current output:

```text
public exports: 116
missing from API_REFERENCE.md: 0
missing names: none
```

## Verified Public Export Addendum

### ColumnSummary

`ColumnSummary(name, dtype, nullable)` summarizes one `ArFrame` column.

### read_csv_chunked

Streams CSV input as `ArFrame` chunks.

### read_jsonl

Reads JSON Lines data into an `ArFrame`.

### read_jsonl_chunked

Streams JSON Lines input as `ArFrame` chunks.

### read_parquet

Reads Parquet input into an `ArFrame` through the optional Arrow integration.

### write_parquet

Writes an `ArFrame` to Parquet through the optional Arrow integration.

### normalize_whitespace

Collapses repeated whitespace in string values and trims surrounding whitespace.

### drop_empty_columns

Drops columns that contain only null or empty-string values.

### clean_column_names

`clean_column_names(frame, *, case_type="lower") -> ArFrame`

Normalizes column names by replacing non-alphanumeric characters with underscores, collapsing repeated underscores, trimming boundary underscores, and applying `case_type`. This is distinct from [`trim_column_names`](#trim_column_names), which only removes surrounding whitespace.

### winsorize_outliers

Clips numeric values using quantile bounds.

### normalize_minmax

Scales numeric columns to a min-max range.

### coalesce_columns

Creates an output column from the first non-null value across a column subset.

### rename_columns_matching

Renames columns whose names match a regular expression.

### drop_columns_matching

Drops columns whose names match a regular expression.

### parse_bool_strings

Converts supported boolean-like strings to booleans.

### find_fuzzy_duplicates

Finds approximate duplicates using the configured fuzzy-matching options.

### CastFailure

Record describing one failed cast during cast reporting.

### CastReport

Report object returned by cast operations that collect cast failures.

### CleaningSuggestion

Suggested cleaning action returned by [`suggest_cleaning`](#suggest_cleaning).

### slugify_column_names

Converts column names to slug-style identifiers.

### standardize_missing_tokens

Replaces common missing-value sentinel strings with null values.

### to_arrow

Converts an `ArFrame` to a `pyarrow.Table`.

### to_polars

Converts an `ArFrame` to a Polars DataFrame.

### from_polars

Builds an `ArFrame` from a Polars DataFrame.

### from_records

Builds an `ArFrame` from record-style Python data.

### from_dict

`from_dict(data: dict) -> ArFrame`

Builds an `ArFrame` from a dictionary whose keys are strings and whose values are same-length sequences of scalar values. The public Python helper accepts only the `data` mapping; dtype hints and row counts belong to the native core interface, not this public API.

### register_duckdb

Registers an `ArFrame` for DuckDB querying.

### unregister_step

`unregister_step(name: str) -> None`

Removes a registered custom Python pipeline step by name. Built-in steps remain protected by the registry.

### get_builtin_step_signatures

Returns signatures for built-in pipeline steps.

### list_steps

Lists built-in and custom pipeline step names currently registered.

### PipelineContext

Context object passed to custom pipeline steps that opt in to pipeline metadata.

### LineageReport

Pipeline lineage metadata collected during pipeline execution.

### reset_steps

Resets the pipeline step registry to the built-in step set.

### save_pipeline

Serializes a pipeline definition.

### load_pipeline

Loads a serialized pipeline definition.

### compare_profiles

Compares two data quality profiles.

### CleanStepRecord

Record describing one cleaning step applied during automatic cleaning.

### CleanExplanation

Explanation object returned when automatic cleaning is requested with explanations.

### ProfileComparison

Result object returned by [`compare_profiles`](#compare_profiles).

### QualityGateIssue

Represents one quality gate failure.

### SchemaDiff

Result object returned by [`diff_schema`](#diff_schema).

### SchemaDiffEntry

One changed, added, or removed field in a schema diff.

### diff_schema

Compares two schemas and reports structural differences.

### CurrencyCode

Schema field for 3-letter ISO 4217 currency codes.

### LanguageCode

Schema field for lowercase ISO 639-1 language codes.

### TimeZone

Schema field that validates values against IANA timezone names exposed by Python's `zoneinfo.available_timezones()`, such as `"Asia/Kolkata"` or `"UTC"`.

### PhoneNumber

Schema field for common phone number formats.

### Regex

Schema field that validates values against a regular expression.

### register_validator

Registers a custom validation function for [`Custom`](#custom) schema fields.

### Date

Schema field for strict calendar dates.

### schema_from_yaml

Deserializes a schema from YAML.

### schema_to_dict

Serializes a schema to a dictionary.

### schema_to_yaml

Serializes a schema to YAML.

### JsonlReadError

Raised when JSON Lines input cannot be parsed.

### RemoteReadError

Raised when a remote data source cannot be read.

### PipelineStepError

Raised when a custom pipeline step fails during execution.

### SchemaValidationError

Raised by schema-validation workflows that convert validation failures into exceptions.

### PipelineSerializationError

Raised when pipeline serialization or loading fails.

### encode_categorical

Encodes categorical columns using the configured categorical encoding options.

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

---

### write_json

Write an `ArFrame` to a JSON file.

```python
ar.write_json(frame, "output.json")
```

| Parameter  | Type                  | Default   | Description                                                        |
| :--------- | :-------------------- | :-------- | :----------------------------------------------------------------- |
| `frame`    | `ArFrame`             |           | The data frame to write.                                           |
| `path`     | `str` or `PathLike`   |           | Destination file path (must end with `.json`).                     |
| `orient`   | `str`                 | `"records"` | JSON orientation to use (`"records"`, `"list"`, or `"split"`).   |
| `indent`   | `int` or `None`       | `None`    | Indentation level for pretty-printing (writes compactly if `None`). |

**Returns:** `None`

**Raises:**
- `TypeError`: If input frame is not an `ArFrame` or path is invalid.
- `ValueError`: If file extension is unsupported or orient is invalid.

**Examples:**
```python
ar.write_json(frame, "output.json")

# Pretty print with indentation
ar.write_json(frame, "output.json", indent=4)

# List orientation
ar.write_json(frame, "output.json", orient="list")
```

### write_jsonl

Write an `ArFrame` to a newline-delimited JSON file.

```python
ar.write_jsonl(frame, "output.jsonl")
```

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `frame` | `ArFrame` | required | The data frame to write. |
| `path` | `str` or `PathLike` | required | Destination file path. Must end with `.jsonl` or `.ndjson`. |
| `encoding` | `str` | `"utf-8"` | Output file encoding. |
| `encoding_errors` | `str` | `"strict"` | How encoding errors are handled: `"strict"`, `"replace"`, or `"ignore"`. |

**Returns:** `None`

**Raises:**
- `TypeError`: If input frame is not an `ArFrame`, path is invalid, or encoding options are invalid.
- `ValueError`: If file extension is unsupported, encoding is unknown, encoding error handling is invalid, or a value cannot be serialized as JSON.
- `RuntimeError`: If the file cannot be opened or written.

**Examples:**

```python
ar.write_jsonl(frame, "output.jsonl")

ar.write_jsonl(frame, "output.ndjson", encoding="utf-8")
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

A high-level convenience shorthand that applies `strip_whitespace`, `drop_nulls`, and `drop_duplicates` in a single call. It accepts either a boolean to toggle the step, or a configuration dictionary to pass custom arguments to that step.

```python
# Default usage (applies strip_whitespace with default settings)
df = ar.clean(df)

# Advanced usage (passing configuration dictionaries to specific steps)
df = ar.clean(
    df,
    strip_whitespace={"subset": ["customer_name"]},
    drop_nulls=True,
    drop_duplicates={"keep": "last"}
)
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

### from_arrow

Converts a PyArrow Table to an Arnio `ArFrame`. This is useful for interoperability with other tools in the Arrow ecosystem.

Requires `pyarrow` to be installed (`pip install arnio[arrow]`).

```python
import pyarrow as pa
import arnio as ar

data = pa.table({"a": [1, 2, 3], "b": [4, 5, 6]})
frame = ar.from_arrow(data)

print(frame.shape)
# (3, 2)
```
