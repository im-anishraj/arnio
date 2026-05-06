"""Generate synthetic benchmark CSV — run this before benchmarking."""
import numpy as np
import pandas as pd

def generate(rows=1_000_000, path="benchmarks/benchmark_1m.csv"):
    rng = np.random.default_rng(42)
    df = pd.DataFrame({
        "id":       rng.integers(1, 999999, rows),
        "name":     np.where(rng.random(rows) > 0.05,
                        rng.choice(["  Alice", "BOB  ", " charlie", "DIANA "], rows),
                        None),
        "revenue":  np.where(rng.random(rows) > 0.08,
                        rng.uniform(100, 99999, rows).round(2), None),
        "age":      rng.integers(18, 80, rows).astype(float),
        "city":     rng.choice(["  Mumbai", "DELHI  ", " bangalore", None], rows),
        "score":    rng.uniform(0, 100, rows).round(4),
        "active":   rng.choice(["true", "false", "TRUE", "FALSE", None], rows),
        "category": rng.choice(["  A", "B  ", " C", "D "], rows),
        "visits":   rng.integers(0, 500, rows),
        "amount":   rng.uniform(0, 5000, rows).round(2),
        "region":   rng.choice(["NORTH", "south", " East", "WEST  "], rows),
        "code":     rng.integers(1000, 9999, rows),
    })
    df.to_csv(path, index=False)
    print(f"Generated {rows:,} row CSV → {path}")

if __name__ == "__main__":
    generate()
