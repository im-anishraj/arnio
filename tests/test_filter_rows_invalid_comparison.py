"""Tests for filter_rows with invalid / incompatible comparison types.

Covers the audit requirement from issue #614: filter_rows should test
incompatible comparison values inside pipeline execution.
"""

import pandas as pd
import pytest

import arnio as ar

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_frame(data: dict) -> ar.ArFrame:
    """Shorthand to build an ArFrame from a dict."""
    return ar.from_pandas(pd.DataFrame(data))


# ---------------------------------------------------------------------------
# Incompatible ordering comparisons via pipeline (>, <, >=, <=)
# ---------------------------------------------------------------------------


class TestFilterRowsInvalidComparisonTypesPipeline:
    """Incompatible comparison values passed through ar.pipeline()."""

    def test_gt_string_column_with_int_value(self):
        """Ordering a string column against an int should raise TypeError."""
        frame = _make_frame({"name": ["Alice", "Bob", "Charlie"]})
        with pytest.raises(TypeError):
            ar.pipeline(
                frame,
                [("filter_rows", {"column": "name", "op": ">", "value": 10})],
            )

    def test_lt_string_column_with_int_value(self):
        """Ordering a string column against an int should raise TypeError."""
        frame = _make_frame({"name": ["Alice", "Bob"]})
        with pytest.raises(TypeError):
            ar.pipeline(
                frame,
                [("filter_rows", {"column": "name", "op": "<", "value": 5})],
            )

    def test_ge_string_column_with_float_value(self):
        """Ordering a string column against a float should raise TypeError."""
        frame = _make_frame({"city": ["NYC", "London"]})
        with pytest.raises(TypeError):
            ar.pipeline(
                frame,
                [("filter_rows", {"column": "city", "op": ">=", "value": 3.14})],
            )

    def test_le_int_column_with_string_value(self):
        """Ordering an int column against a string should raise TypeError."""
        frame = _make_frame({"age": [20, 30, 40]})
        with pytest.raises(TypeError):
            ar.pipeline(
                frame,
                [("filter_rows", {"column": "age", "op": "<=", "value": "thirty"})],
            )

    def test_gt_int_column_with_list_value(self):
        """Comparing an int column against a list raises ValueError (length mismatch)."""
        frame = _make_frame({"score": [80, 90, 100]})
        with pytest.raises(ValueError, match="Lengths must be equal"):
            ar.pipeline(
                frame,
                [("filter_rows", {"column": "score", "op": ">", "value": [50]})],
            )

    def test_lt_int_column_with_dict_value(self):
        """Comparing an int column against a dict should raise TypeError."""
        frame = _make_frame({"score": [80, 90]})
        with pytest.raises(TypeError):
            ar.pipeline(
                frame,
                [("filter_rows", {"column": "score", "op": "<", "value": {"a": 1}})],
            )

    # ---------------------------------------------------------------------------
    # Equality comparisons with type mismatches (==, !=)
    # These don't raise in pandas — they just produce no matches / all matches.
    # The test documents this contract: incompatible == silently returns no rows.
    # ---------------------------------------------------------------------------

    def test_eq_int_column_with_string_value_returns_empty(self):
        """== between int column and string returns zero matches (no crash)."""
        frame = _make_frame({"age": [20, 30, 40]})
        result = ar.pipeline(
            frame,
            [("filter_rows", {"column": "age", "op": "==", "value": "thirty"})],
        )
        result_df = ar.to_pandas(result)
        assert len(result_df) == 0

    def test_ne_int_column_with_string_value_returns_all(self):
        """!= between int column and string returns all rows (no crash)."""
        frame = _make_frame({"age": [20, 30, 40]})
        result = ar.pipeline(
            frame,
            [("filter_rows", {"column": "age", "op": "!=", "value": "thirty"})],
        )
        result_df = ar.to_pandas(result)
        assert len(result_df) == 3

    def test_eq_string_column_with_int_value_returns_empty(self):
        """== between string column and int returns zero matches (no crash)."""
        frame = _make_frame({"name": ["Alice", "Bob"]})
        result = ar.pipeline(
            frame,
            [("filter_rows", {"column": "name", "op": "==", "value": 42})],
        )
        result_df = ar.to_pandas(result)
        assert len(result_df) == 0

    # ---------------------------------------------------------------------------
    # Comparison with None / NaN values
    # ---------------------------------------------------------------------------

    def test_gt_with_none_value(self):
        """Ordering comparison against None should raise TypeError."""
        frame = _make_frame({"age": [20, 30, 40]})
        with pytest.raises(TypeError):
            ar.pipeline(
                frame,
                [("filter_rows", {"column": "age", "op": ">", "value": None})],
            )

    def test_eq_with_none_returns_empty_for_non_null_column(self):
        """== against None on a non-null int column returns no rows."""
        frame = _make_frame({"age": [20, 30, 40]})
        result = ar.pipeline(
            frame,
            [("filter_rows", {"column": "age", "op": "==", "value": None})],
        )
        result_df = ar.to_pandas(result)
        assert len(result_df) == 0

    # ---------------------------------------------------------------------------
    # Bool column with non-bool comparison value
    # ---------------------------------------------------------------------------

    def test_gt_bool_column_with_string_value(self):
        """Ordering a bool column against a string should raise TypeError."""
        frame = _make_frame({"active": [True, False, True]})
        with pytest.raises(TypeError):
            ar.pipeline(
                frame,
                [("filter_rows", {"column": "active", "op": ">", "value": "yes"})],
            )

    # ---------------------------------------------------------------------------
    # Multi-step pipeline with invalid filter in the middle
    # ---------------------------------------------------------------------------

    def test_invalid_comparison_in_multi_step_pipeline(self):
        """A type-incompatible filter_rows step should fail even when chained."""
        frame = _make_frame({"name": ["  Alice  ", "  Bob  "], "age": [30, 25]})
        with pytest.raises(TypeError):
            ar.pipeline(
                frame,
                [
                    ("strip_whitespace",),
                    ("filter_rows", {"column": "name", "op": ">", "value": 100}),
                ],
            )

    # ---------------------------------------------------------------------------
    # Direct API path (not via pipeline) — same invalid comparison
    # ---------------------------------------------------------------------------

    def test_direct_api_gt_string_vs_int_raises(self):
        """Direct ar.filter_rows() also raises on incompatible ordering."""
        frame = _make_frame({"name": ["Alice", "Bob"]})
        with pytest.raises(TypeError):
            ar.filter_rows(frame, column="name", op=">", value=10)

    def test_direct_api_eq_int_vs_string_returns_empty(self):
        """Direct ar.filter_rows() with == on mismatched types returns empty."""
        frame = _make_frame({"age": [20, 30]})
        result = ar.filter_rows(frame, column="age", op="==", value="twenty")
        result_df = ar.to_pandas(result)
        assert len(result_df) == 0

    def test_direct_api_ne_int_vs_string_returns_all(self):
        """Direct ar.filter_rows() with != on mismatched types returns all."""
        frame = _make_frame({"age": [20, 30]})
        result = ar.filter_rows(frame, column="age", op="!=", value="twenty")
        result_df = ar.to_pandas(result)
        assert len(result_df) == 2
