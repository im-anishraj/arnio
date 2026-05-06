"""
Test fixtures for arnio.
"""

import pytest


@pytest.fixture
def sample_csv(tmp_path):
    """Create a basic CSV file for testing."""
    csv_content = "name,age,email,active\nAlice,30,alice@test.com,true\nBob,25,bob@test.com,false\nCharlie,35,charlie@test.com,true\n"
    path = tmp_path / "sample.csv"
    path.write_text(csv_content)
    return str(path)


@pytest.fixture
def csv_with_nulls(tmp_path):
    """CSV with empty/null values."""
    csv_content = "name,age,score\nAlice,30,95.5\n,25,\nCharlie,,88.0\nDiana,28,92.3\n"
    path = tmp_path / "nulls.csv"
    path.write_text(csv_content)
    return str(path)


@pytest.fixture
def csv_with_duplicates(tmp_path):
    """CSV with duplicate rows."""
    csv_content = "name,age\nAlice,30\nBob,25\nAlice,30\nCharlie,35\nBob,25\n"
    path = tmp_path / "dupes.csv"
    path.write_text(csv_content)
    return str(path)


@pytest.fixture
def csv_with_whitespace(tmp_path):
    """CSV with whitespace in values."""
    csv_content = (
        "name,city\n  Alice  , New York  \n Bob ,  London\n  Charlie ,Tokyo  \n"
    )
    path = tmp_path / "whitespace.csv"
    path.write_text(csv_content)
    return str(path)


@pytest.fixture
def csv_no_header(tmp_path):
    """CSV without header."""
    csv_content = "Alice,30,alice@test.com\nBob,25,bob@test.com\n"
    path = tmp_path / "noheader.csv"
    path.write_text(csv_content)
    return str(path)


@pytest.fixture
def large_csv(tmp_path):
    """Generate a larger CSV for performance sanity checks."""
    lines = ["id,value,label"]
    for i in range(1000):
        lines.append(f"{i},{i * 1.5},item_{i}")
    path = tmp_path / "large.csv"
    path.write_text("\n".join(lines))
    return str(path)
