import pandas as pd
import arnio as ar

df = pd.DataFrame(
    {
        "name": ["Alice", "Bob", "Charlie"],
        "score": [90, 85, 92],
    },
    index=["row_1", "row_2", "row_3"],
)

print("Original:")
print(df)

frame = ar.from_pandas(df)

result = ar.to_pandas(frame)

print("\nAfter round trip:")
print(result)

print("\nOriginal index:")
print(df.index)

print("\nReturned index:")
print(result.index)