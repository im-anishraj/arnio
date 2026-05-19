"""Tests for chunked CSV reading."""

import pandas as pd
import pytest

import arnio as ar


def _chunked_rows(path: str, **kwargs) -> list[ar.ArFrame]:
    return list(ar.read_csv_chunked(path, **kwargs))


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
        path.write_text(
            'id,text\n'
            '1,"line one\nline two"\n'
            '2,simple\n'
            '3,"another\nquoted"\n'
            '4,plain\n'
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
