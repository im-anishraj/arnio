"""Tests for _is_safely_convertible_to_dtype helper in arnio.schema."""

import pandas as pd

from arnio.schema import _is_safely_convertible_to_dtype


class TestIsSafelyConvertible:
    """Test suite for _is_safely_convertible_to_dtype helper."""

    def test_returns_true_for_numeric_strings_to_int(self):
        """Returns True for clean numeric strings when converting to int."""
        series = pd.Series(["123", "456", "789"])
        result = _is_safely_convertible_to_dtype(series, "int64", "count")
        assert result is True

    def test_returns_false_for_identifier_like_with_leading_zero_to_int(self):
        """Returns False for zip-code-like strings (leading zero) to int."""
        series = pd.Series(["01234", "05678"])
        result = _is_safely_convertible_to_dtype(series, "int64", "zip")
        assert result is False

    def test_returns_false_for_uuid_like_to_int(self):
        """Returns False for uuid-like strings when converting to int."""
        series = pd.Series(["abc123-def456", "ghi789-xyz012"])
        result = _is_safely_convertible_to_dtype(series, "int64", "uuid_col")
        assert result is False

    def test_returns_true_for_numeric_zip_code_to_int(self):
        """Returns True for plain numeric zip code strings (without leading zero) to int."""
        series = pd.Series(["10001", "90210", "90211"])
        result = _is_safely_convertible_to_dtype(series, "int64", "zip")
        assert result is True

    def test_returns_false_for_leading_zero_id_to_int(self):
        """Returns False for id/user_id columns with leading-zero string numbers to int."""
        series = pd.Series(["00123", "00456"])
        result = _is_safely_convertible_to_dtype(series, "int64", "user_id")
        assert result is False

    def test_returns_true_for_clean_int_strings_with_id_suffix(self):
        """Returns True for identifier-like column with numeric string to int."""
        series = pd.Series(["123", "456"])
        result = _is_safely_convertible_to_dtype(series, "int64", "user_id")
        assert result is True

    def test_returns_false_for_non_numeric_string_to_int(self):
        """Returns False for non-numeric strings when converting to int."""
        series = pd.Series(["abc", "def", "ghi"])
        result = _is_safely_convertible_to_dtype(series, "int64", "name")
        assert result is False

    def test_returns_true_for_clean_strings_to_float(self):
        """Returns True for clean numeric strings when converting to float."""
        series = pd.Series(["1.5", "2.5", "3.0"])
        result = _is_safely_convertible_to_dtype(series, "float64", "price")
        assert result is True

    def test_returns_false_for_mixed_alphanumeric_to_numeric(self):
        """Returns False for mixed alphanumeric strings to numeric."""
        series = pd.Series(["123abc", "456def"])
        result = _is_safely_convertible_to_dtype(series, "int64", "code")
        assert result is False

    def test_returns_false_for_empty_series(self):
        """Returns False for empty series."""
        series = pd.Series([], dtype=object)
        result = _is_safely_convertible_to_dtype(series, "int64", "empty")
        assert result is False

    def test_returns_false_for_series_with_all_null(self):
        """Returns False for series where all values are null."""
        series = pd.Series([None, None, None])
        result = _is_safely_convertible_to_dtype(series, "int64", "all_null")
        assert result is False

    def test_handles_negative_numbers_to_int(self):
        """Returns True for negative numeric strings to int."""
        series = pd.Series(["-123", "456", "-789"])
        result = _is_safely_convertible_to_dtype(series, "int64", "delta")
        assert result is True

    def test_handles_float_with_decimal_to_float(self):
        """Returns True for decimal strings to float."""
        series = pd.Series(["1.234", "5.678", "9.012"])
        result = _is_safely_convertible_to_dtype(series, "float64", "measurement")
        assert result is True

    def test_returns_false_for_out_of_range_int(self):
        """Returns False for integers outside int64 range."""
        series = pd.Series(["99999999999999999999999999999"])
        result = _is_safely_convertible_to_dtype(series, "int64", "huge")
        assert result is False

    def test_column_name_not_id_or_uuid_still_normal_check(self):
        """Non-identifier columns bypass leading-zero check."""
        series = pd.Series(["01234", "01235"])
        result = _is_safely_convertible_to_dtype(series, "int64", "some_number")
        assert result is True
