"""Tests for the pandas DataFrame accessor."""

import pandas as pd
import pytest

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


def test_pandas_accessor_supports_direct_cleaning_wrapper_chains():
    df = pd.DataFrame({"name": [" Alice ", "Bob", None], "age": [25, 150, 30]})

    result = (
        df.arnio.strip_whitespace(subset=["name"])
        .arnio.clip_numeric(upper=100, subset=["age"])
        .arnio.drop_nulls()
    )

    assert isinstance(result, pd.DataFrame)
    assert list(result["name"]) == ["Alice", "Bob"]
    assert list(result["age"]) == [25, 100]
    assert list(df["name"]) == [" Alice ", "Bob", None]
    assert list(df["age"]) == [25, 150, 30]


def test_pandas_accessor_fill_nulls_updates_selected_columns_only():
    df = pd.DataFrame(
        {"name": ["Alice", None], "city": [None, "Delhi"], "score": [10, 20]}
    )

    result = df.arnio.fill_nulls("unknown", subset=["city"])

    assert isinstance(result, pd.DataFrame)
    assert list(result["city"]) == ["unknown", "Delhi"]
    assert pd.isna(result.loc[1, "name"])
    assert list(result["score"]) == [10, 20]
    assert pd.isna(df.loc[0, "city"])


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
    # dry_run=True with return_report=True should raise because dry_run
    # already returns the report directly.
    df = pd.DataFrame({"name": [" Alice ", " Bob "]})

    with pytest.raises(
        ValueError, match="return_report=True cannot be used with dry_run=True"
    ):
        df.arnio.auto_clean(dry_run=True, return_report=True)

    assert list(df["name"]) == [" Alice ", " Bob "]


def test_pandas_accessor_auto_clean_dry_run_safe_mode():
    # dry_run=True in safe mode should also return report without mutating
    df = pd.DataFrame({"score": ["10", "20", "30"]})

    result = df.arnio.auto_clean(mode="safe", dry_run=True)

    assert isinstance(result, ar.DataQualityReport)
    # Original frame must not be mutated
    assert list(df["score"]) == ["10", "20", "30"]


def test_pandas_accessor_auto_clean_strict_requires_confirmed_casts():
    df = pd.DataFrame({"active": ["true", "false"]})

    with pytest.raises(ValueError, match="requires confirmed_casts"):
        df.arnio.auto_clean(mode="strict", allow_lossy_casts=True)


def test_pandas_accessor_auto_clean_strict_accepts_confirmed_casts():
    df = pd.DataFrame({"active": ["true", "false"]})
    report = df.arnio.auto_clean(mode="strict", dry_run=True)
    confirmed_casts = dict(report.suggestions)["cast_types"]

    result = df.arnio.auto_clean(
        mode="strict",
        allow_lossy_casts=True,
        confirmed_casts=confirmed_casts,
    )

    assert list(result["active"]) == [True, False]
    assert pd.api.types.is_bool_dtype(result["active"])
    assert list(df["active"]) == ["true", "false"]


def test_pandas_accessor_validates_dataframe():
    df = pd.DataFrame({"email": ["alice@example.com", "bad"]})

    result = df.arnio.validate({"email": ar.Email(nullable=False)})

    assert isinstance(result, ar.ValidationResult)
    assert not result.passed
    assert result.issues[0].rule == "email"


# --- Issue: dry_run mode for auto_clean missing edge cases ---
# Tests added to cover dry_run=True with return_report=True and safe mode


def test_auto_clean_dry_run_with_return_report():
    # dry_run=True with return_report=True should raise because dry_run
    # already returns the report directly.
    frame = ar.from_pandas(pd.DataFrame({"name": [" Alice ", " Bob "]}))

    with pytest.raises(
        ValueError, match="return_report=True cannot be used with dry_run=True"
    ):
        ar.auto_clean(frame, dry_run=True, return_report=True)


def test_auto_clean_dry_run_safe_mode_does_not_mutate():
    # dry_run=True in safe mode should return report without mutating
    frame = ar.from_pandas(pd.DataFrame({"score": ["10", "20", "30"]}))

    result = ar.auto_clean(frame, mode="safe", dry_run=True)

    assert isinstance(result, ar.DataQualityReport)
    # Frame must not be mutated — score stays as string
    assert frame.dtypes["score"] == "string"


# --- Issue #1397: expose explain= on pandas accessor auto_clean ---


def test_pandas_accessor_auto_clean_explain_returns_dataframe_and_explanation():
    df = pd.DataFrame({"name": [" Alice ", "Bob"]})

    result, explanation = df.arnio.auto_clean(explain=True)

    assert isinstance(result, pd.DataFrame)
    assert list(result["name"]) == ["Alice", "Bob"]
    assert isinstance(explanation, ar.CleanExplanation)
    assert explanation.mode == "safe"
    assert any(s.step == "strip_whitespace" for s in explanation.steps)


def test_pandas_accessor_auto_clean_return_report_and_explain():
    df = pd.DataFrame({"name": [" Alice ", "Bob"]})

    result, report, explanation = df.arnio.auto_clean(return_report=True, explain=True)

    assert isinstance(result, pd.DataFrame)
    assert list(result["name"]) == ["Alice", "Bob"]
    assert isinstance(report, ar.DataQualityReport)
    assert isinstance(explanation, ar.CleanExplanation)


def test_pandas_accessor_validate_respects_max_errors():
    # max_errors=1 should cap the result at one issue even when multiple rows fail.
    df = pd.DataFrame({"age": [-1, -2, -3]})
    schema = ar.Schema({"age": ar.Int64(min=0)})

    result_capped = df.arnio.validate(schema, max_errors=1)
    result_full = df.arnio.validate(schema)

    assert isinstance(result_capped, ar.ValidationResult)
    assert not result_capped.passed
    assert result_capped.issue_count == 1
    # Full run should report all three failures
    assert result_full.issue_count == 3
