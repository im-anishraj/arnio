# Guide for troubleshooting

If you are setting up Arnio from source, remember that `pip install -e ".[dev]"`
must build the native C++ extension before most examples and tests can run. The
[Core Stability Sprint](../CORE_STABILITY_SPRINT.md) tracks this as a release
gate because import failures are usually build/setup problems, not test logic
problems.

Run the environment doctor before debugging build failures:

```bash
python examples/check_env.py
```

On Windows, `[BUILD BLOCKED]` usually means PowerShell cannot see Visual Studio
Build Tools commands such as `cl` or `nmake`. Install the `Desktop development
with C++` workload, then retry from an x64 Developer Command Prompt.

## `ModuleNotFoundError: No module named 'hypothesis'` while running tests

### Problem

Running `pytest` may fail during test collection with:

```text
ModuleNotFoundError: No module named 'hypothesis'
```

### Why it happens

This usually happens when the development dependencies are not installed.

### What to do about it

Install the development dependencies:

```bash
pip install -e ".[dev]"
```

Then rerun the tests:

```bash
pytest
```

## MemoryError when reading large CSV files

### Problem

Some users may encounter a MemoryError when trying to load large CSV files.

### Why it happens

Large datasets may not fully fit into memory, even if the machine appears to have enough resources. In some cases, automatic column type inference can also increase memory usage.

### What to do about it

* Use `usecols` in `ar.read_csv(...)` to load only required columns
* Use `select_columns()` to reduce unnecessary data before processing
* Avoid unnecessary `cast_types()` operations unless they are required

### Quick example

```python
import arnio as ar

frame = ar.read_csv(
    "large.csv",
    usecols=["id", "name"]
)
```

## Numeric columns inferred as strings

### Problem

Sometimes a numeric column gets detected as a string, even when you expect it to contain only numbers.

### Why it happens

This usually happens when the column contains mixed values, missing entries, or unexpected characters. The loader may then treat the entire column as text instead of numeric data.

### What to do about it

* Use `cast_types()` to apply explicit Arnio datatypes when needed
* Check columns for invalid values or unexpected symbols before validation

### Quick example

```python
import arnio as ar

frame = ar.read_csv("data.csv")

frame = ar.cast_types(
    frame,
    {"age": "int64"}
)
```

## ValidationResult.passed returning False

### Problem

Sometimes a dataset may appear valid but still fail validation checks.

### Why it happens

This usually happens because the dataset contains missing values, incorrect datatypes, unexpected nulls, or schema mismatches.

### What to do about it

* Review the validation output from `ar.validate(...)` carefully
* Inspect rows containing null or unexpected values before validation
* Verify that column names and datatypes match the expected `Schema`
* Ensure all required fields defined in the schema are present

### Quick example

```python
result = ar.validate(frame, schema)

print(result.passed)
print(result.issues)
```

## Unknown or custom steps not running

### Problem

Sometimes custom pipeline steps fail to execute or appear as unknown during runtime.

### Why it happens

This usually happens when the custom step is not registered correctly or required imports are missing.

### What to do about it

* Verify that the custom step is registered using `ar.register_step(...)`
* Check that the custom step function and imports are available before running the pipeline
* Restart the environment after adding new custom pipeline steps
* Ensure the correct step name is referenced inside `ar.pipeline(...)`

### Quick example

```python
def clean_data(frame):
    return frame

ar.register_step("clean_data", clean_data)

ops = [
    ("clean_data",),
]
frame = ar.pipeline(frame, ops)
```

## Slow CSV parsing and performance issues

### Problem

Large CSV files may take a long time to load or process.

### Why it happens

Performance issues usually occur when unnecessary columns are loaded, datatype inference becomes expensive, or the entire dataset is processed at once.

### What to do about it

* Use `usecols` in `ar.read_csv(...)` to load only required columns
* Avoid unnecessary `cast_types()` operations unless they are needed
* Use `select_columns()` to reduce unnecessary data before processing
* Remove unused columns with `drop_columns()` when possible

### Quick example

```python
import arnio as ar

frame = ar.read_csv(
    "large.csv",
    usecols=["id", "name"]
)
```
