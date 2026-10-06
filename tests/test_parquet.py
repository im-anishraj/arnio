"""Tests for write_parquet functionality.

Tests that require pyarrow are marked with @skip_without_pyarrow and are
skipped when pyarrow is not installed.  The TestWriteParquetErrors class
has no skip marker so the ImportError contract test and path/compression
validation tests always run regardless of whether pyarrow is present.
"""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest

import arnio as ar
from arnio import ArFrame

try:
    import pyarrow  # noqa: F401

    HAS_PYARROW = True
except ImportError:
    HAS_PYARROW = False

skip_without_pyarrow = pytest.mark.skipif(
    not HAS_PYARROW, reason="pyarrow not installed — install arnio[parquet]"
)


@skip_without_pyarrow
class TestWriteParquetBasic:
    def test_basic_write_creates_file(self, tmp_path):
        frame = ar.from_pandas(pd.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "z"]}))
        out = tmp_path / "out.parquet"
        ar.write_parquet(frame, out)
        assert out.exists()

    def test_pq_extension_accepted(self, tmp_path):
        frame = ar.from_pandas(pd.DataFrame({"x": [1, 2]}))
        out = tmp_path / "out.pq"
        ar.write_parquet(frame, out)
        assert out.exists()

    def test_pathlike_input(self, tmp_path):
        frame = ar.from_pandas(pd.DataFrame({"v": [42]}))
        ar.write_parquet(frame, Path(tmp_path / "out.parquet"))
        assert (tmp_path / "out.parquet").exists()

    def test_string_path_input(self, tmp_path):
        frame = ar.from_pandas(pd.DataFrame({"v": [42]}))
        ar.write_parquet(frame, str(tmp_path / "out.parquet"))
        assert (tmp_path / "out.parquet").exists()

    def test_returns_none(self, tmp_path):
        frame = ar.from_pandas(pd.DataFrame({"a": [1]}))
        result = ar.write_parquet(frame, tmp_path / "out.parquet")
        assert result is None


@skip_without_pyarrow
class TestWriteParquetRoundTrip:
    def test_integer_column_round_trips(self, tmp_path):
        frame = ar.from_pandas(pd.DataFrame({"n": [1, 2, 3]}))
        out = tmp_path / "out.parquet"
        ar.write_parquet(frame, out)
        df = pd.read_parquet(out, engine="pyarrow")
        assert df["n"].tolist() == [1, 2, 3]

    def test_float_column_round_trips(self, tmp_path):
        frame = ar.from_pandas(pd.DataFrame({"f": [1.1, 2.2, 3.3]}))
        out = tmp_path / "out.parquet"
        ar.write_parquet(frame, out)
        df = pd.read_parquet(out, engine="pyarrow")
        assert [round(v, 1) for v in df["f"].tolist()] == [1.1, 2.2, 3.3]

    def test_string_column_round_trips(self, tmp_path):
        frame = ar.from_pandas(pd.DataFrame({"s": ["alice", "bob"]}))
        out = tmp_path / "out.parquet"
        ar.write_parquet(frame, out)
        df = pd.read_parquet(out, engine="pyarrow")
        assert df["s"].tolist() == ["alice", "bob"]

    def test_bool_column_round_trips(self, tmp_path):
        frame = ar.from_pandas(pd.DataFrame({"b": [True, False, True]}))
        out = tmp_path / "out.parquet"
        ar.write_parquet(frame, out)
        df = pd.read_parquet(out, engine="pyarrow")
        assert df["b"].tolist() == [True, False, True]

    def test_null_values_round_trip(self, tmp_path):
        frame = ar.from_pandas(pd.DataFrame({"a": [1, None, 3], "b": ["x", None, "z"]}))
        out = tmp_path / "out.parquet"
        ar.write_parquet(frame, out)
        df = pd.read_parquet(out, engine="pyarrow")
        assert pd.isna(df["a"].iloc[1])
        assert pd.isna(df["b"].iloc[1])

    def test_mixed_dtypes_round_trip(self, tmp_path):
        frame = ar.from_pandas(
            pd.DataFrame(
                {
                    "i": [1, 2, 3],
                    "f": [1.0, 2.0, 3.0],
                    "s": ["a", "b", "c"],
                    "b": [True, False, True],
                }
            )
        )
        out = tmp_path / "out.parquet"
        ar.write_parquet(frame, out)
        df = pd.read_parquet(out, engine="pyarrow")
        assert list(df.columns) == ["i", "f", "s", "b"]
        assert df.shape == (3, 4)

    def test_result_consistent_with_to_pandas(self, tmp_path):
        original_df = pd.DataFrame({"x": [10, 20, 30], "y": ["a", "b", "c"]})
        frame = ar.from_pandas(original_df)
        out = tmp_path / "out.parquet"
        ar.write_parquet(frame, out)
        roundtrip_df = pd.read_parquet(out, engine="pyarrow")
        arnio_df = ar.to_pandas(frame)
        assert roundtrip_df["x"].tolist() == arnio_df["x"].tolist()
        assert roundtrip_df["y"].tolist() == arnio_df["y"].tolist()


@skip_without_pyarrow
class TestWriteParquetCompression:
    @pytest.mark.parametrize("codec", ["snappy", "gzip", "brotli", "zstd", "none"])
    def test_compression_codecs_accepted(self, tmp_path, codec):
        frame = ar.from_pandas(pd.DataFrame({"v": [1, 2, 3]}))
        out = tmp_path / f"out_{codec}.parquet"
        ar.write_parquet(frame, out, compression=codec)
        assert out.exists()
        df = pd.read_parquet(out, engine="pyarrow")
        assert df["v"].tolist() == [1, 2, 3]

    def test_default_compression_is_snappy(self, tmp_path):
        frame = ar.from_pandas(pd.DataFrame({"v": [1]}))
        out = tmp_path / "out.parquet"
        ar.write_parquet(frame, out)
        df = pd.read_parquet(out, engine="pyarrow")
        assert df["v"].tolist() == [1]

    def test_unknown_compression_raises(self, tmp_path):
        frame = ar.from_pandas(pd.DataFrame({"v": [1]}))
        with pytest.raises(ValueError, match="Unknown compression codec"):
            ar.write_parquet(frame, tmp_path / "out.parquet", compression="lz4")


@skip_without_pyarrow
class TestWriteParquetZeroColumn:
    def test_zero_by_zero_frame_round_trips_empty(self, tmp_path):
        frame = ar.from_pandas(pd.DataFrame())
        assert frame.shape == (0, 0)

        out = tmp_path / "empty.parquet"

        ar.write_parquet(frame, out)
        df = pd.read_parquet(out, engine="pyarrow")

        assert df.shape == (0, 0)
        assert out.exists()

    def test_zero_column_with_row_raises(self, tmp_path):
        frame = ar.from_pandas(pd.DataFrame(index=range(3)))
        assert frame.shape == (3, 0)

        out = tmp_path / "zero_cols.parquet"
        with pytest.raises(
            ValueError,
            match="Cannot write a zero-column ArFrame with 3 rows to Parquet: the current export path cannot preserve row count without columns.",
        ):
            ar.write_parquet(frame, out)

        assert not out.exists()

    def test_normal_frame_still_round_trips(self, tmp_path):
        frame = ar.from_pandas(pd.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "z"]}))
        assert frame.shape == (3, 2)

        out = tmp_path / "normal.parquet"
        ar.write_parquet(frame, out)
        df = pd.read_parquet(out, engine="pyarrow")
        assert df.shape == (3, 2)
        assert df["a"].tolist() == [1, 2, 3]
        assert df["b"].tolist() == ["x", "y", "z"]
        assert out.exists()


@skip_without_pyarrow
class TestWriteParquetRowGroupSize:
    def test_row_group_size_accepted(self, tmp_path):
        frame = ar.from_pandas(pd.DataFrame({"v": list(range(100))}))
        out = tmp_path / "out.parquet"
        ar.write_parquet(frame, out, row_group_size=25)
        df = pd.read_parquet(out, engine="pyarrow")
        assert len(df) == 100

    def test_row_group_size_none_uses_default(self, tmp_path):
        frame = ar.from_pandas(pd.DataFrame({"v": [1, 2, 3]}))
        out = tmp_path / "out.parquet"
        ar.write_parquet(frame, out, row_group_size=None)
        assert out.exists()

    def test_row_group_size_zero_raises(self, tmp_path):
        frame = ar.from_pandas(pd.DataFrame({"v": [1]}))
        with pytest.raises(ValueError, match="positive integer"):
            ar.write_parquet(frame, tmp_path / "out.parquet", row_group_size=0)

    def test_row_group_size_negative_raises(self, tmp_path):
        frame = ar.from_pandas(pd.DataFrame({"v": [1]}))
        with pytest.raises(ValueError, match="positive integer"):
            ar.write_parquet(frame, tmp_path / "out.parquet", row_group_size=-1)

    def test_row_group_size_non_integer_raises(self, tmp_path):
        frame = ar.from_pandas(pd.DataFrame({"v": [1]}))
        with pytest.raises(TypeError, match="integer"):
            ar.write_parquet(frame, tmp_path / "out.parquet", row_group_size=1.5)


class TestWriteParquetErrors:
    """Error-path tests that run regardless of whether pyarrow is installed."""

    def test_unsupported_extension_raises(self, tmp_path):
        frame = ar.from_pandas(pd.DataFrame({"a": [1]}))
        with pytest.raises(ValueError, match="Unsupported file format"):
            ar.write_parquet(frame, tmp_path / "out.csv")

    def test_json_extension_raises(self, tmp_path):
        frame = ar.from_pandas(pd.DataFrame({"a": [1]}))
        with pytest.raises(ValueError, match="Unsupported file format"):
            ar.write_parquet(frame, tmp_path / "out.json")

    def test_unknown_compression_raises_without_pyarrow(self, tmp_path):
        # Validation happens before the pyarrow import check.
        frame = ar.from_pandas(pd.DataFrame({"a": [1]}))
        with pytest.raises(ValueError, match="Unknown compression codec"):
            ar.write_parquet(frame, tmp_path / "out.parquet", compression="lz4")

    @pytest.mark.parametrize("compression", [None, 123, True, ["snappy"]])
    def test_non_string_compression_raises_type_error(self, tmp_path, compression):
        # Compression type validation happens before codec validation and pyarrow import.
        frame = ar.from_pandas(pd.DataFrame({"a": [1]}))

        with pytest.raises(TypeError, match="compression must be a string"):
            ar.write_parquet(
                frame,
                tmp_path / "out.parquet",
                compression=compression,
            )

    @pytest.mark.parametrize(
        "preserve_attrs",
        ["False", 0, 1, None, [], {}, object()],
    )
    def test_non_bool_preserve_attrs_raises_type_error(self, tmp_path, preserve_attrs):
        # preserve_attrs validation happens before the pyarrow import check.
        frame = ar.from_pandas(pd.DataFrame({"a": [1]}))

        with pytest.raises(TypeError, match="preserve_attrs must be a bool"):
            ar.write_parquet(
                frame,
                tmp_path / "out.parquet",
                preserve_attrs=preserve_attrs,
            )

    def test_missing_pyarrow_raises_import_error(self, tmp_path):
        # This test mocks pyarrow away and must run even without pyarrow.
        frame = ar.from_pandas(pd.DataFrame({"a": [1]}))
        with patch.dict("sys.modules", {"pyarrow": None}):
            with pytest.raises(ImportError, match="pip install arnio\\[parquet\\]"):
                ar.write_parquet(frame, tmp_path / "out.parquet")

    @pytest.mark.parametrize(
        "bad_input",
        [
            object(),
            None,
            pd.DataFrame({"a": [1, 2]}),
        ],
    )
    def test_write_parquet_invalid_frame(self, tmp_path, bad_input):
        with pytest.raises(TypeError, match="frame must be an ArFrame"):
            ar.write_parquet(bad_input, tmp_path / "out.parquet")


@skip_without_pyarrow
def test_write_parquet_json_safe_attrs(tmp_path):
    src = pd.DataFrame({"a": [1]})
    src.attrs = {"tag": "v1", "count": 42, "flag": True, "meta": {"x": [1, 2]}}
    ar.write_parquet(ar.from_pandas(src), tmp_path / "out.parquet")


@skip_without_pyarrow
def test_write_parquet_unsupported_attrs_raises(tmp_path):
    src = pd.DataFrame({"a": [1]})
    src.attrs = {"bad": object()}
    with pytest.raises(TypeError, match="JSON-serializable"):
        ar.write_parquet(ar.from_pandas(src), tmp_path / "out.parquet")


@skip_without_pyarrow
def test_write_parquet_preserve_attrs_false_drops_metadata(tmp_path):
    src = pd.DataFrame({"a": [1]})
    src.attrs = {"bad": object()}
    out = tmp_path / "out.parquet"
    ar.write_parquet(ar.from_pandas(src), out, preserve_attrs=False)
    assert pd.read_parquet(out).attrs == {}


@skip_without_pyarrow
def test_write_parquet_empty_attrs_skips_validation(tmp_path):
    src = pd.DataFrame({"a": [1]})
    ar.write_parquet(ar.from_pandas(src), tmp_path / "out.parquet")


def test_write_parquet_rejects_bool_path(tmp_path):
    frame = ar.from_pandas(pd.DataFrame({"a": [1, 2, 3]}))
    with pytest.raises(TypeError, match="path must be a string"):
        ar.write_parquet(frame, True)


def test_write_parquet_rejects_int_path(tmp_path):
    frame = ar.from_pandas(pd.DataFrame({"a": [1, 2, 3]}))
    with pytest.raises(TypeError, match="path must be a string"):
        ar.write_parquet(frame, 42)


class _BytesPathLike:
    def __init__(self, path: bytes) -> None:
        self._path = path

    def __fspath__(self) -> bytes:
        return self._path


@skip_without_pyarrow
def test_write_parquet_accepts_bytes_path(tmp_path):
    frame = ar.from_pandas(pd.DataFrame({"a": [1, 2, 3]}))
    out = tmp_path / "out.parquet"
    ar.write_parquet(frame, os.fsencode(out))
    assert out.exists()


@skip_without_pyarrow
def test_write_parquet_accepts_pathlike_bytes_path(tmp_path):
    frame = ar.from_pandas(pd.DataFrame({"a": [1, 2, 3]}))
    out = tmp_path / "out.parquet"
    ar.write_parquet(frame, _BytesPathLike(os.fsencode(out)))
    assert out.exists()


# ---------------------------------------------------------------------------
# read_parquet tests
# ---------------------------------------------------------------------------


@skip_without_pyarrow
class TestReadParquetBasic:
    def test_returns_arframe(self, tmp_path):
        frame = ar.from_pandas(pd.DataFrame({"a": [1, 2], "b": ["x", "y"]}))
        out = tmp_path / "test.parquet"
        ar.write_parquet(frame, str(out))
        result = ar.read_parquet(str(out))
        assert isinstance(result, ArFrame)

    def test_correct_shape(self, tmp_path):
        frame = ar.from_pandas(pd.DataFrame({"a": [1, 2, 3], "b": [4.0, 5.0, 6.0]}))
        out = tmp_path / "test.parquet"
        ar.write_parquet(frame, str(out))
        result = ar.read_parquet(str(out))
        assert result.shape == (3, 2)

    def test_column_names_preserved(self, tmp_path):
        frame = ar.from_pandas(pd.DataFrame({"name": ["Alice"], "age": [30]}))
        out = tmp_path / "test.parquet"
        ar.write_parquet(frame, str(out))
        result = ar.read_parquet(str(out))
        assert result.columns == ["name", "age"]

    def test_pq_extension_accepted(self, tmp_path):
        frame = ar.from_pandas(pd.DataFrame({"x": [1, 2]}))
        out = tmp_path / "test.pq"
        ar.write_parquet(frame, str(out))
        result = ar.read_parquet(str(out))
        assert result.shape == (2, 1)


@skip_without_pyarrow
class TestReadParquetDtypes:
    def test_int64_round_trip(self, tmp_path):
        frame = ar.from_pandas(pd.DataFrame({"n": [1, 2, 3]}))
        out = tmp_path / "ints.parquet"
        ar.write_parquet(frame, str(out))
        result = ar.read_parquet(str(out))
        assert result.dtypes["n"] == "int64"

    def test_float64_round_trip(self, tmp_path):
        frame = ar.from_pandas(pd.DataFrame({"f": [1.1, 2.2, 3.3]}))
        out = tmp_path / "floats.parquet"
        ar.write_parquet(frame, str(out))
        result = ar.read_parquet(str(out))
        assert result.dtypes["f"] == "float64"

    def test_bool_round_trip(self, tmp_path):
        frame = ar.from_pandas(pd.DataFrame({"b": [True, False, True]}))
        out = tmp_path / "bools.parquet"
        ar.write_parquet(frame, str(out))
        result = ar.read_parquet(str(out))
        assert result.dtypes["b"] == "bool"

    def test_string_round_trip(self, tmp_path):
        frame = ar.from_pandas(pd.DataFrame({"s": ["a", "b", "c"]}))
        out = tmp_path / "strings.parquet"
        ar.write_parquet(frame, str(out))
        result = ar.read_parquet(str(out))
        assert result.dtypes["s"] == "string"


@skip_without_pyarrow
class TestReadParquetNulls:
    def test_nulls_preserved(self, tmp_path):
        df = pd.DataFrame({"x": pd.array([1, None, 3], dtype="Int64")})
        frame = ar.from_pandas(df)
        out = tmp_path / "nulls.parquet"
        ar.write_parquet(frame, str(out))
        result = ar.read_parquet(str(out))
        result_df = ar.to_pandas(result)
        assert result_df["x"].isna().sum() == 1


@skip_without_pyarrow
class TestReadParquetColumns:
    def test_columns_subset(self, tmp_path):
        frame = ar.from_pandas(pd.DataFrame({"a": [1], "b": [2], "c": [3]}))
        out = tmp_path / "multi.parquet"
        ar.write_parquet(frame, str(out))
        result = ar.read_parquet(str(out), columns=["a", "c"])
        assert result.columns == ["a", "c"]

    def test_usecols_subset(self, tmp_path):
        frame = ar.from_pandas(pd.DataFrame({"a": [1], "b": [2], "c": [3]}))
        out = tmp_path / "multi.parquet"
        ar.write_parquet(frame, str(out))
        result = ar.read_parquet(str(out), usecols=["b"])
        assert result.columns == ["b"]

    def test_columns_and_usecols_conflict_raises(self, tmp_path):
        frame = ar.from_pandas(pd.DataFrame({"a": [1], "b": [2]}))
        out = tmp_path / "conflict.parquet"
        ar.write_parquet(frame, str(out))
        with pytest.raises(ValueError, match="Cannot specify both"):
            ar.read_parquet(str(out), columns=["a"], usecols=["b"])

    def test_empty_columns_raises(self, tmp_path):
        frame = ar.from_pandas(pd.DataFrame({"a": [1]}))
        out = tmp_path / "empty.parquet"
        ar.write_parquet(frame, str(out))
        with pytest.raises(ValueError, match="must not be empty"):
            ar.read_parquet(str(out), columns=[])

    def test_bare_string_columns_raises(self, tmp_path):
        frame = ar.from_pandas(pd.DataFrame({"a": [1], "b": [2]}))
        out = tmp_path / "str_columns.parquet"
        ar.write_parquet(frame, str(out))
        with pytest.raises(TypeError, match="bare string"):
            ar.read_parquet(str(out), columns="a")

    def test_bare_string_usecols_raises(self, tmp_path):
        frame = ar.from_pandas(pd.DataFrame({"a": [1], "b": [2]}))
        out = tmp_path / "str_usecols.parquet"
        ar.write_parquet(frame, str(out))
        with pytest.raises(TypeError, match="bare string"):
            ar.read_parquet(str(out), usecols="a")


class TestReadParquetErrors:
    def test_bad_extension_raises(self, tmp_path):
        f = tmp_path / "data.csv"
        f.write_text("a,b\n1,2\n")
        with pytest.raises(ValueError, match=".parquet"):
            ar.read_parquet(str(f))

    def test_file_not_found_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            ar.read_parquet(str(tmp_path / "missing.parquet"))

    def test_wrong_path_type_raises(self):
        with pytest.raises(TypeError, match="path must be"):
            ar.read_parquet(123)

    def test_missing_pyarrow_raises_import_error(self, tmp_path, monkeypatch):
        import sys

        # File must exist so the FileNotFoundError check passes and only
        # the missing-dependency ImportError is raised.
        fake = tmp_path / "x.parquet"
        fake.write_bytes(b"PAR1")  # minimal stub — just needs to exist

        monkeypatch.setitem(sys.modules, "pyarrow", None)
        monkeypatch.setitem(sys.modules, "pyarrow.parquet", None)
        with pytest.raises(ImportError, match="arnio\\[parquet\\]"):
            ar.read_parquet(str(fake))

    @skip_without_pyarrow
    def test_corrupted_file_raises(self, tmp_path):
        bad = tmp_path / "bad.parquet"
        bad.write_bytes(b"not a parquet file at all")
        with pytest.raises(Exception):
            ar.read_parquet(str(bad))


@skip_without_pyarrow
class TestReadParquetWriteRoundTrip:
    def test_full_round_trip(self, tmp_path):
        df = pd.DataFrame(
            {
                "id": pd.array([1, 2, 3], dtype="Int64"),
                "score": [1.5, 2.5, 3.5],
                "flag": [True, False, True],
                "label": ["a", "b", "c"],
            }
        )
        frame = ar.from_pandas(df)
        out = tmp_path / "roundtrip.parquet"
        ar.write_parquet(frame, str(out))
        result = ar.read_parquet(str(out))
        result_df = ar.to_pandas(result)
        assert list(result_df.columns) == ["id", "score", "flag", "label"]
        assert result_df["score"].tolist() == [1.5, 2.5, 3.5]
        assert result_df["label"].tolist() == ["a", "b", "c"]
