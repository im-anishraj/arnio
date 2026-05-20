"""Extra validation tests for combine_columns edge cases."""

import pandas as pd
import pytest

import arnio as ar


def test_combine_columns_empty_subset():
    # combine_columns should raise ValueError if subset list is empty
    df = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})
    frame = ar.from_pandas(df)

    with pytest.raises(ValueError, match="subset must not be empty"):
        ar.combine_columns(frame, subset=[], target="c")


def test_combine_columns_invalid_target_type():
    df = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})
    frame = ar.from_pandas(df)

    with pytest.raises(TypeError, match="target must be a string"):
        ar.combine_columns(frame, subset=["a", "b"], target=123)  # type: ignore
