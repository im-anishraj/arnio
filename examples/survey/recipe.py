"""
Recipe: Survey Response Cleaning
===================================
Demonstrates: profile, pipeline, validate

Common issues in this dataset:
  - Mixed-case satisfaction labels ("SATISFIED", "Satisfied", "very dissatisfied")
  - Duplicate submission (response_id 2 appears twice)
  - Missing respondent name (rows dropped — cannot be attributed)
  - Missing satisfaction + nps_score (kept but flagged via validation)
  - Whitespace in free-text comments (" no comment ")
  - Missing comments — filled with "no response"

Run:
    pip install arnio
    python recipe.py
"""

import arnio as ar

# Load from csv
frame = ar.read_csv("messy_survey.csv")
print(f"Loaded: {frame.shape[0]} rows × {frame.shape[1]} columns\n")

# Profile the raw data to identify quality issues
report = ar.profile(frame)
print("=== Data Quality Report ===")
print(f"  Duplicate rows : {report.duplicate_rows}")
for col, p in report.columns.items():
    print(f"  {col:15s}: nulls={p.null_count}, whitespace={p.whitespace_count}")
print()

# Pipeline — clean step by step
clean_frame = ar.pipeline(
    frame,
    [
        ("strip_whitespace",),  # trim " no comment "
        ("normalize_case", {"case_type": "lower"}),  # unify satisfaction labels
        ("drop_duplicates",),  # remove duplicate response_id 2
        (
            "fill_nulls",
            {"value": "no response", "subset": ["comments"]},
        ),  # tag blank comments
        ("drop_nulls", {"subset": ["respondent"]}),  # drop anonymous rows
    ],
)

# validate the cleaned data against a schema
schema = ar.Schema(
    {
        "response_id": ar.Int64(nullable=False, unique=True),
        "respondent": ar.String(nullable=False),
        "nps_score": ar.Int64(nullable=True, min=0, max=10),
        "satisfaction": ar.String(
            nullable=True,
            allowed={
                "very satisfied",
                "satisfied",
                "neutral",
                "dissatisfied",
                "very dissatisfied",
            },
        ),
    }
)
result = ar.validate(clean_frame, schema)
print("Validation Result:")
if result.passed:
    print(" All checks passed")
else:
    for issue in result.issues:
        print(f"   [{issue.column}] row {issue.row_index}: {issue.message}")

# export to pandas for display purposes
df = ar.to_pandas(clean_frame)
print(f"\n--- Clean Data ({df.shape[0]} rows) ---")
print(df.to_string(index=False))
