"""
Recipe: Financial Transaction Cleaning
 <-------------------------------->
Demonstrates: auto_clean, pipeline, profile, validate

Common issues in this dataset:
  - Mixed-case transaction types ("DEBIT", "Debit", "credit")
  - Mixed-case currency codes ("USD", "usd")
  - Duplicate transaction (T002 appears twice)
  - Missing amount — filled with 0.0 and flagged by validator
  - Missing account number — rows dropped (cannot post to ledger)
  - Empty notes — filled with "n/a"

Run:
    pip install arnio
    python recipe.py

"""

import arnio as ar

# Load from csv
frame = ar.read_csv("messy_finance.csv")
print(f"Loaded: {frame.shape[0]} rows × {frame.shape[1]} columns\n")

# Cleaning
frame, pre_report = ar.auto_clean(frame, mode="safe", return_report=True)
print("<--- Pre-Clean Summary --->")
summary = pre_report.summary()
total_nulls = sum(p.null_count for p in pre_report.columns.values())
print(f"  Duplicate rows : {summary['duplicate_rows']}")
print(f"  Columns w/ nulls: {summary['columns_with_nulls']}")
print(f"  Total nulls    : {total_nulls}\n")

# Pipeline
clean_frame = ar.pipeline(
    frame,
    [
        ("normalize_case", {"case_type": "upper", "subset": ["type", "currency"]}),
        ("drop_duplicates",),
        ("fill_nulls", {"value": 0.0, "subset": ["amount"]}),
        ("fill_nulls", {"value": "n/a", "subset": ["notes"]}),
        ("drop_nulls", {"subset": ["account"]}),
    ],
)

# validate the cleaned data against a schema
schema = ar.Schema(
    {
        "txn_id": ar.String(nullable=False, unique=True),
        "type": ar.String(nullable=False, allowed={"DEBIT", "CREDIT"}),
        "amount": ar.Float64(nullable=False, min=0.0),
        "currency": ar.String(nullable=False, allowed={"USD", "GBP", "EUR"}),
        "account": ar.String(nullable=False),
    }
)
result = ar.validate(clean_frame, schema)
print("Validation Result:")
if result.passed:
    print("  All checks passed")
else:
    for issue in result.issues:
        print(f"   [{issue.column}] row {issue.row_index}: {issue.message}")

# export
df = ar.to_pandas(clean_frame)
print(f"\n-- Clean Data ({df.shape[0]} rows) --")
print(df.to_string(index=False))
