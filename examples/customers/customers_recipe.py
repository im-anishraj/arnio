"""
Recipe: Customer Data Cleaning
================================
Demonstrates: profile, suggest_cleaning, pipeline, validate

Common issues in this dataset:
  - Mixed-case names ("DUPLI CATE", "bablu kumar") and cities ("SEATTLE")
  - Extra whitespace padding in name and city (" Dev Raj ", " Mumbai ")
  - Missing city — filled with "unknown"
  - Missing name (row with no name — dropped, cannot be attributed)
  - Missing email (dropped — required for contact)
  - Duplicate customer record (customer_id 102 appears twice)

Run:
    pip install arnio
    python customers_recipe.py
"""

import arnio as ar

# Loading the dataset from .csv file
frame = ar.read_csv("messy_customers.csv")
print(f"Loaded: {frame.shape[0]} rows × {frame.shape[1]} columns\n")

suggestions = ar.suggest_cleaning(frame)
print("--Suggested Cleaning Steps --")
for name, kwargs in suggestions:
    print(f"  • {name}: {kwargs}")
print()

# Pipelinne
clean_frame = ar.pipeline(frame, [
    ("strip_whitespace",),                                       
    ("normalize_case", {"case_type": "title"}),                 
    ("drop_duplicates",),                                        
    ("fill_nulls", {"value": "Unknown", "subset": ["city"]}),   
    ("drop_nulls", {"subset": ["name", "email"]}),              
])

# validate the cleaned data against a schema
schema = ar.Schema({
    "customer_id": ar.Int64(nullable=False, unique=True),
    "name":        ar.String(nullable=False),
    "email":       ar.Email(nullable=False, unique=True),
    "age":         ar.Int64(nullable=True, min=0, max=120),
})
result = ar.validate(clean_frame, schema)
print("Validation Result:")
if result.passed:
    print("  All checks passed")
else:
    for issue in result.issues:
        print(f"  [{issue.column}] {issue.message}")

#Export to pandas for display purposes
df = ar.to_pandas(clean_frame)
print(f"\n--Cleaned Data ({df.shape[0]} rows) --")
print(df.to_string())
