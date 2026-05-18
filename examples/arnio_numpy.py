# issue 397 solve
# Clean → Numeric array
import arnio as ar
import pandas as pd
import numpy as np

data = {
    "values": [1, 2, None, 4]
}

df = pd.DataFrame(data)

frame = ar.from_pandas(df)

clean = ar.pipeline(frame, [
    ("drop_nulls",),
])

clean_df = ar.to_pandas(clean)

arr = clean_df["values"].to_numpy()

print(arr.mean())