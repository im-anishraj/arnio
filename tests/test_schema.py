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
    assert result.bad_rows == [1, 2]
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
        ar.read_csv(path), {"code": ar.String(pattern=r"[A-Z]{2}-\d{3}")}
    )

    assert not result.passed
    assert result.issues[0].rule == "pattern"
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

    assert [issue.row_index for issue in result.issues] == [0, 1, 2, 3, 4, 5]
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
