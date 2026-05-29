"""Tests for winsorize_outliers boundary conditions in arnio.cleaning."""

import pandas as pd
import pytest

import arnio as ar
from arnio.cleaning import winsorize_outliers


class TestWinsorizeOutliersBoundary:
    """Boundary condition tests for winsorize_outliers function."""

    def test_single_row_frame(self):
        """winsorize_outliers handles single-row frame gracefully."""
        frame = ar.from_pandas(pd.DataFrame({"val": [42.0]}))
        result = winsorize_outliers(frame, lower=0.1, upper=0.9)
        df = ar.to_pandas(result)
        assert len(df) == 1
        assert df["val"].iloc[0] == pytest.approx(42.0)

    def test_all_same_values(self):
        """winsorize_outliers handles column with all identical values."""
        frame = ar.from_pandas(pd.DataFrame({"val": [5.0, 5.0, 5.0, 5.0]}))
        result = winsorize_outliers(frame, lower=0.1, upper=0.9)
        df = ar.to_pandas(result)
        assert list(df["val"]) == [5.0, 5.0, 5.0, 5.0]

    def test_values_inside_bounds_are_unchanged(self):
        """winsorize_outliers makes no changes to values already within the quantile bounds."""
        frame = ar.from_pandas(pd.DataFrame({"val": [10.0, 20.0, 30.0, 40.0, 50.0]}))
        result = winsorize_outliers(frame, lower=0.2, upper=0.8)
        df = ar.to_pandas(result)
        # 0.2 quantile is 18.0, 0.8 quantile is 42.0.
        # Only 20.0, 30.0, 40.0 are inside the bounds and remain unchanged.
        # 10.0 and 50.0 are clipped.
        assert list(df["val"]) == pytest.approx([18.0, 20.0, 30.0, 40.0, 42.0])

    def test_extreme_outliers_clipped(self):
        """winsorize_outliers clips extreme outliers correctly."""
        frame = ar.from_pandas(pd.DataFrame({"val": [1.0, 2.0, 3.0, 4.0, 100.0]}))
        # Quantile bounds for [1, 2, 3, 4, 100] at 0.1 and 0.9:
        # 0.1 quantile is 1.4, 0.9 quantile is 61.6
        result = winsorize_outliers(frame, lower=0.1, upper=0.9)
        df = ar.to_pandas(result)
        assert list(df["val"]) == pytest.approx([1.4, 2.0, 3.0, 4.0, 61.6])

    def test_negative_outliers_clipped(self):
        """winsorize_outliers clips negative outliers."""
        frame = ar.from_pandas(pd.DataFrame({"val": [-100.0, 1.0, 2.0, 3.0, 4.0]}))
        # Quantile bounds at 0.1 and 0.9:
        # 0.1 quantile is -59.6, 0.9 quantile is 3.6
        result = winsorize_outliers(frame, lower=0.1, upper=0.9)
        df = ar.to_pandas(result)
        assert list(df["val"]) == pytest.approx([-59.6, 1.0, 2.0, 3.0, 3.6])

    def test_subset_column_not_in_frame_raises(self):
        """winsorize_outliers raises for unknown column in subset."""
        frame = ar.from_pandas(pd.DataFrame({"a": [1.0, 2.0, 3.0]}))
        with pytest.raises(ValueError, match="Unknown columns in subset"):
            winsorize_outliers(frame, subset=["a", "nonexistent"])

    def test_raises_when_lower_negative(self):
        """winsorize_outliers raises ValueError when lower is negative."""
        frame = ar.from_pandas(pd.DataFrame({"val": [1.0, 2.0, 3.0]}))
        with pytest.raises(ValueError, match="between 0 and 1"):
            winsorize_outliers(frame, lower=-0.1)

    def test_raises_when_upper_greater_than_one(self):
        """winsorize_outliers raises ValueError when upper exceeds 1."""
        frame = ar.from_pandas(pd.DataFrame({"val": [1.0, 2.0, 3.0]}))
        with pytest.raises(ValueError, match="between 0 and 1"):
            winsorize_outliers(frame, upper=1.5)

    def test_raises_when_lower_greater_than_or_equal_upper(self):
        """winsorize_outliers raises ValueError when lower >= upper."""
        frame = ar.from_pandas(pd.DataFrame({"val": [1.0, 2.0, 3.0]}))
        with pytest.raises(ValueError, match="lower must be less than upper"):
            winsorize_outliers(frame, lower=0.8, upper=0.3)

    def test_raises_when_lower_equal_upper(self):
        """winsorize_outliers raises ValueError when lower == upper."""
        frame = ar.from_pandas(pd.DataFrame({"val": [1.0, 2.0, 3.0]}))
        with pytest.raises(ValueError, match="lower must be less than upper"):
            winsorize_outliers(frame, lower=0.5, upper=0.5)

    def test_subset_with_valid_columns_only(self):
        """winsorize_outliers applies only to specified columns in subset."""
        frame = ar.from_pandas(
            pd.DataFrame(
                {"a": [1.0, 2.0, 3.0, 4.0, 100.0], "b": [1.0, 2.0, 3.0, 4.0, 5.0]}
            )
        )
        result = winsorize_outliers(frame, lower=0.2, upper=0.8, subset=["a"])
        df = ar.to_pandas(result)
        # a is clipped: bounds at 0.2 and 0.8 are 1.8 and 23.2
        assert list(df["a"]) == pytest.approx([1.8, 2.0, 3.0, 4.0, 23.2])
        assert list(df["b"]) == [1.0, 2.0, 3.0, 4.0, 5.0]

    def test_two_column_frame(self):
        """winsorize_outliers handles frame with two numeric columns."""
        frame = ar.from_pandas(
            pd.DataFrame({"col1": [1.0, 2.0, 3.0], "col2": [10.0, 20.0, 30.0]})
        )
        result = winsorize_outliers(frame, lower=0.1, upper=0.9)
        df = ar.to_pandas(result)
        assert len(df) == 3
        assert list(df.columns) == ["col1", "col2"]

    def test_handles_nan_and_null_values(self):
        """winsorize_outliers correctly handles columns with NaN/None values."""
        frame = ar.from_pandas(pd.DataFrame({"val": [1.0, None, 3.0, 4.0, 100.0]}))
        # In pandas, quantiles ignore NaN values by default.
        # [1.0, 3.0, 4.0, 100.0] has 0.1 quantile = 1.6, 0.9 quantile = 71.2
        result = winsorize_outliers(frame, lower=0.1, upper=0.9)
        df = ar.to_pandas(result)
        assert pd.isna(df["val"].iloc[1]) is True
        assert df["val"].iloc[0] == pytest.approx(1.6)
        assert df["val"].iloc[4] == pytest.approx(71.2)

    def test_no_numeric_columns_returns_distinct_frame(self):
        """winsorize_outliers returns a new distinct ArFrame when no numeric columns exist.

        Regression test for: the early-return path returned the original frame
        object unchanged, violating the documented 'New frame' return contract.
        """
        frame = ar.from_pandas(pd.DataFrame({"name": ["alice", "bob", "carol"]}))
        result = winsorize_outliers(frame)

        # Must be a distinct object, not the same reference
        assert result is not frame

        # Data must be identical (no transformation should occur)
        original_df = ar.to_pandas(frame)
        result_df = ar.to_pandas(result)
        assert list(result_df.columns) == list(original_df.columns)
        assert list(result_df["name"]) == list(original_df["name"])

    def test_no_numeric_columns_with_subset_empty_after_filter_returns_distinct_frame(self):
        """winsorize_outliers returns a new ArFrame when the frame has no numeric columns at all."""
        frame = ar.from_pandas(
            pd.DataFrame({"label": ["x", "y"], "category": ["a", "b"]})
        )
        result = winsorize_outliers(frame)

        assert result is not frame
        result_df = ar.to_pandas(result)
        assert list(result_df.columns) == ["label", "category"]
        assert list(result_df["label"]) == ["x", "y"]
