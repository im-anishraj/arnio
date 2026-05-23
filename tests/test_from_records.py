"""Tests for ArFrame.from_records class method - extended coverage."""

import pytest

from arnio import ArFrame


class TestArFrameFromRecordsExtended:
    """Extended test suite for ArFrame.from_records beyond basic coverage."""

    def test_list_of_dicts_with_none_values(self):
        """from_records handles None values in dict records correctly."""
        records = [{"name": "Alice", "age": None}, {"name": "Bob", "age": 25}]
        frame = ArFrame.from_records(records)
        assert frame.shape == (2, 2)
        assert frame["name"] == ["Alice", "Bob"]
        assert frame["age"] == [None, 25]

    def test_list_of_dicts_with_bool_values(self):
        """from_records correctly handles boolean values in dict records."""
        records = [{"active": True, "name": "Alice"}, {"active": False, "name": "Bob"}]
        frame = ArFrame.from_records(records)
        assert frame.shape == (2, 2)
        assert frame["active"] == [True, False]
        assert frame["name"] == ["Alice", "Bob"]

    def test_list_of_dicts_with_float_values(self):
        """from_records correctly handles float values in dict records."""
        records = [{"price": 10.5, "name": "Alice"}, {"price": 20.75, "name": "Bob"}]
        frame = ArFrame.from_records(records)
        assert frame.shape == (2, 2)
        assert frame["price"] == [10.5, 20.75]
        assert frame["name"] == ["Alice", "Bob"]

    def test_list_of_dicts_with_mixed_int_float(self):
        """from_records correctly handles mixed int/float in same column."""
        records = [{"score": 1, "name": "Alice"}, {"score": 2.5, "name": "Bob"}]
        frame = ArFrame.from_records(records)
        assert frame.shape == (2, 2)
        assert frame["score"] == [1.0, 2.5]
        assert frame["name"] == ["Alice", "Bob"]

    def test_list_of_dicts_infers_columns_from_union(self):
        """from_records returns union of all dict keys as columns."""
        records = [{"a": 1, "b": 2}, {"a": 3, "c": 4}]
        frame = ArFrame.from_records(records)
        assert set(frame.columns) == {"a", "b", "c"}

    def test_list_of_lists_with_none_values(self):
        """from_records correctly handles None values in list records."""
        records = [["Alice", None], ["Bob", 25]]
        frame = ArFrame.from_records(records, columns=["name", "age"])
        assert frame.shape == (2, 2)
        assert frame["name"] == ["Alice", "Bob"]
        assert frame["age"] == [None, 25]

    def test_list_of_lists_with_bool_values(self):
        """from_records correctly handles boolean values in list records."""
        records = [[True, "Alice"], [False, "Bob"]]
        frame = ArFrame.from_records(records, columns=["active", "name"])
        assert frame.shape == (2, 2)
        assert frame["active"] == [True, False]
        assert frame["name"] == ["Alice", "Bob"]

    def test_list_of_tuples_with_none_values(self):
        """from_records correctly handles None values in tuple records."""
        records = [("Alice", None), ("Bob", 25)]
        frame = ArFrame.from_records(records, columns=["name", "age"])
        assert frame.shape == (2, 2)
        assert frame["name"] == ["Alice", "Bob"]
        assert frame["age"] == [None, 25]

    def test_single_row_dict_list(self):
        """from_records correctly handles single row dict list."""
        records = [{"name": "Alice", "age": 30}]
        frame = ArFrame.from_records(records)
        assert frame.shape == (1, 2)
        assert frame["name"] == ["Alice"]
        assert frame["age"] == [30]

    def test_single_row_list(self):
        """from_records correctly handles single row list."""
        records = [["Alice", 30]]
        frame = ArFrame.from_records(records, columns=["name", "age"])
        assert frame.shape == (1, 2)
        assert frame["name"] == ["Alice"]
        assert frame["age"] == [30]

    def test_dict_records_with_string_numbers(self):
        """from_records handles numeric strings in dict records."""
        records = [{"count": "1"}, {"count": "2"}]
        frame = ArFrame.from_records(records)
        assert frame.shape == (2, 1)
        assert frame["count"] == ["1", "2"]

    def test_dict_records_preserve_order(self):
        """from_records preserves the order of columns from first dict."""
        records = [{"z": 1, "a": 2, "m": 3}]
        frame = ArFrame.from_records(records)
        assert list(frame.columns) == ["z", "a", "m"]

    def test_list_of_lists_row_length_mismatch_raises_with_position(self):
        """from_records raises ValueError with row index for length mismatch."""
        records = [[1, 2], [3, 4, 5]]
        with pytest.raises(ValueError) as exc_info:
            ArFrame.from_records(records, columns=["a", "b"])
        assert "row 1" in str(exc_info.value) or "1" in str(exc_info.value)

    def test_dict_with_nested_list_raises_specifically(self):
        """from_records raises TypeError for nested list in dict value."""
        records = [{"items": [1, 2, 3]}]
        with pytest.raises(TypeError, match="nested"):
            ArFrame.from_records(records)

    def test_dict_with_nested_dict_raises_specifically(self):
        """from_records raises TypeError for nested dict in dict value."""
        records = [{"nested": {"a": 1}}]
        with pytest.raises(TypeError, match="nested"):
            ArFrame.from_records(records)
