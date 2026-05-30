import arnio as ar
import os

# Create a dummy CSV
csv_path = "dummy_chunked.csv"
with open(csv_path, "w") as f:
    f.write("a,b\n")
    for i in range(100):
        if i % 2 == 0:
            f.write(f"{i},\n")
        else:
            f.write(f"{i},{i*2}\n")

# Test reading chunked
print("Testing chunksize in read_csv...")
chunked = ar.read_csv(csv_path, chunksize=10)
assert type(chunked).__name__ == "ChunkedArFrame"

# Test pipeline lazily
print("Testing pipeline on ChunkedArFrame...")
pipelined = ar.pipeline(chunked, [("drop_nulls",)])
assert type(pipelined).__name__ == "ChunkedArFrame"

# Materialize to pandas
print("Testing to_pandas()...")
df = pipelined.to_pandas()
# Since half of 100 are nulls in column 'b', we expect 50 rows remaining
assert len(df) == 50, f"Expected 50 rows, got {len(df)}"

# Test full pass validation
print("Testing _FULL_PASS_STEPS validation...")
try:
    ar.pipeline(chunked, [("drop_duplicates",)])
    raise AssertionError("Should have raised ValueError")
except ValueError as e:
    print(f"Correctly caught error: {e}")

os.remove(csv_path)
print("All tests passed!")
