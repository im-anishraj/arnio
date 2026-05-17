# Schema Validation — `arnio.schema`

Production data contracts and validation for `ArFrame` objects.

## `validate`

```python
arnio.validate(frame, schema) -> ValidationResult
```

Validate an `ArFrame` against a schema.

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `frame` | `ArFrame` | *required* | Input frame. |
| `schema` | `Schema \| dict[str, Field]` | *required* | Validation contract. |

### Returns

`ValidationResult` — Contains all issues and bad row indexes.

### Example

```python
import arnio as ar

schema = ar.Schema({
    "email": ar.Email(nullable=False, unique=True),
    "age": ar.Int64(min=0, max=150),
    "name": ar.String(nullable=False, min_length=1),
})

result = ar.validate(frame, schema)
if not result.passed:
    print(f"Found {result.issue_count} issues")
    for issue in result.issues:
        print(f"  {issue.column}: {issue.message}")
```

---

## `Schema`

```python
Schema(fields, strict=False)
```

Named column validation contract.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `fields` | `dict[str, Field]` | *required* | Column validation rules. |
| `strict` | `bool` | `False` | If `True`, rejects unexpected columns. |

---

## `Field`

```python
Field(
    dtype=None, nullable=True, min=None, max=None,
    pattern=None, semantic=None, allowed=None,
    unique=False, min_length=None, max_length=None,
)
```

Validation rules for one column.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `dtype` | `str \| None` | `None` | Expected dtype: `"int64"`, `"float64"`, `"bool"`, `"string"`. |
| `nullable` | `bool` | `True` | Whether null values are allowed. |
| `min` | `int \| float \| None` | `None` | Minimum value (numeric columns). |
| `max` | `int \| float \| None` | `None` | Maximum value (numeric columns). |
| `pattern` | `str \| None` | `None` | Regex pattern the values must match. |
| `semantic` | `str \| None` | `None` | Semantic type: `"email"`, `"url"`, `"phone"`. |
| `allowed` | `set \| None` | `None` | Set of allowed values. |
| `unique` | `bool` | `False` | Whether all values must be unique. |
| `min_length` | `int \| None` | `None` | Minimum string length. |
| `max_length` | `int \| None` | `None` | Maximum string length. |

---

## Type Helper Functions

### `Int64`

```python
Int64(*, nullable=True, min=None, max=None, unique=False) -> Field
```

Create an `int64` schema field with optional range and uniqueness constraints.

### `Float64`

```python
Float64(*, nullable=True, min=None, max=None, unique=False) -> Field
```

Create a `float64` schema field.

### `String`

```python
String(*, nullable=True, pattern=None, allowed=None, unique=False,
       min_length=None, max_length=None) -> Field
```

Create a `string` schema field.

### `Bool`

```python
Bool(*, nullable=True) -> Field
```

Create a `bool` schema field.

### `Email`

```python
Email(*, nullable=True, unique=False) -> Field
```

Create an email-address schema field (validates against email regex).

### `URL`

```python
URL(*, nullable=True, unique=False) -> Field
```

Create a URL schema field (validates against `http(s)://` pattern).

---

## `ValidationResult`

| Property/Method | Type | Description |
|----------------|------|-------------|
| `passed` | `bool` | Whether validation passed with zero issues. |
| `row_count` | `int` | Total rows in the validated frame. |
| `issue_count` | `int` | Number of validation issues found. |
| `issues` | `list[ValidationIssue]` | All validation issues. |
| `bad_rows` | `list[int]` | Row indexes with issues. |
| `to_dict()` | `dict` | JSON-friendly representation. |
| `summary()` | `dict` | Compact summary grouped by rule and column. |
| `to_pandas()` | `pd.DataFrame` | Issues as a pandas DataFrame. |

## `ValidationIssue`

| Field | Type | Description |
|-------|------|-------------|
| `column` | `str \| None` | Column name (None for frame-level issues). |
| `rule` | `str` | Rule that failed (e.g., `"nullable"`, `"dtype"`, `"unique"`). |
| `message` | `str` | Human-readable description. |
| `row_index` | `int \| None` | Row index of the failing value. |
| `value` | `Any` | The failing value. |
