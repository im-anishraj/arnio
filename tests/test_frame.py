"""Tests for ArFrame.to_numpy()."""

import numpy as np
import pandas as pd
import pytest

import arnio as ar


class TestToNumpy:

    # --- Happy path ---

    def test_integer_frame(self):
        frame = ar.from_pandas(pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]}))
        result = frame.to_numpy()
        assert isinstance(result, np.ndarray)
        assert result.shape == (3, 2)
        assert result.dtype == np.int64
        assert result[0, 0] == 1
        assert result[2, 1] == 6

    def test_float_frame(self):
        frame = ar.from_pandas(pd.DataFrame({"x": [1.5, 2.5], "y": [3.5, 4.5]}))
        result = frame.to_numpy()
        assert isinstance(result, np.ndarray)
        assert result.shape == (2, 2)
        assert result.dtype == np.float64
        assert result[0, 0] == 1.5

    def test_bool_frame(self):
        frame = ar.from_pandas(
            pd.DataFrame({"p": [True, False, True], "q": [False, True, False]})
        )
        result = frame.to_numpy()
        assert isinstance(result, np.ndarray)
        assert result.shape == (3, 2)
        assert result.dtype == np.bool_

    def test_mixed_numeric_frame(self):
        """Int and float columns together — NumPy promotes to float64."""
        frame = ar.from_pandas(pd.DataFrame({"a": [1, 2, 3], "b": [1.1, 2.2, 3.3]}))
        result = frame.to_numpy()
        assert result.shape == (3, 2)
        assert result.dtype == np.float64  # int promoted to float64

    def test_returns_correct_values(self):
        frame = ar.from_pandas(pd.DataFrame({"a": [10, 20], "b": [30, 40]}))
        result = frame.to_numpy()
        assert result[0, 0] == 10
        assert result[0, 1] == 30
        assert result[1, 0] == 20
        assert result[1, 1] == 40

    def test_column_order_preserved(self):
        """Columns should appear in the same order as frame.columns."""
        frame = ar.from_pandas(pd.DataFrame({"z": [1, 2], "a": [3, 4]}))
        result = frame.to_numpy()
        assert result[0, 0] == 1  # z comes first
        assert result[0, 1] == 3  # a comes second

    def test_result_is_2d(self):
        frame = ar.from_pandas(pd.DataFrame({"a": [1, 2, 3]}))
        result = frame.to_numpy()
        assert result.ndim == 2

    # --- Null handling ---

    def test_nulls_without_fill_value_raises(self):
        frame = ar.from_pandas(
            pd.DataFrame({"a": [1, None, 3], "b": [4, 5, 6]}, dtype=object)
        )
        with pytest.raises(ValueError, match="null values"):
            frame.to_numpy()

    def test_nulls_with_fill_value(self):
        frame = ar.from_pandas(
            pd.DataFrame({"a": [1, None, 3], "b": [4, 5, 6]}, dtype=object)
        )
        result = frame.to_numpy(fill_value=0)
        assert result[1, 0] == 0

    def test_fill_value_does_not_affect_non_null(self):
        frame = ar.from_pandas(pd.DataFrame({"a": [1, None, 3]}, dtype=object))
        result = frame.to_numpy(fill_value=99)
        assert result[0, 0] == 1
        assert result[2, 0] == 3

    # --- TypeError cases ---

    def test_string_column_raises(self):
        frame = ar.from_pandas(
            pd.DataFrame({"name": ["Alice", "Bob"], "age": [25, 30]})
        )
        with pytest.raises(TypeError, match="to_numpy()"):
            frame.to_numpy()

    def test_all_string_frame_raises(self):
        frame = ar.from_pandas(pd.DataFrame({"a": ["x", "y"], "b": ["p", "q"]}))
        with pytest.raises(TypeError, match="to_numpy()"):
            frame.to_numpy()

    def test_mixed_dtype_frame_raises(self):
        """Any string column in an otherwise numeric frame should raise."""
        frame = ar.from_pandas(
            pd.DataFrame({"a": [1, 2], "b": [1.5, 2.5], "c": ["x", "y"]})
        )
        with pytest.raises(TypeError):
            frame.to_numpy()

    def test_error_message_contains_column_name(self):
        frame = ar.from_pandas(pd.DataFrame({"score": [1, 2], "label": ["a", "b"]}))
        with pytest.raises(TypeError, match="label"):
            frame.to_numpy()

    # --- Edge cases ---

    def test_empty_frame(self):
        """Zero columns → shape (0, 0)."""
        frame = ar.from_pandas(pd.DataFrame({}))
        result = frame.to_numpy()
        assert isinstance(result, np.ndarray)
        assert result.shape == (0, 0)

    def test_zero_row_frame(self):
        """Zero rows but n cols → shape (0, n_cols)."""
        df = pd.DataFrame(
            {"a": pd.Series([], dtype=int), "b": pd.Series([], dtype=float)}
        )
        frame = ar.from_pandas(df)
        result = frame.to_numpy()
        assert result.shape == (0, 2)

    def test_single_column(self):
        frame = ar.from_pandas(pd.DataFrame({"a": [1, 2, 3]}))
        result = frame.to_numpy()
        assert result.shape == (3, 1)

    def test_single_row(self):
        frame = ar.from_pandas(pd.DataFrame({"a": [42], "b": [99]}))
        result = frame.to_numpy()
        assert result.shape == (1, 2)

    def test_single_cell(self):
        frame = ar.from_pandas(pd.DataFrame({"a": [7]}))
        result = frame.to_numpy()
        assert result.shape == (1, 1)
        assert result[0, 0] == 7
