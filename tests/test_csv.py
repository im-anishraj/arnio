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

    def test_contains_operator(self, sample_csv):
        frame = ar.read_csv(sample_csv)

        assert "name" in frame
        assert "missing" not in frame
        assert 123 not in frame

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

    def test_utf16_encoding_with_nul_bytes_reads_successfully(self, tmp_path):
        csv_path = tmp_path / "utf16.csv"
        csv_path.write_text("name,age\nAlice,30\n", encoding="utf-16")

        frame = ar.read_csv(csv_path, encoding="utf-16")
        df = ar.to_pandas(frame)

        assert frame.columns == ["name", "age"]
        assert frame.shape == (1, 2)
        assert df["name"].iloc[0] == "Alice"
        assert df["age"].iloc[0] == 30

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

    def test_empty_file_raises(self, tmp_path):
        csv_path = tmp_path / "empty.csv"
        csv_path.write_text("")
        with pytest.raises(ar.CsvReadError, match="CSV file is empty"):
            ar.read_csv(str(csv_path))

    def test_missing_file_passthrough(self, tmp_path):
        with pytest.raises(ar.CsvReadError):
            ar.read_csv(str(tmp_path / "nonexistent.csv"))


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

    def test_scan_utf16_encoding_with_nul_bytes_reads_successfully(self, tmp_path):
        csv_path = tmp_path / "utf16.csv"
        csv_path.write_text("name,age\nAlice,30\n", encoding="utf-16")

        schema = ar.scan_csv(csv_path, encoding="utf-16")

        assert schema == {"name": "string", "age": "int64"}

    def test_scan_binary_file_rejection(self, tmp_path):
        file_path = str(tmp_path / "data.csv")

        with open(file_path, "wb") as f:
            f.write(b"col1,col2\n\0binary\0,data\n")

        with pytest.raises(
            ar.CsvReadError,
            match="CSV input contains NUL bytes and appears to be binary or corrupted",
        ):
            ar.scan_csv(file_path)

    def test_scan_empty_file_raises(self, tmp_path):
        csv_path = tmp_path / "empty.csv"
        csv_path.write_text("")
        with pytest.raises(ar.CsvReadError, match="CSV file is empty"):
            ar.scan_csv(str(csv_path))

    def test_scan_missing_file_passthrough(self, tmp_path):
        with pytest.raises(ar.CsvReadError):
            ar.scan_csv(str(tmp_path / "nonexistent.csv"))

    def test_scan_schema_preserves_column_order(self, tmp_path):
        csv_path = tmp_path / "order_test.csv"
        csv_path.write_text("z,a,m\n1,2,3\n")

        schema = ar.scan_csv(str(csv_path))
        frame = ar.read_csv(str(csv_path))

        assert list(schema.keys()) == ["z", "a", "m"]
        assert list(frame.columns) == ["z", "a", "m"]

    def test_scan_schema_order_matches_read_csv(self, sample_csv):
        schema = ar.scan_csv(sample_csv)
        frame = ar.read_csv(sample_csv)

        assert list(schema.keys()) == list(frame.columns)

    def test_scan_csv_non_utf8_multiline_boundary(self, tmp_path):
        """scan_csv must not split a quoted multiline record at the sample boundary.

        Previously the sampling path iterated raw physical lines, which could
        cut through a quoted field that contained an embedded newline. The result
        was an invalid partial CSV fed to scan_schema, causing either a parse
        error or wrong type inference. With record-aware sampling (csv.reader)
        the boundary always falls between complete records.
        """
        csv_file = tmp_path / "test_multiline_boundary.csv"

        # Build ~10 000 rows so the multiline record sits right at the limit.
        content_lines = ["id,text"]
        for i in range(1, 9999):
            content_lines.append(f"{i},value")

        # Row 9999 — a quoted field containing embedded newlines and a
        # latin-1 character (é). This record straddles the old line-count
        # boundary and would have been split by the previous implementation.
        content_lines.append('9999,"multiline\nrecord\ncafé"')
        content_lines.append("10000,end")

        csv_content = "\n".join(content_lines)

        # Write as latin-1 so the non-UTF-8 transcode path is exercised.
        csv_file.write_bytes(csv_content.encode("latin-1"))

        schema = ar.scan_csv(str(csv_file), encoding="latin-1")
        assert schema == {"id": "int64", "text": "string"}

    def test_scan_csv_type_evidence_after_limit(self, tmp_path):
        """Type evidence that appears after the sample window must not affect inference.

        scan_csv is documented to infer types from a leading sample. A float
        value that appears only beyond row 10 000 should not change the inferred
        type of a column that looks like int64 within the sample. This test pins
        that contract so future changes to the sample size don't silently break
        the documented behaviour.
        """
        csv_file = tmp_path / "test_type_evidence.csv"

        content_lines = ["id,value"]
        for i in range(1, 10005):
            content_lines.append(f"{i},100")

        # Row 10 006 — float evidence that falls outside the 10 000-row sample.
        content_lines.append("10006,3.14")

        csv_content = "\n".join(content_lines)

        # latin-1 encoding so the transcode + sampling path is exercised.
        csv_file.write_bytes(csv_content.encode("latin-1"))

        schema = ar.scan_csv(str(csv_file), encoding="latin-1")
        # The float is outside the sample; 'value' must be inferred as int64.
        assert schema["value"] == "int64"
