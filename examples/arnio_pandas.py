# issue 397 solve
# Clean → Analyze
import arnio as ar
import pandas as pd

# Step 1: Create messy data
data = {
    "name": [" Alice ", "Bob", "alice", None],
    "age": [25, None, 25, 30]
}

df = pd.DataFrame(data)

# Step 2: Convert to Arnio
frame = ar.from_pandas(df)

# Step 3: Clean
clean = ar.pipeline(frame, [
    ("strip_whitespace",),
    ("drop_nulls",),
    ("drop_duplicates",),
])

# Step 4: Back to pandas
clean_df = ar.to_pandas(clean)

# Step 5: Analyze
print(clean_df.describe())