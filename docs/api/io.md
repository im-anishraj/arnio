# I/O — `arnio.io`

CSV reading functions powered by the C++ backend.

## `read_csv`

```python
arnio.read_csv(
    path,
    *,
    delimiter=",",
    has_header=True,
    usecols=None,
    nrows=None,
    encoding="utf-8",
) -> ArFrame
```

Read a CSV file into an `ArFrame` via the C++ backend.

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `path` | `str \| PathLike` | *required* | Path to the CSV file. Supports `.csv`, `.txt`, and `.tsv` extensions. |
| `delimiter` | `str` | `","` | Field delimiter character. |
| `has_header` | `bool` | `True` | Whether the file has a header row. |
| `usecols` | `list[str] \| None` | `None` | Columns to read. If `None`, reads all columns. |
| `nrows` | `int \| None` | `None` | Number of rows to read. If `None`, reads all rows. |
| `encoding` | `str` | `"utf-8"` | File encoding. Non-UTF-8 inputs are automatically transcoded. |

### Returns

`ArFrame` — Data frame containing the CSV data.

### Raises

- `ValueError` — If file format is unsupported.
- `CsvReadError` — If CSV input contains NUL bytes or is corrupted.

### Example

```python
import arnio as ar

frame = ar.read_csv("data.csv", delimiter=",", has_header=True)

# Read specific columns only
frame = ar.read_csv("data.csv", usecols=["name", "age"])

# Read first 100 rows
frame = ar.read_csv("data.csv", nrows=100)

# Handle non-UTF-8 encoding
frame = ar.read_csv("data.csv", encoding="latin-1")
```

---

## `scan_csv`

```python
arnio.scan_csv(
    path,
    *,
    delimiter=",",
    encoding="utf-8",
) -> dict[str, str]
```

Return schema (column names + inferred types) **without loading data**. Useful for inspecting large files before committing to a full read.

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `path` | `str \| PathLike` | *required* | Path to the CSV file. |
| `delimiter` | `str` | `","` | Field delimiter character. |
| `encoding` | `str` | `"utf-8"` | File encoding. |

### Returns

`dict[str, str]` — Dictionary mapping column names to inferred type strings (e.g., `"int64"`, `"float64"`, `"string"`).

### Raises

- `ValueError` — If file format is unsupported.
- `CsvReadError` — If CSV input contains NUL bytes.

### Example

```python
import arnio as ar

schema = ar.scan_csv("large_data.csv")
# {'name': 'string', 'age': 'int64', 'score': 'float64'}

# Check types before loading
for col, dtype in schema.items():
    print(f"{col}: {dtype}")
```

### When to Use `scan_csv` vs `read_csv`

- Use `scan_csv` when you need to inspect schema without the memory cost of loading data.
- Use `read_csv` when you need the actual data for processing.
