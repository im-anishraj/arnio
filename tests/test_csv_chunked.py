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

        chunks = list(ar.read_csv_chunked(str(path), chunksize=5, skiprows=10))
        df = pd.concat([ar.to_pandas(c) for c in chunks], ignore_index=True)
        assert df.shape[0] == 10
        assert df["id"].tolist() == list(range(10, 20))

    def test_skip_rows_old_name_still_works_with_deprecation_warning(self, tmp_path):
        """skip_rows still works but emits DeprecationWarning."""
        lines = ["id,value"] + [f"{i},{i}" for i in range(10)]
        path = tmp_path / "skip_rows_compat.csv"
        path.write_text("\n".join(lines))

        with pytest.warns(DeprecationWarning, match="skip_rows is deprecated"):
            chunks = list(ar.read_csv_chunked(str(path), skip_rows=5))
        df = pd.concat([ar.to_pandas(c) for c in chunks], ignore_index=True)
        assert df.shape[0] == 5

    def test_skip_rows_and_skiprows_together_raises(self, tmp_path):
        """Passing both skip_rows and skiprows is an error."""
        lines = ["id,value"] + [f"{i},{i}" for i in range(10)]
        path = tmp_path / "both.csv"
        path.write_text("\n".join(lines))

        with pytest.raises(TypeError, match="Cannot pass both"):
            list(ar.read_csv_chunked(str(path), skip_rows=2, skiprows=2))

    def test_delimiter_auto_inferred_for_tsv(self, tmp_path):
        """delimiter=None auto-infers tab for .tsv files, matching read_csv."""
        path = tmp_path / "data.tsv"
        path.write_text("name\tage\nAlice\t30\nBob\t25\n")

        chunks = list(ar.read_csv_chunked(str(path)))
        df = pd.concat([ar.to_pandas(c) for c in chunks], ignore_index=True)
        assert list(df.columns) == ["name", "age"]
        assert df.shape[0] == 2

    def test_delimiter_auto_inferred_for_csv(self, tmp_path):
        """delimiter=None defaults to comma for .csv files."""
        path = tmp_path / "data.csv"
        path.write_text("name,age\nAlice,30\nBob,25\n")

        chunks = list(ar.read_csv_chunked(str(path)))
        df = pd.concat([ar.to_pandas(c) for c in chunks], ignore_index=True)
        assert list(df.columns) == ["name", "age"]

    def test_explicit_delimiter_overrides_extension(self, tmp_path):
        """Explicit delimiter always takes precedence over extension inference."""
        path = tmp_path / "data.tsv"
        path.write_text("name,age\nAlice,30\nBob,25\n")

        chunks = list(ar.read_csv_chunked(str(path), delimiter=","))
        df = pd.concat([ar.to_pandas(c) for c in chunks], ignore_index=True)
        assert list(df.columns) == ["name", "age"]
