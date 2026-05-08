"""Tests for CSV reading functionality."""

import arnio as ar


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
        import pytest

        file_path = str(tmp_path / "data.csv")
        with open(file_path, "wb") as f:
            f.write(b"col1,col2\n\0binary\0,data\n")

        with pytest.raises(ValueError, match="File appears to be binary"):
            ar.read_csv(file_path)

    def test_utf8_bom_handling(self, tmp_path):
        csv_path = tmp_path / "bom.csv"
        csv_path.write_bytes(b"\xef\xbb\xbfname,age\nAlice,30\nBob,25\n")

        frame = ar.read_csv(str(csv_path), usecols=["name"])
        assert frame.columns == ["name"]
        assert frame.shape == (2, 1)

        schema = ar.scan_csv(str(csv_path))
        assert "name" in schema
        assert "\ufeffname" not in schema


class TestScanCsv:
    def test_scan_schema(self, sample_csv):
        schema = ar.scan_csv(sample_csv)
        assert isinstance(schema, dict)
        assert "name" in schema
        assert "age" in schema
        assert schema["age"] == "int64"
