# issue 397 solve
# Clean → Query
import arnio as ar
import pandas as pd
import duckdb

data = {
    "name": ["Alice", "Bob", None],
    "salary": [50000, 60000, 70000]
}

df = pd.DataFrame(data)

frame = ar.from_pandas(df)

clean = ar.pipeline(frame, [
    ("drop_nulls",),
])

clean_df = ar.to_pandas(clean)

result = duckdb.query(
    "SELECT AVG(salary) FROM clean_df"
).to_df()

print(result)