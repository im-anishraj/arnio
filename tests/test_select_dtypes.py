"""
Tests for ArFrame.select_dtypes() — issue #222.

- select_dtypes() returns an ArFrame, not a list.
- No columns matched → raises ValueError("No columns match").
- include/exclude overlap → raises ValueError("overlap").

"""

from __future__ import annotations

import pytest

import arnio as ar

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mixed_csv(tmp_path):
    """CSV with int64, float64, string and bool columns."""
    path = tmp_path / "mixed.csv"
    path.write_text(
        "name,age,score,active\n"
        "Alice,30,9.5,true\n"
        "Bob,25,8.0,false\n"
        "Charlie,35,7.5,true\n"
    )
    return str(path)


@pytest.fixture
def string_only_csv(tmp_path):
    """CSV with only string columns."""
    path = tmp_path / "strings.csv"
    path.write_text("first,last,city\nAlice,Smith,NYC\nBob,Jones,LA\n")
    return str(path)


@pytest.fixture
def single_col_csv(tmp_path):
    """CSV with a single integer column."""
    path = tmp_path / "one_col.csv"
    path.write_text("value\n1\n2\n3\n")
    return str(path)


# ---------------------------------------------------------------------------
# Normal behaviour — returns ArFrame
# ---------------------------------------------------------------------------


def test_select_dtypes_include_string_returns_arframe(mixed_csv):
    frame = ar.read_csv(mixed_csv)
    selected = frame.select_dtypes(include="string")
    assert isinstance(selected, ar.ArFrame)
    assert selected.columns == ["name"]


def test_select_dtypes_include_int64(mixed_csv):
    frame = ar.read_csv(mixed_csv)
    selected = frame.select_dtypes(include="int64")
    assert isinstance(selected, ar.ArFrame)
    assert selected.columns == ["age"]


def test_select_dtypes_include_float64(mixed_csv):
    frame = ar.read_csv(mixed_csv)
    selected = frame.select_dtypes(include="float64")
    assert isinstance(selected, ar.ArFrame)
    assert selected.columns == ["score"]


def test_select_dtypes_include_bool(mixed_csv):
    frame = ar.read_csv(mixed_csv)
    selected = frame.select_dtypes(include="bool")
    assert isinstance(selected, ar.ArFrame)
    assert selected.columns == ["active"]


def test_select_dtypes_include_multiple(mixed_csv):
    # exact order: "age" (col 1) before "score" (col 2) in the original frame
    frame = ar.read_csv(mixed_csv)
    selected = frame.select_dtypes(include=["int64", "float64"])
    assert isinstance(selected, ar.ArFrame)
    assert selected.columns == ["age", "score"]


def test_select_dtypes_preserves_column_order(mixed_csv):
    frame = ar.read_csv(mixed_csv)
    selected = frame.select_dtypes(include=["int64", "float64"])
    assert selected.columns.index("age") < selected.columns.index("score")


def test_select_dtypes_exclude_string(mixed_csv):
    frame = ar.read_csv(mixed_csv)
    selected = frame.select_dtypes(exclude="string")
    assert isinstance(selected, ar.ArFrame)
    assert "name" not in selected.columns
    assert set(selected.columns) == {"age", "score", "active"}


def test_select_dtypes_exclude_multiple(mixed_csv):
    frame = ar.read_csv(mixed_csv)
    selected = frame.select_dtypes(exclude=["int64", "float64"])
    assert set(selected.columns) == {"name", "active"}


def test_select_dtypes_include_all_returns_all_columns(mixed_csv):
    frame = ar.read_csv(mixed_csv)
    selected = frame.select_dtypes(include=["int64", "float64", "string", "bool"])
    assert set(selected.columns) == set(frame.columns)


def test_select_dtypes_result_has_correct_shape(mixed_csv):
    frame = ar.read_csv(mixed_csv)
    selected = frame.select_dtypes(include="string")
    assert selected.shape == (frame.shape[0], 1)


def test_select_dtypes_on_sample_csv(sample_csv):
    # sample_csv: name(string), age(int64), email(string), active(bool)
    frame = ar.read_csv(sample_csv)
    selected = frame.select_dtypes(include="string")
    assert isinstance(selected, ar.ArFrame)
    assert set(selected.columns) == {"name", "email"}


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


def test_select_dtypes_include_as_list_matches_string(mixed_csv):
    frame = ar.read_csv(mixed_csv)
    assert (
        frame.select_dtypes(include="string").columns
        == frame.select_dtypes(include=["string"]).columns
    )


def test_select_dtypes_include_as_tuple(mixed_csv):
    frame = ar.read_csv(mixed_csv)
    selected = frame.select_dtypes(include=("int64", "float64"))
    assert selected.columns == ["age", "score"]


def test_select_dtypes_single_column_frame(single_col_csv):
    frame = ar.read_csv(single_col_csv)
    selected = frame.select_dtypes(include="int64")
    assert isinstance(selected, ar.ArFrame)
    assert selected.columns == ["value"]


def test_select_dtypes_null_dtype_is_valid(mixed_csv):
    # "null" is a recognised dtype — no TypeError, but no null columns here
    frame = ar.read_csv(mixed_csv)
    with pytest.raises(ValueError, match="No columns match"):
        frame.select_dtypes(include="null")


# ---------------------------------------------------------------------------
# Empty match → raises ValueError
# ---------------------------------------------------------------------------


def test_select_dtypes_no_match_raises_value_error(string_only_csv):
    frame = ar.read_csv(string_only_csv)
    with pytest.raises(ValueError, match="No columns match"):
        frame.select_dtypes(include="int64")


def test_select_dtypes_exclude_all_raises_value_error(mixed_csv):
    frame = ar.read_csv(mixed_csv)
    with pytest.raises(ValueError, match="No columns match"):
        frame.select_dtypes(exclude=["int64", "float64", "string", "bool"])


# ---------------------------------------------------------------------------
# Overlap check → raises ValueError
# ---------------------------------------------------------------------------


def test_select_dtypes_include_exclude_overlap_raises(mixed_csv):
    frame = ar.read_csv(mixed_csv)
    with pytest.raises(ValueError, match="overlap"):
        frame.select_dtypes(include="int64", exclude="int64")


def test_select_dtypes_partial_overlap_raises(mixed_csv):
    frame = ar.read_csv(mixed_csv)
    with pytest.raises(ValueError, match="overlap"):
        frame.select_dtypes(include=["int64", "float64"], exclude=["float64", "string"])


# ---------------------------------------------------------------------------
# Invalid input → raises errors
# ---------------------------------------------------------------------------


def test_select_dtypes_no_args_raises_value_error(mixed_csv):
    frame = ar.read_csv(mixed_csv)
    with pytest.raises(ValueError, match="at least one of 'include' or 'exclude'"):
        frame.select_dtypes()


def test_select_dtypes_unknown_include_raises_value_error(mixed_csv):
    frame = ar.read_csv(mixed_csv)
    with pytest.raises(ValueError, match="Unrecognised dtype"):
        frame.select_dtypes(include="datetime64")


def test_select_dtypes_unknown_exclude_raises_value_error(mixed_csv):
    frame = ar.read_csv(mixed_csv)
    with pytest.raises(ValueError, match="Unrecognised dtype"):
        frame.select_dtypes(exclude="object")


def test_select_dtypes_unknown_dtype_in_list_raises(mixed_csv):
    frame = ar.read_csv(mixed_csv)
    with pytest.raises(ValueError, match="Unrecognised dtype"):
        frame.select_dtypes(include=["int64", "bad_type"])


def test_select_dtypes_wrong_type_for_include_raises_type_error(mixed_csv):
    frame = ar.read_csv(mixed_csv)
    with pytest.raises(TypeError, match="'include' must be a string"):
        frame.select_dtypes(include=42)


def test_select_dtypes_wrong_type_for_exclude_raises_type_error(mixed_csv):
    frame = ar.read_csv(mixed_csv)
    with pytest.raises(TypeError, match="'exclude' must be a string"):
        frame.select_dtypes(exclude=3.14)


def test_select_dtypes_error_message_shows_valid_dtypes(mixed_csv):
    frame = ar.read_csv(mixed_csv)
    with pytest.raises(ValueError) as exc_info:
        frame.select_dtypes(include="nope")
    msg = str(exc_info.value)
    assert "int64" in msg
    assert "float64" in msg


def test_select_dtypes_non_string_item_in_list_raises_type_error(mixed_csv):
    frame = ar.read_csv(mixed_csv)
    with pytest.raises(TypeError, match="must contain only strings"):
        frame.select_dtypes(include=[123])


def test_select_dtypes_non_string_item_in_exclude_raises_type_error(mixed_csv):
    frame = ar.read_csv(mixed_csv)
    with pytest.raises(TypeError, match="must contain only strings"):
        frame.select_dtypes(exclude=[None, "int64"])
