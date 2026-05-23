"""Tests for ArFrame.to_dict method - additional coverage."""

import pandas as pd

import arnio as ar


class TestArFrameToDictExtended:
    """Extended test suite for ArFrame.to_dict beyond existing coverage."""

    def test_to_dict_with_single_column(self):
        """to_dict works correctly with a single column frame."""
        frame = ar.from_pandas(pd.DataFrame({"name": ["Alice", "Bob", "Charlie"]}))
        result = frame.to_dict()
        assert list(result.keys()) == ["name"]
        assert result["name"] == ["Alice", "Bob", "Charlie"]

    def test_to_dict_with_multiple_columns(self):
        """to_dict works correctly with multiple columns."""
        frame = ar.from_pandas(pd.DataFrame({"a": [1, 2], "b": [3, 4], "c": [5, 6]}))
        result = frame.to_dict()
        assert len(result) == 3
        assert result["a"] == [1, 2]
        assert result["b"] == [3, 4]
        assert result["c"] == [5, 6]

    def test_to_dict_preserves_column_order(self):
        """to_dict preserves the order of columns."""
        frame = ar.from_pandas(pd.DataFrame({"z": [1], "a": [2], "m": [3]}))
        result = frame.to_dict()
        assert list(result.keys()) == ["z", "a", "m"]

    def test_to_dict_with_none_values(self):
        """to_dict correctly handles None values in frame."""
        frame = ar.from_pandas(pd.DataFrame({"name": ["Alice", None, "Charlie"]}))
        result = frame.to_dict()
        assert result["name"] == ["Alice", None, "Charlie"]

    def test_to_dict_with_all_none_column(self):
        """to_dict handles column where all values are None."""
        frame = ar.from_pandas(pd.DataFrame({"empty": [None, None, None]}))
        result = frame.to_dict()
        assert result["empty"] == [None, None, None]

    def test_to_dict_with_mixed_types(self):
        """to_dict handles columns with mixed value types."""
        frame = ar.from_pandas(
            pd.DataFrame(
                {
                    "id": [1, 2, 3],
                    "name": ["Alice", "Bob", "Charlie"],
                    "active": [True, False, True],
                }
            )
        )
        result = frame.to_dict()
        assert result["id"] == [1, 2, 3]
        assert result["name"] == ["Alice", "Bob", "Charlie"]
        assert result["active"] == [True, False, True]

    def test_to_dict_with_float_values(self):
        """to_dict handles float values correctly."""
        frame = ar.from_pandas(pd.DataFrame({"price": [10.5, 20.75, 30.0]}))
        result = frame.to_dict()
        assert result["price"] == [10.5, 20.75, 30.0]

    def test_to_dict_with_empty_strings(self):
        """to_dict handles empty string values."""
        frame = ar.from_pandas(pd.DataFrame({"name": ["Alice", "", "Charlie"]}))
        result = frame.to_dict()
        assert result["name"] == ["Alice", "", "Charlie"]

    def test_to_dict_return_type_is_dict(self):
        """to_dict returns a Python dict type."""
        frame = ar.from_pandas(pd.DataFrame({"a": [1, 2]}))
        result = frame.to_dict()
        assert isinstance(result, dict)

    def test_to_dict_column_values_are_lists(self):
        """to_dict returns column values as lists."""
        frame = ar.from_pandas(pd.DataFrame({"name": ["Alice", "Bob"]}))
        result = frame.to_dict()
        assert isinstance(result["name"], list)

    def test_to_dict_with_row_count(self):
        """to_dict returns correct number of rows per column."""
        frame = ar.from_pandas(
            pd.DataFrame({"name": ["Alice", "Bob", "Charlie", "Diana"]})
        )
        result = frame.to_dict()
        assert len(result["name"]) == 4

    def test_to_dict_empty_column_names_in_result(self):
        """to_dict keys match actual column names."""
        frame = ar.from_pandas(pd.DataFrame({"user_name": ["Alice"], "user_age": [30]}))
        result = frame.to_dict()
        assert "user_name" in result
        assert "user_age" in result

    def test_to_dict_consistent_with_len(self):
        """to_dict column length matches frame row count."""
        frame = ar.from_pandas(
            pd.DataFrame({"a": [1, 2, 3, 4, 5], "b": ["x", "y", "z", "w", "v"]})
        )
        result = frame.to_dict()
        assert len(result["a"]) == len(frame)
        assert len(result["b"]) == len(frame)
