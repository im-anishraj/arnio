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
