"""Tests for CSV reading functionality."""

from pathlib import Path

import pandas as pd
import pytest

import arnio as ar

MESSY_CSV = str(Path(__file__).parent / "fixtures" / "messy_sales_data.csv")


class TestReadCsv:
    def test_basic_read(self, sample_csv):
        frame = ar.read_csv(sample_csv)
        assert isinstance(frame, ar.ArFrame)
        assert frame.shape == (3, 4)
        assert frame.columns == ["name", "age", "email", "active"]

    def test_usecols(self, sample_csv):
        frame = ar.read_csv(sample_csv, usecols=["name", "age"])
        assert frame.shape == (3, 2)
        assert frame.columns == ["name", "age"]

    def test_nrows(self, sample_csv):
        frame = ar.read_csv(sample_csv, nrows=2)
        assert frame.shape == (2, 4)

    def test_no_header(self, csv_no_header):
        frame = ar.read_csv(csv_no_header, has_header=False)
        assert frame.shape == (2, 3)
        assert "col_0" in frame.columns

    def test_type_inference(self, sample_csv):
        frame = ar.read_csv(sample_csv)
        dtypes = frame.dtypes
        assert dtypes["age"] == "int64"
        assert dtypes["name"] == "string"
        assert dtypes["active"] == "bool"

    def test_large_csv(self, large_csv):
        frame = ar.read_csv(large_csv)
        assert frame.shape == (1000, 3)

    def test_memory_usage(self, sample_csv):
        frame = ar.read_csv(sample_csv)
        assert frame.memory_usage() > 0

    def test_repr(self, sample_csv):
        frame = ar.read_csv(sample_csv)
        assert "3 rows" in repr(frame)
        assert "4 cols" in repr(frame)

    def test_len(self, sample_csv):
        frame = ar.read_csv(sample_csv)
        assert len(frame) == 3

    def test_header_whitespace(self, tmp_path):

        csv_path = str(tmp_path / "whitespace.csv")
        with open(csv_path, "w") as f:
            f.write("name ,  age\nAlice,25\n")

        frame = ar.read_csv(csv_path)
        assert frame.columns == ["name", "age"]

    def test_unsupported_extension(self, tmp_path):
        import pytest

        file_path = str(tmp_path / "data.json")
        with open(file_path, "w") as f:
            f.write('{"a": 1}')

        with pytest.raises(ValueError, match="Unsupported file format"):
            ar.read_csv(file_path)

    def test_binary_file_rejection(self, tmp_path):
        file_path = str(tmp_path / "data.csv")
        with open(file_path, "wb") as f:
            f.write(b"col1,col2\n\0binary\0,data\n")

        with pytest.raises(
            ar.CsvReadError,
            match="CSV input contains NUL bytes and appears to be binary or corrupted",
        ):
            ar.read_csv(file_path)

    def test_read_with_nulls(self, csv_with_nulls):
        frame = ar.read_csv(csv_with_nulls)
        assert frame.shape == (4, 3)

        df = ar.to_pandas(frame)
        assert df["name"].isna().sum() == 1
        assert df["age"].isna().sum() == 1
        assert df["score"].isna().sum() == 1

        assert pd.isna(df.loc[1, "name"])
        assert pd.isna(df.loc[1, "score"])
        assert pd.isna(df.loc[2, "age"])

        assert df.loc[0, "name"] == "Alice"
        assert df.loc[3, "name"] == "Diana"

    def test_read_messy_nulls(self):
        frame = ar.read_csv(MESSY_CSV)
        assert frame.shape == (3, 3)

        df = ar.to_pandas(frame)
        assert df["revenue"].isna().sum() == 1
        assert pd.isna(df.loc[1, "revenue"])

    def test_utf8_bom_handling(self, tmp_path):
        csv_path = tmp_path / "bom.csv"
        csv_path.write_bytes(b"\xef\xbb\xbfname,age\nAlice,30\nBob,25\n")

        frame = ar.read_csv(str(csv_path), usecols=["name"])
        assert frame.columns == ["name"]
        assert frame.shape == (2, 1)

        schema = ar.scan_csv(str(csv_path))
        assert "name" in schema
        assert "\ufeffname" not in schema

    def test_pathlike_input(self, sample_csv):
        frame = ar.read_csv(Path(sample_csv))
        assert frame.shape == (3, 4)

    def test_non_utf8_encoding(self, tmp_path):
        csv_path = tmp_path / "latin.csv"
        csv_path.write_bytes("name\nAndré\n".encode("latin-1"))

        frame = ar.read_csv(csv_path, encoding="latin-1")
        df = ar.to_pandas(frame)

        assert df["name"].iloc[0] == "André"

    def test_quoted_newline_record(self, tmp_path):
        csv_path = tmp_path / "quoted_newline.csv"
        csv_path.write_text('id,text\n1,"hello\nworld"\n2,ok\n')

        frame = ar.read_csv(csv_path)
        df = ar.to_pandas(frame)

        assert frame.shape == (2, 2)
        assert df["text"].iloc[0] == "hello\nworld"
        assert df["text"].iloc[1] == "ok"

    def test_unterminated_quote_rejected(self, tmp_path):
        csv_path = tmp_path / "unterminated.csv"
        csv_path.write_text('id,text\n1,"hello\n')

        with pytest.raises(ar.CsvReadError, match="Unterminated quoted CSV record"):
            ar.read_csv(csv_path)

    def test_duplicate_headers_rejected(self, tmp_path):
        csv_path = tmp_path / "duplicate_headers.csv"
        csv_path.write_text("a,a\n1,2\n")

        with pytest.raises(ar.CsvReadError, match="Duplicate column name: a"):
            ar.read_csv(csv_path)


class TestScanCsv:
    def test_scan_schema(self, sample_csv):
        schema = ar.scan_csv(sample_csv)
        assert isinstance(schema, dict)
        assert "name" in schema
        assert "age" in schema
        assert schema["age"] == "int64"

    def test_scan_non_utf8_encoding(self, tmp_path):
        csv_path = tmp_path / "latin.csv"
        csv_path.write_bytes("name\nAndré\n".encode("latin-1"))

        schema = ar.scan_csv(csv_path, encoding="latin-1")

        assert schema == {"name": "string"}

    def test_scan_binary_file_rejection(self, tmp_path):
        file_path = str(tmp_path / "data.csv")

        with open(file_path, "wb") as f:
            f.write(b"col1,col2\n\0binary\0,data\n")

        with pytest.raises(
            ar.CsvReadError,
            match="CSV input contains NUL bytes and appears to be binary or corrupted",
        ):
            ar.scan_csv(file_path)


class TestWriteCsv:
    """Tests for write_csv delimiter, newline, and quote validation."""

    def test_write_basic(self, sample_csv, tmp_path):
        """write_csv creates a readable CSV file."""
        import arnio as ar
        frame = ar.read_csv(sample_csv)
        out = str(tmp_path / "out.csv")
        ar.write_csv(frame, out)
        result = ar.read_csv(out)
        assert result.shape == frame.shape
        assert result.columns == frame.columns

    def test_write_custom_delimiter(self, sample_csv, tmp_path):
        """write_csv respects custom delimiter."""
        import arnio as ar
        frame = ar.read_csv(sample_csv)
        out = str(tmp_path / "out.tsv")
        ar.write_csv(frame, out, delimiter="\t")
        content = open(out).read()
        assert "\t" in content

    def test_write_invalid_delimiter_empty(self, sample_csv, tmp_path):
        """write_csv raises ValueError for empty delimiter."""
        import arnio as ar
        frame = ar.read_csv(sample_csv)
        out = str(tmp_path / "out.csv")
        with pytest.raises(ValueError, match="delimiter"):
            ar.write_csv(frame, out, delimiter="")

    def test_write_invalid_delimiter_multi(self, sample_csv, tmp_path):
        """write_csv raises ValueError for multi-char delimiter."""
        import arnio as ar
        frame = ar.read_csv(sample_csv)
        out = str(tmp_path / "out.csv")
        with pytest.raises(ValueError, match="delimiter"):
            ar.write_csv(frame, out, delimiter=",,")

    def test_write_newline_crlf(self, sample_csv, tmp_path):
        """write_csv respects CRLF newline."""
        import arnio as ar
        frame = ar.read_csv(sample_csv)
        out = str(tmp_path / "out.csv")
        ar.write_csv(frame, out, newline="\r\n")
        content = open(out, "rb").read()
        assert b"\r\n" in content

    def test_write_newline_cr(self, sample_csv, tmp_path):
        """write_csv respects CR newline."""
        import arnio as ar
        frame = ar.read_csv(sample_csv)
        out = str(tmp_path / "out.csv")
        ar.write_csv(frame, out, newline="\r")
        content = open(out, "rb").read()
        assert b"\r" in content

    def test_write_invalid_newline(self, sample_csv, tmp_path):
        """write_csv raises ValueError for invalid newline."""
        import arnio as ar
        frame = ar.read_csv(sample_csv)
        out = str(tmp_path / "out.csv")
        with pytest.raises(ValueError, match="newline"):
            ar.write_csv(frame, out, newline="\\n")

    def test_write_custom_quote_char(self, sample_csv, tmp_path):
        """write_csv respects custom quote character."""
        import arnio as ar
        frame = ar.read_csv(sample_csv)
        out = str(tmp_path / "out.csv")
        ar.write_csv(frame, out, quote_char="'")
        content = open(out).read()
        assert content  # file written successfully

    def test_write_invalid_quote_char_empty(self, sample_csv, tmp_path):
        """write_csv raises ValueError for empty quote_char."""
        import arnio as ar
        frame = ar.read_csv(sample_csv)
        out = str(tmp_path / "out.csv")
        with pytest.raises(ValueError, match="quote_char"):
            ar.write_csv(frame, out, quote_char="")

    def test_write_invalid_quote_char_multi(self, sample_csv, tmp_path):
        """write_csv raises ValueError for multi-char quote_char."""
        import arnio as ar
        frame = ar.read_csv(sample_csv)
        out = str(tmp_path / "out.csv")
        with pytest.raises(ValueError, match="quote_char"):
            ar.write_csv(frame, out, quote_char='""')

    def test_write_unsupported_extension(self, sample_csv, tmp_path):
        """write_csv raises ValueError for unsupported file extension."""
        import arnio as ar
        frame = ar.read_csv(sample_csv)
        out = str(tmp_path / "out.xlsx")
        with pytest.raises(ValueError, match="Unsupported file format"):
            ar.write_csv(frame, out)
