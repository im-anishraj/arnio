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


def test_custom_pattern_validation(tmp_path):
    path = tmp_path / "codes.csv"
    path.write_text("code\nAA-123\nbad\n")
    result = ar.validate(
        ar.read_csv(path), {"code": ar.String(pattern=r"[A-Z]{2}-\d{3}")}
    )

    assert not result.passed
    assert result.issues[0].rule == "pattern"
    assert result.issues[0].row_index == 1


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

