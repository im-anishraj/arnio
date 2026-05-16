"""Tests for benchmark dataset helpers."""

import pandas as pd
import pytest

import arnio as ar
from benchmarks import benchmark_vs_pandas
from benchmarks.generate_data import generate, generate_wide


def test_generate_tall_benchmark_csv_shape(tmp_path):
    csv_path = tmp_path / "benchmark_tall.csv"

    generate(rows=5, path=csv_path)

    df = pd.read_csv(csv_path)
    assert df.shape == (5, 12)
    assert list(df.columns) == [
        "id",
        "name",
        "revenue",
        "age",
        "city",
        "score",
        "active",
        "category",
        "visits",
        "amount",
        "region",
        "code",
    ]


def test_generate_wide_benchmark_csv_round_trips_through_arnio(tmp_path):
    csv_path = tmp_path / "benchmark_wide.csv"

    generate_wide(rows=4, columns=9, path=csv_path)

    pandas_df = pd.read_csv(csv_path)
    frame = ar.read_csv(csv_path)
    arnio_df = ar.to_pandas(frame)

    assert pandas_df.shape == (4, 9)
    assert frame.shape == (4, 9)
    assert arnio_df.shape == (4, 9)
    assert arnio_df.columns.tolist() == pandas_df.columns.tolist()
    assert list(ar.scan_csv(csv_path).keys()) == list(pandas_df.columns)


def test_generate_wide_rejects_too_few_columns(tmp_path):
    csv_path = tmp_path / "too_narrow.csv"

    with pytest.raises(ValueError, match="at least 4 columns"):
        generate_wide(rows=4, columns=3, path=csv_path)


def test_run_case_benchmarks_the_selected_case_path(monkeypatch):
    seen_paths = []

    def fake_benchmark(path):
        seen_paths.append(path)
        return 1.0, 1.0

    monkeypatch.setattr(benchmark_vs_pandas, "RUNS", 2)
    monkeypatch.setattr(benchmark_vs_pandas, "benchmark_pandas", fake_benchmark)
    monkeypatch.setattr(benchmark_vs_pandas, "benchmark_arnio", fake_benchmark)

    benchmark_vs_pandas.run_case(
        benchmark_vs_pandas.BenchmarkCase("Wide fixture", "wide.csv")
    )

    assert seen_paths == ["wide.csv", "wide.csv", "wide.csv", "wide.csv"]
