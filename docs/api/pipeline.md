# Pipeline — `arnio.pipeline`

Chained cleaning pipeline for composing multiple operations.

## `pipeline`

```python
arnio.pipeline(frame, steps) -> ArFrame
```

Apply a list of cleaning steps sequentially. Each step is a tuple of `(step_name,)` or `(step_name, kwargs_dict)`.

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `frame` | `ArFrame` | *required* | Input data frame. |
| `steps` | `list[tuple]` | *required* | List of steps. Each step is `(name,)` or `(name, kwargs)`. |

### Returns

`ArFrame` — Data frame with all steps applied sequentially.

### Raises

- `ValueError` — If step format is invalid.
- `UnknownStepError` — If step name is not registered.

### Built-in Steps

| Step Name | Parameters | Description |
|-----------|------------|-------------|
| `drop_nulls` | `subset: list[str]` | Remove null rows |
| `fill_nulls` | `value, subset: list[str]` | Fill null values |
| `drop_duplicates` | `subset: list[str], keep: str` | Remove duplicates |
| `strip_whitespace` | `subset: list[str]` | Trim whitespace |
| `normalize_case` | `subset: list[str], case_type: str` | Normalize case |
| `rename_columns` | `mapping: dict` | Rename columns |
| `cast_types` | `mapping: dict` | Cast column types |
| `filter_rows` | `column, op, value` | Filter rows |

### Step Format

For `rename_columns` and `cast_types`, the kwargs dict is passed directly as the mapping:

```python
("rename_columns", {"old_name": "new_name"})
("cast_types", {"age": "int64"})
```

For all other steps, use standard keyword arguments:

```python
("drop_nulls", {"subset": ["age"]})
("strip_whitespace",)  # no kwargs needed
```

### Example

```python
import arnio as ar

frame = ar.read_csv("data.csv")

cleaned = ar.pipeline(frame, [
    ("strip_whitespace",),
    ("drop_nulls", {"subset": ["email"]}),
    ("normalize_case", {"subset": ["name"], "case_type": "title"}),
    ("drop_duplicates", {"subset": ["email"], "keep": "first"}),
    ("cast_types", {"age": "int64", "score": "float64"}),
])
```

---

## `register_step`

```python
arnio.register_step(name, fn)
```

Register a custom Python pipeline step.

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `name` | `str` | *required* | Name of the step for use in pipelines. |
| `fn` | `Callable` | *required* | Function to call. Should accept `(df, **kwargs)` and return a modified DataFrame. |

### Example

```python
import arnio as ar

def remove_outliers(df, column="value", threshold=3.0):
    mean = df[column].mean()
    std = df[column].std()
    return df[(df[column] - mean).abs() <= threshold * std]

ar.register_step("remove_outliers", remove_outliers)

cleaned = ar.pipeline(frame, [
    ("strip_whitespace",),
    ("remove_outliers", {"column": "price", "threshold": 2.5}),
])
```

!!! note
    Custom Python steps convert the frame to pandas internally, so they are slower than built-in C++-backed steps.
