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
