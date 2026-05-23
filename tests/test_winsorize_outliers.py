"""Tests for winsorize_outliers boundary conditions in arnio.cleaning."""

import pytest
from arnio import ArFrame
from arnio.cleaning import winsorize_outliers


class TestWinsorizeOutliersBoundary:
    """Boundary condition tests for winsorize_outliers function."""

    def test_identical_quantiles_no_change(self):
        """winsorize_outliers applies no change when lower equals upper."""
        frame = ArFrame({"val": [1, 2, 3, 4, 5]})
        result = winsorize_outliers(frame, lower=0.5, upper=0.5)
        assert result["val"].tolist() == [1, 2, 3, 4, 5]

    def test_single_row_frame(self):
        """winsorize_outliers handles single-row frame gracefully."""
        frame = ArFrame({"val": [42]})
        result = winsorize_outliers(frame, lower=0.1, upper=0.9)
        assert len(result) == 1

    def test_all_same_values(self):
        """winsorize_outliers handles column with all identical values."""
        frame = ArFrame({"val": [5, 5, 5, 5]})
        result = winsorize_outliers(frame, lower=0.1, upper=0.9)
        assert result["val"].tolist() == [5, 5, 5, 5]

    def test_all_values_already_within_bounds(self):
        """winsorize_outliers makes no changes when all values within bounds."""
        frame = ArFrame({"val": [25, 30, 35, 40, 45]})
        result = winsorize_outliers(frame, lower=0.1, upper=0.9)
        assert result["val"].tolist() == [25, 30, 35, 40, 45]

    def test_extreme_outliers_clipped(self):
        """winsorize_outliers clips extreme outliers correctly."""
        frame = ArFrame({"val": [1, 2, 3, 4, 100]})
        result = winsorize_outliers(frame, lower=0.1, upper=0.9)
        val_list = result["val"].tolist()
        assert val_list[-1] != 100

    def test_negative_outliers_clipped(self):
        """winsorize_outliers clips negative outliers."""
        frame = ArFrame({"val": [-100, 1, 2, 3, 4]})
        result = winsorize_outliers(frame, lower=0.1, upper=0.9)
        val_list = result["val"].tolist()
        assert val_list[0] != -100

    def test_subset_column_not_in_frame_raises(self):
        """winsorize_outliers raises for unknown column in subset."""
        frame = ArFrame({"a": [1, 2, 3]})
        with pytest.raises(ValueError, match="not found"):
            winsorize_outliers(frame, subset=["a", "nonexistent"])

    def test_raises_when_lower_negative(self):
        """winsorize_outliers raises ValueError when lower is negative."""
        frame = ArFrame({"val": [1, 2, 3]})
        with pytest.raises(ValueError, match="between 0 and 1"):
            winsorize_outliers(frame, lower=-0.1)

    def test_raises_when_upper_greater_than_one(self):
        """winsorize_outliers raises ValueError when upper exceeds 1."""
        frame = ArFrame({"val": [1, 2, 3]})
        with pytest.raises(ValueError, match="between 0 and 1"):
            winsorize_outliers(frame, upper=1.5)

    def test_raises_when_lower_greater_than_or_equal_upper(self):
        """winsorize_outliers raises ValueError when lower >= upper."""
        frame = ArFrame({"val": [1, 2, 3]})
        with pytest.raises(ValueError, match="lower must be less than upper"):
            winsorize_outliers(frame, lower=0.8, upper=0.3)

    def test_raises_when_lower_equal_upper(self):
        """winsorize_outliers raises ValueError when lower == upper."""
        frame = ArFrame({"val": [1, 2, 3]})
        with pytest.raises(ValueError, match="lower must be less than upper"):
            winsorize_outliers(frame, lower=0.5, upper=0.5)

    def test_subset_with_valid_columns_only(self):
        """winsorize_outliers applies only to specified columns in subset."""
        frame = ArFrame({"a": [1, 2, 3, 4, 100], "b": [1, 2, 3, 4, 5]})
        result = winsorize_outliers(frame, lower=0.2, upper=0.8, subset=["a"])
        assert result["a"].tolist() != frame["a"].tolist()
        assert result["b"].tolist() == frame["b"].tolist()

    def test_two_column_frame(self):
        """winsorize_outliers handles frame with two numeric columns."""
        frame = ArFrame({"col1": [1, 2, 3], "col2": [10, 20, 30]})
        result = winsorize_outliers(frame, lower=0.1, upper=0.9)
        assert len(result) == 3
        assert len(result.columns) == 2