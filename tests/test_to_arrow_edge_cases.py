"""Tests for to_arrow edge cases in arnio.convert."""

import pandas as pd
import pytest

import arnio as ar
from arnio.convert import to_arrow

HAS_PYARROW = pytest.importorskip("pyarrow") is not None


class TestToArrowEdgeCases:
    """Edge case tests for to_arrow conversion function."""

    def test_zero_column_frame(self):
        """to_arrow handles zero-column frame gracefully."""
        frame = ar.from_pandas(pd.DataFrame())
        table = to_arrow(frame)
        assert table.num_columns == 0

    def test_all_null_column(self):
        """to_arrow handles column with all null values."""
        frame = ar.from_pandas(pd.DataFrame({"val": [None, None, None]}))
        table = to_arrow(frame)
        assert table.num_columns == 1
        col = table.column(0)
        assert col.null_count == 3

    def test_single_row_frame(self):
        """to_arrow produces valid table for single row frame."""
        frame = ar.from_pandas(pd.DataFrame({"name": ["Alice"], "age": [30]}))
        table = to_arrow(frame)
        assert table.num_rows == 1
        assert table.num_columns == 2

    def test_string_dtype_preservation(self):
        """to_arrow preserves string data correctly."""
        frame = ar.from_pandas(pd.DataFrame({"name": ["Alice", "Bob", "Charlie"]}))
        table = to_arrow(frame)
        assert table.num_columns == 1
        assert table.num_rows == 3
        assert table.column(0).to_pylist() == ["Alice", "Bob", "Charlie"]

    def test_int_dtype_preservation(self):
        """to_arrow preserves integer data correctly."""
        frame = ar.from_pandas(pd.DataFrame({"count": [1, 2, 3, 4, 5]}))
        table = to_arrow(frame)
        assert table.num_columns == 1
        assert table.num_rows == 5
        assert table.column(0).to_pylist() == [1, 2, 3, 4, 5]

    def test_float_dtype_with_nan(self):
        """to_arrow handles float column with NaN values."""
        frame = ar.from_pandas(pd.DataFrame({"val": [1.0, float("nan"), 3.0]}))
        table = to_arrow(frame)
        assert table.num_columns == 1
        assert table.num_rows == 3

    def test_bool_dtype_preservation(self):
        """to_arrow preserves boolean data correctly."""
        frame = ar.from_pandas(pd.DataFrame({"active": [True, False, True]}))
        table = to_arrow(frame)
        assert table.num_columns == 1
        assert table.num_rows == 3
        assert table.column(0).to_pylist() == [True, False, True]

    def test_mixed_columns(self):
        """to_arrow handles frame with mixed dtype columns."""
        frame = ar.from_pandas(
            pd.DataFrame(
                {"id": [1, 2], "name": ["Alice", "Bob"], "active": [True, False]}
            )
        )
        table = to_arrow(frame)
        assert table.num_columns == 3
        assert table.num_rows == 2

    def test_empty_string_values(self):
        """to_arrow handles empty string values correctly."""
        frame = ar.from_pandas(pd.DataFrame({"name": ["Alice", "", "Charlie"]}))
        table = to_arrow(frame)
        assert table.num_columns == 1
        assert table.num_rows == 3
        assert table.column(0).to_pylist() == ["Alice", "", "Charlie"]

    def test_special_characters_in_strings(self):
        """to_arrow handles special characters in string values."""
        frame = ar.from_pandas(
            pd.DataFrame({"text": ["Hello\nWorld", "Tab\tHere", 'Quote"Test']})
        )
        table = to_arrow(frame)
        assert table.num_columns == 1
        assert table.num_rows == 3

    def test_negative_numbers(self):
        """to_arrow handles negative numeric values."""
        frame = ar.from_pandas(pd.DataFrame({"val": [-10, -5, 0, 5, 10]}))
        table = to_arrow(frame)
        assert table.num_columns == 1
        assert table.num_rows == 5
        assert table.column(0).to_pylist() == [-10, -5, 0, 5, 10]

    def test_large_integers(self):
        """to_arrow handles large integer values."""
        frame = ar.from_pandas(pd.DataFrame({"val": [10**9, 10**10, 10**11]}))
        table = to_arrow(frame)
        assert table.num_columns == 1
        assert table.num_rows == 3
