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

    def test_no_numeric_columns_with_subset_empty_after_filter_returns_distinct_frame(
        self,
    ):
        """winsorize_outliers returns a new ArFrame when the frame has no numeric columns at all."""
        frame = ar.from_pandas(
            pd.DataFrame({"label": ["x", "y"], "category": ["a", "b"]})
        )
        result = winsorize_outliers(frame)

        assert result is not frame
        result_df = ar.to_pandas(result)
        assert list(result_df.columns) == ["label", "category"]
        assert list(result_df["label"]) == ["x", "y"]


class TestWinsorizeOutliersAdditional:
    """Additional edge-case and coverage tests for winsorize_outliers."""

    # ------------------------------------------------------------------
    # Boundary percentiles: lower=0.0 and upper=1.0
    # ------------------------------------------------------------------

    def test_zero_lower_bound_leaves_minimum_unchanged(self):
        """lower=0.0 means no lower clamping; the minimum value is kept as-is."""
        frame = ar.from_pandas(pd.DataFrame({"val": [1.0, 2.0, 3.0, 4.0, 5.0]}))
        result = winsorize_outliers(frame, lower=0.0, upper=0.9)
        df = ar.to_pandas(result)
        # 0.0 quantile = 1.0 (min), so min value must not be raised
        assert df["val"].iloc[0] == pytest.approx(1.0)
        # 0.9 quantile of [1,2,3,4,5] = 4.6; last value must be clamped
        assert df["val"].iloc[4] == pytest.approx(4.6)

    def test_unit_upper_bound_leaves_maximum_unchanged(self):
        """upper=1.0 means no upper clamping; the maximum value is kept as-is."""
        frame = ar.from_pandas(pd.DataFrame({"val": [1.0, 2.0, 3.0, 4.0, 5.0]}))
        result = winsorize_outliers(frame, lower=0.1, upper=1.0)
        df = ar.to_pandas(result)
        # 1.0 quantile = 5.0 (max), so max value must not be reduced
        assert df["val"].iloc[4] == pytest.approx(5.0)
        # 0.1 quantile of [1,2,3,4,5] = 1.4; first value must be raised
        assert df["val"].iloc[0] == pytest.approx(1.4)

    def test_full_range_lower_zero_upper_one_no_change(self):
        """lower=0.0 + upper=1.0 covers the full range; no value should be altered."""
        data = [-999.0, 10.0, 20.0, 30.0, 40.0, 999.0]
        frame = ar.from_pandas(pd.DataFrame({"val": data}))
        result = winsorize_outliers(frame, lower=0.0, upper=1.0)
        df = ar.to_pandas(result)
        assert list(df["val"]) == pytest.approx(data)

    # ------------------------------------------------------------------
    # Multiple numeric columns winsorized simultaneously
    # ------------------------------------------------------------------

    def test_multiple_numeric_columns_all_clipped(self):
        """winsorize_outliers clips each numeric column independently."""
        frame = ar.from_pandas(
            pd.DataFrame(
                {
                    "a": [1.0, 2.0, 3.0, 4.0, 100.0],
                    "b": [200.0, 10.0, 20.0, 30.0, 40.0],
                }
            )
        )
        result = winsorize_outliers(frame, lower=0.2, upper=0.8)
        df = ar.to_pandas(result)
        # Column a: 0.2q=1.8, 0.8q=23.2
        assert list(df["a"]) == pytest.approx([1.8, 2.0, 3.0, 4.0, 23.2])
        # Column b: compute expected bounds dynamically to stay robust
        b_series = pd.Series([200.0, 10.0, 20.0, 30.0, 40.0])
        b_lo = b_series.quantile(0.2)
        b_hi = b_series.quantile(0.8)
        expected_b = [min(max(v, b_lo), b_hi) for v in b_series]
        assert list(df["b"]) == pytest.approx(expected_b)

    # ------------------------------------------------------------------
    # Mixed dtypes: string columns must be ignored
    # ------------------------------------------------------------------

    def test_string_column_is_not_altered_by_winsorization(self):
        """String columns must pass through completely unmodified."""
        frame = ar.from_pandas(
            pd.DataFrame(
                {
                    "score": [1.0, 2.0, 3.0, 4.0, 100.0],
                    "name": ["alice", "bob", "carol", "dave", "eve"],
                }
            )
        )
        result = winsorize_outliers(frame, lower=0.1, upper=0.9)
        df = ar.to_pandas(result)
        assert list(df["name"]) == ["alice", "bob", "carol", "dave", "eve"]

    def test_non_numeric_subset_raises_value_error(self):
        """Explicitly requesting a non-numeric column via subset raises ValueError."""
        frame = ar.from_pandas(
            pd.DataFrame(
                {
                    "score": [1.0, 2.0, 3.0],
                    "label": ["a", "b", "c"],
                }
            )
        )
        with pytest.raises(ValueError, match="only supports numeric columns"):
            winsorize_outliers(frame, subset=["label"])

    # ------------------------------------------------------------------
    # Integer column dtype handling
    # ------------------------------------------------------------------

    def test_integer_column_values_are_clipped(self):
        """int64 columns are cast to float64 during winsorization."""
        data = [1, 2, 3, 4, 50]
        frame = ar.from_pandas(pd.DataFrame({"count": data}))
        result = winsorize_outliers(frame, lower=0.1, upper=0.9)
        df = ar.to_pandas(result)
        series = pd.Series(data, dtype="float64")
        expected_lower = series.quantile(0.1)
        expected_upper = series.quantile(0.9)
        # Smallest value should be raised to the lower bound
        assert df["count"].iloc[0] == pytest.approx(expected_lower)
        # Largest value should be clamped to the upper bound
        assert df["count"].iloc[4] == pytest.approx(expected_upper)

    # ------------------------------------------------------------------
    # Immutability — the original frame must not be modified
    # ------------------------------------------------------------------

    def test_original_frame_is_not_modified(self):
        """winsorize_outliers must not mutate the input frame."""
        data = [1.0, 2.0, 3.0, 4.0, 999.0]
        frame = ar.from_pandas(pd.DataFrame({"val": data}))
        original_values = list(ar.to_pandas(frame)["val"])
        _ = winsorize_outliers(frame, lower=0.1, upper=0.9)
        after_values = list(ar.to_pandas(frame)["val"])
        assert after_values == original_values

    def test_result_is_a_new_frame_object(self):
        """winsorize_outliers always returns a new distinct frame object."""
        frame = ar.from_pandas(pd.DataFrame({"val": [1.0, 2.0, 3.0, 4.0, 5.0]}))
        result = winsorize_outliers(frame, lower=0.1, upper=0.9)
        assert result is not frame

    # ------------------------------------------------------------------
    # Pipeline integration
    # ------------------------------------------------------------------

    def test_pipeline_integration(self):
        """winsorize_outliers works correctly when invoked via ar.pipeline()."""
        frame = ar.from_pandas(pd.DataFrame({"val": [1.0, 2.0, 3.0, 4.0, 100.0]}))
        result = ar.pipeline(
            frame,
            [("winsorize_outliers", {"lower": 0.2, "upper": 0.8})],
        )
        df = ar.to_pandas(result)
        assert list(df["val"]) == pytest.approx([1.8, 2.0, 3.0, 4.0, 23.2])

    def test_pipeline_integration_with_subset(self):
        """winsorize_outliers subset parameter works via ar.pipeline()."""
        frame = ar.from_pandas(
            pd.DataFrame(
                {
                    "a": [1.0, 2.0, 3.0, 4.0, 100.0],
                    "b": [1.0, 2.0, 3.0, 4.0, 5.0],
                }
            )
        )
        result = ar.pipeline(
            frame,
            [("winsorize_outliers", {"lower": 0.2, "upper": 0.8, "subset": ["a"]})],
        )
        df = ar.to_pandas(result)
        assert list(df["a"]) == pytest.approx([1.8, 2.0, 3.0, 4.0, 23.2])
        assert list(df["b"]) == [1.0, 2.0, 3.0, 4.0, 5.0]

    # ------------------------------------------------------------------
    # Multiple NaN values scattered across a column
    # ------------------------------------------------------------------

    def test_multiple_nans_are_preserved_and_non_nans_are_clipped(self):
        """NaN values at multiple positions are preserved; non-NaN values are clipped."""
        frame = ar.from_pandas(pd.DataFrame({"val": [None, 1.0, None, 4.0, 100.0]}))
        result = winsorize_outliers(frame, lower=0.1, upper=0.9)
        df = ar.to_pandas(result)
        # NaN positions must remain NaN
        assert pd.isna(df["val"].iloc[0])
        assert pd.isna(df["val"].iloc[2])
        # Non-NaN positions must remain non-NaN
        assert not pd.isna(df["val"].iloc[1])
        assert not pd.isna(df["val"].iloc[3])
        assert not pd.isna(df["val"].iloc[4])

    def test_all_nan_column_stays_all_nan(self):
        """A column of only NaN values stays fully NaN after winsorization."""
        frame = ar.from_pandas(pd.DataFrame({"val": [None, None, None, None]}))
        result = winsorize_outliers(frame, lower=0.05, upper=0.95)
        df = ar.to_pandas(result)
        assert df["val"].isna().all()

    # ------------------------------------------------------------------
    # Small datasets
    # ------------------------------------------------------------------

    def test_two_row_dataset_symmetric_clipping(self):
        """Two-row frame: both values are moved toward each other's quantile bound."""
        frame = ar.from_pandas(pd.DataFrame({"val": [0.0, 100.0]}))
        result = winsorize_outliers(frame, lower=0.1, upper=0.9)
        df = ar.to_pandas(result)
        # 0.1q=10.0, 0.9q=90.0 for [0.0, 100.0]
        assert df["val"].iloc[0] == pytest.approx(10.0)
        assert df["val"].iloc[1] == pytest.approx(90.0)

    def test_three_row_dataset(self):
        """Three-row frame with a clear upper outlier: the large value is clamped."""
        data = [1.0, 5.0, 1000.0]
        frame = ar.from_pandas(pd.DataFrame({"val": data}))
        result = winsorize_outliers(frame, lower=0.1, upper=0.9)
        df = ar.to_pandas(result)
        series = pd.Series(data)
        expected_lower = series.quantile(0.1)
        expected_upper = series.quantile(0.9)
        # Largest value must be clamped to upper bound
        assert df["val"].iloc[2] == pytest.approx(expected_upper)
        # Smallest value must be at least the lower bound
        assert df["val"].iloc[0] == pytest.approx(max(data[0], expected_lower))

    # ------------------------------------------------------------------
    # Default parameters
    # ------------------------------------------------------------------

    def test_default_lower_and_upper_are_applied(self):
        """Calling winsorize_outliers() without explicit bounds uses lower=0.05, upper=0.95."""
        data = [float(x) for x in range(1, 21)]  # [1.0 .. 20.0]
        frame = ar.from_pandas(pd.DataFrame({"val": data}))
        result = winsorize_outliers(frame)
        df = ar.to_pandas(result)
        series = pd.Series(data)
        expected_lower = series.quantile(0.05)
        expected_upper = series.quantile(0.95)
        assert df["val"].min() == pytest.approx(expected_lower)
        assert df["val"].max() == pytest.approx(expected_upper)

    # ------------------------------------------------------------------
    # Column order and shape are preserved
    # ------------------------------------------------------------------

    def test_column_order_is_preserved(self):
        """Column order in the result matches the original frame."""
        frame = ar.from_pandas(
            pd.DataFrame(
                {
                    "z": [1.0, 2.0, 3.0, 4.0, 5.0],
                    "a": [10.0, 20.0, 30.0, 40.0, 50.0],
                    "m": [100.0, 200.0, 300.0, 400.0, 500.0],
                }
            )
        )
        result = winsorize_outliers(frame, lower=0.1, upper=0.9)
        df = ar.to_pandas(result)
        assert list(df.columns) == ["z", "a", "m"]

    def test_row_count_is_preserved(self):
        """winsorize_outliers never drops rows; shape[0] stays the same."""
        frame = ar.from_pandas(pd.DataFrame({"val": [float(i) for i in range(50)]}))
        result = winsorize_outliers(frame, lower=0.1, upper=0.9)
        assert ar.to_pandas(result).shape[0] == 50
