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
    def test_compare_schema_method(sample_csv, tmp_path):
    # 1. Base Frame and Matching Frame Setup
    df_base = ar.read_csv(sample_csv)
    df_match = ar.read_csv(sample_csv)

    # 2. Setup Shuffled/Swapped Order Frame
    # (Same columns as sample_csv, but positions are swapped)
    shuffled_path = tmp_path / "shuffled.csv"
    shuffled_path.write_text(
        "age,name,email,active\n"
        "30,Alice,alice@test.com,True\n"
    )
    df_shuffled = ar.read_csv(shuffled_path)

    # 3. Setup Wrong Data Type Frame
    # (Here, 'age' is a decimal/float instead of an integer)
    wrong_dtype_path = tmp_path / "wrong_dtype.csv"
    wrong_dtype_path.write_text(
        "name,age,email,active\n"
        "Alice,30.5,alice@test.com,True\n"
    )
    df_wrong_dtype = ar.read_csv(wrong_dtype_path)

    # 4. Setup Wrong Column Names Frame
    # (Replaced 'active' with an unexpected column name 'status')
    wrong_cols_path = tmp_path / "wrong_cols.csv"
    wrong_cols_path.write_text(
        "name,age,email,status\n"
        "Alice,30,alice@test.com,active\n"
    )
    df_wrong_cols = ar.read_csv(wrong_cols_path)

    # --- ASSERTIONS (Verifying all review requirements) ---

    # Requirement A: Same schema test (Strict vs Non-Strict should both be True)
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
    import pytest
    with pytest.raises(TypeError):
        df_base.compare_schema(["not", "an", "ArFrame", "object"])
