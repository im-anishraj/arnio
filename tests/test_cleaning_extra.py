"""Extra validation tests for trim_column_names."""

import pandas as pd
import pytest

import arnio as ar


def test_trim_column_names_duplicate_raises():
    # If trimming leading/trailing spaces produces duplicate names, raise ValueError
    df = pd.DataFrame({"name ": [1, 2], " name": [3, 4]})
    frame = ar.from_pandas(df)

    with pytest.raises(
        ValueError, match="Trimming column names would create duplicates"
    ):
        ar.trim_column_names(frame)


def test_trim_column_names_no_op():
    df = pd.DataFrame({"name": [1, 2], "age": [3, 4]})
    frame = ar.from_pandas(df)

    result = ar.trim_column_names(frame)
    assert result.columns == ["name", "age"]
