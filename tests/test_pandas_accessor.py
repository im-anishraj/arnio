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


# --- Issue: dry_run mode for auto_clean via pandas accessor ---
# Tests added to verify dry_run=True returns report without mutating the frame


def test_pandas_accessor_auto_clean_dry_run_returns_report():
    # dry_run=True should return a DataQualityReport without mutating the frame
    df = pd.DataFrame({"name": [" Alice ", " Bob "]})

    result = df.arnio.auto_clean(dry_run=True)

    assert isinstance(result, ar.DataQualityReport)
    # Original frame must not be mutated
    assert list(df["name"]) == [" Alice ", " Bob "]


def test_pandas_accessor_auto_clean_dry_run_with_return_report():
    # dry_run=True with return_report=True should return (frame, report)
    df = pd.DataFrame({"name": [" Alice ", " Bob "]})

    result = df.arnio.auto_clean(dry_run=True, return_report=True)

    assert isinstance(result, tuple)
    frame, report = result
    assert isinstance(report, ar.DataQualityReport)
    # Original frame must not be mutated
    assert list(df["name"]) == [" Alice ", " Bob "]


def test_pandas_accessor_auto_clean_dry_run_safe_mode():
    # dry_run=True in safe mode should also return report without mutating
    df = pd.DataFrame({"score": ["10", "20", "30"]})

    result = df.arnio.auto_clean(mode="safe", dry_run=True)

    assert isinstance(result, ar.DataQualityReport)
    # Original frame must not be mutated
    assert list(df["score"]) == ["10", "20", "30"]


def test_pandas_accessor_validates_dataframe():
    df = pd.DataFrame({"email": ["alice@example.com", "bad"]})

    result = df.arnio.validate({"email": ar.Email(nullable=False)})

    assert isinstance(result, ar.ValidationResult)
    assert not result.passed
    assert result.issues[0].rule == "email"


# --- Issue: dry_run mode for auto_clean missing edge cases ---
# Tests added to cover dry_run=True with return_report=True and safe mode


def test_auto_clean_dry_run_with_return_report():
    # dry_run=True with return_report=True should return (frame, report)
    frame = ar.from_pandas(pd.DataFrame({"name": [" Alice ", " Bob "]}))

    result = ar.auto_clean(frame, dry_run=True, return_report=True)

    assert isinstance(result, tuple)
    original_frame, report = result
    assert isinstance(report, ar.DataQualityReport)
    # Frame must not be mutated
    assert frame.dtypes["name"] == "string"


def test_auto_clean_dry_run_safe_mode_does_not_mutate():
    # dry_run=True in safe mode should return report without mutating
    frame = ar.from_pandas(pd.DataFrame({"score": ["10", "20", "30"]}))

    result = ar.auto_clean(frame, mode="safe", dry_run=True)

    assert isinstance(result, ar.DataQualityReport)
    # Frame must not be mutated — score stays as string
    assert frame.dtypes["score"] == "string"
