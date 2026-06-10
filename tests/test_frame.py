"""
Tests for ArFrame.preview()
"""

import copy
import math

import numpy as np
import pandas as pd
import pytest

import arnio as ar
from arnio._core import _Column, _DType, _Frame

# ── Normal behaviour ──────────────────────────────────────────────────────────


def test_dict():
    data = {"name": ["Alice", "Bob"], "age": [25, 30]}

    frame = ar.from_dict(data)
    assert frame.columns == ["name", "age"]
    assert frame.shape == (2, 2)
    assert frame.columns[0] == "name"
    assert frame.columns[1] == "age"
    assert frame["name"][0] == "Alice"
    assert frame["age"][1] == 30


def test_dict_ArFrame():
    data = {"name": ["Alice", "Bob"], "age": [25, 30]}

    frame = ar.ArFrame.from_dict(data)
    assert frame.columns == ["name", "age"]
    assert frame.shape == (2, 2)
    assert frame.columns[0] == "name"
    assert frame.columns[1] == "age"
    assert frame["name"][0] == "Alice"
    assert frame["age"][1] == 30


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


def test_empty_dict():
    data = {}
    frame = ar.from_dict(data)

    assert frame.shape == (0, 0)
    assert frame.columns == []


def test_empty_dict_ArFrame():
    data = {}
    frame = ar.ArFrame.from_dict(data)

    assert frame.shape == (0, 0)
    assert frame.columns == []


def test_none_value():
    # Verifies that columns containing None/missing values are accepted
    data = {"name": ["Alice", "Bob"], "age": [25, None]}

    frame = ar.from_dict(data)
    assert frame.shape == (2, 2)
    assert frame.columns == ["name", "age"]
    assert frame.columns[0] == "name"
    assert frame.columns[1] == "age"
    assert frame["name"][0] == "Alice"
    assert frame["age"][1] is None


def test_none_value_ArFrame():
    # Verifies that columns containing None/missing values are accepted
    data = {"name": ["Alice", "Bob"], "age": [25, None]}

    frame = ar.ArFrame.from_dict(data)
    assert frame.shape == (2, 2)
    assert frame.columns == ["name", "age"]
    assert frame.columns[0] == "name"
    assert frame.columns[1] == "age"
    assert frame["name"][0] == "Alice"
    assert frame["age"][1] is None


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


def test_nested_dict_keys():
    data = {"name": ["Alice", "Bob"], 36: [25, 30]}
    with pytest.raises(TypeError):
        ar.from_dict(data)


def test_nested_dict_keys_ArFrame():
    data = {"name": ["Alice", "Bob"], 36: [25, 30]}
    with pytest.raises(TypeError):
        ar.ArFrame.from_dict(data)


def test_nested_dict_values():
    data = {
        "name": ["Alice", "Bob"],
        "info": [{"city": "NY", "age": 25}, {"city": "LA", "age": 30}],
    }
    with pytest.raises(TypeError):
        ar.from_dict(data)


def test_nested_dict_values_ArFrame():
    data = {
        "name": ["Alice", "Bob"],
        "info": [{"city": "NY", "age": 25}, {"city": "LA", "age": 30}],
    }
    with pytest.raises(TypeError):
        ar.ArFrame.from_dict(data)


def test_nested_dictvalues():
    data = {"info": {"city": "NY", "age": 25}}

    with pytest.raises(
        ValueError, match="Nested objects are not supported in column 'info'"
    ):
        ar.from_dict(data)


def test_nested_dictvalues_ArFrame():
    data = {"info": {"city": "NY", "age": 25}}

    with pytest.raises(
        ValueError, match="Nested objects are not supported in column 'info'"
    ):
        ar.ArFrame.from_dict(data)


def test_length_mismatch():
    data = {"name": ["Alice", "Bob"], "age": [25]}  # Missing an age
    with pytest.raises(ValueError):
        ar.from_dict(data)


def test_length_mismatch_ArFrame():
    data = {"name": ["Alice", "Bob"], "age": [25]}  # Missing an age
    with pytest.raises(ValueError):
        ar.ArFrame.from_dict(data)


def test_scalar_dict():
    data = {"name": "Alice", "age": 25}

    with pytest.raises(
        TypeError,
        match="Column 'name' must be a sequence of values",
    ):
        ar.from_dict(data)


def test_scalar_dict_ArFrame():
    data = {"name": "Alice", "age": 25}

    with pytest.raises(
        TypeError,
        match="Column 'name' must be a sequence of values",
    ):
        ar.ArFrame.from_dict(data)


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


def test_preview_zero_column_frame():
    df = pd.DataFrame(index=range(3))

    frame = ar.from_pandas(df)
    result = frame.preview()

    expected = "ArFrame preview: 3 rows x 0 columns (no columns to display)"

    assert result == expected


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


def test_select_columns_null_nan_handling():
    df = pd.DataFrame(
        {
            "id": [1, None, 3],
            "name": ["Alice", "Bob", None],
            "score": [95.5, float("nan"), 80.0],
        }
    )
    frame = ar.from_pandas(df)
    selected = frame.select_columns(["id", "score"])
    res_df = ar.to_pandas(selected)
    assert pd.isna(res_df["id"].iloc[1])
    assert pd.isna(res_df["score"].iloc[1])
    assert res_df["id"].iloc[0] == 1
    assert res_df["score"].iloc[0] == 95.5


def test_select_columns_single_column_frame():
    df = pd.DataFrame({"id": [1, 2]})
    frame = ar.from_pandas(df)
    selected = frame.select_columns(["id"])
    assert selected.columns == ["id"]
    assert selected.shape == (2, 1)

    multi_df = pd.DataFrame({"id": [1, 2], "name": ["A", "B"]})
    multi_frame = ar.from_pandas(multi_df)
    selected_single = multi_frame.select_columns(["name"])
    assert selected_single.columns == ["name"]
    assert selected_single.shape == (2, 1)


def test_select_columns_reordering():
    df = pd.DataFrame(
        {
            "id": [1, 2],
            "name": ["Alice", "Bob"],
            "age": [25, 30],
        }
    )
    frame = ar.from_pandas(df)
    reordered = frame.select_columns(["age", "id", "name"])
    assert reordered.columns == ["age", "id", "name"]
    res_df = ar.to_pandas(reordered)
    assert list(res_df["age"]) == [25, 30]
    assert list(res_df["id"]) == [1, 2]
    assert list(res_df["name"]) == ["Alice", "Bob"]


def test_select_columns_invalid_container_types():
    df = pd.DataFrame({"id": [1, 2], "name": ["A", "B"]})
    frame = ar.from_pandas(df)

    with pytest.raises(TypeError, match="must be a list or tuple"):
        frame.select_columns({"id": "name"})

    gen = (col for col in ["id"])
    with pytest.raises(TypeError, match="must be a list or tuple"):
        frame.select_columns(gen)

    with pytest.raises(TypeError, match="must be a list or tuple"):
        frame.select_columns(None)
    with pytest.raises(TypeError, match="must be a list or tuple"):
        frame.select_columns(123)


def test_select_columns_dtype_preservation():
    df = pd.DataFrame(
        {
            "int_col": pd.Series([1, 2], dtype="Int64"),
            "float_col": pd.Series([1.5, 2.5], dtype="float64"),
            "bool_col": pd.Series([True, False], dtype="boolean"),
            "str_col": pd.Series(["A", "B"], dtype="string"),
        }
    )
    frame = ar.from_pandas(df)
    original_dtypes = frame.dtypes

    selected = frame.select_columns(["float_col", "str_col", "int_col"])
    new_dtypes = selected.dtypes

    assert new_dtypes["int_col"] == original_dtypes["int_col"]
    assert new_dtypes["float_col"] == original_dtypes["float_col"]
    assert new_dtypes["str_col"] == original_dtypes["str_col"]

    res_df = ar.to_pandas(selected)
    assert res_df["int_col"].dtype == pd.Int64Dtype()
    assert res_df["float_col"].dtype == "float64"
    assert res_df["str_col"].dtype == pd.StringDtype()


def test_head_native_path_avoids_pandas_roundtrip(monkeypatch):
    frame = ar.from_pandas(
        pd.DataFrame(
            {
                "name": ["alice", "bob", "charlie"],
                "salary": [100, 200, 300],
            }
        )
    )

    from arnio import convert

    def fail_to_pandas(_):
        raise AssertionError("head() should avoid to_pandas")

    monkeypatch.setattr(convert, "to_pandas", fail_to_pandas)

    result = frame.head(2)

    assert result.shape == (2, 2)
    assert result.columns == ["name", "salary"]


def test_tail_native_path_avoids_pandas_roundtrip(monkeypatch):
    frame = ar.from_pandas(
        pd.DataFrame(
            {
                "name": ["alice", "bob", "charlie"],
                "salary": [100, 200, 300],
            }
        )
    )

    from arnio import convert

    def fail_to_pandas(_):
        raise AssertionError("tail() should avoid to_pandas")

    monkeypatch.setattr(convert, "to_pandas", fail_to_pandas)

    result = frame.tail(2)

    assert result.shape == (2, 2)
    assert result.columns == ["name", "salary"]


@pytest.mark.parametrize("method_name", ["head", "tail"])
def test_head_tail_preserve_attrs_roundtrip(method_name):
    df = pd.DataFrame({"name": ["alice", "bob"], "score": [10, 20]})
    df.attrs = {"source": "qa", "metadata": {"tags": ["sample"]}}
    frame = ar.from_pandas(df)

    subset = getattr(frame, method_name)(1)
    result = ar.to_pandas(subset)

    assert result.attrs == {"source": "qa", "metadata": {"tags": ["sample"]}}


@pytest.mark.parametrize("method_name", ["head", "tail"])
def test_head_tail_attrs_are_deep_copied(method_name):
    df = pd.DataFrame({"name": ["alice", "bob"], "score": [10, 20]})
    df.attrs = {"metadata": {"tags": ["sample"]}}
    frame = ar.from_pandas(df)

    subset = getattr(frame, method_name)(1)
    subset._attrs["metadata"]["tags"].append("subset")

    assert frame._attrs == {"metadata": {"tags": ["sample"]}}


def test_head_default_n():
    frame = ar.from_pandas(
        pd.DataFrame(
            {
                "a": [1, 2, 3, 4, 5, 6],
            }
        )
    )

    result = frame.head()

    assert result.shape == (5, 1)
    assert result["a"] == [1, 2, 3, 4, 5]


def test_tail_default_n():
    frame = ar.from_pandas(
        pd.DataFrame(
            {
                "a": [1, 2, 3, 4, 5, 6],
            }
        )
    )

    result = frame.tail()

    assert result.shape == (5, 1)
    assert result["a"] == [2, 3, 4, 5, 6]


def test_head_zero_rows():
    frame = ar.from_pandas(
        pd.DataFrame(
            {
                "a": [1, 2, 3],
            }
        )
    )

    result = frame.head(0)

    assert result.shape == (0, 1)
    assert result["a"] == []


def test_tail_zero_rows():
    frame = ar.from_pandas(
        pd.DataFrame(
            {
                "a": [1, 2, 3],
            }
        )
    )

    result = frame.tail(0)

    assert result.shape == (0, 1)
    assert result["a"] == []


def test_head_oversized_n():
    frame = ar.from_pandas(
        pd.DataFrame(
            {
                "a": [1, 2, 3],
            }
        )
    )

    result = frame.head(999)

    assert result.shape == (3, 1)
    assert result["a"] == [1, 2, 3]


def test_tail_oversized_n():
    frame = ar.from_pandas(
        pd.DataFrame(
            {
                "a": [1, 2, 3],
            }
        )
    )

    result = frame.tail(999)

    assert result.shape == (3, 1)
    assert result["a"] == [1, 2, 3]


@pytest.mark.parametrize("invalid_n", [-1, 1.5, "5", True, None])
def test_head_invalid_n(invalid_n):
    frame = ar.from_pandas(pd.DataFrame({"a": [1, 2, 3]}))

    with pytest.raises(ValueError):
        frame.head(invalid_n)


@pytest.mark.parametrize("invalid_n", [-1, 1.5, "5", True, None])
def test_tail_invalid_n(invalid_n):
    frame = ar.from_pandas(pd.DataFrame({"a": [1, 2, 3]}))

    with pytest.raises(ValueError):
        frame.tail(invalid_n)


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
        assert copied._frame is not frame._frame

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


def test_str_zero_columns_non_empty_rows_has_explicit_message():
    frame = ar.from_pandas(pd.DataFrame(index=range(2)))

    result = str(frame)

    assert "ArFrame: 2 rows × 0 columns" in result
    assert "Columns: []" in result
    assert "DTypes: {}" in result
    assert "(no columns to display)" in result


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

main
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

    numeric_frame = frame.select_dtypes(include=["int64", "float64"])
    stats = numeric_frame.describe()

    assert list(stats.keys()) == ["id", "value"]

    for col in ["id", "value"]:
        metric_keys = list(stats[col].keys())
        assert metric_keys == ["count", "nulls", "non_finite", "mean", "min", "max"]


def test_describe_all_string_columns(csv_with_whitespace):
    frame = ar.read_csv(csv_with_whitespace)
    stats = frame.describe()

    assert list(stats.keys()) == ["name", "city"]

    for col in ["name", "city"]:
        metric_keys = list(stats[col].keys())
        assert metric_keys == ["count", "nulls", "unique"]


def test_describe_includes_boolean_columns():
    frame = ar.ArFrame.from_records(
        [
            {"flag": True, "name": "a"},
            {"flag": False, "name": "b"},
            {"flag": True, "name": "c"},
        ]
    )

    stats = frame.describe()

    assert list(stats.keys()) == ["flag", "name"]
    assert list(stats["flag"].keys()) == [
        "count",
        "nulls",
        "true",
        "false",
        "true_ratio",
    ]
    assert stats["flag"]["count"] == 3.0
    assert stats["flag"]["nulls"] == 0.0
    assert stats["flag"]["true"] == 2.0
    assert stats["flag"]["false"] == 1.0
    assert stats["flag"]["true_ratio"] == pytest.approx(2.0 / 3.0)


def test_describe_boolean_columns_with_nulls():
    frame = ar.from_pandas(
        pd.DataFrame({"flag": pd.Series([True, None, False, True], dtype="boolean")})
    )

    stats = frame.describe()

    assert stats["flag"]["count"] == 3.0
    assert stats["flag"]["nulls"] == 1.0
    assert stats["flag"]["true"] == 2.0
    assert stats["flag"]["false"] == 1.0
    assert stats["flag"]["true_ratio"] == pytest.approx(2.0 / 3.0)


def test_describe_preserves_mixed_column_outputs():
    df = pd.DataFrame(
        {
            "id": [1, 2, 3, 4],
            "score": [1.5, 2.5, 3.5, 4.5],
            "label": ["a", "b", "a", "c"],
            "active": [True, False, True, True],
        }
    )

    frame = ar.from_pandas(df)
    stats = frame.describe()

    assert stats["id"]["count"] == 4.0
    assert stats["id"]["nulls"] == 0.0
    assert stats["id"]["non_finite"] == 0.0
    assert stats["id"]["mean"] == 2.5
    assert stats["id"]["min"] == 1.0
    assert stats["id"]["max"] == 4.0

    assert stats["score"]["count"] == 4.0
    assert stats["score"]["nulls"] == 0.0
    assert stats["score"]["non_finite"] == 0.0
    assert stats["score"]["mean"] == 3.0
    assert stats["score"]["min"] == 1.5
    assert stats["score"]["max"] == 4.5

    assert stats["label"]["count"] == 4.0
    assert stats["label"]["nulls"] == 0.0
    assert stats["label"]["unique"] == 3.0

    assert stats["active"]["count"] == 4.0
    assert stats["active"]["nulls"] == 0.0
    assert stats["active"]["true"] == 3.0
    assert stats["active"]["false"] == 1.0
    assert stats["active"]["true_ratio"] == pytest.approx(0.75)


def test_describe_preserves_null_and_non_finite_float_handling():
    import io

    frame = ar.read_csv(
        io.StringIO("value,name\n" "1.0,a\n" "inf,b\n" "3.0,\n" ",c\n" "-inf,a\n")
    )

    stats = frame.describe()

    assert stats["value"]["count"] == 4.0
    assert stats["value"]["nulls"] == 1.0
    assert stats["value"]["non_finite"] == 2.0
    assert stats["value"]["mean"] == 2.0
    assert stats["value"]["min"] == 1.0
    assert stats["value"]["max"] == 3.0

    assert stats["name"]["count"] == 4.0
    assert stats["name"]["nulls"] == 1.0
    assert stats["name"]["unique"] == 3.0


# ── non-finite describe regression tests ─────────────────────────────────────


def test_describe_non_finite_mixed_float_column():
    """inf and -inf are excluded from sum/min/max; non_finite count is reported."""
    import io

    frame = ar.read_csv(io.StringIO("x\n1.0\ninf\n-inf\n3.0\n"))
    stats = frame.describe()

    assert stats["x"]["count"] == 4.0
    assert stats["x"]["nulls"] == 0.0
    assert stats["x"]["non_finite"] == 2.0
    assert stats["x"]["mean"] == pytest.approx(2.0)
    assert stats["x"]["min"] == pytest.approx(1.0)
    assert stats["x"]["max"] == pytest.approx(3.0)


def test_describe_non_finite_all_finite_column():
    """All-finite column: non_finite == 0, mean/min/max computed normally."""
    import io

    frame = ar.read_csv(io.StringIO("x\n2.0\n4.0\n6.0\n"))
    stats = frame.describe()

    assert stats["x"]["non_finite"] == 0.0
    assert stats["x"]["mean"] == pytest.approx(4.0)
    assert stats["x"]["min"] == pytest.approx(2.0)
    assert stats["x"]["max"] == pytest.approx(6.0)


def test_describe_non_finite_all_non_finite_column():
    """All-non-finite column: mean/min/max fall back to 0.0 deterministically."""
    import io

    frame = ar.read_csv(io.StringIO("x\ninf\n-inf\n"))
    stats = frame.describe()

    assert stats["x"]["count"] == 2.0
    assert stats["x"]["non_finite"] == 2.0
    assert stats["x"]["mean"] == 0.0
    assert stats["x"]["min"] == 0.0
    assert stats["x"]["max"] == 0.0


def test_describe_non_finite_negative_inf_only():
    """-inf only column is fully non-finite; fallback values are 0.0."""
    import io

    frame = ar.read_csv(io.StringIO("x\n-inf\n-inf\n"))
    stats = frame.describe()

    assert stats["x"]["non_finite"] == 2.0
    assert stats["x"]["mean"] == 0.0
    assert stats["x"]["min"] == 0.0
    assert stats["x"]["max"] == 0.0


def test_describe_non_finite_int64_no_regression():
    """int64 columns cannot hold inf; non_finite must always be 0."""
    frame = ar.from_pandas(pd.DataFrame({"x": [10, 20, 30]}))
    stats = frame.describe()

    assert stats["x"]["non_finite"] == 0.0
    assert stats["x"]["count"] == 3.0
    assert stats["x"]["mean"] == pytest.approx(20.0)


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


@pytest.mark.parametrize("invalid_dtype", [[], (), set()])
def test_astype_rejects_invalid_dtype_containers(invalid_dtype):
    frame = ar.ArFrame.from_records([{"a": 1, "b": "x"}, {"a": 2, "b": "y"}])

    with pytest.raises(TypeError, match="dtype must"):
        frame.astype(invalid_dtype)


def test_astype_rejects_unknown_mapping_columns():
    frame = ar.ArFrame.from_records([{"a": 1}, {"a": 2}])

    with pytest.raises(ValueError, match="Unknown column"):
        frame.astype({"missing": int})


def test_astype_rejects_invalid_mapping_dtype():
    frame = ar.ArFrame.from_records([{"a": 1}, {"a": 2}])

    with pytest.raises(TypeError, match="dtype must"):
        frame.astype({"a": []})


@pytest.mark.parametrize(
    "invalid_dtype",
    [object, "object", np.object_, np.dtype("O")],
)
def test_astype_rejects_object_dtype_aliases(invalid_dtype):
    frame = ar.ArFrame.from_records([{"a": 1}, {"a": 2}])

    with pytest.raises(TypeError, match="dtype must"):
        frame.astype(invalid_dtype)


# ── drop_columns ──────────────────────────────────────────────────────────────


class TestDropColumns:
    """Tests for ArFrame.drop_columns()."""

    def test_drop_single_column(self):
        df = pd.DataFrame({"a": [1, 2], "b": [3, 4], "c": [5, 6]})
        frame = ar.from_pandas(df)
        result = frame.drop_columns(["b"])
        assert result.columns == ["a", "c"]
        assert result.shape == (2, 2)

    def test_accepts_tuple_of_column_names(self):
        frame = ar.from_pandas(
            pd.DataFrame(
                {
                    "a": [1],
                    "b": [2],
                    "c": [3],
                }
            )
        )

        result = frame.drop_columns(("a",))

        assert result.columns == ["b", "c"]

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
 main


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


def test_repr_html_zero_columns_preserves_row_count():
    frame = ar.from_pandas(pd.DataFrame({"a": [None, None]}))
    zero = ar.drop_empty_columns(frame)

    out = zero._repr_html_()

    assert zero.shape == (2, 0)
    assert "ArFrame [2 rows × 0 cols]" in out
    assert "(no columns to display)" in out
    assert "(empty)" not in out


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
    """_repr_html_() must not call to_pandas() for automatic display."""
    frame = ar.read_csv(large_csv)

    from arnio import convert

    call_sizes = []

    def tracking_to_pandas(f, **kwargs):
        call_sizes.append(len(f))
        raise AssertionError("_repr_html_() must not call to_pandas()")

    monkeypatch.setattr(convert, "to_pandas", tracking_to_pandas)
    frame._repr_html_()

    assert (
        call_sizes == []
    ), f"_repr_html_() should not call to_pandas(), but got calls with {call_sizes} rows"
 main
 main



# ── filter_rows() tests ───────────────────────────────────────────────────────


class TestFilterRows:
    """Tests for arnio.filter_rows function."""

    def test_filter_rows_numeric_greater_than(self):
        # We test '>' on a numeric column.
        data = {"name": ["Alice", "Bob", "Charlie"], "age": [25, 17, 30]}
        frame = ar.from_dict(data)
        filtered = ar.filter_rows(frame, column="age", op=">", value=18)
        assert filtered.columns == ["name", "age"]
        assert filtered.shape == (2, 2)
        assert filtered["name"] == ["Alice", "Charlie"]
        assert filtered["age"] == [25, 30]

    def test_filter_rows_numeric_less_than(self):
        # We test '<' on a numeric column.
        data = {"name": ["Alice", "Bob", "Charlie"], "age": [25, 17, 30]}
        frame = ar.from_dict(data)
        filtered = ar.filter_rows(frame, column="age", op="<", value=18)
        assert filtered.shape == (1, 2)
        assert filtered["name"] == ["Bob"]
        assert filtered["age"] == [17]

    def test_filter_rows_numeric_greater_equal(self):
        # We test '>=' on a numeric column.
        data = {"name": ["Alice", "Bob", "Charlie"], "age": [25, 18, 30]}
        frame = ar.from_dict(data)
        filtered = ar.filter_rows(frame, column="age", op=">=", value=18)
        assert filtered.shape == (3, 2)
        assert filtered["name"] == ["Alice", "Bob", "Charlie"]

    def test_filter_rows_numeric_less_equal(self):
        # We test '<=' on a numeric column.
        data = {"name": ["Alice", "Bob", "Charlie"], "age": [25, 18, 30]}
        frame = ar.from_dict(data)
        filtered = ar.filter_rows(frame, column="age", op="<=", value=18)
        assert filtered.shape == (1, 2)
        assert filtered["name"] == ["Bob"]

    def test_filter_rows_numeric_equal(self):
        # We test '==' on a numeric column.
        data = {"name": ["Alice", "Bob", "Charlie"], "age": [25, 18, 30]}
        frame = ar.from_dict(data)
        filtered = ar.filter_rows(frame, column="age", op="==", value=18)
        assert filtered.shape == (1, 2)
        assert filtered["name"] == ["Bob"]

    def test_filter_rows_numeric_not_equal(self):
        # We test '!=' on a numeric column.
        data = {"name": ["Alice", "Bob", "Charlie"], "age": [25, 18, 30]}
        frame = ar.from_dict(data)
        filtered = ar.filter_rows(frame, column="age", op="!=", value=18)
        assert filtered.shape == (2, 2)
        assert filtered["name"] == ["Alice", "Charlie"]

    def test_filter_rows_string_equal(self):
        # We test '==' on a string column.
        data = {"name": ["Alice", "Bob", "Charlie"], "city": ["NYC", "Paris", "NYC"]}
        frame = ar.from_dict(data)
        filtered = ar.filter_rows(frame, column="city", op="==", value="NYC")
        assert filtered.shape == (2, 2)
        assert filtered["name"] == ["Alice", "Charlie"]

    def test_filter_rows_string_not_equal(self):
        # We test '!=' on a string column.
        data = {"name": ["Alice", "Bob", "Charlie"], "city": ["NYC", "Paris", "NYC"]}
        frame = ar.from_dict(data)
        filtered = ar.filter_rows(frame, column="city", op="!=", value="NYC")
        assert filtered.shape == (1, 2)
        assert filtered["name"] == ["Bob"]

    def test_filter_rows_boolean_equal(self):
        # We test '==' on a boolean column.
        data = {"name": ["Alice", "Bob", "Charlie"], "active": [True, False, True]}
        frame = ar.from_dict(data)
        filtered = ar.filter_rows(frame, column="active", op="==", value=True)
        assert filtered.shape == (2, 2)
        assert filtered["name"] == ["Alice", "Charlie"]

    def test_filter_rows_boolean_not_equal(self):
        # We test '!=' on a boolean column.
        data = {"name": ["Alice", "Bob", "Charlie"], "active": [True, False, True]}
        frame = ar.from_dict(data)
        filtered = ar.filter_rows(frame, column="active", op="!=", value=True)
        assert filtered.shape == (1, 2)
        assert filtered["name"] == ["Bob"]

    def test_filter_rows_with_null_values_filled_false(self):
        # Null values inside a filtered column should be filled with False in the comparison mask
        # and not raise errors or keep the null rows for operators like >.
        data = {"name": ["Alice", "Bob", "Charlie", "David"], "age": [25, None, 30, 15]}
        frame = ar.from_dict(data)
        filtered = ar.filter_rows(frame, column="age", op=">", value=18)
        assert filtered.shape == (2, 2)
        assert filtered["name"] == ["Alice", "Charlie"]

    def test_filter_rows_accepts_and_returns_pandas_dataframe(self):
        # When filter_rows gets a pd.DataFrame, it should return a pd.DataFrame.
        data = {"name": ["Alice", "Bob"], "age": [25, 17]}
        df = pd.DataFrame(data)
        filtered = ar.filter_rows(df, column="age", op=">", value=18)
        assert isinstance(filtered, pd.DataFrame)
        assert len(filtered) == 1
        assert list(filtered["name"]) == ["Alice"]

    def test_filter_rows_empty_frame(self):
        # Filtering an empty frame should return a brand new empty frame with the same columns.
        data = {"name": [], "age": []}
        frame = ar.from_dict(data)
        filtered = ar.filter_rows(frame, column="age", op=">", value=18)
        assert filtered.is_empty is True
        assert filtered.columns == ["name", "age"]

    def test_filter_rows_zero_matching_rows(self):
        # If no rows match, we should get an empty frame.
        data = {"name": ["Alice", "Bob"], "age": [25, 17]}
        frame = ar.from_dict(data)
        filtered = ar.filter_rows(frame, column="age", op=">", value=100)
        assert filtered.is_empty is True
        assert filtered.columns == ["name", "age"]

    def test_filter_rows_all_matching_rows(self):
        # If all rows match, we should get all rows back.
        data = {"name": ["Alice", "Bob"], "age": [25, 17]}
        frame = ar.from_dict(data)
        filtered = ar.filter_rows(frame, column="age", op=">", value=10)
        assert filtered.shape == (2, 2)
        assert filtered["name"] == ["Alice", "Bob"]

    def test_filter_rows_invalid_operator(self):
        # Passing an unsupported operator should raise ValueError.
        data = {"name": ["Alice", "Bob"], "age": [25, 17]}
        frame = ar.from_dict(data)
        with pytest.raises(ValueError, match="Unsupported operator: %%"):
            ar.filter_rows(frame, column="age", op="%%", value=18)

    def test_filter_rows_missing_column(self):
        # Passing a non-existent column name should raise ValueError.
        data = {"name": ["Alice", "Bob"], "age": [25, 17]}
        frame = ar.from_dict(data)
        with pytest.raises(ValueError, match="Unknown column: salary"):
            ar.filter_rows(frame, column="salary", op=">", value=18)

    def test_filter_rows_non_scalar_value(self):
        # Passing a non-scalar value (like a list) should raise TypeError.
        data = {"name": ["Alice", "Bob"], "age": [25, 17]}
        frame = ar.from_dict(data)
        with pytest.raises(TypeError, match="filter_rows value must be a scalar"):
            ar.filter_rows(frame, column="age", op=">", value=[18])

    def test_filter_rows_incompatible_types_comparison(self):
        # Comparing incompatible types (e.g. string vs number with '>') should raise TypeError.
        data = {"name": ["Alice", "Bob"], "age": [25, 17]}
        frame = ar.from_dict(data)
        with pytest.raises(
            TypeError,
            match="cannot compare column 'name' with value 18 using operator '>'",
        ):
            ar.filter_rows(frame, column="name", op=">", value=18)


# ── select_dtypes zero-column ─────────────────────────────────────────────────


def test_select_dtypes_include_absent_dtype_returns_zero_col_frame():
    frame = ar.from_pandas(pd.DataFrame({"age": [1, 2], "score": [3.5, 4.0]}))
    result = frame.select_dtypes(include="string")
    assert result.shape == (2, 0)
    assert result.columns == []


def test_select_dtypes_exclude_all_columns_returns_zero_col_frame():
    frame = ar.from_pandas(pd.DataFrame({"age": [1, 2], "score": [3.5, 4.0]}))
    result = frame.select_dtypes(exclude=["int64", "float64"])
    assert result.shape == (2, 0)
    assert result.columns == []


def test_select_dtypes_zero_col_preserves_row_count():
    frame = ar.from_pandas(pd.DataFrame({"age": [1, 2, 3, 4, 5]}))
    result = frame.select_dtypes(include="string")
    assert result.shape[0] == 5
    assert result.shape[1] == 0


def test_select_dtypes_zero_col_preserves_attrs():
    frame = ar.from_pandas(pd.DataFrame({"age": [1, 2]}))
    frame._attrs["source"] = "test"
    result = frame.select_dtypes(include="string")
    assert result._attrs == {"source": "test"}
    assert result._attrs is not frame._attrs


# ── selection methods attrs preservation ──────────────────────────────────────


def test_selection_methods_preserve_attrs():
    df = pd.DataFrame({"a": [1, 2], "b": [3.5, 4.0], "c": ["x", "y"]})
    frame = ar.from_pandas(df)
    frame._attrs = {"metadata": {"source": "crm", "version": 1}}

    # 1. select_columns
    res_select = frame.select_columns(["a", "b"])
    assert res_select._attrs == {"metadata": {"source": "crm", "version": 1}}
    assert res_select._attrs is not frame._attrs
    # Deep copy isolation check
    res_select._attrs["metadata"]["version"] = 2
    assert frame._attrs["metadata"]["version"] == 1

    # 2. drop_columns
    res_drop = frame.drop_columns(["c"])
    assert res_drop._attrs == {"metadata": {"source": "crm", "version": 1}}
    assert res_drop._attrs is not frame._attrs
    # Deep copy isolation check
    res_drop._attrs["metadata"]["version"] = 2
    assert frame._attrs["metadata"]["version"] == 1

    # 2.1 drop_columns empty input
    res_drop_empty = frame.drop_columns([])
    assert res_drop_empty._attrs == {"metadata": {"source": "crm", "version": 1}}
    assert res_drop_empty._attrs is not frame._attrs
    # Deep copy isolation check
    res_drop_empty._attrs["metadata"]["version"] = 2
    assert frame._attrs["metadata"]["version"] == 1

    # 3. select_dtypes
    res_dtypes = frame.select_dtypes(include="int64")
    assert res_dtypes._attrs == {"metadata": {"source": "crm", "version": 1}}
    assert res_dtypes._attrs is not frame._attrs
    # Deep copy isolation check
    res_dtypes._attrs["metadata"]["version"] = 2
    assert frame._attrs["metadata"]["version"] == 1


def test_shallow_copy_independent_frame():
    import copy

    import pandas as pd

    import arnio as ar

    original = ar.from_pandas(pd.DataFrame({"a": [1, 2, 3]}))
    shallow = copy.copy(original)

    assert shallow._frame is not original._frame
    ar.rename_columns(original, {"a": "b"})
    assert "a" in shallow.columns  # mutation must not leak


# ── from_records empty-columns guard ─────────────────────────────────────────


def test_from_records_dict_empty_columns_raises():
    """columns=[] with dict records must raise ValueError, not silently lose rows."""
    with pytest.raises(ValueError, match="columns must not be empty"):
        ar.ArFrame.from_records([{"a": 1}, {"a": 2}], columns=[])


def test_from_records_dict_empty_columns_message_is_helpful():
    """The error message should mention passing columns=None."""
    with pytest.raises(ValueError, match="columns=None"):
        ar.ArFrame.from_records([{"a": 1}], columns=[])


def test_from_records_dict_columns_none_infers_from_keys():
    """columns=None (default) should infer column names from dict keys."""
    frame = ar.ArFrame.from_records([{"a": 1}, {"a": 2}])
    assert frame.shape == (2, 1)
    assert frame.columns == ["a"]


def test_from_records_dict_explicit_valid_columns_subset():
    """A non-empty explicit columns list should select only those columns."""
    frame = ar.ArFrame.from_records([{"a": 1, "b": 2}, {"a": 3, "b": 4}], columns=["a"])
    assert frame.shape == (2, 1)
    assert frame.columns == ["a"]
    assert frame["a"] == [1, 3]
 main
 main



def test_to_dict_invalid_orient_types():
    data = {"name": ["Alice", "Bob"], "age": [25, 30]}
    frame = ar.from_dict(data)

    # 1. Unhashable list input must raise TypeError cleanly
    with pytest.raises(TypeError, match="orient must be a string"):
        frame.to_dict(orient=["list"])

    # 2. Unhashable dict input must raise TypeError cleanly
    with pytest.raises(TypeError, match="orient must be a string"):
        frame.to_dict(orient={"mode": "list"})

    # 3. Hashable non-string input (like int) must also raise TypeError cleanly
    with pytest.raises(TypeError, match="orient must be a string"):
        frame.to_dict(orient=1)

    # 4. Backward Compatibility: Unsupported string must still raise ValueError
    with pytest.raises(ValueError, match="orient must be one of: list, records, split"):
        frame.to_dict(orient="invalid_string")
 main
