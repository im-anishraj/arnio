"""Extra validation tests for round_numeric_columns negative decimals."""

import pandas as pd
import pytest

import arnio as ar


def test_round_numeric_columns_negative_decimals():
    # round_numeric_columns should support negative decimals (e.g. -1 to round to tens)
    df = pd.DataFrame({"value": [12.34, 56.78, 99.99]})
    frame = ar.from_pandas(df)

    # We round to tens (decimals=-1)
    rounded = ar.round_numeric_columns(frame, columns=["value"], decimals=-1)
    res_df = ar.to_pandas(rounded)

    expected = pd.DataFrame({"value": [10.0, 60.0, 100.0]})
    pd.testing.assert_frame_equal(res_df, expected)


def test_round_numeric_columns_invalid_decimals_type():
    df = pd.DataFrame({"value": [12.34]})
    frame = ar.from_pandas(df)

    with pytest.raises(TypeError, match="decimals must be an integer"):
        ar.round_numeric_columns(frame, columns=["value"], decimals="two")  # type: ignore
