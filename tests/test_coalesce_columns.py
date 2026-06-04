"""Unit tests for coalesce_columns cleaning utility and pipeline step."""

import pandas as pd
import pytest

import arnio as ar


def test_coalesce_columns_basic() -> None:
    # Test coalesce on pandas DataFrame
    df = pd.DataFrame(
        {
            "a": [None, 2.0, None, 4.0],
            "b": [10.0, None, None, 5.0],
            "c": [20.0, 30.0, 40.0, None],
        }
    )

    # Coalesce checked in order: a, b, c
    res_df = ar.coalesce_columns(df, subset=["a", "b", "c"], output_column="result")

    expected = df.copy()
    expected["result"] = [10.0, 2.0, 40.0, 4.0]

    pd.testing.assert_frame_equal(res_df, expected, check_dtype=False)


def test_coalesce_columns_arframe() -> None:
    # Test coalesce on ArFrame
    df = pd.DataFrame(
        {
            "a": [None, "hello", None],
            "b": ["world", None, None],
        }
    )
    frame = ar.from_pandas(df)
    res_frame = ar.coalesce_columns(frame, subset=["a", "b"], output_column="coalesced")

    assert isinstance(res_frame, ar.ArFrame)
    res_df = ar.to_pandas(res_frame)

    expected = df.copy()
    expected["coalesced"] = ["world", "hello", None]

    pd.testing.assert_frame_equal(res_df, expected, check_dtype=False)


def test_coalesce_columns_pipeline() -> None:
    # Test coalesce as a pipeline step
    df = pd.DataFrame(
        {
            "x": [1.0, None, None],
            "y": [None, 2.0, None],
            "z": [None, None, 3.0],
        }
    )
    frame = ar.from_pandas(df)

    res_frame = ar.pipeline(
        frame,
        [
            ("coalesce_columns", {"subset": ["x", "y", "z"], "output_column": "res"}),
        ],
    )

    res_df = ar.to_pandas(res_frame)
    expected = df.copy()
    expected["res"] = [1.0, 2.0, 3.0]

    pd.testing.assert_frame_equal(res_df, expected, check_dtype=False)


def test_coalesce_columns_validation() -> None:
    df = pd.DataFrame({"a": [1, 2], "b": [3, 4]})
    frame = ar.from_pandas(df)

    # Empty subset
    with pytest.raises(ValueError, match="subset must contain at least one column"):
        ar.coalesce_columns(frame, subset=[])

    # Missing column in subset
    with pytest.raises(KeyError, match="Missing columns"):
        ar.coalesce_columns(frame, subset=["a", "non_existent"])

    # Output column already exists
    with pytest.raises(ValueError, match="already exists"):
        ar.coalesce_columns(frame, subset=["a"], output_column="b")

    # Invalid subset type (string)
    with pytest.raises(
        TypeError, match="subset must be a sequence of column names, not a string"
    ):
        ar.coalesce_columns(frame, subset="not_a_list")  # type: ignore

    # Invalid subset type (unordered set)
    with pytest.raises(TypeError, match="subset must be a sequence of column names"):
        ar.coalesce_columns(frame, subset={"a", "b"})  # type: ignore

    # Invalid output_column type
    with pytest.raises(ValueError, match="must be a non-empty string"):
        ar.coalesce_columns(frame, subset=["a"], output_column="")


def test_coalesce_columns_pandas_index() -> None:
    # Test coalesce on pandas DataFrame with pandas Index for subset
    df = pd.DataFrame(
        {
            "a": [None, 2.0, None],
            "b": [10.0, None, None],
            "c": [20.0, 30.0, 40.0],
        }
    )
    subset_index = pd.Index(["a", "b", "c"])
    res_df = ar.coalesce_columns(df, subset=subset_index, output_column="result")

    expected = df.copy()
    expected["result"] = [10.0, 2.0, 40.0]

    pd.testing.assert_frame_equal(res_df, expected, check_dtype=False)
