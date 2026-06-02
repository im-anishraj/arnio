# Error taxonomy and recovery playbook

This document targets deterministic recovery when you integrate **Arnio** into production pipelines.

It covers three common classes of failures:

1. **Pipeline step dispatch failures** (`UnknownStepError`)
2. **Type casting failures** (`TypeCastError`)
3. **Schema validation failures** (`ValidationResult` / `ValidationIssue`)

> Conventions:
> - Pipeline step names are resolved before any execution begins.
> - `ar.validate()` returns a `ValidationResult` (it does **not** raise on validation failures).
> - `ValidationIssue.row_index` is **1-based** and counts **data rows only** (header excluded).

---

## 1) Error taxonomy (exception / return types)

| Error / return type | What it means | Typical recovery path |
|---|---|---|
| `arnio.exceptions.UnknownStepError` | A step name in `ar.pipeline(..., steps=[...])` is not registered/available (including missing namespaces / typos). | List steps (`ar.list_steps()`), verify exact name, then register missing custom steps with `ar.register_step(...)`. |
| `arnio.exceptions.TypeCastError` | `ar.cast_types(...)` hit an incompatible value conversion while `errors="raise"` (or when internal cast logic treats the cast as fatal). | Re-run with `errors="coerce"` (turn invalid values into nulls) or pre-clean the problematic values, then validate with `Schema`. |
| `arnio.schema.ValidationResult` + `arnio.schema.ValidationIssue` | Schema validation failed; issues are returned for inspection. | Extract issues, group by column/rule, inspect offending rows using `row_index` / `bad_rows`, then fix input parsing/cleaning parameters and re-validate. |

---

## 2) Copy/paste recipes

### Recipe A — Recover from `UnknownStepError` (typo vs missing registration/import)

**Public APIs involved**
- `ar.pipeline(frame, steps, ...)` raises `arnio.exceptions.UnknownStepError`
- `ar.list_steps()` returns available step names
- `ar.register_step(name, fn, overwrite=False)` registers a custom Python step

**When it happens**
- The step name in your `steps` spec is misspelled.
- Your custom step function was not registered (or you registered it under a different name).

```python
import arnio as ar
from arnio.exceptions import UnknownStepError

# Example: pipeline that references an unknown step name
steps = [
    ("strip_whitespace",),
    ("my_drop_nulls", {"subset": ["age"]}),  # <-- might be a typo or missing registration
]

frame = ar.read_csv("data.csv")

try:
    cleaned = ar.pipeline(frame, steps)
except UnknownStepError as e:
    print("Pipeline failed with UnknownStepError:")
    print(e)

    # 1) Inspect what Arnio currently knows about
    available = ar.list_steps()
    print("Available steps:")
    print(available)

    # 2) If this is a custom step, register it under the exact name
    #    Make sure this function is defined/imported before ar.pipeline(...)
    def my_drop_nulls(df, subset):
        # Minimal example: use existing built-in behavior via pandas bridge
        # (You can implement your own logic as long as you return a pandas.DataFrame.)
        df2 = df.copy()
        return df2.dropna(subset=subset)

    # Register under the name used in `steps`
    ar.register_step("my_drop_nulls", my_drop_nulls, overwrite=False)

    # 3) Retry the pipeline
    cleaned = ar.pipeline(frame, steps)

# `cleaned` is an ArFrame
print(cleaned.dtypes)
```

**Notes for deterministic debugging**
- `UnknownStepError` is raised *before execution begins*.
- Use `ar.list_steps()` in the same process where you call `ar.pipeline()`.
- Built-in C++ steps live under their canonical names (for example, `"drop_nulls"`).
- If you use a namespaced convention like `"team:step_name"`, ensure you registered the exact namespaced name.

---

### Recipe B — Recover from `TypeCastError` (use `errors="coerce"` + validate with `Schema`)

**Public APIs involved**
- `ar.cast_types(frame, mapping, errors="raise"|"coerce"|"ignore")` raises `arnio.exceptions.TypeCastError`
- `ar.Schema`, `ar.validate(frame, schema)` returns `ValidationResult`
- `ValidationResult.passed` and `ValidationResult.issues`

**When it happens**
- You attempted to cast a column and at least one value cannot be converted to the target dtype.

```python
import arnio as ar
from arnio.exceptions import TypeCastError

frame = ar.read_csv("data.csv")

# Example: age contains some non-numeric strings
cast_mapping = {"age": "int64"}

try:
    # Default behavior is effectively "raise" (fatal on incompatible values)
    frame2 = ar.cast_types(frame, cast_mapping, errors="raise")
except TypeCastError as e:
    print("Cast failed:", e)

    # Deterministic recovery strategy 1:
    # - Coerce invalid values to null
    frame2 = ar.cast_types(frame, cast_mapping, errors="coerce")

# Deterministic recovery strategy 2: validate the recovered frame
schema = ar.Schema({
    "age": ar.Int64(nullable=True, min=0),
})

result = ar.validate(frame2, schema)
print("passed?", result.passed)

if not result.passed:
    # Print issues (you may want to inspect row_index in recipe C)
    for issue in result.issues[:20]:
        print(issue.column, issue.rule, issue.row_index, issue.message)
```

**How to choose `errors`**
- `errors="raise"` (strict): best when you want to fail fast.
- `errors="coerce"` (recoverable): best when you prefer invalid values to become nulls.
- `errors="ignore"`: leaves affected columns unchanged for values that cannot be cast.

---

### Recipe C — Triaging `ValidationResult` failures (extract issues, isolate offending rows)

**Public APIs involved**
- `ar.validate(frame, schema, max_errors=None) -> ValidationResult`
- `ValidationResult.issues: list[ValidationIssue]`
- `ValidationResult.bad_rows: list[int]`
- `ValidationIssue.row_index` (1-based, data rows only)

```python
import arnio as ar

frame = ar.read_csv("data.csv")

schema = ar.Schema({
    "age": ar.Int64(nullable=False, min=0),
    "email": ar.Email(nullable=False),
})

result = ar.validate(frame, schema)

print("passed?", result.passed)
print("issue_count:", result.issue_count)
print("bad_rows (1-based data row indexes):", result.bad_rows)

# 1) Inspect issues grouped by column
issues_by_column = {}
for issue in result.issues:
    col = issue.column or "<schema>"
    issues_by_column.setdefault(col, []).append(issue)

for col, issues in issues_by_column.items():
    print("\nCOLUMN:", col)
    for i in issues[:10]:
        print("- rule=", i.rule, " row_index=", i.row_index, " severity=", i.severity)
        print("  message=", i.message)

# 2) Isolate a small set of offending rows for inspection
#    - row_index is 1-based and counts data rows only
#    - if `frame` originated from `read_csv`, row_index maps to the same in-memory row order

bad = set(result.bad_rows)

# Convert to pandas for row slicing/debug printing.
# (This is only for triage/inspection; you can avoid pandas in hot paths.)
pdf = ar.to_pandas(frame, copy=False)

triage_rows = pdf.iloc[sorted(bad)].copy()  # NOTE: row_index 1..N => iloc uses 0..N-1
print(triage_rows.head())
```

**Important: `row_index` semantics**
- `row_index` refers to the **position of the data row inside the validated in-memory table**.
- It is **1-based** and counts **only data rows** (header excluded).
- When the original data came from `read_csv(...)`, the in-memory row order matches the file order (after Arnio loads it).
- When the original data came from `from_pandas(...)`, `row_index` matches the position of rows in that pandas DataFrame (again, 1-based). In other words: it’s never the pandas index label; it’s the row position.

**Optional: isolate by specific column/rule**
- Filter `result.issues` down to the column/rule you care about, then collect their `row_index` values.
- Use a unique set to avoid duplicates.

---

## 3) Recommended production workflow

A production-friendly loop looks like this:

1. **Run `cast_types(..., errors="coerce")`** for recoverable parsing issues.
2. **Run `validate(...)`**.
3. If validation fails:
   - Use recipe C to inspect `result.issues` / `bad_rows`.
   - Apply targeted cleaning based on the failing columns/rules.
4. Re-run casting + validation until `result.passed == True`.

---

## 4) What to log for observability

Log these fields to correlate failures deterministically:
- For `UnknownStepError`: the missing name and `ar.list_steps()` snapshot.
- For `TypeCastError`: the mapping attempted and the chosen `errors` mode.
- For `ValidationResult`: `result.passed`, `result.issue_count`, and a capped list of `(column, rule, row_index, message)`.