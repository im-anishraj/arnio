"""Tests for schema validation."""

import pytest

import arnio as ar
from arnio.frame import ArFrame
from arnio.schema import (
    _SEMANTIC_PATTERNS,
    Field,
    Schema,
    _is_safely_convertible_to_dtype,
    validate,
)


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


def test_schema_rejects_non_string_field_name_integer(sample_csv):
    frame = ar.read_csv(sample_csv)
    with pytest.raises(TypeError, match="Schema field names must be strings"):
        ar.validate(frame, {1: ar.String()})


def test_schema_rejects_non_string_field_name_none(sample_csv):
    frame = ar.read_csv(sample_csv)
    with pytest.raises(TypeError, match="Schema field names must be strings"):
        ar.validate(frame, {None: ar.String()})


def test_schema_rejects_non_string_field_name_tuple(sample_csv):
    frame = ar.read_csv(sample_csv)
    with pytest.raises(TypeError, match="Schema field names must be strings"):
        ar.validate(frame, {("a", "b"): ar.String()})


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


def test_string_allowed_is_case_sensitive_by_default(tmp_path):
    path = tmp_path / "status.csv"
    path.write_text("status\nactive\nACTIVE\nActive\n")

    result = ar.validate(
        ar.read_csv(path),
        {"status": ar.String(allowed=["active"])},
    )

    assert not result.passed
    assert result.issue_count == 2
    assert [issue.row_index for issue in result.issues] == [2, 3]


def test_string_case_sensitive_round_trips_through_json():
    schema = ar.Schema({"status": ar.String(allowed=["active"], case_sensitive=False)})

    restored = ar.Schema.from_json(schema.to_json())

    assert restored.fields["status"].case_sensitive is False


def test_string_allowed_supports_case_insensitive_matching(tmp_path):
    path = tmp_path / "status.csv"
    path.write_text("status\nactive\nACTIVE\nActive\ninactive\n")

    result = ar.validate(
        ar.read_csv(path),
        {
            "status": ar.String(
                allowed=["active", "inactive"],
                case_sensitive=False,
            )
        },
    )

    assert result.passed
    assert result.issue_count == 0


def test_string_allowed_case_insensitive_rejects_invalid_values(tmp_path):
    path = tmp_path / "status.csv"
    path.write_text("status\nactive\nACTIVE\npending\n")

    result = ar.validate(
        ar.read_csv(path),
        {
            "status": ar.String(
                allowed=["active"],
                case_sensitive=False,
            )
        },
    )

    assert not result.passed
    assert result.issue_count == 1
    assert result.issues[0].row_index == 3
    assert result.issues[0].rule == "allowed"


def test_string_case_sensitive_must_be_bool():
    with pytest.raises(TypeError, match="case_sensitive must be a bool"):
        ar.String(allowed=["active"], case_sensitive="false")


def test_schema_reports_missing_and_unexpected_columns(sample_csv):
    frame = ar.read_csv(sample_csv)
    schema = ar.Schema({"missing": ar.String()}, strict=True)

    result = ar.validate(frame, schema)
    rules = [issue.rule for issue in result.issues]

    assert "required_column" in rules
    assert "unexpected_column" in rules


# --- ValidationResult constructor validation (regression for #1684) ---


def test_validation_result_rejects_string_row_count():
    with pytest.raises(TypeError, match="row_count"):
        ar.ValidationResult(row_count="1", issue_count=0, issues=[])


def test_validation_result_rejects_negative_row_count():
    with pytest.raises(ValueError, match="row_count"):
        ar.ValidationResult(row_count=-1, issue_count=0, issues=[])


def test_validation_result_rejects_bool_row_count():
    with pytest.raises(TypeError, match="row_count"):
        ar.ValidationResult(row_count=True, issue_count=0, issues=[])


def test_validation_result_rejects_string_issue_count():
    with pytest.raises(TypeError, match="issue_count"):
        ar.ValidationResult(row_count=1, issue_count="0", issues=[])


def test_validation_result_rejects_negative_issue_count():
    with pytest.raises(ValueError, match="issue_count"):
        ar.ValidationResult(row_count=1, issue_count=-1, issues=[])


def test_validation_result_rejects_bool_issue_count():
    with pytest.raises(TypeError, match="issue_count"):
        ar.ValidationResult(row_count=1, issue_count=False, issues=[])


def test_validation_result_rejects_non_list_issues():
    with pytest.raises(TypeError, match="issues"):
        ar.ValidationResult(row_count=1, issue_count=0, issues=None)


def test_validation_result_rejects_string_item_in_issues():
    with pytest.raises(TypeError, match="issues"):
        ar.ValidationResult(row_count=1, issue_count=1, issues=["bad"])


def test_validation_result_rejects_string_bad_rows():
    with pytest.raises(TypeError, match="bad_rows"):
        ar.ValidationResult(row_count=1, issue_count=0, issues=[], bad_rows="abc")


def test_validation_result_rejects_negative_bad_rows_entry():
    with pytest.raises(ValueError, match="bad_rows"):
        ar.ValidationResult(row_count=1, issue_count=0, issues=[], bad_rows=[-1])


def test_validation_result_rejects_non_int_bad_rows_entry():
    with pytest.raises(TypeError, match="bad_rows"):
        ar.ValidationResult(row_count=1, issue_count=0, issues=[], bad_rows=["1"])


def test_validation_result_rejects_mismatched_issue_count():
    issue = ar.ValidationIssue(column="x", rule="dtype", message="bad type")
    with pytest.raises(ValueError, match="issue_count"):
        ar.ValidationResult(row_count=1, issue_count=2, issues=[issue])


def test_validation_result_valid_construction():
    issue = ar.ValidationIssue(column="x", rule="dtype", message="bad type")
    result = ar.ValidationResult(
        row_count=5,
        issue_count=1,
        issues=[issue],
        bad_rows=[0],
    )
    assert result.row_count == 5
    assert result.issue_count == 1
    assert len(result.issues) == 1
    assert result.bad_rows == [0]


# --- end ValidationResult constructor validation ---


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


def test_validation_result_summary_severity_counts_error():
    """severity_counts must be populated for issues with default 'error' severity."""
    result = ar.ValidationResult(
        row_count=3,
        issue_count=2,
        issues=[
            ar.ValidationIssue(
                column="age", rule="min", message="too small", row_index=0
            ),
            ar.ValidationIssue(
                column="name", rule="max", message="too long", row_index=1
            ),
        ],
        bad_rows=[0, 1],
    )
    summary = result.summary()
    assert summary["severity_counts"] == {"error": 2}


def test_validation_result_summary_severity_counts_mixed():
    """severity_counts must track different severity levels."""
    result = ar.ValidationResult(
        row_count=5,
        issue_count=4,
        issues=[
            ar.ValidationIssue(
                column="x", rule="min", message="small", row_index=0, severity="error"
            ),
            ar.ValidationIssue(
                column="x", rule="max", message="large", row_index=1, severity="warning"
            ),
            ar.ValidationIssue(
                column="x",
                rule="required",
                message="missing",
                row_index=2,
                severity="error",
            ),
            ar.ValidationIssue(
                column="x",
                rule="nullable",
                message="null",
                row_index=3,
                severity="warning",
            ),
        ],
        bad_rows=[0, 1, 2, 3],
    )
    summary = result.summary()
    assert summary["severity_counts"] == {"error": 2, "warning": 2}


def test_validation_result_summary_issue_count_field():
    """summary issue_count must match the result's issue_count field."""
    result = ar.ValidationResult(
        row_count=10,
        issue_count=5,
        issues=[
            ar.ValidationIssue(column="a", rule="min", message="bad", row_index=i)
            for i in range(5)
        ],
        bad_rows=list(range(5)),
    )
    summary = result.summary()
    assert summary["issue_count"] == 5
    assert summary["passed"] is False


def test_validation_result_summary_bad_row_count():
    """summary bad_row_count must equal len(bad_rows)."""
    result = ar.ValidationResult(
        row_count=7,
        issue_count=3,
        issues=[
            ar.ValidationIssue(column="a", rule="min", message="bad", row_index=i)
            for i in [1, 3, 5]
        ],
        bad_rows=[1, 3, 5],
    )
    summary = result.summary()
    assert summary["bad_row_count"] == 3


def test_validation_result_summary_no_issues_severity_counts_empty():
    """When there are no issues, severity_counts must be an empty dict."""
    result = ar.ValidationResult(row_count=3, issue_count=0, issues=[], bad_rows=[])
    summary = result.summary()
    assert summary["severity_counts"] == {}


def test_schema_diff_summary_differences_by_change():
    """SchemaDiff.summary() differences_by_change must aggregate by change kind."""
    diff = ar.SchemaDiff(
        [
            ar.SchemaDiffEntry(
                change="added_column",
                column="new_col",
            ),
            ar.SchemaDiffEntry(
                change="changed_field",
                column="id",
            ),
            ar.SchemaDiffEntry(
                change="added_column",
                column="another_col",
            ),
        ],
    )
    summary = diff.summary()
    assert summary["differences_by_change"] == {"added_column": 2, "changed_field": 1}


def test_schema_diff_summary_differences_by_column():
    """SchemaDiff.summary() differences_by_column must aggregate by column name."""
    diff = ar.SchemaDiff(
        [
            ar.SchemaDiffEntry(
                change="removed_column",
                column="x",
            ),
            ar.SchemaDiffEntry(
                change="changed_type",
                column="x",
            ),
            ar.SchemaDiffEntry(
                change="added_column",
                column="y",
            ),
        ],
    )
    summary = diff.summary()
    assert summary["differences_by_column"] == {"x": 2, "y": 1}


def test_schema_diff_summary_no_differences():
    """SchemaDiff.summary() with no differences must return empty aggregations."""
    diff = ar.SchemaDiff([])
    summary = diff.summary()
    assert summary["changed"] is False
    assert summary["difference_count"] == 0
    assert summary["differences_by_change"] == {}
    assert summary["differences_by_column"] == {}


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


def _make_failing_result() -> ar.ValidationResult:
    """Helper: a ValidationResult with one issue, for redact_values type tests."""
    return ar.ValidationResult(
        row_count=1,
        issue_count=1,
        issues=[
            ar.ValidationIssue(
                column="col",
                rule="min",
                row_index=1,
                value=0,
                message="below minimum",
            )
        ],
        bad_rows=[1],
    )


def test_to_markdown_rejects_non_bool_redact_values():
    """to_markdown() must raise TypeError for any non-bool redact_values argument."""
    result = _make_failing_result()

    for invalid in ("false", "true", "", 0, 1, None, [], {}):
        try:
            result.to_markdown(redact_values=invalid)  # type: ignore[arg-type]
        except TypeError as exc:
            assert "redact_values must be a bool" in str(
                exc
            ), f"Wrong error message for {invalid!r}: {exc}"
        else:
            raise AssertionError(
                f"Expected TypeError for redact_values={invalid!r}, but no exception was raised"
            )


def test_to_markdown_accepts_bool_redact_values():
    """to_markdown() must not raise for redact_values=True or redact_values=False."""
    result = _make_failing_result()

    md_false = result.to_markdown(redact_values=False)
    md_true = result.to_markdown(redact_values=True)

    assert "0" in md_false, "Raw value should appear when redact_values=False"
    assert "[REDACTED]" in md_true, "[REDACTED] should appear when redact_values=True"
    assert "0" not in md_true.split("| Value |")[-1] or "[REDACTED]" in md_true


def test_unique_constraint_detects_duplicates(tmp_path):
    path = tmp_path / "unique.csv"
    path.write_text("id,value\n1,100\n2,200\n1,300\n3,400\n")
    result = ar.validate(ar.read_csv(path), {"id": ar.Int64(unique=True)})
    assert not result.passed
    assert any(
        issue.rule == "unique" and issue.column == "id" for issue in result.issues
    )


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


def test_validation_result_to_markdown_for_success(sample_csv):
    result = ar.validate(ar.read_csv(sample_csv), {"age": ar.Int64()})

    markdown = result.to_markdown()

    assert "## Validation Report" in markdown
    assert "- Status: **passed**" in markdown
    assert "- Issues found: 0" in markdown
    assert "| Column | Rule | Row | Value | Message |" not in markdown


def test_validation_result_to_markdown_includes_issue_table(sample_csv):
    result = ar.validate(
        ar.read_csv(sample_csv),
        {"age": ar.Int64(min=31), "missing": ar.String()},
    )

    markdown = result.to_markdown()

    assert "- Status: **failed**" in markdown
    assert "- Issues found: 3" in markdown
    assert "| Column | Rule | Row | Value | Message |" in markdown
    assert "| age | min | 0 |" in markdown
    assert (
        "| missing | required_column |  |  | Missing required column: missing |"
        in markdown
    )


def test_validation_result_to_markdown_limits_visible_issues(sample_csv):
    result = ar.validate(ar.read_csv(sample_csv), {"age": ar.Int64(min=31)})

    markdown = result.to_markdown(max_issues=1)

    assert "| age | min | 0 |" in markdown
    assert "| age | min | 1 |" not in markdown
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

    markdown = result.to_markdown()

    assert "notes\\|raw" in markdown
    assert "left\\|right<br>next" in markdown
    assert "Expected one\\|two<br>lines" in markdown


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


def test_custom_pattern_validation(tmp_path):
    path = tmp_path / "codes.csv"
    path.write_text("code\nAA-123\nbad\n")
    result = ar.validate(
        ar.read_csv(path), {"code": ar.String(pattern=r"^[A-Z]{2}-\d{3}$")}
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


def test_compare_schema_method(sample_csv, tmp_path):
    # 1. Base Frame and Matching Frame Setup
    df_base = ar.read_csv(sample_csv)
    df_match = ar.read_csv(sample_csv)

    # 2. Setup Shuffled/Swapped Order Frame
    shuffled_path = tmp_path / "shuffled.csv"
    shuffled_path.write_text("age,name,email,active\n" "30,Alice,alice@test.com,True\n")
    df_shuffled = ar.read_csv(shuffled_path)

    # 3. Setup Wrong Data Type Frame
    wrong_dtype_path = tmp_path / "wrong_dtype.csv"
    wrong_dtype_path.write_text(
        "name,age,email,active\n" "Alice,30.5,alice@test.com,True\n"
    )
    df_wrong_dtype = ar.read_csv(wrong_dtype_path)

    # 4. Setup Wrong Column Names Frame
    wrong_cols_path = tmp_path / "wrong_cols.csv"
    wrong_cols_path.write_text(
        "name,age,email,status\n" "Alice,30,alice@test.com,active\n"
    )
    df_wrong_cols = ar.read_csv(wrong_cols_path)

    # --- ASSERTIONS ---
    # Requirement A: Same schema test
    assert df_base.compare_schema(df_match, strict=True) is True
    assert df_base.compare_schema(df_match, strict=False) is True

    # Requirement B: Strict vs Non-Strict order behavior tracking
    assert df_base.compare_schema(df_shuffled, strict=True) is False
    assert df_base.compare_schema(df_shuffled, strict=False) is True

    # Requirement C: Data type mismatch validation
    assert df_base.compare_schema(df_wrong_dtype, strict=False) is False

    # Requirement D: Column naming structural mismatch validation
    assert df_base.compare_schema(df_wrong_cols, strict=False) is False

    # Requirement E: Invalid object class input safe rejection handling
    with pytest.raises(TypeError):
        df_base.compare_schema(["not", "an", "ArFrame", "object"])


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
    assert result.issues[0].row_index == 0


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
    assert result.issues[0].row_index == 1


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
    assert result.issues[0].row_index == 0


def test_compare_schema_matching(sample_csv):
    """Test that identical schemas match under both strict and non-strict modes."""
    df_base = ar.read_csv(sample_csv)
    df_match = ar.read_csv(sample_csv)

    assert df_base.compare_schema(df_match, strict=True) is True
    assert df_base.compare_schema(df_match, strict=False) is True


def test_compare_schema_order_difference(sample_csv, tmp_path):
    """Test that column order differences fail strict mode but pass non-strict mode."""
    df_base = ar.read_csv(sample_csv)

    shuffled_path = tmp_path / "shuffled.csv"
    shuffled_path.write_text("age,name,email,active\n" "30,Alice,alice@test.com,True\n")
    df_shuffled = ar.read_csv(shuffled_path)

    assert df_base.compare_schema(df_shuffled, strict=True) is False
    assert df_base.compare_schema(df_shuffled, strict=False) is True


def test_compare_schema_dtype_mismatch(sample_csv, tmp_path):
    """Test that schema matching fails when column data types mismatch."""
    df_base = ar.read_csv(sample_csv)

    wrong_dtype_path = tmp_path / "wrong_dtype.csv"
    wrong_dtype_path.write_text(
        "name,age,email,active\n" "Alice,30.5,alice@test.com,True\n"
    )
    df_wrong_dtype = ar.read_csv(wrong_dtype_path)

    assert df_base.compare_schema(df_wrong_dtype, strict=False) is False


def test_compare_schema_column_mismatch(sample_csv, tmp_path):
    """Test that schema matching fails when column names do not match."""
    df_base = ar.read_csv(sample_csv)

    wrong_cols_path = tmp_path / "wrong_cols.csv"
    wrong_cols_path.write_text(
        "name,age,email,status\n" "Alice,30,alice@test.com,active\n"
    )
    df_wrong_cols = ar.read_csv(wrong_cols_path)

    assert df_base.compare_schema(df_wrong_cols, strict=False) is False


def test_compare_schema_invalid_input(sample_csv):
    """Test that passing a non-ArFrame object correctly raises a TypeError."""
    df_base = ar.read_csv(sample_csv)

    with pytest.raises(TypeError):
        ar.Date(min=123)
    with pytest.raises(TypeError):
        ar.Date(max=45.6)


def test_date_bounds_only_applied_after_format_check(tmp_path):
    """Invalid date strings should report format errors, not spurious bound errors."""
    path = tmp_path / "bad_and_oob.csv"
    path.write_text("dt\n2024-06-15\nnot-a-date\n2023-01-01\n")

    result = ar.validate(
        ar.read_csv(path),
        {"dt": ar.Date(min="2024-01-01")},
    )

    rules = {issue.rule for issue in result.issues}
    assert "date" in rules  # format error for "not-a-date"
    assert "min" in rules  # bound error for 2023-01-01
    # "not-a-date" must NOT also appear as a min violation
    min_issues = [i for i in result.issues if i.rule == "min"]
    assert all(i.value != "not-a-date" for i in min_issues)


def test_date_nullable_values_skip_bounds_check(tmp_path):
    path = tmp_path / "nullable_dates.csv"
    path.write_text("dt\n2024-06-15\n\n")

    result = ar.validate(
        ar.read_csv(path),
        {"dt": ar.Date(min="2024-01-01", max="2024-12-31", nullable=True)},
    )

    assert result.passed


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
    ar.register_validator("positive_pass", lambda v: v > 0)
    path = tmp_path / "scores.csv"
    path.write_text("score\n1\n5\n100\n")
    result = ar.validate(ar.read_csv(path), {"score": ar.Custom("positive_pass")})
    assert result.passed


def test_register_validator_and_custom_field_fails(tmp_path):
    ar.register_validator("positive_fail", lambda v: v > 0)
    path = tmp_path / "scores.csv"
    path.write_text("score\n1\n-5\n0\n")
    result = ar.validate(ar.read_csv(path), {"score": ar.Custom("positive_fail")})
    assert not result.passed
    assert result.issues[0].rule == "custom"
    assert result.issues[0].row_index == 2


def test_custom_field_respects_nullable(tmp_path):
    import pandas as pd

    ar.register_validator("positive_nullable", lambda v: v > 0)
    df = pd.DataFrame({"score": [1, None, 5]})
    frame = ar.from_pandas(df)
    result = ar.validate(
        frame, {"score": ar.Custom("positive_nullable", nullable=False)}
    )
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


def test_custom_validator_exceptions_include_schema_context(tmp_path):
    def broken_validator(value):
        raise RuntimeError("validator exploded")

    ar.register_validator("broken", broken_validator)

    path = tmp_path / "scores.csv"
    path.write_text("score\n1\n")

    with pytest.raises(ar.ArnioError) as exc:
        ar.validate(
            ar.read_csv(path),
            {"score": ar.Custom("broken")},
        )

    message = str(exc.value)
    assert "broken" in message
    assert "score" in message
    assert "validator exploded" in message
    assert isinstance(exc.value.__cause__, RuntimeError)


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
    path.write_text("currency\nUSD\nEUR\nINR\nJPY\nXXX\n")

    result = ar.validate(
        ar.read_csv(path),
        {"currency": ar.CurrencyCode(nullable=False)},
    )

    assert result.passed
    assert result.issue_count == 0


def test_currency_code_invalid(tmp_path):
    path = tmp_path / "bad_currencies.csv"
    # We add a dummy column so the empty currency row isn't skipped as a blank line
    path.write_text(
        "currency,dummy\nUS,1\nUSDD,2\nusd,3\nUS1,4\nEur,5\n,6\nZZZ,7\nABC,8\n"
    )

    result = ar.validate(
        ar.read_csv(path),
        {"currency": ar.CurrencyCode(nullable=False)},
    )

    assert not result.passed
    assert result.issue_count == 8

    assert sorted([issue.row_index for issue in result.issues]) == [
        1,
        2,
        3,
        4,
        5,
        6,
        7,
        8,
    ]

    rules = {issue.rule for issue in result.issues}
    assert "currency_code" in rules
    assert "nullable" in rules


def test_currency_code_override(tmp_path):
    path = tmp_path / "custom_currencies.csv"
    path.write_text("currency\nUSD\nZZZ\n")

    result = ar.validate(
        ar.read_csv(path),
        {"currency": ar.CurrencyCode(nullable=False, allowed={"USD", "ZZZ"})},
    )
    assert result.passed
    assert result.issue_count == 0

    result_default = ar.validate(
        ar.read_csv(path),
        {"currency": ar.CurrencyCode(nullable=False)},
    )
    assert not result_default.passed
    assert result_default.issue_count == 1
    assert result_default.issues[0].value == "ZZZ"


def test_currency_code_rejects_bare_string_allowed():
    with pytest.raises(TypeError):
        ar.CurrencyCode(allowed="USD")


def test_currency_code_accepts_valid_allowed_sequence():
    field = ar.CurrencyCode(allowed=["USD", "EUR"])

    assert field.allowed == {"USD", "EUR"}


def test_currency_code_rejects_non_string_allowed_values():
    with pytest.raises(TypeError):
        ar.CurrencyCode(allowed=["USD", 123])


def test_currency_code_validation_respects_case_insensitive_field(tmp_path):
    path = tmp_path / "mixed_case_currencies.csv"
    path.write_text("currency\nusd\nEur\ninr\n")

    result = ar.validate(
        ar.read_csv(path),
        {
            "currency": ar.Field(
                dtype="string",
                semantic="currency_code",
                case_sensitive=False,
                nullable=False,
            )
        },
    )

    assert result.passed
    assert result.issue_count == 0


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


def test_required_if_treats_blank_strings_as_missing():
    df = pd.DataFrame(
        {
            "user_type": [
                "international",
                "international",
                "local",
            ],
            "country": [
                "",
                "   ",
                "",
            ],
        }
    )

    schema = ar.Schema(
        {
            "user_type": ar.String(nullable=False),
            "country": ar.String(
                nullable=True,
                required_if=("user_type", "international"),
            ),
        }
    )

    result = ar.validate(ar.from_pandas(df), schema)

    assert result.issue_count == 2

    for issue in result.issues:
        assert issue.column == "country"
        assert issue.rule == "required_if"


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


def test_url_allowed_schemes_trims_whitespace():
    ar.URL(allowed_schemes=[" https ", " ftp "])


def test_url_allowed_schemes_accepts_tuple():
    ar.URL(allowed_schemes=("https", "ftp"))


def test_url_allowed_schemes_accepts_set():
    ar.URL(allowed_schemes={"https", "ftp"})


def test_url_allowed_schemes_rejects_bare_string():
    with pytest.raises(TypeError, match="allowed_schemes must be a sequence"):
        ar.URL(allowed_schemes="https")


def test_url_allowed_schemes_rejects_bare_bytes():
    with pytest.raises(TypeError, match="allowed_schemes must be a sequence"):
        ar.URL(allowed_schemes=b"https")


@pytest.mark.parametrize(
    "scheme",
    ["https://", "https ftp", "1http"],
)
def test_url_allowed_schemes_reject_invalid_scheme_names(scheme):
    with pytest.raises(
        ValueError,
        match="allowed_schemes must contain URL scheme names",
    ):
        ar.URL(allowed_schemes=[scheme])


def test_url_allowed_schemes_accept_valid_scheme_characters():
    ar.URL(allowed_schemes=["git+ssh", "custom.scheme"])


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


class TestIsSafelyConvertibleToDtype:
    def test_id_column_rejects_leading_zeros(self):
        series = pd.Series(["001", "002", "003"])
        assert _is_safely_convertible_to_dtype(series, "int64", "id") is False

    def test_user_id_column_rejects_leading_zeros(self):
        series = pd.Series(["0001", "0002"])
        assert _is_safely_convertible_to_dtype(series, "int64", "user_id") is False

    def test_uuid_column_rejects_leading_zeros(self):
        series = pd.Series(["0123", "0456"])
        assert _is_safely_convertible_to_dtype(series, "int64", "uuid") is False

    def test_zip_column_rejects_leading_zeros(self):
        series = pd.Series(["01234", "02345"])
        assert _is_safely_convertible_to_dtype(series, "int64", "zip") is False

    def test_valid_int64_conversion(self):
        series = pd.Series(["1", "2", "3"])
        assert _is_safely_convertible_to_dtype(series, "int64", "count") is True

    def test_negative_int64_conversion(self):
        series = pd.Series(["-1", "2", "3"])
        assert _is_safely_convertible_to_dtype(series, "int64", "delta") is True

    def test_float64_conversion(self):
        series = pd.Series(["1.5", "2.5", "3.0"])
        assert _is_safely_convertible_to_dtype(series, "float64", "price") is True

    def test_invalid_string_for_int64(self):
        series = pd.Series(["abc", "def"])
        assert _is_safely_convertible_to_dtype(series, "int64", "data") is False

    def test_empty_series_returns_false(self):
        series = pd.Series([], dtype="string")
        assert _is_safely_convertible_to_dtype(series, "int64", "col") is False

    def test_all_null_series_returns_false(self):
        series = pd.Series([None, None])
        assert _is_safely_convertible_to_dtype(series, "int64", "col") is False


def test_int64_rejects_string_min():
    with pytest.raises(TypeError, match="min must be numeric or None"):
        ar.Int64(min="a")


def test_int64_rejects_string_max():
    with pytest.raises(TypeError, match="max must be numeric or None"):
        ar.Int64(max="z")


def test_int64_rejects_bool_min():
    with pytest.raises(TypeError, match="min must be numeric or None"):
        ar.Int64(min=True)


def test_int64_rejects_bool_max():
    with pytest.raises(TypeError, match="max must be numeric or None"):
        ar.Int64(max=False)


def test_int64_accepts_valid_numeric_bounds():
    assert ar.Int64(min=0, max=10) is not None


def test_int64_accepts_float_bounds():
    assert ar.Int64(min=0.5, max=9.9) is not None


def test_int64_accepts_none_bounds():
    assert ar.Int64(min=None, max=None) is not None


def test_int64_rejects_string_min_with_valid_max():
    with pytest.raises(TypeError, match="min must be numeric or None"):
        ar.Int64(min="a", max=1)


def test_int64_rejects_valid_min_with_string_max():
    with pytest.raises(TypeError, match="max must be numeric or None"):
        ar.Int64(min=1, max="z")


def test_int64_rejects_bool_pair():
    with pytest.raises(TypeError, match="min must be numeric or None"):
        ar.Int64(min=True, max=False)


def test_float64_rejects_string_min_with_valid_max():
    with pytest.raises(TypeError, match="min must be numeric or None"):
        ar.Float64(min="a", max=1.0)


def test_float64_rejects_bool_pair():
    with pytest.raises(TypeError, match="min must be numeric or None"):
        ar.Float64(min=True, max=False)


def test_validation_issue_accepts_valid_severities():
    error_issue = ar.ValidationIssue(
        column="age", rule="min", message="Too small", severity="error"
    )
    warning_issue = ar.ValidationIssue(
        column="age", rule="min", message="Too small", severity="warning"
    )

    assert error_issue.severity == "error"
    assert warning_issue.severity == "warning"


def test_validation_issue_rejects_invalid_severity_typo():
    with pytest.raises(ValueError, match="severity must be 'error' or 'warning'"):
        ar.ValidationIssue(
            column="score", rule="custom", message="bad", severity="erorr"
        )


def test_custom_rule_with_invalid_severity_fails_validation_execution():
    def bad_custom_rule(df):
        return [
            ar.ValidationIssue(column="x", rule="demo", message="bad", severity="erorr")
        ]

    frame = ar.from_pandas(pd.DataFrame({"x": [1]}))
    schema = ar.Schema({"x": ar.Field()}, rules=[bad_custom_rule])

    with pytest.raises(ValueError, match="severity must be 'error' or 'warning'"):
        schema.validate(frame)


def test_field_dtype_rejects_non_string():
    with pytest.raises(TypeError, match="dtype must be a str or None"):
        ar.Field(dtype=123)


def test_field_pattern_rejects_non_string():
    with pytest.raises(TypeError, match="pattern must be a str or None"):
        ar.Field(pattern=123)


def test_field_pattern_rejects_invalid_regex():
    with pytest.raises(ValueError, match="not a valid regular expression"):
        ar.Field(pattern="[unclosed")


def test_field_allowed_rejects_bare_string():
    with pytest.raises(TypeError, match="allowed must be a list, tuple, or set"):
        ar.Field(allowed="abc")


def test_field_max_length_rejects_non_int():
    with pytest.raises(TypeError, match="max_length must be an int or None"):
        ar.Field(max_length="x")


def test_field_min_length_rejects_non_int():
    with pytest.raises(TypeError, match="min_length must be an int or None"):
        ar.Field(min_length="x")


def test_field_min_length_rejects_negative():
    with pytest.raises(ValueError, match="min_length must be >= 0"):
        ar.Field(min_length=-1)


def test_field_max_length_rejects_negative():
    with pytest.raises(ValueError, match="max_length must be >= 0"):
        ar.Field(max_length=-1)


def test_field_min_length_exceeds_max_length():
    with pytest.raises(ValueError, match="min_length.*must be <= max_length"):
        ar.Field(min_length=10, max_length=3)


def test_field_valid_direct_construction():
    f = ar.Field(
        dtype="string", pattern=r"\d+", allowed=["a", "b"], min_length=1, max_length=5
    )
    assert f.pattern == r"\d+"


def test_field_allowed_rejects_dict():
    with pytest.raises(TypeError, match="allowed must be a list, tuple, or set"):
        ar.Field(allowed={"a": 1})


def test_field_allowed_rejects_generator():
    with pytest.raises(TypeError, match="allowed must be a list, tuple, or set"):
        ar.Field(allowed=(x for x in ["a"]))


def test_field_allowed_rejects_bytes():
    with pytest.raises(TypeError, match="allowed must be a list, tuple, or set"):
        ar.Field(allowed=b"abc")


def test_custom_field_required_if_validation_passes_when_condition_matches(tmp_path):
    ar.register_validator("positive_req", lambda v: v > 0)

    path = tmp_path / "custom_conditional_pass.csv"
    path.write_text("status,score\n" "active,10\n" "inactive,\n")
    frame = ar.read_csv(path)

    schema = ar.Schema(
        {
            "status": ar.String(nullable=False),
            "score": ar.Custom(
                "positive_req", nullable=True, required_if=("status", "active")
            ),
        }
    )

    result = schema.validate(frame)
    assert result.passed
    assert result.issue_count == 0


def test_custom_field_required_if_validation_fails_when_condition_matches(tmp_path):
    ar.register_validator("positive_req", lambda v: v > 0)

    path = tmp_path / "custom_conditional_fail.csv"
    path.write_text("status,score\n" "active,\n" "inactive,5\n")
    frame = ar.read_csv(path)

    schema = ar.Schema(
        {
            "status": ar.String(nullable=False),
            "score": ar.Custom(
                "positive_req", nullable=True, required_if=("status", "active")
            ),
        }
    )

    result = schema.validate(frame)
    assert not result.passed
    assert result.issue_count == 1
    assert result.issues[0].rule == "required_if"
    assert result.issues[0].column == "score"
    assert result.issues[0].row_index == 1


def test_custom_field_required_if_validation_ignores_non_matching_conditions(tmp_path):
    ar.register_validator("positive_req", lambda v: v > 0)

    path = tmp_path / "custom_conditional_ignore.csv"
    path.write_text("status,score\n" "pending,\n" "inactive,\n")
    frame = ar.read_csv(path)

    schema = ar.Schema(
        {
            "status": ar.String(nullable=False),
            "score": ar.Custom(
                "positive_req", nullable=True, required_if=("status", "active")
            ),
        }
    )

    result = schema.validate(frame)
    assert result.passed
    assert result.issue_count == 0


def test_custom_field_required_if_enforces_rule_logic_when_matched(tmp_path):
    ar.register_validator("positive_req", lambda v: v > 0)

    path = tmp_path / "custom_conditional_rule_fail.csv"
    path.write_text("status,score\n" "active,-5\n")
    frame = ar.read_csv(path)

    schema = ar.Schema(
        {
            "status": ar.String(nullable=False),
            "score": ar.Custom(
                "positive_req", nullable=True, required_if=("status", "active")
            ),
        }
    )

    result = schema.validate(frame)
    assert not result.passed
    assert result.issue_count == 1
    assert result.issues[0].rule == "custom"
    assert result.issues[0].column == "score"
    assert result.issues[0].row_index == 1


def test_custom_field_json_roundtrip_preserves_required_if():
    ar.register_validator("positive_req_json", lambda v: v > 0)

    schema = ar.Schema(
        fields={
            "id": ar.String(nullable=False),
            "score": ar.Custom(
                "positive_req_json", nullable=True, required_if=("id", "A1")
            ),
        }
    )

    restored = ar.Schema.from_json(schema.to_json())
    assert restored == schema


def test_unknown_semantic_severity_preservation():
    frame = ar.from_dict({"x": ["abc"]})
    unknown_schema = ar.Schema({"x": ar.Field(semantic="unknown", severity="warning")})

    result = ar.validate(frame, unknown_schema)
    assert not result.issues[0].passed if hasattr(result.issues[0], "passed") else True
    assert len(result.issues) == 1
    assert result.issues[0].rule == "semantic"
    assert result.issues[0].severity == "warning"


def test_missing_custom_validator_severity_preservation():
    frame = ar.from_dict({"x": ["abc"]})
    missing_custom_schema = ar.Schema(
        {"x": ar.Field(semantic="custom:missing", severity="warning")}
    )

    result = ar.validate(frame, missing_custom_schema)
    for issue in result.issues:
        if issue.rule == "custom":
            assert issue.severity == "warning"


def test_validate_max_errors_zero_invalid_data():
    frame = ar.from_pandas(pd.DataFrame({"age": ["not-an-int"]}))
    schema = ar.Schema({"age": ar.Int64()})

    with pytest.raises(ValueError, match="max_errors must be >= 1"):
        ar.validate(frame, schema, max_errors=0)


def test_validate_max_errors_zero_missing_columns():
    frame = ar.from_pandas(pd.DataFrame({"name": ["Alice"]}))
    schema = ar.Schema({"age": ar.Int64()})

    with pytest.raises(ValueError, match="max_errors must be >= 1"):
        ar.validate(frame, schema, max_errors=0)


def test_validate_max_errors_zero_strict_schema():
    frame = ar.from_pandas(pd.DataFrame({"age": [25], "extra": ["unexpected"]}))
    schema = ar.Schema({"age": ar.Int64()}, strict=True)

    with pytest.raises(ValueError, match="max_errors must be >= 1"):
        ar.validate(frame, schema, max_errors=0)


def test_validate_max_errors_zero_valid_data():
    frame = ar.from_pandas(pd.DataFrame({"age": [25]}))
    schema = ar.Schema({"age": ar.Int64()})

    with pytest.raises(ValueError, match="max_errors must be >= 1"):
        ar.validate(frame, schema, max_errors=0)


def test_url_uppercase_scheme_accepted_with_lowercase_allowed(tmp_path):
    path = tmp_path / "urls.csv"
    path.write_text("url\nHTTPS://example.com\n")
    result = ar.validate(ar.read_csv(path), {"url": ar.URL(allowed_schemes=["https"])})
    assert result.passed


def test_url_mixed_case_scheme_accepted(tmp_path):
    path = tmp_path / "urls.csv"
    path.write_text("url\nHttps://example.com\n")
    result = ar.validate(ar.read_csv(path), {"url": ar.URL(allowed_schemes=["https"])})
    assert result.passed


def test_url_uppercase_allowed_scheme_matches_lowercase_url(tmp_path):
    path = tmp_path / "urls.csv"
    path.write_text("url\nhttps://example.com\n")
    result = ar.validate(ar.read_csv(path), {"url": ar.URL(allowed_schemes=["HTTPS"])})
    assert result.passed


def test_url_uppercase_scheme_rejected_when_not_in_allowed(tmp_path):
    path = tmp_path / "urls.csv"
    path.write_text("url\nFTP://files.example.com\n")
    result = ar.validate(ar.read_csv(path), {"url": ar.URL(allowed_schemes=["https"])})
    assert not result.passed


def test_url_mixed_case_allowed_scheme_and_mixed_case_url(tmp_path):
    path = tmp_path / "urls.csv"
    path.write_text("url\nHTTPS://example.com\nHttps://test.org\nhttps://lower.com\n")
    result = ar.validate(ar.read_csv(path), {"url": ar.URL(allowed_schemes=["HTTPS"])})
    assert result.passed
