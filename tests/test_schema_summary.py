"""
Tests for ArFrame.schema_summary property.
"""

import pandas as pd
import pytest

import arnio as ar
from arnio.frame import ColumnSummary

# ---------------------------------------------------------------------------
# ColumnSummary dataclass
# ---------------------------------------------------------------------------


class TestColumnSummary:
    def test_column_summary_invalid_name(self):
        with pytest.raises(TypeError, match="name must be a str"):
            ColumnSummary(name=1, dtype="int64", nullable=False)

    def test_column_summary_invalid_dtype(self):
        with pytest.raises(TypeError, match="dtype must be a str"):
            ColumnSummary(name="id", dtype=2, nullable=False)

    def test_column_summary_invalid_nullable(self):
        with pytest.raises(TypeError, match="nullable must be a bool"):
            ColumnSummary(name="id", dtype="int64", nullable="yes")

    def test_column_summary_valid(self):
        entry = ColumnSummary("id", "int64", True)
        assert entry.name == "id"
        assert entry.dtype == "int64"
        assert entry.nullable is True

    def test_attributes(self):
        entry = ColumnSummary(name="age", dtype="int64", nullable=False)
        assert entry.name == "age"
        assert entry.dtype == "int64"
        assert entry.nullable is False

    def test_repr(self):
        entry = ColumnSummary(name="score", dtype="float64", nullable=True)
        r = repr(entry)
        assert "score" in r
        assert "float64" in r
        assert "True" in r

    def test_equality(self):
        a = ColumnSummary("x", "int64", False)
        b = ColumnSummary("x", "int64", False)
        assert a == b

    def test_inequality_name(self):
        assert ColumnSummary("x", "int64", False) != ColumnSummary("y", "int64", False)

    def test_inequality_dtype(self):
        assert ColumnSummary("x", "int64", False) != ColumnSummary(
            "x", "float64", False
        )

    def test_inequality_nullable(self):
        assert ColumnSummary("x", "int64", False) != ColumnSummary("x", "int64", True)

    def test_not_equal_to_non_column_summary(self):
        entry = ColumnSummary("x", "int64", False)
        assert entry.__eq__("x") is NotImplemented


# ---------------------------------------------------------------------------
# Normal behaviour
# ---------------------------------------------------------------------------


class TestSchemaSummaryNormal:
    def test_returns_list(self):
        df = pd.DataFrame({"a": [1, 2], "b": ["x", "y"]})
        frame = ar.from_pandas(df)
        result = frame.schema_summary
        assert isinstance(result, list)

    def test_length_matches_column_count(self):
        df = pd.DataFrame({"a": [1], "b": [2.0], "c": ["z"]})
        frame = ar.from_pandas(df)
        assert len(frame.schema_summary) == 3

    def test_each_entry_is_column_summary(self):
        df = pd.DataFrame({"a": [1]})
        frame = ar.from_pandas(df)
        for entry in frame.schema_summary:
            assert isinstance(entry, ColumnSummary)

    def test_column_order_preserved(self):
        df = pd.DataFrame({"z": [1], "a": [2], "m": [3]})
        frame = ar.from_pandas(df)
        names = [e.name for e in frame.schema_summary]
        assert names == ["z", "a", "m"]

    def test_names_match_frame_columns(self):
        df = pd.DataFrame({"id": [1, 2], "email": ["a@b.com", "c@d.com"]})
        frame = ar.from_pandas(df)
        assert [e.name for e in frame.schema_summary] == frame.columns

    def test_dtypes_match_frame_dtypes(self):
        df = pd.DataFrame({"id": [1, 2], "score": [1.5, 2.5], "label": ["a", "b"]})
        frame = ar.from_pandas(df)
        summary_dtypes = {e.name: e.dtype for e in frame.schema_summary}
        assert summary_dtypes == frame.dtypes

    def test_non_nullable_column(self):
        df = pd.DataFrame({"age": [10, 20, 30]})
        frame = ar.from_pandas(df)
        entry = frame.schema_summary[0]
        assert entry.nullable is False

    def test_nullable_column_from_null_values(self):
        df = pd.DataFrame({"score": [1.0, None, 3.0]})
        frame = ar.from_pandas(df)
        entry = frame.schema_summary[0]
        assert entry.nullable is True

    def test_nullable_string_column(self):
        df = pd.DataFrame({"name": ["Alice", None, "Charlie"]})
        frame = ar.from_pandas(df)
        entry = frame.schema_summary[0]
        assert entry.nullable is True

    def test_mixed_nullable_and_non_nullable(self):
        df = pd.DataFrame(
            {
                "id": [1, 2, 3],
                "name": ["a", None, "c"],
                "score": [1.0, 2.0, None],
            }
        )
        frame = ar.from_pandas(df)
        summary = {e.name: e.nullable for e in frame.schema_summary}
        assert summary["id"] is False
        assert summary["name"] is True
        assert summary["score"] is True

    def test_all_dtypes_covered(self):
        df = pd.DataFrame(
            {
                "i": [1, 2],
                "f": [1.1, 2.2],
                "s": ["a", "b"],
                "b": [True, False],
            }
        )
        frame = ar.from_pandas(df)
        dtype_map = {e.name: e.dtype for e in frame.schema_summary}
        assert dtype_map["i"] == "int64"
        assert dtype_map["f"] == "float64"
        assert dtype_map["s"] == "string"
        assert dtype_map["b"] == "bool"

    def test_csv_based_frame(self, sample_csv):
        frame = ar.read_csv(sample_csv)
        result = frame.schema_summary
        assert len(result) == len(frame.columns)
        for entry in result:
            assert entry.name in frame.columns
            assert entry.dtype in ("int64", "float64", "string", "bool", "null")

    def test_csv_with_nulls_marks_nullable(self, csv_with_nulls):
        frame = ar.read_csv(csv_with_nulls)
        assert any(e.nullable for e in frame.schema_summary)

    def test_does_not_trigger_pandas_roundtrip(self, monkeypatch):
        """schema_summary must read directly from the C++ frame."""
        df = pd.DataFrame({"x": [1, 2], "y": [3, 4]})
        frame = ar.from_pandas(df)

        from arnio import convert

        def fail_to_pandas(_frame, **_kwargs):
            raise AssertionError("schema_summary must not call to_pandas()")

        monkeypatch.setattr(convert, "to_pandas", fail_to_pandas)

        result = frame.schema_summary
        assert len(result) == 2

    def test_stable_across_calls(self):
        df = pd.DataFrame({"a": [1, None], "b": ["x", "y"]})
        frame = ar.from_pandas(df)
        assert frame.schema_summary == frame.schema_summary

    def test_schema_summary_returns_valid_column_summaries(self):
        df = pd.DataFrame({"id": [1, 2], "name": ["a", None]})
        frame = ar.from_pandas(df)
        for entry in frame.schema_summary:
            assert isinstance(entry.name, str)
            assert isinstance(entry.dtype, str)
            assert isinstance(entry.nullable, bool)


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestSchemaSummaryEdgeCases:
    def test_single_column_frame(self):
        df = pd.DataFrame({"only": [42]})
        frame = ar.from_pandas(df)
        result = frame.schema_summary
        assert len(result) == 1
        assert result[0].name == "only"
        assert result[0].dtype == "int64"
        assert result[0].nullable is False

    def test_empty_frame_no_rows(self):
        df = pd.DataFrame(columns=["name", "age"])
        frame = ar.from_pandas(df)
        result = frame.schema_summary
        assert [e.name for e in result] == ["name", "age"]
        for entry in result:
            assert entry.nullable is False

    def test_single_row_no_nulls(self):
        df = pd.DataFrame({"x": [1], "y": ["hello"]})
        frame = ar.from_pandas(df)
        assert all(not e.nullable for e in frame.schema_summary)

    def test_all_values_null_marks_nullable(self):
        df = pd.DataFrame({"x": [None, None, None]})
        frame = ar.from_pandas(df)
        assert frame.schema_summary[0].nullable is True

    def test_only_last_row_null(self):
        df = pd.DataFrame({"v": [1, 2, None]})
        frame = ar.from_pandas(df)
        assert frame.schema_summary[0].nullable is True

    def test_only_first_row_null(self):
        df = pd.DataFrame({"v": [None, 2, 3]})
        frame = ar.from_pandas(df)
        assert frame.schema_summary[0].nullable is True

    def test_wide_frame(self):
        cols = {f"col_{i}": list(range(5)) for i in range(50)}
        df = pd.DataFrame(cols)
        frame = ar.from_pandas(df)
        result = frame.schema_summary
        assert len(result) == 50
        assert [e.name for e in result] == list(cols.keys())

    def test_publicly_accessible_from_arnio_namespace(self):
        from arnio import ColumnSummary as CS  # noqa: F401

        df = pd.DataFrame({"a": [1]})
        frame = ar.from_pandas(df)
        for entry in frame.schema_summary:
            assert isinstance(entry, CS)

    def test_schema_to_dict_empty_dataframe(self):
        df = pd.DataFrame()
        frame = ar.from_pandas(df)
        res = ar.schema_export.schema_to_dict(frame)
        assert res == {"fields": {}}

    def test_schema_to_yaml_empty_dataframe(self):
        df = pd.DataFrame()
        frame = ar.from_pandas(df)
        res = ar.schema_export.schema_to_yaml(frame)
        assert res == "fields: {}\n"

    def test_schema_to_dict_with_column_summary_list(self):
        df = pd.DataFrame({"age": [20]})
        frame = ar.from_pandas(df)
        res = ar.schema_export.schema_to_dict(frame.schema_summary)
        assert res == {"fields": {"age": {"type": "INT64", "nullable": False}}}


# ---------------------------------------------------------------------------
# ValidationResult.summary()
# ---------------------------------------------------------------------------


class TestValidationResultSummary:
    """Tests for arnio.schema.ValidationResult.summary()."""

    # ------------------------------------------------------------------
    # Return type and top-level keys
    # ------------------------------------------------------------------

    def test_summary_returns_dict(self):
        result = ar.ValidationResult(row_count=5, issue_count=0, issues=[], bad_rows=[])
        assert isinstance(result.summary(), dict)

    def test_summary_has_expected_keys(self):
        result = ar.ValidationResult(row_count=5, issue_count=0, issues=[], bad_rows=[])
        summary = result.summary()
        assert "passed" in summary
        assert "issue_count" in summary
        assert "bad_row_count" in summary
        assert "issues_by_rule" in summary
        assert "severity_counts" in summary
        assert "issues_by_column" in summary
        assert "issues_by_column_and_rule" in summary

    # ------------------------------------------------------------------
    # Basic schema — simple fields, no failures
    # ------------------------------------------------------------------

    def test_summary_passes_for_valid_basic_schema(self):
        df = pd.DataFrame({"id": [1, 2], "name": ["Alice", "Bob"]})
        frame = ar.from_pandas(df)
        schema = ar.Schema(
            {"id": ar.Int64(nullable=False), "name": ar.String(nullable=False)}
        )
        result = ar.validate(frame, schema)
        summary = result.summary()
        assert summary["passed"] is True
        assert summary["issue_count"] == 0
        assert summary["bad_row_count"] == 0
        assert summary["issues_by_rule"] == {}
        assert summary["issues_by_column"] == {}
        assert summary["issues_by_column_and_rule"] == {}

    # ------------------------------------------------------------------
    # Empty schema — no fields in schema, no issues expected
    # ------------------------------------------------------------------

    def test_summary_empty_schema_no_issues(self):
        df = pd.DataFrame({"x": [1, 2, 3]})
        frame = ar.from_pandas(df)
        schema = ar.Schema({})
        result = ar.validate(frame, schema)
        summary = result.summary()
        assert summary["passed"] is True
        assert summary["issue_count"] == 0
        assert summary["issues_by_rule"] == {}

    def test_summary_empty_result_all_empty_dicts(self):
        result = ar.ValidationResult(row_count=0, issue_count=0, issues=[], bad_rows=[])
        summary = result.summary()
        assert summary["issues_by_rule"] == {}
        assert summary["issues_by_column"] == {}
        assert summary["issues_by_column_and_rule"] == {}
        assert summary["severity_counts"] == {}

    # ------------------------------------------------------------------
    # Mixed field types — numeric, string, bool
    # ------------------------------------------------------------------

    def test_summary_mixed_field_types_no_violations(self):
        df = pd.DataFrame(
            {
                "age": [25, 30, 35],
                "score": [9.5, 8.0, 7.5],
                "name": ["Alice", "Bob", "Charlie"],
                "active": [True, False, True],
            }
        )
        frame = ar.from_pandas(df)
        schema = ar.Schema(
            {
                "age": ar.Int64(nullable=False, min=0, max=120),
                "score": ar.Float64(nullable=False, min=0.0, max=10.0),
                "name": ar.String(nullable=False),
                "active": ar.Bool(nullable=False),
            }
        )
        result = ar.validate(frame, schema)
        summary = result.summary()
        assert summary["passed"] is True
        assert summary["issue_count"] == 0

    def test_summary_mixed_field_types_with_violations(self):
        df = pd.DataFrame(
            {
                "age": [25, -5],  # -5 violates min=0
                "score": [9.5, 11.0],  # 11.0 violates max=10.0
                "name": ["Alice", None],  # None violates nullable=False
            }
        )
        frame = ar.from_pandas(df)
        schema = ar.Schema(
            {
                "age": ar.Int64(nullable=False, min=0),
                "score": ar.Float64(nullable=False, max=10.0),
                "name": ar.String(nullable=False),
            }
        )
        result = ar.validate(frame, schema)
        summary = result.summary()
        assert summary["passed"] is False
        assert summary["issue_count"] > 0
        assert summary["bad_row_count"] > 0
        assert "issues_by_column" in summary
        assert (
            "age" in summary["issues_by_column"]
            or "score" in summary["issues_by_column"]
        )

    # ------------------------------------------------------------------
    # Semantic validators — Email and URL
    # ------------------------------------------------------------------

    def test_summary_email_validator_violation_appears_in_issues_by_column(self):
        df = pd.DataFrame(
            {"email": ["alice@example.com", "not-an-email", "bob@test.com"]}
        )
        frame = ar.from_pandas(df)
        schema = ar.Schema({"email": ar.Email(nullable=False)})
        result = ar.validate(frame, schema)
        summary = result.summary()
        assert summary["passed"] is False
        assert "email" in summary["issues_by_column"]
        assert summary["issues_by_column"]["email"] >= 1

    def test_summary_email_validator_all_valid_no_issues(self):
        df = pd.DataFrame({"email": ["alice@example.com", "bob@test.com"]})
        frame = ar.from_pandas(df)
        schema = ar.Schema({"email": ar.Email(nullable=False)})
        result = ar.validate(frame, schema)
        summary = result.summary()
        assert summary["passed"] is True
        assert summary["issue_count"] == 0
        assert "email" not in summary["issues_by_column"]

    def test_summary_url_validator_violation_appears_in_issues_by_rule(self):
        df = pd.DataFrame({"site": ["https://example.com", "not-a-url"]})
        frame = ar.from_pandas(df)
        schema = ar.Schema({"site": ar.URL(nullable=False)})
        result = ar.validate(frame, schema)
        summary = result.summary()
        assert summary["passed"] is False
        assert "site" in summary["issues_by_column"]
        # The rule key for URL validation should be present in issues_by_rule
        assert len(summary["issues_by_rule"]) > 0

    def test_summary_semantic_validator_rule_recorded_in_issues_by_rule(self):
        df = pd.DataFrame({"email": ["bad-email"]})
        frame = ar.from_pandas(df)
        schema = ar.Schema({"email": ar.Email(nullable=False)})
        result = ar.validate(frame, schema)
        summary = result.summary()
        # The rule name for email issues should be in issues_by_rule
        assert any("email" in rule for rule in summary["issues_by_rule"])

    # ------------------------------------------------------------------
    # Custom validators
    # ------------------------------------------------------------------

    def test_summary_custom_validator_issues_appear_correctly(self):
        from arnio import schema as _schema

        original = dict(_schema._CUSTOM_VALIDATORS)
        try:
            ar.register_validator(
                "positive_score", lambda v: isinstance(v, (int, float)) and v > 0
            )
            df = pd.DataFrame({"score": [10, -1, 5, -3]})
            frame = ar.from_pandas(df)
            schema = ar.Schema({"score": ar.Custom("positive_score", nullable=False)})
            result = ar.validate(frame, schema)
            summary = result.summary()
            assert summary["passed"] is False
            assert summary["issues_by_column"].get("score", 0) == 2
            assert "custom" in summary["issues_by_rule"]
            assert summary["issues_by_column_and_rule"]["score"]["custom"] == 2
        finally:
            _schema._CUSTOM_VALIDATORS.clear()
            _schema._CUSTOM_VALIDATORS.update(original)

    def test_summary_custom_validator_all_pass(self):
        from arnio import schema as _schema

        original = dict(_schema._CUSTOM_VALIDATORS)
        try:
            ar.register_validator("is_positive_v2", lambda v: v > 0)
            df = pd.DataFrame({"x": [1, 2, 3]})
            frame = ar.from_pandas(df)
            schema = ar.Schema({"x": ar.Custom("is_positive_v2", nullable=False)})
            result = ar.validate(frame, schema)
            summary = result.summary()
            assert summary["passed"] is True
            assert summary["issue_count"] == 0
            assert summary["issues_by_column"] == {}
        finally:
            _schema._CUSTOM_VALIDATORS.clear()
            _schema._CUSTOM_VALIDATORS.update(original)

    # ------------------------------------------------------------------
    # Severity counts
    # ------------------------------------------------------------------

    def test_summary_severity_counts_errors_only(self):
        result = ar.ValidationResult(
            row_count=3,
            issue_count=2,
            issues=[
                ar.ValidationIssue(
                    column="age", rule="min", message="too small", row_index=1
                ),
                ar.ValidationIssue(
                    column="age", rule="min", message="too small", row_index=2
                ),
            ],
            bad_rows=[1, 2],
        )
        summary = result.summary()
        assert summary["severity_counts"] == {"error": 2}

    def test_summary_severity_counts_warnings_only(self):
        result = ar.ValidationResult(
            row_count=2,
            issue_count=1,
            issues=[
                ar.ValidationIssue(
                    column="age",
                    rule="min",
                    message="low",
                    row_index=1,
                    severity="warning",
                ),
            ],
            bad_rows=[],
        )
        summary = result.summary()
        assert summary["severity_counts"] == {"warning": 1}
        # Warnings alone should not fail validation
        assert summary["passed"] is True

    def test_summary_severity_counts_mixed_error_and_warning(self):
        result = ar.ValidationResult(
            row_count=4,
            issue_count=3,
            issues=[
                ar.ValidationIssue(
                    column="age",
                    rule="min",
                    message="too small",
                    row_index=1,
                    severity="error",
                ),
                ar.ValidationIssue(
                    column="age",
                    rule="max",
                    message="too large",
                    row_index=2,
                    severity="error",
                ),
                ar.ValidationIssue(
                    column="score",
                    rule="min",
                    message="low score",
                    row_index=3,
                    severity="warning",
                ),
            ],
            bad_rows=[1, 2],
        )
        summary = result.summary()
        assert summary["severity_counts"]["error"] == 2
        assert summary["severity_counts"]["warning"] == 1

    # ------------------------------------------------------------------
    # issues_by_column_and_rule grouping
    # ------------------------------------------------------------------

    def test_summary_issues_by_column_and_rule_grouped_correctly(self):
        result = ar.ValidationResult(
            row_count=5,
            issue_count=4,
            issues=[
                ar.ValidationIssue(
                    column="age", rule="min", message="too small", row_index=1
                ),
                ar.ValidationIssue(
                    column="age", rule="min", message="too small", row_index=2
                ),
                ar.ValidationIssue(
                    column="age", rule="max", message="too large", row_index=3
                ),
                ar.ValidationIssue(
                    column="email", rule="email", message="bad email", row_index=4
                ),
            ],
            bad_rows=[1, 2, 3, 4],
        )
        summary = result.summary()
        assert summary["issues_by_column_and_rule"]["age"]["min"] == 2
        assert summary["issues_by_column_and_rule"]["age"]["max"] == 1
        assert summary["issues_by_column_and_rule"]["email"]["email"] == 1

    def test_summary_column_none_not_included_in_issues_by_column(self):
        result = ar.ValidationResult(
            row_count=2,
            issue_count=2,
            issues=[
                ar.ValidationIssue(
                    column=None, rule="required_column", message="missing col"
                ),
                ar.ValidationIssue(
                    column="email", rule="email", message="bad email", row_index=1
                ),
            ],
            bad_rows=[1],
        )
        summary = result.summary()
        # column=None rows should not appear as a column key
        assert None not in summary["issues_by_column"]
        # Non-None column should appear
        assert "email" in summary["issues_by_column"]
        # The rule itself is still counted in issues_by_rule
        assert "required_column" in summary["issues_by_rule"]

    # ------------------------------------------------------------------
    # Large schema
    # ------------------------------------------------------------------

    def test_summary_large_schema_scales_correctly(self):
        """summary() should handle 50+ columns and 500+ issues without error."""
        # Build a frame with 50 int columns and a schema that rejects negative values
        num_cols = 50
        data = {f"col_{i}": [-1] * 10 for i in range(num_cols)}
        df = pd.DataFrame(data)
        frame = ar.from_pandas(df)
        schema = ar.Schema({f"col_{i}": ar.Int64(min=0) for i in range(num_cols)})
        result = ar.validate(frame, schema)
        summary = result.summary()
        assert summary["passed"] is False
        assert summary["issue_count"] == num_cols * 10
        assert len(summary["issues_by_column"]) == num_cols
        for i in range(num_cols):
            assert summary["issues_by_column"][f"col_{i}"] == 10

    # ------------------------------------------------------------------
    # passed flag logic
    # ------------------------------------------------------------------

    def test_summary_passed_is_false_when_any_error_issue(self):
        result = ar.ValidationResult(
            row_count=1,
            issue_count=1,
            issues=[
                ar.ValidationIssue(column="x", rule="min", message="err", row_index=1)
            ],
            bad_rows=[1],
        )
        summary = result.summary()
        assert summary["passed"] is False

    def test_summary_passed_is_true_for_zero_issues(self):
        result = ar.ValidationResult(
            row_count=100, issue_count=0, issues=[], bad_rows=[]
        )
        summary = result.summary()
        assert summary["passed"] is True

    def test_summary_passed_is_true_when_only_warning_issues(self):
        result = ar.ValidationResult(
            row_count=2,
            issue_count=1,
            issues=[
                ar.ValidationIssue(
                    column="age",
                    rule="min",
                    message="low",
                    row_index=1,
                    severity="warning",
                )
            ],
            bad_rows=[],
        )
        summary = result.summary()
        assert summary["passed"] is True

    # ------------------------------------------------------------------
    # bad_row_count
    # ------------------------------------------------------------------

    def test_summary_bad_row_count_matches_bad_rows(self):
        result = ar.ValidationResult(
            row_count=10,
            issue_count=3,
            issues=[
                ar.ValidationIssue(
                    column="age", rule="min", message="err", row_index=1
                ),
                ar.ValidationIssue(
                    column="age", rule="min", message="err", row_index=2
                ),
                ar.ValidationIssue(
                    column="age", rule="min", message="err", row_index=3
                ),
            ],
            bad_rows=[1, 2, 3],
        )
        summary = result.summary()
        assert summary["bad_row_count"] == 3

    # ------------------------------------------------------------------
    # Stable across repeated calls
    # ------------------------------------------------------------------

    def test_summary_is_stable_across_repeated_calls(self):
        result = ar.ValidationResult(
            row_count=2,
            issue_count=1,
            issues=[
                ar.ValidationIssue(column="age", rule="min", message="err", row_index=1)
            ],
            bad_rows=[1],
        )
        assert result.summary() == result.summary()


# ---------------------------------------------------------------------------
# SchemaDiff.summary()
# ---------------------------------------------------------------------------


class TestSchemaDiffSummary:
    """Tests for arnio.schema.SchemaDiff.summary()."""

    # ------------------------------------------------------------------
    # Return type and top-level keys
    # ------------------------------------------------------------------

    def test_schema_diff_summary_returns_dict(self):
        schema_a = ar.Schema({"id": ar.Int64()})
        schema_b = ar.Schema({"id": ar.Int64()})
        diff = ar.diff_schema(schema_a, schema_b)
        assert isinstance(diff.summary(), dict)

    def test_schema_diff_summary_has_expected_keys(self):
        schema_a = ar.Schema({"id": ar.Int64()})
        schema_b = ar.Schema({"id": ar.Int64()})
        diff = ar.diff_schema(schema_a, schema_b)
        summary = diff.summary()
        assert "changed" in summary
        assert "difference_count" in summary
        assert "differences_by_change" in summary
        assert "differences_by_column" in summary

    # ------------------------------------------------------------------
    # No differences
    # ------------------------------------------------------------------

    def test_schema_diff_summary_unchanged_schemas(self):
        schema_a = ar.Schema({"id": ar.Int64(), "name": ar.String()})
        schema_b = ar.Schema({"id": ar.Int64(), "name": ar.String()})
        diff = ar.diff_schema(schema_a, schema_b)
        summary = diff.summary()
        assert summary["changed"] is False
        assert summary["difference_count"] == 0
        assert summary["differences_by_change"] == {}
        assert summary["differences_by_column"] == {}

    def test_schema_diff_summary_empty_schemas(self):
        diff = ar.diff_schema(ar.Schema({}), ar.Schema({}))
        summary = diff.summary()
        assert summary["changed"] is False
        assert summary["difference_count"] == 0

    # ------------------------------------------------------------------
    # Missing columns
    # ------------------------------------------------------------------

    def test_schema_diff_summary_missing_column(self):
        schema_a = ar.Schema({"id": ar.Int64(), "email": ar.Email()})
        schema_b = ar.Schema({"id": ar.Int64()})
        diff = ar.diff_schema(schema_a, schema_b)
        summary = diff.summary()
        assert summary["changed"] is True
        assert summary["differences_by_change"].get("missing_column", 0) >= 1
        assert "email" in summary["differences_by_column"]

    # ------------------------------------------------------------------
    # Extra columns
    # ------------------------------------------------------------------

    def test_schema_diff_summary_extra_column(self):
        schema_a = ar.Schema({"id": ar.Int64()})
        schema_b = ar.Schema({"id": ar.Int64(), "extra": ar.String()})
        diff = ar.diff_schema(schema_a, schema_b)
        summary = diff.summary()
        assert summary["changed"] is True
        assert summary["differences_by_change"].get("extra_column", 0) >= 1
        assert "extra" in summary["differences_by_column"]

    # ------------------------------------------------------------------
    # Multiple change kinds
    # ------------------------------------------------------------------

    def test_schema_diff_summary_multiple_change_kinds_counted_separately(self):
        schema_a = ar.Schema(
            {"id": ar.Int64(), "name": ar.String(), "score": ar.Float64()}
        )
        schema_b = ar.Schema({"id": ar.Int64(), "title": ar.String()})
        diff = ar.diff_schema(schema_a, schema_b)
        summary = diff.summary()
        assert summary["changed"] is True
        # "name" and "score" are missing; "title" is extra
        assert "missing_column" in summary["differences_by_change"]
        assert "extra_column" in summary["differences_by_change"]
        assert summary["differences_by_change"]["missing_column"] == 2
        assert summary["differences_by_change"]["extra_column"] == 1
        assert summary["difference_count"] == 3

    # ------------------------------------------------------------------
    # Stable across repeated calls
    # ------------------------------------------------------------------

    def test_schema_diff_summary_is_stable_across_calls(self):
        schema_a = ar.Schema({"id": ar.Int64(), "name": ar.String()})
        schema_b = ar.Schema({"id": ar.Int64()})
        diff = ar.diff_schema(schema_a, schema_b)
        assert diff.summary() == diff.summary()
