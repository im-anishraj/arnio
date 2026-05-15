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

    def test_trim_headers_true_is_default(self, tmp_path):
        csv_path = str(tmp_path / "trim.csv")
        with open(csv_path, "w") as f:
            f.write(" name ,  age \nAlice,30\n")

        frame = ar.read_csv(csv_path)
        assert frame.columns == ["name", "age"]

    def test_trim_headers_false_preserves_spaces(self, tmp_path):
        csv_path = str(tmp_path / "notrim.csv")
        with open(csv_path, "w") as f:
            f.write(" name ,  age \nAlice,30\n")

        frame = ar.read_csv(csv_path, trim_headers=False)
        assert frame.columns == [" name ", "  age "]

    def test_trim_headers_false_scan_csv(self, tmp_path):
        csv_path = str(tmp_path / "scan_notrim.csv")
        with open(csv_path, "w") as f:
            f.write(" score , active \n95,true\n")

        schema = ar.scan_csv(csv_path, trim_headers=False)
        assert " score " in schema
        assert " active " in schema

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

    def test_na_sentinel_values(self, tmp_path):
        """Test that standard NA sentinel values are recognized as null."""
        csv_path = tmp_path / "na_values.csv"
        csv_path.write_text(
            "name,score,active\n"
            "Alice,10,true\n"
            "NA,NA,NA\n"
            "N/A,N/A,N/A\n"
            "null,null,null\n"
            "None,None,None\n"
            "NaN,NaN,NaN\n"
            "-, -, -\n"
            "Bob,20,false\n"
        )

        frame = ar.read_csv(str(csv_path))
        df = ar.to_pandas(frame)

        # Verify shape
        assert frame.shape == (8, 3)

        # Check that sentinel rows are all null
        sentinel_rows = [1, 2, 3, 4, 5, 6]
        for row_idx in sentinel_rows:
            assert pd.isna(df.loc[row_idx, "name"]), f"Row {row_idx} name should be null"
            assert pd.isna(df.loc[row_idx, "score"]), f"Row {row_idx} score should be null"
            assert pd.isna(df.loc[row_idx, "active"]), f"Row {row_idx} active should be null"

        # Check valid rows
        assert df.loc[0, "name"] == "Alice"
        assert df.loc[0, "score"] == 10
        assert df.loc[0, "active"] == True
        assert df.loc[7, "name"] == "Bob"
        assert df.loc[7, "score"] == 20
        assert df.loc[7, "active"] == False

    def test_na_sentinels_type_inference(self, tmp_path):
        """Test that NA sentinels don't force numeric columns to string."""
        csv_path = tmp_path / "na_inference.csv"
        csv_path.write_text(
            "id,value\n"
            "1,100.5\n"
            "2,NA\n"
            "3,200.0\n"
            "4,None\n"
        )

        frame = ar.read_csv(str(csv_path))
        dtypes = frame.dtypes

        # id should be int64, value should be float64 (not string)
        assert dtypes["id"] == "int64", f"Expected int64, got {dtypes['id']}"
        assert dtypes["value"] == "float64", f"Expected float64, got {dtypes['value']}"

        df = ar.to_pandas(frame)
        assert pd.isna(df.loc[1, "value"])
        assert pd.isna(df.loc[3, "value"])
        assert df.loc[0, "value"] == 100.5
        assert df.loc[2, "value"] == 200.0


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
