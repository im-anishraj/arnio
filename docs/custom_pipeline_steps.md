\# Custom Pipeline Step Cookbook



This guide shows you how to write your own custom cleaning steps for arnio pipelines.

No C++ required — custom steps are pure Python.



\---



\## What is a Custom Step?



Arnio comes with built-in steps like `strip\_whitespace` and `drop\_nulls`.

A custom step lets you add your own cleaning logic and use it inside `ar.pipeline()` just like any built-in step.



\---



\## The Basic Pattern



Every custom step follows this shape:



```python

import pandas as pd



def my\_custom\_step(df: pd.DataFrame, \*\*kwargs) -> pd.DataFrame:

&#x20;   # do something to df

&#x20;   return df

```



\*\*Rules:\*\*

\- Input is always a `pd.DataFrame`

\- Output must always be a `pd.DataFrame`

\- Never modify the original — work on a copy

\- Always return the full DataFrame, not just one column



\---



\## Step 1: Write Your Function



```python

import pandas as pd



def remove\_special\_chars(df: pd.DataFrame, columns=None) -> pd.DataFrame:

&#x20;   """

&#x20;   Removes special characters from string columns.

&#x20;   Keeps only letters, numbers, and spaces.

&#x20;   

&#x20;   Args:

&#x20;       df: Input DataFrame

&#x20;       columns: List of columns to clean. If None, cleans all string columns.

&#x20;   

&#x20;   Returns:

&#x20;       Cleaned DataFrame

&#x20;   """

&#x20;   df = df.copy()

&#x20;   cols = columns or df.select\_dtypes("object").columns.tolist()

&#x20;   for col in cols:

&#x20;       df\[col] = df\[col].str.replace(r"\[^a-zA-Z0-9\\s]", "", regex=True)

&#x20;   return df

```



\---



\## Step 2: Register Your Step



```python

import arnio as ar



ar.register\_step("remove\_special\_chars", remove\_special\_chars)

```



Now arnio knows about your step by name.



\---



\## Step 3: Use It in a Pipeline



```python

frame = ar.read\_csv("messy\_data.csv")



clean = ar.pipeline(frame, \[

&#x20;   ("strip\_whitespace",),

&#x20;   ("remove\_special\_chars",),

&#x20;   ("drop\_nulls",),

])



df = ar.to\_pandas(clean)

```



\---



\## Practical Examples



\### Example 1: Remove Special Characters



\*\*Use case:\*\* Your data has symbols like `@`, `#`, `!` in name or city columns.



```python

import pandas as pd

import arnio as ar



def remove\_special\_chars(df: pd.DataFrame, columns=None) -> pd.DataFrame:

&#x20;   df = df.copy()

&#x20;   cols = columns or df.select\_dtypes("object").columns.tolist()

&#x20;   for col in cols:

&#x20;       df\[col] = df\[col].str.replace(r"\[^a-zA-Z0-9\\s]", "", regex=True)

&#x20;   return df



ar.register\_step("remove\_special\_chars", remove\_special\_chars)



\# Usage

clean = ar.pipeline(frame, \[

&#x20;   ("remove\_special\_chars",),

])

```



\*\*Input:\*\*

| name | city |

|------|------|

| John! | New@York |

| Jane# | Los#Angeles |



\*\*Output:\*\*

| name | city |

|------|------|

| John | NewYork |

| Jane | LosAngeles |



\---



\### Example 2: Capitalize First Letter of Each Word



\*\*Use case:\*\* Names and cities stored in random case.



```python

def title\_case\_columns(df: pd.DataFrame, columns=None) -> pd.DataFrame:

&#x20;   df = df.copy()

&#x20;   cols = columns or df.select\_dtypes("object").columns.tolist()

&#x20;   for col in cols:

&#x20;       df\[col] = df\[col].str.title()

&#x20;   return df



ar.register\_step("title\_case\_columns", title\_case\_columns)



\# Usage

clean = ar.pipeline(frame, \[

&#x20;   ("title\_case\_columns",),

])

```



\*\*Input:\*\*

| name |

|------|

| john doe |

| JANE SMITH |



\*\*Output:\*\*

| name |

|------|

| John Doe |

| Jane Smith |



\---



\### Example 3: Clamp Numeric Values



\*\*Use case:\*\* Remove outliers by capping values within a valid range.



```python

def clamp\_values(df: pd.DataFrame, column: str, min\_val: float, max\_val: float) -> pd.DataFrame:

&#x20;   df = df.copy()

&#x20;   df\[column] = df\[column].clip(lower=min\_val, upper=max\_val)

&#x20;   return df



ar.register\_step("clamp\_values", clamp\_values)



\# Usage

clean = ar.pipeline(frame, \[

&#x20;   ("clamp\_values", {"column": "age", "min\_val": 0, "max\_val": 120}),

])

```



\*\*Input:\*\*

| age |

|-----|

| 25 |

| -5 |

| 999 |



\*\*Output:\*\*

| age |

|-----|

| 25 |

| 0 |

| 120 |



\---



\## Testing Your Custom Step



Always test your step before using it in a pipeline.



```python

import pandas as pd



def test\_remove\_special\_chars():

&#x20;   # Arrange

&#x20;   df = pd.DataFrame({"name": \["John!", "Jane#"], "city": \["New@York", "LA"]})

&#x20;   

&#x20;   # Act

&#x20;   result = remove\_special\_chars(df)

&#x20;   

&#x20;   # Assert

&#x20;   assert result\["name"].tolist() == \["John", "Jane"]

&#x20;   assert result\["city"].tolist() == \["NewYork", "LA"]

&#x20;   print("All tests passed!")



test\_remove\_special\_chars()

```



\*\*What to test:\*\*

\- Normal input — does it work correctly?

\- Empty DataFrame — does it return without errors?

\- Columns with no string data — does it skip them safely?

\- Original DataFrame — make sure it is not modified (always use `df.copy()`)



\---



\## Common Mistakes to Avoid



| Mistake | Why it's a problem | Fix |

|---|---|---|

| Forgetting `df.copy()` | Modifies original data | Always copy first |

| Returning a column instead of DataFrame | Pipeline breaks | Always return full `df` |

| Hardcoding column names | Step won't work on other datasets | Accept `columns` as a parameter |

| Not handling NaN values | Causes errors on empty cells | Use `.fillna()` or check first |



\---



\## Quick Reference



```python

\# 1. Write your function

def my\_step(df: pd.DataFrame, \*\*kwargs) -> pd.DataFrame:

&#x20;   df = df.copy()

&#x20;   # your logic here

&#x20;   return df



\# 2. Register it

ar.register\_step("my\_step", my\_step)



\# 3. Use it

clean = ar.pipeline(frame, \[("my\_step",)])

```

