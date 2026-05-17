"""
Tests for ArFrame.preview()
"""

import numpy as np
import pandas as pd
import pytest

import arnio as ar

# ── Normal behaviour ──────────────────────────────────────────────────────────


def test_preview_returns_string(sample_csv):
    frame = ar.read_csv(sample_csv)
    result = frame.preview()
    assert isinstance(result, str)


def test_preview_contains_word_preview(sample_csv):
    frame = ar.read_csv(sample_csv)
    result = frame.preview()
    assert "preview" in result.lower()


def test_preview_contains_column_names(sample_csv):
    frame = ar.read_csv(sample_csv)
    result = frame.preview()
    for col in frame.columns:
        assert col in result  # "name", "age", "email", "active" all appear


def test_preview_default_shows_three_rows(sample_csv):
    # sample_csv only has 3 rows, so default n=5 clamps to 3
    frame = ar.read_csv(sample_csv)
    result = frame.preview()
    assert "showing 3 of 3" in result


def test_preview_custom_n(sample_csv):
    frame = ar.read_csv(sample_csv)
    result = frame.preview(n=2)
    assert "showing 2 of 3" in result


def test_preview_n_equals_one(sample_csv):
    frame = ar.read_csv(sample_csv)
    result = frame.preview(n=1)
    assert "showing 1 of 3" in result


# ── Edge cases ────────────────────────────────────────────────────────────────


def test_preview_n_exceeds_row_count(sample_csv):
    frame = ar.read_csv(sample_csv)
    result = frame.preview(n=9999)
    assert "showing 3 of 3" in result  # clamps, doesn't crash


def test_preview_n_equals_exact_row_count(sample_csv):
    frame = ar.read_csv(sample_csv)
    result = frame.preview(n=3)
    assert "showing 3 of 3" in result


def test_preview_with_nulls(csv_with_nulls):
    # Should not crash on missing values
    frame = ar.read_csv(csv_with_nulls)
    result = frame.preview()
    assert isinstance(result, str)


def test_preview_large_csv(large_csv):
    # 1000 rows — default should only show 5
    frame = ar.read_csv(large_csv)
    result = frame.preview()
    assert "showing 5 of 1000" in result


# ── Invalid inputs ────────────────────────────────────────────────────────────


def test_preview_invalid_n_zero(sample_csv):
    frame = ar.read_csv(sample_csv)
    with pytest.raises(ValueError):
        frame.preview(n=0)


def test_preview_invalid_n_negative(sample_csv):
    frame = ar.read_csv(sample_csv)
    with pytest.raises(ValueError):
        frame.preview(n=-1)


def test_preview_invalid_n_string(sample_csv):
    frame = ar.read_csv(sample_csv)
    with pytest.raises(ValueError):
        frame.preview(n="five")


def test_preview_invalid_n_float(sample_csv):
    frame = ar.read_csv(sample_csv)
    with pytest.raises(ValueError):
        frame.preview(n=2.5)


def test_preview_invalid_n_bool(sample_csv):
    frame = ar.read_csv(sample_csv)
    with pytest.raises(ValueError):
        frame.preview(n=True)  # bool is subclass of int — must still be rejected


def test_preview_invalid_n_none(sample_csv):
    frame = ar.read_csv(sample_csv)
    with pytest.raises(ValueError):
        frame.preview(n=None)


def test_select_columns_valid():
    df = pd.DataFrame(
        {
            "name": ["Alice", "Bob"],
            "age": [25, 30],
            "salary": [50000, 60000],
        }
    )
    frame = ar.from_pandas(df)
    selected = frame.select_columns(["name", "salary"])
    assert selected.columns == ["name", "salary"]
    assert selected.shape == (2, 2)


def test_select_columns_preserves_order():
    df = pd.DataFrame(
        {
            "name": ["Alice"],
            "age": [25],
            "salary": [50000],
        }
    )
    frame = ar.from_pandas(df)
    selected = frame.select_columns(["salary", "name"])
    assert selected.columns == ["salary", "name"]


def test_select_columns_unknown_column():
    df = pd.DataFrame(
        {
            "name": ["Alice"],
            "age": [25],
        }
    )
    frame = ar.from_pandas(df)
    with pytest.raises(ValueError, match="Unknown columns"):
        frame.select_columns(["name", "salary"])


def test_select_columns_empty():
    df = pd.DataFrame(
        {
            "name": ["Alice"],
        }
    )
    frame = ar.from_pandas(df)
    with pytest.raises(ValueError, match="cannot be empty"):
        frame.select_columns([])


def test_select_columns_duplicate_names():
    df = pd.DataFrame(
        {
            "name": ["Alice"],
            "age": [25],
        }
    )
    frame = ar.from_pandas(df)
    with pytest.raises(ValueError, match="Duplicate column names"):
        frame.select_columns(["name", "name"])


def test_select_columns_string_input():
    df = pd.DataFrame({"name": ["Alice"]})
    frame = ar.from_pandas(df)
    with pytest.raises(TypeError, match="not a string"):
        frame.select_columns("name")


def test_select_columns_non_string_items():
    df = pd.DataFrame({"name": ["Alice"]})
    frame = ar.from_pandas(df)
    with pytest.raises(TypeError, match="must be strings"):
        frame.select_columns(["name", 123])


def test_select_columns_invalid_container():
    df = pd.DataFrame({"name": ["Alice"]})
    frame = ar.from_pandas(df)
    with pytest.raises(TypeError, match="list or tuple"):
        frame.select_columns({"name"})


def test_select_columns_empty_frame():
    df = pd.DataFrame(columns=["name", "age"])
    frame = ar.from_pandas(df)
    selected = frame.select_columns(["name"])
    assert selected.columns == ["name"]
    assert selected.shape == (0, 1)


class TestArFrame:
    """Test ArFrame properties and methods."""

    def test_is_empty_true(self, tmp_path):
        """Test is_empty returns True for frame with zero rows."""
        csv_path = tmp_path / "empty.csv"
        csv_path.write_text("name,age\n")  # Header only, no data rows

        frame = ar.read_csv(str(csv_path))
        assert frame.is_empty is True
        assert len(frame) == 0

    def test_is_empty_false(self, sample_csv):
        """Test is_empty returns False for frame with rows."""
        frame = ar.read_csv(sample_csv)
        assert frame.is_empty is False
        assert len(frame) > 0

    def test_is_empty_single_row(self, tmp_path):
        """Test is_empty with exactly one row."""
        csv_path = tmp_path / "single.csv"
        csv_path.write_text("name,age\nAlice,30\n")

        frame = ar.read_csv(str(csv_path))
        assert frame.is_empty is False
        assert len(frame) == 1


# ── to_numpy() tests ──────────────────────────────────────────────────────────


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
        assert result.dtype == np.float64

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
        assert result[0, 0] == 1
        assert result[0, 1] == 3

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
