"""Tests for the pandas DataFrame accessor."""

import pandas as pd

import arnio as ar


def test_pandas_accessor_converts_to_arframe():
    df = pd.DataFrame({"name": ["Alice"], "age": [30]})

    frame = df.arnio.to_arframe()

    assert isinstance(frame, ar.ArFrame)
    assert frame.shape == (1, 2)
    assert frame.columns == ["name", "age"]


def test_pandas_accessor_runs_explicit_pipeline_without_mutating_source():
    df = pd.DataFrame({"name": [" Alice ", " Bob "], "age": [30, 40]})

    result = df.arnio.clean(
        [
            ("strip_whitespace", {"subset": ["name"]}),
            ("normalize_case", {"subset": ["name"], "case_type": "lower"}),
        ]
    )

    assert isinstance(result, pd.DataFrame)
    assert list(result["name"]) == ["alice", "bob"]
    assert list(df["name"]) == [" Alice ", " Bob "]


def test_pandas_accessor_runs_convenience_clean():
    df = pd.DataFrame({"name": [" Alice ", " Alice "], "score": [10, 10]})

    result = df.arnio.clean(drop_duplicates=True)

    assert list(result["name"]) == ["Alice"]
    assert list(result["score"]) == [10]


def test_pandas_accessor_profiles_dataframe_quality():
    df = pd.DataFrame({"name": [" Alice ", "Bob"], "score": [1.5, None]})

    report = df.arnio.profile()

    assert isinstance(report, ar.DataQualityReport)
    assert report.row_count == 2
    assert report.columns["name"].whitespace_count == 1
    assert report.columns["score"].null_count == 1


def test_pandas_accessor_auto_clean_returns_dataframe_and_report():
    df = pd.DataFrame({"name": [" Alice ", "Bob"]})

    result, report = df.arnio.auto_clean(return_report=True)

    assert isinstance(result, pd.DataFrame)
    assert list(result["name"]) == ["Alice", "Bob"]
    assert isinstance(report, ar.DataQualityReport)


def test_pandas_accessor_validates_dataframe():
    df = pd.DataFrame({"email": ["alice@example.com", "bad"]})

    result = df.arnio.validate({"email": ar.Email(nullable=False)})

    assert isinstance(result, ar.ValidationResult)
    assert not result.passed
    assert result.issues[0].rule == "email"
