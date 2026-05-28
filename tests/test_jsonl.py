"""Tests for read_jsonl functionality."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

import arnio as ar


def _write(tmp_path: Path, name: str, lines: list) -> Path:
    """Write a list of objects/strings as a .jsonl file."""
    p = tmp_path / name
    p.write_text(
        "\n".join(json.dumps(obj) if not isinstance(obj, str) else obj for obj in lines)
        + "\n",
        encoding="utf-8",
    )
    return p


class TestReadJsonlBasic:
    def test_simple_round_trip(self, tmp_path):
        path = _write(
            tmp_path,
            "data.jsonl",
            [{"name": "Alice", "age": 30}, {"name": "Bob", "age": 25}],
        )
        frame = ar.read_jsonl(path)
        df = ar.to_pandas(frame)

        assert list(df.columns) == ["name", "age"]
        assert df["name"].tolist() == ["Alice", "Bob"]
        assert df["age"].tolist() == [30, 25]

    def test_returns_arframe(self, tmp_path):
        path = _write(tmp_path, "data.jsonl", [{"x": 1}])
        assert isinstance(ar.read_jsonl(path), ar.ArFrame)

    def test_ndjson_extension_accepted(self, tmp_path):
        path = tmp_path / "data.ndjson"
        path.write_text('{"a": 1}\n', encoding="utf-8")
        frame = ar.read_jsonl(path)
        assert frame.shape == (1, 1)

    def test_pathlike_input(self, tmp_path):
        path = _write(tmp_path, "data.jsonl", [{"v": 42}])
        frame = ar.read_jsonl(Path(path))
        assert ar.to_pandas(frame)["v"].tolist() == [42]

    def test_string_path_input(self, tmp_path):
        path = _write(tmp_path, "data.jsonl", [{"v": 42}])
        frame = ar.read_jsonl(str(path))
        assert ar.to_pandas(frame)["v"].tolist() == [42]


class TestReadJsonlNullsAndTypes:
    def test_null_values_preserved(self, tmp_path):
        path = _write(
            tmp_path,
            "data.jsonl",
            [{"a": 1, "b": None}, {"a": 2, "b": "hello"}],
        )
        frame = ar.read_jsonl(path)
        df = ar.to_pandas(frame)

        assert pd.isna(df["b"].iloc[0])
        assert df["b"].iloc[1] == "hello"

    def test_missing_key_becomes_null(self, tmp_path):
        # Row 2 is missing key "b" — should become null
        path = _write(
            tmp_path,
            "data.jsonl",
            [{"a": 1, "b": "x"}, {"a": 2}],
        )
        frame = ar.read_jsonl(path)
        df = ar.to_pandas(frame)

        assert df.shape == (2, 2)
        assert pd.isna(df["b"].iloc[1])

    def test_mixed_type_column_coerced_to_string(self, tmp_path):
        # int and string in same column → coerced to string by from_pandas
        path = _write(
            tmp_path,
            "data.jsonl",
            [{"v": 1}, {"v": "two"}],
        )
        frame = ar.read_jsonl(path)
        assert frame.dtypes["v"] == "string"

    def test_integer_column_inferred(self, tmp_path):
        path = _write(tmp_path, "data.jsonl", [{"n": 10}, {"n": 20}])
        frame = ar.read_jsonl(path)
        assert frame.dtypes["n"] == "int64"

    def test_float_column_inferred(self, tmp_path):
        path = _write(tmp_path, "data.jsonl", [{"f": 1.5}, {"f": 2.5}])
        frame = ar.read_jsonl(path)
        assert frame.dtypes["f"] == "float64"

    def test_bool_column_inferred(self, tmp_path):
        path = _write(tmp_path, "data.jsonl", [{"b": True}, {"b": False}])
        frame = ar.read_jsonl(path)
        assert frame.dtypes["b"] == "bool"

    def test_all_null_column(self, tmp_path):
        path = _write(
            tmp_path,
            "data.jsonl",
            [{"a": 1, "b": None}, {"a": 2, "b": None}],
        )
        frame = ar.read_jsonl(path)
        assert ar.to_pandas(frame)["b"].isna().all()


class TestReadJsonlNrows:
    def test_nrows_limits_rows(self, tmp_path):
        path = _write(
            tmp_path,
            "data.jsonl",
            [{"i": i} for i in range(10)],
        )
        frame = ar.read_jsonl(path, nrows=3)
        assert frame.shape[0] == 3

    def test_nrows_stops_before_malformed_record_beyond_limit(self, tmp_path):
        path = tmp_path / "limited.jsonl"
        path.write_text('{"a": 1}\n{"a": 2}\nnot json\n', encoding="utf-8")

        frame = ar.read_jsonl(path, nrows=2)

        assert frame.shape == (2, 1)

    def test_nrows_zero_returns_empty_frame(self, tmp_path):
        path = _write(tmp_path, "data.jsonl", [{"x": 1}, {"x": 2}])
        # nrows=0 is valid — reads 0 rows, returns empty frame
        frame = ar.read_jsonl(path, nrows=0)
        assert frame.shape[0] == 0

    def test_nrows_zero_does_not_inspect_file_contents(self, tmp_path):
        # nrows=0 must short-circuit before opening the file, so malformed
        # content must never raise even when the first line is invalid JSON.
        path = tmp_path / "bad.jsonl"
        path.write_text("not valid json at all\n{also bad}\n", encoding="utf-8")
        frame = ar.read_jsonl(path, nrows=0)
        assert frame.shape[0] == 0

    def test_nrows_zero_skips_extension_validation(self, tmp_path):
        # nrows=0 short-circuits before extension validation — an unsupported
        # extension must not raise when the caller requests zero rows.
        path = tmp_path / "probe.txt"
        path.write_text("not json\n", encoding="utf-8")
        frame = ar.read_jsonl(path, nrows=0)
        assert frame.shape[0] == 0

    def test_nrows_larger_than_file_reads_all(self, tmp_path):
        path = _write(tmp_path, "data.jsonl", [{"x": i} for i in range(5)])
        frame = ar.read_jsonl(path, nrows=100)
        assert frame.shape[0] == 5

    def test_nrows_negative_raises(self, tmp_path):
        path = _write(tmp_path, "data.jsonl", [{"x": 1}])
        with pytest.raises(ValueError, match="nrows must be non-negative"):
            ar.read_jsonl(path, nrows=-1)

    def test_nrows_non_integer_raises(self, tmp_path):
        path = _write(tmp_path, "data.jsonl", [{"x": 1}])
        with pytest.raises(TypeError, match="nrows must be an integer"):
            ar.read_jsonl(path, nrows=1.5)


class TestReadJsonlBlankLines:
    def test_blank_lines_skipped(self, tmp_path):
        path = tmp_path / "data.jsonl"
        path.write_text('{"a": 1}\n\n{"a": 2}\n\n{"a": 3}\n', encoding="utf-8")
        frame = ar.read_jsonl(path)
        assert frame.shape[0] == 3

    def test_whitespace_only_lines_skipped(self, tmp_path):
        path = tmp_path / "data.jsonl"
        path.write_text('{"a": 1}\n   \n{"a": 2}\n', encoding="utf-8")
        frame = ar.read_jsonl(path)
        assert frame.shape[0] == 2


class TestReadJsonlErrors:
    def test_unsupported_extension_raises(self, tmp_path):
        path = tmp_path / "data.json"
        path.write_text('{"a": 1}\n', encoding="utf-8")
        with pytest.raises(ValueError, match="Unsupported file format"):
            ar.read_jsonl(path)

    def test_csv_extension_raises(self, tmp_path):
        path = tmp_path / "data.csv"
        path.write_text("a,b\n1,2\n", encoding="utf-8")
        with pytest.raises(ValueError, match="Unsupported file format"):
            ar.read_jsonl(path)

    def test_empty_file_raises(self, tmp_path):
        path = tmp_path / "empty.jsonl"
        path.write_text("", encoding="utf-8")
        with pytest.raises(ar.JsonlReadError, match="empty"):
            ar.read_jsonl(path)

    def test_blank_lines_only_raises(self, tmp_path):
        path = tmp_path / "blank.jsonl"
        path.write_text("\n\n\n", encoding="utf-8")
        with pytest.raises(ar.JsonlReadError, match="empty"):
            ar.read_jsonl(path)

    def test_malformed_json_raises_with_line_number(self, tmp_path):
        path = tmp_path / "bad.jsonl"
        path.write_text('{"a": 1}\n{bad json}\n{"a": 3}\n', encoding="utf-8")
        with pytest.raises(ar.JsonlReadError, match="line 2"):
            ar.read_jsonl(path)

    def test_malformed_first_line_raises(self, tmp_path):
        path = tmp_path / "bad.jsonl"
        path.write_text("not json\n", encoding="utf-8")
        with pytest.raises(ar.JsonlReadError, match="line 1"):
            ar.read_jsonl(path)

    def test_non_object_line_raises(self, tmp_path):
        # A JSON array is not a valid JSONL record
        path = tmp_path / "bad.jsonl"
        path.write_text("[1, 2, 3]\n", encoding="utf-8")
        with pytest.raises(ar.JsonlReadError, match="JSON object"):
            ar.read_jsonl(path)

    def test_jsonl_read_error_is_arnio_error(self, tmp_path):
        path = tmp_path / "empty.jsonl"
        path.write_text("", encoding="utf-8")
        with pytest.raises(ar.ArnioError):
            ar.read_jsonl(path)


class TestReadJsonlEncoding:
    def test_utf8_default(self, tmp_path):
        path = tmp_path / "data.jsonl"
        path.write_text('{"city": "São Paulo"}\n', encoding="utf-8")
        frame = ar.read_jsonl(path)
        df = ar.to_pandas(frame)
        assert df["city"].iloc[0] == "São Paulo"

    def test_latin1_encoding(self, tmp_path):
        path = tmp_path / "data.jsonl"
        path.write_bytes('{"city": "M\xfcnchen"}\n'.encode("latin-1"))
        frame = ar.read_jsonl(path, encoding="latin-1")
        df = ar.to_pandas(frame)
        assert df["city"].iloc[0] == "München"

    def test_wrong_encoding_raises(self, tmp_path):
        path = tmp_path / "data.jsonl"
        path.write_bytes('{"city": "M\xfcnchen"}\n'.encode("latin-1"))
        with pytest.raises(ar.JsonlReadError, match="decode"):
            ar.read_jsonl(path, encoding="utf-8")


class TestReadJsonlPipelineCompat:
    def test_result_is_pipeline_compatible(self, tmp_path):
        path = _write(
            tmp_path,
            "data.jsonl",
            [{"name": " Alice ", "score": 95}, {"name": " Bob ", "score": 80}],
        )
        frame = ar.read_jsonl(path)
        result = ar.pipeline(frame, [("strip_whitespace",)])
        df = ar.to_pandas(result)

        assert df["name"].tolist() == ["Alice", "Bob"]

    def test_result_works_with_profile(self, tmp_path):
        path = _write(
            tmp_path,
            "data.jsonl",
            [{"a": 1, "b": "x"}, {"a": 1, "b": "x"}, {"a": 2, "b": "y"}],
        )
        frame = ar.read_jsonl(path)
        report = ar.profile(frame)

        assert report.row_count == 3
        assert report.duplicate_rows == 1


def test_read_jsonl_encoding_non_string(tmp_path):
    f = tmp_path / "x.jsonl"
    f.write_text('{"a": 1}\n')
    with pytest.raises(TypeError, match="encoding must be a string"):
        ar.read_jsonl(f, encoding=123)


def test_read_jsonl_encoding_none(tmp_path):
    f = tmp_path / "x.jsonl"
    f.write_text('{"a": 1}\n')
    with pytest.raises(TypeError, match="encoding must be a string"):
        ar.read_jsonl(f, encoding=None)


def test_read_jsonl_encoding_unknown_codec(tmp_path):
    f = tmp_path / "x.jsonl"
    f.write_text('{"a": 1}\n')
    with pytest.raises(ValueError, match="Unknown encoding"):
        ar.read_jsonl(f, encoding="fake-codec")
