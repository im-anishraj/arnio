"""
Arnio + pandas interoperability example

This example demonstrates how to:
1. Start with messy data in pandas
2. Clean and normalize it using Arnio's pipeline
3. Convert it back to pandas for analysis

Key idea:
Arnio is used for cleaning/validation, while pandas is used for analysis.
"""
import arnio as ar
import pandas as pd

# Step 1: Create messy dataset (pandas)
df = pd.DataFrame({
    "name": [" Alice ", "Bob", "CHARLIE", None],
    "age": ["25", "30", None, "40"],
})

print("Original Data:")
print(df)
print("-" * 40)

# Step 2: Convert pandas → Arnio
frame = ar.from_pandas(df)

# Step 3: Clean data using Arnio pipeline
cleaned = ar.pipeline(
    frame,
    [
        ("drop_nulls",),
        ("strip_whitespace",),
        ("normalize_case", {"case_type": "lower"}),
        ("cast_types", {"mapping": {"age": "int64"}}),
    ],
)

# Step 4: Convert Arnio → pandas
clean_df = ar.to_pandas(cleaned)

print("Cleaned Data:")
print(clean_df)
print("-" * 40)

# Step 5: Use pandas for analysis
print("Summary Statistics:")
print(clean_df.describe())
if __name__ == "__main__":
    pass