# DType System — `arnio.schema`

Arnio uses a simple type system for column dtypes.

## Built-in DTypes

| DType | Python Type | Description |
|-------|-------------|-------------|
| `int64` | `int` | 64-bit signed integer |
| `float64` | `float` | 64-bit floating point |
| `bool` | `bool` | Boolean |
| `string` | `str` | UTF-8 string |

## Type Inference

When reading CSV files, Arnio automatically infers column types:

- **Integer-looking values** → `int64`
- **Float-looking values** → `float64`
- **`true`/`false`/`1`/`0`** → `bool`
- **Everything else** → `string`

## Type Casting

Use `cast_types` to explicitly convert between types:

```python
frame = ar.cast_types(frame, {
    "age": "int64",
    "score": "float64",
    "active": "bool",
    "notes": "string",
})
```

## Nullable Handling

All types support null values. When converting to pandas, nullable dtypes are used:

| Arnio | pandas |
|-------|--------|
| `int64` | `pd.Int64Dtype()` |
| `float64` | `float64` with `NaN` |
| `bool` | `pd.BooleanDtype()` |
| `string` | `pd.StringDtype()` |
