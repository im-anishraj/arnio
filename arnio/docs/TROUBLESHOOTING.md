# Guide for troubleshooting

## MemoryError when reading big CSV files

### The problem

Some users might get MemoryError, when they try to load larger CSV files.

### Why it happens

Large datasets may not fully fit into memory, even if the machine appears to have enough resources. In some cases, automatic column type inference can also increase memory usage.

### What to do about it

- Read the file gradually in smaller parts, instead of one big pull
- Only take the columns you truly need, you can skip the rest
- Try not to do unnecessary conversions early on, like casting everything right away

### Quick example

```python
import pandas as pd

for chunk in pd.read_csv("large.csv", chunksize = 10000):
    print(chunk.head())

```

## Numeric columns inferred as strings

### Problem

Sometimes a numeric column gets detected as a string, even when you expect it to contain only numbers.

### Why it happens

Usually because the column has mixed values, a few missing entries , or some odd characters hiding around. And then the loader basically gives up and treats the whole column as text, even if most rows look fine.

### What to do about it

- Clean those inconsistent values before you load anything
- When possible, pass explicit datatype definitions so pandas does not guess
- Also check for empty spaces, stray symbols, or any invalid tokens in numeric columns

### Quick example

```python
import pandas as pd

df = pd.read_csv("data.csv", dtype={"age": int})
print(df.dtypes)
```


## ValidationResult.passed returning false 

### Problem 

There are times when a dataset looks valid but when it goes through validation checks, it fails. 

### The Reason 

The main reasons this can occur are: the dataset has missing or incorrect data types, there is an unexpected null value, or the schema of the dataset does not match what was expected based on the validation rules. 

### How to Fix the Issue 

- Review logs from the validations carefully 
- Look for rows with null or unexpected values 
- Compare the columns in the dataset to see if the names and types of the columns match what you expect them to be 
- Ensure that there are no missing required fields 

### Quick example

```python 
print(validation_result.errors) 
```
---

## Unknown or custom steps not running

### Problem

Sometimes custom pipeline steps fail to execute or appear as unknown during runtime.

### Why it happens

This usually happens when the custom step is not registered correctly or required imports are missing.

### What to do about it
- Confirm that the custom step is registered properly 
- Check any import statements for the customized steps and verify that the names/modules exist 
- Always restart the environment if you've added a new step to the pipeline 
- Validate that your configuration is referencing the proper step name in the pipeline
### Quick example

```python
from pipeline.steps import CustomStep
```

---

##  Slow CSV parsing and performance issues

### Problem

When attempting to load, or to process large CSV files from different sources, it can take a long time for the files to load, or for data within them to be processed.

### Why?

When too many unnecessary columns are being loaded, and when Inference of Datatype has become expensive, and when the entire dataset is processed all at once, the performance of processing these files can be considerably affected.

### How to overcome this problem

- Only load the columns that you actually require.
- Avoid converting datatypes that are unnecessary.
- Process large files in smaller sized chunks.
- Remove unused data before processing.

### Example

```python
# Read large csv file into a Pandas DataFrame
import pandas as pd
df = pd.read_csv('large.csv', usecols=['id', 'name'])
```