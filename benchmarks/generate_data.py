"""Generate deterministic benchmark CSV files before benchmarking."""

import os

import numpy as np
import pandas as pd

DEFAULT_TALL_PATH = "benchmarks/benchmark_1m.csv"
DEFAULT_WIDE_PATH = "benchmarks/benchmark_wide.csv"

DRY_RUN = os.getenv("ARNIO_BENCHMARK_DRY_RUN") == "1"


def generate(rows=1_000_000, path=DEFAULT_TALL_PATH):
    if DRY_RUN:
        rows = min(rows, 10)
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
    if DRY_RUN:
        rows = min(rows, 5)
        columns = min(columns, 10)
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


DEFAULT_MULTILINE_PATH = "benchmarks/benchmark_multiline.csv"


def generate_multiline(rows=100_000, path=DEFAULT_MULTILINE_PATH):
    if DRY_RUN:
        rows = min(rows, 10)
    rng = np.random.default_rng(999)
    df = pd.DataFrame(
        {
            "id": rng.integers(1, 999999, rows),
            "comments": rng.choice(
                [
                    "line 1\nline 2",
                    "simple text",
                    "another\nmultiline\ncomment",
                    "short comment",
                    'quoted "inner" text\nwith newlines',
                ],
                rows,
            ),
            "score": rng.uniform(0, 100, rows).round(4),
            "notes": rng.choice(
                [
                    "first note\nsecond note",
                    "no newline",
                    "yet\nanother\nmultiline\nnote",
                ],
                rows,
            ),
        }
    )
    df.to_csv(path, index=False, lineterminator="\n")
    print(f"Generated {rows:,} row Multiline CSV -> {path}")


DEFAULT_SPARSE_NULLS_PATH = "benchmarks/benchmark_sparse_nulls.csv"


def generate_sparse_nulls(rows=1_000_000, path=DEFAULT_SPARSE_NULLS_PATH, null_density=0.01, seed=42):
    """Generate a deterministic CSV with controlled null density across mixed column types."""
    if DRY_RUN:
        rows = min(rows, 10)
    rng = np.random.default_rng(seed)
    data = {
        "id": rng.integers(1, 999999, rows).tolist(),
        "age": np.where(
            rng.random(rows) < null_density, None, rng.integers(18, 80, rows)
        ).tolist(),
        "salary": np.where(
            rng.random(rows) < null_density,
            None,
            rng.uniform(30000, 150000, rows).round(2),
        ).tolist(),
        "name": np.where(
            rng.random(rows) < null_density,
            None,
            rng.choice(["Alice", "Bob", "Charlie", "Diana"], rows),
        ).tolist(),
        "city": np.where(
            rng.random(rows) < null_density,
            None,
            rng.choice(["New York", "London", "Paris", "Tokyo"], rows),
        ).tolist(),
        "active": np.where(
            rng.random(rows) < null_density,
            None,
            rng.choice([True, False], rows),
        ).tolist(),
    }
    df = pd.DataFrame(data)
    df.to_csv(path, index=False, lineterminator="\n")
    label = f"null_density={null_density:.1%}"
    if DRY_RUN:
        label += " (dry-run)"
    print(f"Generated {rows:,} row sparse-null CSV ({label}) -> {path}")


if __name__ == "__main__":
    generate()
    generate_wide()
    generate_multiline()
    generate_sparse_nulls()
    generate_sparse_nulls(path="benchmarks/benchmark_sparse_nulls_dense.csv", null_density=0.2, seed=99)
