"""Extra validation tests for replace_values parameter bounds."""

import pandas as pd
import pytest

import arnio as ar


def test_replace_values_empty_mapping():
    # replace_values should raise ValueError when mapping is empty
    df = pd.DataFrame({"a": [1, 2, 3]})
    frame = ar.from_pandas(df)

    with pytest.raises(ValueError, match="mapping must not be empty"):
        ar.replace_values(frame, {})


def test_replace_values_non_dict_mapping():
    # replace_values should raise TypeError when mapping is not a dict
    df = pd.DataFrame({"a": [1, 2, 3]})
    frame = ar.from_pandas(df)

    with pytest.raises(TypeError, match="mapping must be a dict-like mapping"):
        ar.replace_values(frame, [1, 2, 3])  # type: ignore
