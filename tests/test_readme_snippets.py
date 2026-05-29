import os
import tempfile

import pandas as pd
import pytest

import arnio as ar


@pytest.fixture
def csv_file():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        f.write("name,age,revenue\n")
        f.write("Alice,30,1000.0\n")
        f.write("  Bob  ,25,2000.0\n")
        f.write("Alice,30,1000.0\n")
        f.write("Charlie,,3000.0\n")
        tmp = f.name
    yield tmp
    os.unlink(tmp)


def test_readme_read_csv(csv_file):
    frame = ar.read_csv(csv_file)
    assert frame.shape[0] == 4
    assert "name" in frame.columns


def test_readme_pipeline(csv_file):
    frame = ar.read_csv(csv_file)
    clean = ar.pipeline(
        frame,
        [
            ("strip_whitespace",),
            ("normalize_case", {"case_type": "lower"}),
            ("drop_nulls",),
            ("drop_duplicates",),
        ],
    )
    df = ar.to_pandas(clean)
    assert df["name"].iloc[0] == "alice"
    assert df.shape[0] == 2


def test_readme_from_dict():
    data = {"name": ["Alice", "Bob"], "age": [25, 30]}
    frame = ar.from_dict(data)
    assert frame.shape == (2, 2)
    assert "name" in frame.columns


def test_readme_select_columns(csv_file):
    frame = ar.read_csv(csv_file)
    selected = ar.select_columns(frame, ["name", "revenue"])
    assert selected.columns == ["name", "revenue"]


def test_readme_scan_csv(csv_file):
    schema = ar.scan_csv(csv_file)
    assert "name" in schema


def test_readme_profile(csv_file):
    frame = ar.read_csv(csv_file)
    result = ar.profile(frame)
    assert result is not None


def test_readme_to_pandas_roundtrip(csv_file):
    frame = ar.read_csv(csv_file)
    df = ar.to_pandas(frame)
    assert isinstance(df, pd.DataFrame)
    assert df.shape[0] == 4


def test_readme_pipeline_dry_run(csv_file):
    frame = ar.read_csv(csv_file)
    ar.pipeline(frame, [("drop_nulls",)], dry_run=True)


def test_readme_pipeline_metadata(csv_file):
    frame = ar.read_csv(csv_file)
    clean, metadata = ar.pipeline(
        frame,
        [("strip_whitespace",), ("drop_duplicates",)],
        return_metadata=True,
    )
    assert "step_timings" in metadata
    assert "applied_steps" in metadata
    assert "row_counts" in metadata


def test_readme_validate(csv_file):
    schema = ar.Schema(
        {
            "name": ar.String(),
            "age": ar.String(),
            "revenue": ar.String(),
        }
    )
    frame = ar.read_csv(csv_file)
    result = ar.validate(frame, schema)
    assert result is not None
    assert hasattr(result, "passed")
    assert hasattr(result, "issues")
