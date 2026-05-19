# Guide for troubleshooting

## MemoryError when reading large CSV files

### Problem

Some users may encounter a MemoryError when trying to load large CSV files.

### Why it happens

Large datasets may not fully fit into memory, even if the machine appears to have enough resources. In some cases, automatic column type inference can also increase memory usage.

### What to do about it

- Load only the data required for your workflow
- Only load the columns you actually need
- Try not to do unnecessary conversions early on, like casting everything right away

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

- Clean those inconsistent values before you load anything
- Pass explicit datatype definitions whenever possible
- Also check for empty spaces, stray symbols, or any invalid tokens in numeric columns

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

- Review logs from the validations carefully
- Look for rows with null or unexpected values
- Compare the columns in the dataset to see if the names and types of the columns match what you expect them to be
- Ensure that there are no missing required fields

### Quick example

```python
result = ar.validate(frame, schema)

print(result.passed)
print(result.summary())
```

## Unknown or custom steps not running

### Problem

Sometimes custom pipeline steps fail to execute or appear as unknown during runtime.

### Why it happens

This usually happens when the custom step is not registered correctly or required imports are missing.

### What to do about it

- Verify that the custom step is registered correctly
- Check any import statements for the customized steps and verify that the names/modules exist
- Always restart the environment if you've added a new step to the pipeline
- Validate that your configuration is referencing the proper step name in the pipeline

### Quick example

```python
def clean_data(df):
    return df

ar.register_step("clean_data", clean_data)

result = ar.pipeline(
    frame,
    [("clean_data",)]
)
```

## Slow CSV parsing and performance issues

### Problem

Large CSV files may take a long time to load or process.

### Why it happens

Performance issues usually occur when unnecessary columns are loaded, datatype inference becomes expensive, or the entire dataset is processed at once.

### What to do about it

- Only load the columns that you actually require.
- Avoid converting datatypes that are unnecessary.
- Process only the data required for your workflow.
- Remove unused data before processing.

### Quick example

```python
import arnio as ar

frame = ar.read_csv(
    "large.csv",
    usecols=["id", "name"]
)
```
