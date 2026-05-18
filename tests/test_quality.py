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


def test_quality_to_dict_default_preserves_sample_values(tmp_path):
    path = tmp_path / "dict_default.csv"
    path.write_text("name\nAlice\nBob\n")
    report = ar.profile(ar.read_csv(path), sample_size=2)

    d = report.to_dict()

    assert d["columns"]["name"]["sample_values"] == ["Alice", "Bob"]


def test_quality_to_dict_redacts_sample_values(tmp_path):
    path = tmp_path / "dict_redacted.csv"
    path.write_text("name\nAlice\nBob\n")
    report = ar.profile(ar.read_csv(path), sample_size=2)

    d = report.to_dict(redact_sample_values=True)

    assert d["columns"]["name"]["sample_values"] == ["[REDACTED]", "[REDACTED]"]
    assert report.columns["name"].sample_values == ["Alice", "Bob"]


def test_quality_to_dict_redacts_multiple_columns_and_preserves_lengths(tmp_path):
    path = tmp_path / "dict_multi.csv"
    path.write_text("name,city\nAlice,Paris\nBob,London\n")
    report = ar.profile(ar.read_csv(path), sample_size=2)

    d = report.to_dict(redact_sample_values=True)

    assert d["columns"]["name"]["sample_values"] == ["[REDACTED]", "[REDACTED]"]
    assert d["columns"]["city"]["sample_values"] == ["[REDACTED]", "[REDACTED]"]
    assert len(d["columns"]["name"]["sample_values"]) == 2
    assert len(d["columns"]["city"]["sample_values"]) == 2


def test_quality_to_dict_redaction_keeps_no_example_cases_empty(tmp_path):
    path = tmp_path / "dict_empty_samples.csv"
    path.write_text("id\n1\n2\n")
    report = ar.profile(ar.read_csv(path), sample_size=0)

    d = report.to_dict(redact_sample_values=True)

    assert d["columns"]["id"]["sample_values"] == []


def test_column_profile_to_dict_redacts_sample_values_direct(tmp_path):
    path = tmp_path / "column_redacted.csv"
    path.write_text("name\nAlice\nBob\n")
    report = ar.profile(ar.read_csv(path), sample_size=2)

    d = report.columns["name"].to_dict(redact_sample_values=True)

    assert d["sample_values"] == ["[REDACTED]", "[REDACTED]"]
    assert report.columns["name"].sample_values == ["Alice", "Bob"]


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


# ── top_values tests ──────────────────────────────────────────────────────────


def test_top_values_correct_order_and_ratio(tmp_path):
    path = tmp_path / "tv.csv"
    path.write_text("city\nLondon\nLondon\nLondon\nParis\nParis\nTokyo\n")
    report = ar.profile(ar.read_csv(path))
    tv = report.columns["city"].top_values

    assert tv is not None
    assert tv[0][0] == "London"
    assert tv[0][1] == 3
    assert tv[0][2] == pytest.approx(0.5, rel=1e-3)
    assert tv[1][0] == "Paris"
    assert tv[1][1] == 2
    assert tv[2][0] == "Tokyo"
    assert tv[2][1] == 1


def test_top_values_nulls_excluded(tmp_path):
    path = tmp_path / "nulls.csv"
    path.write_text("city\nLondon\nLondon\n\nParis\n")
    report = ar.profile(ar.read_csv(path))
    tv = report.columns["city"].top_values

    assert tv is not None
    total_counts = sum(c for _, c, _ in tv)
    # null row excluded — only 3 non-null rows
    assert total_counts == 3
    # ratios sum to 1.0 over non-null total
    assert sum(r for _, _, r in tv) == pytest.approx(1.0, rel=1e-3)


def test_top_values_all_unique(tmp_path):
    path = tmp_path / "unique.csv"
    path.write_text("code\nA\nB\nC\nD\n")
    report = ar.profile(ar.read_csv(path))
    tv = report.columns["code"].top_values

    assert tv is not None
    assert len(tv) == 4
    for _, count, ratio in tv:
        assert count == 1
        assert ratio == pytest.approx(0.25, rel=1e-3)


def test_top_values_single_value(tmp_path):
    path = tmp_path / "single.csv"
    path.write_text("status\nactive\nactive\nactive\n")
    report = ar.profile(ar.read_csv(path))
    tv = report.columns["status"].top_values

    assert tv is not None
    assert len(tv) == 1
    assert tv[0] == ("active", 3, pytest.approx(1.0, rel=1e-3))


def test_top_values_not_computed_for_numeric(tmp_path):
    path = tmp_path / "numeric.csv"
    path.write_text("score\n1\n2\n3\n")
    report = ar.profile(ar.read_csv(path))

    assert report.columns["score"].top_values is None


def test_top_values_empty_column(tmp_path):
    path = tmp_path / "empty.csv"
    path.write_text("name\n\n\n\n")
    report = ar.profile(ar.read_csv(path))
    tv = report.columns["name"].top_values

    # arnio parses blank rows as empty strings, not nulls
    # top_values should still return without crashing
    assert tv is not None
    assert isinstance(tv, list)


def test_top_values_in_to_dict(tmp_path):
    path = tmp_path / "dict.csv"
    path.write_text("city\nLondon\nParis\nLondon\n")
    report = ar.profile(ar.read_csv(path))
    d = report.columns["city"].to_dict()

    assert "top_values" in d
    assert d["top_values"][0]["value"] == "London"
    assert d["top_values"][0]["count"] == 2


def test_identifier_numeric_cast_prevention():
    df = pd.DataFrame(
        {
            "id": ["001", "002", "003"],
            "customer_id": ["00123", "00456", "00789"],
            "zip_code": ["01234", "02345", "03456"],
            "price": ["10.50", "20.00", "30.75"],
            "quantity": ["1", "2", "3"],
        }
    )
    frame = ar.from_pandas(df)
    report = ar.profile(frame)

    assert report.columns["id"].semantic_type == "identifier"
    assert report.columns["customer_id"].semantic_type == "identifier"
    assert report.columns["zip_code"].semantic_type == "identifier"

    suggestions_list = ar.suggest_cleaning(frame)
    suggestions = {}
    for step, kwargs in suggestions_list:
        if step == "cast_types":
            suggestions.update(kwargs)

    assert "price" in suggestions
    assert "quantity" in suggestions
    assert "id" not in suggestions
    assert "customer_id" not in suggestions
    assert "zip_code" not in suggestions

    cleaned = ar.auto_clean(frame, mode="strict")
    result = ar.to_pandas(cleaned)
    assert list(result["id"]) == ["001", "002", "003"]
    assert list(result["customer_id"]) == ["00123", "00456", "00789"]
    assert list(result["zip_code"]) == ["01234", "02345", "03456"]


# ── string length statistics tests ───────────────────────────────────────────


def test_profile_string_metrics():
    df = pd.DataFrame({"text": ["a", "abc", "abcde", "", "  ", None]})
    frame = ar.from_pandas(df)
    report = ar.profile(frame)

    profile = report.columns["text"]
    assert profile.dtype == "string"
    assert profile.min == 0
    assert profile.max == 5
    assert profile.mean == 2.2
    assert profile.empty_string_count == 2
    assert profile.whitespace_count == 1
    assert "empty_strings" in profile.warnings


def test_profile_empty_and_null_strings():
    df = pd.DataFrame(
        {
            "all_null": [None, None],
            "all_empty": ["", ""],
        }
    )
    frame = ar.from_pandas(df)
    report = ar.profile(frame)

    # All null
    p_null = report.columns["all_null"]
    assert p_null.min is None
    assert p_null.max is None
    assert p_null.mean is None
    assert p_null.null_count == 2

    # All empty
    p_empty = report.columns["all_empty"]
    assert p_empty.min == 0
    assert p_empty.max == 0
    assert p_empty.mean == 0.0
    assert p_empty.empty_string_count == 2


def test_profile_string_clean_happy_path():
    """Clean string column with no nulls, no empties — simplest case."""
    df = pd.DataFrame({"name": ["hello", "hi", "hey"]})
    frame = ar.from_pandas(df)
    report = ar.profile(frame)

    p = report.columns["name"]
    assert p.dtype == "string"
    assert p.min == 2
    assert p.max == 5
    assert p.mean == 10 / 3
    assert p.null_count == 0
    assert p.empty_string_count == 0
    assert p.whitespace_count == 0


def test_profile_string_metrics_to_dict():
    """String length values appear correctly in to_dict() output."""
    df = pd.DataFrame({"label": ["short", "medium-ish", "x"]})
    frame = ar.from_pandas(df)
    report = ar.profile(frame)
    d = report.to_dict()

    col = d["columns"]["label"]
    assert col["min"] == 1
    assert col["max"] == 10
    assert col["mean"] == 5.0 + 1 / 3


def test_profile_string_metrics_to_pandas():
    """String length values appear correctly in to_pandas() output."""
    df = pd.DataFrame({"label": ["short", "medium-ish", "x"]})
    frame = ar.from_pandas(df)
    report = ar.profile(frame)
    result_df = report.to_pandas()

    row = result_df[result_df["name"] == "label"].iloc[0]
    assert row["min"] == 1
    assert row["max"] == 10
    assert row["mean"] == 5.0 + 1 / 3


def test_report_to_markdown_basic(tmp_path):
    path = tmp_path / "report.csv"

    path.write_text("id,name\n" "1,Alice\n" "2,Bob\n")

    report = ar.profile(ar.read_csv(path))

    md = report.to_markdown()

    assert "# Data Quality Report" in md
    assert "## Overview" in md
    assert "## Columns" in md
    assert "| id | int64 | identifier |" in md


def test_report_to_markdown_includes_uniqueness_metrics(tmp_path):
    path = tmp_path / "unique_metrics.csv"

    path.write_text("id,name\n" "1,Alice\n" "2,Bob\n" "2,Bob\n")

    report = ar.profile(ar.read_csv(path))

    md = report.to_markdown()

    assert "Unique Count" in md
    assert "Unique Ratio" in md

    # id column: 2 unique non-null values across 3 rows
    assert "66.67%" in md


def test_unique_ratio_empty_column(tmp_path):
    path = tmp_path / "empty_unique.csv"

    path.write_text("name\n\n\n")

    report = ar.profile(ar.read_csv(path))

    column = report.columns["name"]

    assert column.unique_count >= 0
    assert column.unique_ratio >= 0.0


def test_report_to_markdown_deterministic(tmp_path):
    path = tmp_path / "stable.csv"

    path.write_text("id,name\n" "1,Alice\n" "2,Bob\n")

    report = ar.profile(ar.read_csv(path))

    assert report.to_markdown() == report.to_markdown()


def test_report_to_markdown_empty_sections():
    report = ar.DataQualityReport(
        row_count=0,
        column_count=0,
        memory_usage=0,
        duplicate_rows=0,
        duplicate_ratio=0.0,
        columns={},
        suggestions=[],
    )

    md = report.to_markdown()

    assert "# Data Quality Report" in md
    assert "## Overview" in md
    assert "## Columns" not in md
    assert "|---|---|" not in md


# ── quality score tests ───────────────────────────────────────────────────────


def test_quality_score_clean(tmp_path):
    path = tmp_path / "clean.csv"
    path.write_text("id,name\n1,Alice\n2,Bob\n3,Charlie\n")
    report = ar.profile(ar.read_csv(path))

    assert report.quality_score == 100.0
    assert not report.score_components


def test_quality_score_empty(tmp_path):
    path = tmp_path / "empty.csv"
    path.write_text("id,name\n")
    report = ar.profile(ar.read_csv(path))

    assert report.quality_score == 100.0
    assert not report.score_components


def test_quality_score_nulls(tmp_path):
    path = tmp_path / "nulls.csv"
    # id has 2 nulls, name has 1 null
    path.write_text("id,name\n1,Alice\n,Bob\n,\n")
    report = ar.profile(ar.read_csv(path))

    # 3 rows. id null_ratio ~0.66, name null_ratio ~0.33
    # avg null ratio ~0.5 => 50 points penalty => capped at -40.0
    assert report.score_components["null_penalty"] == -40.0
    assert report.quality_score == 60.0


def test_quality_score_duplicates(tmp_path):
    path = tmp_path / "dup.csv"
    path.write_text("id,name\n1,Alice\n1,Alice\n1,Alice\n")
    report = ar.profile(ar.read_csv(path))

    # 3 rows, 2 duplicates. ratio = 0.66
    # 0.66 * 100 = 66 points penalty => capped at -20.0
    assert report.score_components["duplicate_penalty"] == -20.0
    assert report.quality_score == 80.0


def test_quality_score_type_mismatch():
    df = pd.DataFrame(
        {
            "id": [1, 2],
            "score": ["10", "20"],
        }
    )
    frame = ar.from_pandas(df)
    report = ar.profile(frame)

    # 2 columns. 1 has type mismatch. ratio = 0.5 => 50 points => capped at -40.0
    assert report.score_components["type_mismatch_penalty"] == -40.0
    assert report.quality_score == 60.0
