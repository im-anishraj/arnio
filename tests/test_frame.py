"""
Tests for ArFrame.preview()
"""

import copy
import math

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

    # --- Equality tests ---

    def test_arframe_equality_same_values(self):
        frame1 = ar.ArFrame.from_records([{"a": 1, "b": "x"}])
        frame2 = ar.ArFrame.from_records([{"a": 1, "b": "x"}])
        assert frame1 == frame2

    def test_arframe_inequality_different_values(self):
        frame1 = ar.ArFrame.from_records([{"a": 1}])
        frame2 = ar.ArFrame.from_records([{"a": 2}])
        assert frame1 != frame2

    def test_arframe_inequality_different_columns(self):
        frame1 = ar.ArFrame.from_records([{"a": 1}])
        frame2 = ar.ArFrame.from_records([{"b": 1}])
        assert frame1 != frame2

    def test_arframe_inequality_different_column_order(self):
        frame1 = ar.ArFrame.from_records([{"a": 1, "b": 2}])
        frame2 = ar.ArFrame.from_records([{"b": 2, "a": 1}], columns=["b", "a"])
        assert frame1 != frame2

    def test_arframe_inequality_different_shape(self):
        frame1 = ar.ArFrame.from_records([{"a": 1}])
        frame2 = ar.ArFrame.from_records([{"a": 1}, {"a": 2}])
        assert frame1 != frame2

    def test_arframe_inequality_different_dtypes(self):
        frame1 = ar.ArFrame.from_records([{"a": 1}])
        frame2 = ar.ArFrame.from_records([{"a": 1.0}])
        assert frame1 != frame2

    def test_arframe_equality_with_nan(self):
        frame1 = ar.ArFrame.from_records([{"a": math.nan}])
        frame2 = ar.ArFrame.from_records([{"a": math.nan}])
        assert frame1 == frame2

    def test_arframe_equality_with_none(self):
        frame1 = ar.ArFrame.from_records([{"a": None}])
        frame2 = ar.ArFrame.from_records([{"a": None}])
        assert frame1 == frame2

    def test_arframe_inequality_non_arframe(self):
        frame = ar.ArFrame.from_records([{"a": 1}])
        result = frame.__eq__(123)
        assert result is NotImplemented

    def test_arframe_inequality_different_null_positions(self):
        frame1 = ar.ArFrame.from_records([{"a": None}, {"a": 1}])
        frame2 = ar.ArFrame.from_records([{"a": 1}, {"a": None}])
        assert frame1 != frame2

    def test_arframe_equality_is_reflexive(self):
        frame = ar.ArFrame.from_records([{"a": 1}])
        assert frame == frame

    def test_arframe_equality_is_symmetric(self):
        frame1 = ar.ArFrame.from_records([{"a": 1}])
        frame2 = ar.ArFrame.from_records([{"a": 1}])
        assert frame1 == frame2
        assert frame2 == frame1

    def test_arframe_equality_is_transitive(self):
        frame1 = ar.ArFrame.from_records([{"a": 1}])
        frame2 = ar.ArFrame.from_records([{"a": 1}])
        frame3 = ar.ArFrame.from_records([{"a": 1}])
        assert frame1 == frame2
        assert frame2 == frame3
        assert frame1 == frame3

    def test_arframe_equality_ignores_attrs(self):
        frame1 = ar.ArFrame.from_records([{"a": 1}])
        frame2 = ar.ArFrame.from_records([{"a": 1}])
        frame1._attrs["x"] = 1
        assert frame1 == frame2

    def test_empty_frames_are_equal(self):
        frame1 = ar.from_pandas(pd.DataFrame(columns=["a"]))
        frame2 = ar.from_pandas(pd.DataFrame(columns=["a"]))
        assert frame1 == frame2

    def test_empty_frames_different_columns_not_equal(self):
        frame1 = ar.from_pandas(pd.DataFrame(columns=["a"]))
        frame2 = ar.from_pandas(pd.DataFrame(columns=["b"]))
        assert frame1 != frame2

    def test_arframe_nan_not_equal_to_number(self):
        frame1 = ar.ArFrame.from_records([{"a": math.nan}])
        frame2 = ar.ArFrame.from_records([{"a": 1.0}])
        assert frame1 != frame2

    # --- Copy tests ---

    def test_arframe_shallow_copy(self):
        frame = ar.ArFrame.from_records([{"a": 1}])
        copied = copy.copy(frame)
        assert copied == frame
        assert copied is not frame
        assert copied._frame is frame._frame

    def test_arframe_deep_copy(self):
        frame = ar.ArFrame.from_records([{"a": 1}])
        copied = copy.deepcopy(frame)
        assert copied == frame
        assert copied is not frame
        assert copied._frame is not frame._frame

    def test_arframe_shallow_copy_attrs_shared(self):
        frame = ar.ArFrame.from_records([{"a": 1}])
        frame._attrs["x"] = [1, 2]
        copied = copy.copy(frame)
        assert copied._attrs == frame._attrs
        assert copied._attrs is not frame._attrs
        copied._attrs["x"].append(3)
        assert frame._attrs["x"] == [1, 2, 3]

    def test_arframe_deep_copy_attrs_independent(self):
        frame = ar.ArFrame.from_records([{"a": 1}])
        frame._attrs["x"] = [1, 2]
        copied = copy.deepcopy(frame)
        assert copied._attrs == frame._attrs
        assert copied._attrs is not frame._attrs
        assert copied._attrs["x"] is not frame._attrs["x"]
        copied._attrs["x"].append(3)
        assert frame._attrs["x"] == [1, 2]

    def test_arframe_deep_copy_nested_attrs_independent(self):
        frame = ar.ArFrame.from_records([{"a": 1}])
        frame._attrs["x"] = {"nested": [1, 2]}
        copied = copy.deepcopy(frame)
        copied._attrs["x"]["nested"].append(3)
        assert frame._attrs["x"]["nested"] == [1, 2]

    def test_arframe_deep_copy_self_referential_attrs(self):
        frame = ar.ArFrame.from_records([{"a": 1}])
        frame._attrs["self"] = frame
        copied = copy.deepcopy(frame)
        assert copied is not frame
        assert copied._attrs["self"] is copied


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


def test_astype_valid_single_type():
    from arnio.convert import to_pandas
    from arnio.frame import ArFrame

    frame = ArFrame.from_records([{"a": 1, "b": 2}, {"a": 3, "b": 4}])
    casted_frame = frame.astype(float)
    df = to_pandas(casted_frame)

    assert df["a"].dtype == "float64"
    assert df["b"].dtype == "float64"


def test_astype_dict_mapping():
    # Test casting specific columns using a dictionary
    from arnio.convert import to_pandas
    from arnio.frame import ArFrame

    frame = ArFrame.from_records(
        [{"name": "Alice", "age": "25"}, {"name": "Bob", "age": "30"}]
    )

    # Cast 'age' column from string to int
    casted_frame = frame.astype({"age": int})
    df = to_pandas(casted_frame)

    assert df["age"].dtype == "Int64"  # arnio uses Int64Dtype for integers


def test_astype_invalid_raises_error():
    # Test that invalid casting correctly raises clear errors
    import pytest

    from arnio.frame import ArFrame

    frame = ArFrame.from_records([{"name": "Alice"}, {"name": "Bob"}])

    # Trying to cast a text-string column to integer should raise a ValueError
    with pytest.raises(
        ValueError,
        match="Value conversion error during astype|An error occurred during casting",
    ):
        frame.astype(int)

    # Trying to pass None should raise a TypeError
    with pytest.raises(TypeError, match="dtype cannot be None"):
        frame.astype(None)


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


# ── _repr_html_() ─────────────────────────────────────────────────────────────


def test_repr_html_returns_str(sample_csv):
    frame = ar.read_csv(sample_csv)
    assert isinstance(frame._repr_html_(), str)


def test_repr_html_has_table_tag(sample_csv):
    assert "<table" in ar.read_csv(sample_csv)._repr_html_()


def test_repr_html_has_thead_and_tbody(sample_csv):
    out = ar.read_csv(sample_csv)._repr_html_()
    assert "<thead>" in out
    assert "<tbody>" in out


def test_repr_html_contains_column_names(sample_csv):
    frame = ar.read_csv(sample_csv)
    out = frame._repr_html_()
    for col in frame.columns:
        assert col in out


def test_repr_html_contains_cell_values(sample_csv):
    frame = ar.read_csv(sample_csv)
    out = frame._repr_html_()
    assert "Alice" in out
    assert "Bob" in out


def test_repr_html_summary_shows_shape(sample_csv):
    frame = ar.read_csv(sample_csv)
    out = frame._repr_html_()
    rows, cols = frame.shape
    assert str(rows) in out
    assert str(cols) in out


def test_repr_html_summary_shows_dtypes(sample_csv):
    frame = ar.read_csv(sample_csv)
    out = frame._repr_html_()
    for dtype in frame.dtypes.values():
        assert dtype in out


def test_repr_html_truncation_notice_present(large_csv):
    frame = ar.read_csv(large_csv)
    out = frame._repr_html_()
    assert "Showing 10 of 1000 rows" in out


def test_repr_html_no_truncation_for_small_frame(sample_csv):
    frame = ar.read_csv(sample_csv)
    assert "Showing" not in frame._repr_html_()


def test_repr_html_body_capped_at_ten_rows(large_csv):
    frame = ar.read_csv(large_csv)
    out = frame._repr_html_()
    tbody = out[out.index("<tbody>") : out.index("</tbody>") + len("</tbody>")]
    assert tbody.count("<tr>") == 10


def test_repr_html_empty_frame_no_crash(tmp_path):
    csv_path = tmp_path / "empty.csv"
    csv_path.write_text("name,age\n")
    frame = ar.read_csv(str(csv_path))
    out = frame._repr_html_()
    assert isinstance(out, str)
    assert len(out) > 0


def test_repr_html_with_nulls_no_crash(csv_with_nulls):
    frame = ar.read_csv(csv_with_nulls)
    out = frame._repr_html_()
    assert isinstance(out, str)
    assert "<table" in out


def test_repr_html_escapes_html_in_cell_value(tmp_path):
    csv_path = tmp_path / "xss.csv"
    csv_path.write_text('payload\n"<script>alert(1)</script>"\n')
    frame = ar.read_csv(str(csv_path))
    out = frame._repr_html_()
    assert "<script>" not in out
    assert "&lt;script&gt;" in out


def test_repr_html_escapes_html_in_column_name(tmp_path):
    csv_path = tmp_path / "col_xss.csv"
    csv_path.write_text("<b>bad</b>\n1\n")
    frame = ar.read_csv(str(csv_path))
    out = frame._repr_html_()
    assert "<b>bad</b>" not in out
    assert "&lt;b&gt;bad&lt;/b&gt;" in out


def test_repr_html_does_not_convert_full_frame(large_csv, monkeypatch):
    """_repr_html_() must not call to_pandas() on the full frame."""
    frame = ar.read_csv(large_csv)

    from arnio import convert

    original_to_pandas = convert.to_pandas
    call_sizes = []

    def tracking_to_pandas(f, **kwargs):
        call_sizes.append(len(f))
        return original_to_pandas(f, **kwargs)

    monkeypatch.setattr(convert, "to_pandas", tracking_to_pandas)
    frame._repr_html_()

    assert all(
        size <= 10 for size in call_sizes
    ), f"to_pandas() was called with {call_sizes} rows — full frame must not be converted"
