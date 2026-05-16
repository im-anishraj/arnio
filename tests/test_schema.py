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


def test_validation_result_to_pandas(sample_csv):
    result = ar.validate(
        ar.read_csv(sample_csv),
        {"age": ar.Int64(min=31)},
    )
    df = result.to_pandas()

    assert list(df["rule"]) == ["min", "min"]
    assert list(df["row_index"]) == [0, 1]


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


class TestSchemaToJson:
    def test_roundtrip(self):
        schema = ar.Schema({
            "age": ar.Int64(nullable=False, min=0, max=120),
            "name": ar.String(nullable=True, min_length=1),
            "email": ar.Email(nullable=False),
            "active": ar.Bool(),
        }, strict=True)

        restored = ar.Schema.from_json(schema.to_json())

        assert restored.strict == schema.strict
        for name in schema.fields:
            original = schema.fields[name]
            restored_field = restored.fields[name]
            assert original.dtype == restored_field.dtype
            assert original.nullable == restored_field.nullable
            assert original.min == restored_field.min
            assert original.max == restored_field.max

    def test_roundtrip_minimal(self):
        schema = ar.Schema({"x": ar.Int64()})
        restored = ar.Schema.from_json(schema.to_json(indent=None))
        assert restored.fields["x"].dtype == "int64"

    def test_roundtrip_allowed_set(self):
        schema = ar.Schema({"status": ar.String(allowed={"a", "b", "c"})})
        restored = ar.Schema.from_json(schema.to_json())
        assert restored.fields["status"].allowed == {"a", "b", "c"}

    def test_invalid_json_raises(self):
        import pytest

        with pytest.raises(ValueError, match="Invalid schema JSON"):
            ar.Schema.from_json("not json")

    def test_missing_fields_key_raises(self):
        import pytest

        with pytest.raises(ValueError, match="fields"):
            ar.Schema.from_json('{"strict": false}')


def test_custom_pattern_validation(tmp_path):
    path = tmp_path / "codes.csv"
    path.write_text("code\nAA-123\nbad\n")
    result = ar.validate(
        ar.read_csv(path), {"code": ar.String(pattern=r"[A-Z]{2}-\d{3}")}
    )

    assert not result.passed
    assert result.issues[0].rule == "pattern"
    assert result.issues[0].row_index == 1
