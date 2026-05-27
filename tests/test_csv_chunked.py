"""Tests for chunked CSV reading."""

import pandas as pd
import pytest

import arnio as ar
from arnio.exceptions import CsvReadError


def _chunked_rows(path: str, **kwargs) -> list[ar.ArFrame]:
    return list(ar.read_csv_chunked(path, **kwargs))


def _chunked_concat(path: str, chunksize: int = 2, **kwargs) -> pd.DataFrame:
    chunks = _chunked_rows(path, chunksize=chunksize, **kwargs)
    if not chunks:
        return pd.DataFrame()
    return pd.concat([ar.to_pandas(c) for c in chunks], ignore_index=True)


class TestReadCsvChunked:
    def test_multi_chunk_row_counts(self, tmp_path):
        lines = ["id,value,label"]
        for i in range(250):
            lines.append(f"{i},{i * 1.5},item_{i}")
        path = tmp_path / "chunked.csv"
        path.write_text("\n".join(lines))

        chunks = _chunked_rows(str(path), chunksize=100)
        assert len(chunks) == 3
        assert [c.shape[0] for c in chunks] == [100, 100, 50]

    def test_stable_dtypes_across_chunks(self, tmp_path):
        lines = ["name,age,score"]
        for i in range(150):
            lines.append(f"user_{i},{20 + i % 10},{90.5 + i}")
        path = tmp_path / "dtypes.csv"
        path.write_text("\n".join(lines))

        chunks = _chunked_rows(str(path), chunksize=50)
        first_dtypes = chunks[0].dtypes
        for chunk in chunks[1:]:
            assert chunk.dtypes == first_dtypes

    def test_concat_matches_read_csv(self, large_csv):
        chunks = _chunked_rows(large_csv, chunksize=200)
        chunked_df = pd.concat([ar.to_pandas(c) for c in chunks], ignore_index=True)
        full_df = ar.to_pandas(ar.read_csv(large_csv))
        pd.testing.assert_frame_equal(chunked_df, full_df)

    def test_concat_matches_read_csv_sample(self, sample_csv):
        chunks = _chunked_rows(sample_csv, chunksize=2)
        chunked_df = pd.concat([ar.to_pandas(c) for c in chunks], ignore_index=True)
        full_df = ar.to_pandas(ar.read_csv(sample_csv))
        pd.testing.assert_frame_equal(chunked_df, full_df)

    def test_nrows_limits_total_rows(self, large_csv):
        chunks = _chunked_rows(large_csv, chunksize=200, nrows=350)
        total = sum(c.shape[0] for c in chunks)
        assert total == 350
        full_df = ar.to_pandas(ar.read_csv(large_csv, nrows=350))
        chunked_df = pd.concat([ar.to_pandas(c) for c in chunks], ignore_index=True)
        pd.testing.assert_frame_equal(chunked_df, full_df)

    def test_skip_rows(self, tmp_path):
        lines = ["id,value"]
        for i in range(20):
            lines.append(f"{i},{i}")
        path = tmp_path / "skip.csv"
        path.write_text("\n".join(lines))

        chunks = _chunked_rows(str(path), chunksize=5, skip_rows=10)
        chunked_df = pd.concat([ar.to_pandas(c) for c in chunks], ignore_index=True)
        assert chunked_df.shape[0] == 10
        assert chunked_df["id"].tolist() == list(range(10, 20))

    def test_quoted_multiline_field(self, tmp_path):
        path = tmp_path / "multiline.csv"
        path.write_bytes(
            b"id,text\n"
            b'1,"line one\nline two"\n'
            b"2,simple\n"
            b'3,"another\nquoted"\n'
            b"4,plain\n"
        )
        chunks = _chunked_rows(str(path), chunksize=2)
        chunked_df = pd.concat([ar.to_pandas(c) for c in chunks], ignore_index=True)
        full_df = ar.to_pandas(ar.read_csv(str(path)))
        pd.testing.assert_frame_equal(chunked_df, full_df)

    def test_usecols(self, sample_csv):
        chunks = _chunked_rows(sample_csv, chunksize=2, usecols=["name", "age"])
        assert all(c.columns == ["name", "age"] for c in chunks)
        chunked_df = pd.concat([ar.to_pandas(c) for c in chunks], ignore_index=True)
        full_df = ar.to_pandas(ar.read_csv(sample_csv, usecols=["name", "age"]))
        pd.testing.assert_frame_equal(chunked_df, full_df)

    def test_invalid_chunksize(self, sample_csv):
        with pytest.raises(ValueError, match="chunksize must be a positive integer"):
            list(ar.read_csv_chunked(sample_csv, chunksize=0))

    def test_empty_data_rows_header_only(self, tmp_path):
        path = tmp_path / "header_only.csv"
        path.write_text("a,b\n")
        chunks = _chunked_rows(str(path), chunksize=10)
        assert chunks == []

    def test_warn_mode_skips_empty_chunks_from_bad_rows(self, tmp_path):
        path = tmp_path / "bad_warn.csv"

        path.write_text("a,b\n" "1,2,3\n" "4,5\n" "6,7,8\n")

        chunks = list(
            ar.read_csv_chunked(
                str(path),
                chunksize=1,
                on_bad_lines="warn",
            )
        )

        assert [chunk.shape for chunk in chunks] == [(1, 2)]

    def test_skip_mode_skips_empty_chunks_from_bad_rows(self, tmp_path):
        path = tmp_path / "bad_skip.csv"

        path.write_text("a,b\n" "1,2,3\n" "4,5\n" "6,7,8\n")

        chunks = list(
            ar.read_csv_chunked(
                str(path),
                chunksize=1,
                on_bad_lines="skip",
            )
        )

        assert [chunk.shape for chunk in chunks] == [(1, 2)]


class TestReadCsvChunkedParity:
    """Chunked reads must match read_csv for parser options."""

    def test_parity_has_header_false(self, csv_no_header):
        chunked_df = _chunked_concat(csv_no_header, chunksize=1, has_header=False)
        full_df = ar.to_pandas(ar.read_csv(csv_no_header, has_header=False))
        pd.testing.assert_frame_equal(chunked_df, full_df)

    def test_parity_null_values(self, tmp_path):
        path = tmp_path / "nulls.csv"
        path.write_text("a\n1\nNA\n3\n")
        chunked_df = _chunked_concat(str(path), chunksize=1, null_values=["NA"])
        full_df = ar.to_pandas(ar.read_csv(str(path), null_values=["NA"]))
        pd.testing.assert_frame_equal(chunked_df, full_df)

    def test_parity_thousands_separator(self, tmp_path):
        path = tmp_path / "thousands.csv"
        path.write_text('amount\n"1,234"\n500\n')
        chunked_df = _chunked_concat(str(path), chunksize=1, thousands_separator=",")
        full_df = ar.to_pandas(ar.read_csv(str(path), thousands_separator=","))
        pd.testing.assert_frame_equal(chunked_df, full_df)

    def test_parity_permissive_mode(self, tmp_path):
        path = tmp_path / "permissive.csv"
        path.write_text("id,name\n1,Alice\n2\n")
        chunked_df = _chunked_concat(str(path), chunksize=1, mode="permissive")
        full_df = ar.to_pandas(ar.read_csv(str(path), mode="permissive"))
        pd.testing.assert_frame_equal(chunked_df, full_df)

    def test_parity_strict_mode_raises(self, tmp_path):
        path = tmp_path / "strict.csv"
        path.write_text("id,name\n1,Alice\n2\n")
        with pytest.raises(CsvReadError, match="expected 2"):
            _chunked_concat(str(path), chunksize=1, mode="strict")
        with pytest.raises(CsvReadError, match="expected 2"):
            ar.read_csv(str(path), mode="strict")


class TestReadCsvChunkedParamParity:
    """Issue #1256 — encoding_errors, dtype, skiprows/skip_rows parity with read_csv."""

    def test_encoding_errors_replace(self, tmp_path):
        """encoding_errors='replace' substitutes bad bytes instead of crashing."""
        path = tmp_path / "bad_encoding.csv"
        # Write a CSV with a valid header and one row containing an invalid UTF-8 byte
        path.write_bytes(b"name,score\nAlice\xff,90\nBob,85\n")
        chunks = list(ar.read_csv_chunked(str(path), encoding_errors="replace"))
        df = pd.concat([ar.to_pandas(c) for c in chunks], ignore_index=True)
        assert df.shape[0] == 2
        # The replacement character should appear somewhere in the bad row's value
        assert "\ufffd" in df["name"].iloc[0]

    def test_encoding_errors_ignore(self, tmp_path):
        """encoding_errors='ignore' drops bad bytes silently."""
        path = tmp_path / "bad_encoding.csv"
        path.write_bytes(b"name,score\nAli\xffce,90\nBob,85\n")
        chunks = list(ar.read_csv_chunked(str(path), encoding_errors="ignore"))
        df = pd.concat([ar.to_pandas(c) for c in chunks], ignore_index=True)
        assert df.shape[0] == 2
        assert "\ufffd" not in df["name"].iloc[0]

    def test_encoding_errors_strict_raises(self, tmp_path):
        """encoding_errors='strict' (default) raises on bad bytes."""
        path = tmp_path / "bad_encoding.csv"
        path.write_bytes(b"name,score\nAlice\xff,90\n")
        with pytest.raises(Exception):
            list(ar.read_csv_chunked(str(path), encoding_errors="strict"))

    def test_dtype_overrides_inference(self, tmp_path):
        """dtype param forces a column to the requested type in every chunk."""
        lines = ["id,age,score"]
        for i in range(30):
            lines.append(f"{i},{20 + i},9{i % 10}.5")
        path = tmp_path / "dtype_test.csv"
        path.write_text("\n".join(lines))

        chunks = list(
            ar.read_csv_chunked(str(path), chunksize=10, dtype={"age": "string"})
        )
        for chunk in chunks:
            df = ar.to_pandas(chunk)
            # age should be string in every chunk, not int64
            assert str(df["age"].dtype).lower().startswith("string") or str(df["age"].dtype) == "object"

    def test_dtype_applied_consistently_across_chunks(self, tmp_path):
        """dtype is applied the same way in every chunk, not just the first."""
        lines = ["code,value"]
        for i in range(50):
            lines.append(f"C{i:03d},{i}")
        path = tmp_path / "dtype_chunks.csv"
        path.write_text("\n".join(lines))

        chunks = list(
            ar.read_csv_chunked(str(path), chunksize=15, dtype={"value": "string"})
        )
        assert len(chunks) > 1
        dtypes_per_chunk = [ar.to_pandas(c)["value"].dtype for c in chunks]
        assert len(set(str(d) for d in dtypes_per_chunk)) == 1

    def test_skiprows_new_name(self, tmp_path):
        """skiprows (new name) skips the requested number of rows."""
        lines = ["id,value"]
        for i in range(20):
            lines.append(f"{i},{i}")
        path = tmp_path / "skiprows.csv"
        path.write_text("\n".join(lines))

        # Chunk 3 should raise on row 5 (value 5.5)
        with pytest.raises(Exception, match="Type mismatch"):
            next(reader)


class TestCsvChunkedIssue1583:
    """Regression tests for Issue #1583: Respect explicit dtype configuration in CsvChunkReader."""

    def test_explicit_dtype_respected_across_chunks(self, tmp_path):
        """Test that explicit dtypes are correctly locked and respected across all chunks."""
        path = tmp_path / "explicit_dtypes.csv"
        path.write_text("a,b\n1,10.5\n2,20.5\n3,30.5\n4,40.5\n")

        # Configure column 'a' as float64 (even though values look like int64)
        # and column 'b' as string (even though values look like float64)
        chunks = list(
            ar.read_csv_chunked(
                str(path), chunksize=2, dtype={"a": "float64", "b": "string"}
            )
        )
        assert len(chunks) == 2
        for chunk in chunks:
            assert chunk.dtypes == {"a": "float64", "b": "string"}

        df = pd.concat([ar.to_pandas(c) for c in chunks], ignore_index=True)
        assert df["a"].tolist() == [1.0, 2.0, 3.0, 4.0]
        assert df["b"].tolist() == ["10.5", "20.5", "30.5", "40.5"]

    def test_mixed_inferred_and_configured_columns(self, tmp_path):
        """Test that mixed unconfigured (inferred) and configured columns behave correctly."""
        path = tmp_path / "mixed.csv"
        path.write_text("a,b,c\n1,foo,99.9\n2,bar,88.8\n3,baz,77.7\n")

        # Configure only 'a' as float64 and 'b' as string; 'c' is inferred as float64
        chunks = list(
            ar.read_csv_chunked(
                str(path), chunksize=2, dtype={"a": "float64", "b": "string"}
            )
        )
        assert len(chunks) == 2
        for chunk in chunks:
            assert chunk.dtypes == {"a": "float64", "b": "string", "c": "float64"}

    def test_unconfigured_mismatch_still_fails(self, tmp_path):
        """Ensure unconfigured columns still correctly fail-fast on type mismatch."""
        path = tmp_path / "unconfigured_mismatch.csv"
        path.write_text(
            "a,b\n1,10\n2,20\n3,abc\n"
        )  # Column 'b' has integer, integer, then string

        # 'a' is explicitly configured as float64, but 'b' is left unconfigured to be inferred
        reader = ar.read_csv_chunked(str(path), chunksize=2, dtype={"a": "float64"})

        chunk1 = next(reader)
        assert chunk1 is not None
        assert chunk1.dtypes == {"a": "float64", "b": "int64"}

        # Chunk 2 has 'abc' in column 'b' which was inferred/locked as int64, so it must raise!
        with pytest.raises(Exception, match="Type mismatch"):
            next(reader)

    def test_configured_string_column_survives_heterogeneous_values(self, tmp_path):
        """Test that configuring a column as 'string' allows any values without mismatch errors."""
        path = tmp_path / "heterogeneous.csv"
        path.write_text("a,b\n1,100\n2,abc\n3,99.9\n")

        # Column 'b' has int, string, float. If configured as string, it should succeed
        chunks = list(
            ar.read_csv_chunked(str(path), chunksize=1, dtype={"b": "string"})
        )
        assert len(chunks) == 3
        df = pd.concat([ar.to_pandas(c) for c in chunks], ignore_index=True)
        assert df["b"].tolist() == ["100", "abc", "99.9"]

    def test_existing_chunked_inference_remains_unchanged(self, tmp_path):
        """Ensure chunked reading without dtype preserves original inference and success behavior."""
        path = tmp_path / "inference.csv"
        path.write_text("a,b\n1,10.5\n2,20.5\n")

        chunks = list(ar.read_csv_chunked(str(path), chunksize=1))
        assert len(chunks) == 2
        for chunk in chunks:
            assert chunk.dtypes == {"a": "int64", "b": "float64"}

    def test_null_type_initialization_compatibility(self, tmp_path):
        """Ensure all-null columns configured as non-string preserve specified type."""
        path = tmp_path / "nulls.csv"
        path.write_text("a,b\n1,\n2,200\n3,300\n")

        # Column 'b' starts with null in the first chunk, but is explicitly configured as int64
        chunks = list(ar.read_csv_chunked(str(path), chunksize=1, dtype={"b": "int64"}))
        assert len(chunks) == 3
        for chunk in chunks:
            assert chunk.dtypes == {"a": "int64", "b": "int64"}

        df = pd.concat([ar.to_pandas(c) for c in chunks], ignore_index=True)
        assert pd.isna(df.loc[0, "b"])
        assert df.loc[1, "b"] == 200
        assert df.loc[2, "b"] == 300

    def test_chunk_boundary_edge_cases(self, tmp_path):
        """Test configured column dtype mismatch validation at chunk boundaries."""
        path = tmp_path / "boundary.csv"
        path.write_text(
            "a,b\n1,10\n2,abc\n"
        )  # 'b' configured as int64, fails on chunk 2

        reader = ar.read_csv_chunked(str(path), chunksize=1, dtype={"b": "int64"})

        chunk1 = next(reader)
        assert chunk1 is not None
        assert chunk1.dtypes == {"a": "int64", "b": "int64"}

        # Chunk 2 has 'abc' in column 'b' which is configured/locked as int64, so it must raise!
        with pytest.raises(Exception, match="Type mismatch"):
            next(reader)

    def test_headerless_csv_explicit_dtype(self, tmp_path):
        """Verify that synthetic columns in headerless CSVs respect explicit dtypes."""
        path = tmp_path / "headerless.csv"
        path.write_text("1,10.5\n2,20.5\n3,30.5\n")

        chunks = list(
            ar.read_csv_chunked(
                str(path),
                chunksize=2,
                has_header=False,
                dtype={"col_0": "float64", "col_1": "string"},
            )
        )
        assert len(chunks) == 2
        for chunk in chunks:
            assert chunk.dtypes == {"col_0": "float64", "col_1": "string"}

        df = pd.concat([ar.to_pandas(c) for c in chunks], ignore_index=True)
        assert df["col_0"].tolist() == [1.0, 2.0, 3.0]
        assert df["col_1"].tolist() == ["10.5", "20.5", "30.5"]

    def test_dtype_specified_for_non_selected_column(self, tmp_path):
        """Verify that specifying a dtype for a column excluded by usecols raises an exception."""
        path = tmp_path / "usecols_mismatch.csv"
        path.write_text("a,b\n1,10\n2,20\n")

        # Column 'b' is excluded by usecols, but is present in dtype mapping. This should raise CsvReadError.
        with pytest.raises(
            CsvReadError, match="dtype specified for non-selected column: b"
        ):
            list(
                ar.read_csv_chunked(
                    str(path), chunksize=2, usecols=["a"], dtype={"b": "int64"}
                )
            )

    def test_missing_dtype_column_raises_error(self, tmp_path):
        """Verify that specifying a dtype for a non-existent column name raises an error."""
        path = tmp_path / "missing_col.csv"
        path.write_text("a,b\n1,10\n")

        # Column 'c' does not exist in the CSV header. This should raise CsvReadError.
        with pytest.raises(CsvReadError, match="Column not found in dtype mapping: c"):
            list(ar.read_csv_chunked(str(path), chunksize=2, dtype={"c": "int64"}))
