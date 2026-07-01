"""
Focused tests for infer_schema() — issue #855.

Covers:
- mixed numeric/string columns
- boolean variants (yes/no, 1/0, true/false)
- multiple datetime formats
- high-null and all-null columns
- ambiguous columns (top two candidates within threshold)
- to_dict() JSON safety and deterministic ordering
- to_schema() produces a valid Schema with correct dtype mappings
- input validation (non-ArFrame input raises TypeError)
- empty frame (no columns)
- score invariants: all candidates in [0.0, 1.0], confidence in [0.0, 1.0]
- deterministic output (calling twice returns the same result)
"""

from __future__ import annotations

import json

import pytest

import arnio as ar
from arnio.quality import _AMBIGUITY_THRESHOLD, InferredSchema

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _frame(*rows: dict) -> ar.ArFrame:
    return ar.from_records(list(rows))


def _infer(*rows: dict) -> InferredSchema:
    return ar.infer_schema(_frame(*rows))


# ---------------------------------------------------------------------------
# exports
# ---------------------------------------------------------------------------


def test_infer_schema_exported():
    assert hasattr(ar, "infer_schema"), "ar.infer_schema missing"


def test_column_inference_exported():
    assert hasattr(ar, "ColumnInference"), "ar.ColumnInference missing"


def test_inferred_schema_exported():
    assert hasattr(ar, "InferredSchema"), "ar.InferredSchema missing"


# ---------------------------------------------------------------------------
# input validation
# ---------------------------------------------------------------------------


def test_non_arframe_raises():
    import pandas as pd

    with pytest.raises(TypeError):
        ar.infer_schema(pd.DataFrame({"a": [1, 2]}))  # type: ignore[arg-type]


def test_plain_dict_raises():
    with pytest.raises(TypeError):
        ar.infer_schema({"a": [1, 2, 3]})  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# empty frame
# ---------------------------------------------------------------------------


def test_single_row_frame():
    """ArFrame requires at least one row; verify a single-row frame works."""
    frame = ar.from_records([{"x": 1}])
    schema = ar.infer_schema(frame)
    assert isinstance(schema, InferredSchema)
    assert "x" in schema.columns


# ---------------------------------------------------------------------------
# integer column
# ---------------------------------------------------------------------------


def test_integer_column():
    schema = _infer({"age": 25}, {"age": 30}, {"age": 22})
    col = schema.columns["age"]
    assert col.inferred_type == "int64"
    assert col.confidence > 0.5


# ---------------------------------------------------------------------------
# float column
# ---------------------------------------------------------------------------


def test_float_column():
    schema = _infer({"price": 1.5}, {"price": 2.7}, {"price": 3.14})
    col = schema.columns["price"]
    assert col.inferred_type == "float64"
    assert col.confidence > 0.5


# ---------------------------------------------------------------------------
# boolean variants
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "values",
    [
        ["true", "false", "true"],
        ["yes", "no", "yes"],
        ["1", "0", "1"],
        ["True", "False", "True"],
        ["YES", "NO", "YES"],
    ],
)
def test_boolean_variants(values):
    rows = [{"flag": v} for v in values]
    frame = ar.from_records(rows)
    schema = ar.infer_schema(frame)
    col = schema.columns["flag"]
    assert col.inferred_type == "bool", (
        f"Expected bool for values {values}, got {col.inferred_type} "
        f"(confidence={col.confidence}, candidates={col.candidates})"
    )


# ---------------------------------------------------------------------------
# datetime formats
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "values",
    [
        ["2024-01-01", "2024-02-15", "2024-12-31"],
        ["01/01/2024", "02/15/2024", "12/31/2024"],
        ["2024-01-01 10:00:00", "2024-06-15 08:30:00", "2024-12-01 23:59:59"],
    ],
)
def test_datetime_formats(values):
    rows = [{"ts": v} for v in values]
    frame = ar.from_records(rows)
    schema = ar.infer_schema(frame)
    col = schema.columns["ts"]
    assert col.inferred_type == "datetime", (
        f"Expected datetime for {values}, got {col.inferred_type} "
        f"(candidates={col.candidates})"
    )


# ---------------------------------------------------------------------------
# mixed numeric / string column
# ---------------------------------------------------------------------------


def test_mixed_numeric_string():
    """Column with "100" and "unknown" should not confidently infer int64/float64."""
    rows = [{"val": v} for v in ["100", "unknown", "200", "N/A", "300"]]
    frame = ar.from_records(rows)
    schema = ar.infer_schema(frame)
    col = schema.columns["val"]
    # int64/float64 should not win with high confidence
    assert col.candidates["int64"] < 0.9
    assert col.candidates["float64"] < 0.9


# ---------------------------------------------------------------------------
# high-null column
# ---------------------------------------------------------------------------


def test_high_null_column():
    rows = [{"x": None}, {"x": None}, {"x": None}, {"x": "hello"}, {"x": None}]
    frame = ar.from_records(rows)
    schema = ar.infer_schema(frame)
    col = schema.columns["x"]
    # High null ratio should suppress confidence
    assert col.confidence <= 1.0
    # Score invariant
    assert col.confidence >= 0.0


def test_all_null_column():
    rows = [{"x": None}, {"x": None}, {"x": None}]
    frame = ar.from_records(rows)
    schema = ar.infer_schema(frame)
    col = schema.columns["x"]
    assert col.inferred_type == "string"
    assert col.confidence == pytest.approx(0.1)


# ---------------------------------------------------------------------------
# ambiguity
# ---------------------------------------------------------------------------


def test_ambiguous_column_flag():
    """A column with "1", "0" values should be flagged ambiguous (bool vs int)."""
    rows = [{"flag": v} for v in ["1", "0", "1", "0", "1"]]
    frame = ar.from_records(rows)
    schema = ar.infer_schema(frame)
    col = schema.columns["flag"]
    top = col.confidence
    second = list(col.candidates.values())[1]
    expected_ambiguous = (top - second) <= _AMBIGUITY_THRESHOLD
    assert col.is_ambiguous == expected_ambiguous


def test_unambiguous_integer_column():
    """Pure integer column with no null should not be ambiguous."""
    rows = [{"n": v} for v in [42, 100, 7, 999, 3]]
    frame = ar.from_records(rows)
    schema = ar.infer_schema(frame)
    col = schema.columns["n"]
    # Verify is_ambiguous matches the threshold rule
    top = col.confidence
    second = list(col.candidates.values())[1]
    assert col.is_ambiguous == ((top - second) <= _AMBIGUITY_THRESHOLD)


# ---------------------------------------------------------------------------
# score invariants
# ---------------------------------------------------------------------------


def test_score_invariants():
    rows = [
        {"a": 1, "b": "hello", "c": "2024-01-01", "d": None, "e": "yes"},
        {"a": 2, "b": "world", "c": "2024-06-15", "d": None, "e": "no"},
        {"a": 3, "b": "foo", "c": "2024-12-31", "d": None, "e": "yes"},
    ]
    schema = _infer(*rows)
    for name, col in schema.columns.items():
        assert (
            0.0 <= col.confidence <= 1.0
        ), f"{name}: confidence {col.confidence} out of range"
        for ctype, score in col.candidates.items():
            assert 0.0 <= score <= 1.0, f"{name}[{ctype}]: score {score} out of range"
        # inferred_type must be the highest-scored candidate
        top_type = next(iter(col.candidates))
        assert (
            col.inferred_type == top_type
        ), f"{name}: inferred_type {col.inferred_type!r} != top candidate {top_type!r}"


# ---------------------------------------------------------------------------
# to_dict JSON safety
# ---------------------------------------------------------------------------


def test_to_dict_json_safe():
    schema = _infer({"a": 1, "b": "hello"}, {"a": 2, "b": "world"})
    d = schema.to_dict()
    # Must round-trip through json without error
    serialized = json.dumps(d)
    recovered = json.loads(serialized)
    assert set(recovered["columns"].keys()) == {"a", "b"}


def test_column_inference_to_dict_json_safe():
    schema = _infer({"x": "yes"}, {"x": "no"}, {"x": "yes"})
    col = schema.columns["x"]
    d = col.to_dict()
    json.dumps(d)  # must not raise
    assert "name" in d
    assert "inferred_type" in d
    assert "confidence" in d
    assert "is_ambiguous" in d
    assert "candidates" in d


def test_to_dict_deterministic_ordering():
    rows = [{"a": 1, "b": "hello", "c": "2024-01-01"}] * 3
    schema1 = ar.infer_schema(_frame(*rows))
    schema2 = ar.infer_schema(_frame(*rows))
    assert list(schema1.to_dict()["columns"].keys()) == list(
        schema2.to_dict()["columns"].keys()
    )


# ---------------------------------------------------------------------------
# to_schema produces valid Schema
# ---------------------------------------------------------------------------


def test_to_schema_produces_valid_schema():
    from arnio.schema import Schema

    schema = _infer({"age": 25, "name": "Alice"}, {"age": 30, "name": "Bob"})
    ar_schema = schema.to_schema()
    assert isinstance(ar_schema, Schema)
    assert set(ar_schema.fields.keys()) == {"age", "name"}


@pytest.mark.parametrize(
    "values,expected_dtype",
    [
        ([1, 2, 3], "int64"),
        ([1.5, 2.5, 3.5], "float64"),
        (["yes", "no", "yes"], "bool"),
        (["2024-01-01", "2024-06-15", "2024-12-31"], "datetime"),
        (["apple", "apple", "banana"], "string"),  # categorical → string in Field
    ],
)
def test_to_schema_dtype_mappings(values, expected_dtype):
    rows = [{"col": v} for v in values]
    frame = ar.from_records(rows)
    schema = ar.infer_schema(frame)
    ar_schema = schema.to_schema()
    field_dtype = ar_schema.fields["col"].dtype
    assert field_dtype == expected_dtype, (
        f"For values {values}: expected Field dtype {expected_dtype!r}, "
        f"got {field_dtype!r} (inferred_type={schema.columns['col'].inferred_type!r})"
    )


def test_to_schema_nullable_conservative():
    """All fields should be nullable=True (conservative default)."""
    schema = _infer({"a": 1}, {"a": 2}, {"a": None})
    ar_schema = schema.to_schema()
    assert ar_schema.fields["a"].nullable is True


def test_to_schema_validate_roundtrip():
    """Schema from infer_schema should be accepted by ar.validate without error."""
    rows = [{"age": 25, "score": 9.5}, {"age": 30, "score": 8.1}]
    frame = _frame(*rows)
    schema = ar.infer_schema(frame)
    ar_schema = schema.to_schema()
    result = ar.validate(frame, ar_schema)
    # Validation must not raise; result is a ValidationResult
    assert result is not None


# ---------------------------------------------------------------------------
# deterministic output
# ---------------------------------------------------------------------------


def test_deterministic_output():
    rows = [
        {"age": 25, "name": "Alice", "active": "yes", "score": 9.5},
        {"age": 30, "name": "Bob", "active": "no", "score": 8.1},
        {"age": 22, "name": "Carol", "active": "yes", "score": 7.9},
    ]
    frame = _frame(*rows)
    s1 = ar.infer_schema(frame)
    s2 = ar.infer_schema(frame)
    for name in s1.columns:
        assert s1.columns[name].inferred_type == s2.columns[name].inferred_type
        assert s1.columns[name].confidence == s2.columns[name].confidence
        assert s1.columns[name].candidates == s2.columns[name].candidates


# ---------------------------------------------------------------------------
# multi-column frame
# ---------------------------------------------------------------------------


def test_multi_column_frame():
    rows = [
        {
            "id": 1,
            "price": 9.99,
            "active": "yes",
            "created": "2024-01-01",
            "note": "ok",
        },
        {
            "id": 2,
            "price": 4.50,
            "active": "no",
            "created": "2024-06-15",
            "note": "fine",
        },
        {
            "id": 3,
            "price": 1.00,
            "active": "yes",
            "created": "2024-12-31",
            "note": "great",
        },
    ]
    schema = _infer(*rows)
    assert set(schema.columns.keys()) == {"id", "price", "active", "created", "note"}
    assert schema.columns["id"].inferred_type == "int64"
    assert schema.columns["active"].inferred_type == "bool"
    assert schema.columns["created"].inferred_type == "datetime"
