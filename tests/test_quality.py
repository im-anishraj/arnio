"""Tests for data quality profiling and smart cleaning."""

import pandas as pd
import pytest

import arnio as ar


def test_profile_reports_quality_signals(tmp_path):
    path = tmp_path / "quality.csv"
    path.write_text(
        "id,name,email,score\n"
        "1, Alice ,alice@test.com,95.5\n"
        "2,Bob,bob@test.com,\n"
        "2,Bob,bob@test.com,\n"
    )

    report = ar.profile(ar.read_csv(path))

    assert report.row_count == 3
    assert report.column_count == 4
    assert report.duplicate_rows == 1
    assert report.columns["name"].whitespace_count == 1
    assert report.columns["email"].semantic_type == "email"
    assert report.columns["score"].null_count == 2
    assert ("drop_duplicates", {"keep": "first"}) in report.suggestions


def test_report_summary_and_pandas_output(csv_with_whitespace):
    report = ar.profile(ar.read_csv(csv_with_whitespace))
    summary = report.summary()
    df = report.to_pandas()

    assert summary["rows"] == 3
    assert summary["columns_with_whitespace"] == ["name", "city"]
    assert isinstance(df, pd.DataFrame)
    assert set(df["name"]) == {"name", "city"}


def test_suggest_cleaning_returns_pipeline_compatible_steps(csv_with_duplicates):
    frame = ar.read_csv(csv_with_duplicates)
    suggestions = ar.suggest_cleaning(frame)

    assert suggestions == [("drop_duplicates", {"keep": "first"})]
    clean = ar.pipeline(frame, suggestions)
    assert clean.shape == (3, 2)


def test_auto_clean_safe_trims_without_dropping_duplicates(tmp_path):
    path = tmp_path / "safe.csv"
    path.write_text("name\n Alice \n Alice \n")

    frame = ar.read_csv(path)
    clean, report = ar.auto_clean(frame, return_report=True)
    df = ar.to_pandas(clean)

    assert report.duplicate_rows == 1
    assert clean.shape == (2, 1)
    assert list(df["name"]) == ["Alice", "Alice"]


def test_auto_clean_strict_applies_exact_deduplication(tmp_path):
    path = tmp_path / "strict.csv"
    path.write_text("name\n Alice \n Alice \n")

    clean = ar.auto_clean(ar.read_csv(path), mode="strict")

    assert clean.shape == (1, 1)


def test_auto_clean_rejects_unknown_mode(sample_csv):
    frame = ar.read_csv(sample_csv)

    try:
        ar.auto_clean(frame, mode="wild")
        assert False, "Expected ValueError"
    except ValueError as exc:
        assert "mode must be" in str(exc)


def test_profile_sample_size(tmp_path):
    path = tmp_path / "sample.csv"
    path.write_text("id\n1\n2\n3\n4\n5\n6\n7\n")
    frame = ar.read_csv(path)

    report_default = ar.profile(frame)
    assert len(report_default.columns["id"].sample_values) == 5

    report_custom = ar.profile(frame, sample_size=3)
    assert len(report_custom.columns["id"].sample_values) == 3

    report_zero = ar.profile(frame, sample_size=0)
    assert len(report_zero.columns["id"].sample_values) == 0


def test_profile_sample_size_small_dataset_and_nulls(tmp_path):
    path = tmp_path / "sample.csv"
    path.write_text("id\n1\n\n3\n")
    frame = ar.read_csv(path)

    report = ar.profile(frame, sample_size=5)
    assert len(report.columns["id"].sample_values) == 2
    assert report.columns["id"].sample_values == [1.0, 3.0]


def test_profile_sample_size_validation(tmp_path):
    path = tmp_path / "sample.csv"
    path.write_text("id\n1\n")
    frame = ar.read_csv(path)

    try:
        ar.profile(frame, sample_size=-1)
        assert False, "Expected ValueError"
    except ValueError as exc:
        assert "sample_size must be non-negative" in str(exc)

    try:
        ar.profile(frame, sample_size="5")
        assert False, "Expected TypeError"
    except TypeError as exc:
        assert "sample_size must be an integer" in str(exc)


def test_duplicate_count_for_full_rows():
    df = pd.DataFrame(
        [
            {"id": 1, "name": "A"},
            {"id": 1, "name": "A"},
            {"id": 2, "name": "B"},
        ]
    )

    assert ar.duplicate_count(df) == 1


def test_duplicate_count_for_single_column():
    df = pd.DataFrame(
        [
            {"id": 1, "name": "A"},
            {"id": 1, "name": "B"},
            {"id": 2, "name": "C"},
        ]
    )

    assert ar.duplicate_count(df, subset=["id"]) == 1


def test_duplicate_count_for_multiple_columns():
    df = pd.DataFrame(
        [
            {"id": 1, "email": "a@test.com"},
            {"id": 1, "email": "a@test.com"},
            {"id": 1, "email": "b@test.com"},
        ]
    )

    assert ar.duplicate_count(df, subset=["id", "email"]) == 1


def test_duplicate_count_no_duplicates():
    df = pd.DataFrame(
        [
            {"id": 1, "name": "A"},
            {"id": 2, "name": "B"},
        ]
    )

    assert ar.duplicate_count(df, subset=["id"]) == 0


def test_duplicate_count_invalid_column():
    df = pd.DataFrame(
        [
            {"id": 1, "name": "A"},
        ]
    )

    with pytest.raises(ValueError, match="Unknown columns"):
        ar.duplicate_count(df, subset=["email"])
