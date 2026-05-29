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


class TestCsvChunkedNullColumnSchemaInference:
    """Regression tests for the all-null-first-chunk schema corruption bug.

    When a column's first chunk contains only null values the schema must not be
    permanently locked to STRING.  Subsequent chunks that contain real integers
    or floats must be inferred and stored with the correct type.
    """

    def test_integer_column_all_null_in_first_chunk(self, tmp_path):
        """INT column that is all-null in chunk 1 must be int64, not string."""
        path = tmp_path / "null_first.csv"
        # chunk 1 (rows 0-1): id present, value is null
        # chunk 2 (rows 2-3): id present, value is integer
        path.write_text("id,value\n1,\n2,\n3,10\n4,20\n")

        chunks = list(ar.read_csv_chunked(str(path), chunksize=2))
        assert len(chunks) == 2

        # The second chunk must have inferred int64, not string
        dtypes = chunks[1].dtypes
        assert dtypes["value"] == "int64", (
            f"Expected int64 for 'value' in chunk 2, got {dtypes['value']!r}. "
            "Schema was incorrectly locked to STRING because chunk 1 was all-null."
        )

    def test_float_column_all_null_in_first_chunk(self, tmp_path):
        """FLOAT column that is all-null in chunk 1 must be float64, not string."""
        path = tmp_path / "null_first_float.csv"
        path.write_text("name,score\nalice,\nbob,\ncarol,9.5\ndave,8.1\n")

        chunks = list(ar.read_csv_chunked(str(path), chunksize=2))
        assert len(chunks) == 2

        dtypes = chunks[1].dtypes
        assert (
            dtypes["score"] == "float64"
        ), f"Expected float64 for 'score' in chunk 2, got {dtypes['score']!r}."

    def test_null_first_chunk_values_are_null_not_string(self, tmp_path):
        """Null values in chunk 1 must be null, not the string ''."""
        path = tmp_path / "null_values_check.csv"
        path.write_text("id,value\n1,\n2,\n3,42\n4,99\n")

        chunks = list(ar.read_csv_chunked(str(path), chunksize=2))
        df = pd.concat([ar.to_pandas(c) for c in chunks], ignore_index=True)

        # Rows 0 and 1 must be genuinely null (NaN / pd.NA), not the string "".
        assert pd.isna(
            df.loc[0, "value"]
        ), "Row 0 'value' should be null, not a string."
        assert pd.isna(
            df.loc[1, "value"]
        ), "Row 1 'value' should be null, not a string."
        # Rows 2 and 3 must be integers.
        assert df.loc[2, "value"] == 42
        assert df.loc[3, "value"] == 99

    def test_schema_consistent_across_all_chunks(self, tmp_path):
        """Once a column resolves past NULL_TYPE, all subsequent chunks must
        share the same dtype.  Early all-null chunks legitimately emit STRING
        (no evidence yet) and are excluded from the consistency check."""
        path = tmp_path / "consistent.csv"
        lines = ["a,b,c"]
        # Chunks 0-1 (rows 0-3): column b is all-null
        for i in range(4):
            lines.append(f"{i},,{i * 0.5}")
        # Chunks 2-9 (rows 4-19): column b has integers
        for i in range(4, 20):
            lines.append(f"{i},{i},{i * 0.5}")
        path.write_text("\n".join(lines))

        chunks = list(ar.read_csv_chunked(str(path), chunksize=2))
        assert len(chunks) == 10

        # Find the first chunk where b is no longer STRING (i.e. resolved).
        resolved_dtypes = chunks[-1].dtypes
        first_resolved = next(
            i for i, c in enumerate(chunks) if c.dtypes.get("b") != "string"
        )

        # Every chunk from that point onward must have the same dtypes.
        for idx in range(first_resolved, len(chunks)):
            for col, dtype in chunks[idx].dtypes.items():
                assert dtype == resolved_dtypes[col], (
                    f"Chunk {idx} column {col!r}: got {dtype!r}, "
                    f"expected {resolved_dtypes[col]!r}"
                )

        # Sanity: b must actually have resolved to int64.
        assert (
            resolved_dtypes["b"] == "int64"
        ), f"Column 'b' never resolved to int64; got {resolved_dtypes['b']!r}"

    def test_genuinely_all_null_column_becomes_string(self, tmp_path):
        """A column that is null in every row across all chunks must be STRING."""
        path = tmp_path / "always_null.csv"
        path.write_text("id,empty\n1,\n2,\n3,\n4,\n")

        chunks = list(ar.read_csv_chunked(str(path), chunksize=2))
        assert len(chunks) == 2

        for i, chunk in enumerate(chunks):
            assert chunk.dtypes["empty"] == "string", (
                f"Chunk {i}: all-null column 'empty' should fall back to string, "
                f"got {chunk.dtypes['empty']!r}"
            )

    def test_full_dataframe_matches_read_csv_with_null_first_chunk(self, tmp_path):
        """Chunked read must produce correct values and a resolved int64/float64
        dtype for columns that were all-null in the first chunk.

        Full DataFrame equality against read_csv cannot be asserted here:
        early all-null chunks emit STRING, so pandas concat produces object
        dtype for those columns, whereas read_csv infers Int64 in a single
        pass.  What matters is that (a) non-null values are numerically
        correct and (b) the column resolves to the right type by the last chunk.
        """
        path = tmp_path / "parity_null_first.csv"
        lines = ["x,y,z"]
        for i in range(6):
            y_val = "" if i < 2 else str(i * 10)
            lines.append(f"{i},{y_val},{i + 0.1}")
        path.write_text("\n".join(lines))

        chunks = list(ar.read_csv_chunked(str(path), chunksize=2))
        df = pd.concat([ar.to_pandas(c) for c in chunks], ignore_index=True)

        # Null rows must be genuinely null, not the string "".
        assert pd.isna(df.loc[0, "y"])
        assert pd.isna(df.loc[1, "y"])

        # Non-null rows must carry the correct numeric values.
        assert df.loc[2, "y"] == 20
        assert df.loc[3, "y"] == 30
        assert df.loc[4, "y"] == 40
        assert df.loc[5, "y"] == 50

        # The last chunk (where y was resolved) must have int64, not string.
        assert (
            chunks[-1].dtypes["y"] == "int64"
        ), f"Expected last chunk dtype int64, got {chunks[-1].dtypes['y']!r}"

        # Columns x and z must match read_csv exactly (they were never all-null).
        full_df = ar.to_pandas(ar.read_csv(str(path)))
        pd.testing.assert_series_equal(df["x"], full_df["x"], check_names=True)
        pd.testing.assert_series_equal(df["z"], full_df["z"], check_names=True)


class TestCsvChunkedIssue924:
    """Regression tests for Issue #924: Type mismatch in chunked reads."""

    def test_late_mixed_types_raises_error(self, tmp_path):
        """Verify that type mismatches in later chunks raise errors (fail-fast).

        Uses pandas with string values to prevent auto-casting, ensuring the CSV
        file itself contains the mixed types that will trigger the type mismatch error.
        """
        path = tmp_path / "type_mismatch.csv"

        # Create DataFrame with string values: first two are integers, next two are floats
        # This prevents pandas from auto-upcasting to float64 before writing the CSV
        df = pd.DataFrame({"value": ["1", "2", "3.5", "4.8"]})
        df.to_csv(path, index=False)

        # Read with chunksize=2
        # Chunk 1: "1", "2" → inferred as int64
        # Chunk 2: "3.5", "4.8" → contains floats, should raise Type mismatch error
        reader = ar.read_csv_chunked(str(path), chunksize=2)

        # First chunk should succeed
        chunk1 = next(reader)
        assert chunk1 is not None

        # Second chunk should raise because floats don't match int64 type
        with pytest.raises(Exception, match="Type mismatch"):
            next(reader)

    def test_valid_null_handling_preserved(self, tmp_path):
        """Ensure genuine empty/null values don't trigger mismatch errors."""
        path = tmp_path / "valid_nulls.csv"
        # Chunk 1: has some integers
        # Chunk 2: has empty strings and commas (genuine nulls, should be parsed as NaN/None)
        lines = [
            "id,value",
            "1,100",
            "2,200",
            "3,",  # Empty value = genuine null
            "4,400",
            "5,",  # Another empty value
        ]
        path.write_text("\n".join(lines))

        chunks = list(ar.read_csv_chunked(str(path), chunksize=2))
        assert len(chunks) == 3

        # Verify that empty values are parsed as NaN (not errors)
        chunked_df = pd.concat([ar.to_pandas(c) for c in chunks], ignore_index=True)
        assert chunked_df.shape[0] == 5
        # Rows 2 and 4 (0-indexed) should have NaN in value column
        assert pd.isna(chunked_df.loc[2, "value"])
        assert pd.isna(chunked_df.loc[4, "value"])

    def test_multiple_chunk_boundaries(self, tmp_path):
        """Test that type mismatch is detected at the correct chunk boundary (chunk 3)."""
        path = tmp_path / "multi_chunk_mismatch.csv"
        # Chunk 1: integers (1, 2)
        # Chunk 2: integers (3, 4)
        # Chunk 3: has a float (5.5) - should raise here
        # Chunk 4: would have more data
        lines = [
            "number",
            "1",
            "2",
            "3",
            "4",
            "5.5",
            "6",
        ]
        path.write_text("\n".join(lines))

        reader = ar.read_csv_chunked(str(path), chunksize=2)
        chunk1 = next(reader)
        assert chunk1 is not None  # Rows 1, 2

        chunk2 = next(reader)
        assert chunk2 is not None  # Rows 3, 4

        # Chunk 3 should raise on row 5 (value 5.5)
        with pytest.raises(Exception, match="Type mismatch"):
            next(reader)


class TestReadCsvChunkedTsvDelimiter:
    """Regression tests for Issue #1811: auto-detect TSV delimiter in read_csv_chunked.

    read_csv_chunked() must infer delimiter='\\t' for .tsv paths when the
    caller does not supply an explicit delimiter, matching the behaviour of
    read_csv() and scan_csv().
    """

    def test_tsv_columns_auto_detected(self, tmp_path):
        """Omitting delimiter on a .tsv path must yield the correct column names."""
        path = tmp_path / "sample.tsv"
        path.write_text("a\tb\n1\t2\n3\t4\n")

        chunks = list(ar.read_csv_chunked(str(path), chunksize=2))
        assert len(chunks) == 1
        assert list(chunks[0].columns) == ["a", "b"], (
            f"Expected columns ['a', 'b'] but got {list(chunks[0].columns)!r}. "
            "read_csv_chunked is not auto-detecting the tab delimiter for .tsv files."
        )

    def test_tsv_chunked_matches_read_csv(self, tmp_path):
        """Chunked TSV read must produce the same data as read_csv on the same file."""
        lines = ["name\tage\tscore"]
        for i in range(10):
            lines.append(f"user_{i}\t{20 + i}\t{95.0 - i}")
        path = tmp_path / "data.tsv"
        path.write_text("\n".join(lines))

        chunks = list(ar.read_csv_chunked(str(path), chunksize=3))
        chunked_df = pd.concat([ar.to_pandas(c) for c in chunks], ignore_index=True)
        full_df = ar.to_pandas(ar.read_csv(str(path)))
        pd.testing.assert_frame_equal(chunked_df, full_df)

    def test_tsv_explicit_comma_delimiter_overrides_auto_detect(self, tmp_path):
        """An explicit delimiter=',' must be honoured even for a .tsv path."""
        # File is actually comma-delimited despite the .tsv extension.
        path = tmp_path / "comma_disguised.tsv"
        path.write_text("x,y\n1,2\n3,4\n")

        chunks = list(ar.read_csv_chunked(str(path), chunksize=2, delimiter=","))
        assert len(chunks) == 1
        assert list(chunks[0].columns) == [
            "x",
            "y",
        ], "Explicit delimiter=',' on a .tsv path must override auto-detection."

    def test_csv_extension_still_defaults_to_comma(self, tmp_path):
        """A .csv path must still default to comma when delimiter is omitted."""
        path = tmp_path / "regular.csv"
        path.write_text("p,q\n10,20\n30,40\n")

        chunks = list(ar.read_csv_chunked(str(path), chunksize=2))
        assert list(chunks[0].columns) == ["p", "q"]

    def test_tsv_multi_chunk_row_integrity(self, tmp_path):
        """Tab-delimited data must survive chunk boundaries correctly."""
        lines = ["id\tvalue"]
        for i in range(9):
            lines.append(f"{i}\t{i * 10}")
        path = tmp_path / "multi.tsv"
        path.write_text("\n".join(lines))

        chunks = list(ar.read_csv_chunked(str(path), chunksize=4))
        assert len(chunks) == 3  # 4 + 4 + 1

        chunked_df = pd.concat([ar.to_pandas(c) for c in chunks], ignore_index=True)
        assert chunked_df.shape == (9, 2)
        assert chunked_df["id"].tolist() == list(range(9))
        assert chunked_df["value"].tolist() == [i * 10 for i in range(9)]


class TestReadCsvChunkedCoverage:
    def test_invalid_path_type_raises_type_error(self):
        with pytest.raises(TypeError, match="expected a filesystem path or text file-like object"):
            list(ar.read_csv_chunked(123))

    def test_missing_file_raises_csv_read_error(self):
        with pytest.raises(CsvReadError, match="Cannot open file"):
            list(ar.read_csv_chunked("nonexistent_file.csv"))

    def test_unsupported_encoding_raises_value_error(self, tmp_path):
        path = tmp_path / "encoding_test.csv"
        path.write_text("a,b\n1,2\n")
        with pytest.raises(ValueError, match="Unknown encoding"):
            list(ar.read_csv_chunked(str(path), encoding="invalid_encoding"))

    def test_invalid_encoding_decode_error(self, tmp_path):
        path = tmp_path / "decode_test.csv"
        # Write non-ascii byte sequence
        path.write_bytes(b"\x80\n")
        with pytest.raises(CsvReadError, match="Could not decode.*using encoding 'ascii'"):
            list(ar.read_csv_chunked(str(path), encoding="ascii"))

    def test_empty_file_raises_csv_read_error(self, tmp_path):
        path = tmp_path / "empty_file.csv"
        path.write_text("")
        with pytest.raises(CsvReadError, match="CSV file is empty"):
            list(ar.read_csv_chunked(str(path)))

    def test_whitespace_only_file_raises(self, tmp_path):
        path = tmp_path / "whitespace_only.csv"
        path.write_text("   \n\n  \n")
        with pytest.raises(CsvReadError):
            list(ar.read_csv_chunked(str(path)))

    def test_invalid_delimiter_raises(self, tmp_path):
        path = tmp_path / "config_test.csv"
        path.write_text("a,b\n1,2\n")
        with pytest.raises(TypeError, match="delimiter must be a string"):
            list(ar.read_csv_chunked(str(path), delimiter=123))
        with pytest.raises(ValueError, match="delimiter must be exactly one character"):
            list(ar.read_csv_chunked(str(path), delimiter="abc"))

    def test_invalid_mode_raises(self, tmp_path):
        path = tmp_path / "config_test.csv"
        path.write_text("a,b\n1,2\n")
        with pytest.raises(TypeError, match="mode must be a string"):
            list(ar.read_csv_chunked(str(path), mode=123))
        with pytest.raises(ValueError, match="mode must be either 'strict' or 'permissive'"):
            list(ar.read_csv_chunked(str(path), mode="invalid_mode"))

    def test_invalid_on_bad_lines_raises(self, tmp_path):
        path = tmp_path / "config_test.csv"
        path.write_text("a,b\n1,2\n")
        with pytest.raises(TypeError, match="on_bad_lines must be a string"):
            list(ar.read_csv_chunked(str(path), on_bad_lines=123))
        with pytest.raises(ValueError, match="on_bad_lines must be either"):
            list(ar.read_csv_chunked(str(path), on_bad_lines="invalid_action"))

    def test_invalid_skip_rows_raises(self, tmp_path):
        path = tmp_path / "config_test.csv"
        path.write_text("a,b\n1,2\n")
        with pytest.raises(TypeError, match="skip_rows must be an integer"):
            list(ar.read_csv_chunked(str(path), skip_rows="one"))
        with pytest.raises(ValueError, match="skip_rows must be non-negative"):
            list(ar.read_csv_chunked(str(path), skip_rows=-5))

    def test_invalid_decimal_separator_raises(self, tmp_path):
        path = tmp_path / "config_test.csv"
        path.write_text("a,b\n1,2\n")
        with pytest.raises(TypeError, match="decimal_separator must be a string"):
            list(ar.read_csv_chunked(str(path), decimal_separator=123))
        with pytest.raises(ValueError, match="decimal_separator must be a single character"):
            list(ar.read_csv_chunked(str(path), decimal_separator="abc"))
        with pytest.raises(ValueError, match="Invalid decimal_separator"):
            list(ar.read_csv_chunked(str(path), decimal_separator="+"))

    def test_invalid_thousands_separator_raises(self, tmp_path):
        path = tmp_path / "config_test.csv"
        path.write_text("a,b\n1,2\n")
        with pytest.raises(TypeError, match="thousands_separator must be a string"):
            list(ar.read_csv_chunked(str(path), thousands_separator=123))
        with pytest.raises(ValueError, match="thousands_separator must differ from decimal_separator"):
            list(ar.read_csv_chunked(str(path), thousands_separator="."))

    def test_invalid_boolean_options_raise(self, tmp_path):
        path = tmp_path / "config_test.csv"
        path.write_text("a,b\n1,2\n")
        with pytest.raises(TypeError, match="has_header must be True or False"):
            list(ar.read_csv_chunked(str(path), has_header="yes"))
        with pytest.raises(TypeError, match="trim_headers must be True or False"):
            list(ar.read_csv_chunked(str(path), trim_headers="yes"))

    def test_invalid_usecols_raises(self, tmp_path):
        path = tmp_path / "config_test.csv"
        path.write_text("a,b\n1,2\n")
        with pytest.raises(TypeError, match="usecols must be a sequence of column names, not a string"):
            list(ar.read_csv_chunked(str(path), usecols="a"))
        with pytest.raises(TypeError, match="usecols must contain only strings"):
            list(ar.read_csv_chunked(str(path), usecols=[123]))
        with pytest.raises(ValueError, match="usecols must not be empty"):
            list(ar.read_csv_chunked(str(path), usecols=[]))
        with pytest.raises(ValueError, match="usecols must not contain duplicate column names"):
            list(ar.read_csv_chunked(str(path), usecols=["a", "a"]))

    def test_invalid_null_values_raises(self, tmp_path):
        path = tmp_path / "config_test.csv"
        path.write_text("a,b\n1,2\n")
        with pytest.raises(TypeError, match="null_values must be a list of strings, not a bare string"):
            list(ar.read_csv_chunked(str(path), null_values="NA"))
        with pytest.raises(TypeError, match="null_values must contain only strings"):
            list(ar.read_csv_chunked(str(path), null_values=[123]))

    def test_invalid_dtype_raises(self, tmp_path):
        path = tmp_path / "config_test.csv"
        path.write_text("a,b\n1,2\n")
        with pytest.raises(TypeError, match="dtype must be a dictionary"):
            list(ar.read_csv_chunked(str(path), dtype="int64"))
        with pytest.raises(TypeError, match="dtype column names must be strings"):
            list(ar.read_csv_chunked(str(path), dtype={123: "int64"}))
        with pytest.raises(TypeError, match="dtype values must be strings"):
            list(ar.read_csv_chunked(str(path), dtype={"a": 123}))
        with pytest.raises(ValueError, match="Unsupported dtype"):
            list(ar.read_csv_chunked(str(path), dtype={"a": "invalid_type"}))

    def test_invalid_nrows_raises(self, tmp_path):
        path = tmp_path / "config_test.csv"
        path.write_text("a,b\n1,2\n")
        with pytest.raises(TypeError, match="nrows must be an integer"):
            list(ar.read_csv_chunked(str(path), nrows=1.5))
        with pytest.raises(TypeError, match="nrows must be an integer"):
            list(ar.read_csv_chunked(str(path), nrows="one"))
        with pytest.raises(ValueError, match="nrows must be non-negative"):
            list(ar.read_csv_chunked(str(path), nrows=-1))

    def test_skiprows_and_skip_rows_conflicts(self, tmp_path):
        path = tmp_path / "config_test.csv"
        path.write_text("a,b\n1,2\n")
        with pytest.raises(TypeError, match="skiprows must be an integer"):
            list(ar.read_csv_chunked(str(path), skiprows=1.5))
        with pytest.raises(ValueError, match="skiprows must be non-negative"):
            list(ar.read_csv_chunked(str(path), skiprows=-1))
        with pytest.raises(ValueError, match="Conflicting values"):
            list(ar.read_csv_chunked(str(path), skip_rows=1, skiprows=2))

    def test_invalid_chunksize_types_raise(self, tmp_path):
        path = tmp_path / "config_test.csv"
        path.write_text("a,b\n1,2\n")
        with pytest.raises(TypeError, match="chunksize must be an integer"):
            list(ar.read_csv_chunked(str(path), chunksize=1.5))
        with pytest.raises(TypeError, match="chunksize must be an integer"):
            list(ar.read_csv_chunked(str(path), chunksize="one"))
        with pytest.raises(ValueError, match="chunksize must be a positive integer"):
            list(ar.read_csv_chunked(str(path), chunksize=-5))

    def test_nrows_and_chunksize_edge_cases(self, tmp_path):
        # 10 data rows
        lines = ["id"] + [str(i) for i in range(10)]
        path = tmp_path / "edge_cases.csv"
        path.write_text("\n".join(lines) + "\n")

        # nrows is 0
        chunks = list(ar.read_csv_chunked(str(path), chunksize=5, nrows=0))
        assert len(chunks) == 0

        # nrows is smaller than chunksize
        chunks = list(ar.read_csv_chunked(str(path), chunksize=5, nrows=3))
        assert len(chunks) == 1
        assert chunks[0].shape[0] == 3
        assert ar.to_pandas(chunks[0])["id"].tolist() == [0, 1, 2]

        # nrows is a multiple of chunksize
        chunks = list(ar.read_csv_chunked(str(path), chunksize=3, nrows=6))
        assert len(chunks) == 2
        assert [c.shape[0] for c in chunks] == [3, 3]
        df = pd.concat([ar.to_pandas(c) for c in chunks], ignore_index=True)
        assert df["id"].tolist() == [0, 1, 2, 3, 4, 5]

        # nrows is not a multiple of chunksize
        chunks = list(ar.read_csv_chunked(str(path), chunksize=3, nrows=8))
        assert len(chunks) == 3
        assert [c.shape[0] for c in chunks] == [3, 3, 2]
        df = pd.concat([ar.to_pandas(c) for c in chunks], ignore_index=True)
        assert df["id"].tolist() == [0, 1, 2, 3, 4, 5, 6, 7]

        # nrows is larger than total file rows (should read all rows and stop)
        chunks = list(ar.read_csv_chunked(str(path), chunksize=3, nrows=100))
        assert len(chunks) == 4  # 3 + 3 + 3 + 1
        df = pd.concat([ar.to_pandas(c) for c in chunks], ignore_index=True)
        assert df.shape[0] == 10
        assert df["id"].tolist() == list(range(10))

        # chunksize is larger than total file rows
        chunks = list(ar.read_csv_chunked(str(path), chunksize=50))
        assert len(chunks) == 1
        assert chunks[0].shape[0] == 10
        assert ar.to_pandas(chunks[0])["id"].tolist() == list(range(10))
