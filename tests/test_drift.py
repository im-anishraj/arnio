"""Focused tests for detect_drift() and DriftReport (issue #858)."""

from __future__ import annotations

import json

import pandas as pd
import pytest

import arnio as ar
from arnio.quality import DriftReport

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _frame(data: dict) -> ar.ArFrame:
    """Build an ArFrame from a plain dict of column→list pairs."""
    return ar.from_pandas(pd.DataFrame(data))


# ---------------------------------------------------------------------------
# Schema-change detection
# ---------------------------------------------------------------------------


def test_added_column_detected():
    old = _frame({"id": [1, 2, 3], "name": ["a", "b", "c"]})
    new = _frame({"id": [1, 2, 3], "name": ["a", "b", "c"], "score": [10, 20, 30]})

    report = ar.detect_drift(old, new)

    assert report.added_columns == ["score"]
    assert report.removed_columns == []
    assert report.has_drift is True


def test_removed_column_detected():
    old = _frame({"id": [1, 2, 3], "name": ["a", "b", "c"], "score": [10, 20, 30]})
    new = _frame({"id": [1, 2, 3], "name": ["a", "b", "c"]})

    report = ar.detect_drift(old, new)

    assert report.removed_columns == ["score"]
    assert report.added_columns == []
    assert report.has_drift is True


def test_added_and_removed_columns_detected_simultaneously():
    old = _frame({"id": [1, 2], "old_col": ["x", "y"]})
    new = _frame({"id": [1, 2], "new_col": [9, 8]})

    report = ar.detect_drift(old, new)

    assert report.added_columns == ["new_col"]
    assert report.removed_columns == ["old_col"]
    assert report.has_drift is True


# ---------------------------------------------------------------------------
# Dtype-change detection
# ---------------------------------------------------------------------------


def test_dtype_change_detected_int_to_string():
    old = _frame({"id": [1, 2, 3], "value": [10, 20, 30]})  # value: int64
    new = _frame({"id": [1, 2, 3], "value": ["a", "b", "c"]})  # value: string/object

    report = ar.detect_drift(old, new)

    assert "value" in report.dtype_changes
    old_dtype, new_dtype = report.dtype_changes["value"]
    assert old_dtype != new_dtype
    assert report.has_drift is True


def test_no_dtype_change_for_stable_schema():
    old = _frame({"id": [1, 2, 3], "score": [1.0, 2.0, 3.0]})
    new = _frame({"id": [4, 5, 6], "score": [4.0, 5.0, 6.0]})

    report = ar.detect_drift(old, new)

    assert report.dtype_changes == {}


# ---------------------------------------------------------------------------
# Null-ratio change detection
# ---------------------------------------------------------------------------


def test_null_ratio_increase_detected():
    old = _frame({"id": [1, 2, 3], "score": [10.0, 20.0, 30.0]})
    new = _frame({"id": [1, 2, 3], "score": [10.0, None, None]})

    report = ar.detect_drift(old, new)

    assert "score" in report.null_ratio_changes
    old_ratio, new_ratio = report.null_ratio_changes["score"]
    assert old_ratio == 0.0
    assert new_ratio > 0.0
    assert report.has_drift is True


def test_null_ratio_no_change_when_both_frames_clean():
    old = _frame({"a": [1, 2, 3], "b": ["x", "y", "z"]})
    new = _frame({"a": [4, 5, 6], "b": ["p", "q", "r"]})

    report = ar.detect_drift(old, new)

    assert report.null_ratio_changes == {}


# ---------------------------------------------------------------------------
# Row-count difference
# ---------------------------------------------------------------------------


def test_row_count_difference_reported():
    old = _frame({"id": [1, 2, 3]})
    new = _frame({"id": [1, 2, 3, 4, 5]})

    report = ar.detect_drift(old, new)

    assert report.row_count == (3, 5)
    assert report.has_drift is True


def test_row_count_same_is_preserved():
    old = _frame({"x": [1, 2]})
    new = _frame({"x": [3, 4]})

    report = ar.detect_drift(old, new)

    assert report.row_count == (2, 2)


# ---------------------------------------------------------------------------
# No-drift case
# ---------------------------------------------------------------------------


def test_no_drift_case_returns_has_drift_false():
    data = {
        "id": [1, 2, 3],
        "name": ["alice", "bob", "carol"],
        "score": [1.0, 2.0, 3.0],
    }
    old = _frame(data)
    new = _frame(data)

    report = ar.detect_drift(old, new)

    assert report.has_drift is False
    assert report.added_columns == []
    assert report.removed_columns == []
    assert report.dtype_changes == {}
    assert report.null_ratio_changes == {}
    assert report.row_count[0] == report.row_count[1]


# ---------------------------------------------------------------------------
# Empty-frame edge case
# ---------------------------------------------------------------------------


def test_empty_old_frame_all_columns_appear_as_added():
    old = ar.from_pandas(pd.DataFrame({"id": pd.Series([], dtype="int64")}))
    new = _frame({"id": [1, 2], "name": ["a", "b"]})

    report = ar.detect_drift(old, new)

    assert "name" in report.added_columns
    assert report.row_count == (0, 2)
    assert report.has_drift is True


def test_empty_new_frame_all_columns_appear_as_removed():
    old = _frame({"id": [1, 2], "name": ["a", "b"]})
    new = ar.from_pandas(pd.DataFrame({"id": pd.Series([], dtype="int64")}))

    report = ar.detect_drift(old, new)

    assert "name" in report.removed_columns
    assert report.row_count == (2, 0)
    assert report.has_drift is True


# ---------------------------------------------------------------------------
# JSON serialisation
# ---------------------------------------------------------------------------


def test_to_dict_is_json_serializable():
    old = _frame({"id": [1, 2, 3], "score": [1.0, None, 3.0]})
    new = _frame(
        {
            "id": [1, 2, 3, 4],
            "score": [1.0, 2.0, None, 4.0],
            "tag": ["a", "b", "c", "d"],
        }
    )

    report = ar.detect_drift(old, new)

    d = report.to_dict()
    serialized = json.dumps(d)  # must not raise
    restored = json.loads(serialized)

    assert restored["has_drift"] is True
    assert "tag" in restored["added_columns"]
    assert isinstance(restored["row_count"], list)
    assert len(restored["row_count"]) == 2


def test_to_dict_no_drift_is_json_serializable():
    data = {"x": [1, 2, 3]}
    old = _frame(data)
    new = _frame(data)

    report = ar.detect_drift(old, new)
    d = report.to_dict()

    assert json.dumps(d) is not None
    assert d["has_drift"] is False


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------


def test_invalid_old_raises_type_error():
    new = _frame({"x": [1, 2]})

    with pytest.raises(TypeError, match="old"):
        ar.detect_drift("not_a_frame", new)  # type: ignore[arg-type]


def test_invalid_new_raises_type_error():
    old = _frame({"x": [1, 2]})

    with pytest.raises(TypeError, match="new"):
        ar.detect_drift(old, 42)  # type: ignore[arg-type]


def test_both_invalid_raises_type_error():
    with pytest.raises(TypeError):
        ar.detect_drift(None, None)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# DriftReport dataclass validation
# ---------------------------------------------------------------------------


def test_drift_report_rejects_non_list_added_columns():
    with pytest.raises(TypeError, match="added_columns"):
        DriftReport(
            added_columns="col",  # type: ignore[arg-type]
            removed_columns=[],
            dtype_changes={},
            null_ratio_changes={},
            row_count=(0, 0),
        )


def test_drift_report_rejects_non_list_removed_columns():
    with pytest.raises(TypeError, match="removed_columns"):
        DriftReport(
            added_columns=[],
            removed_columns={"col"},  # type: ignore[arg-type]
            dtype_changes={},
            null_ratio_changes={},
            row_count=(0, 0),
        )


def test_drift_report_rejects_bad_dtype_changes_value():
    with pytest.raises(TypeError, match="dtype_changes"):
        DriftReport(
            added_columns=[],
            removed_columns=[],
            dtype_changes={"col": "int64"},  # type: ignore[dict-item]  # must be tuple
            null_ratio_changes={},
            row_count=(0, 0),
        )


def test_drift_report_rejects_negative_row_count():
    with pytest.raises(ValueError, match="row_count"):
        DriftReport(
            added_columns=[],
            removed_columns=[],
            dtype_changes={},
            null_ratio_changes={},
            row_count=(-1, 0),
        )


def test_drift_report_rejects_bool_row_count():
    with pytest.raises(TypeError, match="row_count"):
        DriftReport(
            added_columns=[],
            removed_columns=[],
            dtype_changes={},
            null_ratio_changes={},
            row_count=(True, 0),  # bool subclasses int — must be rejected
        )


# ---------------------------------------------------------------------------
# DriftReport null_ratio_changes value validation
# ---------------------------------------------------------------------------


def test_drift_report_rejects_non_numeric_null_ratio():
    with pytest.raises(TypeError, match="null_ratio_changes"):
        DriftReport(
            added_columns=[],
            removed_columns=[],
            dtype_changes={},
            null_ratio_changes={"score": ("0.1", "0.2")},  # strings, not floats
            row_count=(0, 0),
        )


def test_drift_report_rejects_bool_null_ratio():
    with pytest.raises(TypeError, match="null_ratio_changes"):
        DriftReport(
            added_columns=[],
            removed_columns=[],
            dtype_changes={},
            null_ratio_changes={"score": (True, 0.5)},  # bool subclasses float
            row_count=(0, 0),
        )


def test_drift_report_rejects_nan_null_ratio():
    with pytest.raises(ValueError, match="null_ratio_changes"):
        DriftReport(
            added_columns=[],
            removed_columns=[],
            dtype_changes={},
            null_ratio_changes={"score": (float("nan"), 0.5)},
            row_count=(0, 0),
        )


def test_drift_report_rejects_inf_null_ratio():
    with pytest.raises(ValueError, match="null_ratio_changes"):
        DriftReport(
            added_columns=[],
            removed_columns=[],
            dtype_changes={},
            null_ratio_changes={"score": (0.1, float("inf"))},
            row_count=(0, 0),
        )


def test_drift_report_rejects_negative_inf_null_ratio():
    with pytest.raises(ValueError, match="null_ratio_changes"):
        DriftReport(
            added_columns=[],
            removed_columns=[],
            dtype_changes={},
            null_ratio_changes={"score": (float("-inf"), 0.5)},
            row_count=(0, 0),
        )


def test_drift_report_rejects_out_of_range_null_ratio_above_one():
    with pytest.raises(ValueError, match="null_ratio_changes"):
        DriftReport(
            added_columns=[],
            removed_columns=[],
            dtype_changes={},
            null_ratio_changes={"score": (0.5, 1.5)},
            row_count=(0, 0),
        )


def test_drift_report_rejects_out_of_range_null_ratio_below_zero():
    with pytest.raises(ValueError, match="null_ratio_changes"):
        DriftReport(
            added_columns=[],
            removed_columns=[],
            dtype_changes={},
            null_ratio_changes={"score": (-0.1, 0.5)},
            row_count=(0, 0),
        )


def test_drift_report_accepts_valid_null_ratio_boundaries():
    # 0.0 and 1.0 are valid boundary values
    report = DriftReport(
        added_columns=[],
        removed_columns=[],
        dtype_changes={},
        null_ratio_changes={"score": (0.0, 1.0)},
        row_count=(3, 3),
    )
    assert report.null_ratio_changes["score"] == (0.0, 1.0)


# ---------------------------------------------------------------------------
# Public export parity
# ---------------------------------------------------------------------------


def test_detect_drift_shared_column_semantics_align_with_compare_profiles():
    """detect_drift and compare_profiles must agree on dtype/null_ratio changes
    for shared columns — verifies detect_drift routes through the same
    _compare_column_profiles helper rather than a separate engine."""
    old = _frame({"id": [1, 2, 3], "score": [1.0, None, 3.0]})
    new = _frame({"id": [4, 5, 6], "score": [4.0, 5.0, None]})

    drift = ar.detect_drift(old, new)

    old_profile = ar.profile(old)
    new_profile = ar.profile(new)
    comparison = ar.compare_profiles(old_profile, new_profile)

    # Every dtype change detect_drift reports must also appear in compare_profiles
    for col in drift.dtype_changes:
        assert "dtype" in comparison.drift_report[col]["changes"], (
            f"col '{col}': detect_drift reported dtype change "
            "but compare_profiles did not"
        )

    # Every null_ratio change detect_drift reports must also appear in compare_profiles
    for col in drift.null_ratio_changes:
        assert "null_ratio" in comparison.drift_report[col]["changes"], (
            f"col '{col}': detect_drift reported null_ratio change "
            "but compare_profiles did not"
        )

    # Symmetry: compare_profiles dtype/null_ratio changes must appear in detect_drift too
    for col, col_entry in comparison.drift_report.items():
        if "dtype" in col_entry["changes"]:
            assert col in drift.dtype_changes
        if "null_ratio" in col_entry["changes"]:
            assert col in drift.null_ratio_changes


def test_drift_report_is_exported():
    assert hasattr(ar, "DriftReport"), "ar.DriftReport missing from public API"


def test_drift_report_in_all():
    assert "DriftReport" in ar.__all__


def test_detect_drift_in_all():
    assert "detect_drift" in ar.__all__
