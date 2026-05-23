"""Tests for _compare_column_profiles helper in arnio.quality."""

import pytest
from arnio.quality import _compare_column_profiles


class TestCompareColumnProfiles:
    """Test suite for _compare_column_profiles internal helper."""

    def test_detects_dtype_change(self):
        """_compare_column_profiles reports dtype change between profiles."""
        p1 = {"dtype": "int", "null_ratio": 0.0, "unique_count": 10}
        p2 = {"dtype": "string", "null_ratio": 0.0, "unique_count": 10}
        result = _compare_column_profiles(p1, p2)
        assert "dtype" in result
        assert result["dtype"]["baseline"] == "int"
        assert result["dtype"]["comparison"] == "string"

    def test_detects_null_ratio_change(self):
        """_compare_column_profiles reports null_ratio changes."""
        p1 = {"dtype": "int", "null_ratio": 0.0, "unique_count": 10}
        p2 = {"dtype": "int", "null_ratio": 0.5, "unique_count": 10}
        result = _compare_column_profiles(p1, p2)
        assert "null_ratio" in result
        assert result["null_ratio"]["baseline"] == 0.0
        assert result["null_ratio"]["comparison"] == 0.5

    def test_detects_unique_count_change(self):
        """_compare_column_profiles reports unique_count changes."""
        p1 = {"dtype": "string", "null_ratio": 0.0, "unique_count": 10}
        p2 = {"dtype": "string", "null_ratio": 0.0, "unique_count": 5}
        result = _compare_column_profiles(p1, p2)
        assert "unique_count" in result
        assert result["unique_count"]["baseline"] == 10
        assert result["unique_count"]["comparison"] == 5

    def test_no_changes_for_identical_profiles(self):
        """_compare_column_profiles returns empty changes for identical profiles."""
        p1 = {"dtype": "int", "null_ratio": 0.1, "unique_count": 10}
        p2 = {"dtype": "int", "null_ratio": 0.1, "unique_count": 10}
        result = _compare_column_profiles(p1, p2)
        assert len(result) == 0

    def test_handles_missing_profile_keys(self):
        """_compare_column_profiles handles missing keys in profile gracefully."""
        p1 = {"dtype": "int"}
        p2 = {"dtype": "int", "null_ratio": 0.0}
        result = _compare_column_profiles(p1, p2)
        # Should not raise, should handle gracefully
        assert result is not None

    def test_detects_min_value_change(self):
        """_compare_column_profiles reports min_value changes."""
        p1 = {"dtype": "int", "null_ratio": 0.0, "unique_count": 10, "min_value": 0}
        p2 = {"dtype": "int", "null_ratio": 0.0, "unique_count": 10, "min_value": 10}
        result = _compare_column_profiles(p1, p2)
        assert "min_value" in result

    def test_detects_max_value_change(self):
        """_compare_column_profiles reports max_value changes."""
        p1 = {"dtype": "int", "null_ratio": 0.0, "unique_count": 10, "max_value": 100}
        p2 = {"dtype": "int", "null_ratio": 0.0, "unique_count": 10, "max_value": 200}
        result = _compare_column_profiles(p1, p2)
        assert "max_value" in result

    def test_detects_mean_value_change(self):
        """_compare_column_profiles reports mean_value changes."""
        p1 = {"dtype": "float", "null_ratio": 0.0, "unique_count": 10, "mean_value": 50.0}
        p2 = {"dtype": "float", "null_ratio": 0.0, "unique_count": 10, "mean_value": 75.0}
        result = _compare_column_profiles(p1, p2)
        assert "mean_value" in result

    def test_calculates_delta_for_numeric_changes(self):
        """_compare_column_profiles includes delta in change records."""
        p1 = {"dtype": "int", "null_ratio": 0.0, "unique_count": 10, "min_value": 0}
        p2 = {"dtype": "int", "null_ratio": 0.0, "unique_count": 10, "min_value": 5}
        result = _compare_column_profiles(p1, p2)
        assert "min_value" in result
        assert "delta" in result["min_value"]

    def test_handles_string_profiles(self):
        """_compare_column_profiles works with string-typed profiles."""
        p1 = {"dtype": "string", "null_ratio": 0.0, "unique_count": 10}
        p2 = {"dtype": "string", "null_ratio": 0.1, "unique_count": 8}
        result = _compare_column_profiles(p1, p2)
        assert "null_ratio" in result
        assert "unique_count" in result