"""Additional tests for CountryCode schema validation."""

import pytest

import arnio as ar


def test_country_code_unique_enforced(tmp_path):
    path = tmp_path / "countries_dup.csv"
    path.write_text("country\nUS\nIN\nUS\n")

    result = ar.validate(
        ar.read_csv(path),
        {"country": ar.CountryCode(nullable=False, unique=True)},
    )

    assert not result.passed
    # unique rule should be reported for both duplicate rows
    issues = [i for i in result.issues if i.rule == "unique"]
    assert len(issues) == 2
    assert [i.row_index for i in issues] == [0, 2]


def test_country_code_rejects_unassigned_iso_codes(tmp_path):
    # Use clearly reserved/unassigned-like codes such as ZZ and AA
    path = tmp_path / "countries_unassigned.csv"
    path.write_text("country\nIN\nUS\nZZ\nAA\n")

    result = ar.validate(
        ar.read_csv(path),
        {"country": ar.CountryCode(nullable=False)},
    )

    assert not result.passed
    # Expect country_code semantic rule for the invalid/unassigned values
    assert {issue.rule for issue in result.issues} == {"country_code"}
    # Rows 2 and 3 should be flagged (0-based indexing)
    assert [issue.row_index for issue in result.issues] == [2, 3]
