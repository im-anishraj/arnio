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


def test_quality_score_type_mismatch(tmp_path):
    path = tmp_path / "mismatch.csv"
    # score column is read as string, but contains only numbers,
    # which triggers a suggested_dtype of int64/float64.
    path.write_text('id,score\n1,"10"\n2,"20"\n')
    report = ar.profile(ar.read_csv(path))

    # 2 columns. 1 has type mismatch. ratio = 0.5 => 50 points => capped at -40.0
    assert report.score_components["type_mismatch_penalty"] == -40.0
