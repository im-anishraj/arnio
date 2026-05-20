"""Unit tests for normalize_boolean_values cleaning utility and pipeline step."""

import pandas as pd
import pytest

import arnio as ar


def test_normalize_boolean_values_default() -> None:
    # Test default mappings case-insensitively and with whitespace
    df = pd.DataFrame(
        {
            "a": [" Yes ", "no", "Y", "N", "True", "False", "1", "0", "other"],
        }
    )

    res_df = ar.normalize_boolean_values(df)

    expected = pd.DataFrame(
        {
            "a": [True, False, True, False, True, False, True, False, "other"],
        }
    )

    pd.testing.assert_frame_equal(res_df, expected, check_dtype=False)


def test_normalize_boolean_values_custom() -> None:
    # Test custom mappings
    df = pd.DataFrame(
        {
            "a": ["oui", "non", "maybe"],
        }
    )

    res_df = ar.normalize_boolean_values(
        df,
        true_values=["oui"],
        false_values=["non"],
    )

    expected = pd.DataFrame(
        {
            "a": [True, False, "maybe"],
        }
    )

    pd.testing.assert_frame_equal(res_df, expected, check_dtype=False)


def test_normalize_boolean_values_subset() -> None:
    # Test subset parameter
    df = pd.DataFrame(
        {
            "a": ["yes", "no"],
            "b": ["yes", "no"],
        }
    )

    res_df = ar.normalize_boolean_values(df, subset=["a"])

    expected = pd.DataFrame(
        {
            "a": [True, False],
            "b": ["yes", "no"],
        }
    )

    pd.testing.assert_frame_equal(res_df, expected, check_dtype=False)


def test_normalize_boolean_values_pipeline() -> None:
    # Test pipeline integration
    df = pd.DataFrame(
        {
            "a": ["yes", "no"],
        }
    )
    frame = ar.from_pandas(df)

    res_frame = ar.pipeline(
        frame,
        [
            ("normalize_boolean_values", {"subset": ["a"]}),
        ],
    )

    res_df = ar.to_pandas(res_frame)
    expected = pd.DataFrame(
        {
            "a": [True, False],
        }
    )

    pd.testing.assert_frame_equal(res_df, expected, check_dtype=False)


def test_normalize_boolean_values_validation() -> None:
    df = pd.DataFrame({"a": [1, 2]})
    frame = ar.from_pandas(df)

    # Invalid list of true values
    with pytest.raises(TypeError, match="must be a list"):
        ar.normalize_boolean_values(frame, true_values="yes")  # type: ignore

    # Invalid list of false values
    with pytest.raises(TypeError, match="must be a list"):
        ar.normalize_boolean_values(frame, false_values="no")  # type: ignore

    # Missing column in subset
    with pytest.raises(KeyError, match="Missing columns"):
        ar.normalize_boolean_values(frame, subset=["non_existent"])
