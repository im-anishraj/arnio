import arnio as ar
import pandas as pd

df = pd.DataFrame({
    "email": ["alice@example.com", "not-an-email", None],
    "age": [25, -5, 200],
    "name": ["Alice", "Bob", "Charlie"],
})

# Profile — instant data quality overview
report = ar.profile(df)
print(f"Quality Score: {report.quality_score}")  # 0-100

# Validate — check against a schema
schema = ar.Schema({
    "email": ar.Email(nullable=False),
    "age": ar.Int(min=0, max=150),
    "name": ar.String(min_length=1),
})
result = ar.validate(df, schema)
print(f"Passed validation: {result.passed}")   # False
for issue in result.issues:
    print(f"Issue: {issue.column} - {issue.rule} - {issue.message}")

# Clean — declarative cleaning pipeline
cleaned = ar.clean(df, [
    "strip_whitespace",
    "drop_duplicates",
    ("normalize_case", {"case": "lower"}),
])
print(cleaned)

# Suggest — intelligent cleaning suggestions
suggestions = ar.suggest(df)
for suggestion in suggestions:
    print(f"Suggestion: {suggestion['step']} ({suggestion['reason']})")
