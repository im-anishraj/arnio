"""
Tests for ArFrame.__getitem__ — single-column (list), multi-column (ArFrame),
missing-column, and invalid-key cases.
"""

import pandas as pd
import pytest

import arnio as ar
from arnio.frame import ArFrame


@pytest.fixture
def frame():
    df = pd.DataFrame(
        {
            "name": ["Alice", "Bob", "Charlie"],
            "age": [30, 25, 35],
            "active": [True, False, True],
        }
    )
    return ar.from_pandas(df)


# ── Single str key → list ─────────────────────────────────────────────────────


def test_getitem_single_returns_list(frame):
    assert isinstance(frame["name"], list)


def test_getitem_single_correct_values(frame):
    assert frame["name"] == ["Alice", "Bob", "Charlie"]


def test_getitem_single_numeric_column(frame):
    assert frame["age"] == [30, 25, 35]


def test_getitem_single_bool_column(frame):
    assert frame["active"] == [True, False, True]


def test_getitem_single_preserves_row_count(frame):
    assert len(frame["name"]) == 3


# ── List key → ArFrame ────────────────────────────────────────────────────────


def test_getitem_multi_returns_arframe(frame):
    assert isinstance(frame[["name", "age"]], ArFrame)


def test_getitem_multi_correct_column_count(frame):
    assert frame[["name", "age"]].shape[1] == 2


def test_getitem_multi_correct_column_names(frame):
    assert frame[["name", "age"]].columns == ["name", "age"]


def test_getitem_multi_preserves_row_count(frame):
    assert frame[["name", "age"]].shape[0] == 3


def test_getitem_multi_preserves_requested_order(frame):
    assert frame[["active", "name"]].columns == ["active", "name"]


def test_getitem_all_columns(frame):
    result = frame[["name", "age", "active"]]
    assert result.columns == ["name", "age", "active"]
    assert result.shape == frame.shape


def test_getitem_single_item_list(frame):
    result = frame[["name"]]
    assert isinstance(result, ArFrame)
    assert result.columns == ["name"]


# ── Missing column errors ─────────────────────────────────────────────────────


def test_getitem_missing_single_raises_key_error(frame):
    with pytest.raises(KeyError):
        frame["nonexistent"]


def test_getitem_missing_single_error_mentions_column(frame):
    with pytest.raises(KeyError, match="nonexistent"):
        frame["nonexistent"]


def test_getitem_missing_one_of_multi_raises_key_error(frame):
    with pytest.raises(KeyError):
        frame[["name", "ghost"]]


def test_getitem_missing_all_of_multi_raises_key_error(frame):
    with pytest.raises(KeyError):
        frame[["ghost1", "ghost2"]]


# ── Invalid key types ─────────────────────────────────────────────────────────


def test_getitem_int_key_raises_type_error(frame):
    with pytest.raises(TypeError):
        frame[0]


def test_getitem_none_key_raises_type_error(frame):
    with pytest.raises(TypeError):
        frame[None]


def test_getitem_tuple_key_raises_type_error(frame):
    with pytest.raises(TypeError):
        frame[("name", "age")]


def test_getitem_slice_raises_type_error(frame):
    with pytest.raises(TypeError):
        frame[0:2]


def test_getitem_list_with_non_string_element_raises_type_error(frame):
    with pytest.raises(TypeError):
        frame[["name", 1]]
