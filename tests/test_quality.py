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


def test_profile_numeric_quantiles():
    frame = ar.from_pandas(pd.DataFrame({"age": [1.0, 2.0, 3.0, 4.0, 5.0]}))

    report = ar.profile(frame)
    profile = report.columns["age"].to_dict()

    assert profile["q25"] == 2.0
    assert profile["q50"] == 3.0
    assert profile["q75"] == 4.0
    assert profile["q95"] == 4.8


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


def test_profile_non_numeric_no_quantiles():
    frame = ar.from_pandas(pd.DataFrame({"name": ["Alice", "Bob", "Cara"]}))

    report = ar.profile(frame)
    profile = report.columns["name"].to_dict()

    assert "q25" not in profile
    assert "q50" not in profile
    assert "q75" not in profile
    assert "q95" not in profile


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


def test_auto_clean_dry_run_returns_report_without_mutating():
    frame = ar.from_pandas(pd.DataFrame({"active": ["true", "false"]}))

    report = ar.auto_clean(frame, mode="strict", dry_run=True)

    assert isinstance(report, ar.DataQualityReport)
    assert ("cast_types", {"active": "bool"}) in report.suggestions
    assert frame.dtypes["active"] == "string"


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

    # Apply strict mode with allow_lossy_casts
    clean = ar.auto_clean(frame, mode="strict", allow_lossy_casts=True)
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

    cleaned = ar.auto_clean(frame, mode="strict", allow_lossy_casts=True)
    result = ar.to_pandas(cleaned)
    assert list(result["id"]) == ["001", "002", "003"]
    assert list(result["customer_id"]) == ["00123", "00456", "00789"]
    assert list(result["zip_code"]) == ["01234", "02345", "03456"]


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

    # ── high cardinality warnings tests ──────────────────────────────────────────


def test_high_cardinality_flagged_for_id_like_column(tmp_path):
    path = tmp_path / "high_card.csv"
    path.write_text(
        "user_id\n1\n2\n3\n4\n5\n6\n7\n8\n9\n10\n"
    )
    report = ar.profile(ar.read_csv(path))

    assert report.columns["user_id"].high_cardinality is True
    assert "high_cardinality" in report.columns["user_id"].warnings


def test_high_cardinality_not_flagged_for_low_cardinality_column(tmp_path):
    path = tmp_path / "low_card.csv"
    path.write_text(
        "status\nactive\nactive\ninactive\nactive\ninactive\n"
    )
    report = ar.profile(ar.read_csv(path))

    assert report.columns["status"].high_cardinality is False
    assert "high_cardinality" not in report.columns["status"].warnings


def test_high_cardinality_appears_in_to_dict(tmp_path):
    path = tmp_path / "card_dict.csv"
    path.write_text(
        "uid\na\nb\nc\nd\ne\nf\ng\nh\ni\nj\n"
    )
    report = ar.profile(ar.read_csv(path))
    d = report.columns["uid"].to_dict()

    assert "high_cardinality" in d
    assert d["high_cardinality"] is True


def test_high_cardinality_false_for_single_value_column(tmp_path):
    path = tmp_path / "constant.csv"
    path.write_text(
        "flag\nyes\nyes\nyes\nyes\nyes\n"
    )
    report = ar.profile(ar.read_csv(path))

    assert report.columns["flag"].high_cardinality is False
