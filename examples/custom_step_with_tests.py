"""
Runnable pytest examples for the Custom Pipeline Step Cookbook.
See docs/custom_pipeline_steps.md for the full guide.

Run with:
    pytest examples/custom_step_with_tests.py -v
"""

import pandas as pd
import pytest

import arnio as ar

# ---------------------------------------------------------------------------
# Helpers used throughout the tests
# ---------------------------------------------------------------------------


def make_frame(data: dict) -> ar.ArFrame:
    """Create an ArFrame from a plain dict — convenience wrapper for tests."""
    return ar.from_pandas(pd.DataFrame(data))


def to_list(frame: ar.ArFrame, column: str) -> list:
    """Extract a single column from an ArFrame as a plain Python list."""
    return ar.to_pandas(frame)[column].tolist()


# ---------------------------------------------------------------------------
# The step under test — remove_outliers
# ---------------------------------------------------------------------------


def remove_outliers(
    df: pd.DataFrame,
    column: str,
    threshold: float,
    keep: str = "below",
) -> pd.DataFrame:
    """Remove rows where a numeric column exceeds (or falls below) a threshold.

    Parameters
    ----------
    df        : Input DataFrame. Not modified in place.
    column    : Name of the numeric column to filter on.
    threshold : The cutoff value.
    keep      : "below" keeps rows where column <= threshold (default).
                "above" keeps rows where column >= threshold.

    Raises
    ------
    ValueError
        If column is not in the DataFrame, or keep is not a valid option.
    TypeError
        If column is not numeric.
    """
    if column not in df.columns:
        raise ValueError(
            f"remove_outliers: column '{column}' not found. "
            f"Available columns: {list(df.columns)}"
        )
    if not pd.api.types.is_numeric_dtype(df[column]):
        raise TypeError(
            f"remove_outliers: column '{column}' must be numeric, "
            f"got dtype '{df[column].dtype}'."
        )
    if keep not in ("below", "above"):
        raise ValueError(
            f"remove_outliers: 'keep' must be 'below' or 'above', got '{keep}'."
        )
    df = df.copy()
    if keep == "below":
        return df[df[column] <= threshold]
    return df[df[column] >= threshold]


ar.register_step("remove_outliers", remove_outliers)


# ---------------------------------------------------------------------------
# Normal cases
# ---------------------------------------------------------------------------


def test_keep_below_removes_high_values():
    frame = make_frame({"revenue": [100, 999, 50, 10_000]})
    result = ar.pipeline(
        frame,
        [
            ("remove_outliers", {"column": "revenue", "threshold": 500}),
        ],
    )
    assert to_list(result, "revenue") == [100, 50]


def test_keep_above_removes_low_values():
    frame = make_frame({"revenue": [100, 999, 50, 10_000]})
    result = ar.pipeline(
        frame,
        [
            (
                "remove_outliers",
                {"column": "revenue", "threshold": 500, "keep": "above"},
            ),
        ],
    )
    assert to_list(result, "revenue") == [999, 10_000]


def test_threshold_boundary_value_is_kept():
    """Rows exactly equal to the threshold should be kept."""
    frame = make_frame({"revenue": [500, 501, 499]})
    result = ar.pipeline(
        frame,
        [
            ("remove_outliers", {"column": "revenue", "threshold": 500}),
        ],
    )
    assert to_list(result, "revenue") == [500, 499]


def test_all_rows_kept_when_none_exceed_threshold():
    frame = make_frame({"revenue": [10, 20, 30]})
    result = ar.pipeline(
        frame,
        [
            ("remove_outliers", {"column": "revenue", "threshold": 100}),
        ],
    )
    assert to_list(result, "revenue") == [10, 20, 30]


def test_all_rows_removed_when_all_exceed_threshold():
    frame = make_frame({"revenue": [1000, 2000, 3000]})
    result = ar.pipeline(
        frame,
        [
            ("remove_outliers", {"column": "revenue", "threshold": 500}),
        ],
    )
    assert ar.to_pandas(result).empty


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


def test_empty_dataframe_returns_empty():
    frame = make_frame({"revenue": []})
    result = ar.pipeline(
        frame,
        [
            ("remove_outliers", {"column": "revenue", "threshold": 500}),
        ],
    )
    assert ar.to_pandas(result).empty


def test_single_row_kept():
    frame = make_frame({"revenue": [100]})
    result = ar.pipeline(
        frame,
        [
            ("remove_outliers", {"column": "revenue", "threshold": 500}),
        ],
    )
    assert to_list(result, "revenue") == [100]


def test_single_row_removed():
    frame = make_frame({"revenue": [9999]})
    result = ar.pipeline(
        frame,
        [
            ("remove_outliers", {"column": "revenue", "threshold": 500}),
        ],
    )
    assert ar.to_pandas(result).empty


def test_does_not_mutate_input_frame():
    df_original = pd.DataFrame({"revenue": [100, 9999]})
    frame = ar.from_pandas(df_original.copy())
    ar.pipeline(
        frame,
        [
            ("remove_outliers", {"column": "revenue", "threshold": 500}),
        ],
    )
    assert df_original["revenue"].tolist() == [100, 9999]


def test_float_values():
    frame = make_frame({"score": [0.1, 0.5, 0.9, 1.5]})
    result = ar.pipeline(
        frame,
        [
            ("remove_outliers", {"column": "score", "threshold": 1.0}),
        ],
    )
    assert to_list(result, "score") == [0.1, 0.5, 0.9]


def test_negative_values():
    frame = make_frame({"temp": [-10, 0, 5, 100]})
    result = ar.pipeline(
        frame,
        [
            ("remove_outliers", {"column": "temp", "threshold": 10}),
        ],
    )
    assert to_list(result, "temp") == [-10, 0, 5]


# ---------------------------------------------------------------------------
# Invalid cases
# ---------------------------------------------------------------------------


def test_missing_column_raises_value_error():
    frame = make_frame({"revenue": [100, 200]})
    with pytest.raises(
        ar.PipelineStepError, match="column 'amount' not found"
    ) as exc_info:
        ar.pipeline(
            frame,
            [
                ("remove_outliers", {"column": "amount", "threshold": 500}),
            ],
        )
    assert isinstance(exc_info.value.orig_err, ValueError)


def test_non_numeric_column_raises_type_error():
    frame = make_frame({"name": ["alice", "bob"]})
    with pytest.raises(ar.PipelineStepError, match="must be numeric") as exc_info:
        ar.pipeline(
            frame,
            [
                ("remove_outliers", {"column": "name", "threshold": 500}),
            ],
        )
    assert isinstance(exc_info.value.orig_err, TypeError)


def test_invalid_keep_value_raises_value_error():
    frame = make_frame({"revenue": [100, 200]})
    with pytest.raises(
        ar.PipelineStepError, match="'keep' must be 'below' or 'above'"
    ) as exc_info:
        ar.pipeline(
            frame,
            [
                (
                    "remove_outliers",
                    {"column": "revenue", "threshold": 500, "keep": "middle"},
                ),
            ],
        )
    assert isinstance(exc_info.value.orig_err, ValueError)
