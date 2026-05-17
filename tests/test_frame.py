"""Tests for ArFrame.memory_usage(deep=False/True), preview(), and select_columns()."""

import pandas as pd
import pytest

import arnio as ar


class TestMemoryUsageShallow:
    """memory_usage() with default deep=False — backward-compatible behaviour."""

    def test_returns_positive_int_for_int_frame(self):
        df = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})
        frame = ar.from_pandas(df)
        result = frame.memory_usage()
        assert isinstance(result, int)
        assert result > 0

    def test_returns_positive_int_for_float_frame(self):
        df = pd.DataFrame({"x": [1.1, 2.2, 3.3]})
        frame = ar.from_pandas(df)
        assert frame.memory_usage() > 0

    def test_returns_positive_int_for_bool_frame(self):
        df = pd.DataFrame({"flag": [True, False, True]})
        frame = ar.from_pandas(df)
        assert frame.memory_usage() > 0

    def test_returns_positive_int_for_string_frame(self):
        df = pd.DataFrame({"name": ["Alice", "Bob", "Charlie"]})
        frame = ar.from_pandas(df)
        assert frame.memory_usage() > 0

    def test_returns_positive_int_for_mixed_frame(self):
        df = pd.DataFrame(
            {
                "name": ["Alice", "Bob"],
                "age": [30, 25],
                "score": [9.5, 8.1],
                "active": [True, False],
            }
        )
        frame = ar.from_pandas(df)
        assert frame.memory_usage() > 0

    def test_empty_frame_returns_nonnegative(self):
        """An empty ArFrame must not raise and must return a non-negative int."""
        frame = ar.from_pandas(pd.DataFrame())
        result = frame.memory_usage()
        assert isinstance(result, int)
        assert result >= 0

    def test_explicit_false_matches_default(self):
        """memory_usage(deep=False) must equal memory_usage()."""
        df = pd.DataFrame({"text": ["hello", "world"]})
        frame = ar.from_pandas(df)
        assert frame.memory_usage(deep=False) == frame.memory_usage()


class TestMemoryUsageDeep:
    """memory_usage(deep=True) — precise estimate including string heap bytes."""

    def test_deep_greater_than_shallow_for_string_column(self):
        """For a string frame deep=True must report MORE bytes than deep=False."""
        # Use strings long enough to guarantee heap allocation (> SSO buffer).
        long_strings = ["x" * 100, "y" * 200, "z" * 300]
        df = pd.DataFrame({"text": long_strings})
        frame = ar.from_pandas(df)
        assert frame.memory_usage(deep=True) > frame.memory_usage(deep=False)

    def test_deep_equals_shallow_for_int_column(self):
        """For numeric columns deep has no extra effect — both values are equal."""
        df = pd.DataFrame({"n": [1, 2, 3, 4, 5]})
        frame = ar.from_pandas(df)
        assert frame.memory_usage(deep=True) == frame.memory_usage(deep=False)

    def test_deep_equals_shallow_for_float_column(self):
        df = pd.DataFrame({"f": [1.0, 2.0, 3.0]})
        frame = ar.from_pandas(df)
        assert frame.memory_usage(deep=True) == frame.memory_usage(deep=False)

    def test_deep_equals_shallow_for_bool_column(self):
        df = pd.DataFrame({"b": [True, False, True]})
        frame = ar.from_pandas(df)
        assert frame.memory_usage(deep=True) == frame.memory_usage(deep=False)

    def test_deep_greater_for_mixed_frame_with_strings(self):
        """Mixed frame: deep > shallow because of string columns."""
        df = pd.DataFrame(
            {
                "name": ["Alice" * 10, "Bob" * 20],
                "age": [30, 25],
            }
        )
        frame = ar.from_pandas(df)
        assert frame.memory_usage(deep=True) > frame.memory_usage(deep=False)

    def test_longer_strings_use_more_deep_memory(self):
        """A frame with longer strings must report more deep memory."""
        short_frame = ar.from_pandas(pd.DataFrame({"t": ["hi", "ok"]}))
        long_frame = ar.from_pandas(pd.DataFrame({"t": ["x" * 500, "y" * 500]}))
        assert long_frame.memory_usage(deep=True) > short_frame.memory_usage(deep=True)

    def test_deep_returns_int(self):
        df = pd.DataFrame({"s": ["hello", "world"]})
        frame = ar.from_pandas(df)
        assert isinstance(frame.memory_usage(deep=True), int)

    def test_empty_frame_deep_returns_nonnegative(self):
        frame = ar.from_pandas(pd.DataFrame())
        assert frame.memory_usage(deep=True) >= 0

    def test_null_string_column_deep_does_not_crash(self):
        """Columns with null strings must not raise under deep=True."""
        df = pd.DataFrame({"name": ["Alice", None, "Charlie"]}, dtype=object)
        frame = ar.from_pandas(df)
        result = frame.memory_usage(deep=True)
        assert isinstance(result, int)
        assert result > 0


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
