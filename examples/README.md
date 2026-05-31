# arnio Examples

Ready-to-run cleaning recipes for common messy CSV formats.

Each folder contains a small synthetic CSV with realistic data quality issues and a `recipe.py` that cleans, profiles, and validates it using the arnio API.

## Recipes

| Dataset | CSV | Issues Covered | arnio Features Used |
|---|---|---|---|
| [Sales](./sales/) | `messy_sales.csv` | duplicates, mixed-case regions, missing revenue | `pipeline`, `profile`, `validate` |
| [Customers](./customers/) | `messy_customers.csv` | whitespace in names, missing city, duplicate records | `suggest_cleaning`, `pipeline`, `validate` |
| [Survey](./survey/) | `messy_survey.csv` | mixed-case labels, missing scores, duplicate submissions | `profile`, `pipeline`, `validate` |
| [Logs](./logs/) | `messy_logs.csv` | mixed log levels, duplicate lines, missing timestamp | `scan_csv`, `pipeline`, `profile`, `validate` |
| [Finance](./finance/) | `messy_finance.csv` | mixed-case types, duplicate transactions, missing amount | `auto_clean`, `pipeline`, `validate` |

## Running an Example

```bash
pip install arnio

cd examples/sales
python recipe.py
```

## arnio API Features Demonstrated

- `ar.read_csv()` — load a CSV file into an `ArFrame` via the C++ backend
- `ar.scan_csv()` — inspect inferred column types without loading all data
- `ar.profile()` — generate a `DataQualityReport` (nulls, duplicates, whitespace, unique counts)
- `ar.suggest_cleaning()` — get auto-suggested pipeline steps from a profile
- `ar.auto_clean()` — one-call safe or strict cleaning with optional report return
- `ar.pipeline()` — apply a declarative sequence of cleaning steps
- `ar.validate()` — check an `ArFrame` against a typed `Schema`
- `ar.to_pandas()` — convert a cleaned `ArFrame` to a pandas `DataFrame`

## Pipeline Steps Used

| Step | Purpose |
|---|---|
| `strip_whitespace` | Trim leading/trailing whitespace from string columns |
| `normalize_case` | Standardise string values to `lower`, `upper`, or `title` case |
| `drop_duplicates` | Remove exact duplicate rows |
| `fill_nulls` | Replace nulls with a fallback value in specified columns |
| `drop_nulls` | Drop rows where specified columns are null |

## Schema Field Types

```python
ar.String(nullable=False, allowed={"north", "south"})
ar.Int64(nullable=True, min=0, max=120)
ar.Float64(nullable=False, min=0.0)
ar.Email(nullable=False, unique=True)
```

## Integration & Tutorial Scripts

Ready-to-run scripts in the `examples/` directory for common integrations and workflows.

| Script | Description | Run |
|---|---|---|
| [basic_usage.py](./basic_usage.py) | Quickstart: load, clean, and validate a CSV | `python basic_usage.py` |
| [arnio_with_pandas.py](./arnio_with_pandas.py) | Clean messy data with Arnio, analyse with pandas | `python arnio_with_pandas.py` |
| [arnio_with_numpy.py](./arnio_with_numpy.py) | Clean numeric data with Arnio, compute with NumPy | `python arnio_with_numpy.py` |
| [arnio_with_arrow.py](./arnio_with_arrow.py) | Clean data with Arnio, export to PyArrow Table | `python arnio_with_arrow.py` |
| [arnio_with_duckdb.py](./arnio_with_duckdb.py) | Clean data with Arnio, query with DuckDB SQL | `python arnio_with_duckdb.py` |
| [arnio_with_jsonl.py](./arnio_with_jsonl.py) | Load a JSONL file and run a cleaning pipeline | `python arnio_with_jsonl.py` |
| [arnio_with_sklearn.py](./arnio_with_sklearn.py) | Prepare data with Arnio, train a scikit-learn model | `python arnio_with_sklearn.py` |
| [sklearn_pipeline.py](./sklearn_pipeline.py) | Full scikit-learn pipeline with Arnio preprocessing | `python sklearn_pipeline.py` |
| [schema_validation.py](./schema_validation.py) | Define a Schema and validate typed fields end-to-end | `python schema_validation.py` |
| [custom_step.py](./custom_step.py) | Register a custom Python cleaning step in a pipeline | `python custom_step.py` |
| [arnio_chunk_reading.py](./arnio_chunk_reading.py) | Read and process large files in chunks | `python arnio_chunk_reading.py` |
