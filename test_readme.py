import arnio as ar

# 1. Load the raw file using the C++ core (no Python overhead)
frame = ar.read_csv("messy_sales_data.csv")

# 2. Define a strict, readable cleaning pipeline
clean_frame = ar.pipeline(
    frame,
    [
        ("strip_whitespace",),
        ("normalize_case", {"case_type": "lower"}),
        ("fill_nulls", {"value": 0.0, "subset": ["revenue"]}),
        ("drop_nulls",),
        ("drop_duplicates",),
    ],
)

# 3. Export to a clean pandas DataFrame and start your analysis!
df = ar.to_pandas(clean_frame)
print(df)

schema = ar.scan_csv("messy_sales_data.csv")
print(schema)
