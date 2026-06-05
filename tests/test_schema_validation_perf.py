import pandas as pd

import arnio as ar


def test_validation_issue_fast_create_matches_constructor():
    normal = ar.ValidationIssue(
        column="email",
        rule="pattern",
        message="bad email",
        row_index=1,
        value="x",
        severity="error",
    )

    fast = ar.ValidationIssue._fast_create(
        column="email",
        rule="pattern",
        message="bad email",
        row_index=1,
        value="x",
        severity="error",
    )

    assert fast.column == normal.column
    assert fast.rule == normal.rule
    assert fast.message == normal.message
    assert fast.row_index == normal.row_index
    assert fast.value == normal.value
    assert fast.severity == normal.severity


def test_schema_validate_large_invalid_column():
    df = pd.DataFrame(
        {
            "email": ["bad"] * 1000,
        }
    )

    frame = ar.from_pandas(df)

    schema = ar.Schema({"email": ar.Regex(r"^[^@]+@[^@]+\.[^@]+$")})

    result = schema.validate(frame)

    assert not result.passed
    assert len(result.issues) == 1000
