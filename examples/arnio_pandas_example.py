import pandas as pd

data = {
    "age": [20, None, "25", "invalid"],
    "name": ["Alice", "Bob", "Charlie", "David"]
}

df = pd.DataFrame(data)

print("Original Data:")
print(df)

df["age"] = pd.to_numeric(df["age"], errors="coerce")
df = df.dropna()

print("\nCleaned Data:")
print(df)
