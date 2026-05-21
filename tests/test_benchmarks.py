"""Tests for benchmark dataset helpers."""

import pandas as pd
import pytest

import arnio as ar
from benchmarks import benchmark_vs_pandas
from benchmarks.generate_data import generate, generate_sparse_nulls, generate_wide


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


def test_generate_sparse_nulls_round_trips_through_arnio(tmp_path):
    csv_path = tmp_path / "sparse_nulls.csv"

    generate_sparse_nulls(rows=10, path=csv_path, null_density=0.2)

    pandas_df = pd.read_csv(csv_path)
    frame = ar.read_csv(csv_path)
    arnio_df = ar.to_pandas(frame)

    assert pandas_df.shape == (10, 6)
    assert frame.shape == (10, 6)
    assert arnio_df.shape == (10, 6)
    assert arnio_df.columns.tolist() == pandas_df.columns.tolist()


def test_generate_sparse_nulls_zero_density_has_no_nulls(tmp_path):
    csv_path = tmp_path / "sparse_no_nulls.csv"

    generate_sparse_nulls(rows=20, path=csv_path, null_density=0.0)

    df = pd.read_csv(csv_path)
    assert df.isnull().sum().sum() == 0


def test_generate_sparse_nulls_full_density_all_nulls(tmp_path):
    csv_path = tmp_path / "sparse_all_nulls.csv"

    generate_sparse_nulls(rows=10, path=csv_path, null_density=1.0)

    df = pd.read_csv(csv_path)
    assert not df["id"].isnull().any()
    for col in ["age", "salary", "name", "city", "active"]:
        assert df[col].isnull().all()


def test_generate_wide_rejects_too_few_columns(tmp_path):
    csv_path = tmp_path / "too_narrow.csv"

    with pytest.raises(ValueError, match="at least 4 columns"):
        generate_wide(rows=4, columns=3, path=csv_path)


def test_run_case_benchmarks_the_selected_case_path(monkeypatch):
    seen_calls = []

    def fake_run_subprocess(engine, path):
        seen_calls.append((engine, path))
        return {"elapsed": 1.0, "peak_trace_mb": 1.0, "peak_rss_mb": 2.0}

    monkeypatch.setattr(benchmark_vs_pandas, "RUNS", 2)
    monkeypatch.setattr(benchmark_vs_pandas, "run_subprocess", fake_run_subprocess)

    benchmark_vs_pandas.run_case(
        benchmark_vs_pandas.BenchmarkCase("Wide fixture", "wide.csv"),
        skip_correctness=True,
    )

    assert seen_calls == [
        ("pandas", "wide.csv"),
        ("arnio", "wide.csv"),
        ("pandas", "wide.csv"),
        ("arnio", "wide.csv"),
    ]
