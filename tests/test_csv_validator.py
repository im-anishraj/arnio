
import tempfile

from arnio.csv_validator import detect_csv_issues


def test_inconsistent_columns():

    csv_content = """name,age
Alice,22
Bob,25,Extra
"""

    with tempfile.NamedTemporaryFile(
        mode="w+",
        suffix=".csv",
        delete=False
    ) as temp_file:

        temp_file.write(csv_content)

        temp_file.flush()

        issues = detect_csv_issues(temp_file.name)

    assert len(issues) == 1
    assert issues[0]["issue_type"] == "inconsistent_columns"


def test_clean_csv():

    csv_content = """name,age
Alice,22
Bob,25
"""

    with tempfile.NamedTemporaryFile(
        mode="w+",
        suffix=".csv",
        delete=False
    ) as temp_file:

        temp_file.write(csv_content)

        temp_file.flush()

        issues = detect_csv_issues(temp_file.name)

    assert issues == []


def test_missing_file():

    issues = detect_csv_issues("missing.csv")

    assert issues[0]["issue_type"] == "missing_file"
