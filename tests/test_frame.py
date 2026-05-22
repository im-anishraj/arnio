"""
Tests for ArFrame.preview()
"""

import pandas as pd
import pytest

import arnio as ar
from arnio._core import _Column, _DType, _Frame

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


def test_select_columns_native_path_avoids_pandas_roundtrip(monkeypatch):
    frame = ar.from_pandas(
        pd.DataFrame(
            {
                "name": ["alice", "bob"],
                "salary": [100, 200],
            }
        )
    )

    from arnio import convert

    original_to_pandas = convert.to_pandas

    def fail_to_pandas(_):
        raise AssertionError("native select_columns path should avoid to_pandas")

    monkeypatch.setattr(convert, "to_pandas", fail_to_pandas)

    selected = frame.select_columns(["salary", "name"])

    df = original_to_pandas(selected)

    assert list(df.columns) == ["salary", "name"]


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


def test_str_truncates_long_column_names():
    df = pd.DataFrame({"very_very_very_long_column_name_for_testing": [1, 2]})

    frame = ar.from_pandas(df)

    result = str(frame)

    assert "very_very_very_long_..." in result

    columns_line = [line for line in result.split("\n") if line.startswith("Columns:")][
        0
    ]

    assert "very_very_very_long_column_name_for_testing" not in columns_line

    assert frame.columns == ["very_very_very_long_column_name_for_testing"]


def test_str_keeps_normal_column_names():
    df = pd.DataFrame({"name": [1, 2]})

    frame = ar.from_pandas(df)

    result = str(frame)

    assert "name" in result
    assert "..." not in result


def test_add_column_accepts_matching_lengths():
    from arnio._arnio_cpp import Column, DType, Frame

    frame = Frame()

    c1 = Column("a", DType.INT64)
    c1.push_back(1)
    c1.push_back(2)

    c2 = Column("b", DType.INT64)
    c2.push_back(10)
    c2.push_back(20)

    frame.add_column(c1)
    frame.add_column(c2)

    assert frame.shape() == (2, 2)


def test_add_column_rejects_mismatched_lengths():
    from arnio._arnio_cpp import Column, DType, Frame

    frame = Frame()

    c1 = Column("a", DType.INT64)
    c1.push_back(1)
    c1.push_back(2)
    c1.push_back(3)

    c2 = Column("b", DType.INT64)
    c2.push_back(10)

    frame.add_column(c1)

    with pytest.raises(ValueError, match="expected"):
        frame.add_column(c2)


def test_add_column_allows_first_column_in_empty_frame():
    from arnio._arnio_cpp import Column, DType, Frame

    frame = Frame()

    c1 = Column("a", DType.INT64)
    c1.push_back(1)

    frame.add_column(c1)

    assert frame.shape() == (1, 1)


def test_cpp_frame_explicit_zero_rows_rejects_nonempty_first_column():
    frame = _Frame(0)
    column = _Column("a", _DType.INT64)
    column.push_back(1)

    with pytest.raises(ValueError, match="row count"):
        frame.add_column(column)


 main
# ── Zero-column frame tests ───────────────────────────────────────────────────


def test_cpp_frame_with_explicit_row_count_preserves_shape():
    """Test that Frame(size_t row_count) creates a frame with correct row count."""
    frame = _Frame(5)
    assert frame.num_rows() == 5
    assert frame.num_cols() == 0
    assert frame.shape() == (5, 0)


def test_cpp_frame_from_empty_vector_has_unknown_row_count():
    """Test that Frame({}) initially has unknown row count and can accept first column."""
    frame = _Frame([])
    assert frame.num_rows() == 0
    assert frame.num_cols() == 0

    # First column should set the row count
    column = _Column("a", _DType.INT64)
    column.push_back(1)
    column.push_back(2)
    column.push_back(3)

    frame.add_column(column)

    assert frame.num_rows() == 3
    assert frame.num_cols() == 1


def test_cpp_frame_select_columns_preserves_row_count_with_zero_cols():
    """Test that select_columns([]) preserves row count."""
    column = _Column("a", _DType.INT64)
    column.push_back(1)
    column.push_back(2)

    frame = _Frame([column])
    assert frame.shape() == (2, 1)

    # Select no columns - should preserve row count
    empty_frame = frame.select_columns([])
    assert empty_frame.shape() == (2, 0)
    assert empty_frame.num_rows() == 2


def test_cpp_frame_clone_preserves_row_count_with_zero_cols():
    """Test that clone() preserves row count for zero-column frames."""
    frame_with_rows = _Frame(3)
    cloned = frame_with_rows.clone()
    assert cloned.shape() == (3, 0)


def test_arframe_pandas_roundtrip_zero_columns():
    """Test that pandas round-trip preserves zero-column frames with row count."""
    # Create an empty-column frame with 3 rows
    df_empty = pd.DataFrame(index=range(3))
    frame = ar.from_pandas(df_empty)
    assert frame.shape == (3, 0)

    # Convert back to pandas
    df_result = ar.to_pandas(frame)
    assert df_result.shape == (3, 0)
    assert len(df_result.index) == 3


def test_arframe_drop_all_constant_columns_preserves_shape():
    """Test that drop_constant_columns preserves row count when all columns are dropped."""
    # All columns are constant
    frame = ar.from_pandas(pd.DataFrame({"a": [1, 1], "b": ["x", "x"]}))
    assert frame.shape == (2, 2)

    result = ar.drop_constant_columns(frame)
    assert result.shape == (2, 0)
    assert result.columns == []


def test_arframe_drop_partial_constant_columns():
    """Test drop_constant_columns with mixed constant and non-constant columns."""
    df = pd.DataFrame({"const": [1, 1, 1], "var": [1, 2, 3], "const2": [None, None, None]})
    frame = ar.from_pandas(df)

    result = ar.drop_constant_columns(frame)
    assert result.shape == (3, 1)
    assert result.columns == ["var"]


def test_arframe_zero_columns_shape_persists():
    """Test that a zero-column frame maintains its shape through operations."""
    df = pd.DataFrame({"c": [1, 1, 1]})  # Single constant column
    frame = ar.from_pandas(df)

    # Drop the only constant column
    result = ar.drop_constant_columns(frame)
    assert result.shape[0] == 3
    assert result.shape[1] == 0

    # Round-trip through pandas
    df_roundtrip = ar.to_pandas(result)
    assert df_roundtrip.shape == (3, 0)

    # Convert back to ArFrame
    frame_roundtrip = ar.from_pandas(df_roundtrip)
    assert frame_roundtrip.shape == (3, 0)


def test_arframe_select_columns_empty_on_multirow_frame():
    """Test that selecting no columns from a multi-row frame preserves row count via C++ path."""
    df = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})
    frame = ar.from_pandas(df)

    # The C++ select_columns should reject empty selection
    with pytest.raises(ValueError, match="cannot be empty"):
        frame.select_columns([])

def test_add_column_rejects_duplicate_name():
    from arnio._arnio_cpp import Column, DType, Frame

    frame = Frame()

    c1 = Column("a", DType.INT64)
    c1.push_back(1)
    c1.push_back(2)

    c2 = Column("a", DType.INT64)
    c2.push_back(3)
    c2.push_back(4)

    frame.add_column(c1)

    with pytest.raises(ValueError, match="already exists"):
        frame.add_column(c2)


# ArFrame.describe() Tests


def test_describe_sample_metrics(sample_csv):
    frame = ar.read_csv(sample_csv)
    stats = frame.describe()

    assert stats["age"]["count"] == 3.0
    assert stats["age"]["nulls"] == 0.0
    assert stats["age"]["mean"] == 30.0
    assert stats["age"]["min"] == 25.0
    assert stats["age"]["max"] == 35.0

    assert stats["name"]["count"] == 3.0
    assert stats["name"]["nulls"] == 0.0
    assert stats["name"]["unique"] == 3.0
    assert "mean" not in stats["name"]


def test_describe_excludes_null_values(csv_with_nulls):
    frame = ar.read_csv(csv_with_nulls)
    stats = frame.describe()

    assert stats["age"]["count"] == 3.0
    assert stats["age"]["nulls"] == 1.0
    assert stats["age"]["min"] == 25.0
    assert stats["age"]["max"] == 30.0
    assert stats["age"]["mean"] == pytest.approx(27.6666, rel=1e-3)

    assert stats["name"]["count"] == 3.0
    assert stats["name"]["nulls"] == 1.0
    assert stats["name"]["unique"] == 3.0


def test_describe_empty_frame_edge_case(tmp_path):
    csv_path = tmp_path / "empty_input.csv"
    csv_path.write_text("name,age\n")

    frame = ar.read_csv(str(csv_path))
    stats = frame.describe()

    assert "name" in stats
    assert "age" in stats

    for col in frame.columns:
        assert stats[col]["count"] == 0.0
        assert stats[col]["nulls"] == 0.0

        if "mean" in stats[col]:
            assert stats[col]["mean"] == 0.0
            assert stats[col]["min"] == 0.0
            assert stats[col]["max"] == 0.0
        elif "unique" in stats[col]:
            assert stats[col]["unique"] == 0.0


def test_describe_dictionary_subclass_repr(sample_csv):
    frame = ar.read_csv(sample_csv)
    stats = frame.describe()

    assert stats["age"]["count"] == 3.0
    assert "{\n" in repr(stats)


def test_describe_all_numeric_columns(large_csv):
    frame = ar.read_csv(large_csv)

    numeric_frame = frame.select_dtypes(include=["int64", "float64"])
    stats = numeric_frame.describe()

    assert list(stats.keys()) == ["id", "value"]

    for col in ["id", "value"]:
        metric_keys = list(stats[col].keys())
        assert metric_keys == ["count", "nulls", "mean", "min", "max"]


def test_describe_all_string_columns(csv_with_whitespace):
    frame = ar.read_csv(csv_with_whitespace)
    stats = frame.describe()

    assert list(stats.keys()) == ["name", "city"]

    for col in ["name", "city"]:
        metric_keys = list(stats[col].keys())
        assert metric_keys == ["count", "nulls", "unique"]


# ── drop_columns ──────────────────────────────────────────────────────────────


class TestDropColumns:
    """Tests for ArFrame.drop_columns()."""

    def test_drop_single_column(self):
        df = pd.DataFrame({"a": [1, 2], "b": [3, 4], "c": [5, 6]})
        frame = ar.from_pandas(df)
        result = frame.drop_columns(["b"])
        assert result.columns == ["a", "c"]
        assert result.shape == (2, 2)

    def test_drop_multiple_columns(self):
        df = pd.DataFrame({"a": [1], "b": [2], "c": [3], "d": [4]})
        frame = ar.from_pandas(df)
        result = frame.drop_columns(["a", "c"])
        assert result.columns == ["b", "d"]

    def test_drop_preserves_column_order(self):
        df = pd.DataFrame({"x": [1], "y": [2], "z": [3]})
        frame = ar.from_pandas(df)
        result = frame.drop_columns(["y"])
        assert result.columns == ["x", "z"]

    def test_drop_empty_list_returns_copy(self):
        df = pd.DataFrame({"a": [1, 2], "b": [3, 4]})
        frame = ar.from_pandas(df)
        result = frame.drop_columns([])
        assert result.columns == ["a", "b"]
        assert result.shape == frame.shape

    def test_drop_all_columns_returns_empty_frame(self):
        df = pd.DataFrame({"a": [1], "b": [2]})
        frame = ar.from_pandas(df)
        result = frame.drop_columns(["a", "b"])
        assert result.columns == []
        assert result.shape == (1, 0)

    def test_drop_duplicate_names_in_cols(self):
        df = pd.DataFrame({"a": [1], "b": [2], "c": [3]})
        frame = ar.from_pandas(df)
        result = frame.drop_columns(["a", "a"])
        assert result.columns == ["b", "c"]

    def test_drop_unknown_column_raises_value_error(self):
        df = pd.DataFrame({"a": [1], "b": [2]})
        frame = ar.from_pandas(df)
        with pytest.raises(ValueError, match="Unknown column"):
            frame.drop_columns(["z"])

    def test_drop_non_list_raises_type_error(self):
        df = pd.DataFrame({"a": [1]})
        frame = ar.from_pandas(df)
        with pytest.raises(TypeError, match="cols must be a list"):
            frame.drop_columns("a")

    def test_drop_non_string_items_raises_type_error(self):
        df = pd.DataFrame({"a": [1], "b": [2]})
        frame = ar.from_pandas(df)
        with pytest.raises(TypeError, match="strings"):
            frame.drop_columns([1, 2])

    def test_drop_does_not_mutate_original(self):
        df = pd.DataFrame({"a": [1], "b": [2]})
        frame = ar.from_pandas(df)
        frame.drop_columns(["a"])
        assert frame.columns == ["a", "b"]
 main
