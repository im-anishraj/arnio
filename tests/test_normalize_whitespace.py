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


def test_only_whitespace_becomes_empty():
    """String with only whitespace becomes empty string."""
    frame = ar.from_pandas(pd.DataFrame({"name": ["   \t\n   "]}))
    result = ar.to_pandas(ar.pipeline(frame, [("normalize_whitespace",)]))
    assert result["name"][0] == ""


def test_multiple_whitespace_types_combined():
    """Multiple whitespace characters (spaces, tabs, newlines) are collapsed."""
    frame = ar.from_pandas(pd.DataFrame({"text": ["hello  \t\n  world"]}))
    result = ar.to_pandas(ar.pipeline(frame, [("normalize_whitespace",)]))
    assert result["text"][0] == "hello world"


def test_carriage_return_handled():
    """Carriage return characters are normalized."""
    frame = ar.from_pandas(pd.DataFrame({"text": ["hello\rworld"]}))
    result = ar.to_pandas(ar.pipeline(frame, [("normalize_whitespace",)]))
    assert result["text"][0] == "hello world"


def test_normalize_whitespace_preserves_case():
    """Whitespace normalization does not change character case."""
    frame = ar.from_pandas(pd.DataFrame({"name": ["  ALICE  ", "  bob  "]}))
    result = ar.to_pandas(ar.pipeline(frame, [("normalize_whitespace",)]))
    assert result["name"][0] == "ALICE"
    assert result["name"][1] == "bob"


def test_normalize_whitespace_multiple_rows():
    """Normalization works across multiple rows."""
    frame = ar.from_pandas(
        pd.DataFrame(
            {
                "name": [
                    "  alice  ",
                    "bob\t\t",
                    "  carol  ",
                ]
            }
        )
    )
    result = ar.to_pandas(ar.pipeline(frame, [("normalize_whitespace",)]))
    assert result["name"].tolist() == ["alice", "bob", "carol"]


def test_normalize_whitespace_direct_arframe_call():
    """normalize_whitespace works as a direct ArFrame method via pipeline."""
    frame = ar.from_pandas(pd.DataFrame({"text": ["  hello  "]}))
    result_frame = ar.pipeline(frame, [("normalize_whitespace",)])
    assert isinstance(result_frame, ar.ArFrame)
    result_df = ar.to_pandas(result_frame)
    assert result_df["text"][0] == "hello"


def test_normalize_whitespace_preserves_other_columns():
    """Non-string columns are not affected by normalize_whitespace."""
    frame = ar.from_pandas(
        pd.DataFrame(
            {
                "name": ["  alice  "],
                "age": [30],
                "score": [95.5],
                "active": [True],
            }
        )
    )
    result = ar.to_pandas(ar.pipeline(frame, [("normalize_whitespace",)]))
    assert result["name"][0] == "alice"
    assert result["age"][0] == 30
    assert result["score"][0] == 95.5
    assert result["active"][0]


def test_normalize_whitespace_empty_frame():
    """normalize_whitespace handles empty frame."""
    frame = ar.from_pandas(pd.DataFrame({"name": pd.Series([], dtype="string")}))
    result = ar.to_pandas(ar.pipeline(frame, [("normalize_whitespace",)]))
    assert len(result) == 0


def test_leading_whitespace_only():
    """String with only leading whitespace is trimmed."""
    frame = ar.from_pandas(pd.DataFrame({"name": ["   hello"]}))
    result = ar.to_pandas(ar.pipeline(frame, [("normalize_whitespace",)]))
    assert result["name"][0] == "hello"
