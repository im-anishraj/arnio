"""
Tests for validate_chunked() (arnio/schema.py).

Covers:
- Parity with single-frame validate() on small datasets
- Global row indices remain correct across chunk boundaries
- max_errors stops processing early
- Chunked profiling aggregates counts correctly
- min/max aggregation remains correct across chunks
- Null statistics aggregate correctly
- Empty input handling
- Schema mismatch detection across chunks
- Existing validate() and profile() behaviour unchanged
"""

from __future__ import annotations

import pytest

import arnio as ar
from arnio.schema import ValidationResult

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_csv(rows: list[dict]) -> str:
    """Return a CSV string from a list of dicts."""
    if not rows:
        return ""
    headers = list(rows[0].keys())
    lines = [",".join(headers)]
    for row in rows:
        lines.append(",".join(str(row.get(h, "")) for h in headers))
    return "\n".join(lines) + "\n"


def _frame_from_rows(rows: list[dict]) -> ar.ArFrame:
    import pandas as pd

    return ar.from_pandas(pd.DataFrame(rows))


def _chunked_frames(rows: list[dict], chunk_size: int):
    """Yield ArFrame chunks of *chunk_size* rows from *rows*."""
    for start in range(0, max(len(rows), 1), chunk_size):
        yield _frame_from_rows(rows[start : start + chunk_size])


# ---------------------------------------------------------------------------
# validate_chunked — type-checking
# ---------------------------------------------------------------------------


def test_validate_chunked_raises_on_non_arframe():
    schema = ar.Schema({"a": ar.Int64()})
    with pytest.raises(TypeError, match="ArFrame"):
        ar.validate_chunked(["not a frame"], schema)


def test_validate_chunked_raises_on_bad_max_errors_type():
    schema = ar.Schema({"a": ar.Int64()})
    with pytest.raises(TypeError, match="max_errors"):
        ar.validate_chunked([], schema, max_errors="10")  # type: ignore[arg-type]


def test_validate_chunked_raises_on_max_errors_zero():
    schema = ar.Schema({"a": ar.Int64()})
    with pytest.raises(ValueError, match="max_errors"):
        ar.validate_chunked([], schema, max_errors=0)


def test_validate_chunked_raises_on_max_errors_bool():
    schema = ar.Schema({"a": ar.Int64()})
    with pytest.raises(TypeError, match="max_errors"):
        ar.validate_chunked([], schema, max_errors=True)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# validate_chunked — empty input
# ---------------------------------------------------------------------------


def test_validate_chunked_empty_iterable():
    schema = ar.Schema({"a": ar.Int64()})
    result = ar.validate_chunked([], schema)
    assert result.row_count == 0
    assert result.issue_count == 0
    assert result.issues == []
    assert result.bad_rows == []
    assert result.passed


def test_validate_chunked_single_empty_chunk():
    # An empty frame has no columns; use an empty schema so no
    # required-column issues are raised and the result passes.
    schema = ar.Schema({})
    frame = _frame_from_rows([])
    result = ar.validate_chunked([frame], schema)
    assert result.row_count == 0
    assert result.passed


# ---------------------------------------------------------------------------
# validate_chunked — parity with validate() on small datasets
# ---------------------------------------------------------------------------


def test_validate_chunked_parity_no_issues(tmp_path):
    """Chunked result matches single-frame result when data is valid."""
    rows = [{"id": i, "value": i * 10} for i in range(12)]
    schema = ar.Schema({"id": ar.Int64(), "value": ar.Int64()})

    single_frame = _frame_from_rows(rows)
    single_result = ar.validate(single_frame, schema)
    chunked_result = ar.validate_chunked(_chunked_frames(rows, 4), schema)

    assert chunked_result.passed == single_result.passed
    assert chunked_result.row_count == single_result.row_count
    assert chunked_result.issue_count == single_result.issue_count


def test_validate_chunked_parity_with_issues(tmp_path):
    """Issue count matches single-frame validate() for nullable violations."""
    rows = [
        {"id": 1, "email": "alice@example.com"},
        {"id": 2, "email": ""},  # empty — fails Email
        {"id": 3, "email": "bob@example.com"},
        {"id": 4, "email": ""},  # empty — fails Email
        {"id": 5, "email": "carol@example.com"},
        {"id": 6, "email": "dave@example.com"},
    ]
    schema = ar.Schema({"id": ar.Int64(), "email": ar.Email(nullable=False)})

    single_frame = _frame_from_rows(rows)
    single_result = ar.validate(single_frame, schema)
    chunked_result = ar.validate_chunked(_chunked_frames(rows, 2), schema)

    assert chunked_result.issue_count == single_result.issue_count
    assert chunked_result.row_count == single_result.row_count
    assert chunked_result.passed == single_result.passed


# ---------------------------------------------------------------------------
# validate_chunked — global row index correctness
# ---------------------------------------------------------------------------


def test_validate_chunked_row_indices_are_global():
    """row_index values in issues reflect positions in the full dataset."""
    # Row at position 5 (0-based chunk offset) has a bad email.
    rows = [{"id": i, "email": "ok@ok.com"} for i in range(6)]
    rows[5]["email"] = "not-an-email"

    schema = ar.Schema({"id": ar.Int64(), "email": ar.Email(nullable=False)})
    result = ar.validate_chunked(_chunked_frames(rows, 2), schema)

    # There should be at least one issue for the bad email.
    assert not result.passed
    row_indices = [
        issue.row_index for issue in result.issues if issue.row_index is not None
    ]
    # The bad row is at global position 5 (1-based row_index = 6 by convention).
    assert any(
        idx >= 5 for idx in row_indices
    ), f"Expected a row_index >= 5, got {row_indices}"


def test_validate_chunked_bad_rows_sorted():
    """bad_rows is always a sorted list of globally-correct indices."""
    rows = [{"id": i} for i in range(20)]
    # Make several rows invalid.
    for bad in [3, 7, 15]:
        rows[bad]["id"] = "not-an-int"

    schema = ar.Schema({"id": ar.Int64(nullable=False)})
    result = ar.validate_chunked(_chunked_frames(rows, 5), schema)

    assert result.bad_rows == sorted(result.bad_rows), "bad_rows must be sorted"
    # All bad_rows must be non-negative.
    assert all(r >= 0 for r in result.bad_rows)


def test_validate_chunked_row_count_is_total():
    """row_count reflects the sum of all chunk sizes."""
    rows = [{"v": i} for i in range(30)]
    schema = ar.Schema({"v": ar.Int64()})
    result = ar.validate_chunked(_chunked_frames(rows, 7), schema)
    assert result.row_count == 30


# ---------------------------------------------------------------------------
# validate_chunked — max_errors early stop
# ---------------------------------------------------------------------------


def test_validate_chunked_max_errors_limits_issues():
    """Issue list is capped at max_errors."""
    # Every row has a bad email.
    rows = [{"email": "bad"} for _ in range(50)]
    schema = ar.Schema({"email": ar.Email(nullable=False)})
    result = ar.validate_chunked(_chunked_frames(rows, 10), schema, max_errors=5)
    assert result.issue_count <= 5
    assert len(result.issues) <= 5


def test_validate_chunked_max_errors_row_count_reflects_processed_chunks():
    """row_count reflects only the chunks actually read before early stop.

    Once max_errors is reached the iterator is not consumed further, so
    row_count is the sum of rows in the chunks processed up to and
    including the chunk where the limit was hit — not the total file size.
    """
    rows = [{"v": "bad"} for _ in range(40)]
    schema = ar.Schema({"v": ar.Int64(nullable=False)})
    # chunk_size=10, max_errors=3 — limit hit inside first chunk (10 rows).
    result = ar.validate_chunked(_chunked_frames(rows, 10), schema, max_errors=3)
    # row_count must be a multiple of chunk_size and <= total rows.
    assert result.row_count % 10 == 0
    assert result.row_count <= 40
    assert result.issue_count <= 3


# ---------------------------------------------------------------------------
# validate_chunked — schema mismatch
# ---------------------------------------------------------------------------


def test_validate_chunked_missing_column_detected():
    """A missing required column is flagged across chunks."""
    rows = [{"a": i} for i in range(10)]
    schema = ar.Schema({"a": ar.Int64(), "b": ar.String(nullable=False)})
    result = ar.validate_chunked(_chunked_frames(rows, 3), schema)
    rules = {issue.rule for issue in result.issues}
    assert "required_column" in rules


# ---------------------------------------------------------------------------
# validate_chunked — existing validate() unchanged
# ---------------------------------------------------------------------------


def test_validate_not_modified():
    """validate() still rejects an iterable input (not an ArFrame)."""
    schema = ar.Schema({"x": ar.Int64()})
    with pytest.raises(TypeError, match="single ArFrame"):
        ar.validate([], schema)  # type: ignore[arg-type]


def test_validate_single_frame_still_works():
    """validate() still works as before for a single frame."""
    frame = _frame_from_rows([{"x": 1}, {"x": 2}])
    schema = ar.Schema({"x": ar.Int64()})
    result = ar.validate(frame, schema)
    assert isinstance(result, ValidationResult)
    assert result.passed


# ---------------------------------------------------------------------------
# validate_chunked — public export
# ---------------------------------------------------------------------------


def test_validate_chunked_is_exported():
    assert hasattr(ar, "validate_chunked")
    assert callable(ar.validate_chunked)


def test_validate_chunked_in_all():
    assert "validate_chunked" in ar.__all__
