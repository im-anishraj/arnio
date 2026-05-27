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


# --- Tests for df.arnio.pipeline() keyword arguments ---


def test_pandas_accessor_pipeline_returns_dataframe_by_default():
    """Default behavior: pipeline returns a pandas DataFrame."""
    df = pd.DataFrame({"name": [" Alice ", " Bob "], "age": [30, 40]})

    result = df.arnio.pipeline(
        [
            ("strip_whitespace", {"subset": ["name"]}),
        ]
    )

    assert isinstance(result, pd.DataFrame)
    assert list(result["name"]) == ["Alice", "Bob"]


def test_pandas_accessor_pipeline_with_return_metadata():
    """return_metadata=True returns (DataFrame, metadata) tuple."""
    df = pd.DataFrame({"name": [" Alice ", " Bob "]})

    result, metadata = df.arnio.pipeline(
        [
            ("strip_whitespace", {"subset": ["name"]}),
            ("normalize_case", {"subset": ["name"], "case_type": "lower"}),
        ],
        return_metadata=True,
    )

    assert isinstance(result, pd.DataFrame)
    assert list(result["name"]) == ["alice", "bob"]

    # Verify metadata structure
    assert isinstance(metadata, dict)
    assert set(metadata.keys()) == {"applied_steps", "row_counts", "step_timings"}
    assert metadata["applied_steps"] == ["strip_whitespace", "normalize_case"]
    assert len(metadata["row_counts"]) == 2
    assert metadata["row_counts"][0]["step"] == "strip_whitespace"
    assert metadata["row_counts"][0]["before"] == 2
    assert metadata["row_counts"][0]["after"] == 2
    assert metadata["row_counts"][0]["dry_run"] is False
    assert len(metadata["step_timings"]) == 2


def test_pandas_accessor_pipeline_with_dry_run():
    """dry_run=True validates without mutating."""
    df = pd.DataFrame({"name": [" Alice ", " Bob "]})

    result = df.arnio.pipeline(
        [
            ("strip_whitespace", {"subset": ["name"]}),
        ],
        dry_run=True,
    )

    assert isinstance(result, pd.DataFrame)
    # With dry_run=True, the result should be the original frame
    assert list(result["name"]) == [" Alice ", " Bob "]


def test_pandas_accessor_pipeline_with_verbose(caplog):
    """verbose=True enables diagnostic logging."""
    df = pd.DataFrame({"name": [" Alice "]})

    caplog.set_level("INFO", logger="arnio")

    result = df.arnio.pipeline(
        [
            ("strip_whitespace", {"subset": ["name"]}),
        ],
        verbose=True,
    )

    assert isinstance(result, pd.DataFrame)
    assert any("strip_whitespace" in record.message for record in caplog.records)


def test_pandas_accessor_pipeline_with_return_metadata_and_dry_run():
    """return_metadata=True with dry_run=True returns (original_df, metadata)."""
    df = pd.DataFrame({"value": [None, 10, 20]})

    result, metadata = df.arnio.pipeline(
        [
            ("drop_nulls", {}),
        ],
        return_metadata=True,
        dry_run=True,
    )

    assert isinstance(result, pd.DataFrame)
    assert len(result) == 3  # Original frame unchanged in dry_run
    assert isinstance(metadata, dict)
    assert metadata["row_counts"][0]["dry_run"] is True
    # In dry_run, after should equal before
    assert metadata["row_counts"][0]["after"] == metadata["row_counts"][0]["before"]


def test_pandas_accessor_pipeline_invalid_step_raises():
    """Invalid pipeline input raises appropriate error."""
    df = pd.DataFrame({"name": ["Alice"]})

    with pytest.raises(Exception):  # Could be UnknownStepError or ValueError
        df.arnio.pipeline(
            [
                ("nonexistent_step",),
            ]
        )


def test_pandas_accessor_pipeline_invalid_step_kwargs_raises():
    """Invalid step kwargs raises appropriate error."""
    df = pd.DataFrame({"name": ["Alice"]})

    with pytest.raises(Exception):  # Could be KeyError or similar
        df.arnio.pipeline(
            [
                ("drop_nulls", {"subset": ["nonexistent_column"]}),
            ]
        )
