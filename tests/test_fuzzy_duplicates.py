"""Tests for find_fuzzy_duplicates."""

from __future__ import annotations

import pandas as pd
import pytest

import arnio as ar
from arnio import ArFrame


def _frame(*dicts) -> ArFrame:
    return ar.from_pandas(pd.DataFrame(list(dicts)))


# ---------------------------------------------------------------------------
# Basic grouping
# ---------------------------------------------------------------------------


class TestExactDuplicates:
    def test_exact_duplicates_always_grouped(self):
        frame = _frame(
            {"name": "Alice", "city": "Delhi"},
            {"name": "Bob", "city": "Mumbai"},
            {"name": "Alice", "city": "Delhi"},
        )
        groups = ar.find_fuzzy_duplicates(frame, threshold=1.0)
        assert [0, 2] in groups

    def test_no_duplicates_returns_empty(self):
        frame = _frame(
            {"name": "Alice"},
            {"name": "Bob"},
            {"name": "Carol"},
        )
        groups = ar.find_fuzzy_duplicates(frame, threshold=1.0)
        assert groups == []

    def test_empty_frame_returns_empty(self):
        frame = ar.from_pandas(pd.DataFrame({"name": pd.Series([], dtype=str)}))
        assert ar.find_fuzzy_duplicates(frame) == []

    def test_single_row_returns_empty(self):
        frame = _frame({"name": "Alice"})
        assert ar.find_fuzzy_duplicates(frame) == []


# ---------------------------------------------------------------------------
# ignore_case
# ---------------------------------------------------------------------------


class TestIgnoreCase:
    def test_case_difference_grouped_when_ignore_case_true(self):
        frame = _frame({"name": "John Doe"}, {"name": "john doe"})
        groups = ar.find_fuzzy_duplicates(frame, threshold=1.0, ignore_case=True)
        assert [0, 1] in groups

    def test_case_difference_not_grouped_when_ignore_case_false(self):
        frame = _frame({"name": "John Doe"}, {"name": "john doe"})
        groups = ar.find_fuzzy_duplicates(frame, threshold=1.0, ignore_case=False)
        assert groups == []


# ---------------------------------------------------------------------------
# normalize_whitespace
# ---------------------------------------------------------------------------


class TestNormalizeWhitespace:
    def test_extra_spaces_grouped_when_normalize_true(self):
        frame = _frame({"name": "John  Doe"}, {"name": "John Doe"})
        groups = ar.find_fuzzy_duplicates(
            frame, threshold=1.0, normalize_whitespace=True
        )
        assert [0, 1] in groups

    def test_extra_spaces_not_grouped_when_normalize_false(self):
        frame = _frame({"name": "John  Doe"}, {"name": "John Doe"})
        groups = ar.find_fuzzy_duplicates(
            frame, threshold=1.0, normalize_whitespace=False
        )
        assert groups == []


# ---------------------------------------------------------------------------
# Threshold behaviour
# ---------------------------------------------------------------------------


class TestThreshold:
    def test_typo_grouped_at_low_threshold(self):
        # "John Doe" vs "Jon Doe" — one char difference, high similarity
        frame = _frame({"name": "John Doe"}, {"name": "Jon Doe"})
        groups = ar.find_fuzzy_duplicates(frame, threshold=0.7, ignore_case=False)
        assert [0, 1] in groups

    def test_typo_not_grouped_at_high_threshold(self):
        frame = _frame({"name": "John Doe"}, {"name": "Jon Doe"})
        groups = ar.find_fuzzy_duplicates(frame, threshold=1.0, ignore_case=False)
        assert groups == []

    def test_threshold_zero_groups_all_rows(self):
        frame = _frame({"name": "Alice"}, {"name": "Bob"}, {"name": "Carol"})
        groups = ar.find_fuzzy_duplicates(frame, threshold=0.0)
        # All rows should be in one group
        all_indices = sorted(i for g in groups for i in g)
        assert all_indices == [0, 1, 2]

    def test_threshold_out_of_range_raises(self):
        frame = _frame({"name": "Alice"})
        with pytest.raises(ValueError, match="threshold"):
            ar.find_fuzzy_duplicates(frame, threshold=1.5)

    def test_threshold_negative_raises(self):
        frame = _frame({"name": "Alice"})
        with pytest.raises(ValueError, match="threshold"):
            ar.find_fuzzy_duplicates(frame, threshold=-0.1)


# ---------------------------------------------------------------------------
# subset
# ---------------------------------------------------------------------------


class TestSubset:
    def test_subset_limits_comparison_columns(self):
        frame = _frame(
            {"name": "Alice", "city": "Delhi"},
            {"name": "Alice", "city": "Mumbai"},
        )
        # Names match exactly, cities differ — grouping only on name
        groups = ar.find_fuzzy_duplicates(frame, subset=["name"], threshold=1.0)
        assert [0, 1] in groups

    def test_subset_missing_column_raises(self):
        frame = _frame({"name": "Alice"})
        with pytest.raises(ValueError, match="not found"):
            ar.find_fuzzy_duplicates(frame, subset=["nonexistent"])

    def test_subset_empty_raises(self):
        frame = _frame({"name": "Alice"})
        with pytest.raises(ValueError, match="empty"):
            ar.find_fuzzy_duplicates(frame, subset=[])


# ---------------------------------------------------------------------------
# Mixed column types
# ---------------------------------------------------------------------------


class TestMixedTypes:
    def test_numeric_column_uses_exact_equality(self):
        frame = ar.from_pandas(
            pd.DataFrame(
                {
                    "name": ["Alice", "Alice"],
                    "age": pd.array([30, 31], dtype="Int64"),
                }
            )
        )
        # Names match but ages differ — should NOT be grouped at threshold=1.0
        groups = ar.find_fuzzy_duplicates(frame, subset=["name", "age"], threshold=1.0)
        assert groups == []

    def test_string_column_only_by_default(self):
        frame = ar.from_pandas(
            pd.DataFrame(
                {
                    "name": ["Alice", "Alice"],
                    "score": [1.0, 2.0],
                }
            )
        )
        # Default subset picks string cols only; names match
        groups = ar.find_fuzzy_duplicates(frame, threshold=1.0)
        assert [0, 1] in groups


# ---------------------------------------------------------------------------
# Transitive grouping
# ---------------------------------------------------------------------------


class TestTransitiveGrouping:
    def test_transitive_near_duplicates_grouped_together(self):
        # row0 ~ row1, row1 ~ row2 → all three in one group
        frame = _frame(
            {"name": "John Doe"},
            {"name": "john doe"},  # same as row0 with ignore_case
            {"name": "john doe "},  # same as row1 with normalize_whitespace
        )
        groups = ar.find_fuzzy_duplicates(
            frame,
            threshold=1.0,
            ignore_case=True,
            normalize_whitespace=True,
        )
        all_indices = sorted(i for g in groups for i in g)
        assert 0 in all_indices
        assert 1 in all_indices
        assert 2 in all_indices


# ---------------------------------------------------------------------------
# Pandas DataFrame input
# ---------------------------------------------------------------------------


class TestPandasInput:
    def test_accepts_pandas_dataframe(self):
        df = pd.DataFrame({"name": ["Alice", "alice"]})
        groups = ar.find_fuzzy_duplicates(df, threshold=1.0, ignore_case=True)
        assert [0, 1] in groups


# ---------------------------------------------------------------------------
# dtype helpers regression
# ---------------------------------------------------------------------------


class TestNullableNumericDtype:
    def test_nullable_int64_uses_exact_equality(self):
        """Nullable Int64 must use exact equality, not string similarity."""
        df = pd.DataFrame(
            {
                "name": ["Alice", "Alice"],
                "id": pd.array([1000, 1001], dtype="Int64"),
            }
        )
        groups = ar.find_fuzzy_duplicates(df, subset=["name", "id"])
        assert groups == []

    def test_nullable_uint64_uses_exact_equality(self):
        df = pd.DataFrame(
            {
                "name": ["Bob", "Bob"],
                "code": pd.array([99, 100], dtype="UInt64"),
            }
        )
        groups = ar.find_fuzzy_duplicates(df, subset=["name", "code"])
        assert groups == []


class TestInvalidInput:
    def test_invalid_input_type_raises_typeerror(self):
        with pytest.raises(TypeError, match="ArFrame or pandas DataFrame"):
            ar.find_fuzzy_duplicates({"name": ["Alice", "Alice"]})

    def test_list_input_raises_typeerror(self):
        with pytest.raises(TypeError, match="ArFrame or pandas DataFrame"):
            ar.find_fuzzy_duplicates([["Alice"], ["Alice"]])


class TestNullableNAHandling:
    def test_nullable_int64_both_na_treated_as_exact_match(self):
        """Two pd.NA values in a numeric column count as matching."""
        df = pd.DataFrame(
            {
                "name": ["Alice", "Alice"],
                "id": pd.array([pd.NA, pd.NA], dtype="Int64"),
            }
        )
        groups = ar.find_fuzzy_duplicates(df, subset=["name", "id"], threshold=1.0)
        assert [0, 1] in groups

    def test_nullable_int64_one_na_treated_as_mismatch(self):
        """pd.NA vs a real value counts as mismatch — rows not grouped."""
        df = pd.DataFrame(
            {
                "name": ["Alice", "Alice"],
                "id": pd.array([pd.NA, 1001], dtype="Int64"),
            }
        )
        groups = ar.find_fuzzy_duplicates(df, subset=["name", "id"], threshold=1.0)
        assert groups == []

    def test_nullable_boolean_with_na_does_not_crash(self):
        """Nullable boolean column containing pd.NA must not raise TypeError."""
        df = pd.DataFrame(
            {
                "name": ["Alice", "Alice"],
                "flag": pd.array([pd.NA, True], dtype="boolean"),
            }
        )
        # Should not raise — result doesn't matter, just no crash
        result = ar.find_fuzzy_duplicates(df, subset=["name", "flag"], threshold=1.0)
        assert isinstance(result, list)

    def test_nullable_boolean_both_na_treated_as_exact_match(self):
        df = pd.DataFrame(
            {
                "name": ["Bob", "Bob"],
                "flag": pd.array([pd.NA, pd.NA], dtype="boolean"),
            }
        )
        groups = ar.find_fuzzy_duplicates(df, subset=["name", "flag"], threshold=1.0)
        assert [0, 1] in groups
