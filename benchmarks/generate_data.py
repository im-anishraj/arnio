"""Generate deterministic benchmark CSV files before benchmarking."""

import numpy as np
import pandas as pd

DEFAULT_TALL_PATH = "benchmarks/benchmark_1m.csv"
DEFAULT_WIDE_PATH = "benchmarks/benchmark_wide.csv"
DEFAULT_MULTILINE_PATH = "benchmarks/benchmark_multiline.csv"


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
def generate_multiline(
    rows=100_000,
    path=DEFAULT_MULTILINE_PATH,
    multiline_ratio=0.3,
):
    """
    Generate deterministic multiline benchmark CSV.

    Used for benchmarking quoted multiline CSV parsing.
    """

    if rows < 1:
        raise ValueError(
            "multiline benchmark requires at least 1 row"
        )

    rng = np.random.default_rng(512)

    multiline_templates = [
        "First line\nSecond line",
        "hello world\nthis is multiline text",
        "alpha\nbeta\ngamma",
        "quoted field\nwith embedded newline",
        "line1\nline2\nline3",
    ]

    singleline_templates = [
        "simple text",
        "benchmark row",
        "plain csv value",
        "single line content",
    ]

    descriptions = []

    for _ in range(rows):
        if rng.random() < multiline_ratio:
            descriptions.append(
                rng.choice(multiline_templates)
            )
        else:
            descriptions.append(
                rng.choice(singleline_templates)
            )

    df = pd.DataFrame(
        {
            "id": np.arange(rows),
            "description": descriptions,
            "category": rng.choice(
                ["A", "B", "C"],
                rows,
            ),
            "value": rng.uniform(
                0,
                1000,
                rows,
            ).round(2),
        }
    )

    df.to_csv(
        path,
        index=False,
        lineterminator="\n",
    )

    print(
        f"Generated multiline benchmark CSV -> {path}"
    )
if __name__ == "__main__":
    generate()
    generate_wide()
    generate_multiline()
