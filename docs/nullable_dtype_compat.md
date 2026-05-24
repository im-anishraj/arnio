# Nullable pandas Extension Dtype Compatibility

This section documents how arnio handles pandas nullable extension dtypes
during a `from_pandas` → arnio → `to_pandas` round-trip.

## Supported Dtypes

| pandas input dtype | Supported | NA sentinel | Round-trip output dtype | Notes |
|--------------------|-----------|-------------|------------------------|-------|
| `Int64`            | ✅        | `pd.NA`     | `Int64`                | Nullable integer preserved |
| `UInt64`           | ✅ (bounded) | `pd.NA`  | `Int64`                | Values must fit in signed int64 |
| `Float64`          | ✅        | `pd.NA`     | `float64`              | Upcasts to native float |
| `boolean`          | ✅        | `pd.NA`     | `boolean`              | Nullable bool preserved |
| `string`           | ✅        | `pd.NA`     | `string`               | Nullable string preserved |

> **Note:** `Float64` (capital F) is the pandas nullable float extension dtype.
> After a round-trip it becomes `float64` (lowercase), the standard NumPy dtype.
> The values and null positions are preserved; only the container dtype changes.

## Round-Trip Example

```python
import pandas as pd
import arnio as ar

df = pd.DataFrame({
    "int_col":   pd.array([1, 2, None],        dtype="Int64"),
    "float_col": pd.array([1.5, None, 3.7],    dtype="Float64"),
    "bool_col":  pd.array([True, None, False],  dtype="boolean"),
    "str_col":   pd.array(["a", None, "c"],     dtype="string"),
})

frame  = ar.from_pandas(df)
result = ar.to_pandas(frame)

print(result.dtypes)
# int_col      Int64
# float_col    float64   ← note: Float64 → float64
# bool_col     boolean
# str_col      string
```

## NA Handling

- `pd.NA` is preserved as `pd.NA` for `Int64`, `boolean`, and `string` columns.
- `pd.NA` in a `Float64` column becomes `float('nan')` / `pd.isna()` after
  round-trip because the output dtype is native `float64`.

## Unsupported Dtypes

The following dtypes raise `TypeError` with a fix hint:

| pandas dtype     | Error |
|-----------------|-------|
| `datetime64`    | Convert to string first: `.astype(str)` |
| `timedelta64`   | Convert to seconds: `.dt.total_seconds()` |
| `category`      | Convert to string first: `.astype(str)` |
| `complex128`    | Convert to string: `.apply(str)` |

## UInt64 Boundary

`UInt64` values must fit within the signed 64-bit integer range
(`0` to `9223372036854775807`). Values exceeding this raise `ValueError`."" 
