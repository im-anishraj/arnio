"""
Tests for ArFrame.schema_summary property.
"""

import pandas as pd
import pytest

import arnio as ar
from arnio.frame import ColumnSummary

# ---------------------------------------------------------------------------
# ColumnSummary dataclass
# ---------------------------------------------------------------------------


class TestColumnSummary:
    def test_column_summary_invalid_name(self):
        with pytest.raises(TypeError, match="name must be a str"):
            ColumnSummary(name=1, dtype="int64", nullable=False)

    def test_column_summary_invalid_dtype(self):
        with pytest.raises(TypeError, match="dtype must be a str"):
            ColumnSummary(name="id", dtype=2, nullable=False)

    def test_column_summary_invalid_nullable(self):
        with pytest.raises(TypeError, match="nullable must be a bool"):
            ColumnSummary(name="id", dtype="int64", nullable="yes")

    def test_column_summary_valid(self):
        entry = ColumnSummary("id", "int64", True)
        assert entry.name == "id"
        assert entry.dtype == "int64"
        assert entry.nullable is True

    def test_attributes(self):
        entry = ColumnSummary(name="age", dtype="int64", nullable=False)
        assert entry.name == "age"
        assert entry.dtype == "int64"
        assert entry.nullable is False

    def test_repr(self):
        entry = ColumnSummary(name="score", dtype="float64", nullable=True)
        r = repr(entry)
        assert "score" in r
        assert "float64" in r
        assert "True" in r

    def test_equality(self):
        a = ColumnSummary("x", "int64", False)
        b = ColumnSummary("x", "int64", False)
        assert a == b

    def test_inequality_name(self):
        assert ColumnSummary("x", "int64", False) != ColumnSummary("y", "int64", False)

    def test_inequality_dtype(self):
        assert ColumnSummary("x", "int64", False) != ColumnSummary(
            "x", "float64", False
        )

    def test_inequality_nullable(self):
        assert ColumnSummary("x", "int64", False) != ColumnSummary("x", "int64", True)

    def test_not_equal_to_non_column_summary(self):
        entry = ColumnSummary("x", "int64", False)
        assert entry.__eq__("x") is NotImplemented


# ---------------------------------------------------------------------------
# Normal behaviour
# ---------------------------------------------------------------------------


class TestSchemaSummaryNormal:
    def test_returns_list(self):
        df = pd.DataFrame({"a": [1, 2], "b": ["x", "y"]})
        frame = ar.from_pandas(df)
        result = frame.schema_summary
        assert isinstance(result, list)

    def test_length_matches_column_count(self):
        df = pd.DataFrame({"a": [1], "b": [2.0], "c": ["z"]})
        frame = ar.from_pandas(df)
        assert len(frame.schema_summary) == 3

    def test_each_entry_is_column_summary(self):
        df = pd.DataFrame({"a": [1]})
        frame = ar.from_pandas(df)
        for entry in frame.schema_summary:
            assert isinstance(entry, ColumnSummary)

    def test_column_order_preserved(self):
        df = pd.DataFrame({"z": [1], "a": [2], "m": [3]})
        frame = ar.from_pandas(df)
        names = [e.name for e in frame.schema_summary]
        assert names == ["z", "a", "m"]

    def test_names_match_frame_columns(self):
        df = pd.DataFrame({"id": [1, 2], "email": ["a@b.com", "c@d.com"]})
        frame = ar.from_pandas(df)
        assert [e.name for e in frame.schema_summary] == frame.columns

    def test_dtypes_match_frame_dtypes(self):
        df = pd.DataFrame({"id": [1, 2], "score": [1.5, 2.5], "label": ["a", "b"]})
        frame = ar.from_pandas(df)
        summary_dtypes = {e.name: e.dtype for e in frame.schema_summary}
        assert summary_dtypes == frame.dtypes

    def test_non_nullable_column(self):
        df = pd.DataFrame({"age": [10, 20, 30]})
        frame = ar.from_pandas(df)
        entry = frame.schema_summary[0]
        assert entry.nullable is False

    def test_nullable_column_from_null_values(self):
        df = pd.DataFrame({"score": [1.0, None, 3.0]})
        frame = ar.from_pandas(df)
        entry = frame.schema_summary[0]
        assert entry.nullable is True

    def test_nullable_string_column(self):
        df = pd.DataFrame({"name": ["Alice", None, "Charlie"]})
        frame = ar.from_pandas(df)
        entry = frame.schema_summary[0]
        assert entry.nullable is True

    def test_mixed_nullable_and_non_nullable(self):
        df = pd.DataFrame(
            {
                "id": [1, 2, 3],
                "name": ["a", None, "c"],
                "score": [1.0, 2.0, None],
            }
        )
        frame = ar.from_pandas(df)
        summary = {e.name: e.nullable for e in frame.schema_summary}
        assert summary["id"] is False
        assert summary["name"] is True
        assert summary["score"] is True

    def test_all_dtypes_covered(self):
        df = pd.DataFrame(
            {
                "i": [1, 2],
                "f": [1.1, 2.2],
                "s": ["a", "b"],
                "b": [True, False],
            }
        )
        frame = ar.from_pandas(df)
        dtype_map = {e.name: e.dtype for e in frame.schema_summary}
        assert dtype_map["i"] == "int64"
        assert dtype_map["f"] == "float64"
        assert dtype_map["s"] == "string"
        assert dtype_map["b"] == "bool"

    def test_csv_based_frame(self, sample_csv):
        frame = ar.read_csv(sample_csv)
        result = frame.schema_summary
        assert len(result) == len(frame.columns)
        for entry in result:
            assert entry.name in frame.columns
            assert entry.dtype in ("int64", "float64", "string", "bool", "null")

    def test_csv_with_nulls_marks_nullable(self, csv_with_nulls):
        frame = ar.read_csv(csv_with_nulls)
        assert any(e.nullable for e in frame.schema_summary)

    def test_does_not_trigger_pandas_roundtrip(self, monkeypatch):
        """schema_summary must read directly from the C++ frame."""
        df = pd.DataFrame({"x": [1, 2], "y": [3, 4]})
        frame = ar.from_pandas(df)

        from arnio import convert

        def fail_to_pandas(_frame, **_kwargs):
            raise AssertionError("schema_summary must not call to_pandas()")

        monkeypatch.setattr(convert, "to_pandas", fail_to_pandas)

        result = frame.schema_summary
        assert len(result) == 2

    def test_stable_across_calls(self):
        df = pd.DataFrame({"a": [1, None], "b": ["x", "y"]})
        frame = ar.from_pandas(df)
        assert frame.schema_summary == frame.schema_summary

    def test_schema_summary_returns_valid_column_summaries(self):
        df = pd.DataFrame({"id": [1, 2], "name": ["a", None]})
        frame = ar.from_pandas(df)
        for entry in frame.schema_summary:
            assert isinstance(entry.name, str)
            assert isinstance(entry.dtype, str)
            assert isinstance(entry.nullable, bool)


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestSchemaSummaryEdgeCases:
    def test_single_column_frame(self):
        df = pd.DataFrame({"only": [42]})
        frame = ar.from_pandas(df)
        result = frame.schema_summary
        assert len(result) == 1
        assert result[0].name == "only"
        assert result[0].dtype == "int64"
        assert result[0].nullable is False

    def test_empty_frame_no_rows(self):
        df = pd.DataFrame(columns=["name", "age"])
        frame = ar.from_pandas(df)
        result = frame.schema_summary
        assert [e.name for e in result] == ["name", "age"]
        for entry in result:
            assert entry.nullable is False

    def test_single_row_no_nulls(self):
        df = pd.DataFrame({"x": [1], "y": ["hello"]})
        frame = ar.from_pandas(df)
        assert all(not e.nullable for e in frame.schema_summary)

    def test_all_values_null_marks_nullable(self):
        df = pd.DataFrame({"x": [None, None, None]})
        frame = ar.from_pandas(df)
        assert frame.schema_summary[0].nullable is True

    def test_only_last_row_null(self):
        df = pd.DataFrame({"v": [1, 2, None]})
        frame = ar.from_pandas(df)
        assert frame.schema_summary[0].nullable is True

    def test_only_first_row_null(self):
        df = pd.DataFrame({"v": [None, 2, 3]})
        frame = ar.from_pandas(df)
        assert frame.schema_summary[0].nullable is True

    def test_wide_frame(self):
        cols = {f"col_{i}": list(range(5)) for i in range(50)}
        df = pd.DataFrame(cols)
        frame = ar.from_pandas(df)
        result = frame.schema_summary
        assert len(result) == 50
        assert [e.name for e in result] == list(cols.keys())

    def test_publicly_accessible_from_arnio_namespace(self):
        from arnio import ColumnSummary as CS  # noqa: F401

        df = pd.DataFrame({"a": [1]})
        frame = ar.from_pandas(df)
        for entry in frame.schema_summary:
            assert isinstance(entry, CS)

    def test_schema_to_dict_empty_dataframe(self):
        df = pd.DataFrame()
        frame = ar.from_pandas(df)
        res = ar.schema_export.schema_to_dict(frame)
        assert res == {"fields": {}}

    def test_schema_to_yaml_empty_dataframe(self):
        df = pd.DataFrame()
        frame = ar.from_pandas(df)
        res = ar.schema_export.schema_to_yaml(frame)
        assert res == "fields: {}\n"

    def test_schema_to_dict_with_column_summary_list(self):
        df = pd.DataFrame({"age": [20]})
        frame = ar.from_pandas(df)
        res = ar.schema_export.schema_to_dict(frame.schema_summary)
        assert res == {"fields": {"age": {"type": "INT64", "nullable": False}}}
