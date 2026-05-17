# Conversion — `arnio.convert`

Functions for converting between `ArFrame` and pandas `DataFrame`.

## `to_pandas`

```python
arnio.to_pandas(frame) -> pd.DataFrame
```

Convert an `ArFrame` to a pandas `DataFrame` with proper dtypes and null handling.

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `frame` | `ArFrame` | *required* | Input ArFrame to convert. |

### Returns

`pd.DataFrame` — Equivalent pandas DataFrame. Null values are represented using pandas nullable dtypes (`Int64Dtype`, `BooleanDtype`, `StringDtype`).

### Type Mapping

| Arnio (C++) | pandas |
|-------------|--------|
| `int64` | `pd.Int64Dtype()` (nullable integer) |
| `float64` | `float64` with `NaN` for nulls |
| `bool` | `pd.BooleanDtype()` (nullable boolean) |
| `string` | `pd.StringDtype()` (nullable string) |

### Example

```python
import arnio as ar

frame = ar.read_csv("data.csv")
df = ar.to_pandas(frame)
print(df.dtypes)
```

---

## `from_pandas`

```python
arnio.from_pandas(df) -> ArFrame
```

Convert a pandas `DataFrame` to an `ArFrame` with inferred types.

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `df` | `pd.DataFrame` | *required* | Input pandas DataFrame. |

### Returns

`ArFrame` — Equivalent ArFrame with inferred types.

### Raises

- `TypeError` — If the DataFrame contains unsupported nested/complex types (list, dict, tuple, set, ndarray).

### Type Coercion Rules

- Mixed `int` + `float` columns → `float`
- Mixed `bool` + other types → `string`
- Mixed `string` + other types → `string`
- `NaN`/`NA` → `None`

### Edge Cases & Limitations

- **Nested types** (lists, dicts, arrays) are not supported and will raise `TypeError`.
- **Mixed-type columns** are coerced to the most general type (usually `string`).
- **Boolean values** mixed with non-boolean types are converted to strings.

### Example

```python
import pandas as pd
import arnio as ar

df = pd.DataFrame({
    "name": ["Alice", "Bob", "Charlie"],
    "age": [25, 30, 35],
    "score": [95.5, 87.3, 92.1],
})

frame = ar.from_pandas(df)
```
