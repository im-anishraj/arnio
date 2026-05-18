"""Tests for arnio.to_numpy — DataFrame-to-NumPy conversion helper."""

import numpy as np
import pandas as pd
import pytest

import arnio as ar


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_frame(**kwargs) -> ar.ArFrame:
    """Shorthand: build an ArFrame from keyword column data."""
    return ar.from_pandas(pd.DataFrame(kwargs))


# ---------------------------------------------------------------------------
# Selected numeric columns
# ---------------------------------------------------------------------------

class TestSelectedNumericColumns:
    def test_explicit_int_and_float(self):
        frame = _make_frame(name=["Alice", "Bob"], age=[30, 25], score=[95.5, 87.0])
        result = ar.to_numpy(frame, columns=["age", "score"])

        expected = np.array([[30.0, 95.5], [25.0, 87.0]])
        np.testing.assert_array_equal(result, expected)
        assert result.dtype == np.float64

    def test_auto_select_numeric_columns(self):
        frame = _make_frame(name=["Alice", "Bob"], age=[30, 25], score=[95.5, 87.0])
        result = ar.to_numpy(frame)

        # Should pick age and score, skip name
        assert result.shape == (2, 2)
        np.testing.assert_array_equal(result[:, 0], [30.0, 25.0])
        np.testing.assert_array_equal(result[:, 1], [95.5, 87.0])

    def test_single_column_returns_2d(self):
        frame = _make_frame(x=[1, 2, 3])
        result = ar.to_numpy(frame, columns=["x"])

        assert result.shape == (3, 1)
        np.testing.assert_array_equal(result[:, 0], [1.0, 2.0, 3.0])


# ---------------------------------------------------------------------------
# Missing columns
# ---------------------------------------------------------------------------

class TestMissingColumns:
    def test_single_missing_column(self):
        frame = _make_frame(x=[1, 2])
        with pytest.raises(ValueError, match="Unknown columns.*nonexistent"):
            ar.to_numpy(frame, columns=["nonexistent"])

    def test_multiple_missing_columns(self):
        frame = _make_frame(x=[1, 2])
        with pytest.raises(ValueError, match="Unknown columns"):
            ar.to_numpy(frame, columns=["a", "b", "c"])

    def test_mix_of_valid_and_missing(self):
        frame = _make_frame(x=[1, 2], y=[3, 4])
        with pytest.raises(ValueError, match="Unknown columns.*missing"):
            ar.to_numpy(frame, columns=["x", "missing"])


# ---------------------------------------------------------------------------
# Mixed / non-numeric columns
# ---------------------------------------------------------------------------

class TestNonNumericColumns:
    def test_string_column_raises_by_default(self):
        frame = _make_frame(name=["Alice", "Bob"], age=[30, 25])
        with pytest.raises(TypeError, match="Non-numeric columns.*name"):
            ar.to_numpy(frame, columns=["name", "age"])

    def test_allow_non_numeric_skips_strings(self):
        frame = _make_frame(name=["Alice", "Bob"], age=[30, 25], score=[1.0, 2.0])
        result = ar.to_numpy(
            frame, columns=["name", "age", "score"], allow_non_numeric=True
        )

        # name should be filtered out, leaving age and score
        assert result.shape == (2, 2)
        np.testing.assert_array_equal(result[:, 0], [30.0, 25.0])
        np.testing.assert_array_equal(result[:, 1], [1.0, 2.0])

    def test_all_non_numeric_with_allow_raises(self):
        frame = _make_frame(a=["x", "y"], b=["p", "q"])
        with pytest.raises(ValueError, match="All selected columns are non-numeric"):
            ar.to_numpy(frame, columns=["a", "b"], allow_non_numeric=True)

    def test_auto_select_only_strings_raises(self):
        frame = _make_frame(a=["x", "y"], b=["p", "q"])
        with pytest.raises(ValueError, match="No numeric columns found"):
            ar.to_numpy(frame)

    def test_bool_column_widened_to_float(self):
        df = pd.DataFrame({"flag": pd.Series([True, False, True], dtype="boolean")})
        frame = ar.from_pandas(df)
        result = ar.to_numpy(frame, columns=["flag"])

        np.testing.assert_array_equal(result[:, 0], [1.0, 0.0, 1.0])
        assert result.dtype == np.float64


# ---------------------------------------------------------------------------
# Null handling
# ---------------------------------------------------------------------------

class TestNullHandling:
    def test_default_nan_for_nulls(self):
        df = pd.DataFrame({"x": pd.Series([1, pd.NA, 3], dtype=pd.Int64Dtype())})
        frame = ar.from_pandas(df)
        result = ar.to_numpy(frame, columns=["x"])

        assert np.isnan(result[1, 0])
        assert result[0, 0] == 1.0
        assert result[2, 0] == 3.0

    def test_custom_sentinel_for_nulls(self):
        df = pd.DataFrame({"x": pd.Series([1, pd.NA, 3], dtype=pd.Int64Dtype())})
        frame = ar.from_pandas(df)
        result = ar.to_numpy(frame, columns=["x"], null_value=-1.0)

        np.testing.assert_array_equal(result[:, 0], [1.0, -1.0, 3.0])

    def test_float_column_nulls(self):
        df = pd.DataFrame({"y": [1.5, None, 3.5]})
        frame = ar.from_pandas(df)
        result = ar.to_numpy(frame, columns=["y"])

        assert result[0, 0] == 1.5
        assert np.isnan(result[1, 0])
        assert result[2, 0] == 3.5

    def test_bool_column_null_uses_sentinel(self):
        df = pd.DataFrame(
            {"flag": pd.Series([True, pd.NA, False], dtype="boolean")}
        )
        frame = ar.from_pandas(df)
        result = ar.to_numpy(frame, columns=["flag"], null_value=-99.0)

        np.testing.assert_array_equal(result[:, 0], [1.0, -99.0, 0.0])

    def test_all_nulls(self):
        df = pd.DataFrame({"x": pd.Series([pd.NA, pd.NA], dtype=pd.Int64Dtype())})
        frame = ar.from_pandas(df)
        result = ar.to_numpy(frame, columns=["x"])

        assert result.shape == (2, 1)
        assert np.isnan(result[0, 0])
        assert np.isnan(result[1, 0])


# ---------------------------------------------------------------------------
# Empty inputs
# ---------------------------------------------------------------------------

class TestEmptyInputs:
    def test_zero_row_frame_auto_select_raises(self):
        """Empty frames lose numeric dtype during from_pandas; auto-select finds nothing."""
        df = pd.DataFrame(
            {"x": pd.Series([], dtype="int64"), "y": pd.Series([], dtype="float64")}
        )
        frame = ar.from_pandas(df)
        # C++ core infers empty columns as string, so no numeric cols to auto-select
        with pytest.raises(ValueError, match="No numeric columns found"):
            ar.to_numpy(frame)

    def test_zero_row_via_drop_nulls(self):
        """Create a truly empty numeric frame by dropping all rows."""
        df = pd.DataFrame({"x": pd.Series([pd.NA], dtype=pd.Int64Dtype())})
        frame = ar.from_pandas(df)
        cleaned = ar.drop_nulls(frame)

        assert cleaned.shape[0] == 0
        result = ar.to_numpy(cleaned, columns=["x"])
        assert result.shape == (0, 1)
        assert result.dtype == np.float64



# ---------------------------------------------------------------------------
# Row-order preservation
# ---------------------------------------------------------------------------

class TestRowOrderPreservation:
    def test_values_match_insertion_order(self):
        values = [42, 7, 99, 3, 15]
        frame = _make_frame(v=values)
        result = ar.to_numpy(frame, columns=["v"])

        np.testing.assert_array_equal(result[:, 0], [float(v) for v in values])

    def test_multi_column_order(self):
        frame = _make_frame(a=[10, 20, 30], b=[1.1, 2.2, 3.3])
        result = ar.to_numpy(frame, columns=["a", "b"])

        np.testing.assert_array_equal(result[0], [10.0, 1.1])
        np.testing.assert_array_equal(result[1], [20.0, 2.2])
        np.testing.assert_array_equal(result[2], [30.0, 3.3])

    def test_column_selection_order_respected(self):
        """Columns appear in the array in the order they were requested."""
        frame = _make_frame(a=[1, 2], b=[3, 4], c=[5, 6])
        result_ab = ar.to_numpy(frame, columns=["a", "b"])
        result_ba = ar.to_numpy(frame, columns=["b", "a"])

        np.testing.assert_array_equal(result_ab[:, 0], [1.0, 2.0])
        np.testing.assert_array_equal(result_ab[:, 1], [3.0, 4.0])
        np.testing.assert_array_equal(result_ba[:, 0], [3.0, 4.0])
        np.testing.assert_array_equal(result_ba[:, 1], [1.0, 2.0])


# ---------------------------------------------------------------------------
# Pandas accessor integration
# ---------------------------------------------------------------------------

class TestAccessor:
    def test_accessor_to_numpy(self):
        df = pd.DataFrame({"x": [1, 2, 3], "y": [4.0, 5.0, 6.0]})
        result = df.arnio.to_numpy(columns=["x"])

        assert isinstance(result, np.ndarray)
        assert result.shape == (3, 1)
        np.testing.assert_array_equal(result[:, 0], [1.0, 2.0, 3.0])

    def test_accessor_auto_select(self):
        df = pd.DataFrame(
            {"name": ["Alice", "Bob"], "age": [30, 25], "score": [95.5, 87.0]}
        )
        result = df.arnio.to_numpy()

        assert result.shape == (2, 2)
        np.testing.assert_array_equal(result[:, 0], [30.0, 25.0])
        np.testing.assert_array_equal(result[:, 1], [95.5, 87.0])

    def test_accessor_null_value(self):
        df = pd.DataFrame({"x": pd.Series([1, pd.NA, 3], dtype=pd.Int64Dtype())})
        result = df.arnio.to_numpy(null_value=-1.0)

        np.testing.assert_array_equal(result[:, 0], [1.0, -1.0, 3.0])
