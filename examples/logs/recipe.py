"""
Recipe: Application Log Cleaning
---------------------------------
Demonstrates: scan_csv, pipeline, profile, validate

Common issues in this dataset:
  - Mixed-case log levels ("ERROR", "error") and service names ("AUTH-SERVICE")
  - Duplicate log line (log_id 4 appears twice)
  - Missing log level — filled with "unknown"
  - Missing timestamp and service (rows dropped — unattributable)

Run:
    pip install arnio
    python recipe.py
"""

import arnio as ar

# Scan the csv to infer schema and data types
schema_map = ar.scan_csv("messy_logs.csv")
print("=== Inferred Schema ===")
for col, dtype in schema_map.items():
    print(f"  {col}: {dtype}")
print()

# Load from csv using inferred schema
frame = ar.read_csv("messy_logs.csv")
print(f"Loaded: {frame.shape[0]} rows × {frame.shape[1]} columns\n")

# Profile the raw data to identify quality issues
clean_frame = ar.pipeline(
    frame,
    [
        ("strip_whitespace",),
        ("normalize_case", {"case_type": "lower"}),
        ("drop_duplicates",),
        ("fill_nulls", {"value": "unknown", "subset": ["level"]}),
        ("drop_nulls", {"subset": ["timestamp", "service"]}),
    ],
)

# Clean Result
report = ar.profile(clean_frame)
print("Post-Clean Quality Report")
print(f"  Rows: {report.row_count}  |  Duplicates: {report.duplicate_rows}")
for col, p in report.columns.items():
    print(f"  {col:12s}: nulls={p.null_count}")
print()

# Validate the cleaned data against a schema
schema = ar.Schema(
    {
        "log_id": ar.Int64(nullable=False),
        "level": ar.String(
            nullable=False, allowed={"info", "warn", "error", "debug", "unknown"}
        ),
        "service": ar.String(nullable=False),
        "message": ar.String(nullable=True),
    }
)
result = ar.validate(clean_frame, schema)
print(" Validation Result:")
if result.passed:
    print(" All checks passed")
else:
    for issue in result.issues:
        print(f" [{issue.column}] row {issue.row_index}: {issue.message}")

# export to pandas for display purposes
df = ar.to_pandas(clean_frame)
print(f"\n--- Clean Data ({df.shape[0]} rows) ---")
print(df.to_string(index=False))
