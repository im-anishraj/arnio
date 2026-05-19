import pandas as pd

df = pd.DataFrame({"A": [1, None, None], "B": [None, 2, None], "C": [3, 4, None]})

subset = ["A", "B", "C"]
separator = "-"

combined = df[subset].astype("string").fillna("").agg(separator.join, axis=1)
null_mask = df[subset].isna().all(axis=1)
combined = combined.mask(null_mask, pd.NA)

df["combined"] = combined
print(df)
