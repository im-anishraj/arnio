"""Tests for schema validation."""

import arnio as ar


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
    ]


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


def test_validation_result_to_markdown_includes_issue_table(sample_csv):
    result = ar.validate(
        ar.read_csv(sample_csv),
        {"age": ar.Int64(min=31), "missing": ar.String()},
    )

    markdown = result.to_markdown()

    assert "- Status: **failed**" in markdown
    assert "- Issues found: 3" in markdown
    assert "| Column | Rule | Row | Value | Message |" in markdown
    assert "| age | min | 1 |" in markdown
    assert (
        "| missing | required_column |  |  | Missing required column: missing |"
        in markdown
    )


def test_validation_result_to_markdown_limits_visible_issues(sample_csv):
    result = ar.validate(ar.read_csv(sample_csv), {"age": ar.Int64(min=31)})

    markdown = result.to_markdown(max_issues=1)

    assert "| age | min | 1 |" in markdown
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
    path.write_text("country\nIND\n1A\nA\nUSA\ngb\nFr\n\n")

    result = ar.validate(
        ar.read_csv(path),
        {"country": ar.CountryCode(nullable=False)},
    )

    assert not result.passed
    assert result.issue_count == 6

    assert [issue.row_index for issue in result.issues] == [1, 2, 3, 4, 5, 6]
    assert {issue.rule for issue in result.issues} == {"country_code"}


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
    assert issues[0].row_index == 0
    assert issues[1].row_index == 2
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


def test_bootstrap_from_report_normal_case():
    report = ar.DataQualityReport(
        row_count=100,
        column_count=4,
        memory_usage=1024,
        duplicate_rows=0,
        duplicate_ratio=0.0,
        columns={
            "id": ar.ColumnProfile(
                name="id",
                dtype="int64",
                semantic_type="identifier",
                row_count=100,
                null_count=0,
                null_ratio=0.0,
                unique_count=100,
                unique_ratio=1.0,
            ),
            "score": ar.ColumnProfile(
                name="score",
                dtype="float32",
                semantic_type="numeric",
                row_count=100,
                null_count=0,
                null_ratio=0.0,
                unique_count=50,
                unique_ratio=0.5,
            ),
            "is_active": ar.ColumnProfile(
                name="is_active",
                dtype="bool",
                semantic_type="boolean",
                row_count=100,
                null_count=0,
                null_ratio=0.0,
                unique_count=2,
                unique_ratio=0.02,
            ),
            "name": ar.ColumnProfile(
                name="name",
                dtype="object",
                semantic_type="text",
                row_count=100,
                null_count=0,
                null_ratio=0.0,
                unique_count=90,
                unique_ratio=0.9,
            ),
        },
    )

    schema = ar.Schema.bootstrap_from_report(report)

    assert isinstance(schema, ar.Schema)
    assert set(schema.fields.keys()) == {"id", "score", "is_active", "name"}
    assert schema.fields["id"].dtype == "integer"
    assert schema.fields["score"].dtype == "float"
    assert schema.fields["is_active"].dtype == "boolean"
    assert schema.fields["name"].dtype == "string"


def test_bootstrap_from_report_nullable_columns():
    report = ar.DataQualityReport(
        row_count=100,
        column_count=3,
        memory_usage=1024,
        duplicate_rows=0,
        duplicate_ratio=0.0,
        columns={
            "no_nulls": ar.ColumnProfile(
                name="no_nulls",
                dtype="int64",
                semantic_type="numeric",
                row_count=100,
                null_count=0,
                null_ratio=0.0,
                unique_count=100,
                unique_ratio=1.0,
            ),
            "some_nulls": ar.ColumnProfile(
                name="some_nulls",
                dtype="int64",
                semantic_type="numeric",
                row_count=100,
                null_count=5,
                null_ratio=0.05,
                unique_count=90,
                unique_ratio=0.9,
            ),
            "all_nulls": ar.ColumnProfile(
                name="all_nulls",
                dtype="float",
                semantic_type="empty",
                row_count=100,
                null_count=100,
                null_ratio=1.0,
                unique_count=0,
                unique_ratio=0.0,
            ),
        },
    )

    schema = ar.Schema.bootstrap_from_report(report)

    assert schema.fields["no_nulls"].nullable is False
    assert schema.fields["some_nulls"].nullable is True
    assert schema.fields["all_nulls"].nullable is True

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


def test_bootstrap_from_report_mixed_string_like_columns():
    report = ar.DataQualityReport(
        row_count=10,
        column_count=2,
        memory_usage=128,
        duplicate_rows=0,
        duplicate_ratio=0.0,
        columns={
            "cat_col": ar.ColumnProfile(
                name="cat_col",
                dtype="category",
                semantic_type="categorical",
                row_count=10,
                null_count=0,
                null_ratio=0.0,
                unique_count=3,
                unique_ratio=0.3,
            ),
            "obj_col": ar.ColumnProfile(
                name="obj_col",
                dtype="object",
                semantic_type="text",
                row_count=10,
                null_count=0,
                null_ratio=0.0,
                unique_count=10,
                unique_ratio=1.0,
            ),
        },
    )

    schema = ar.Schema.bootstrap_from_report(report)

    assert schema.fields["cat_col"].dtype == "string"
    assert schema.fields["obj_col"].dtype == "string"


def test_bootstrap_from_report_empty_malformed_inputs():
    import pytest

    with pytest.raises(TypeError, match="Expected DataQualityReport"):
        ar.Schema.bootstrap_from_report(None)

    with pytest.raises(TypeError, match="Expected DataQualityReport"):
        ar.Schema.bootstrap_from_report({"columns": {}})

    empty_report = ar.DataQualityReport(
        row_count=0,
        column_count=0,
        memory_usage=0,
        duplicate_rows=0,
        duplicate_ratio=0.0,
        columns={},
    )
    with pytest.raises(ValueError, match="empty"):
        ar.Schema.bootstrap_from_report(empty_report)

    report_missing_dtype = ar.DataQualityReport(
        row_count=10,
        column_count=1,
        memory_usage=100,
        duplicate_rows=0,
        duplicate_ratio=0.0,
        columns={"bad_col": {"null_count": 0}},  # type: ignore
    )
    with pytest.raises(ValueError, match="dtype"):
        ar.Schema.bootstrap_from_report(report_missing_dtype)
