"""Tests for the normalize_whitespace pipeline step."""

import pandas as pd
import pytest

import arnio as ar


def test_collapses_multiple_internal_spaces():
    frame = ar.from_pandas(pd.DataFrame({"name": ["hello   world"]}))
    result = ar.to_pandas(ar.pipeline(frame, [("normalize_whitespace",)]))
    assert result["name"][0] == "hello world"


def test_collapses_internal_tab():
    frame = ar.from_pandas(pd.DataFrame({"name": ["name:\tAlice"]}))
    result = ar.to_pandas(ar.pipeline(frame, [("normalize_whitespace",)]))
    assert result["name"][0] == "name: Alice"


def test_collapses_internal_newline():
    frame = ar.from_pandas(pd.DataFrame({"name": ["line1\nline2"]}))
    result = ar.to_pandas(ar.pipeline(frame, [("normalize_whitespace",)]))
    assert result["name"][0] == "line1 line2"


def test_strips_edges_and_collapses_internal():
    frame = ar.from_pandas(pd.DataFrame({"name": ["  hi   there  "]}))
    result = ar.to_pandas(ar.pipeline(frame, [("normalize_whitespace",)]))
    assert result["name"][0] == "hi there"


def test_already_clean_string_unchanged():
    frame = ar.from_pandas(pd.DataFrame({"name": ["hello world"]}))
    result = ar.to_pandas(ar.pipeline(frame, [("normalize_whitespace",)]))
    assert result["name"][0] == "hello world"


def test_empty_string_stays_empty():
    frame = ar.from_pandas(pd.DataFrame({"name": [""]}))
    result = ar.to_pandas(ar.pipeline(frame, [("normalize_whitespace",)]))
    assert result["name"][0] == ""


def test_whitespace_only_string_becomes_empty():
    frame = ar.from_pandas(pd.DataFrame({"name": ["   \t\n   "]}))
    result = ar.to_pandas(ar.pipeline(frame, [("normalize_whitespace",)]))
    assert result["name"][0] == ""


def test_skips_non_string_columns_by_default():
    frame = ar.from_pandas(pd.DataFrame({"age": [25, 30]}))
    result = ar.to_pandas(ar.pipeline(frame, [("normalize_whitespace",)]))
    assert list(result["age"]) == [25, 30]


def test_columns_argument_targets_only_specified_column():
    frame = ar.from_pandas(
        pd.DataFrame(
            {
                "name": ["hello   world"],
                "city": ["new   york"],
            }
        )
    )
    result = ar.to_pandas(
        ar.pipeline(frame, [("normalize_whitespace", {"columns": ["name"]})])
    )
    assert result["name"][0] == "hello world"
    assert result["city"][0] == "new   york"


def test_pandas_dataframe_input_returns_dataframe():
    df = pd.DataFrame({"name": ["hello   world"]})
    result = ar.normalize_whitespace(df)
    assert isinstance(result, pd.DataFrame)
    assert result["name"][0] == "hello world"


def test_missing_column_raises_value_error():
    frame = ar.from_pandas(pd.DataFrame({"name": ["hello world"]}))
    with pytest.raises(ValueError, match="Missing columns for normalize_whitespace"):
        ar.pipeline(frame, [("normalize_whitespace", {"columns": ["nonexistent"]})])


def test_explicit_non_string_column_is_skipped():
    frame = ar.from_pandas(
        pd.DataFrame({"age": [25, 30], "name": ["hello   world", "foo   bar"]})
    )
    result = ar.to_pandas(
        ar.pipeline(frame, [("normalize_whitespace", {"columns": ["age", "name"]})])
    )
    assert list(result["age"]) == [25, 30]
    assert result["name"][0] == "hello world"
