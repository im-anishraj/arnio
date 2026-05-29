"""
Regression tests for PR #1310 – OOM / caller-isolation fix.

These tests assert that every function changed in the PR does NOT mutate the
caller's original pandas DataFrame when the direct-pandas API path is exercised.
They also confirm that winsorize_outliers and parse_bool_strings do not mutate
the original ArFrame's underlying data.

Requested by reviewer: im-anishraj (owner) in PR #1310 review.
"""

import pandas as pd
import pytest

import arnio as ar
from arnio.cleaning import (
    coalesce_columns,
    combine_columns,
    parse_bool_strings,
    replace_values,
    round_numeric_columns,
    safe_divide_columns,
    standardize_missing_tokens,
    winsorize_outliers,
)

# ---------------------------------------------------------------------------
# winsorize_outliers — deep=False is safe because only whole-column
# reassignment (df[col] = ...) is performed, never in-place cell mutation.
# ---------------------------------------------------------------------------


class TestWinsorizeOutliersNoMutation:
    def test_arframe_input_not_mutated(self):
        """winsorize_outliers does not mutate the original ArFrame's data."""
        original_pd = pd.DataFrame({"val": [1.0, 2.0, 3.0, 4.0, 100.0]})
        frame = ar.from_pandas(original_pd.copy())
        _ = winsorize_outliers(frame, lower=0.1, upper=0.9)

        # The ArFrame round-trips back identically
        after = ar.to_pandas(frame)
        pd.testing.assert_frame_equal(after, original_pd, check_dtype=False)

    def test_pandas_values_unchanged_before_and_after(self):
        """winsorize_outliers result frame has clipped values; original is untouched."""
        original_pd = pd.DataFrame({"val": [1.0, 2.0, 3.0, 4.0, 100.0]})
        frame = ar.from_pandas(original_pd.copy())
        result = winsorize_outliers(frame, lower=0.1, upper=0.9)

        result_df = ar.to_pandas(result)
        # Clipping must have happened in the result
        assert result_df["val"].iloc[4] < 100.0
        # The original ArFrame is unaffected
        assert ar.to_pandas(frame)["val"].iloc[4] == pytest.approx(100.0)


# ---------------------------------------------------------------------------
# parse_bool_strings — deep=False is safe: only whole-column assignment used.
# ---------------------------------------------------------------------------


class TestParseBoolStringsNoMutation:
    def test_arframe_input_not_mutated(self):
        """parse_bool_strings does not mutate the underlying ArFrame."""
        original_pd = pd.DataFrame({"flag": ["true", "false", "yes", "unknown"]})
        frame = ar.from_pandas(original_pd.copy())
        _ = parse_bool_strings(frame)

        after = ar.to_pandas(frame)
        pd.testing.assert_frame_equal(after, original_pd, check_dtype=False)

    def test_result_has_parsed_values_original_unchanged(self):
        """parse_bool_strings result has booleans; original ArFrame strings intact."""
        original_pd = pd.DataFrame({"flag": ["true", "false"]})
        frame = ar.from_pandas(original_pd.copy())
        result = parse_bool_strings(frame)

        result_df = ar.to_pandas(result)
        assert result_df["flag"].iloc[0] == True
        # Original is still strings
        assert ar.to_pandas(frame)["flag"].iloc[0] == "true"


# ---------------------------------------------------------------------------
# replace_values — pandas-path must NOT mutate the caller's DataFrame.
# ---------------------------------------------------------------------------


class TestReplaceValuesNoMutation:
    def test_pandas_input_not_mutated_single_column(self):
        """replace_values does not mutate the caller's DataFrame (single column)."""
        original = pd.DataFrame({"x": [1, 2, 3], "y": [4, 5, 6]})
        snapshot = original.copy(deep=True)
        _ = replace_values(original, mapping={1: 99}, column="x")
        pd.testing.assert_frame_equal(original, snapshot)

    def test_pandas_input_not_mutated_all_columns(self):
        """replace_values does not mutate the caller's DataFrame (all columns)."""
        original = pd.DataFrame({"a": ["foo", "bar"], "b": ["baz", "foo"]})
        snapshot = original.copy(deep=True)
        _ = replace_values(original, mapping={"foo": "REPLACED"})
        pd.testing.assert_frame_equal(original, snapshot)

    def test_arframe_roundtrip_unaffected(self):
        """replace_values on an ArFrame leaves the original frame untouched."""
        original_pd = pd.DataFrame({"name": ["Alice", "Bob", "Alice"]})
        frame = ar.from_pandas(original_pd.copy())
        _ = replace_values(frame, mapping={"Alice": "Carol"})
        pd.testing.assert_frame_equal(ar.to_pandas(frame), original_pd, check_dtype=False)


# ---------------------------------------------------------------------------
# standardize_missing_tokens — must NOT mutate caller's DataFrame.
# ---------------------------------------------------------------------------


class TestStandardizeMissingTokensNoMutation:
    def test_pandas_input_not_mutated(self):
        """standardize_missing_tokens does not mutate the caller's DataFrame."""
        original = pd.DataFrame({"val": ["N/A", "hello", "NA", "world"]})
        snapshot = original.copy(deep=True)
        _ = standardize_missing_tokens(original)
        pd.testing.assert_frame_equal(original, snapshot)

    def test_pandas_subset_not_mutated(self):
        """standardize_missing_tokens with subset does not mutate the caller's DataFrame."""
        original = pd.DataFrame({"a": ["N/A", "ok"], "b": ["N/A", "fine"]})
        snapshot = original.copy(deep=True)
        _ = standardize_missing_tokens(original, subset=["a"])
        pd.testing.assert_frame_equal(original, snapshot)

    def test_arframe_not_mutated(self):
        """standardize_missing_tokens does not mutate the original ArFrame."""
        original_pd = pd.DataFrame({"val": ["N/A", "hello"]})
        frame = ar.from_pandas(original_pd.copy())
        _ = standardize_missing_tokens(frame)
        pd.testing.assert_frame_equal(ar.to_pandas(frame), original_pd, check_dtype=False)


# ---------------------------------------------------------------------------
# safe_divide_columns — must NOT mutate caller's DataFrame.
# ---------------------------------------------------------------------------


class TestSafeDivideColumnsNoMutation:
    def test_pandas_input_not_mutated(self):
        """safe_divide_columns does not mutate the caller's DataFrame."""
        original = pd.DataFrame({"num": [10.0, 20.0, 30.0], "den": [2.0, 0.0, 5.0]})
        snapshot = original.copy(deep=True)
        _ = safe_divide_columns(original, "num", "den", "ratio")
        pd.testing.assert_frame_equal(original, snapshot)

    def test_arframe_not_mutated(self):
        """safe_divide_columns string path does not mutate the original ArFrame."""
        original_pd = pd.DataFrame({"num": ["10", "20"], "den": ["2", "0"]})
        frame = ar.from_pandas(original_pd.copy())
        _ = safe_divide_columns(frame, "num", "den", "ratio")
        pd.testing.assert_frame_equal(ar.to_pandas(frame), original_pd, check_dtype=False)


# ---------------------------------------------------------------------------
# combine_columns — pandas-path must NOT mutate caller's DataFrame.
# ---------------------------------------------------------------------------


class TestCombineColumnsNoMutation:
    def test_pandas_input_not_mutated(self):
        """combine_columns does not mutate the caller's pandas DataFrame."""
        original = pd.DataFrame({"first": ["John", "Jane"], "last": ["Doe", "Smith"]})
        snapshot = original.copy(deep=True)
        _ = combine_columns(original, subset=["first", "last"], output_column="full")
        pd.testing.assert_frame_equal(original, snapshot)


# ---------------------------------------------------------------------------
# round_numeric_columns — must NOT mutate caller's DataFrame.
# ---------------------------------------------------------------------------


class TestRoundNumericColumnsNoMutation:
    def test_pandas_input_not_mutated(self):
        """round_numeric_columns does not mutate the caller's pandas DataFrame."""
        original = pd.DataFrame({"val": [1.555, 2.444, 3.678]})
        snapshot = original.copy(deep=True)
        _ = round_numeric_columns(original, decimals=1)
        pd.testing.assert_frame_equal(original, snapshot)

    def test_arframe_not_mutated(self):
        """round_numeric_columns does not mutate the original ArFrame."""
        original_pd = pd.DataFrame({"score": [1.555, 2.444]})
        frame = ar.from_pandas(original_pd.copy())
        _ = round_numeric_columns(frame, decimals=1)
        pd.testing.assert_frame_equal(ar.to_pandas(frame), original_pd, check_dtype=False)


# ---------------------------------------------------------------------------
# coalesce_columns — must NOT mutate caller's DataFrame.
# ---------------------------------------------------------------------------


class TestCoalesceColumnsNoMutation:
    def test_pandas_input_not_mutated(self):
        """coalesce_columns does not mutate the caller's pandas DataFrame."""
        original = pd.DataFrame({"a": [None, 2, None], "b": [1, None, 3]})
        snapshot = original.copy(deep=True)
        _ = coalesce_columns(original, subset=["a", "b"], output_column="result")
        pd.testing.assert_frame_equal(original, snapshot)

    def test_arframe_not_mutated(self):
        """coalesce_columns does not mutate the original ArFrame."""
        original_pd = pd.DataFrame({"a": [None, 2.0], "b": [1.0, None]})
        frame = ar.from_pandas(original_pd.copy())
        _ = coalesce_columns(frame, subset=["a", "b"], output_column="out")
        pd.testing.assert_frame_equal(ar.to_pandas(frame), original_pd, check_dtype=False)
