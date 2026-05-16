# Custom Pipeline Step Cookbook

This guide shows you how to write your own custom cleaning steps for arnio pipelines. No C++ required — custom steps are pure Python.

Read this top-to-bottom the first time; afterwards use it as a copy-paste template.

## Table of Contents

1. [The Contract](#1-the-contract)
2. [Safe Patterns](#2-safe-patterns)
3. [Unsafe Patterns](#3-unsafe-patterns)
4. [Full Example](#4-full-example--remove_outliers)
5. [Testing Your Custom Step](#5-testing-your-custom-step)
6. [Quick Reference](#6-quick-reference)

## 1. The Contract

Every custom step registered with `ar.register_step()` must follow this contract, or the pipeline will raise an error or silently corrupt data.

| | Type |
|---|---|
| Input | `pd.DataFrame` (arnio converts `ArFrame` to `DataFrame` for you) |
| Output | `pd.DataFrame` (arnio converts it back to `ArFrame`) |
| Errors | Raise `ValueError` or `TypeError` with a clear message |

Minimal valid step signature:

```python
def my_step(df: pd.DataFrame, **kwargs) -> pd.DataFrame:
    # your logic here
    return df
```

One input, one output, same type. That is it.

## 2. Safe Patterns

### Pattern 1 — Always work on a copy, never mutate the input

Mutating in place corrupts data for every step that runs after yours.

```python
def safe_strip_prefix(df: pd.DataFrame, column: str, prefix: str) -> pd.DataFrame:
    df = df.copy()
    if column not in df.columns:
        raise ValueError(
            f"safe_strip_prefix: column '{column}' not found. "
            f"Available columns: {list(df.columns)}"
        )
    df[column] = df[column].astype(str).str.removeprefix(prefix)
    return df
```

### Pattern 2 — Validate inputs before touching data

Check that required columns exist and that parameter values make sense.

```python
def safe_clamp(
    df: pd.DataFrame,
    column: str,
    min_val: float,
    max_val: float,
) -> pd.DataFrame:
    df = df.copy()
    if column not in df.columns:
        raise ValueError(
            f"safe_clamp: column '{column}' not found. "
            f"Available columns: {list(df.columns)}"
        )
    if min_val > max_val:
        raise ValueError(
            f"safe_clamp: min_val ({min_val}) must be <= max_val ({max_val})."
        )
    if not pd.api.types.is_numeric_dtype(df[column]):
        raise TypeError(
            f"safe_clamp: column '{column}' must be numeric, "
            f"got dtype '{df[column].dtype}'."
        )
    df[column] = df[column].clip(lower=min_val, upper=max_val)
    return df
```

### Pattern 3 — Handle nulls explicitly

Decide upfront: skip nulls, fill them, or raise. Document the choice.

```python
def safe_normalize_phone(df: pd.DataFrame, column: str) -> pd.DataFrame:
    """Remove all non-digit characters from a phone number column.

    Null values are left as-is (not dropped, not filled).
    """
    df = df.copy()
    if column not in df.columns:
        raise ValueError(
            f"safe_normalize_phone: column '{column}' not found. "
            f"Available columns: {list(df.columns)}"
        )
    mask = df[column].notna()
    df.loc[mask, column] = (
        df.loc[mask, column].astype(str).str.replace(r"\D", "", regex=True)
    )
    return df
```

## 3. Unsafe Patterns

Do not do any of the following.

**Mutates input in place:**

```python
def unsafe_mutate(df, column):
    df[column] = df[column].str.lower()  # modifies the caller's DataFrame
    return df
```

**Forgets to return the DataFrame:**

```python
def unsafe_no_return(df, column):
    df = df.copy()
    df[column] = df[column].str.lower()
    # missing: return df — pipeline receives None and crashes
```

**Silently swallows errors:**

```python
def unsafe_silent(df, column):
    try:
        df = df.copy()
        df[column] = df[column].str.lower()
    except Exception:
        pass  # hides bugs, returns wrong data
    return df
```

**No column existence check:**

```python
def unsafe_no_check(df, column):
    df = df.copy()
    df[column] = df[column].str.lower()  # KeyError if column is missing
    return df
```

## 4. Full Example — `remove_outliers`

This is a complete, PR-ready custom step. Copy this pattern for any new step you contribute.

```python
import pandas as pd
import arnio as ar


def remove_outliers(
    df: pd.DataFrame,
    column: str,
    threshold: float,
    keep: str = "below",
) -> pd.DataFrame:
    """Remove rows where a numeric column exceeds (or falls below) a threshold.

    Parameters
    ----------
    df        : Input DataFrame. Not modified in place.
    column    : Name of the numeric column to filter on.
    threshold : The cutoff value.
    keep      : "below" keeps rows where column <= threshold (default).
                "above" keeps rows where column >= threshold.

    Returns
    -------
    pd.DataFrame
        A new DataFrame with outlier rows removed.

    Raises
    ------
    ValueError
        If column is not in the DataFrame, or keep is not a valid option.
    TypeError
        If column is not numeric.

    Examples
    --------
    >>> ar.register_step("remove_outliers", remove_outliers)
    >>> frame = ar.from_pandas(pd.DataFrame({"revenue": [100, 999, 50, 10_000]}))
    >>> clean = ar.pipeline(frame, [
    ...     ("remove_outliers", {"column": "revenue", "threshold": 500}),
    ... ])
    >>> ar.to_pandas(clean)["revenue"].tolist()
    [100, 50]
    """
    if column not in df.columns:
        raise ValueError(
            f"remove_outliers: column '{column}' not found. "
            f"Available columns: {list(df.columns)}"
        )
    if not pd.api.types.is_numeric_dtype(df[column]):
        raise TypeError(
            f"remove_outliers: column '{column}' must be numeric, "
            f"got dtype '{df[column].dtype}'."
        )
    if keep not in ("below", "above"):
        raise ValueError(
            f"remove_outliers: 'keep' must be 'below' or 'above', got '{keep}'."
        )
    df = df.copy()
    if keep == "below":
        return df[df[column] <= threshold]
    return df[df[column] >= threshold]


ar.register_step("remove_outliers", remove_outliers)
```

Use it in a pipeline:

```python
frame = ar.from_pandas(pd.DataFrame({"revenue": [100, 999, 50, 10_000]}))
clean = ar.pipeline(frame, [
    ("remove_outliers", {"column": "revenue", "threshold": 500}),
])
df = ar.to_pandas(clean)
# df["revenue"].tolist() -> [100, 50]
```

Input and output:

| revenue (before) | revenue (after) |
|---|---|
| 100 | 100 |
| 999 | removed |
| 50 | 50 |
| 10000 | removed |

## 5. Testing Your Custom Step

Run tests with:

```bash
pytest examples/custom_step_with_tests.py -v
```

Every step needs three categories of tests.

| Category | What to test |
|---|---|
| Normal cases | Expected inputs produce expected outputs |
| Edge cases | Empty DataFrame, all nulls, single row, boundary values |
| Invalid cases | Wrong column name, wrong type, bad parameters |

Normal case:

```python
def test_keep_below_removes_high_values():
    frame = make_frame({"revenue": [100, 999, 50, 10_000]})
    result = ar.pipeline(frame, [
        ("remove_outliers", {"column": "revenue", "threshold": 500}),
    ])
    assert to_list(result, "revenue") == [100, 50]
```

Edge case:

```python
def test_empty_dataframe_returns_empty():
    frame = make_frame({"revenue": []})
    result = ar.pipeline(frame, [
        ("remove_outliers", {"column": "revenue", "threshold": 500}),
    ])
    assert ar.to_pandas(result).empty

def test_does_not_mutate_input_frame():
    df_original = pd.DataFrame({"revenue": [100, 9999]})
    frame = ar.from_pandas(df_original.copy())
    ar.pipeline(frame, [
        ("remove_outliers", {"column": "revenue", "threshold": 500}),
    ])
    assert df_original["revenue"].tolist() == [100, 9999]
```

Invalid case:

```python
def test_missing_column_raises_value_error():
    frame = make_frame({"revenue": [100, 200]})
    with pytest.raises(ValueError, match="column 'amount' not found"):
        ar.pipeline(frame, [
            ("remove_outliers", {"column": "amount", "threshold": 500}),
        ])

def test_non_numeric_column_raises_type_error():
    frame = make_frame({"name": ["alice", "bob"]})
    with pytest.raises(TypeError, match="must be numeric"):
        ar.pipeline(frame, [
            ("remove_outliers", {"column": "name", "threshold": 500}),
        ])
```

## 6. Quick Reference

```python
# 1. Write your function
def my_step(df: pd.DataFrame, **kwargs) -> pd.DataFrame:
    df = df.copy()
    # validate inputs
    # your logic here
    return df

# 2. Register it
ar.register_step("my_step", my_step)

# 3. Use it in a pipeline
clean = ar.pipeline(frame, [("my_step",)])
```
