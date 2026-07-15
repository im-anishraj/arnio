import pandas as pd
import arnio as ar
import random
import string
import gc
import traceback
import sys

def random_string(length):
    return ''.join(random.choices(string.ascii_letters + string.digits + " !@#$%^&*()", k=length))

def generate_chaos_data(rows: int) -> pd.DataFrame:
    data = {
        "id": [random.randint(-1000, 10000) if random.random() > 0.1 else None for _ in range(rows)],
        "name": [random_string(random.randint(0, 100)) if random.random() > 0.2 else None for _ in range(rows)],
        "email": [random_string(10) + "@" + random_string(5) + ".com" if random.random() > 0.5 else random_string(20) for _ in range(rows)],
        "age": [random.randint(-50, 150) if random.random() > 0.1 else "invalid_age" for _ in range(rows)],
        "score": [random.uniform(-100.0, 200.0) if random.random() > 0.1 else float('inf') for _ in range(rows)],
        # Add random unicode and missing values
        "mixed_unicode": ["こんにちは" if random.random() > 0.5 else "😂" for _ in range(rows)],
    }
    return pd.DataFrame(data)

schema = ar.Schema({
    "id": ar.Int(min=0),
    "name": ar.String(max_length=50, nullable=True),
    "email": ar.Email(nullable=True),
    "age": ar.Int(min=0, max=120),
    "score": ar.Float(min=0.0, max=100.0),
    "mixed_unicode": ar.String(nullable=True)
})

pipeline = ar.Pipeline([
    "strip_whitespace",
    ("normalize_case", {"columns": ["email", "name", "mixed_unicode"], "case": "lower"}),
    ("fill_nulls", {"column": "name", "value": "Unknown"}),
    ("drop_nulls", {"columns": ["id"]})
])

def run_chaos(iterations=5):
    print(f"\n--- Running Chaos Testing ({iterations} iterations) ---")
    
    for i in range(iterations):
        rows = random.randint(100, 50_000)
        df = generate_chaos_data(rows)
        
        try:
            # 1. Profile
            report = ar.profile(df)
            
            # 2. Validate
            result = ar.validate(df, schema)
            
            # 3. Clean
            cleaned = pipeline.run(df)
            
        except Exception as e:
            print(f"CHAOS TEST FAILED ON ITERATION {i}")
            print(f"Rows: {rows}")
            traceback.print_exc()
            sys.exit(1)
            
    print("Chaos testing passed! All operations handled the corrupted data gracefully.")

if __name__ == "__main__":
    run_chaos(10)
