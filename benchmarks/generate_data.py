"""Generate deterministic benchmark CSV files before benchmarking."""

import numpy as np
import pandas as pd

DEFAULT_TALL_PATH = "benchmarks/benchmark_1m.csv"
DEFAULT_WIDE_PATH = "benchmarks/benchmark_wide.csv"
DEFAULT_SPARSE_NULL_PATH = "benchmarks/benchmark_sparse_null.csv"


def generate(rows=1_000_000, path=DEFAULT_TALL_PATH):
    rng = np.random.default_rng(42)
    df = pd.DataFrame(
        {
            "id": rng.integers(1, 999999, rows),
            "name": np.where(
                rng.random(rows) > 0.05,
                rng.choice(["  Alice", "BOB  ", " charlie", "DIANA "], rows),
                None,
            ),
            "revenue": np.where(
                rng.random(rows) > 0.08, rng.uniform(100, 99999, rows).round(2), None
            ),
            "age": rng.integers(18, 80, rows).astype(float),
            "city": rng.choice(["  Mumbai", "DELHI  ", " bangalore", None], rows),
            "score": rng.uniform(0, 100, rows).round(4),
            "active": rng.choice(["true", "false", "TRUE", "FALSE", None], rows),
            "category": rng.choice(["  A", "B  ", " C", "D "], rows),
            "visits": rng.integers(0, 500, rows),
            "amount": rng.uniform(0, 5000, rows).round(2),
            "region": rng.choice(["NORTH", "south", " East", "WEST  "], rows),
            "code": rng.integers(1000, 9999, rows),
        }
    )
    df.to_csv(path, index=False, lineterminator="\n")
    print(f"Generated {rows:,} row CSV -> {path}")


def generate_wide(rows=5_000, columns=256, path=DEFAULT_WIDE_PATH):
    if rows < 1:
        raise ValueError("wide benchmark requires at least 1 row")
    if columns < 4:
        raise ValueError("wide benchmark requires at least 4 columns")

    rng = np.random.default_rng(252)
    data = {"row_id": np.arange(rows)}

    for index in range(columns - 1):
        column_id = f"{index:03d}"
        kind = index % 4

        if kind == 0:
            data[f"metric_{column_id}"] = rng.normal(1_000, 250, rows).round(4)
        elif kind == 1:
            values = rng.choice(
                ["  alpha", "BETA  ", " gamma", "DELTA ", None],
                rows,
            )
            values[0] = "  alpha"
            data[f"label_{column_id}"] = values
        elif kind == 2:
            values = rng.choice(
                ["true", "false", "TRUE", "FALSE", None],
                rows,
            )
            values[0] = "true"
            data[f"flag_{column_id}"] = values
        else:
            data[f"amount_{column_id}"] = rng.uniform(0, 10_000, rows).round(2)

    df = pd.DataFrame(data)
    df.to_csv(path, index=False, lineterminator="\n")
    print(f"Generated {rows:,} row x {columns:,} column CSV -> {path}")


def generate_sparse_null(rows=500_000, path=DEFAULT_SPARSE_NULL_PATH):
    """Generates a deterministic dataset with highly concentrated missing values (95%+ nulls) to benchmark sparse null masks."""
    rng = np.random.default_rng(999)
    
    df = pd.DataFrame(
        {
            "id": rng.integers(1, 999999, rows),
            # 95% missing text values
            "sparse_comment": np.where(rng.random(rows) > 0.95, "Flagged Workload Entry", None),
            # 98% missing float numbers
            "sparse_tax_rate": np.where(rng.random(rows) > 0.98, rng.uniform(5, 28, rows).round(2), None),
            "age": rng.integers(1, 100, rows).astype(float),
            # 97% missing binary choices
            "sparse_verified": np.where(rng.random(rows) > 0.97, rng.choice(["TRUE", "FALSE"], rows), None),
            "score": rng.uniform(0, 10, rows).round(2),
            # 99% missing localized labels
            "sparse_region_code": np.where(rng.random(rows) > 0.99, rng.choice(["LOC_A", "LOC_B"], rows), None),
        }
    )
    df.to_csv(path, index=False, lineterminator="\n")
    print(f"Generated {rows:,} row Sparse-Null CSV -> {path}")


if __name__ == "__main__":
    generate()
    generate_wide()
    generate_sparse_null()