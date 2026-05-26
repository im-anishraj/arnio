"""Tests for schema validation."""

import io
import json
import warnings

import pandas as pd
import pytest

import arnio as ar


def test_dtype_validation_reports_safe_int_conversion_for_numeric_strings():
    frame = ar.from_pandas(
        pd.DataFrame(
            {
                "age": pd.Series(
                    ["1", "2", "3"],
                    dtype="string",
                )
            }
        )
    )

    schema = ar.Schema({"age": ar.Int64()})

    result = ar.validate(frame, schema)

    assert not result.passed
    assert "safely convertible to 'int64'" in result.issues[0].message


def test_dtype_validation_reports_safe_float_conversion_for_numeric_strings():
    frame = ar.from_pandas(
        pd.DataFrame(
            {
                "score": pd.Series(
                    ["1.5", "2.0", "3.25"],
                    dtype="string",
                )
            }
        )
    )

    schema = ar.Schema({"score": ar.Float64()})

    result = ar.validate(frame, schema)

    assert not result.passed
    assert "safely convertible to 'float64'" in result.issues[0].message


def test_schema_validation_row_indexed_issues_respect_cap():
    frame = ar.from_pandas(
        pd.DataFrame(
            {
                "name": [None, None, "ok"],
            }
        )
    )

    schema = ar.Schema(
        {
            "name": ar.Field(nullable=False),
        }
    )

    result = ar.validate(frame, schema, max_errors=1)

    assert result.issue_count == 1
    assert result.bad_rows == [1]


def test_dtype_validation_does_not_report_safe_conversion_for_invalid_numeric_strings():
    frame = ar.from_pandas(
        pd.DataFrame(
            {
                "age": pd.Series(
                    ["1", "abc", "3"],
                    dtype="string",
                )
            }
        )
    )

    schema = ar.Schema({"age": ar.Int64()})

    result = ar.validate(frame, schema)

    assert not result.passed
    assert "safely convertible" not in result.issues[0].message


def test_validate_rejects_chunked_iterators(tmp_path):
    path = tmp_path / "data.csv"
    path.write_text("email\n" "a@example.com\n")

    chunks = ar.read_csv_chunked(path, chunksize=1)

    with pytest.raises(
        TypeError, match="Chunked validation is not currently supported"
    ):
        ar.validate(chunks, {"email": ar.Email(nullable=False)})


def test_dtype_validation_does_not_report_safe_conversion_for_identifier_like_columns():
    frame = ar.from_pandas(
        pd.DataFrame(
            {
                "user_id": pd.Series(
                    ["001", "002", "003"],
                    dtype="string",
                )
            }
        )
    )

    schema = ar.Schema({"user_id": ar.Int64()})

    result = ar.validate(frame, schema)

    assert not result.passed
    assert "safely convertible" not in result.issues[0].message


def test_dtype_validation_does_not_report_safe_conversion_for_empty_strings():
    frame = ar.from_pandas(
        pd.DataFrame(
            {
                "age": pd.Series(
                    [None, None],
                    dtype="string",
                )
            }
        )
    )

    schema = ar.Schema({"age": ar.Int64()})

    result = ar.validate(frame, schema)

    assert not result.passed
    assert "safely convertible" not in result.issues[0].message


def test_dtype_validation_preserves_warning_severity_for_numeric_strings():
    frame = ar.from_pandas(
        pd.DataFrame(
            {
                "age": pd.Series(
                    ["1", "2", "3"],
                    dtype="string",
                )
            }
        )
    )

    schema = ar.Schema(
        {
            "age": ar.Int64(severity="warning"),
        }
    )

    result = ar.validate(frame, schema)

    assert result.issues[0].severity == "warning"


def test_dtype_validation_does_not_report_safe_conversion_above_int64_max():
    frame = ar.from_pandas(
        pd.DataFrame(
            {
                "value": pd.Series(
                    ["9223372036854775808"],
                    dtype="string",
                )
            }
        )
    )

    schema = ar.Schema({"value": ar.Int64()})

    result = ar.validate(frame, schema)

    assert not result.passed
    assert "safely convertible" not in result.issues[0].message


def test_dtype_validation_does_not_report_safe_conversion_below_int64_min():
    frame = ar.from_pandas(
        pd.DataFrame(
            {
                "value": pd.Series(
                    ["-9223372036854775809"],
                    dtype="string",
                )
            }
        )
    )

    schema = ar.Schema({"value": ar.Int64()})

    result = ar.validate(frame, schema)

    assert not result.passed
    assert "safely convertible" not in result.issues[0].message


def test_schema_validation_passes_for_valid_frame(sample_csv):
    frame = ar.read_csv(sample_csv)
    schema = ar.Schema(
        {
            "name": ar.String(nullable=False, min_length=3),
            "age": ar.Int64(nullable=False, min=0, max=120),
            "email": ar.Email(nullable=False, unique=True),
            "active": ar.Bool(nullable=False),
        },
        strict=True,
    )

    result = ar.validate(frame, schema)

    assert result.passed
    assert result.issue_count == 0
    assert result.bad_rows == []


def test_schema_validation_stops_after_max_errors(tmp_path):
    path = tmp_path / "bad.csv"

    path.write_text(
        "name,age,email\n"
        ",150,invalid-email\n"
        ",200,another-invalid\n"
        ",300,bad-email\n"
    )

    frame = ar.read_csv(path)
    schema = ar.Schema(
        {
            "name": ar.String(nullable=False),
            "age": ar.Int64(min=0, max=120),
            "email": ar.Email(nullable=False),
        }
    )

    result = ar.validate(frame, schema, max_errors=2)

    assert result.issue_count == 2
    assert len(result.issues) == 2


def test_schema_rejects_invalid_field_values_string(sample_csv):
    frame = ar.read_csv(sample_csv)
    with pytest.raises(TypeError, match="must be a Field instance"):
        ar.validate(frame, {"id": "int64"})


def test_schema_rejects_invalid_field_values_dict(sample_csv):
    frame = ar.read_csv(sample_csv)
    with pytest.raises(TypeError, match="must be a Field instance"):
        ar.validate(frame, {"id": {"type": "int64"}})


def test_schema_rejects_invalid_field_values_none(sample_csv):
    frame = ar.read_csv(sample_csv)
    with pytest.raises(TypeError, match="must be a Field instance"):
        ar.validate(frame, {"id": None})


def test_schema_validation_collects_row_level_issues(tmp_path):
    path = tmp_path / "bad.csv"
    path.write_text(
        "name,age,email,status\n"
        "Alice,30,alice@test.com,active\n"
        ",150,not-an-email,blocked\n"
        "Bob,-1,bob@test.com,unknown\n"
    )
    frame = ar.read_csv(path)
    schema = ar.Schema(
        {
            "name": ar.String(nullable=False),
            "age": ar.Int64(nullable=False, min=0, max=120),
            "email": ar.Email(nullable=False),
            "status": ar.String(allowed={"active", "blocked"}),
        }
    )

    result = schema.validate(frame)
    rules = {issue.rule for issue in result.issues}

    assert not result.passed
    assert result.bad_rows == [2, 3]
    assert {"nullable", "max", "min", "email", "allowed"} <= rules
    assert result.summary()["issues_by_column"]["age"] == 2


def test_schema_reports_missing_and_unexpected_columns(sample_csv):
    frame = ar.read_csv(sample_csv)
    schema = ar.Schema({"missing": ar.String()}, strict=True)

    result = ar.validate(frame, schema)
    rules = [issue.rule for issue in result.issues]

    assert "required_column" in rules
    assert "unexpected_column" in rules


def test_validation_result_to_pandas_empty_has_stable_columns():
    result = ar.ValidationResult(
        row_count=3,
        issue_count=0,
        issues=[],
        bad_rows=[],
    )

    df = result.to_pandas()

    assert df.empty
    assert list(df.columns) == [
        "column",
        "rule",
        "message",
        "row_index",
        "value",
        "severity",
    ]


def test_schema_validation_bool_max_errors_rejected():
    frame = ar.from_pandas(pd.DataFrame({"a": [1]}))
    schema = ar.Schema({"a": ar.Field()})

    with pytest.raises(TypeError, match="max_errors"):
        ar.validate(frame, schema, max_errors=True)


def test_schema_validation_float_max_errors_rejected():
    frame = ar.from_pandas(pd.DataFrame({"a": [1]}))
    schema = ar.Schema({"a": ar.Field()})

    with pytest.raises(TypeError, match="max_errors"):
        ar.validate(frame, schema, max_errors=1.5)


def test_schema_validation_custom_rule_respects_max_errors():
    def bad_rule(df):
        return [
            ar.ValidationIssue(
                column="a",
                rule="custom",
                message="error 1",
                row_index=1,
            ),
            ar.ValidationIssue(
                column="a",
                rule="custom",
                message="error 2",
                row_index=2,
            ),
        ]

    frame = ar.from_pandas(pd.DataFrame({"a": [1, 2]}))

    schema = ar.Schema(
        {"a": ar.Field()},
        rules=[bad_rule],
    )

    result = ar.validate(frame, schema, max_errors=1)

    assert result.issue_count == 1
    assert result.bad_rows == [1]


def test_validation_result_summary_counts_repeated_issues_in_one_column():
    result = ar.ValidationResult(
        row_count=3,
        issue_count=3,
        issues=[
            ar.ValidationIssue(
                column="age", rule="min", message="too small", row_index=0
            ),
            ar.ValidationIssue(
                column="age", rule="min", message="too small", row_index=1
            ),
            ar.ValidationIssue(
                column="age", rule="min", message="too small", row_index=2
            ),
        ],
        bad_rows=[0, 1, 2],
    )

    summary = result.summary()

    assert summary["issues_by_rule"] == {"min": 3}
    assert summary["issues_by_column"] == {"age": 3}
    assert summary["issues_by_column_and_rule"] == {"age": {"min": 3}}


def test_schema_validation_max_errors_zero(tmp_path):
    path = tmp_path / "data.csv"

    path.write_text("name,age\njohn,\n")

    frame = ar.read_csv(path)

    schema = ar.Schema(
        {
            "name": ar.String(),
            "age": ar.Int64(nullable=False),
        }
    )
    result = ar.validate(frame, schema, max_errors=0)

    assert result.issue_count == 0
    assert result.issues == []


def test_schema_validation_negative_max_errors(tmp_path):
    path = tmp_path / "data.csv"

    path.write_text("name\njohn\n")

    frame = ar.read_csv(path)

    schema = ar.Schema(
        {
            "name": ar.String(),
        }
    )

    with pytest.raises(ValueError):
        ar.validate(frame, schema, max_errors=-1)


def test_schema_validation_unique_missing_columns_respects_max_errors():
    frame = ar.read_csv(io.StringIO("x\n1\n"))

    schema = ar.Schema(
        {},
        unique=["a", "b"],
    )

    result = ar.validate(frame, schema, max_errors=1)

    assert result.issue_count == 1


def test_schema_validation_rule_keyerror_respects_max_errors():
    def bad_rule(df):
        _ = df["missing_column"]
        return []

    frame = ar.read_csv(io.StringIO("a\n1\n"))

    schema = ar.Schema(
        {
            "a": ar.String(),
        },
        rules=[bad_rule],
    )

    result = ar.validate(frame, schema, max_errors=1)

    assert result.issue_count == 1


def test_schema_validation_strict_max_errors_cap(tmp_path):
    path = tmp_path / "data.csv"

    path.write_text("name,extra1,extra2\njohn,a,b\n")

    frame = ar.read_csv(path)

    schema = ar.Schema(
        {
            "name": ar.String(),
        },
        strict=True,
    )

    result = ar.validate(frame, schema, max_errors=1)

    assert result.issue_count == 1
    assert len(result.issues) == 1


def test_schema_validation_unique_max_errors_cap(tmp_path):
    path = tmp_path / "data.csv"

    path.write_text("id\n1\n1\n1\n")

    frame = ar.read_csv(path)

    schema = ar.Schema(
        {
            "id": ar.Int64(),
        },
        unique=["id"],
    )

    result = ar.validate(frame, schema, max_errors=1)

    assert result.issue_count == 1
    assert len(result.issues) == 1


def test_validation_result_summary_counts_issues_across_multiple_columns():
    result = ar.ValidationResult(
        row_count=3,
        issue_count=4,
        issues=[
            ar.ValidationIssue(
                column="age", rule="min", message="too small", row_index=0
            ),
            ar.ValidationIssue(
                column="status", rule="allowed", message="bad status", row_index=1
            ),
            ar.ValidationIssue(
                column="email", rule="email", message="bad email", row_index=1
            ),
            ar.ValidationIssue(
                column=None, rule="required_column", message="missing column"
            ),
        ],
        bad_rows=[0, 1],
    )

    summary = result.summary()

    assert summary["issues_by_rule"] == {
        "min": 1,
        "allowed": 1,
        "email": 1,
        "required_column": 1,
    }
    assert summary["issues_by_column"] == {"age": 1, "status": 1, "email": 1}
    assert summary["issues_by_column_and_rule"] == {
        "age": {"min": 1},
        "status": {"allowed": 1},
        "email": {"email": 1},
    }


def test_validation_result_summary_counts_grouped_rules_under_one_column():
    result = ar.ValidationResult(
        row_count=2,
        issue_count=3,
        issues=[
            ar.ValidationIssue(
                column="age", rule="min", message="too small", row_index=0
            ),
            ar.ValidationIssue(
                column="age", rule="max", message="too large", row_index=1
            ),
            ar.ValidationIssue(
                column="age", rule="numeric", message="not numeric", row_index=1
            ),
        ],
        bad_rows=[0, 1],
    )

    summary = result.summary()

    assert summary["issues_by_rule"] == {"min": 1, "max": 1, "numeric": 1}
    assert summary["issues_by_column"] == {"age": 3}
    assert summary["issues_by_column_and_rule"] == {
        "age": {"min": 1, "max": 1, "numeric": 1}
    }


def test_validation_result_summary_counts_no_issue_result():
    result = ar.ValidationResult(row_count=3, issue_count=0, issues=[], bad_rows=[])

    summary = result.summary()

    assert summary["passed"] is True
    assert summary["issue_count"] == 0
    assert summary["bad_row_count"] == 0
    assert summary["issues_by_rule"] == {}
    assert summary["issues_by_column"] == {}
    assert summary["issues_by_column_and_rule"] == {}


def test_validation_result_to_pandas(sample_csv):
    result = ar.validate(
        ar.read_csv(sample_csv),
        {"age": ar.Int64(min=31)},
    )
    df = result.to_pandas()
    assert list(df["rule"]) == ["min", "min"]
    assert list(df["row_index"]) == [1, 2]


def test_validation_result_to_markdown_for_success(sample_csv):
    result = ar.validate(ar.read_csv(sample_csv), {"age": ar.Int64()})

    markdown = result.to_markdown()

    assert "## Validation Report" in markdown
    assert "- Status: **passed**" in markdown
    assert "- Issues found: 0" in markdown
    assert "| Column | Rule | Row | Value | Message |" not in markdown


def test_warning_severity_does_not_fail_validation(tmp_path):
    path = tmp_path / "warnings.csv"
    path.write_text("age\n15\n")

    schema = {
        "age": ar.Field(
            dtype="int64",
            min=18,
            severity="warning",
        )
    }

    result = ar.validate(ar.read_csv(path), schema)

    assert result.passed
    assert result.issue_count == 1
    assert result.issues[0].severity == "warning"
    assert result.issues[0].rule == "min"


def test_warning_severity_does_not_fail_dtype_mismatch(tmp_path):
    path = tmp_path / "dtype_warning.csv"
    path.write_text("age\nhello\n")

    result = ar.validate(
        ar.read_csv(path),
        {"age": ar.Int64(severity="warning")},
    )

    assert result.passed
    assert result.issue_count == 1
    assert result.issues[0].rule == "dtype"
    assert result.issues[0].severity == "warning"


def test_validation_result_to_markdown_includes_issue_table(sample_csv):
    result = ar.validate(
        ar.read_csv(sample_csv),
        {"age": ar.Int64(min=31), "missing": ar.String()},
    )

    # Default: redact_values=False — raw values are shown
    markdown = result.to_markdown()

    assert "- Status: **failed**" in markdown
    assert "- Issues found: 3" in markdown
    assert "| Column | Rule | Severity | Row | Value | Message |" in markdown
    assert "| age | min | error | 1 |" in markdown
    assert (
        "| missing | required_column | error |  |  | Missing required column: missing |"
        in markdown
    )


def test_validation_result_to_markdown_limits_visible_issues(sample_csv):
    result = ar.validate(ar.read_csv(sample_csv), {"age": ar.Int64(min=31)})

    markdown = result.to_markdown(max_issues=1)

    assert "| age | min | error | 1 |" in markdown
    assert "| age | min | 2 |" not in markdown
    assert "_Showing 1 of 2 issues._" in markdown


def test_validation_result_to_markdown_escapes_table_cells():
    result = ar.ValidationResult(
        row_count=1,
        issue_count=1,
        issues=[
            ar.ValidationIssue(
                column="notes|raw",
                rule="pattern",
                row_index=0,
                value="left|right\nnext",
                message="Expected one|two\nlines",
            )
        ],
        bad_rows=[0],
    )

    # Column, value, and message cells are escaped (default: redact_values=False)
    markdown = result.to_markdown()
    assert "notes\\|raw" in markdown
    assert "left\\|right<br>next" in markdown
    assert "Expected one\\|two<br>lines" in markdown

    # Opt-in to redaction — value is replaced with [REDACTED]
    markdown_redacted = result.to_markdown(redact_values=True)
    assert "notes\\|raw" in markdown_redacted
    assert "[REDACTED]" in markdown_redacted
    assert "Expected one\\|two<br>lines" in markdown_redacted


def test_validation_result_to_markdown_rejects_negative_max_issues(sample_csv):
    result = ar.validate(ar.read_csv(sample_csv), {"age": ar.Int64(min=31)})

    try:
        result.to_markdown(max_issues=-1)
    except ValueError as exc:
        assert "max_issues" in str(exc)
    else:
        raise AssertionError("Expected max_issues validation to raise")


def test_validation_result_to_markdown_rejects_non_integer_max_issues(sample_csv):
    result = ar.validate(ar.read_csv(sample_csv), {"age": ar.Int64(min=31)})

    for invalid in ("1", 1.5, True):
        try:
            result.to_markdown(max_issues=invalid)  # type: ignore[arg-type]
        except TypeError as exc:
            assert "max_issues must be an integer or None" in str(exc)
        else:
            raise AssertionError(f"Expected max_issues={invalid!r} to raise")


def test_schema_construction_validates_rules():
    with pytest.raises(TypeError, match="Schema 'rules' must be a list of callables"):
        ar.Schema({"x": ar.Int64()}, rules="abc")

    with pytest.raises(TypeError, match="Schema 'rules' must be a list of callables"):
        ar.Schema({"x": ar.Int64()}, rules=123)

    with pytest.raises(TypeError, match="Schema 'rules' must be a list of callables"):
        ar.Schema({"x": ar.Int64()}, rules=object())

    with pytest.raises(TypeError, match="Schema 'rules' must be a list of callables"):
        ar.Schema({"x": ar.Int64()}, rules=[object()])

    def valid_rule(df):
        return []

    with pytest.raises(TypeError, match="Schema 'rules' must be a list of callables"):
        ar.Schema({"x": ar.Int64()}, rules=[valid_rule, 456])

    assert ar.Schema({"x": ar.Int64()}, rules=[valid_rule]).rules is not None
    assert ar.Schema({"x": ar.Int64()}, rules=(valid_rule,)).rules is not None
    assert ar.Schema({"x": ar.Int64()}, rules=None).rules is None


# ---------------------------------------------------------------------------
# Regression tests: redaction policy for ValidationResult.to_markdown
# ---------------------------------------------------------------------------


def test_validation_result_to_markdown_does_not_redact_by_default():
    """Value column must contain raw value when redact_values=False (default)."""
    result = ar.ValidationResult(
        row_count=1,
        issue_count=1,
        issues=[
            ar.ValidationIssue(
                column="email",
                rule="email",
                row_index=1,
                value="secret@internal.example.com",
                message="Invalid email",
            )
        ],
        bad_rows=[1],
    )

    markdown = result.to_markdown()  # default: redact_values=False

    assert "[REDACTED]" not in markdown
    assert "secret@internal.example.com" in markdown


def test_validation_result_to_markdown_redacts_when_opted_in():
    """Value column must contain [REDACTED] when redact_values=True."""
    result = ar.ValidationResult(
        row_count=1,
        issue_count=1,
        issues=[
            ar.ValidationIssue(
                column="email",
                rule="email",
                row_index=1,
                value="secret@internal.example.com",
                message="Invalid email",
            )
        ],
        bad_rows=[1],
    )

    markdown = result.to_markdown(redact_values=True)

    assert "[REDACTED]" in markdown
    assert "secret@internal.example.com" not in markdown


def test_validation_result_to_markdown_redacted_output_is_deterministic():
    """to_markdown() must return identical output on repeated calls."""
    result = ar.ValidationResult(
        row_count=2,
        issue_count=2,
        issues=[
            ar.ValidationIssue(
                column="age", rule="min", row_index=1, value=-5, message="below 0"
            ),
            ar.ValidationIssue(
                column="age", rule="max", row_index=2, value=999, message="above 120"
            ),
        ],
        bad_rows=[1, 2],
    )

    assert result.to_markdown() == result.to_markdown()
    assert result.to_markdown(redact_values=True) == result.to_markdown(
        redact_values=True
    )


def test_validation_result_to_markdown_none_value_redacted():
    """None/missing values are also replaced with [REDACTED] when redaction is enabled."""
    result = ar.ValidationResult(
        row_count=1,
        issue_count=1,
        issues=[
            ar.ValidationIssue(
                column="col",
                rule="nullable",
                row_index=1,
                value=None,
                message="Null not allowed",
            )
        ],
        bad_rows=[1],
    )

    markdown = result.to_markdown(redact_values=True)  # explicit redaction
    assert "[REDACTED]" in markdown

    markdown_raw = result.to_markdown()  # default redaction is False
    # None -> empty cell in raw mode
    assert "[REDACTED]" not in markdown_raw


def test_unique_constraint_detects_duplicates(tmp_path):
    path = tmp_path / "unique.csv"
    path.write_text("id,value\n1,100\n2,200\n1,300\n3,400\n")
    result = ar.validate(ar.read_csv(path), {"id": ar.Int64(unique=True)})
    assert not result.passed
    assert any(
        issue.rule == "unique" and issue.column == "id" for issue in result.issues
    )


def test_custom_pattern_validation(tmp_path):
    path = tmp_path / "codes.csv"
    path.write_text("code\nAA-123\nbad\n")
    result = ar.validate(
        ar.read_csv(path), {"code": ar.String(pattern=r"[A-Z]{2}-\d{3}")}
    )

    assert not result.passed
    assert result.issues[0].rule == "pattern"
    assert result.issues[0].row_index == 2


def test_row_index_is_one_based_for_first_row(tmp_path):
    path = tmp_path / "codes.csv"
    path.write_text("age\n-1\n30\n25\n")
    frame = ar.read_csv(path)
    result = ar.validate(frame, {"age": ar.Int64(min=0)})

    assert not result.passed
    assert len(result.issues) == 1
    assert result.issues[0].row_index == 1


def test_raise_for_errors_passes(sample_csv):
    frame = ar.read_csv(sample_csv)
    schema = ar.Schema({"name": ar.String(nullable=False)})

    result = ar.validate(frame, schema)

    assert result.passed
    assert result.raise_for_errors() is None


def test_raise_for_errors_single_issue(tmp_path):
    path = tmp_path / "single.csv"
    path.write_text("a,b\n1,2\n")

    frame = ar.read_csv(path)
    schema = ar.Schema({"c": ar.String()})

    result = ar.validate(frame, schema)

    with pytest.raises(ar.ArnioError) as exc:
        result.raise_for_errors()

    assert "Missing required column" in str(exc.value)


def test_raise_for_errors_multiple_issues(tmp_path):
    path = tmp_path / "ages.csv"
    path.write_text("age\n1\n2\n")

    frame = ar.read_csv(path)
    schema = ar.Schema({"age": ar.Int64(min=3)})

    result = ar.validate(frame, schema)

    assert result.issue_count == 2

    with pytest.raises(ar.ArnioError) as exc:
        result.raise_for_errors()

    msg = str(exc.value)
    assert "below 3" in msg
    assert "row 1" in msg and "row 2" in msg


def test_schema_bootstrap_from_report_infers_dtype_and_nullable(tmp_path):
    path = tmp_path / "quality.csv"
    path.write_text(
        "id,name,score,active\n"
        "1,Alice,9.5,true\n"
        "2,Bob,,false\n"
        "3,Carol,7.25,true\n"
    )
    report = ar.profile(ar.read_csv(path))

    schema = ar.Schema.bootstrap_from_report(report)

    assert schema.fields == {
        "id": ar.Field(dtype="int64", nullable=False),
        "name": ar.Field(dtype="string", nullable=False),
        "score": ar.Field(dtype="float64", nullable=True),
        "active": ar.Field(dtype="bool", nullable=False),
    }


def test_schema_bootstrap_from_report_validates_source_frame(tmp_path):
    path = tmp_path / "quality.csv"
    path.write_text("id,name\n1,Alice\n2,Bob\n")
    frame = ar.read_csv(path)
    report = ar.profile(frame)

    schema = ar.Schema.bootstrap_from_report(report)
    result = schema.validate(frame)

    assert result.passed
    assert result.issue_count == 0


def test_schema_bootstrap_from_report_rejects_non_report():
    with pytest.raises(TypeError, match="Expected DataQualityReport"):
        ar.Schema.bootstrap_from_report({"columns": {}})


def test_schema_bootstrap_from_report_rejects_empty_report():
    from arnio.quality import DataQualityReport

    report = DataQualityReport(
        row_count=0,
        column_count=0,
        memory_usage=0,
        duplicate_rows=0,
        duplicate_ratio=0.0,
        columns={},
    )

    with pytest.raises(ValueError, match="empty report"):
        ar.Schema.bootstrap_from_report(report)


def test_email_validation_rejects_invalid_validation_mode():
    with pytest.raises(ValueError):
        ar.Email(validation="banana")


def test_email_default_validation_mode_is_backward_compatible(tmp_path):
    path = tmp_path / "emails.csv"
    path.write_text("email\n" "simple@test.com\n")

    frame = ar.read_csv(path)

    result = ar.validate(
        frame,
        {"email": ar.Email(nullable=False)},
    )

    assert result.passed


def test_email_strict_validation_rejects_invalid_emails(tmp_path):
    path = tmp_path / "invalid_emails.csv"
    path.write_text("email\n" "bad@@test.com\n" "user@localhost\n" "user@.com\n")

    frame = ar.read_csv(path)

    result = ar.validate(
        frame,
        {
            "email": ar.Email(
                nullable=False,
                validation="strict",
            )
        },
    )

    assert not result.passed
    assert result.issue_count == 3
    assert all(issue.rule == "email:strict" for issue in result.issues)


def test_email_strict_validation_accepts_valid_emails(tmp_path):
    path = tmp_path / "valid_emails.csv"
    path.write_text(
        "email\n" "user@example.com\n" "first.last@test.co.uk\n" "hello+tag@gmail.com\n"
    )

    frame = ar.read_csv(path)

    result = ar.validate(
        frame,
        {
            "email": ar.Email(
                nullable=False,
                validation="strict",
            )
        },
    )

    assert result.passed


def test_phone_number_validation_passes():
    import pandas as pd

    schema = ar.Schema(
        {
            "phone": ar.PhoneNumber(),
        }
    )

    df = pd.DataFrame(
        {
            "phone": [
                "+1-555-123-4567",
                "+1 (555) 123-4567",
                "+91 9876543210",
                "5551234567",
            ]
        }
    )

    frame = ar.from_pandas(df)
    result = ar.validate(frame, schema)

    assert result.passed


def test_phone_number_validation_fails():
    import pandas as pd

    schema = ar.Schema(
        {
            "phone": ar.PhoneNumber(),
        }
    )

    df = pd.DataFrame(
        {
            "phone": [
                "abc123",
                "12",
                "++123456",
                "phone-number",
            ]
        }
    )

    frame = ar.from_pandas(df)
    result = ar.validate(frame, schema)

    assert not result.passed


def test_phone_number_nullable_true_accepts_nulls():
    import pandas as pd

    schema = ar.Schema(
        {
            "phone": ar.PhoneNumber(nullable=True),
        }
    )

    df = pd.DataFrame(
        {
            "phone": [
                "+1-555-123-4567",
                None,
                pd.NA,
            ]
        }
    )

    frame = ar.from_pandas(df)

    result = ar.validate(frame, schema)

    assert result.passed


def test_phone_number_nullable_false_rejects_nulls():
    import pandas as pd

    schema = ar.Schema(
        {
            "phone": ar.PhoneNumber(nullable=False),
        }
    )

    df = pd.DataFrame(
        {
            "phone": [
                "+1-555-123-4567",
                None,
            ]
        }
    )

    frame = ar.from_pandas(df)

    result = ar.validate(frame, schema)

    assert not result.passed

    assert any(issue.rule == "nullable" for issue in result.issues)


def test_phone_number_unique_constraint():
    import pandas as pd

    schema = ar.Schema(
        {
            "phone": ar.PhoneNumber(unique=True),
        }
    )

    df = pd.DataFrame(
        {
            "phone": [
                "555-123-4567",
                "555-123-4567",
            ]
        }
    )

    frame = ar.from_pandas(df)

    result = ar.validate(frame, schema)

    assert not result.passed

    assert any(issue.rule == "unique" for issue in result.issues)


def test_phone_number_formatted_and_invalid_edge_cases():
    import pandas as pd

    schema = ar.Schema(
        {
            "phone": ar.PhoneNumber(),
        }
    )

    df = pd.DataFrame(
        {
            "phone": [
                "+1 (555) 123-4567",
                "555-123-4567",
                "++1-555-123-4567",
                "123",
            ]
        }
    )

    frame = ar.from_pandas(df)

    result = ar.validate(frame, schema)

    assert not result.passed

    invalid_values = {issue.value for issue in result.issues}

    assert "++1-555-123-4567" in invalid_values
    assert "123" in invalid_values


def test_phone_number_mixed_object_column_behavior():
    import pandas as pd

    schema = ar.Schema(
        {
            "phone": ar.PhoneNumber(nullable=True),
        }
    )

    df = pd.DataFrame(
        {
            "phone": [
                "+1-555-123-4567",
                1234567890,
                True,
                None,
                "invalid",
            ]
        },
        dtype=object,
    )

    frame = ar.from_pandas(df)

    result = ar.validate(frame, schema)

    assert not result.passed

    invalid_values = {str(issue.value) for issue in result.issues}

    assert "True" in invalid_values
    assert "invalid" in invalid_values


def test_phone_number_warning_severity_does_not_fail_validation():
    import pandas as pd

    schema = ar.Schema(
        {
            "phone": ar.PhoneNumber(severity="warning"),
        }
    )

    df = pd.DataFrame(
        {
            "phone": ["invalid-phone"],
        }
    )

    frame = ar.from_pandas(df)

    result = ar.validate(frame, schema)

    assert result.passed

    assert result.issue_count == 1

    assert result.issues[0].severity == "warning"


def test_country_code_validation_accepts_iso_alpha_2_codes(tmp_path):
    path = tmp_path / "countries.csv"
    path.write_text("country\nIN\nUS\nGB\nFR\n")

    result = ar.validate(
        ar.read_csv(path),
        {"country": ar.CountryCode(nullable=False)},
    )

    assert result.passed
    assert result.issue_count == 0


def test_country_code_validation_rejects_invalid_codes(tmp_path):
    path = tmp_path / "bad_countries.csv"
    path.write_text("country\nIND\n1A\nA\nUSA\ngb\nFr\nQQ\nZZ\nAA\n")

    result = ar.validate(
        ar.read_csv(path),
        {"country": ar.CountryCode(nullable=False)},
    )

    assert not result.passed
    assert result.issue_count == 9

    assert [issue.row_index for issue in result.issues] == [1, 2, 3, 4, 5, 6, 7, 8, 9]
    assert all(issue.rule == "country_code" for issue in result.issues)


def test_language_code_validation_accepts_iso_639_1_codes(tmp_path):
    path = tmp_path / "languages.csv"
    path.write_text("language\nen\nhi\nfr\nde\n")

    result = ar.validate(
        ar.read_csv(path),
        {"language": ar.LanguageCode(nullable=False)},
    )

    assert result.passed
    assert result.issue_count == 0


def test_language_code_validation_rejects_invalid_codes(tmp_path):
    path = tmp_path / "bad_languages.csv"
    path.write_text("language\nenglish\neng\nEN\nEN-US\nzz\n123\n\n")

    result = ar.validate(
        ar.read_csv(path),
        {"language": ar.LanguageCode(nullable=False)},
    )

    assert not result.passed
    assert result.issue_count == 6

    assert [issue.row_index for issue in result.issues] == [1, 2, 3, 4, 5, 6]
    assert all(issue.rule == "language_code" for issue in result.issues)


def test_timezone_validation_accepts_iana_timezones(tmp_path):
    path = tmp_path / "timezones.csv"
    path.write_text("timezone\nAsia/Kolkata\nAmerica/New_York\nEurope/Paris\n")

    result = ar.validate(
        ar.read_csv(path),
        {"timezone": ar.TimeZone(nullable=False)},
    )

    assert result.passed
    assert result.issue_count == 0


def test_timezone_validation_rejects_invalid_values(tmp_path):
    path = tmp_path / "bad_timezones.csv"
    path.write_text("timezone\nIST\nGMT+5:30\nIndia\nAsia\\Kolkata\nrandom_text\n")

    result = ar.validate(
        ar.read_csv(path),
        {"timezone": ar.TimeZone(nullable=False)},
    )

    assert not result.passed
    assert result.issue_count == 5
    assert all(issue.rule == "timezone" for issue in result.issues)


def test_language_code_validation_accepts_extended_iso_codes(tmp_path):
    path = tmp_path / "extended_languages.csv"
    path.write_text("language\nzu\nxh\nvo\nwa\n")

    result = ar.validate(
        ar.read_csv(path),
        {"language": ar.LanguageCode(nullable=False)},
    )

    assert result.passed
    assert result.issue_count == 0


def test_language_code_validation_nullable_behavior(tmp_path):
    path = tmp_path / "nullable_languages.csv"
    path.write_text('language\nen\n""\nfr\n')

    result_nullable = ar.validate(
        ar.read_csv(path),
        {"language": ar.LanguageCode(nullable=True)},
    )

    assert result_nullable.passed
    assert result_nullable.issue_count == 0

    result_non_nullable = ar.validate(
        ar.read_csv(path),
        {"language": ar.LanguageCode(nullable=False)},
    )

    assert not result_non_nullable.passed
    assert result_non_nullable.issue_count == 1


def test_language_code_validation_rejects_mixed_case_codes(tmp_path):
    path = tmp_path / "mixed_case_languages.csv"
    path.write_text("language\nEn\nHI\nFr\n")

    result = ar.validate(
        ar.read_csv(path),
        {"language": ar.LanguageCode(nullable=False)},
    )

    assert not result.passed
    assert result.issue_count == 3


def test_language_code_validation_rejects_non_string_values(tmp_path):
    path = tmp_path / "numeric_languages.csv"
    path.write_text("language\n123\n456\n")

    result = ar.validate(
        ar.read_csv(path),
        {"language": ar.LanguageCode(nullable=False)},
    )

    assert not result.passed
    assert result.issue_count == 3
    assert any(issue.rule == "dtype" for issue in result.issues)
    assert sum(issue.rule == "language_code" for issue in result.issues) == 2


def test_country_code_enforces_uniqueness(tmp_path):
    path = tmp_path / "duplicate_countries.csv"
    path.write_text("country\nIN\nUS\nIN\n")

    result = ar.validate(
        ar.read_csv(path),
        {"country": ar.CountryCode(unique=True)},
    )

    assert not result.passed
    assert result.issue_count == 2
    assert all(issue.rule == "unique" for issue in result.issues)
    assert [issue.row_index for issue in result.issues] == [1, 3]
    assert [issue.value for issue in result.issues] == ["IN", "IN"]


def test_country_code_unique_ignores_multiple_nulls(tmp_path):
    path = tmp_path / "nullable_duplicate_countries.csv"
    path.write_text('country\nIN\n""\n""\nUS\n')

    result = ar.validate(
        ar.read_csv(path),
        {"country": ar.CountryCode(nullable=True, unique=True)},
    )

    assert result.passed
    assert result.issue_count == 0


def test_country_code_rejects_unassigned_alpha_2_codes(tmp_path):
    path = tmp_path / "unassigned_countries.csv"
    path.write_text("country\nAA\nQM\nQZ\nXA\nZZ\n")

    result = ar.validate(
        ar.read_csv(path),
        {"country": ar.CountryCode(nullable=False)},
    )

    assert not result.passed
    assert result.issue_count == 5
    assert all(issue.rule == "country_code" for issue in result.issues)
    assert [issue.row_index for issue in result.issues] == [1, 2, 3, 4, 5]
    assert [issue.value for issue in result.issues] == ["AA", "QM", "QZ", "XA", "ZZ"]


def test_country_code_nullable_behavior(tmp_path):
    path = tmp_path / "nullable_countries.csv"
    path.write_text('country\nIN\n""\nUS\n')

    # nullable=True should pass
    result_nullable = ar.validate(
        ar.read_csv(path),
        {"country": ar.CountryCode(nullable=True)},
    )
    assert result_nullable.passed

    # nullable=False should fail on row 2
    result_not_nullable = ar.validate(
        ar.read_csv(path),
        {"country": ar.CountryCode(nullable=False)},
    )
    assert not result_not_nullable.passed
    assert result_not_nullable.issue_count == 1
    assert result_not_nullable.issues[0].rule == "nullable"
    assert result_not_nullable.issues[0].row_index == 2


def test_string_min_length_boundary(tmp_path):
    path = tmp_path / "names.csv"
    path.write_text("name\nab\nabc\n")

    result = ar.validate(
        ar.read_csv(path),
        {"name": ar.String(min_length=3)},
    )

    assert not result.passed
    assert result.issue_count == 1
    assert result.issues[0].rule == "min_length"
    assert result.issues[0].row_index == 1


def test_string_max_length_boundary(tmp_path):
    path = tmp_path / "names.csv"
    path.write_text("name\nabcde\nabcdef\n")

    result = ar.validate(
        ar.read_csv(path),
        {"name": ar.String(max_length=5)},
    )

    assert not result.passed
    assert result.issue_count == 1
    assert result.issues[0].rule == "max_length"
    assert result.issues[0].row_index == 2


def test_null_values_skip_length_validation(tmp_path):
    path = tmp_path / "names.csv"
    path.write_text("name\n\nabcd\n")

    result = ar.validate(
        ar.read_csv(path),
        {"name": ar.String(min_length=5)},
    )

    assert not result.passed
    assert result.issue_count == 1
    assert result.issues[0].rule == "min_length"

    assert result.issues[0].row_index == 1


def test_int64_rejects_impossible_bounds():
    try:
        ar.Int64(min=10, max=1)
    except ValueError as exc:
        assert "min must be less than or equal to max" in str(exc)
    else:
        raise AssertionError("Expected invalid Int64 bounds to raise")


def test_invalid_severity_raises():
    with pytest.raises(ValueError, match="severity must be"):
        ar.Int64(severity="warn")


def test_float64_rejects_impossible_bounds():
    try:
        ar.Float64(min=10.0, max=1.0)
    except ValueError as exc:
        assert "min must be less than or equal to max" in str(exc)
    else:
        raise AssertionError("Expected invalid Float64 bounds to raise")


def test_string_rejects_impossible_length_bounds():
    try:
        ar.String(min_length=5, max_length=2)
    except ValueError as exc:
        assert "min_length must be less than or equal to max_length" in str(exc)
    else:
        raise AssertionError("Expected invalid String bounds to raise")


def test_equal_numeric_bounds_are_valid():
    field = ar.Int64(min=5, max=5)

    assert field.min == 5
    assert field.max == 5


def test_equal_string_length_bounds_are_valid():
    field = ar.String(min_length=3, max_length=3)

    assert field.min_length == 3
    assert field.max_length == 3


def test_schema_composite_unique_passes(tmp_path):
    path = tmp_path / "composite.csv"
    path.write_text("user_id,course_id\n1,101\n1,102\n2,101\n")
    frame = ar.read_csv(path)
    schema = ar.Schema(
        {
            "user_id": ar.Int64(),
            "course_id": ar.Int64(),
        },
        unique=["user_id", "course_id"],
    )
    result = schema.validate(frame)
    assert result.passed
    assert result.issue_count == 0


def test_schema_composite_unique_fails(tmp_path):
    path = tmp_path / "composite_bad.csv"
    path.write_text("user_id,course_id\n1,101\n1,102\n1,101\n")
    frame = ar.read_csv(path)
    schema = ar.Schema(
        {
            "user_id": ar.Int64(),
            "course_id": ar.Int64(),
        },
        unique=["user_id", "course_id"],
    )
    result = schema.validate(frame)
    assert not result.passed
    issues = [i for i in result.issues if i.rule == "composite_unique"]
    assert len(issues) == 2
    assert issues[0].row_index == 1
    assert issues[1].row_index == 3
    assert "['user_id', 'course_id']" in issues[0].message


def test_schema_composite_unique_invalid_column(tmp_path):
    path = tmp_path / "composite_invalid.csv"
    path.write_text("user_id,course_id\n1,101\n")
    frame = ar.read_csv(path)
    schema = ar.Schema(
        {
            "user_id": ar.Int64(),
            "course_id": ar.Int64(),
        },
        unique=["user_id", "bad_column"],
    )
    result = schema.validate(frame)
    assert not result.passed
    issues = [i for i in result.issues if i.rule == "missing_column"]
    assert len(issues) == 1
    assert issues[0].column == "bad_column"


def test_schema_composite_unique_empty_columns(tmp_path):
    path = tmp_path / "composite_empty.csv"
    path.write_text("user_id,course_id\n1,101\n")
    frame = ar.read_csv(path)
    schema = ar.Schema(
        {
            "user_id": ar.Int64(),
            "course_id": ar.Int64(),
        },
        unique=[],
    )
    result = schema.validate(frame)
    assert not result.passed
    issues = [i for i in result.issues if i.rule == "composite_unique"]
    assert len(issues) == 1
    assert "cannot be empty" in issues[0].message


def test_schema_unique_rejects_string():
    with pytest.raises(TypeError) as exc:
        ar.Schema(
            {
                "user_id": ar.Int64(),
            },
            unique="user_id",
        )
    assert "bare string" in str(exc.value)


def test_schema_unique_rejects_invalid_type():
    with pytest.raises(TypeError) as exc:
        ar.Schema(
            {
                "user_id": ar.Int64(),
            },
            unique=123,  # type: ignore[arg-type]
        )
    assert "must be a list or tuple" in str(exc.value)


def test_schema_unique_rejects_non_string_members():
    with pytest.raises(TypeError) as exc:
        ar.Schema(
            {
                "user_id": ar.Int64(),
            },
            unique=["col1", None],  # type: ignore[list-item]
        )
    assert "members must be strings" in str(exc.value)

    with pytest.raises(TypeError) as exc:
        ar.Schema(
            {
                "user_id": ar.Int64(),
            },
            unique=["col1", 123],  # type: ignore[list-item]
        )
    assert "members must be strings" in str(exc.value)


def test_schema_unique_accepts_valid_types():
    # Verify list of strings initializes successfully
    schema_list = ar.Schema(
        {
            "user_id": ar.Int64(),
            "course_id": ar.Int64(),
        },
        unique=["user_id", "course_id"],
    )
    assert schema_list.unique == ["user_id", "course_id"]

    # Verify tuple of strings initializes successfully
    schema_tuple = ar.Schema(
        {
            "user_id": ar.Int64(),
            "course_id": ar.Int64(),
        },
        unique=("user_id", "course_id"),
    )
    assert schema_tuple.unique == ("user_id", "course_id")


@pytest.mark.parametrize("value", ["false", 1, None])
def test_field_nullable_rejects_non_bool_values(value):
    with pytest.raises(TypeError, match="nullable must be a bool"):
        ar.String(nullable=value)  # type: ignore[arg-type]


@pytest.mark.parametrize("value", ["yes", 1, None])
def test_field_unique_rejects_non_bool_values(value):
    with pytest.raises(TypeError, match="unique must be a bool"):
        ar.Int64(unique=value)  # type: ignore[arg-type]


def test_field_nullable_and_unique_accept_valid_bools():
    field = ar.String(nullable=False, unique=True)

    assert field.nullable is False
    assert field.unique is True


def test_email_default_keeps_backward_compatibility(sample_csv):
    frame = ar.read_csv(sample_csv)

    result = ar.validate(
        frame,
        {"email": ar.Email(nullable=False)},
    )

    assert all(
        issue.rule == "email" for issue in result.issues if "email" in issue.rule
    )


def test_datetime_validation_passes_for_valid_column(tmp_path):
    path = tmp_path / "valid_datetimes.csv"
    path.write_text(
        "ts\n" "2026-01-01T12:00:00\n" "2026-06-15T08:30:00\n" "2026-12-31T23:59:59\n"
    )

    result = ar.validate(
        ar.read_csv(path),
        {
            "ts": ar.DateTime(
                nullable=False,
                format="%Y-%m-%dT%H:%M:%S",
                min="2026-01-01",
                max="2026-12-31T23:59:59",
            )
        },
    )

    assert result.passed
    assert result.issue_count == 0
    assert result.bad_rows == []


def test_datetime_rejects_invalid_format_type():
    with pytest.raises(TypeError, match="format must be a string or None"):
        ar.DateTime(format=123)


def test_datetime_rejects_invalid_boundary_values():
    with pytest.raises(ValueError, match="min must be a parseable datetime scalar"):
        ar.DateTime(min="not-a-date")

    with pytest.raises(ValueError, match="max must be a parseable datetime scalar"):
        ar.DateTime(max=["2026-01-01", "2026-01-02"])


def test_datetime_rejects_min_greater_than_max():
    with pytest.raises(ValueError, match="min must be less than or equal to max"):
        ar.DateTime(min="2026-12-31", max="2026-01-01")


def test_datetime_validation(tmp_path):
    path = tmp_path / "datetimes.csv"
    path.write_text(
        "ts,note\n"
        "2026-01-01T12:00:00,start\n"
        "2026-12-31T23:59:59,end\n"
        ",missing\n"
        "invalid-date,bad\n"
    )
    frame = ar.read_csv(path)
    schema = ar.Schema(
        {
            "ts": ar.DateTime(
                nullable=False,
                format="%Y-%m-%dT%H:%M:%S",
                min="2026-01-01",
                max="2026-12-31T23:59:59",
            )
        }
    )

    result = ar.validate(frame, schema)
    rules = [issue.rule for issue in result.issues]

    assert not result.passed
    assert "format" in rules
    assert "nullable" in rules

    path2 = tmp_path / "boundary.csv"
    path2.write_text("ts\n" "2025-12-31T23:59:59\n" "2027-01-01T00:00:00\n")
    frame2 = ar.read_csv(path2)
    result2 = ar.validate(frame2, schema)
    rules2 = [issue.rule for issue in result2.issues]

    assert "min" in rules2
    assert "max" in rules2


def test_row_index_is_one_based_for_middle_row(tmp_path):
    path = tmp_path / "codes.csv"
    path.write_text("age\n30\n-5\n25\n")
    frame = ar.read_csv(path)
    result = ar.validate(frame, {"age": ar.Int64(min=0)})

    assert not result.passed
    assert len(result.issues) == 1
    assert result.issues[0].row_index == 2


def test_row_index_is_one_based_for_last_row(tmp_path):
    path = tmp_path / "codes.csv"
    path.write_text("age\n30\n25\n-1\n")
    frame = ar.read_csv(path)
    result = ar.validate(frame, {"age": ar.Int64(min=0)})

    assert not result.passed
    assert len(result.issues) == 1
    assert result.issues[0].row_index == 3


def test_row_index_multiple_invalid_rows(tmp_path):
    path = tmp_path / "codes.csv"
    path.write_text("age\n-1\n30\n-5\n25\n-9\n")
    frame = ar.read_csv(path)
    result = ar.validate(frame, {"age": ar.Int64(min=0)})

    assert not result.passed
    row_indexes = [issue.row_index for issue in result.issues]
    assert row_indexes == [1, 3, 5]


def test_bad_rows_reflects_one_based_indexes(tmp_path):
    """bad_rows should contain 1-based row numbers."""
    path = tmp_path / "codes.csv"
    path.write_text("age\n-1\n30\n-5\n")
    frame = ar.read_csv(path)
    result = ar.validate(frame, {"age": ar.Int64(min=0)})

    assert result.bad_rows == [1, 3]
    assert result.issues[0].row_index == 1


def test_regex_valid_match(tmp_path):
    path = tmp_path / "ids.csv"
    path.write_text("user_id\nUSR-1234\nUSR-5678\n")
    result = ar.validate(
        ar.read_csv(path),
        {"user_id": ar.Regex(r"^USR-\d{4}$", nullable=False)},
    )

    assert result.passed
    assert result.issue_count == 0


def test_regex_mismatch_reports_pattern_rule(tmp_path):
    path = tmp_path / "ids.csv"
    path.write_text("user_id\nUSR-1234\nbadvalue\n")
    result = ar.validate(
        ar.read_csv(path),
        {"user_id": ar.Regex(r"^USR-\d{4}$", nullable=False)},
    )

    assert not result.passed
    assert result.issues[0].rule == "pattern"
    assert result.issues[0].row_index == 2


def test_regex_null_allowed(tmp_path):
    path = tmp_path / "ids.csv"
    path.write_text("user_id\nUSR-1234\n\n")
    result = ar.validate(
        ar.read_csv(path),
        {"user_id": ar.Regex(r"^USR-\d{4}$", nullable=True)},
    )
    assert result.passed


def test_date_validation_rejects_invalid_dates(tmp_path):
    path = tmp_path / "bad_dates.csv"
    path.write_text("created_at\n2026-99-99\nhello\n15/05/2026\n2026-02-30\n")

    result = ar.validate(
        ar.read_csv(path),
        {"created_at": ar.Date(nullable=False)},
    )

    assert not result.passed
    assert result.issue_count == 4

    rules = {issue.rule for issue in result.issues}
    assert "date" in rules


def test_date_validation_handles_nullable_values(tmp_path):
    path = tmp_path / "nullable_dates.csv"
    path.write_text("created_at\n2026-05-15\n\n")

    result = ar.validate(
        ar.read_csv(path),
        {"created_at": ar.Date(nullable=True)},
    )

    assert result.passed


def test_regex_null_not_allowed(tmp_path):
    path = tmp_path / "ids.csv"
    path.write_text("user_id,other\nUSR-1234,a\n,b\n")
    result = ar.validate(
        ar.read_csv(path),
        {"user_id": ar.Regex(r"^USR-\d{4}$", nullable=False)},
    )

    assert not result.passed
    assert result.issues[0].rule == "nullable"


def test_regex_invalid_pattern_raises_at_construction():
    try:
        ar.Regex(r"[invalid")
        assert False, "Expected re.error"
    except Exception as exc:
        assert (
            "unterminated" in str(exc).lower() or "error" in type(exc).__name__.lower()
        )


def test_regex_numeric_column_coerces_to_string(tmp_path):
    path = tmp_path / "codes.csv"
    path.write_text("code\n123\n456\n")
    result = ar.validate(
        ar.read_csv(path),
        {"code": ar.Regex(r"^\d+$")},
    )

    assert result.issues[0].rule == "dtype"


def test_regex_fullmatch_not_partial(tmp_path):
    path = tmp_path / "ids.csv"
    path.write_text("user_id\nUSR-1234-EXTRA\n")
    result = ar.validate(
        ar.read_csv(path),
        {"user_id": ar.Regex(r"^USR-\d{4}$")},
    )

    assert not result.passed
    assert result.issues[0].rule == "pattern"


def test_date_validation_rejects_non_zero_padded_dates(tmp_path):
    path = tmp_path / "non_padded_dates.csv"
    path.write_text("created_at\n" "2026-5-15\n" "2026-05-5\n" "2026-5-5\n")

    result = ar.validate(
        ar.read_csv(path),
        {"created_at": ar.Date(nullable=False)},
    )

    assert not result.passed
    assert result.issue_count == 3

    rules = {issue.rule for issue in result.issues}
    assert "date" in rules


def test_required_if_validation_passes_when_condition_matches(tmp_path):
    path = tmp_path / "conditional_pass.csv"
    path.write_text("user_type,country\n" "international,IN\n" "local,\n")

    frame = ar.read_csv(path)

    schema = ar.Schema(
        {
            "user_type": ar.String(nullable=False),
            "country": ar.String(
                nullable=True,
                required_if=("user_type", "international"),
            ),
        }
    )

    result = schema.validate(frame)

    assert result.passed
    assert result.issue_count == 0
    assert result.bad_rows == []


def test_required_if_validation_fails_when_condition_matches(tmp_path):
    path = tmp_path / "conditional_fail.csv"
    path.write_text("user_type,country\n" "international,\n" "local,IN\n")

    frame = ar.read_csv(path)

    schema = ar.Schema(
        {
            "user_type": ar.String(nullable=False),
            "country": ar.String(
                nullable=True,
                required_if=("user_type", "international"),
            ),
        }
    )

    result = schema.validate(frame)

    assert not result.passed
    assert result.issue_count == 1
    assert result.issues[0].rule == "required_if"
    assert result.issues[0].column == "country"
    assert result.issues[0].row_index == 1


def _date_order_rule(df):
    return [
        ar.ValidationIssue(
            column="end_date",
            rule="cross_field",
            message="end_date must be >= start_date",
            row_index=int(i) + 1,
        )
        for i, row in df.iterrows()
        if row["end_date"] < row["start_date"]
    ]


def test_schema_rules_passes_when_all_rows_satisfy_rule(tmp_path):
    path = tmp_path / "dates.csv"
    path.write_text(
        "start_date,end_date\n2024-01-01,2024-06-01\n2024-03-01,2024-12-31\n"
    )
    frame = ar.read_csv(path)
    schema = ar.Schema(
        {"start_date": ar.String(), "end_date": ar.String()},
        rules=[_date_order_rule],
    )

    result = schema.validate(frame)

    assert result.passed
    assert result.issue_count == 0
    assert result.bad_rows == []


def test_schema_rules_fails_when_end_date_before_start_date(tmp_path):
    path = tmp_path / "dates.csv"
    path.write_text(
        "start_date,end_date\n2025-05-17,2025-05-16\n2025-05-1,2025-05-11\n"
    )
    frame = ar.read_csv(path)
    schema = ar.Schema(
        {"start_date": ar.String(), "end_date": ar.String()},
        rules=[_date_order_rule],
    )

    result = schema.validate(frame)

    assert not result.passed
    assert result.issue_count == 1
    assert result.issues[0].rule == "cross_field"
    assert result.issues[0].column == "end_date"


def test_required_if_validation_ignores_non_matching_conditions(tmp_path):
    path = tmp_path / "conditional_ignore.csv"
    path.write_text("user_type,country\n" "local,\n" "guest,\n")

    frame = ar.read_csv(path)

    schema = ar.Schema(
        {
            "user_type": ar.String(nullable=False),
            "country": ar.String(
                nullable=True,
                required_if=("user_type", "international"),
            ),
        }
    )

    result = schema.validate(frame)

    assert result.passed
    assert result.issue_count == 0


def test_schema_rules_equal_boundary_passes(tmp_path):
    path = tmp_path / "dates.csv"
    path.write_text("start_date,end_date\n2025-05-18,2025-05-18\n")
    frame = ar.read_csv(path)
    schema = ar.Schema(
        {"start_date": ar.String(), "end_date": ar.String()},
        rules=[_date_order_rule],
    )

    result = schema.validate(frame)

    assert result.passed
    assert result.issue_count == 0


def test_required_if_validation_reports_missing_trigger_column(tmp_path):
    path = tmp_path / "missing_trigger.csv"
    path.write_text("country\n" "IN\n")
    frame = ar.read_csv(path)
    schema = ar.Schema(
        {
            "country": ar.String(
                required_if=("user_type", "international"),
            ),
        }
    )
    result = schema.validate(frame)
    assert not result.passed
    assert result.issue_count == 1
    assert result.issues[0].rule == "missing_column"
    assert result.issues[0].column == "user_type"


def test_schema_rules_row_index_is_one_based(tmp_path):
    path = tmp_path / "dates.csv"
    path.write_text(
        "start_date,end_date\n"
        "2025-01-01,2025-06-01\n"
        "2025-09-01,2025-03-01\n"
        "2025-01-01,2025-12-31\n"
    )
    frame = ar.read_csv(path)
    schema = ar.Schema(
        {"start_date": ar.String(), "end_date": ar.String()},
        rules=[_date_order_rule],
    )
    result = schema.validate(frame)
    assert not result.passed
    assert len(result.issues) == 1
    assert result.issues[0].row_index == 2


def test_schema_rules_row_index_for_multiple_failing_rows(tmp_path):
    path = tmp_path / "dates.csv"
    path.write_text(
        "start_date,end_date\n"
        "2025-06-01,2025-01-01\n"
        "2024-01-01,2024-12-31\n"
        "2024-12-01,2024-03-01\n"
    )
    frame = ar.read_csv(path)
    schema = ar.Schema(
        {"start_date": ar.String(), "end_date": ar.String()},
        rules=[_date_order_rule],
    )
    result = schema.validate(frame)
    row_indexes = [issue.row_index for issue in result.issues]
    assert row_indexes == [1, 3]


def test_row_index_convention_is_documented_and_correct(tmp_path):
    """Regression: row_index is 1-based, header excluded, first data row = 1."""
    path = tmp_path / "rows.csv"
    path.write_text("name,age\nAlice,30\nBob,-1\nCarol,25\n")
    frame = ar.read_csv(path)
    result = ar.validate(frame, {"age": ar.Int64(min=0)})

    assert not result.passed
    assert len(result.issues) == 1
    # Bob is the second data row → row_index must be 2, not 0 or 1
    assert result.issues[0].row_index == 2
    assert result.issues[0].column == "age"
    assert result.issues[0].rule == "min"


def test_schema_rules_missing_column_returns_validation_issue(tmp_path):
    path = tmp_path / "dates.csv"
    path.write_text("start_date,end_date\n2024-01-01,2024-06-01\n")
    frame = ar.read_csv(path)

    def rule_with_bad_column(df):
        return [
            ar.ValidationIssue(
                column="nonexistent",
                rule="cross_field",
                message="column missing",
                row_index=int(i) + 1,
            )
            for i, row in df.iterrows()
            if row["nonexistent"] < row["start_date"]
        ]

    schema = ar.Schema(
        {"start_date": ar.String(), "end_date": ar.String()},
        rules=[rule_with_bad_column],
    )
    result = schema.validate(frame)
    assert not result.passed
    assert result.issue_count == 1
    issue = result.issues[0]
    assert isinstance(issue, ar.ValidationIssue)
    assert issue.rule == "missing_column"
    assert "nonexistent" in issue.message


def test_required_if_validation_handles_null_trigger_values(tmp_path):
    path = tmp_path / "null_trigger.csv"
    path.write_text("user_type,country\n" ",\n" "international,IN\n")
    frame = ar.read_csv(path)
    schema = ar.Schema(
        {
            "user_type": ar.String(nullable=True),
            "country": ar.String(
                nullable=True,
                required_if=("user_type", "international"),
            ),
        }
    )
    result = schema.validate(frame)
    assert result.passed
    assert result.issue_count == 0


def test_register_validator_and_custom_field_passes(tmp_path):
    ar.register_validator("positive", lambda v: v > 0)
    path = tmp_path / "scores.csv"
    path.write_text("score\n1\n5\n100\n")
    result = ar.validate(ar.read_csv(path), {"score": ar.Custom("positive")})
    assert result.passed


def test_register_validator_and_custom_field_fails(tmp_path):
    ar.register_validator("positive", lambda v: v > 0)
    path = tmp_path / "scores.csv"
    path.write_text("score\n1\n-5\n0\n")
    result = ar.validate(ar.read_csv(path), {"score": ar.Custom("positive")})
    assert not result.passed
    assert result.issues[0].rule == "custom"
    assert result.issues[0].row_index == 2


def test_custom_field_respects_nullable(tmp_path):
    import pandas as pd

    ar.register_validator("positive", lambda v: v > 0)
    df = pd.DataFrame({"score": [1, None, 5]})
    frame = ar.from_pandas(df)
    result = ar.validate(frame, {"score": ar.Custom("positive", nullable=False)})
    assert not result.passed
    assert any(i.rule == "nullable" for i in result.issues)


def test_custom_raises_for_unregistered_name():
    try:
        ar.Custom("nonexistent_validator")
    except ValueError as exc:
        assert "nonexistent_validator" in str(exc)
    else:
        raise AssertionError("Expected ValueError for unregistered validator")


def test_register_validator_raises_for_non_callable():
    try:
        ar.register_validator("bad", "not_a_function")
    except TypeError as exc:
        assert "callable" in str(exc)
    else:
        raise AssertionError("Expected TypeError")


def test_register_validator_raises_for_empty_name():
    try:
        ar.register_validator("", lambda v: True)
    except ValueError as exc:
        assert "non-empty" in str(exc)
    else:
        raise AssertionError("Expected ValueError for empty name")


def test_custom_validator_exceptions_propagate(tmp_path):
    def broken_validator(value):
        raise RuntimeError("validator exploded")

    ar.register_validator("broken", broken_validator)

    path = tmp_path / "scores.csv"
    path.write_text("score\n1\n")

    with pytest.raises(RuntimeError) as exc:
        ar.validate(
            ar.read_csv(path),
            {"score": ar.Custom("broken")},
        )

    assert "validator exploded" in str(exc.value)


def test_schema_rules_multiple_rules_all_run(tmp_path):
    path = tmp_path / "dates.csv"
    path.write_text("start_date,end_date\n2025-06-01,2025-01-01\n")
    frame = ar.read_csv(path)

    def always_fails(df):
        return [
            ar.ValidationIssue(
                column="start_date",
                rule="custom_check",
                message="always fails",
                row_index=1,
            )
        ]

    schema = ar.Schema(
        {"start_date": ar.String(), "end_date": ar.String()},
        rules=[_date_order_rule, always_fails],
    )
    result = schema.validate(frame)
    rules = {issue.rule for issue in result.issues}
    assert "cross_field" in rules
    assert "custom_check" in rules
    assert result.issue_count == 2


def test_schema_rules_none_by_default(tmp_path):
    path = tmp_path / "dates.csv"
    path.write_text("start_date,end_date\n2025-05-01,2025-01-01\n")
    frame = ar.read_csv(path)
    schema = ar.Schema({"start_date": ar.String(), "end_date": ar.String()})
    result = schema.validate(frame)
    assert result.passed
    assert result.issue_count == 0


def test_currency_code_valid(tmp_path):
    path = tmp_path / "currencies.csv"
    path.write_text("currency\nUSD\nEUR\nINR\nJPY\n")

    result = ar.validate(
        ar.read_csv(path),
        {"currency": ar.CurrencyCode(nullable=False)},
    )

    assert result.passed
    assert result.issue_count == 0


def test_currency_code_invalid(tmp_path):
    path = tmp_path / "bad_currencies.csv"
    # We add a dummy column so the empty currency row isn't skipped as a blank line
    path.write_text("currency,dummy\nUS,1\nUSDD,2\nusd,3\nUS1,4\nEur,5\n,6\n")

    result = ar.validate(
        ar.read_csv(path),
        {"currency": ar.CurrencyCode(nullable=False)},
    )

    assert not result.passed
    assert result.issue_count == 6

    assert sorted([issue.row_index for issue in result.issues]) == [1, 2, 3, 4, 5, 6]

    rules = {issue.rule for issue in result.issues}
    assert "currency_code" in rules
    assert "nullable" in rules


def test_schema_rules_issue_shape_matches_validation_issue(tmp_path):
    path = tmp_path / "dates.csv"
    path.write_text("start_date,end_date\n2025-05-01,2025-01-01\n")
    frame = ar.read_csv(path)
    schema = ar.Schema(
        {"start_date": ar.String(), "end_date": ar.String()},
        rules=[_date_order_rule],
    )
    result = schema.validate(frame)
    issue = result.issues[0]
    assert isinstance(issue, ar.ValidationIssue)
    assert issue.column == "end_date"
    assert issue.rule == "cross_field"
    assert isinstance(issue.message, str)
    assert issue.row_index is not None


def test_schema_rules_invalid_output_raises_type_error(tmp_path):
    path = tmp_path / "dates.csv"
    path.write_text("start_date,end_date\n2025-01-01,2025-06-01\n")
    frame = ar.read_csv(path)

    def bad_rule(df):
        return ["not a ValidationIssue"]

    schema = ar.Schema(
        {"start_date": ar.String(), "end_date": ar.String()},
        rules=[bad_rule],
    )

    with pytest.raises(TypeError, match="ValidationIssue"):
        schema.validate(frame)


def test_diff_schema_reports_missing_extra_and_changed_fields():
    expected = ar.Schema(
        {
            "id": ar.Int64(nullable=False, unique=True),
            "email": ar.Email(nullable=False),
            "status": ar.String(allowed={"active", "blocked"}),
        },
        strict=True,
    )
    observed = ar.Schema(
        {
            "id": ar.Int64(nullable=False),
            "status": ar.String(allowed={"active", "pending"}),
            "created_at": ar.DateTime(format="%Y-%m-%d"),
        },
        strict=False,
    )

    diff = ar.diff_schema(expected, observed)
    changes = {(item.column, item.change, item.attribute) for item in diff.differences}

    assert diff.changed
    assert diff.difference_count == 5
    assert ("email", "missing_column", None) in changes
    assert ("created_at", "extra_column", None) in changes
    assert ("id", "changed_field", "unique") in changes
    assert ("status", "changed_field", "allowed") in changes
    assert (None, "changed_schema", "strict") in changes


def test_diff_schema_accepts_plain_field_dicts():
    diff = ar.diff_schema(
        {"id": ar.Int64(nullable=False)},
        {"id": ar.Int64(nullable=False)},
    )

    assert not diff.changed
    assert diff.difference_count == 0
    assert diff.to_dict() == {
        "changed": False,
        "difference_count": 0,
        "differences": [],
    }


def test_diff_schema_treats_composite_unique_order_as_equivalent():
    expected = ar.Schema(
        {"user_id": ar.String(), "event_id": ar.String()},
        unique=["user_id", "event_id"],
    )
    observed = ar.Schema(
        {"user_id": ar.String(), "event_id": ar.String()},
        unique=["event_id", "user_id"],
    )

    diff = ar.diff_schema(expected, observed)

    assert not diff.changed
    assert diff.difference_count == 0


def test_diff_schema_reports_composite_unique_column_set_changes():
    expected = ar.Schema(
        {"user_id": ar.String(), "event_id": ar.String(), "session_id": ar.String()},
        unique=["user_id", "event_id"],
    )
    observed = ar.Schema(
        {"user_id": ar.String(), "event_id": ar.String(), "session_id": ar.String()},
        unique=["user_id", "session_id"],
    )

    diff = ar.diff_schema(expected, observed)

    assert diff.changed
    assert diff.differences == [
        ar.SchemaDiffEntry(
            column=None,
            change="changed_schema",
            attribute="unique",
            expected=("event_id", "user_id"),
            observed=("session_id", "user_id"),
        )
    ]


def test_schema_diff_summary_and_markdown_escape_cells():
    diff = ar.SchemaDiff(
        [
            ar.SchemaDiffEntry(
                column="notes|raw",
                change="changed_field",
                attribute="pattern",
                expected="left|right",
                observed="left\nright",
            )
        ]
    )

    assert diff.summary() == {
        "changed": True,
        "difference_count": 1,
        "differences_by_change": {"changed_field": 1},
        "differences_by_column": {"notes|raw": 1},
    }
    markdown = diff.to_markdown()
    assert "## Schema Diff" in markdown
    assert "notes\\|raw" in markdown
    assert "left\\|right" in markdown
    assert "left<br>right" in markdown


def test_datetime_timezone_aware_within_bounds_passes(tmp_path):
    path = tmp_path / "tz_datetimes.csv"
    path.write_text("ts\n2026-06-01T12:00:00+05:30\n")
    frame = ar.read_csv(path)
    schema = ar.Schema(
        {
            "ts": ar.DateTime(
                nullable=False,
                format="%Y-%m-%dT%H:%M:%S%z",
                min="2026-01-01T00:00:00+05:30",
                max="2026-12-31T23:59:59+05:30",
            )
        }
    )
    result = schema.validate(frame)
    assert result.passed
    assert result.issue_count == 0


def test_datetime_timezone_aware_below_min_fails(tmp_path):
    path = tmp_path / "tz_datetimes.csv"
    path.write_text("ts\n2025-12-31T23:59:59+05:30\n")
    frame = ar.read_csv(path)
    schema = ar.Schema(
        {
            "ts": ar.DateTime(
                nullable=False,
                format="%Y-%m-%dT%H:%M:%S%z",
                min="2026-01-01T00:00:00+05:30",
                max="2026-12-31T23:59:59+05:30",
            )
        }
    )
    result = schema.validate(frame)
    assert not result.passed
    assert any(i.rule == "min" for i in result.issues)
    assert result.issues[0].row_index == 1


def test_datetime_timezone_aware_above_max_fails(tmp_path):
    path = tmp_path / "tz_datetimes.csv"
    path.write_text("ts\n2027-01-01T00:00:00+05:30\n")
    frame = ar.read_csv(path)
    schema = ar.Schema(
        {
            "ts": ar.DateTime(
                nullable=False,
                format="%Y-%m-%dT%H:%M:%S%z",
                min="2026-01-01T00:00:00+05:30",
                max="2026-12-31T23:59:59+05:30",
            )
        }
    )
    result = schema.validate(frame)
    assert not result.passed
    assert any(i.rule == "max" for i in result.issues)
    assert result.issues[0].row_index == 1


def test_validate_unique_string_raises_type_error(tmp_path):
    schema = ar.Schema(fields={"id": ar.String()}, unique=["id"])

    object.__setattr__(schema, "unique", "id")

    path = tmp_path / "unique_test.csv"
    path.write_text("id\nA\nB\nA\n")
    frame = ar.read_csv(path)

    with pytest.raises(
        TypeError, match="Schema 'unique' must be a list or tuple of strings"
    ):
        ar.validate(frame, schema)


def test_validate_unique_invalid_member_type_raises_type_error(tmp_path):
    schema = ar.Schema(fields={"id": ar.String()}, unique=["id"])

    object.__setattr__(schema, "unique", ["id", 123])

    path = tmp_path / "unique_member_test.csv"
    path.write_text("id\nA\nB\n")
    frame = ar.read_csv(path)

    with pytest.raises(TypeError, match="Schema 'unique' members must be strings"):
        ar.validate(frame, schema)


def test_schema_json_roundtrip_preserves_fields_and_options():
    ar.register_validator("positive_json", lambda v: v > 0)

    schema = ar.Schema(
        fields={
            "id": ar.String(nullable=False, min_length=3, max_length=8, unique=True),
            "status": ar.String(
                allowed={"active", "inactive"}, required_if=("id", "A1")
            ),
            "score": ar.Custom("positive_json", nullable=False),
            "created_at": ar.DateTime(
                nullable=False,
                format="%Y-%m-%dT%H:%M:%S",
                min="2026-01-01T00:00:00",
                max="2026-12-31T23:59:59",
            ),
        },
        strict=True,
        unique=["id", "created_at"],
    )

    restored = ar.Schema.from_json(schema.to_json())

    assert restored == schema


def test_schema_from_json_rejects_invalid_json():
    with pytest.raises(ValueError, match="Invalid schema JSON"):
        ar.Schema.from_json("{bad json}")


def test_schema_to_json_warns_and_omits_rules():
    schema = ar.Schema(
        {"id": ar.String()},
        rules=[lambda df: []],
    )

    with pytest.warns(UserWarning, match="rules_omitted"):
        payload_str = schema.to_json()

    payload = json.loads(payload_str)
    assert payload["rules_omitted"] is True
    assert "id" in payload["fields"]


def test_schema_from_json_rejects_non_object_field_definition():
    with pytest.raises(TypeError, match="must be an object"):
        ar.Schema.from_json('{"fields":{"id":"string"},"strict":false,"unique":null}')


def test_empty_string_fails_when_not_nullable():
    df = pd.DataFrame(
        {
            "user_id": [1, 2, 3, 4, 5],
            "username": ["alice", "", "   ", None, float("nan")],
        }
    )
    schema = ar.Schema(
        {"user_id": ar.Int64(nullable=False), "username": ar.String(nullable=False)}
    )
    result = ar.validate(ar.from_pandas(df), schema)

    assert result.issue_count == 4
    for issue in result.issues:
        assert issue.column == "username"
        assert issue.rule == "nullable"


def test_empty_string_passes_when_nullable():
    df = pd.DataFrame(
        {
            "user_id": [1, 2, 3, 4, 5],
            "username": ["alice", "", "   ", None, float("nan")],
        }
    )
    schema = ar.Schema(
        {"user_id": ar.Int64(nullable=False), "username": ar.String(nullable=True)}
    )
    result = ar.validate(ar.from_pandas(df), schema)

    assert result.issue_count == 0


def test_url_https_only_accepts_https(tmp_path):
    path = tmp_path / "urls.csv"
    path.write_text("url\nhttps://example.com\nhttps://test.org\n")
    result = ar.validate(ar.read_csv(path), {"url": ar.URL(allowed_schemes=["https"])})
    assert result.passed


def test_url_https_only_rejects_http(tmp_path):
    path = tmp_path / "urls.csv"
    path.write_text("url\nhttp://example.com\n")
    result = ar.validate(ar.read_csv(path), {"url": ar.URL(allowed_schemes=["https"])})
    assert not result.passed


def test_url_multiple_schemes_accepted(tmp_path):
    path = tmp_path / "urls.csv"
    path.write_text("url\nhttps://example.com\nftp://files.example.com\n")
    result = ar.validate(
        ar.read_csv(path), {"url": ar.URL(allowed_schemes=["https", "ftp"])}
    )
    assert result.passed


def test_url_multiple_schemes_rejects_unlisted(tmp_path):
    path = tmp_path / "urls.csv"
    path.write_text("url\nhttp://example.com\n")
    result = ar.validate(
        ar.read_csv(path), {"url": ar.URL(allowed_schemes=["https", "ftp"])}
    )
    assert not result.passed


def test_url_default_accepts_http_and_https(tmp_path):
    path = tmp_path / "urls.csv"
    path.write_text("url\nhttp://example.com\nhttps://example.com\n")
    result = ar.validate(ar.read_csv(path), {"url": ar.URL()})
    assert result.passed


def test_url_allowed_schemes_nullable_true_accepts_nulls(tmp_path):
    path = tmp_path / "urls.csv"
    path.write_text("url,dummy\nhttps://example.com,1\n,2\n")
    result = ar.validate(
        ar.read_csv(path), {"url": ar.URL(allowed_schemes=["https"], nullable=True)}
    )
    assert result.passed


def test_url_allowed_schemes_nullable_false_rejects_nulls(tmp_path):
    path = tmp_path / "urls.csv"
    path.write_text("url,dummy\nhttps://example.com,1\n,2\n")
    result = ar.validate(
        ar.read_csv(path), {"url": ar.URL(allowed_schemes=["https"], nullable=False)}
    )
    assert not result.passed


def test_url_allowed_schemes_empty_list_raises():
    with pytest.raises(ValueError, match="non-empty"):
        ar.URL(allowed_schemes=[])


def test_url_allowed_schemes_empty_string_raises():
    with pytest.raises(ValueError, match="non-empty strings"):
        ar.URL(allowed_schemes=[""])


def test_url_allowed_schemes_non_string_raises():
    with pytest.raises(ValueError, match="non-empty strings"):
        ar.URL(allowed_schemes=[123])


def test_url_allowed_schemes_whitespace_string_raises():
    with pytest.raises(ValueError, match="non-empty strings"):
        ar.URL(allowed_schemes=["   "])


# --- Issue #1279: Schema.to_json() rules_omitted contract ---


def test_schema_to_json_with_rules_emits_warning():
    """to_json() emits UserWarning when rules are present."""
    schema = ar.Schema(
        {"start_date": ar.String(), "end_date": ar.String()},
        rules=[lambda df: []],
    )
    with pytest.warns(UserWarning, match="rules_omitted"):
        schema.to_json()


def test_schema_to_json_with_rules_includes_marker():
    """to_json() payload contains rules_omitted: true when rules are present."""
    schema = ar.Schema(
        {"id": ar.String()},
        rules=[lambda df: []],
    )
    with pytest.warns(UserWarning):
        payload = json.loads(schema.to_json())
    assert payload["rules_omitted"] is True


def test_schema_to_json_without_rules_no_marker():
    """to_json() payload does not include rules_omitted when no rules are present."""
    schema = ar.Schema({"id": ar.String()})
    payload = json.loads(schema.to_json())
    assert "rules_omitted" not in payload


def test_schema_to_json_without_rules_no_warning():
    """to_json() emits no warning when no rules are present."""
    schema = ar.Schema({"id": ar.String()})
    with warnings.catch_warnings():
        warnings.simplefilter("error", UserWarning)
        schema.to_json()  # must not raise


def test_schema_to_json_with_rules_fields_are_preserved():
    """Field definitions are fully serialized even when rules are omitted."""
    schema = ar.Schema(
        {
            "start_date": ar.String(nullable=False),
            "end_date": ar.String(nullable=True),
        },
        rules=[lambda df: []],
    )
    with pytest.warns(UserWarning):
        payload = json.loads(schema.to_json())
    assert set(payload["fields"].keys()) == {"start_date", "end_date"}


def test_schema_from_json_tolerates_rules_omitted_marker():
    """from_json() accepts a payload with rules_omitted: true without error or warning."""
    schema = ar.Schema(
        {"id": ar.String(nullable=False)},
        rules=[lambda df: []],
    )
    with pytest.warns(UserWarning):
        json_str = schema.to_json()

    # Must not raise or warn
    with warnings.catch_warnings():
        warnings.simplefilter("error", UserWarning)
        restored = ar.Schema.from_json(json_str)

    assert "id" in restored.fields
    assert not restored.rules


def test_schema_field_only_roundtrip_with_rules_present():
    """Fields, strict, and unique survive a to_json/from_json round-trip even when rules exist."""
    schema = ar.Schema(
        {
            "id": ar.String(nullable=False),
            "score": ar.Int64(nullable=True),
        },
        strict=True,
        unique=["id"],
        rules=[lambda df: []],
    )
    with pytest.warns(UserWarning):
        restored = ar.Schema.from_json(schema.to_json())

    assert restored.fields["id"] == schema.fields["id"]
    assert restored.fields["score"] == schema.fields["score"]
    assert restored.strict is True
    assert list(restored.unique) == ["id"]
    assert not restored.rules
