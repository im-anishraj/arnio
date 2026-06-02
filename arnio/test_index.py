import pandas as pd
import arnio as ar

# String index test
df1 = pd.DataFrame(
    {
        "name": ["Alice", "Bob", "Charlie"],
        "score": [90, 85, 92]
    },
    index=["row_1", "row_2", "row_3"]
)

frame1 = ar.from_pandas(df1)
result1 = ar.to_pandas(frame1)

print("STRING INDEX TEST")
print("Original:", df1.index.tolist())
print("Result  :", result1.index.tolist())
print()


# DATETIME INDEX TEST 👇
df2 = pd.DataFrame(
    {"value": [1, 2, 3]},
    index=pd.date_range("2025-01-01", periods=3)
)

frame2 = ar.from_pandas(df2)
result2 = ar.to_pandas(frame2)

print("DATETIME INDEX TEST")
print("Original:", df2.index)
print("Result  :", result2.index)
print("Match   :", result2.index.equals(df2.index))