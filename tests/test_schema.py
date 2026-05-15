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


def test_date_validation_accepts_valid_dates(tmp_path):
    path = tmp_path / "dates.csv"
    path.write_text("created_at\n2026-05-15\n2024-02-29\n")

    result = ar.validate(
        ar.read_csv(path),
        {"created_at": ar.Date(nullable=False)},
    )

    assert result.passed
    assert result.issue_count == 0


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
