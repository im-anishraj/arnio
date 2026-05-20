"""Extra validation tests for combine_columns edge cases."""

import pandas as pd
import pytest

import arnio as ar


def test_combine_columns_empty_subset() -> None:
    # combine_columns should raise ValueError if subset list is empty
    df = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})
    frame = ar.from_pandas(df)

    with pytest.raises(ValueError, match="subset must contain at least one column"):
        ar.combine_columns(frame, subset=[], output_column="c")


def test_combine_columns_invalid_target_type() -> None:
    df = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})
    frame = ar.from_pandas(df)

    with pytest.raises(ValueError, match="output_column must be a non-empty string"):
        ar.combine_columns(frame, subset=["a", "b"], output_column=123)  # type: ignore
