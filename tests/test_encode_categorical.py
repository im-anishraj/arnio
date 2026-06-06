"""Tests for arnio.encode_categorical."""

import pandas as pd
import pytest

import arnio as ar
from arnio.encode_categorical import encode_categorical

# ── fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def color_frame():
    return ar.from_records(
        [
            {"color": "red", "size": "S"},
            {"color": "blue", "size": "M"},
            {"color": "red", "size": "L"},
            {"color": "green", "size": "S"},
        ]
    )


@pytest.fixture
def nullable_frame():
    return ar.from_records(
        [
            {"color": "red"},
            {"color": None},
            {"color": "blue"},
            {"color": None},
        ]
    )


# ── one_hot: basic correctness ─────────────────────────────────────────────────


def test_one_hot_appends_indicator_columns(color_frame):
    result = encode_categorical(color_frame, ["color"])
    assert "color_blue" in result.columns
    assert "color_green" in result.columns
    assert "color_red" in result.columns


def test_one_hot_preserves_original_columns(color_frame):
    result = encode_categorical(color_frame, ["color"])
    assert "color" in result.columns
    assert "size" in result.columns


def test_one_hot_indicator_values(color_frame):
    result = encode_categorical(color_frame, ["color"])
    assert result["color_red"] == [1, 0, 1, 0]
    assert result["color_blue"] == [0, 1, 0, 0]
    assert result["color_green"] == [0, 0, 0, 1]


def test_one_hot_sorted_alphabetically(color_frame):
    result = encode_categorical(color_frame, ["color"])
    new_cols = [c for c in result.columns if c.startswith("color_")]
    assert new_cols == sorted(new_cols)


def test_one_hot_multi_column(color_frame):
    result = encode_categorical(color_frame, ["color", "size"])
    assert "color_red" in result.columns
    assert "size_S" in result.columns
    assert "size_M" in result.columns
    assert "size_L" in result.columns


# ── one_hot: null handling ─────────────────────────────────────────────────────


def test_one_hot_nulls_produce_all_zeros(nullable_frame):
    result = encode_categorical(nullable_frame, ["color"])
    assert result["color_red"] == [1, 0, 0, 0]
    assert result["color_blue"] == [0, 0, 1, 0]


# ── one_hot: dtype validation ──────────────────────────────────────────────────


def test_one_hot_rejects_non_string_column():
    frame = ar.from_records([{"x": 1}, {"x": 2}])
    with pytest.raises(ValueError, match="STRING"):
        encode_categorical(frame, ["x"])


# ── one_hot: column validation ─────────────────────────────────────────────────


def test_one_hot_unknown_column_raises_key_error(color_frame):
    with pytest.raises(KeyError):
        encode_categorical(color_frame, ["nonexistent"])


def test_one_hot_empty_columns_raises_value_error(color_frame):
    with pytest.raises(ValueError):
        encode_categorical(color_frame, [])


def test_one_hot_bare_string_columns_raises_type_error(color_frame):
    with pytest.raises(TypeError, match="columns must be a sequence of column names"):
        encode_categorical(color_frame, "color")


def test_one_hot_rejects_existing_output_name_collision():
    frame = ar.from_records([{"color": "red", "color_red": 10}])
    with pytest.raises(ValueError, match="generated column name 'color_red'"):
        encode_categorical(frame, ["color"])


def test_one_hot_rejects_collision_between_generated_names():
    frame = ar.from_records([{"a": "b_c", "a_b": "c"}])
    with pytest.raises(ValueError, match="generated column name 'a_b_c'"):
        encode_categorical(frame, ["a", "a_b"])


def test_one_hot_rejects_repeated_all_null_target_column():
    frame = ar.from_pandas(
        pd.DataFrame({"color": pd.Series([None, None], dtype="string")})
    )
    with pytest.raises(ValueError, match="columns contains duplicate column names"):
        encode_categorical(frame, ["color", "color"])


# ── ordinal: basic correctness ─────────────────────────────────────────────────


def test_ordinal_appends_ordinal_column(color_frame):
    result = encode_categorical(
        color_frame,
        ["color"],
        method="ordinal",
        ordinal_mappings={"color": {"red": 0, "blue": 1, "green": 2}},
    )
    assert "color_ordinal" in result.columns
    assert result["color_ordinal"] == [0, 1, 0, 2]


def test_ordinal_preserves_original_columns(color_frame):
    result = encode_categorical(
        color_frame,
        ["color"],
        method="ordinal",
        ordinal_mappings={"color": {"red": 0, "blue": 1, "green": 2}},
    )
    assert "color" in result.columns
    assert "size" in result.columns


def test_ordinal_nulls_preserved_as_null(nullable_frame):
    result = encode_categorical(
        nullable_frame,
        ["color"],
        method="ordinal",
        ordinal_mappings={"color": {"red": 0, "blue": 1}},
    )
    col = result["color_ordinal"]
    assert col[0] == 0
    assert col[1] is None
    assert col[2] == 1
    assert col[3] is None


# ── ordinal: error cases ───────────────────────────────────────────────────────


def test_ordinal_missing_mappings_raises_value_error(color_frame):
    with pytest.raises(ValueError, match="ordinal_mappings"):
        encode_categorical(color_frame, ["color"], method="ordinal")


def test_ordinal_missing_mapping_for_one_of_multiple_columns(color_frame):
    with pytest.raises(
        ValueError, match="ordinal_mappings is missing an entry for column 'size'"
    ):
        encode_categorical(
            color_frame,
            ["color", "size"],
            method="ordinal",
            ordinal_mappings={"color": {"red": 0, "blue": 1, "green": 2}},
        )


def test_ordinal_unmapped_value_raises(color_frame):
    with pytest.raises(ValueError, match="has no mapping entry"):
        # "green" not in mapping → C++ raises std::invalid_argument
        encode_categorical(
            color_frame,
            ["color"],
            method="ordinal",
            ordinal_mappings={"color": {"red": 0, "blue": 1}},
        )


def test_ordinal_rejects_non_string_column():
    frame = ar.from_records([{"x": 1}, {"x": 2}])
    with pytest.raises(ValueError, match="STRING"):
        encode_categorical(frame, ["x"], method="ordinal", ordinal_mappings={"x": {}})


def test_ordinal_rejects_existing_output_name_collision():
    frame = ar.from_records([{"color": "red", "color_ordinal": 10}])
    with pytest.raises(ValueError, match="generated column name 'color_ordinal'"):
        encode_categorical(
            frame,
            ["color"],
            method="ordinal",
            ordinal_mappings={"color": {"red": 0}},
        )


def test_ordinal_rejects_repeated_target_column(color_frame):
    with pytest.raises(ValueError, match="columns contains duplicate column names"):
        encode_categorical(
            color_frame,
            ["color", "color"],
            method="ordinal",
            ordinal_mappings={"color": {"red": 0, "blue": 1, "green": 2}},
        )


# ── bad method ─────────────────────────────────────────────────────────────────


def test_unknown_method_raises_value_error(color_frame):
    with pytest.raises(ValueError, match="Unknown encoding method"):
        encode_categorical(color_frame, ["color"], method="label")
