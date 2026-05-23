"""Tests for _compare_column_profiles helper in arnio.quality."""

from arnio.quality import ColumnProfile, _compare_column_profiles


def make_profile(
    name="col",
    dtype="int64",
    semantic_type="numeric",
    row_count=10,
    null_count=0,
    null_ratio=0.0,
    unique_count=10,
    unique_ratio=1.0,
    min=None,
    max=None,
    mean=None,
    std=None,
):
    """Helper to create a ColumnProfile instance with default values."""
    return ColumnProfile(
        name=name,
        dtype=dtype,
        semantic_type=semantic_type,
        row_count=row_count,
        null_count=null_count,
        null_ratio=null_ratio,
        unique_count=unique_count,
        unique_ratio=unique_ratio,
        min=min,
        max=max,
        mean=mean,
        std=std,
    )


class TestCompareColumnProfiles:
    """Test suite for _compare_column_profiles internal helper."""

    def test_detects_dtype_change(self):
        """_compare_column_profiles reports dtype change between profiles."""
        p1 = make_profile(dtype="int64")
        p2 = make_profile(dtype="string")
        result = _compare_column_profiles(p1, p2)
        assert "dtype" in result["changes"]
        assert result["changes"]["dtype"]["baseline"] == "int64"
        assert result["changes"]["dtype"]["comparison"] == "string"

    def test_detects_null_ratio_change(self):
        """_compare_column_profiles reports null_ratio changes."""
        p1 = make_profile(null_ratio=0.0)
        p2 = make_profile(null_ratio=0.5)
        result = _compare_column_profiles(p1, p2)
        assert "null_ratio" in result["changes"]
        assert result["changes"]["null_ratio"]["baseline"] == 0.0
        assert result["changes"]["null_ratio"]["comparison"] == 0.5

    def test_detects_unique_count_change(self):
        """_compare_column_profiles reports unique_count changes."""
        p1 = make_profile(unique_count=10)
        p2 = make_profile(unique_count=5)
        result = _compare_column_profiles(p1, p2)
        assert "unique_count" in result["changes"]
        assert result["changes"]["unique_count"]["baseline"] == 10
        assert result["changes"]["unique_count"]["comparison"] == 5

    def test_no_changes_for_identical_profiles(self):
        """_compare_column_profiles returns empty changes for identical profiles."""
        p1 = make_profile(null_ratio=0.1, unique_count=10)
        p2 = make_profile(null_ratio=0.1, unique_count=10)
        result = _compare_column_profiles(p1, p2)
        assert len(result["changes"]) == 0

    def test_handles_missing_profile_keys(self):
        """_compare_column_profiles handles None values for stats in profile gracefully."""
        p1 = make_profile(min=None, max=None, mean=None, std=None)
        p2 = make_profile(min=None, max=None, mean=None, std=None)
        result = _compare_column_profiles(p1, p2)
        assert result is not None
        assert len(result["changes"]) == 0

    def test_detects_min_value_change(self):
        """_compare_column_profiles reports min_value changes."""
        p1 = make_profile(dtype="int64", min=0)
        p2 = make_profile(dtype="int64", min=10)
        result = _compare_column_profiles(p1, p2)
        assert "min" in result["changes"]

    def test_detects_max_value_change(self):
        """_compare_column_profiles reports max_value changes."""
        p1 = make_profile(dtype="int64", max=100)
        p2 = make_profile(dtype="int64", max=200)
        result = _compare_column_profiles(p1, p2)
        assert "max" in result["changes"]

    def test_detects_mean_value_change(self):
        """_compare_column_profiles reports mean_value changes."""
        p1 = make_profile(dtype="float64", mean=50.0)
        p2 = make_profile(dtype="float64", mean=75.0)
        result = _compare_column_profiles(p1, p2)
        assert "mean" in result["changes"]

    def test_calculates_delta_for_numeric_changes(self):
        """_compare_column_profiles includes delta in change records."""
        p1 = make_profile(dtype="int64", min=0)
        p2 = make_profile(dtype="int64", min=5)
        result = _compare_column_profiles(p1, p2)
        assert "min" in result["changes"]
        assert "delta" in result["changes"]["min"]
        assert result["changes"]["min"]["delta"] == 5.0

    def test_handles_string_profiles(self):
        """_compare_column_profiles works with string-typed profiles."""
        p1 = make_profile(dtype="string", null_ratio=0.0, unique_count=10)
        p2 = make_profile(dtype="string", null_ratio=0.1, unique_count=8)
        result = _compare_column_profiles(p1, p2)
        assert "null_ratio" in result["changes"]
        assert "unique_count" in result["changes"]
