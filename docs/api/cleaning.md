# Cleaning — `arnio.cleaning`

Data cleaning operations for `ArFrame` objects. All functions return a **new** `ArFrame` (immutable pattern).

## `clean`

```python
arnio.clean(frame, *, strip_whitespace=True, drop_nulls=False, drop_duplicates=False) -> ArFrame
```

Convenience function to apply common cleaning operations in one call. Operations are applied in order:

1. `strip_whitespace` (if enabled)
2. `drop_nulls` (if enabled)
3. `drop_duplicates` (if enabled)

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `frame` | `ArFrame` | *required* | Input data frame. |
| `strip_whitespace` | `bool` | `True` | Trim leading/trailing whitespace from string columns. |
| `drop_nulls` | `bool` | `False` | Remove rows containing null/empty values. |
| `drop_duplicates` | `bool` | `False` | Remove duplicate rows. |

### Example

```python
import arnio as ar

frame = ar.read_csv("messy.csv")
cleaned = ar.clean(frame, strip_whitespace=True, drop_nulls=True, drop_duplicates=True)
```

---

## `drop_nulls`

```python
arnio.drop_nulls(frame, *, subset=None) -> ArFrame
```

Remove rows containing null/empty values.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `frame` | `ArFrame` | *required* | Input data frame. |
| `subset` | `list[str] \| None` | `None` | Columns to check. If `None`, checks all columns. A row is dropped if ANY column in the subset contains a null. |

```python
clean = ar.drop_nulls(frame, subset=["age", "name"])
```

---

## `fill_nulls`

```python
arnio.fill_nulls(frame, value, *, subset=None) -> ArFrame
```

Replace null/empty values with a given fill value.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `frame` | `ArFrame` | *required* | Input data frame. |
| `value` | `Any` | *required* | Value to replace nulls with. |
| `subset` | `list[str] \| None` | `None` | Columns to fill. If `None`, fills all columns. |

```python
filled = ar.fill_nulls(frame, 0, subset=["age"])
filled = ar.fill_nulls(frame, "unknown", subset=["name"])
```

---

## `drop_duplicates`

```python
arnio.drop_duplicates(frame, *, subset=None, keep="first") -> ArFrame
```

Remove duplicate rows.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `frame` | `ArFrame` | *required* | Input data frame. |
| `subset` | `list[str] \| None` | `None` | Columns to consider. If `None`, uses all columns. |
| `keep` | `str \| bool` | `"first"` | Which duplicate to keep: `"first"`, `"last"`, `"none"`, or `False` (drop all). |

```python
unique = ar.drop_duplicates(frame, subset=["email"], keep="first")
# Drop ALL duplicates (keep neither)
strict = ar.drop_duplicates(frame, subset=["id"], keep=False)
```

---

## `strip_whitespace`

```python
arnio.strip_whitespace(frame, *, subset=None) -> ArFrame
```

Trim leading and trailing whitespace from string columns.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `frame` | `ArFrame` | *required* | Input data frame. |
| `subset` | `list[str] \| None` | `None` | Columns to strip. If `None`, applies to all string columns. |

```python
clean = ar.strip_whitespace(frame, subset=["name", "email"])
```

---

## `normalize_case`

```python
arnio.normalize_case(frame, *, subset=None, case_type="lower") -> ArFrame
```

Normalize string columns to a specified case.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `frame` | `ArFrame` | *required* | Input data frame. |
| `subset` | `list[str] \| None` | `None` | Columns to normalize. If `None`, applies to all string columns. |
| `case_type` | `str` | `"lower"` | Case to normalize to: `"lower"`, `"upper"`, or `"title"`. |

```python
lower = ar.normalize_case(frame, case_type="lower")
title = ar.normalize_case(frame, subset=["name"], case_type="title")
```

---

## `rename_columns`

```python
arnio.rename_columns(frame, mapping) -> ArFrame
```

Rename columns via a `{old_name: new_name}` dictionary.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `frame` | `ArFrame` | *required* | Input data frame. |
| `mapping` | `dict[str, str]` | *required* | Dictionary mapping old column names to new names. |

```python
renamed = ar.rename_columns(frame, {"Old Name": "new_name", "User ID": "user_id"})
```

---

## `cast_types`

```python
arnio.cast_types(frame, mapping) -> ArFrame
```

Cast columns to specified types.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `frame` | `ArFrame` | *required* | Input data frame. |
| `mapping` | `dict[str, str]` | *required* | Dictionary mapping column names to target types: `"int64"`, `"float64"`, `"bool"`, `"string"`. |

### Raises

- `TypeCastError` — If a cast fails (e.g., non-numeric value in an int column).

```python
casted = ar.cast_types(frame, {"age": "int64", "score": "float64", "active": "bool"})
```

---

## `filter_rows`

```python
arnio.filter_rows(frame, column, op, value) -> ArFrame
```

Filter rows based on a column condition. Supports comparison operators.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `frame` | `ArFrame` | *required* | Input data frame (or pandas DataFrame). |
| `column` | `str` | *required* | Column name to filter on. |
| `op` | `str` | *required* | Comparison operator: `>`, `<`, `>=`, `<=`, `==`, `!=`. |
| `value` | `Any` | *required* | Value to compare against. |

```python
adults = ar.filter_rows(frame, "age", ">=", 18)
high_score = ar.filter_rows(frame, "score", ">", 90)
```
