"""
Recipe: Sales Data Cleaning
============================
Demonstrates: pipeline, profile, validate

Common issues in this dataset:
  - Leading/trailing whitespace in product and region columns
  - Mixed-case region names ("NORTH", "south", "EAST")
  - Duplicate rows (order_id 2 appears twice)
  - Missing revenue (filled with 0.0 — flagged for review)
  - Missing product name (rows dropped as incomplete)

Run:
    pip install arnio
    python sales_recipe.py
"""

import arnio as ar

#Load from csv
frame = ar.read_csv("messy_sales.csv")
print(f"Loaded: {frame.shape[0]} rows × {frame.shape[1]} columns")
print(f"Columns: {frame.columns}\n")

# Profile the raw data to identify quality issues
report = ar.profile(frame)
print("=== Data Quality Report ===")
for col, p in report.columns.items():
    print(f"  {col}: nulls={p.null_count}, unique={p.unique_count}, whitespace={p.whitespace_count}")
print(f"  Duplicate rows: {report.duplicate_rows}\n")

# Clean the data using a pipeline of transformations
clean_frame = ar.pipeline(frame, [
    ("strip_whitespace",),                                
    ("normalize_case", {"case_type": "lower"}),               
    ("drop_duplicates",),                                        
    ("fill_nulls", {"value": 0.0, "subset": ["revenue"]}),    
    ("drop_nulls", {"subset": ["product"]}),                    
])

# validate the cleaned data against a schema
schema = ar.Schema({
    "order_id": ar.Int64(nullable=False, unique=True),
    "product":  ar.String(nullable=False),
    "revenue":  ar.Float64(nullable=False, min=0.0),
    "region":   ar.String(nullable=False, allowed={"north", "south", "east", "west"}),
})
result = ar.validate(clean_frame, schema)
print("=== Validation ===")
if result.passed:
    print("  All checks passed")
else:
    for issue in result.issues:
        print(f"  ⚠ [{issue.column}] {issue.message}")

# export to pandas for display purposes
df = ar.to_pandas(clean_frame)
print(f"\n=== Clean Data ({df.shape[0]} rows) ===")
print(df.to_string(index=False))
