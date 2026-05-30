"""Tests for data quality profiling and smart cleaning."""

import io
import json
import math

import pandas as pd
import pytest

import arnio as ar
from arnio.quality import (
    _validate_gate_bool,
    _validate_gate_ratio_threshold,
    _validate_gate_threshold,
)


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


def test_profile_numeric_quantiles():
    frame = ar.from_pandas(pd.DataFrame({"age": [1.0, 2.0, 3.0, 4.0, 5.0]}))

    report = ar.profile(frame)
    profile = report.columns["age"].to_dict()

    assert profile["q25"] == 2.0
    assert profile["q50"] == 3.0
    assert profile["q75"] == 4.0
    assert profile["q95"] == 4.8
    assert profile["iqr"] == 2.0
    assert profile["outlier_lower_bound"] == -1.0
    assert profile["outlier_upper_bound"] == 7.0
    assert profile["outlier_count"] == 0
    assert profile["outlier_ratio"] == 0.0


def test_profile_numeric_quantiles_and_outliers():
    frame = ar.from_pandas(pd.DataFrame({"x": [1.0, 2.0, 3.0, 4.0, 100.0]}))

    report = ar.profile(frame)
    profile = report.columns["x"].to_dict()

    assert profile["q25"] == 2.0
    assert profile["q50"] == 3.0
    assert profile["q75"] == 4.0
    assert profile["q95"] == 80.8
    assert profile["iqr"] == 2.0
    assert profile["outlier_lower_bound"] == -1.0
    assert profile["outlier_upper_bound"] == 7.0
    assert profile["outlier_count"] == 1
    assert profile["outlier_ratio"] == 0.2
    assert "potential_outliers" in profile["warnings"]


def test_profile_all_null_numeric_quantiles():
    frame = ar.from_pandas(
        pd.DataFrame({"score": pd.Series([None, None], dtype="float64")})
    )

    report = ar.profile(frame)
    profile = report.columns["score"].to_dict()

    assert profile["q25"] is None
    assert profile["q50"] is None
    assert profile["q75"] is None
    assert profile["q95"] is None
    assert profile["outlier_count"] is None
    assert profile["outlier_ratio"] is None
    assert profile["iqr"] is None
    assert profile["outlier_lower_bound"] is None
    assert profile["outlier_upper_bound"] is None


def test_profile_numeric_outliers_skipped_when_too_few_values():
    frame = ar.from_pandas(pd.DataFrame({"x": [1.0, 2.0, 3.0]}))

    report = ar.profile(frame)
    profile = report.columns["x"].to_dict()

    # Quartiles still computed; IQR summary needs >= 4 non-null values
    assert profile["q25"] is not None
    assert profile["outlier_count"] is None
    assert profile["outlier_ratio"] is None
    assert profile["iqr"] is None
    assert profile["outlier_lower_bound"] is None
    assert profile["outlier_upper_bound"] is None
    assert "potential_outliers" not in profile["warnings"]


def test_profile_numeric_outliers_skipped_with_two_values():
    frame = ar.from_pandas(pd.DataFrame({"x": [1.0, 100.0]}))

    report = ar.profile(frame)
    profile = report.columns["x"].to_dict()

    assert profile["outlier_count"] is None
    assert profile["outlier_ratio"] is None
    assert profile["iqr"] is None
    assert profile["outlier_lower_bound"] is None
    assert profile["outlier_upper_bound"] is None


def test_profile_numeric_zero_iqr_constant_column_no_outliers():
    frame = ar.from_pandas(pd.DataFrame({"x": [5.0, 5.0, 5.0, 5.0]}))

    report = ar.profile(frame)
    profile = report.columns["x"].to_dict()

    assert profile["q25"] == profile["q75"] == 5.0
    assert profile["iqr"] == 0.0
    assert profile["outlier_lower_bound"] == 5.0
    assert profile["outlier_upper_bound"] == 5.0
    assert profile["outlier_count"] == 0
    assert profile["outlier_ratio"] == 0.0
    assert "potential_outliers" not in profile["warnings"]


def test_profile_numeric_zero_iqr_with_extreme_value():
    frame = ar.from_pandas(pd.DataFrame({"x": [10.0, 10.0, 10.0, 10.0, 50.0]}))

    report = ar.profile(frame)
    profile = report.columns["x"].to_dict()

    assert profile["q25"] == 10.0
    assert profile["q75"] == 10.0
    assert profile["iqr"] == 0.0
    assert profile["outlier_lower_bound"] == 10.0
    assert profile["outlier_upper_bound"] == 10.0
    assert profile["outlier_count"] == 1
    assert profile["outlier_ratio"] == 0.2
    assert profile["warnings"] == ["potential_outliers"]


def test_profile_non_numeric_no_quantiles():
    frame = ar.from_pandas(pd.DataFrame({"name": ["Alice", "Bob", "Cara"]}))

    report = ar.profile(frame)
    profile = report.columns["name"].to_dict()

    assert "q25" not in profile
    assert "q50" not in profile
    assert "q75" not in profile
    assert "q95" not in profile
    assert "iqr" not in profile
    assert "outlier_lower_bound" not in profile
    assert "outlier_upper_bound" not in profile
    assert "outlier_count" not in profile
    assert "outlier_ratio" not in profile


def test_profile_email_and_url_validity_ratios():
    df = pd.DataFrame(
        {
            "good_email": [
                "alice@test.com",
                "bob@test.com",
                "cara@test.com",
                "dave@test.com",
                "eve@test.com",
            ],
            "mixed_email": [
                "alice@test.com",
                "bob@test.com",
                "cara@test.com",
                "dave@test.com",
                "invalid-email",
            ],
            "good_url": [
                "http://test.com",
                "https://example.com/foo",
                "https://another.org",
                "http://a.b",
                "https://last.com",
            ],
            "mixed_url": [
                "http://test.com",
                "https://example.com/foo",
                "https://another.org",
                "http://a.b",
                "not-a-url",
            ],
            "generic": ["hello", "world", "foo", "bar", "baz"],
        }
    )

    frame = ar.from_pandas(df)
    report = ar.profile(frame)

    assert report.columns["good_email"].semantic_type == "email"
    assert report.columns["mixed_email"].semantic_type == "email"
    assert report.columns["good_url"].semantic_type == "url"
    assert report.columns["mixed_url"].semantic_type == "url"
    assert report.columns["generic"].semantic_type == "categorical"

    assert report.columns["good_email"].email_validity_ratio == 1.0
    assert report.columns["good_email"].url_validity_ratio is None

    assert report.columns["mixed_email"].email_validity_ratio == 0.8
    assert report.columns["mixed_email"].url_validity_ratio is None

    assert report.columns["good_url"].url_validity_ratio == 1.0
    assert report.columns["good_url"].email_validity_ratio is None

    assert report.columns["mixed_url"].url_validity_ratio == 0.8
    assert report.columns["mixed_url"].email_validity_ratio is None

    assert report.columns["generic"].email_validity_ratio is None
    assert report.columns["generic"].url_validity_ratio is None

    good_email_dict = report.columns["good_email"].to_dict()
    assert good_email_dict["email_validity_ratio"] == 1.0
    assert good_email_dict["url_validity_ratio"] is None

    mixed_url_dict = report.columns["mixed_url"].to_dict()
    assert mixed_url_dict["url_validity_ratio"] == 0.8
    assert mixed_url_dict["email_validity_ratio"] is None

    pdf = report.to_pandas()
    good_email_row = pdf[pdf["name"] == "good_email"].iloc[0]
    assert good_email_row["email_validity_ratio"] == 1.0
    assert (
        pd.isna(good_email_row["url_validity_ratio"])
        or good_email_row["url_validity_ratio"] is None
    )


def test_compare_profiles_identical_profiles_are_ok():
    frame = ar.from_pandas(
        pd.DataFrame({"score": [10.0, 11.0, 12.0], "city": ["a", "b", "a"]})
    )

    comparison = ar.compare_profiles(ar.profile(frame), ar.profile(frame))

    assert set(comparison.drift_report) == {"score", "city"}
    assert all(entry["status"] == "ok" for entry in comparison.drift_report.values())
    assert comparison.status_counts == {"ok": 2, "warning": 0, "changed": 0}


def test_compare_profiles_detects_numeric_drift():
    baseline = ar.profile(ar.from_pandas(pd.DataFrame({"score": [10.0, 10.0, 10.0]})))
    current = ar.profile(ar.from_pandas(pd.DataFrame({"score": [20.0, 20.0, 20.0]})))

    comparison = ar.compare_profiles(baseline, current)

    assert comparison.drift_report["score"]["status"] in {"warning", "changed"}
    assert comparison.drift_report["score"]["changes"]["mean"]["baseline"] == 10.0
    assert comparison.drift_report["score"]["changes"]["mean"]["comparison"] == 20.0


def test_compare_profiles_rejects_schema_mismatch():
    left = ar.profile(ar.from_pandas(pd.DataFrame({"score": [1.0, 2.0]})))
    right = ar.profile(
        ar.from_pandas(pd.DataFrame({"score": [1.0, 2.0], "city": ["a", "b"]}))
    )

    with pytest.raises(ValueError, match="incompatible schemas"):
        ar.compare_profiles(left, right)


def test_compare_profiles_handles_empty_profiles():
    empty = ar.profile(ar.from_pandas(pd.DataFrame()))

    comparison = ar.compare_profiles(empty, empty)

    assert comparison.drift_report == {}
    assert comparison.status_counts == {"ok": 0, "warning": 0, "changed": 0}


def test_compare_profiles_handles_single_column_profiles():
    frame = ar.from_pandas(pd.DataFrame({"name": ["Alice", "Bob"]}))

    comparison = ar.compare_profiles(ar.profile(frame), ar.profile(frame))

    assert comparison.drift_report["name"]["status"] == "ok"
    assert comparison.status_counts == {"ok": 1, "warning": 0, "changed": 0}


def test_profile_comparison_accepts_valid_status_counts():
    base = ar.DataQualityReport(0, 0, 0, 0, 0.0, {})

    comparison = ar.ProfileComparison(
        base,
        base,
        {},
        {"ok": 1, "warning": 2, "changed": 0},
    )

    assert comparison.status_counts == {
        "ok": 1,
        "warning": 2,
        "changed": 0,
    }


def test_profile_comparison_rejects_bool_status_counts():
    base = ar.DataQualityReport(0, 0, 0, 0, 0.0, {})

    with pytest.raises(
        TypeError,
        match="status_counts values must not be booleans",
    ):
        ar.ProfileComparison(
            base,
            base,
            {},
            {"passed": True},
        )


def test_profile_comparison_rejects_negative_status_counts():
    base = ar.DataQualityReport(0, 0, 0, 0, 0.0, {})

    with pytest.raises(
        ValueError,
        match="status_counts values must be non-negative integers",
    ):
        ar.ProfileComparison(
            base,
            base,
            {},
            {"failed": -1},
        )


def test_check_quality_gates_passes_identical_profiles():
    frame = ar.from_pandas(
        pd.DataFrame({"score": [10.0, 11.0, 12.0], "city": ["a", "b", "a"]})
    )

    result = ar.check_quality_gates(ar.profile(frame), ar.profile(frame))

    assert result.passed is True
    assert result.issues == []
    assert result.summary()["passed"] is True
    assert result.to_dict()["passed"] is True
    assert result.to_dict()["summary"]["issue_count"] == 0
    assert "All configured quality gates passed" in result.to_markdown()


def test_check_quality_gates_detects_row_duplicate_null_and_numeric_drift():
    baseline = ar.profile(
        ar.from_pandas(
            pd.DataFrame({"score": [10.0, 10.0, 10.0], "city": ["a", "b", "c"]})
        )
    )
    current = ar.profile(
        ar.from_pandas(
            pd.DataFrame(
                {
                    "score": [20.0, 20.0, None, None, 20.0],
                    "city": ["a", "a", "a", "a", "a"],
                }
            )
        )
    )

    result = ar.check_quality_gates(
        baseline,
        current,
        max_row_count_delta_ratio=0.2,
        max_duplicate_ratio_delta=0.1,
        max_null_ratio_delta=0.1,
        max_numeric_mean_delta_ratio=0.5,
    )

    metrics = {issue.metric for issue in result.issues}
    assert result.passed is False
    assert {"row_count", "duplicate_ratio", "null_ratio", "numeric_mean"} <= metrics
    assert any(issue.column == "score" for issue in result.issues)


def test_check_quality_gates_detects_schema_and_dtype_changes():
    baseline = ar.profile(
        ar.from_pandas(pd.DataFrame({"score": [1, 2], "city": ["a", "b"]}))
    )
    current = ar.profile(
        ar.from_pandas(pd.DataFrame({"score": ["1", "2"], "state": ["a", "b"]}))
    )

    result = ar.check_quality_gates(baseline, current)

    issues = {(issue.metric, issue.column) for issue in result.issues}
    assert ("missing_column", "city") in issues
    assert ("new_column", "state") in issues
    assert ("dtype", "score") in issues


def test_check_quality_gates_can_allow_schema_changes_and_disable_thresholds():
    baseline = ar.profile(ar.from_pandas(pd.DataFrame({"score": [1.0, 2.0]})))
    current = ar.profile(
        ar.from_pandas(pd.DataFrame({"score": [100.0, 200.0], "extra": ["x", "y"]}))
    )

    result = ar.check_quality_gates(
        baseline,
        current,
        allow_new_columns=True,
        max_numeric_mean_delta_ratio=None,
        max_numeric_std_delta_ratio=None,
    )

    assert result.passed is True


def test_check_quality_gates_markdown_escapes_table_cells():
    baseline = ar.profile(ar.from_pandas(pd.DataFrame({"bad|name": [1, 2]})))
    current = ar.profile(ar.from_pandas(pd.DataFrame({"other": [1, 2]})))

    markdown = ar.check_quality_gates(baseline, current).to_markdown()

    assert "bad\\|name" in markdown


def test_check_quality_gates_validates_thresholds_and_flags():
    report = ar.profile(ar.from_pandas(pd.DataFrame({"score": [1.0, 2.0]})))

    with pytest.raises(ValueError, match="finite non-negative"):
        ar.check_quality_gates(report, report, max_null_ratio_delta=-0.1)

    with pytest.raises(ValueError, match="must be a ratio between 0.0 and 1.0"):
        ar.check_quality_gates(report, report, max_null_ratio_delta=1.5)

    with pytest.raises(ValueError, match="must be a ratio between 0.0 and 1.0"):
        ar.check_quality_gates(report, report, max_duplicate_ratio_delta=1.0001)

    result = ar.check_quality_gates(report, report, max_row_count_delta_ratio=2.5)
    assert result.passed is True

    with pytest.raises(TypeError, match="allow_new_columns must be a bool"):
        ar.check_quality_gates(report, report, allow_new_columns="yes")


def test_quality_gate_result_raise_for_failures():
    baseline = ar.profile(ar.from_pandas(pd.DataFrame({"score": [1.0, 2.0]})))
    current = ar.profile(ar.from_pandas(pd.DataFrame({"score": [100.0, 200.0]})))

    result = ar.check_quality_gates(
        baseline,
        current,
        max_numeric_mean_delta_ratio=0.1,
    )

    with pytest.raises(ValueError, match="data quality gate"):
        result.raise_for_failures()


def test_suggest_cleaning_returns_pipeline_compatible_steps(csv_with_duplicates):
    frame = ar.read_csv(csv_with_duplicates)
    suggestions = ar.suggest_cleaning(frame)

    assert suggestions == [("drop_duplicates", {"keep": "first"})]
    clean = ar.pipeline(frame, suggestions)
    assert clean.shape == (3, 2)


def test_suggest_cleaning_confidence_metadata():
    df = pd.DataFrame(
        {
            "id": [1, 2, 3, 3],
            "name": ["Alice ", "Bob", "Charlie ", "Charlie "],
            "active": ["true", "false", "true", "true"],
            "duplicates": [1, 1, 1, 1],
        }
    )
    frame = ar.from_pandas(df)
    report = ar.profile(frame)
    suggestions = ar.suggest_cleaning(report)

    # Convert to standard list of step names to find the specific suggestions
    step_names = [s[0] for s in suggestions]

    # Check strip_whitespace
    assert "strip_whitespace" in step_names
    strip_sug = next(s for s in suggestions if s[0] == "strip_whitespace")
    assert getattr(strip_sug, "confidence_score") == 0.95
    assert "Trimming leading/trailing whitespace" in getattr(
        strip_sug, "confidence_reason"
    )
    assert getattr(strip_sug, "step") == "strip_whitespace"
    assert getattr(strip_sug, "kwargs") == {"subset": ["name"]}

    # Check cast_types
    assert "cast_types" in step_names
    cast_sug = next(s for s in suggestions if s[0] == "cast_types")
    assert getattr(cast_sug, "confidence_score") == 0.95
    assert "conforms perfectly to bool structure" in getattr(
        cast_sug, "confidence_reason"
    )

    # Check drop_duplicates
    assert "drop_duplicates" in step_names
    drop_sug = next(s for s in suggestions if s[0] == "drop_duplicates")
    # Duplicate ratio here is 1 duplicate out of 4 rows = 0.25 <= 0.5
    assert getattr(drop_sug, "confidence_score") == 0.95
    assert "Low duplicate ratio" in getattr(drop_sug, "confidence_reason")

    # Check JSON serialization of confidence metadata
    report_dict = report.to_dict()
    dict_suggestions = report_dict["suggestions"]
    assert len(dict_suggestions) == 3
    for s in dict_suggestions:
        assert "confidence_score" in s
        assert "confidence_reason" in s
        assert isinstance(s["confidence_score"], float)
        assert isinstance(s["confidence_reason"], str)

    # Check Markdown formatting
    md = report.to_markdown()
    assert "(Confidence: 0.95 -" in md


def test_cleaning_suggestion_backward_compatibility():
    """Prove backward compatibility with the existing tuple contract."""
    from arnio.quality import CleaningSuggestion

    sug = CleaningSuggestion("drop_duplicates", {"keep": "first"}, 0.9, "reason")

    # It should equate to the exact 2-tuple.
    assert sug == ("drop_duplicates", {"keep": "first"})

    # It should unpack correctly into 2 variables.
    step, kwargs = sug
    assert step == "drop_duplicates"
    assert kwargs == {"keep": "first"}

    # It should work natively with ar.pipeline
    df = pd.DataFrame(
        {
            "id": [1, 2, 2],
        }
    )
    frame = ar.from_pandas(df)
    clean = ar.pipeline(frame, [sug])
    assert clean.shape == (2, 1)


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


def test_auto_clean_strict_casts_require_explicit_opt_in():
    frame = ar.from_pandas(pd.DataFrame({"active": ["true", "false"]}))

    with pytest.raises(ValueError, match="would apply type casts"):
        ar.auto_clean(frame, mode="strict")


def test_auto_clean_strict_casts_require_preview_confirmation():
    frame = ar.from_pandas(pd.DataFrame({"active": ["true", "false"]}))

    with pytest.raises(ValueError, match="requires confirmed_casts"):
        ar.auto_clean(frame, mode="strict", allow_lossy_casts=True)


def test_auto_clean_strict_rejects_mismatched_cast_confirmation():
    frame = ar.from_pandas(pd.DataFrame({"active": ["true", "false"]}))

    with pytest.raises(ValueError, match="must match the proposed cast mapping"):
        ar.auto_clean(
            frame,
            mode="strict",
            allow_lossy_casts=True,
            confirmed_casts={"active": "int64"},
        )


@pytest.mark.parametrize(
    "confirmed_casts",
    [
        [("active", "bool")],
        {1: "bool"},
        {"active": 1},
    ],
    ids=["list", "non-string-key", "non-string-value"],
)
def test_auto_clean_rejects_invalid_confirmed_casts(confirmed_casts):
    frame = ar.from_pandas(pd.DataFrame({"active": ["true", "false"]}))

    with pytest.raises(TypeError, match="confirmed_casts"):
        ar.auto_clean(frame, mode="strict", confirmed_casts=confirmed_casts)


def test_exclude_columns_prevents_leakage_in_json():
    import json

    frame = ar.from_pandas(pd.DataFrame({"secret_token": ["true", "false"]}))
    report = ar.profile(frame)

    report_dict = report.to_dict(exclude_columns=["secret_token"])
    json_str = json.dumps(report_dict)

    assert "secret_token" not in json_str


def test_auto_clean_dry_run_returns_report_without_mutating():
    frame = ar.from_pandas(pd.DataFrame({"active": ["true", "false"]}))

    report = ar.auto_clean(frame, mode="strict", dry_run=True)

    assert isinstance(report, ar.DataQualityReport)
    assert ("cast_types", {"active": "bool"}) in report.suggestions
    assert frame.dtypes["active"] == "string"


def test_auto_clean_strict_casts_after_explicit_preview_confirmation():
    frame = ar.from_pandas(pd.DataFrame({"active": ["true", "false"]}))
    report = ar.auto_clean(frame, mode="strict", dry_run=True)
    confirmed_casts = dict(report.suggestions)["cast_types"]

    clean = ar.auto_clean(
        frame,
        mode="strict",
        allow_lossy_casts=True,
        confirmed_casts=confirmed_casts,
    )
    result = ar.to_pandas(clean)

    assert list(result["active"]) == [True, False]
    assert pd.api.types.is_bool_dtype(result["active"])


def test_auto_clean_dry_run_with_return_report_raises():
    frame = ar.from_pandas(pd.DataFrame({"name": [" Alice ", " Bob "]}))

    with pytest.raises(
        ValueError, match="return_report=True cannot be used with dry_run=True"
    ):
        ar.auto_clean(frame, dry_run=True, return_report=True)


@pytest.mark.parametrize(
    "value",
    [
        "yes",
        1,
        None,
        [],
        object(),
    ],
    ids=["string", "integer", "none", "list", "object"],
)
def test_auto_clean_rejects_non_boolean_return_report(value):
    frame = ar.from_pandas(pd.DataFrame({"name": [" Alice ", " Bob "]}))

    with pytest.raises(TypeError, match="return_report must be a bool"):
        ar.auto_clean(frame, return_report=value)


def test_auto_clean_accepts_boolean_return_report_values():
    frame = ar.from_pandas(pd.DataFrame({"name": [" Alice ", " Bob "]}))

    clean_only = ar.auto_clean(frame, return_report=False)
    clean_with_report = ar.auto_clean(frame, return_report=True)

    assert isinstance(clean_only, ar.ArFrame)
    assert isinstance(clean_with_report, tuple)
    assert len(clean_with_report) == 2
    cleaned, report = clean_with_report
    assert isinstance(cleaned, ar.ArFrame)
    assert isinstance(report, ar.DataQualityReport)


def test_auto_clean_rejects_unknown_mode(sample_csv):
    frame = ar.read_csv(sample_csv)

    try:
        ar.auto_clean(frame, mode="wild")
        assert False, "Expected ValueError"
    except ValueError as exc:
        assert "mode must be" in str(exc)


def test_auto_clean_strict_casts_ambiguous_numeric_strings():
    df = pd.DataFrame(
        {
            "code": ["007", "008"],  # Not identifier-like, but has leading zeros
            "user_id": ["001", "002"],  # Identifier-like, has leading zeros
        }
    )
    frame = ar.from_pandas(df)

    # Verify that without allow_lossy_casts, strict mode fails
    with pytest.raises(ValueError, match="would apply type casts"):
        ar.auto_clean(frame, mode="strict")

    # Apply strict mode after explicitly confirming the previewed cast mapping.
    report = ar.auto_clean(frame, mode="strict", dry_run=True)
    clean = ar.auto_clean(
        frame,
        mode="strict",
        allow_lossy_casts=True,
        confirmed_casts=dict(report.suggestions)["cast_types"],
    )
    result = ar.to_pandas(clean)

    # "code" is cast to int64, losing leading zeros
    assert list(result["code"]) == [7, 8]
    assert pd.api.types.is_integer_dtype(result["code"])

    # "user_id" is protected and retains leading zeros
    assert list(result["user_id"]) == ["001", "002"]
    assert pd.api.types.is_string_dtype(result["user_id"])


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


def test_profile_approx_top_values_deterministic_high_cardinality():
    values = [f"user_{i}" for i in range(2000)]
    frame = ar.from_pandas(pd.DataFrame({"user": values}))

    report = ar.profile(
        frame,
        approx_top_values=True,
        approx_top_values_min_unique=1000,
        approx_top_values_min_ratio=0.5,
        approx_top_values_sample_size=200,
    )
    report_again = ar.profile(
        frame,
        approx_top_values=True,
        approx_top_values_min_unique=1000,
        approx_top_values_min_ratio=0.5,
        approx_top_values_sample_size=200,
    )

    column = report.columns["user"]
    assert column.top_values_is_approximate is True
    assert column.top_values == report_again.columns["user"].top_values
    assert len(column.top_values) <= 5
    assert column.top_values_sample_count == 200
    assert column.top_values_sample_ratio == pytest.approx(0.1, rel=1e-3)

    payload = report.to_dict()
    col_dict = payload["columns"]["user"]
    assert col_dict["top_values_is_approximate"] is True
    assert col_dict["top_values_sample_count"] == 200


def test_profile_approx_top_values_skips_low_cardinality():
    frame = ar.from_pandas(pd.DataFrame({"city": ["a", "b", "a", "c"]}))

    report = ar.profile(
        frame,
        approx_top_values=True,
        approx_top_values_min_unique=10,
        approx_top_values_min_ratio=0.9,
    )

    column = report.columns["city"]
    assert column.top_values_is_approximate is False
    assert column.top_values[0][0] == "a"
    assert column.top_values[0][1] == 2


def test_profile_approx_top_values_avoids_exact_counts(monkeypatch):
    values = [f"user_{i}" for i in range(1500)]
    frame = ar.from_pandas(pd.DataFrame({"user": values}))

    def raise_exact(*_args, **_kwargs):
        raise AssertionError("exact top_values should not be called")

    monkeypatch.setattr("arnio.quality._top_values", raise_exact)

    report = ar.profile(
        frame,
        approx_top_values=True,
        approx_top_values_min_unique=1000,
        approx_top_values_min_ratio=0.5,
        approx_top_values_sample_size=200,
    )

    assert report.columns["user"].top_values_is_approximate is True


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


def test_quality_to_dict_redacts_top_values_when_requested(tmp_path):
    path = tmp_path / "dict_redacted_top_values.csv"
    path.write_text("email\nalice@example.com\nalice@example.com\nbob@example.com\n")
    report = ar.profile(ar.read_csv(path), sample_size=2)

    d = report.to_dict(redact_sample_values=True)

    assert d["columns"]["email"]["sample_values"] == ["[REDACTED]", "[REDACTED]"]
    assert d["columns"]["email"]["top_values"] == [
        {"value": "[REDACTED]", "count": 2, "ratio": pytest.approx(2 / 3)},
        {"value": "[REDACTED]", "count": 1, "ratio": pytest.approx(1 / 3)},
    ]
    assert report.columns["email"].top_values == [
        ("alice@example.com", 2, pytest.approx(2 / 3)),
        ("bob@example.com", 1, pytest.approx(1 / 3)),
    ]


@pytest.mark.parametrize(
    "invalid_value",
    ["true", 1, None, ["redact"], object()],
)
def test_redact_sample_values_requires_bool(tmp_path, invalid_value):
    path = tmp_path / "redact_type.csv"
    path.write_text("name\nAlice\n")
    report = ar.profile(ar.read_csv(path), sample_size=1)

    with pytest.raises(TypeError, match="redact_sample_values must be a bool"):
        report.to_dict(redact_sample_values=invalid_value)

    with pytest.raises(TypeError, match="redact_sample_values must be a bool"):
        report.to_json(redact_sample_values=invalid_value)

    with pytest.raises(TypeError, match="redact_sample_values must be a bool"):
        report.columns["name"].to_dict(redact_sample_values=invalid_value)


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


def test_profile_approx_top_values_validation(tmp_path):
    path = tmp_path / "sample.csv"
    path.write_text("id\n1\n")
    frame = ar.read_csv(path)

    with pytest.raises(TypeError, match="approx_top_values must be a bool"):
        ar.profile(frame, approx_top_values="yes")

    with pytest.raises(
        TypeError, match="approx_top_values_min_unique must be an integer"
    ):
        ar.profile(frame, approx_top_values_min_unique="5")

    with pytest.raises(
        ValueError, match="approx_top_values_min_unique must be non-negative"
    ):
        ar.profile(frame, approx_top_values_min_unique=-1)

    with pytest.raises(TypeError, match="approx_top_values_min_ratio must be a float"):
        ar.profile(frame, approx_top_values_min_ratio="0.5")

    with pytest.raises(
        ValueError, match="approx_top_values_min_ratio must be between 0 and 1"
    ):
        ar.profile(frame, approx_top_values_min_ratio=1.5)

    with pytest.raises(
        ValueError,
        match="approx_top_values_min_ratio must be a finite number between 0 and 1",
    ):
        ar.profile(frame, approx_top_values_min_ratio=float("nan"))

    with pytest.raises(
        ValueError,
        match="approx_top_values_min_ratio must be a finite number between 0 and 1",
    ):
        ar.profile(frame, approx_top_values_min_ratio=float("inf"))

    with pytest.raises(
        ValueError,
        match="approx_top_values_min_ratio must be a finite number between 0 and 1",
    ):
        ar.profile(frame, approx_top_values_min_ratio=float("-inf"))

    with pytest.raises(
        TypeError, match="approx_top_values_sample_size must be an integer"
    ):
        ar.profile(frame, approx_top_values_sample_size="10")

    with pytest.raises(
        ValueError, match="approx_top_values_sample_size must be positive"
    ):
        ar.profile(frame, approx_top_values_sample_size=0)


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

    report = ar.auto_clean(frame, mode="strict", dry_run=True)
    cleaned = ar.auto_clean(
        frame,
        mode="strict",
        allow_lossy_casts=True,
        confirmed_casts=dict(report.suggestions)["cast_types"],
    )
    result = ar.to_pandas(cleaned)
    assert list(result["id"]) == ["001", "002", "003"]
    assert list(result["customer_id"]) == ["00123", "00456", "00789"]
    assert list(result["zip_code"]) == ["01234", "02345", "03456"]


def test_profile_detects_near_constant_column():
    frame = ar.from_pandas(
        pd.DataFrame({"status": (["active"] * 95 + ["inactive"] * 5)})
    )

    report = ar.profile(frame)

    assert "near_constant" in report.columns["status"].warnings
    assert "constant" not in report.columns["status"].warnings


def test_profile_constant_column_not_marked_near_constant():
    frame = ar.from_pandas(pd.DataFrame({"status": ["active"] * 100}))

    report = ar.profile(frame)

    assert "constant" in report.columns["status"].warnings
    assert "near_constant" not in report.columns["status"].warnings


def test_profile_balanced_column_not_marked_near_constant():
    frame = ar.from_pandas(
        pd.DataFrame({"status": (["active"] * 50 + ["inactive"] * 50)})
    )

    report = ar.profile(frame)

    assert "near_constant" not in report.columns["status"].warnings


def test_profile_near_constant_ignores_nulls():
    frame = ar.from_pandas(
        pd.DataFrame({"status": (["active"] * 95 + ["inactive"] * 5 + [None] * 20)})
    )

    report = ar.profile(frame)

    assert "near_constant" in report.columns["status"].warnings


def test_profile_near_constant_threshold_boundary():
    frame = ar.from_pandas(
        pd.DataFrame({"status": (["active"] * 95 + ["inactive"] * 5)})
    )

    report = ar.profile(frame)

    assert "near_constant" in report.columns["status"].warnings


def test_profile_detects_high_cardinality_identifier_column(tmp_path):
    path = tmp_path / "ids.csv"
    path.write_text(
        "user_id\n" + "\n".join(f"id_{i}" for i in range(200)),
        encoding="utf-8",
    )

    frame = ar.read_csv(path)
    report = ar.profile(frame)

    assert "high_cardinality" in report.columns["user_id"].warnings


def test_profile_low_cardinality_column_not_marked_high_cardinality(tmp_path):
    path = tmp_path / "status.csv"
    values = ["active", "inactive"] * 100
    path.write_text("status\n" + "\n".join(values), encoding="utf-8")

    frame = ar.read_csv(path)
    report = ar.profile(frame)

    assert "high_cardinality" not in report.columns["status"].warnings


def test_profile_constant_column_not_marked_high_cardinality(tmp_path):
    path = tmp_path / "constant.csv"
    path.write_text("user_id\n" + "\n".join(["same"] * 200), encoding="utf-8")

    frame = ar.read_csv(path)
    report = ar.profile(frame)

    assert "high_cardinality" not in report.columns["user_id"].warnings


def test_profile_null_heavy_column_not_marked_high_cardinality(tmp_path):
    path = tmp_path / "null_heavy.csv"
    values = [f"id_{i}" for i in range(20)] + [""] * 180
    path.write_text("user_id\n" + "\n".join(values), encoding="utf-8")

    frame = ar.read_csv(path)
    report = ar.profile(frame)

    assert "high_cardinality" not in report.columns["user_id"].warnings


def test_profile_exclude_columns_default_behavior(sample_csv):
    frame = ar.read_csv(sample_csv)

    report = ar.profile(frame)

    assert set(report.columns) == set(frame.columns)
    assert report.column_count == len(frame.columns)


def test_profile_exclude_columns_valid_exclusion(tmp_path):
    path = tmp_path / "profile_exclude.csv"
    path.write_text(
        "id,status,raw_payload\n" "1,active,{a}\n" "2,inactive,{b}\n" "3,active,{c}\n",
        encoding="utf-8",
    )

    frame = ar.read_csv(path)
    report = ar.profile(frame, exclude_columns=["id", "raw_payload"])

    assert list(report.columns) == ["status"]
    assert report.column_count == 1
    markdown = report.to_markdown()
    html = report.to_html()

    assert "| status |" in markdown
    assert "| id |" not in markdown
    assert "| raw_payload |" not in markdown
    assert ">id<" not in html
    assert ">raw_payload<" not in html


def test_profile_exclude_columns_scopes_memory_usage(tmp_path):
    path = tmp_path / "profile_memory_scope.csv"
    large_values = ["x" * 1000 for _ in range(100)]
    path.write_text(
        "keep,drop\n" + "\n".join(f"{i},{large_values[i]}" for i in range(100)) + "\n",
        encoding="utf-8",
    )

    frame = ar.read_csv(path)

    full_report = ar.profile(frame)
    scoped_report = ar.profile(frame, exclude_columns=["drop"])

    assert scoped_report.memory_usage < full_report.memory_usage


def test_profile_default_memory_usage_matches_frame_memory_usage(sample_csv):
    frame = ar.read_csv(sample_csv)

    report = ar.profile(frame)

    assert report.memory_usage == frame.memory_usage()


def test_profile_exclude_columns_rejects_missing_column(sample_csv):
    frame = ar.read_csv(sample_csv)

    with pytest.raises(KeyError, match="Missing columns for profile"):
        ar.profile(frame, exclude_columns=["missing"])


@pytest.mark.parametrize(
    "exclude_columns",
    [
        123,
        (name for name in ["name"]),
    ],
)
def test_profile_exclude_columns_rejects_non_sequences(sample_csv, exclude_columns):
    frame = ar.read_csv(sample_csv)

    with pytest.raises(TypeError, match="exclude_columns must be a sequence"):
        ar.profile(frame, exclude_columns=exclude_columns)


def test_profile_exclude_columns_rejects_bare_string(sample_csv):
    frame = ar.read_csv(sample_csv)

    with pytest.raises(TypeError, match="exclude_columns must be a sequence"):
        ar.profile(frame, exclude_columns="name")


def test_profile_exclude_columns_rejects_non_string_items(sample_csv):
    frame = ar.read_csv(sample_csv)

    with pytest.raises(TypeError, match="exclude_columns must contain only string"):
        ar.profile(frame, exclude_columns=["name", 123])


def test_profile_exclude_columns_accepts_empty_list(sample_csv):
    frame = ar.read_csv(sample_csv)

    full_report = ar.profile(frame)
    report = ar.profile(frame, exclude_columns=[])

    assert list(report.columns) == list(full_report.columns)
    assert report.column_count == full_report.column_count


def test_profile_exclude_columns_scopes_report_metrics_and_suggestions(tmp_path):
    path = tmp_path / "profile_scope.csv"
    path.write_text(
        "id,score\n" "1,10\n" "1,10\n" "2,20\n",
        encoding="utf-8",
    )

    frame = ar.read_csv(path)
    full_report = ar.profile(frame)
    scoped_report = ar.profile(frame, exclude_columns=["id"])

    assert full_report.column_count == 2
    assert scoped_report.column_count == 1
    assert list(scoped_report.columns) == ["score"]

    assert full_report.duplicate_rows == 1
    assert scoped_report.duplicate_rows == 1

    assert all(
        getattr(suggestion, "kwargs", {}).get("subset") != ["id"]
        for suggestion in scoped_report.suggestions
    )


# ── string length statistics tests ───────────────────────────────────────────


def test_decimal_looking_strings_suggest_float64_not_int64():
    frame = ar.from_pandas(pd.DataFrame({"price": ["1.0", "2.50", "3.00"]}))

    report = ar.profile(frame)

    assert report.columns["price"].suggested_dtype == "float64"

    suggestions = {}
    for step, kwargs in ar.suggest_cleaning(report):
        if step == "cast_types":
            suggestions.update(kwargs)

    assert suggestions["price"] == "float64"


def test_finite_numeric_strings_suggest_float64():
    frame = ar.from_pandas(pd.DataFrame({"x": ["1.5", "2.0", "3.14"]}))

    report = ar.profile(frame)

    assert report.columns["x"].suggested_dtype == "float64"


@pytest.mark.parametrize(
    "values",
    [
        ["inf", "2.0"],
        ["-inf", "2.0"],
        ["Infinity", "2.0"],
    ],
)
def test_non_finite_numeric_strings_do_not_suggest_float64(values):
    frame = ar.from_pandas(pd.DataFrame({"x": values}))

    report = ar.profile(frame)

    assert report.columns["x"].suggested_dtype is None


def test_auto_clean_strict_float64_suggestions_are_executable():
    frame = ar.from_pandas(pd.DataFrame({"x": ["1.5", "2.0"]}))
    report = ar.auto_clean(frame, mode="strict", dry_run=True)

    clean = ar.auto_clean(
        frame,
        mode="strict",
        allow_lossy_casts=True,
        confirmed_casts=dict(report.suggestions)["cast_types"],
    )

    result = ar.to_pandas(clean)

    assert pd.api.types.is_float_dtype(result["x"])
    assert list(result["x"]) == [1.5, 2.0]


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


def test_profile_empty_numeric_column_iqr_outliers_none():
    frame = ar.from_pandas(pd.DataFrame({"score": pd.Series(dtype="float64")}))
    report = ar.profile(frame)
    profile = report.columns["score"].to_dict()

    assert profile["iqr"] is None
    assert profile["outlier_lower_bound"] is None
    assert profile["outlier_upper_bound"] is None
    assert profile["outlier_count"] is None
    assert profile["outlier_ratio"] is None


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

    path.write_text("id,name\n1,Alice\n2,Bob\n")

    report = ar.profile(ar.read_csv(path))

    md = report.to_markdown()

    assert "# Data Quality Report" in md
    assert "## Overview" in md
    assert "## Columns" in md
    assert "| id | int64 | identifier |" in md


def test_report_to_markdown_writes_to_stringio(sample_csv, tmp_path):
    import io

    frame = ar.read_csv(sample_csv)
    report = ar.profile(frame)
    buffer = io.StringIO()

    result = report.to_markdown(output=buffer)

    assert result is None
    assert buffer.getvalue() == report.to_markdown()
    assert "# Data Quality Report" in buffer.getvalue()


def test_report_to_markdown_writes_to_text_file_handle(sample_csv, tmp_path):
    frame = ar.read_csv(sample_csv)
    report = ar.profile(frame)
    out_path = tmp_path / "report.md"

    with out_path.open("w", encoding="utf-8") as f:
        result = report.to_markdown(output=f)

    assert result is None
    assert out_path.read_text(encoding="utf-8") == report.to_markdown()


def test_report_to_markdown_rejects_invalid_output(sample_csv, tmp_path):
    frame = ar.read_csv(sample_csv)
    report = ar.profile(frame)

    with pytest.raises(TypeError, match="output must be a writable text stream"):
        report.to_markdown(output=object())


def test_report_to_markdown_includes_uniqueness_metrics(tmp_path):
    path = tmp_path / "unique_metrics.csv"

    path.write_text("id,name\n1,Alice\n2,Bob\n2,Bob\n")

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

    path.write_text("id,name\n1,Alice\n2,Bob\n")

    report = ar.profile(ar.read_csv(path))

    assert report.to_markdown() == report.to_markdown()


def test_report_to_markdown_escapes_pipe_characters_in_column_cells():
    report = ar.DataQualityReport(
        row_count=2,
        column_count=1,
        memory_usage=128,
        duplicate_rows=0,
        duplicate_ratio=0.0,
        columns={
            "bad|name": ar.ColumnProfile(
                name="bad|name",
                dtype="string",
                semantic_type="free|text",
                row_count=2,
                null_count=0,
                null_ratio=0.0,
                unique_count=2,
                unique_ratio=1.0,
                warnings=["contains | pipe"],
            )
        },
        suggestions=[],
    )

    md = report.to_markdown()

    assert "bad\\|name" in md
    assert "free\\|text" in md
    assert "contains \\| pipe" in md


def test_report_to_markdown_escapes_newlines_in_cell_values():
    """Newlines in column names or warnings must not break Markdown table rows."""
    from arnio.quality import ColumnProfile, DataQualityReport

    report = DataQualityReport(
        row_count=2,
        column_count=1,
        memory_usage=128,
        duplicate_rows=0,
        duplicate_ratio=0.0,
        columns={
            "col\nname": ColumnProfile(
                name="col\nname",
                dtype="string\r\nwith newline",
                semantic_type="text\rwith CR",
                row_count=2,
                null_count=0,
                null_ratio=0.0,
                unique_count=2,
                unique_ratio=1.0,
                warnings=["warn\nwith newline", "warn\r\nwith CRLF"],
            )
        },
        suggestions=[],
    )

    md = report.to_markdown()

    # Newlines must be replaced with <br>
    assert "<br>" in md
    assert "col\nname" not in md
    assert "warn\nwith newline" not in md
    assert "warn\r\nwith CRLF" not in md
    assert "string\r\nwith newline" not in md
    assert "text\rwith CR" not in md

    # col name and warning content should still appear, escaped
    assert "col<br>name" in md
    assert "warn<br>with newline" in md
    assert "warn<br>with CRLF" in md


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


def test_report_to_markdown_suggestions_stable_ordering():
    unordered_kwargs = {"z_item": 100, "a_item": "test", "m_item": True}

    report = ar.DataQualityReport(
        row_count=10,
        column_count=2,
        memory_usage=128,
        duplicate_rows=0,
        duplicate_ratio=0.0,
        columns={},
        suggestions=[("custom_clean", unordered_kwargs)],
    )

    md = report.to_markdown()
    expected_substring = (
        '`custom_clean`: `{"a_item": "test", "m_item": true, "z_item": 100}`'
    )
    assert expected_substring in md


def test_report_to_markdown_limits_suggestions():
    report = ar.DataQualityReport(
        row_count=2,
        column_count=1,
        memory_usage=100,
        duplicate_rows=0,
        duplicate_ratio=0.0,
        columns={},
        suggestions=[
            ("strip_whitespace", {"columns": ["name"]}),
            ("drop_nulls", {"subset": ["age"]}),
            ("normalize_case", {"columns": ["city"]}),
        ],
    )

    md = report.to_markdown(max_suggestions=2)

    assert "strip_whitespace" in md
    assert "drop_nulls" in md
    assert "normalize_case" not in md
    assert "Showing 2 of 3 suggestions." in md
    assert len(report.suggestions) == 3


def test_report_to_markdown_max_suggestions_none_preserves_default():
    report = ar.DataQualityReport(
        row_count=2,
        column_count=1,
        memory_usage=100,
        duplicate_rows=0,
        duplicate_ratio=0.0,
        columns={},
        suggestions=[
            ("strip_whitespace", {"columns": ["name"]}),
            ("drop_nulls", {"subset": ["age"]}),
        ],
    )

    assert report.to_markdown(max_suggestions=None) == report.to_markdown()


@pytest.mark.parametrize("value", [0, -1])
def test_report_to_markdown_rejects_non_positive_max_suggestions(value):
    report = ar.DataQualityReport(
        row_count=0,
        column_count=0,
        memory_usage=0,
        duplicate_rows=0,
        duplicate_ratio=0.0,
        columns={},
        suggestions=[],
    )

    with pytest.raises(ValueError, match="max_suggestions must be positive"):
        report.to_markdown(max_suggestions=value)


@pytest.mark.parametrize("value", [True, 1.5, "2"])
def test_report_to_markdown_rejects_invalid_max_suggestions_type(value):
    report = ar.DataQualityReport(
        row_count=0,
        column_count=0,
        memory_usage=0,
        duplicate_rows=0,
        duplicate_ratio=0.0,
        columns={},
        suggestions=[],
    )

    with pytest.raises(TypeError, match="max_suggestions must be an integer or None"):
        report.to_markdown(max_suggestions=value)


def test_report_to_markdown_suggestions_normal_existing_output(tmp_path):
    path = tmp_path / "sample_data.csv"
    path.write_text("id,name\n1,Alice\n2,Bob\n2,Bob\n")

    report = ar.profile(ar.read_csv(path))
    md = report.to_markdown()

    if report.suggestions:
        assert '{"' in md
        assert '"}' in md


def test_report_to_markdown_suggestions_non_json_serializable():
    class DummyObject:
        def __str__(self):
            return "custom_val"

    mixed_kwargs = {"custom_field": DummyObject(), "strategy": "mean"}

    report = ar.DataQualityReport(
        row_count=10,
        column_count=2,
        memory_usage=128,
        duplicate_rows=0,
        duplicate_ratio=0.0,
        columns={},
        suggestions=[("custom_clean", mixed_kwargs)],
    )

    md = report.to_markdown()

    expected_substring = (
        '`custom_clean`: `{"custom_field": "custom_val", "strategy": "mean"}`'
    )
    assert expected_substring in md


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


def test_data_quality_report_to_html(tmp_path):
    df = pd.DataFrame(
        {
            "id": [1, 2, 3],
            "<script>malicious</script>": ["A", "B", "C"],
        }
    )
    frame = ar.from_pandas(df)
    report = ar.profile(frame)

    html_out = report.to_html()

    assert html_out.startswith("<!DOCTYPE html>")
    assert "Data Quality Report" in html_out
    assert "&lt;script&gt;malicious&lt;/script&gt;" in html_out
    assert "<script>" not in html_out
    assert "Rows" in html_out
    assert "3" in html_out

    out_path = tmp_path / "report.html"
    report.to_html(file_path=str(out_path))
    assert out_path.exists()
    assert out_path.read_text(encoding="utf-8").startswith("<!DOCTYPE html>")


def test_report_to_html_rejects_invalid_filepath_types():
    report = ar.DataQualityReport(
        row_count=0,
        column_count=0,
        memory_usage=0,
        duplicate_rows=0,
        duplicate_ratio=0.0,
        columns={},
        suggestions=[],
    )

    invalid_paths = [True, False, 123, object()]

    for invalid_path in invalid_paths:
        with pytest.raises(TypeError, match="must be a string, bytes, or os.PathLike"):
            report.to_html(file_path=invalid_path)


def test_report_to_html_limits_suggestions():
    report = ar.DataQualityReport(
        row_count=2,
        column_count=1,
        memory_usage=100,
        duplicate_rows=0,
        duplicate_ratio=0.0,
        columns={},
        suggestions=[
            ("strip_whitespace", {"columns": ["name"]}),
            ("drop_nulls", {"subset": ["age"]}),
            ("normalize_case", {"columns": ["city"]}),
        ],
    )

    html = report.to_html(max_suggestions=2)

    assert "strip_whitespace" in html
    assert "drop_nulls" in html
    assert "normalize_case" not in html
    assert "Showing 2 of 3 suggestions." in html
    assert len(report.suggestions) == 3


def test_report_to_html_max_suggestions_none_preserves_default():
    report = ar.DataQualityReport(
        row_count=2,
        column_count=1,
        memory_usage=100,
        duplicate_rows=0,
        duplicate_ratio=0.0,
        columns={},
        suggestions=[
            ("strip_whitespace", {"columns": ["name"]}),
            ("drop_nulls", {"subset": ["age"]}),
        ],
    )

    assert report.to_html(max_suggestions=None) == report.to_html()


@pytest.mark.parametrize("value", [0, -1])
def test_report_to_html_rejects_non_positive_max_suggestions(value):
    report = ar.DataQualityReport(
        row_count=0,
        column_count=0,
        memory_usage=0,
        duplicate_rows=0,
        duplicate_ratio=0.0,
        columns={},
        suggestions=[],
    )

    with pytest.raises(ValueError, match="max_suggestions must be positive"):
        report.to_html(max_suggestions=value)


@pytest.mark.parametrize("value", [True, 1.5, "2"])
def test_report_to_html_rejects_invalid_max_suggestions_type(value):
    report = ar.DataQualityReport(
        row_count=0,
        column_count=0,
        memory_usage=0,
        duplicate_rows=0,
        duplicate_ratio=0.0,
        columns={},
        suggestions=[],
    )

    with pytest.raises(TypeError, match="max_suggestions must be an integer or None"):
        report.to_html(max_suggestions=value)


def test_report_to_html_writes_to_stringio(sample_csv, tmp_path):
    import io

    frame = ar.read_csv(sample_csv)
    report = ar.profile(frame)
    buffer = io.StringIO()

    result = report.to_html(output=buffer)

    assert result is None
    assert buffer.getvalue() == report.to_html()
    assert "<html" in buffer.getvalue()


def test_report_to_html_writes_to_text_file_handle(sample_csv, tmp_path):
    frame = ar.read_csv(sample_csv)
    report = ar.profile(frame)
    out_path = tmp_path / "report.html"

    with out_path.open("w", encoding="utf-8") as f:
        result = report.to_html(output=f)

    assert result is None
    assert out_path.read_text(encoding="utf-8") == report.to_html()


def test_report_to_html_rejects_invalid_output(sample_csv, tmp_path):
    frame = ar.read_csv(sample_csv)
    report = ar.profile(frame)

    with pytest.raises(TypeError, match="output must be a writable text stream"):
        report.to_html(output=object())


def test_report_to_html_preserves_file_path_behavior(sample_csv, tmp_path):
    frame = ar.read_csv(sample_csv)
    report = ar.profile(frame)
    out_path = tmp_path / "report.html"

    result = report.to_html(file_path=str(out_path))

    assert result == report.to_html()
    assert out_path.read_text(encoding="utf-8") == result


def test_data_quality_report_to_html_focused(tmp_path):
    from arnio.quality import CleaningSuggestion, ColumnProfile, DataQualityReport

    # 1. Construct a mock ColumnProfile with HTML characters in warning and name, and specific missing value counts and dtypes
    col_unsafe = ColumnProfile(
        name="<script>unsafe_col</script>",
        dtype="int64",
        semantic_type="numeric",
        row_count=10,
        null_count=3,
        null_ratio=0.3,
        unique_count=5,
        unique_ratio=0.5,
        empty_string_count=0,
        whitespace_count=0,
        suggested_dtype="<script>unsafe_dtype</script>",
        warnings=["<script>unsafe_warning</script>"],
        top_values=[
            ("<script>unsafe_val</script>", 7, 0.7),
            ("B", 2, 0.2),
            ("C", 1, 0.1),
        ],
    )

    # 2. Construct a CleaningSuggestion with HTML characters
    suggest = CleaningSuggestion(
        step="<script>unsafe_step</script>",
        kwargs={"col": "<script>unsafe_val</script>"},
        confidence_score=0.95,
        confidence_reason="<script>unsafe_reason</script>",
    )

    # 3. Construct DataQualityReport
    report = DataQualityReport(
        row_count=10,
        column_count=1,
        memory_usage=80,
        duplicate_rows=2,
        duplicate_ratio=0.2,
        columns={"<script>unsafe_col</script>": col_unsafe},
        quality_score=95.0,
        score_components={"null_penalty": -5.0},
        suggestions=[suggest],
    )

    # 4. Generate HTML and assert safe escaping, missing-value counts, and dtype rendering
    html_out = report.to_html()

    # Verify basic HTML structures
    assert html_out.startswith("<!DOCTYPE html>")
    assert "Data Quality Report" in html_out

    # Verify missing-value counts and dtype rendering
    assert "3" in html_out  # null_count
    assert "int64" in html_out  # dtype
    assert "10" in html_out  # row_count

    # Verify proper HTML escaping of column name
    assert "&lt;script&gt;unsafe_col&lt;/script&gt;" in html_out
    assert "<script>unsafe_col</script>" not in html_out

    # Verify proper HTML escaping of warnings
    assert "&lt;script&gt;unsafe_warning&lt;/script&gt;" in html_out
    assert "<script>unsafe_warning</script>" not in html_out

    # Verify proper HTML escaping of suggestions
    assert "&lt;script&gt;unsafe_step&lt;/script&gt;" in html_out
    assert "<script>unsafe_step</script>" not in html_out
    assert "&lt;script&gt;unsafe_val&lt;/script&gt;" in html_out
    assert "<script>unsafe_val</script>" not in html_out
    assert "&lt;script&gt;unsafe_reason&lt;/script&gt;" in html_out
    assert "<script>unsafe_reason</script>" not in html_out
    assert "0.95" in html_out  # confidence_score is rendered
    assert "&lt;script&gt;unsafe_dtype&lt;/script&gt;" in html_out

    # Verify proper HTML escaping of top_values
    assert "&lt;script&gt;unsafe_val&lt;/script&gt;" in html_out
    assert "<script>unsafe_val</script>" not in html_out

    # Verify file writing
    out_path = tmp_path / "report_focused.html"
    report.to_html(file_path=str(out_path))
    assert out_path.exists()
    assert out_path.read_text(encoding="utf-8").startswith("<!DOCTYPE html>")


def test_data_quality_report_repr_html_snippet():
    from arnio.quality import ColumnProfile, DataQualityReport

    col = ColumnProfile(
        name="<script>unsafe_col</script>",
        dtype="object",
        semantic_type="string",
        row_count=3,
        null_count=1,
        null_ratio=1 / 3,
        unique_count=2,
        unique_ratio=2 / 3,
        warnings=["<script>unsafe_warning</script>"],
        top_values=[("<script>unsafe_val</script>", 2, 2 / 3)],
    )
    report = DataQualityReport(
        row_count=3,
        column_count=1,
        memory_usage=1234,
        duplicate_rows=0,
        duplicate_ratio=0.0,
        columns={"x": col},
        quality_score=88.0,
        score_components={"null_penalty": -10.0},
    )

    html_out = report._repr_html_()
    assert "<!DOCTYPE html>" not in html_out
    assert 'class="arnio-dqr"' in html_out
    assert "Data Quality Report" in html_out
    assert "&lt;script&gt;unsafe_col&lt;/script&gt;" in html_out
    assert "<script>unsafe_col</script>" not in html_out


# ── to_html redaction and column-exclusion tests (Fixes #1754) ────────────────


def test_to_html_redact_top_values_hides_labels():
    """redact_top_values=True must replace every chip label with [REDACTED]
    while still rendering counts/ratios."""
    from arnio.quality import ColumnProfile, DataQualityReport

    col = ColumnProfile(
        name="email",
        dtype="string",
        semantic_type="email",
        row_count=10,
        null_count=0,
        null_ratio=0.0,
        unique_count=3,
        unique_ratio=0.3,
        top_values=[
            ("alice@secret.com", 5, 0.5),
            ("bob@secret.com", 3, 0.3),
            ("carol@secret.com", 2, 0.2),
        ],
    )
    report = DataQualityReport(
        row_count=10,
        column_count=1,
        memory_usage=100,
        duplicate_rows=0,
        duplicate_ratio=0.0,
        columns={"email": col},
    )

    html = report.to_html(redact_top_values=True)

    assert "alice@secret.com" not in html
    assert "bob@secret.com" not in html
    assert "carol@secret.com" not in html
    assert "[REDACTED]" in html
    assert "50%" in html
    assert "30%" in html
    assert "20%" in html


def test_to_html_redact_top_values_false_shows_real_labels():
    """Default (redact_top_values=False) must still render actual top-value labels."""
    from arnio.quality import ColumnProfile, DataQualityReport

    col = ColumnProfile(
        name="city",
        dtype="string",
        semantic_type="categorical",
        row_count=6,
        null_count=0,
        null_ratio=0.0,
        unique_count=2,
        unique_ratio=0.333333,
        top_values=[
            ("Paris", 4, 0.666667),
            ("Lyon", 2, 0.333333),
        ],
    )
    report = DataQualityReport(
        row_count=6,
        column_count=1,
        memory_usage=80,
        duplicate_rows=0,
        duplicate_ratio=0.0,
        columns={"city": col},
    )

    html = report.to_html()

    assert "Paris" in html
    assert "Lyon" in html
    assert "[REDACTED]" not in html


def test_to_html_exclude_columns_drops_column_from_table():
    """exclude_columns must prevent the column row from appearing in the HTML table."""
    from arnio.quality import ColumnProfile, DataQualityReport

    def make_col(name: str) -> ColumnProfile:
        return ColumnProfile(
            name=name,
            dtype="string",
            semantic_type="text",
            row_count=4,
            null_count=0,
            null_ratio=0.0,
            unique_count=4,
            unique_ratio=1.0,
            top_values=[(f"val_{name}", 1, 0.25)],
        )

    report = DataQualityReport(
        row_count=4,
        column_count=2,
        memory_usage=80,
        duplicate_rows=0,
        duplicate_ratio=0.0,
        columns={
            "public_col": make_col("public_col"),
            "secret_col": make_col("secret_col"),
        },
    )

    html = report.to_html(exclude_columns=["secret_col"])

    assert "secret_col" not in html
    assert "val_secret_col" not in html
    assert "public_col" in html
    assert "val_public_col" in html


def test_to_html_redact_and_exclude_combined():
    """redact_top_values and exclude_columns can be used together."""
    from arnio.quality import ColumnProfile, DataQualityReport

    def make_col(name: str, value: str) -> ColumnProfile:
        return ColumnProfile(
            name=name,
            dtype="string",
            semantic_type="text",
            row_count=4,
            null_count=0,
            null_ratio=0.0,
            unique_count=2,
            unique_ratio=0.5,
            top_values=[(value, 3, 0.75)],
        )

    report = DataQualityReport(
        row_count=4,
        column_count=2,
        memory_usage=80,
        duplicate_rows=0,
        duplicate_ratio=0.0,
        columns={
            "visible": make_col("visible", "safe_value"),
            "hidden": make_col("hidden", "secret_value"),
        },
    )

    html = report.to_html(redact_top_values=True, exclude_columns=["hidden"])

    assert "<code>hidden</code>" not in html
    assert "secret_value" not in html
    assert "visible" in html
    assert "safe_value" not in html
    assert "[REDACTED]" in html


def test_to_html_redact_top_values_must_be_bool():
    """redact_top_values rejects non-bool values."""
    from arnio.quality import DataQualityReport

    report = DataQualityReport(
        row_count=0,
        column_count=0,
        memory_usage=0,
        duplicate_rows=0,
        duplicate_ratio=0.0,
        columns={},
    )
    for bad in [1, "true", None, 0.0]:
        with pytest.raises(TypeError, match="redact_top_values must be a bool"):
            report.to_html(redact_top_values=bad)  # type: ignore[arg-type]


def test_to_html_exclude_columns_rejects_unknown_column():
    """exclude_columns raises KeyError for column names not in the report."""
    from arnio.quality import DataQualityReport

    report = DataQualityReport(
        row_count=0,
        column_count=0,
        memory_usage=0,
        duplicate_rows=0,
        duplicate_ratio=0.0,
        columns={},
    )
    with pytest.raises(KeyError, match="Unknown exclude_columns"):
        report.to_html(exclude_columns=["does_not_exist"])


def test_to_html_exclude_columns_rejects_non_collection():
    """exclude_columns rejects bare strings and non-sequence types."""
    from arnio.quality import DataQualityReport

    report = DataQualityReport(
        row_count=0,
        column_count=0,
        memory_usage=0,
        duplicate_rows=0,
        duplicate_ratio=0.0,
        columns={},
    )
    with pytest.raises(
        TypeError, match="exclude_columns must be a list, tuple, set, or None"
    ):
        report.to_html(exclude_columns="col_name")  # type: ignore[arg-type]

    with pytest.raises(
        TypeError, match="exclude_columns must be a list, tuple, set, or None"
    ):
        report.to_html(exclude_columns=123)  # type: ignore[arg-type]


def test_to_html_exclude_columns_accepts_set_and_tuple():
    """exclude_columns works when passed as a set or tuple."""
    from arnio.quality import ColumnProfile, DataQualityReport

    col = ColumnProfile(
        name="sensitive",
        dtype="string",
        semantic_type="text",
        row_count=2,
        null_count=0,
        null_ratio=0.0,
        unique_count=2,
        unique_ratio=1.0,
    )
    report = DataQualityReport(
        row_count=2,
        column_count=1,
        memory_usage=50,
        duplicate_rows=0,
        duplicate_ratio=0.0,
        columns={"sensitive": col},
    )

    html_set = report.to_html(exclude_columns={"sensitive"})
    html_tuple = report.to_html(exclude_columns=("sensitive",))

    assert "sensitive" not in html_set
    assert "sensitive" not in html_tuple


def test_repr_html_unaffected_by_new_params():
    """_repr_html_() still works with no arguments and shows values by default."""
    from arnio.quality import ColumnProfile, DataQualityReport

    col = ColumnProfile(
        name="x",
        dtype="string",
        semantic_type="text",
        row_count=2,
        null_count=0,
        null_ratio=0.0,
        unique_count=2,
        unique_ratio=1.0,
        top_values=[("hello", 1, 0.5), ("world", 1, 0.5)],
    )
    report = DataQualityReport(
        row_count=2,
        column_count=1,
        memory_usage=50,
        duplicate_rows=0,
        duplicate_ratio=0.0,
        columns={"x": col},
    )

    html = report._repr_html_()

    assert "<!DOCTYPE html>" not in html
    assert 'class="arnio-dqr"' in html
    assert "hello" in html
    assert "world" in html
    assert "[REDACTED]" not in html


# ── explain mode tests ────────────────────────────────────────────────────────


def test_auto_clean_explain_normal_clean(tmp_path):
    """Normal auto_clean with explain=False and return_report=False should return ArFrame."""
    path = tmp_path / "data.csv"
    path.write_text("id,name\n1, Alice \n2, Bob \n")
    frame = ar.read_csv(path)

    result = ar.auto_clean(frame, explain=False, return_report=False)
    assert isinstance(result, ar.ArFrame)


def test_auto_clean_explain_return_report_only(tmp_path):
    """return_report=True and explain=False should return (ArFrame, DataQualityReport)."""
    path = tmp_path / "data.csv"
    path.write_text("id,name\n1, Alice \n2, Bob \n")
    frame = ar.read_csv(path)

    result = ar.auto_clean(frame, explain=False, return_report=True)
    assert isinstance(result, tuple)
    assert len(result) == 2
    cleaned, report = result
    assert isinstance(cleaned, ar.ArFrame)
    assert isinstance(report, ar.DataQualityReport)


def test_auto_clean_explain_returns_tuple(tmp_path):
    """explain=True and return_report=False should return (ArFrame, CleanExplanation)."""
    path = tmp_path / "data.csv"
    path.write_text("id,name\n1, Alice \n2, Alice \n")
    frame = ar.read_csv(path)

    result = ar.auto_clean(frame, mode="strict", explain=True, allow_lossy_casts=True)

    assert isinstance(result, tuple)
    assert len(result) == 2
    cleaned, explanation = result
    assert isinstance(cleaned, ar.ArFrame)
    assert isinstance(explanation, ar.CleanExplanation)


def test_auto_clean_explain_row_counts(tmp_path):
    """CleanExplanation rows_before/after/removed should be accurate."""
    path = tmp_path / "dups.csv"
    path.write_text("id,name\n1,Alice\n1,Alice\n2,Bob\n")
    frame = ar.read_csv(path)

    cleaned, explanation = ar.auto_clean(
        frame, mode="strict", explain=True, allow_lossy_casts=True
    )

    assert explanation.rows_before == 3
    assert explanation.rows_after == 2
    assert explanation.rows_removed == 1
    assert explanation.mode == "strict"


def test_auto_clean_explain_steps_recorded(tmp_path):
    """Each applied step should produce a CleanStepRecord."""
    path = tmp_path / "ws.csv"
    path.write_text("id,name\n1, Alice \n2, Bob \n")
    frame = ar.read_csv(path)

    cleaned, explanation = ar.auto_clean(
        frame, mode="safe", explain=True, allow_lossy_casts=True
    )

    assert len(explanation.steps) >= 1
    step = explanation.steps[0]
    assert isinstance(step, ar.CleanStepRecord)
    assert step.step == "strip_whitespace"
    assert step.rows_before == 2
    assert step.rows_after == 2
    assert step.rows_removed == 0
    assert isinstance(step.reason, str)
    assert len(step.reason) > 0


def test_auto_clean_explain_with_return_report(tmp_path):
    """explain=True and return_report=True should return (ArFrame, DataQualityReport, CleanExplanation)."""
    path = tmp_path / "data.csv"
    path.write_text("id,name\n1, Alice \n2, Bob \n")
    frame = ar.read_csv(path)

    result = ar.auto_clean(
        frame,
        mode="safe",
        return_report=True,
        explain=True,
        allow_lossy_casts=True,
    )

    assert isinstance(result, tuple)
    assert len(result) == 3
    cleaned, report, explanation = result
    assert isinstance(cleaned, ar.ArFrame)
    assert isinstance(report, ar.DataQualityReport)
    assert isinstance(explanation, ar.CleanExplanation)


def test_auto_clean_explain_no_steps_clean_data(tmp_path):
    """A perfectly clean dataset should result in zero steps applied."""
    path = tmp_path / "clean.csv"
    path.write_text("id,name\n1,Alice\n2,Bob\n")
    frame = ar.read_csv(path)

    cleaned, explanation = ar.auto_clean(
        frame, mode="strict", explain=True, allow_lossy_casts=True
    )

    assert explanation.rows_removed == 0
    assert explanation.rows_before == explanation.rows_after


def test_auto_clean_explain_str_representation(tmp_path):
    """CleanExplanation __str__ should be human-readable."""
    path = tmp_path / "ws.csv"
    path.write_text("id,name\n1, Alice \n2, Bob \n")
    frame = ar.read_csv(path)

    _, explanation = ar.auto_clean(
        frame, mode="safe", explain=True, allow_lossy_casts=True
    )
    text = str(explanation)

    assert "CleanExplanation" in text
    assert "rows" in text
    assert "steps applied" in text


def test_auto_clean_explain_dry_run_error(tmp_path):
    """Using explain=True with dry_run=True should raise a ValueError."""
    path = tmp_path / "data.csv"
    path.write_text("id,name\n1,Alice\n2,Bob\n")
    frame = ar.read_csv(path)

    import pytest

    with pytest.raises(
        ValueError, match="explain=True cannot be used with dry_run=True"
    ):
        ar.auto_clean(frame, explain=True, dry_run=True)


def test_compare_profiles_under_threshold_is_ok():
    """Changes below warning thresholds should result in 'ok' status."""
    baseline = ar.profile(ar.from_pandas(pd.DataFrame({"score": [10.0, 11.0, 12.0]})))
    # Shift values by 0.1 to keep std constant but shift mean slightly
    current = ar.profile(ar.from_pandas(pd.DataFrame({"score": [10.1, 11.1, 12.1]})))

    comparison = ar.compare_profiles(baseline, current)
    assert comparison.drift_report["score"]["status"] == "ok"
    assert comparison.status_counts == {"ok": 1, "warning": 0, "changed": 0}


def test_compare_profiles_above_warning_threshold_is_warning():
    """Changes above warning but below changed threshold should result in 'warning' status."""
    baseline = ar.profile(ar.from_pandas(pd.DataFrame({"score": [10.0, 11.0, 12.0]})))
    # Shift values by 1.8 to trigger warning status (approx 15% shift)
    current = ar.profile(ar.from_pandas(pd.DataFrame({"score": [11.8, 12.8, 13.8]})))

    comparison = ar.compare_profiles(baseline, current)
    assert comparison.drift_report["score"]["status"] == "warning"
    assert comparison.status_counts == {"ok": 0, "warning": 1, "changed": 0}


def test_compare_profiles_above_changed_threshold_is_changed():
    """Changes above changed threshold should result in 'changed' status."""
    baseline = ar.profile(ar.from_pandas(pd.DataFrame({"score": [10.0, 11.0, 12.0]})))
    # Shift values by 5.0 to trigger changed status (approx 45% shift)
    current = ar.profile(ar.from_pandas(pd.DataFrame({"score": [15.0, 16.0, 17.0]})))

    comparison = ar.compare_profiles(baseline, current)
    assert comparison.drift_report["score"]["status"] == "changed"
    assert comparison.status_counts == {"ok": 0, "warning": 0, "changed": 1}


# ── duplicate_rows correctness tests (Refs #662) ─────────────────────────────
# These tests verify the duplicate_rows field in DataQualityReport against
# the pandas df.duplicated().sum() baseline.  profile() continues to use
# df.duplicated().sum() as its default; the hash_pandas_object candidate
# is covered separately below for future comparison only.


class TestProfileDuplicateRowsCorrectness:
    """Focused correctness tests for duplicate_rows in DataQualityReport.

    profile() uses df.duplicated().sum() as its default implementation.
    Each test asserts ar.profile() against the pandas baseline directly so
    any future change to the counting path is immediately caught.
    """

    def _baseline(self, frame: ar.ArFrame) -> int:
        """Reference implementation: pandas df.duplicated().sum()."""
        return int(ar.to_pandas(frame).duplicated().sum())

    def test_no_duplicates(self):
        frame = ar.from_pandas(pd.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "z"]}))
        assert ar.profile(frame).duplicate_rows == 0
        assert ar.profile(frame).duplicate_rows == self._baseline(frame)

    def test_all_duplicate_rows(self):
        frame = ar.from_pandas(pd.DataFrame({"a": [7, 7, 7], "b": ["q", "q", "q"]}))
        # 3 rows, 1 unique → 2 duplicates
        assert ar.profile(frame).duplicate_rows == 2
        assert ar.profile(frame).duplicate_rows == self._baseline(frame)

    def test_partial_duplicates(self):
        frame = ar.from_pandas(
            pd.DataFrame({"a": [1, 1, 2, 3, 3], "b": ["x", "x", "y", "z", "z"]})
        )
        # rows 0==1 and 3==4 → 2 duplicates
        assert ar.profile(frame).duplicate_rows == 2
        assert ar.profile(frame).duplicate_rows == self._baseline(frame)

    def test_null_rows_treated_as_duplicates(self):
        # Two rows where every cell is null should count as one duplicate,
        # matching pandas default (NaN == NaN for deduplication purposes).
        frame = ar.from_pandas(
            pd.DataFrame({"a": [None, None, 1.0], "b": [None, None, 2.0]})
        )
        assert ar.profile(frame).duplicate_rows == 1
        assert ar.profile(frame).duplicate_rows == self._baseline(frame)

    def test_partial_null_rows(self):
        # Only the null-containing column matches; the other differs.
        frame = ar.from_pandas(
            pd.DataFrame({"a": [None, None, 1.0], "b": [1.0, 2.0, 3.0]})
        )
        # All rows are distinct → 0 duplicates
        assert ar.profile(frame).duplicate_rows == 0
        assert ar.profile(frame).duplicate_rows == self._baseline(frame)

    def test_mixed_dtypes_int_float_string_bool(self):
        frame = ar.from_pandas(
            pd.DataFrame(
                {
                    "i": [1, 1, 2],
                    "f": [1.0, 1.0, 2.0],
                    "s": ["a", "a", "b"],
                    "b": [True, True, False],
                }
            )
        )
        assert ar.profile(frame).duplicate_rows == 1
        assert ar.profile(frame).duplicate_rows == self._baseline(frame)

    def test_single_row_frame(self):
        frame = ar.from_pandas(pd.DataFrame({"x": [42]}))
        assert ar.profile(frame).duplicate_rows == 0
        assert ar.profile(frame).duplicate_rows == self._baseline(frame)

    def test_empty_frame_returns_zero(self):
        frame = ar.from_pandas(pd.DataFrame({"x": pd.Series(dtype="float64")}))
        assert ar.profile(frame).duplicate_rows == 0

    def test_duplicate_ratio_consistent_with_duplicate_rows(self):
        frame = ar.from_pandas(
            pd.DataFrame({"a": [1, 1, 2, 3], "b": ["x", "x", "y", "z"]})
        )
        report = ar.profile(frame)
        assert report.duplicate_rows == 1
        assert abs(report.duplicate_ratio - 1 / 4) < 1e-9


# ── duplicate_rows timing guard (perf/#662) ───────────────────────────────────


def test_profile_duplicate_count_hash_path_matches_pandas_baseline_at_scale():
    """Verify hash_pandas_object produces the same duplicate count as df.duplicated().

    This test documents the candidate faster implementation explored in #662.
    The hash path is NOT currently used as the default in profile() — benchmark
    results were inconsistent across CI configurations (0.72x–1.58x depending
    on Python version and OS).  The correctness equivalence is preserved here so
    the implementation can be re-enabled once stable benchmark evidence is
    available across the full CI matrix.

    See benchmarks/benchmark_profile_duplicate_count.py for the manual timing
    comparison.
    """
    import numpy as np

    rng = np.random.default_rng(0)
    n = 50_000
    df = pd.DataFrame(
        {
            "a": rng.integers(0, int(n * 0.9), size=n).tolist(),
            "b": rng.uniform(0, 1000, size=n).tolist(),
            "c": [f"s{i % 5000}" for i in range(n)],
        }
    )
    frame = ar.from_pandas(df)
    df_converted = ar.to_pandas(frame)

    # Candidate path (not yet the default)
    hashes = pd.util.hash_pandas_object(df_converted, index=False)
    hash_count = int(hashes.duplicated().sum())

    # Current baseline — what profile() uses
    baseline_count = int(df_converted.duplicated().sum())

    assert hash_count == baseline_count
    assert ar.profile(frame).duplicate_rows == baseline_count


def test_report_repr_is_concise_and_stable():
    frame = ar.from_pandas(
        pd.DataFrame(
            {
                "b": [1, 2],
                "a": [3, 4],
            }
        )
    )

    report = ar.profile(frame)

    output = repr(report)

    assert "DataQualityReport(" in output
    assert "rows=2" in output
    assert "columns=2" in output

    # deterministic ordering
    assert "column_names=[a, b]" in output


def test_report_repr_handles_empty_reports():
    frame = ar.from_pandas(pd.DataFrame())

    report = ar.profile(frame)

    output = repr(report)

    assert "rows=0" in output
    assert "columns=0" in output
    assert "column_names=[]" in output


def test_report_to_dict_is_deterministic():
    frame = ar.from_pandas(
        pd.DataFrame(
            {
                "z": [1],
                "a": [2],
                "m": [3],
            }
        )
    )

    report = ar.profile(frame)

    result = report.to_dict()

    assert list(result["columns"].keys()) == ["a", "m", "z"]


def test_report_suggestions_are_deterministic():
    report = ar.DataQualityReport(
        row_count=1,
        column_count=1,
        memory_usage=1,
        duplicate_rows=0,
        duplicate_ratio=0.0,
        columns={},
        suggestions=[
            ("z_step", {"b": 2, "a": 1}),
            ("a_step", {"d": 4, "c": 3}),
        ],
    )

    result = report.to_dict()

    assert result["suggestions"][0]["step"] == "a_step"
    assert result["suggestions"][1]["step"] == "z_step"

    assert list(result["suggestions"][0]["kwargs"].keys()) == ["c", "d"]


# ── numeric histogram tests ──────────────────────────────────────────────────


def test_profile_numeric_histogram_normal():
    # Test normal distribution / sequence
    df = pd.DataFrame({"nums": list(range(1, 101))})
    frame = ar.from_pandas(df)
    report = ar.profile(frame)
    profile = report.columns["nums"]

    assert profile.histogram is not None
    assert len(profile.histogram) == 10

    # Check that counts sum to 100
    counts = [c for _, _, c, _ in profile.histogram]
    ratios = [r for _, _, _, r in profile.histogram]
    assert sum(counts) == 100
    assert abs(sum(ratios) - 1.0) < 1e-9

    # Check bounds
    assert profile.histogram[0][0] == 1.0
    assert profile.histogram[-1][1] == 100.0

    # Serialization test
    dct = profile.to_dict()
    assert "histogram" in dct
    assert len(dct["histogram"]) == 10
    assert dct["histogram"][0]["bucket_start"] == 1.0
    assert dct["histogram"][0]["count"] == 10
    assert abs(dct["histogram"][0]["ratio"] - 0.1) < 1e-9


def test_profile_numeric_histogram_constant_values():
    # Test constant values
    df = pd.DataFrame({"nums": [5.0] * 20})
    frame = ar.from_pandas(df)
    report = ar.profile(frame)
    profile = report.columns["nums"]

    assert profile.histogram is not None
    assert len(profile.histogram) == 10

    counts = [c for _, _, c, _ in profile.histogram]
    assert sum(counts) == 20

    # numpy.histogram handles constant values by setting bin boundaries offset by a small delta (typically +/- 0.5)
    # let's assert the counts are correct and serialize properly
    dct = profile.to_dict()
    assert "histogram" in dct
    assert len(dct["histogram"]) == 10


def test_profile_numeric_histogram_empty_and_all_nulls():
    # All nulls
    df = pd.DataFrame({"nums": [None, None, None]})
    df["nums"] = df["nums"].astype("float64")
    frame = ar.from_pandas(df)
    report = ar.profile(frame)
    profile = report.columns["nums"]
    assert profile.histogram is None

    # Empty column (0 rows)
    df_empty = pd.DataFrame({"nums": pd.Series(dtype="float64")})
    frame_empty = ar.from_pandas(df_empty)
    report_empty = ar.profile(frame_empty)
    profile_empty = report_empty.columns["nums"]
    assert profile_empty.histogram is None


def test_profile_numeric_histogram_missing_values():
    # Mix of nulls and numeric values
    df = pd.DataFrame({"nums": [10.0, None, 20.0, None, 30.0]})
    frame = ar.from_pandas(df)
    report = ar.profile(frame)
    profile = report.columns["nums"]

    assert profile.histogram is not None
    assert len(profile.histogram) == 10
    counts = [c for _, _, c, _ in profile.histogram]
    assert sum(counts) == 3  # only non-null values are counted

    ratios = [r for _, _, _, r in profile.histogram]
    assert abs(sum(ratios) - 1.0) < 1e-5


def test_profile_numeric_histogram_small_sample():
    # Just 1 value
    df = pd.DataFrame({"nums": [42.0]})
    frame = ar.from_pandas(df)
    report = ar.profile(frame)
    profile = report.columns["nums"]

    assert profile.histogram is not None
    assert len(profile.histogram) == 10
    counts = [c for _, _, c, _ in profile.histogram]
    assert sum(counts) == 1


def test_profile_numeric_histogram_non_numeric():
    # String column should have histogram = None
    df = pd.DataFrame({"names": ["Alice", "Bob", "Charlie"]})
    frame = ar.from_pandas(df)
    report = ar.profile(frame)
    profile = report.columns["names"]

    assert profile.histogram is None
    assert "histogram" in profile.to_dict()
    assert profile.to_dict()["histogram"] is None


def test_profile_numeric_histogram_to_pandas():
    df = pd.DataFrame({"nums": [1, 2, 3]})
    frame = ar.from_pandas(df)
    report = ar.profile(frame)

    pdf = report.to_pandas()
    assert "histogram" in pdf.columns
    assert pdf.loc[pdf["name"] == "nums", "histogram"].values[0] is not None


def test_profile_numeric_histogram_non_finite_values():
    # Test handling of infinite values in histogram calculation
    from arnio._core import _DType, _Frame
    from arnio.frame import ArFrame

    cpp_frame = _Frame.from_dict(
        {"nums": [1.0, 2.0, float("inf"), float("-inf"), None, 3.0]},
        {"nums": _DType.FLOAT64},
    )
    frame = ArFrame(cpp_frame)
    report = ar.profile(frame)
    profile = report.columns["nums"]

    # The histogram should filter out +/- inf and NaNs, binning only [1.0, 2.0, 3.0]
    assert profile.histogram is not None
    assert len(profile.histogram) == 10

    counts = [c for _, _, c, _ in profile.histogram]
    assert sum(counts) == 3

    # All infinities (no finite values to bin)
    cpp_frame_all_inf = _Frame.from_dict(
        {"nums": [float("inf"), float("-inf")]},
        {"nums": _DType.FLOAT64},
    )
    frame_all_inf = ArFrame(cpp_frame_all_inf)
    report_all_inf = ar.profile(frame_all_inf)
    profile_all_inf = report_all_inf.columns["nums"]
    assert profile_all_inf.histogram is None


def test_report_to_markdown_escapes_newlines_in_column_cells():
    report = ar.DataQualityReport(
        row_count=2,
        column_count=1,
        memory_usage=128,
        duplicate_rows=0,
        duplicate_ratio=0.0,
        columns={
            "multi\nline": ar.ColumnProfile(
                name="multi\nline",
                dtype="string",
                semantic_type="free\ntext",
                row_count=2,
                null_count=0,
                null_ratio=0.0,
                unique_count=2,
                unique_ratio=1.0,
                warnings=["contains\nnewline"],
            )
        },
        suggestions=[],
    )
    md = report.to_markdown()
    assert "multi<br>line" in md
    assert "free<br>text" in md
    assert "contains<br>newline" in md
    assert "| multi\nline |" not in md


def test_quality_gate_markdown_escapes_pipe_characters():
    report = ar.DataQualityReport(
        row_count=2,
        column_count=1,
        memory_usage=128,
        duplicate_rows=0,
        duplicate_ratio=0.0,
        columns={
            "col|name": ar.ColumnProfile(
                name="col|name",
                dtype="str|ing",
                semantic_type="cat|egory",
                row_count=2,
                null_count=0,
                null_ratio=0.0,
                unique_count=2,
                unique_ratio=1.0,
                warnings=["pipe|warning"],
            )
        },
        suggestions=[],
    )

    md = report.to_markdown()

    assert r"col\|name" in md
    assert r"str\|ing" in md
    assert r"cat\|egory" in md
    assert r"pipe\|warning" in md
    assert "| col|name |" not in md


def test_data_quality_report_to_dict_exclude_columns():
    frame = ar.read_csv(io.StringIO("name,age\nalice,20\nbob,30\n"))

    report = ar.profile(frame)

    result = report.to_dict(exclude_columns=["age"])

    assert "age" not in result["columns"]
    assert "name" in result["columns"]


def test_data_quality_report_to_dict_exclude_columns_accepts_set_and_tuple():
    frame = ar.read_csv(io.StringIO("name,age,secret_token\nalice,20,a\nbob,30,b\n"))

    report = ar.profile(frame)

    set_result = report.to_dict(exclude_columns={"secret_token"})
    tuple_result = report.to_dict(exclude_columns=("age",))

    assert "secret_token" not in set_result["columns"]
    assert "name" in set_result["columns"]
    assert "age" not in tuple_result["columns"]
    assert "name" in tuple_result["columns"]


def test_data_quality_report_to_dict_default_behavior():
    frame = ar.read_csv(io.StringIO("name\nalice\nbob\n"))

    report = ar.profile(frame)

    result = report.to_dict()

    assert "name" in result["columns"]


def test_data_quality_report_to_dict_unknown_column():
    frame = ar.read_csv(io.StringIO("name\nalice\nbob\n"))

    report = ar.profile(frame)

    with pytest.raises(
        KeyError, match="Unknown exclude_columns: \\['missing_column'\\]"
    ):
        report.to_dict(exclude_columns=["missing_column"])


def test_data_quality_report_to_dict_multiple_unknown_columns():
    frame = ar.read_csv(io.StringIO("name\nalice\nbob\n"))

    report = ar.profile(frame)

    with pytest.raises(
        KeyError,
        match="Unknown exclude_columns: \\['missing_column', 'secret_tokn'\\]",
    ):
        report.to_dict(exclude_columns=["secret_tokn", "missing_column"])


def test_data_quality_report_to_dict_invalid_exclude_columns_type():
    frame = ar.read_csv(io.StringIO("name\nalice\nbob\n"))

    report = ar.profile(frame)

    with pytest.raises(TypeError):
        report.to_dict(exclude_columns="name")


def test_data_quality_report_to_dict_invalid_exclude_columns_entries():
    frame = ar.read_csv(io.StringIO("name\nalice\nbob\n"))

    report = ar.profile(frame)

    with pytest.raises(TypeError):
        report.to_dict(exclude_columns=["name", 123])


def test_data_quality_report_to_dict_excludes_columns_from_suggestions():
    columns = ar.profile(
        ar.from_pandas(
            pd.DataFrame(
                {
                    "name": [" Alice ", "Bob"],
                    "age": [30, 40],
                }
            )
        )
    ).columns
    report = ar.DataQualityReport(
        row_count=2,
        column_count=2,
        memory_usage=100,
        duplicate_rows=0,
        duplicate_ratio=0.0,
        quality_score=1.0,
        score_components={},
        columns=columns,
        suggestions=[
            (
                "strip_whitespace",
                {
                    "subset": ["name", "age"],
                    "cast_types": {
                        "name": "string",
                        "age": "int",
                    },
                },
            )
        ],
    )

    result = report.to_dict(exclude_columns=["age"])

    kwargs = result["suggestions"][0]["kwargs"]

    assert kwargs["subset"] == ["name"]
    assert kwargs["cast_types"] == {"name": "string"}


def test_data_quality_report_to_dict_preserves_non_column_suggestion_values():
    columns = ar.profile(ar.from_pandas(pd.DataFrame({"age": [30, 40]}))).columns
    report = ar.DataQualityReport(
        row_count=2,
        column_count=1,
        memory_usage=100,
        duplicate_rows=0,
        duplicate_ratio=0.0,
        quality_score=1.0,
        score_components={},
        columns=columns,
        suggestions=[
            (
                "custom_step",
                {
                    "message": ["age"],
                    "metadata": {"age": "keep"},
                    "threshold": 5,
                },
            )
        ],
    )

    result = report.to_dict(exclude_columns=["age"])

    kwargs = result["suggestions"][0]["kwargs"]

    assert kwargs["message"] == ["age"]
    assert kwargs["metadata"] == {"age": "keep"}
    assert kwargs["threshold"] == 5


def test_data_quality_report_to_json_returns_valid_json():
    report = ar.DataQualityReport(
        row_count=10,
        column_count=1,
        memory_usage=100,
        duplicate_rows=0,
        duplicate_ratio=0.0,
        columns={},
    )

    json_output = report.to_json()

    parsed = json.loads(json_output)

    assert parsed["row_count"] == 10
    assert parsed["column_count"] == 1


def test_data_quality_report_to_json_writes_to_stringio():
    import io

    report = ar.profile(
        ar.from_pandas(
            pd.DataFrame(
                {
                    "name": ["Alice", "Bob"],
                    "age": [30, 40],
                }
            )
        )
    )
    buffer = io.StringIO()

    result = report.to_json(output=buffer)

    assert result is None
    assert buffer.getvalue() == report.to_json()


def test_data_quality_report_to_json_writes_to_text_file_handle(tmp_path):
    report = ar.profile(
        ar.from_pandas(
            pd.DataFrame(
                {
                    "name": ["Alice", "Bob"],
                    "age": [30, 40],
                }
            )
        )
    )
    out_path = tmp_path / "report.json"

    with out_path.open("w", encoding="utf-8") as f:
        result = report.to_json(output=f, indent=2)

    assert result is None
    assert out_path.read_text(encoding="utf-8") == report.to_json(indent=2)


def test_data_quality_report_to_json_rejects_invalid_output():
    report = ar.profile(
        ar.from_pandas(
            pd.DataFrame(
                {
                    "name": ["Alice", "Bob"],
                    "age": [30, 40],
                }
            )
        )
    )

    with pytest.raises(TypeError, match="output must be a writable text stream"):
        report.to_json(output=object())


def test_data_quality_report_to_json_output_preserves_options():
    import io

    report = ar.profile(
        ar.from_pandas(
            pd.DataFrame(
                {
                    "name": ["Alice", "Bob"],
                    "age": [30, 40],
                }
            )
        )
    )
    buffer = io.StringIO()

    result = report.to_json(
        output=buffer,
        indent=2,
        redact_sample_values=True,
        exclude_columns=["age"],
    )

    assert result is None
    assert buffer.getvalue() == report.to_json(
        indent=2,
        redact_sample_values=True,
        exclude_columns=["age"],
    )


def test_data_quality_report_to_json_indent():
    report = ar.DataQualityReport(
        row_count=10,
        column_count=1,
        memory_usage=100,
        duplicate_rows=0,
        duplicate_ratio=0.0,
        columns={},
    )

    json_output = report.to_json(indent=2)

    assert "\n" in json_output
    assert '  "row_count"' in json_output


def test_data_quality_report_to_json_exclude_columns():
    from arnio._core import _DType, _Frame
    from arnio.frame import ArFrame

    cpp_frame = _Frame.from_dict(
        {
            "name": ["John"],
            "age": [21],
        },
        {
            "name": _DType.STRING,
            "age": _DType.INT64,
        },
    )

    frame = ArFrame(cpp_frame)

    report = ar.profile(frame)

    json_output = report.to_json(exclude_columns=["age"])

    parsed = json.loads(json_output)

    assert "name" in parsed["columns"]
    assert "age" not in parsed["columns"]


def test_data_quality_report_to_json_unknown_exclude_column():
    report = ar.profile(
        ar.from_pandas(
            pd.DataFrame(
                {
                    "name": ["Alice", "Bob"],
                    "secret_token": ["abc", "def"],
                }
            )
        )
    )

    with pytest.raises(KeyError, match="Unknown exclude_columns: \\['secret_tokn'\\]"):
        report.to_json(exclude_columns=["secret_tokn"])


def test_data_quality_report_to_json_redact_sample_values():
    from arnio._core import _DType, _Frame
    from arnio.frame import ArFrame

    cpp_frame = _Frame.from_dict(
        {"name": ["John"]},
        {"name": _DType.STRING},
    )

    frame = ArFrame(cpp_frame)

    report = ar.profile(frame)

    json_output = report.to_json(redact_sample_values=True)

    parsed = json.loads(json_output)

    assert parsed["columns"]["name"]["sample_values"] == ["[REDACTED]"]


def test_report_suggestions_are_deterministic_with_nested_kwargs():
    report = ar.DataQualityReport(
        row_count=1,
        column_count=1,
        memory_usage=1,
        duplicate_rows=0,
        duplicate_ratio=0.0,
        columns={},
        suggestions=[
            (
                "same_step",
                {
                    "config": {"z": 1, "a": 2},
                    "values": [3, 2, 1],
                },
            ),
            (
                "same_step",
                {
                    "config": {"a": 2, "z": 1},
                    "values": [1, 2, 3],
                },
            ),
        ],
    )

    result = report.to_dict()

    assert result["suggestions"][0]["step"] == "same_step"
    assert result["suggestions"][1]["step"] == "same_step"


def test_data_quality_report_to_json_redacts_top_values():
    frame = ar.from_pandas(
        pd.DataFrame(
            {
                "email": [
                    "alice@example.com",
                    "alice@example.com",
                    "bob@example.com",
                ]
            }
        )
    )
    report = ar.profile(frame, sample_size=2)

    json_output = report.to_json(redact_sample_values=True)

    parsed = json.loads(json_output)

    assert parsed["columns"]["email"]["sample_values"] == ["[REDACTED]", "[REDACTED]"]
    assert parsed["columns"]["email"]["top_values"] == [
        {"value": "[REDACTED]", "count": 2, "ratio": pytest.approx(2 / 3)},
        {"value": "[REDACTED]", "count": 1, "ratio": pytest.approx(1 / 3)},
    ]


def test_profile_empty_dataframe():
    frame = ar.from_pandas(
        pd.DataFrame({"a": pd.Series(dtype="int64"), "b": pd.Series(dtype="float64")})
    )
    report = ar.profile(frame)
    assert report.row_count == 0
    assert report.column_count == 2
    assert report.duplicate_rows == 0
    assert report.memory_usage >= 0
    assert "a" in report.columns
    assert "b" in report.columns
    assert report.columns["a"].row_count == 0
    assert report.columns["a"].null_count == 0
    assert report.columns["b"].row_count == 0
    assert report.columns["b"].null_count == 0


# --- Tests for ProfileComparison.to_json() ---


def test_profile_comparison_to_json_returns_string():
    frame = ar.from_pandas(pd.DataFrame({"x": [1, 2, 3]}))
    p = ar.profile(frame)
    comparison = ar.compare_profiles(p, p)
    result = comparison.to_json()
    assert isinstance(result, str)
    parsed = json.loads(result)
    assert "drift_report" in parsed
    assert "status_counts" in parsed


def test_profile_comparison_to_json_indent():
    frame = ar.from_pandas(pd.DataFrame({"x": [1, 2, 3]}))
    p = ar.profile(frame)
    comparison = ar.compare_profiles(p, p)
    result = comparison.to_json(indent=2)
    assert "\n" in result


def test_profile_comparison_to_json_output_stream():
    frame = ar.from_pandas(pd.DataFrame({"x": [1, 2, 3]}))
    p = ar.profile(frame)
    comparison = ar.compare_profiles(p, p)
    buf = io.StringIO()
    ret = comparison.to_json(output=buf)
    assert ret is None
    assert len(buf.getvalue()) > 0


def test_profile_comparison_to_json_invalid_output_raises():
    frame = ar.from_pandas(pd.DataFrame({"x": [1, 2, 3]}))
    p = ar.profile(frame)
    comparison = ar.compare_profiles(p, p)
    with pytest.raises(TypeError, match="writable text stream"):
        comparison.to_json(output="not_a_stream")


# --- ProfileComparison.to_markdown() ---


def test_profile_comparison_to_markdown_returns_string():
    frame = ar.from_pandas(pd.DataFrame({"x": [1, 2, 3]}))
    p = ar.profile(frame)
    comparison = ar.compare_profiles(p, p)
    result = comparison.to_markdown()
    assert isinstance(result, str)
    assert "Profile Comparison Report" in result
    assert "Column Drift" in result


def test_profile_comparison_to_markdown_output_stream():
    frame = ar.from_pandas(pd.DataFrame({"x": [1, 2, 3]}))
    p = ar.profile(frame)
    comparison = ar.compare_profiles(p, p)
    buf = io.StringIO()
    ret = comparison.to_markdown(output=buf)
    assert ret is None
    assert "Profile Comparison" in buf.getvalue()


def test_profile_comparison_to_markdown_invalid_output_raises():
    frame = ar.from_pandas(pd.DataFrame({"x": [1, 2, 3]}))
    p = ar.profile(frame)
    comparison = ar.compare_profiles(p, p)
    with pytest.raises(TypeError, match="writable text stream"):
        comparison.to_markdown(output=42)


# --- Tests for QualityGateResult.to_json() ---


def test_quality_gate_result_to_json_returns_string():
    frame = ar.from_pandas(pd.DataFrame({"x": [1, 2, 3]}))
    p = ar.profile(frame)
    result = ar.check_quality_gates(p, p)
    out = result.to_json()
    assert isinstance(out, str)
    parsed = json.loads(out)
    assert "passed" in parsed
    assert "issues" in parsed


def test_quality_gate_result_to_json_indent():
    frame = ar.from_pandas(pd.DataFrame({"x": [1, 2, 3]}))
    p = ar.profile(frame)
    result = ar.check_quality_gates(p, p)
    out = result.to_json(indent=2)
    assert "\n" in out


def test_quality_gate_result_to_json_output_stream():
    frame = ar.from_pandas(pd.DataFrame({"x": [1, 2, 3]}))
    p = ar.profile(frame)
    result = ar.check_quality_gates(p, p)
    buf = io.StringIO()
    ret = result.to_json(output=buf)
    assert ret is None
    assert len(buf.getvalue()) > 0


def test_quality_gate_result_to_json_invalid_output_raises():
    frame = ar.from_pandas(pd.DataFrame({"x": [1, 2, 3]}))
    p = ar.profile(frame)
    result = ar.check_quality_gates(p, p)
    with pytest.raises(TypeError, match="writable text stream"):
        result.to_json(output=123)


# --- Tests for ProfileComparison.to_json() ---


def test_compare_profiles_mismatched_exclude_columns_hints_user():
    df = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6], "c": [7, 8, 9]})
    frame = ar.from_pandas(df)
    profile_a = ar.profile(frame, exclude_columns=["c"])
    profile_b = ar.profile(frame)

    with pytest.raises(ValueError, match="exclude_columns"):
        ar.compare_profiles(profile_a, profile_b)


class TestValidateGateThreshold:
    def test_none_returns_none(self):
        assert _validate_gate_threshold(None, "max_row_count_delta_ratio") is None

    def test_int_returns_float(self):
        result = _validate_gate_threshold(5, "max_row_count_delta_ratio")
        assert result == 5.0
        assert isinstance(result, float)

    def test_float_returns_float(self):
        result = _validate_gate_threshold(0.1, "max_row_count_delta_ratio")
        assert result == 0.1

    def test_bool_raises_type_error(self):
        with pytest.raises(TypeError, match="must be a non-negative number or None"):
            _validate_gate_threshold(True, "max_row_count_delta_ratio")

    def test_string_raises_type_error(self):
        with pytest.raises(TypeError, match="must be a non-negative number or None"):
            _validate_gate_threshold("0.1", "max_row_count_delta_ratio")

    def test_negative_raises_value_error(self):
        with pytest.raises(ValueError, match="must be a finite non-negative number"):
            _validate_gate_threshold(-0.1, "max_row_count_delta_ratio")

    def test_infinity_raises_value_error(self):
        with pytest.raises(ValueError, match="must be a finite non-negative number"):
            _validate_gate_threshold(math.inf, "max_row_count_delta_ratio")


class TestValidateGateBool:
    def test_true_returns_true(self):
        assert _validate_gate_bool(True, "allow_new_columns") is True

    def test_false_returns_false(self):
        assert _validate_gate_bool(False, "allow_new_columns") is False

    def test_int_raises_type_error(self):
        with pytest.raises(TypeError, match="must be a bool"):
            _validate_gate_bool(0, "allow_new_columns")

    def test_string_raises_type_error(self):
        with pytest.raises(TypeError, match="must be a bool"):
            _validate_gate_bool("true", "allow_new_columns")


class TestValidateGateRatioThreshold:
    def test_none_returns_none(self):
        assert _validate_gate_ratio_threshold(None, "max_null_ratio_delta") is None

    def test_valid_ratio_returns_float(self):
        result = _validate_gate_ratio_threshold(0.5, "max_null_ratio_delta")
        assert result == 0.5
        assert isinstance(result, float)

    def test_boundary_values(self):
        assert _validate_gate_ratio_threshold(0.0, "max_null_ratio_delta") == 0.0
        assert _validate_gate_ratio_threshold(1.0, "max_null_ratio_delta") == 1.0

    def test_value_above_one_raises_value_error(self):
        with pytest.raises(ValueError, match="must be a ratio between 0.0 and 1.0"):
            _validate_gate_ratio_threshold(1.01, "max_null_ratio_delta")

    def test_negative_raises_value_error(self):
        with pytest.raises(ValueError, match="must be a finite non-negative number"):
            _validate_gate_ratio_threshold(-0.05, "max_null_ratio_delta")

    def test_string_raises_type_error(self):
        with pytest.raises(TypeError, match="must be a non-negative number or None"):
            _validate_gate_ratio_threshold("0.5", "max_null_ratio_delta")


# ── ProfileComparison redaction tests ────────────────────────────────────────


def test_profile_comparison_to_dict_redacts_sample_values():
    """redact_sample_values=True must replace sample values in both nested profiles."""
    frame = ar.from_pandas(
        pd.DataFrame({"email": ["alice@example.com", "bob@example.com"]})
    )
    left = ar.profile(frame)
    right = ar.profile(frame)
    comparison = ar.compare_profiles(left, right)

    redacted = comparison.to_dict(redact_sample_values=True)
    plain = comparison.to_dict()

    # Sensitive values must not appear in the redacted export
    assert "alice@example.com" not in str(redacted)
    assert "bob@example.com" not in str(redacted)

    # Sample values are replaced with the redaction sentinel
    left_samples = redacted["left_profile"]["columns"]["email"]["sample_values"]
    right_samples = redacted["right_profile"]["columns"]["email"]["sample_values"]
    assert all(v == "[REDACTED]" for v in left_samples)
    assert all(v == "[REDACTED]" for v in right_samples)

    # Plain export still contains the real values
    assert "alice@example.com" in str(plain)


def test_profile_comparison_to_dict_exclude_columns():
    """exclude_columns must omit the named column from both nested profiles."""
    frame = ar.from_pandas(pd.DataFrame({"name": ["Alice", "Bob"], "score": [10, 20]}))
    left = ar.profile(frame)
    right = ar.profile(frame)
    comparison = ar.compare_profiles(left, right)

    result = comparison.to_dict(exclude_columns=["name"])

    assert "name" not in result["left_profile"]["columns"]
    assert "name" not in result["right_profile"]["columns"]
    # Non-excluded column is still present
    assert "score" in result["left_profile"]["columns"]
    assert "score" in result["right_profile"]["columns"]


def test_profile_comparison_to_json_redacts_sample_values():
    """to_json(redact_sample_values=True) must not contain sensitive values."""
    frame = ar.from_pandas(pd.DataFrame({"token": ["secret-abc", "secret-xyz"]}))
    left = ar.profile(frame)
    right = ar.profile(frame)
    comparison = ar.compare_profiles(left, right)

    json_redacted = comparison.to_json(redact_sample_values=True)
    json_plain = comparison.to_json()

    assert "secret-abc" not in json_redacted
    assert "secret-xyz" not in json_redacted
    assert "[REDACTED]" in json_redacted

    # Plain export contains the real values
    assert "secret-abc" in json_plain


def test_profile_comparison_constructor_validation():
    import pandas as pd

    frame = ar.from_pandas(pd.DataFrame({"col1": [1, 2, 3]}))
    valid_report = ar.profile(frame)

    # 1. Test that valid types construct perfectly fine without errors
    comparison = ar.quality.ProfileComparison(
        left_profile=valid_report,
        right_profile=valid_report,
        drift_report={},
        status_counts={},
    )
    assert comparison.drift_report == {}

    # 2. Test invalid left_profile type throws TypeError
    with pytest.raises(
        TypeError, match="left_profile must be an instance of DataQualityReport"
    ):
        ar.quality.ProfileComparison(
            left_profile="not_a_report_object",
            right_profile=valid_report,
            drift_report={},
            status_counts={},
        )

    # 3. Test invalid right_profile type throws TypeError
    with pytest.raises(
        TypeError, match="right_profile must be an instance of DataQualityReport"
    ):
        ar.quality.ProfileComparison(
            left_profile=valid_report,
            right_profile="not_a_report_object",
            drift_report={},
            status_counts={},
        )

    # 4. Test malformed nested drift_report dictionary throws TypeError
    with pytest.raises(
        TypeError, match="drift_report must be a nested dictionary of dict"
    ):
        ar.quality.ProfileComparison(
            left_profile=valid_report,
            right_profile=valid_report,
            drift_report={"col1": "should_be_a_dict_but_is_a_string"},
            status_counts={},
        )

    # 5. Test non-int status_counts values throw TypeError
    with pytest.raises(TypeError, match="status_counts values must be integers"):
        ar.quality.ProfileComparison(
            left_profile=valid_report,
            right_profile=valid_report,
            drift_report={},
            status_counts={"missing_values": "should_be_an_int"},
        )


def test_column_profile_invariant_valid_initialization():
    from arnio.quality import ColumnProfile

    cp = ColumnProfile(
        name="score",
        dtype="float64",
        semantic_type="numeric",
        row_count=100,
        null_count=5,
        null_ratio=0.05,
        unique_count=90,
        unique_ratio=0.9,
    )
    assert cp.name == "score"
    assert cp.row_count == 100


def test_column_profile_invariant_invalid_counts():
    from arnio.quality import ColumnProfile

    with pytest.raises(ValueError, match="row_count cannot be negative"):
        ColumnProfile("x", "int64", "numeric", -1, 0, 0.0, 0, 0.0)

    with pytest.raises(ValueError, match="null_count cannot be negative"):
        ColumnProfile("x", "int64", "numeric", 10, -5, 0.0, 0, 0.0)

    with pytest.raises(ValueError, match="top_values_sample_count cannot be negative"):
        ColumnProfile(
            "x", "int64", "numeric", 10, 0, 0.0, 0, 0.0, top_values_sample_count=-10
        )

    with pytest.raises(TypeError, match="row_count must be an integer"):
        ColumnProfile("x", "int64", "numeric", True, 0, 0.0, 0, 0.0)

    with pytest.raises(TypeError, match="null_count must be an integer"):
        ColumnProfile("x", "int64", "numeric", 10, "0", 0.0, 0, 0.0)

    with pytest.raises(ValueError, match="unique_count cannot be negative"):
        ColumnProfile("x", "int64", "numeric", 10, 0, 0.0, -1, 0.0)

    with pytest.raises(TypeError, match="unique_count must be an integer"):
        ColumnProfile("x", "int64", "numeric", 10, 0, 0.0, True, 0.0)


def test_column_profile_invariant_invalid_ratios():
    from arnio.quality import ColumnProfile

    with pytest.raises(ValueError, match="null_ratio must be a finite ratio"):
        ColumnProfile("x", "int64", "numeric", 10, 0, 1.05, 0, 0.0)

    with pytest.raises(ValueError, match="unique_ratio must be a finite ratio"):
        ColumnProfile("x", "int64", "numeric", 10, 0, 0.1, 0, -0.01)

    with pytest.raises(ValueError, match="email_validity_ratio must be a finite ratio"):
        ColumnProfile(
            "x", "string", "email", 10, 0, 0.0, 0, 0.0, email_validity_ratio=2.0
        )

    with pytest.raises(ValueError, match="null_ratio must be a finite ratio"):
        ColumnProfile("x", "int64", "numeric", 10, 0, float("nan"), 0, 0.0)

    with pytest.raises(ValueError, match="unique_ratio must be a finite ratio"):
        ColumnProfile("x", "int64", "numeric", 10, 0, 0.0, 0, float("inf"))


def test_data_quality_report_invariant_valid_initialization():
    from arnio.quality import DataQualityReport

    report = DataQualityReport(
        row_count=200,
        column_count=5,
        memory_usage=4096,
        duplicate_rows=10,
        duplicate_ratio=0.05,
        columns={},
        quality_score=95.5,
    )
    assert report.row_count == 200
    assert report.quality_score == 95.5


def test_data_quality_report_invariant_invalid_metrics():
    from arnio.quality import DataQualityReport

    with pytest.raises(ValueError, match="memory_usage cannot be negative"):
        DataQualityReport(10, 2, -1024, 0, 0.0, {})

    with pytest.raises(ValueError, match="quality_score must be a finite value"):
        DataQualityReport(10, 2, 512, 0, 0.0, {}, quality_score=100.5)

    with pytest.raises(ValueError, match="quality_score must be a finite value"):
        DataQualityReport(10, 2, 512, 0, 0.0, {}, quality_score=-1.0)

    with pytest.raises(TypeError, match="quality_score must be a number"):
        DataQualityReport(10, 2, 512, 0, 0.0, {}, quality_score=False)

    with pytest.raises(ValueError, match="quality_score must be a finite value"):
        DataQualityReport(10, 2, 512, 0, 0.0, {}, quality_score=float("nan"))


# ── CleanStepRecord and CleanExplanation validation tests (Fixes #1687) ──────


class TestCleanStepRecordValidation:
    """CleanStepRecord.__post_init__ must reject invalid field types early."""

    def _valid_record(self, **overrides):
        defaults = dict(
            step="strip_whitespace",
            kwargs={"subset": ["name"]},
            rows_before=10,
            rows_after=10,
            rows_removed=0,
            reason="whitespace found",
        )
        defaults.update(overrides)
        return ar.CleanStepRecord(**defaults)

    def test_valid_construction_succeeds(self):
        rec = self._valid_record()
        assert rec.step == "strip_whitespace"
        assert rec.rows_removed == 0

    def test_step_must_be_str(self):
        with pytest.raises(TypeError, match="step must be a str"):
            self._valid_record(step=42)

    def test_reason_must_be_str(self):
        with pytest.raises(TypeError, match="reason must be a str"):
            self._valid_record(reason=None)

    def test_kwargs_must_be_dict(self):
        with pytest.raises(TypeError, match="kwargs must be a dict"):
            self._valid_record(kwargs="not-a-dict")

    def test_rows_before_must_be_int(self):
        with pytest.raises(TypeError, match="rows_before must be an int"):
            self._valid_record(rows_before="ten")

    def test_rows_before_rejects_bool(self):
        with pytest.raises(TypeError, match="rows_before must be an int"):
            self._valid_record(rows_before=True)

    def test_rows_after_must_be_int(self):
        with pytest.raises(TypeError, match="rows_after must be an int"):
            self._valid_record(rows_after=3.5)

    def test_rows_removed_must_be_int(self):
        with pytest.raises(TypeError, match="rows_removed must be an int"):
            self._valid_record(rows_removed=[])

    def test_rows_before_cannot_be_negative(self):
        with pytest.raises(ValueError, match="rows_before cannot be negative"):
            self._valid_record(rows_before=-1)

    def test_rows_after_cannot_be_negative(self):
        with pytest.raises(ValueError, match="rows_after cannot be negative"):
            self._valid_record(rows_after=-5)

    def test_rows_removed_cannot_be_negative(self):
        with pytest.raises(ValueError, match="rows_removed cannot be negative"):
            self._valid_record(rows_removed=-3)


class TestCleanExplanationValidation:
    """CleanExplanation.__post_init__ must reject invalid field types early."""

    def _valid_record(self):
        return ar.CleanStepRecord(
            step="strip_whitespace",
            kwargs={},
            rows_before=5,
            rows_after=5,
            rows_removed=0,
            reason="whitespace",
        )

    def _valid_explanation(self, **overrides):
        defaults = dict(
            mode="safe",
            rows_before=5,
            rows_after=5,
            rows_removed=0,
            steps=[],
        )
        defaults.update(overrides)
        return ar.CleanExplanation(**defaults)

    def test_valid_construction_empty_steps(self):
        exp = self._valid_explanation()
        assert exp.mode == "safe"
        assert exp.steps == []

    def test_valid_construction_with_steps(self):
        exp = self._valid_explanation(steps=[self._valid_record()])
        assert len(exp.steps) == 1

    def test_mode_must_be_str(self):
        with pytest.raises(TypeError, match="mode must be a str"):
            self._valid_explanation(mode=123)

    def test_mode_rejects_none(self):
        with pytest.raises(TypeError, match="mode must be a str"):
            self._valid_explanation(mode=None)

    def test_rows_before_must_be_int(self):
        with pytest.raises(TypeError, match="rows_before must be an int"):
            self._valid_explanation(rows_before="a")

    def test_rows_before_rejects_bool(self):
        with pytest.raises(TypeError, match="rows_before must be an int"):
            self._valid_explanation(rows_before=True)

    def test_rows_after_must_be_int(self):
        with pytest.raises(TypeError, match="rows_after must be an int"):
            self._valid_explanation(rows_after=None)

    def test_rows_removed_must_be_int(self):
        with pytest.raises(TypeError, match="rows_removed must be an int"):
            self._valid_explanation(rows_removed=[])

    def test_rows_before_cannot_be_negative(self):
        with pytest.raises(ValueError, match="rows_before cannot be negative"):
            self._valid_explanation(rows_before=-1)

    def test_rows_after_cannot_be_negative(self):
        with pytest.raises(ValueError, match="rows_after cannot be negative"):
            self._valid_explanation(rows_after=-1)

    def test_rows_removed_cannot_be_negative(self):
        with pytest.raises(ValueError, match="rows_removed cannot be negative"):
            self._valid_explanation(rows_removed=-1)

    def test_steps_must_be_list(self):
        with pytest.raises(TypeError, match="steps must be a list"):
            self._valid_explanation(steps="bad")

    def test_steps_elements_must_be_cleansteprecord(self):
        with pytest.raises(TypeError, match="steps\\[0\\] must be a CleanStepRecord"):
            self._valid_explanation(steps=["bad"])

    def test_steps_rejects_mixed_list(self):
        with pytest.raises(TypeError, match="steps\\[1\\] must be a CleanStepRecord"):
            self._valid_explanation(steps=[self._valid_record(), 42])

    def test_original_issue_repro_raises_at_construction(self):
        """Regression: invalid state must be caught at construction, not in __str__."""
        with pytest.raises((TypeError, ValueError)):
            ar.CleanExplanation(
                mode=123,
                rows_before="a",
                rows_after=None,
                rows_removed=[],
                steps=["bad"],
            )

    def test_str_works_on_valid_explanation(self):
        exp = self._valid_explanation(steps=[self._valid_record()])
        text = str(exp)
        assert "CleanExplanation" in text
        assert "strip_whitespace" in text

    def test_str_works_on_empty_steps(self):
        exp = self._valid_explanation()
        text = str(exp)
        assert "(none)" in text


class TestQualityGateResultConstructorValidation:
    """Tests for QualityGateIssue and QualityGateResult constructor field validation."""

    def test_quality_gate_issue_valid(self):
        issue = ar.QualityGateIssue(
            metric="null_ratio",
            message="Column has too many nulls",
            column="age",
            baseline=0.05,
            current=0.10,
            threshold=0.08,
            delta=0.05,
        )
        assert issue.metric == "null_ratio"
        assert issue.message == "Column has too many nulls"
        assert issue.column == "age"
        assert issue.delta == 0.05
        assert issue.to_dict()["metric"] == "null_ratio"

    def test_quality_gate_issue_invalid_metric(self):
        with pytest.raises(TypeError, match="metric must be a str"):
            ar.QualityGateIssue(metric=123, message="msg")
        with pytest.raises(ValueError, match="metric must be a non-empty string"):
            ar.QualityGateIssue(metric="   ", message="msg")

    def test_quality_gate_issue_invalid_message(self):
        with pytest.raises(TypeError, match="message must be a str"):
            ar.QualityGateIssue(metric="null_ratio", message=42)
        with pytest.raises(ValueError, match="message must be a non-empty string"):
            ar.QualityGateIssue(metric="null_ratio", message="")

    def test_quality_gate_issue_invalid_column(self):
        with pytest.raises(TypeError, match="column must be a str or None"):
            ar.QualityGateIssue(metric="null_ratio", message="msg", column=123)

    def test_quality_gate_issue_invalid_delta(self):
        with pytest.raises(TypeError, match="delta must be a float, integer, or None"):
            ar.QualityGateIssue(metric="null_ratio", message="msg", delta="0.5")
        with pytest.raises(TypeError, match="delta must be a float, integer, or None"):
            ar.QualityGateIssue(metric="null_ratio", message="msg", delta=True)

    def test_quality_gate_result_valid(self):
        df = pd.DataFrame({"x": [1, 2, 3]})
        report = ar.profile(ar.from_pandas(df))

        issue = ar.QualityGateIssue(metric="null_ratio", message="msg")
        res = ar.QualityGateResult(
            baseline_profile=report,
            current_profile=report,
            issues=[issue],
            thresholds={"null_ratio": 0.05},
        )
        assert res.passed is False
        assert len(res.issues) == 1
        assert res.thresholds == {"null_ratio": 0.05}

    def test_quality_gate_result_invalid_profiles(self):
        issue = ar.QualityGateIssue(metric="null_ratio", message="msg")
        with pytest.raises(
            TypeError, match="baseline_profile must be a DataQualityReport instance"
        ):
            ar.QualityGateResult(
                baseline_profile="not a report",
                current_profile="not a report",
                issues=[issue],
                thresholds={},
            )

    def test_quality_gate_result_invalid_issues(self):
        df = pd.DataFrame({"x": [1, 2, 3]})
        report = ar.profile(ar.from_pandas(df))

        with pytest.raises(TypeError, match="issues must be a list"):
            ar.QualityGateResult(
                baseline_profile=report,
                current_profile=report,
                issues="not a list",
                thresholds={},
            )

        with pytest.raises(
            TypeError, match="issues\\[0\\] must be a QualityGateIssue instance"
        ):
            ar.QualityGateResult(
                baseline_profile=report,
                current_profile=report,
                issues=["not an issue"],
                thresholds={},
            )

    def test_quality_gate_result_invalid_thresholds(self):
        df = pd.DataFrame({"x": [1, 2, 3]})
        report = ar.profile(ar.from_pandas(df))
        issue = ar.QualityGateIssue(metric="null_ratio", message="msg")

        with pytest.raises(TypeError, match="thresholds must be a dict"):
            ar.QualityGateResult(
                baseline_profile=report,
                current_profile=report,
                issues=[issue],
                thresholds="not a dict",
            )
