"""Tests for sniff_delimiter function in arnio.io."""

import pytest

import arnio as ar
from arnio.exceptions import CsvReadError
from arnio.io import sniff_delimiter


class TestSniffDelimiter:
    """Test suite for sniff_delimiter CSV delimiter detection."""

    def test_returns_comma_for_simple_csv(self, tmp_path):
        """sniff_delimiter returns comma for standard CSV data."""
        path = tmp_path / "simple.csv"
        path.write_text("name,age,city\nAlice,30,NYC\nBob,25,LA\n")
        result = sniff_delimiter(path)
        assert result == ","

    def test_returns_tab_for_tsv(self, tmp_path):
        """sniff_delimiter returns tab for TSV data."""
        path = tmp_path / "tsv.txt"
        path.write_text("name\tage\tcity\nAlice\t30\tNYC\nBob\t25\tLA\n")
        result = sniff_delimiter(path)
        assert result == "\t"

    def test_returns_pipe_delimiter(self, tmp_path):
        """sniff_delimiter detects pipe delimiter when present."""
        path = tmp_path / "pipe.txt"
        path.write_text("name|age|city\nAlice|30|NYC\nBob|25|LA\n")
        result = sniff_delimiter(path)
        assert result == "|"

    def test_returns_semicolon_delimiter(self, tmp_path):
        """sniff_delimiter detects semicolon delimiter when present."""
        path = tmp_path / "semicolon.txt"
        path.write_text("name;age;city\nAlice;30;NYC\nBob;25;LA\n")
        result = sniff_delimiter(path)
        assert result == ";"

    def test_raises_csv_read_error_for_empty_file(self, tmp_path):
        """sniff_delimiter raises CsvReadError when file is empty."""
        path = tmp_path / "empty.csv"
        path.write_text("")
        with pytest.raises(CsvReadError, match="CSV file is empty"):
            sniff_delimiter(path)

    def test_raises_csv_read_error_for_binary_file(self, tmp_path):
        """sniff_delimiter raises CsvReadError when file contains binary data."""
        path = tmp_path / "binary.csv"
        path.write_bytes(b"\x00\x01\x02\x03\x04")
        with pytest.raises(CsvReadError, match="NUL bytes"):
            sniff_delimiter(path)

    def test_raises_value_error_for_ambiguous_delimiter(self, tmp_path):
        """sniff_delimiter raises ValueError when delimiter is ambiguous."""
        path = tmp_path / "ambiguous.csv"
        path.write_text("a,b;c\nd,e;f\n")
        with pytest.raises(ValueError, match="multiple candidate delimiters"):
            sniff_delimiter(path)

    def test_raises_on_nonexistent_file(self, tmp_path):
        """sniff_delimiter raises FileNotFoundError for missing file."""
        path = tmp_path / "nonexistent.csv"
        with pytest.raises(FileNotFoundError):
            sniff_delimiter(path)

    def test_raises_type_error_for_invalid_encoding_type(self, tmp_path):
        """sniff_delimiter raises TypeError when encoding is not string."""
        path = tmp_path / "test.csv"
        path.write_text("a,b\n1,2\n")
        with pytest.raises(TypeError, match="encoding must be a string"):
            sniff_delimiter(path, encoding=123)

    def test_raises_type_error_for_invalid_sample_size_type(self, tmp_path):
        """sniff_delimiter raises TypeError when sample_size is not integer."""
        path = tmp_path / "test.csv"
        path.write_text("a,b\n1,2\n")
        with pytest.raises(TypeError, match="sample_size must be an integer"):
            sniff_delimiter(path, sample_size="not an int")

    def test_raises_value_error_for_negative_sample_size(self, tmp_path):
        """sniff_delimiter raises ValueError when sample_size is negative."""
        path = tmp_path / "test.csv"
        path.write_text("a,b\n1,2\n")
        with pytest.raises(ValueError, match="sample_size must be a positive integer"):
            sniff_delimiter(path, sample_size=-5)

    def test_respects_sample_size_parameter(self, tmp_path):
        """sniff_delimiter respects sample_size for large files."""
        path = tmp_path / "large.csv"
        path.write_text("a,b\n" + "x,y\n" * 1000)
        result = sniff_delimiter(path, sample_size=10)
        assert result == ","

    def test_handles_custom_encoding(self, tmp_path):
        """sniff_delimiter respects encoding parameter."""
        path = tmp_path / "latin1.csv"
        path.write_text("a,b\n1,2\n")
        result = sniff_delimiter(path, encoding="latin-1")
        assert result == ","

    def test_handles_quoted_fields_with_delimiter(self, tmp_path):
        """sniff_delimiter correctly handles delimiters inside quoted fields."""
        path = tmp_path / "quoted.csv"
        path.write_text('name,city\n"Smith, John",NYC\n"Doe, Jane",LA\n')
        result = sniff_delimiter(path)
        assert result == ","

    def test_detects_delimiter_in_single_line_file(self, tmp_path):
        """sniff_delimiter works on single-line CSV."""
        path = tmp_path / "single.csv"
        path.write_text("header1,header2,header3\n")
        result = sniff_delimiter(path)
        assert result == ","

    def test_raises_on_unknown_encoding(self, tmp_path):
        """sniff_delimiter raises ValueError for unknown encoding."""
        path = tmp_path / "test.csv"
        path.write_text("a,b\n1,2\n")
        with pytest.raises(ValueError, match="Unknown encoding"):
            sniff_delimiter(path, encoding="nonexistent_encoding_xyz")

    def test_does_not_confuse_trailing_newline_as_delimiter(self, tmp_path):
        """sniff_delimiter correctly identifies delimiter not counting empty lines."""
        path = tmp_path / "newlines.csv"
        path.write_text("a,b\nc,d\n\n")
        result = sniff_delimiter(path)
        assert result == ","

    def test_raises_value_error_for_single_column_no_delimiter(self, tmp_path):
        """sniff_delimiter raises ValueError when a single column file has no candidate delimiters."""
        path = tmp_path / "single_column.csv"
        path.write_text("onlycolumn\n123\n456\n")
        with pytest.raises(ValueError, match="no candidate delimiters found"):
            sniff_delimiter(path)

    def test_handles_complex_quoting_with_delimiters(self, tmp_path):
        """sniff_delimiter correctly detects comma for complex quoted fields."""
        path = tmp_path / "complex_quotes.csv"
        path.write_text('"col1,col2","col3,col4"\n"val1,val2","val3,val4"\n')
        result = sniff_delimiter(path)
        assert result == ","

    def test_handles_escaped_quotes_inside_fields(self, tmp_path):
        """sniff_delimiter correctly handles escaped quotes inside fields."""
        path = tmp_path / "escaped_quotes.csv"
        path.write_text(
            '"name","quote"\n"Alice","She said, ""hello""!"\n"Bob","He said, ""hi""!"\n'
        )
        result = sniff_delimiter(path)
        assert result == ","


class TestSniffDelimiterPublicAPI:
    """Tests validating sniff_delimiter with public parsing APIs."""

    def write_csv(self, tmp_path, name, content):
        path = tmp_path / name
        if isinstance(content, str):
            path.write_text(content, encoding="utf-8")
        else:
            path.write_bytes(content)
        return path

    def test_sniff_comma_delimiter(self, tmp_path):
        path = self.write_csv(tmp_path, "comma.csv", "a,b,c\n1,2,3\n")
        delim = ar.sniff_delimiter(str(path))
        assert delim == ","
        frame = ar.read_csv(str(path), delimiter=delim)
        assert frame.columns == ["a", "b", "c"]

    def test_sniff_semicolon_delimiter(self, tmp_path):
        path = self.write_csv(tmp_path, "semi.csv", "a;b;c\n1;2;3\n")
        delim = ar.sniff_delimiter(str(path))
        assert delim == ";"
        frame = ar.read_csv(str(path), delimiter=delim)
        assert frame.columns == ["a", "b", "c"]

    def test_sniff_tab_delimiter(self, tmp_path):
        path = self.write_csv(tmp_path, "tab.csv", "a\tb\tc\n1\t2\t3\n")
        delim = ar.sniff_delimiter(str(path))
        assert delim == "\t"
        frame = ar.read_csv(str(path), delimiter=delim)
        assert frame.columns == ["a", "b", "c"]

    def test_sniff_pipe_delimiter(self, tmp_path):
        path = self.write_csv(tmp_path, "pipe.csv", "a|b|c\n1|2|3\n")
        delim = ar.sniff_delimiter(str(path))
        assert delim == "|"
        frame = ar.read_csv(str(path), delimiter=delim)
        assert frame.columns == ["a", "b", "c"]

    def test_sniff_only_header_row(self, tmp_path):
        path = self.write_csv(tmp_path, "header.csv", "col1;col2;col3\n")
        delim = ar.sniff_delimiter(str(path))
        assert delim == ";"
        frame = ar.read_csv(str(path), delimiter=delim)
        assert frame.columns == ["col1", "col2", "col3"]

    def test_sniff_with_quoted_delimiter_inside_field(self, tmp_path):
        path = self.write_csv(
            tmp_path, "quoted.csv", 'name;desc\n"Alice;Smith";"a;b;c"\n'
        )
        delim = ar.sniff_delimiter(str(path))
        assert delim == ";"
        frame = ar.read_csv(str(path), delimiter=delim)
        assert frame.columns == ["name", "desc"]

    def test_sniff_mixed_whitespace(self, tmp_path):
        path = self.write_csv(tmp_path, "whitespace.csv", "a ; b ; c\n1 ; 2 ; 3\n")
        delim = ar.sniff_delimiter(str(path))
        assert delim == ";"
        frame = ar.read_csv(str(path), delimiter=delim)
        assert len(frame.columns) == 3

    def test_sniff_single_column_file(self, tmp_path):
        path = self.write_csv(tmp_path, "single.csv", "header\nval1\nval2\n")
        with pytest.raises(ValueError, match="no candidate delimiters found"):
            ar.sniff_delimiter(str(path))

    def test_sniff_inconsistent_rows(self, tmp_path):
        path = self.write_csv(tmp_path, "inconsistent.csv", "a;b;c\n1;2\n4;5;6;7\n")
        delim = ar.sniff_delimiter(str(path))
        assert delim == ";"
        with pytest.raises(ar.CsvReadError):
            ar.read_csv(str(path), delimiter=delim, mode="strict")
        with pytest.raises(ar.CsvReadError):
            ar.read_csv(str(path), delimiter=delim, mode="permissive")

    def test_utf8_bom(self, tmp_path):
        path = self.write_csv(tmp_path, "bom.csv", b"\xef\xbb\xbfa;b;c\n1;2;3\n")
        delim = ar.sniff_delimiter(str(path))
        assert delim == ";"
        frame = ar.read_csv(str(path), delimiter=delim)
        assert frame.columns == ["a", "b", "c"]

    def test_sniff_empty_file_raises(self, tmp_path):
        path = self.write_csv(tmp_path, "empty.csv", "")
        with pytest.raises(ar.CsvReadError, match="CSV file is empty"):
            ar.sniff_delimiter(str(path))

    def test_sniff_binary_file_raises(self, tmp_path):
        path = self.write_csv(tmp_path, "binary.csv", b"\x00\x01\x02\x03\x04")
        with pytest.raises(ar.CsvReadError, match="NUL bytes"):
            ar.sniff_delimiter(str(path))

    def test_detected_delimiter_correct_values(self, tmp_path):
        path = self.write_csv(tmp_path, "correct.csv", "a;b;c\n1;2;3\n4;5;6\n")
        delim = ar.sniff_delimiter(str(path))
        assert delim == ";"
        frame = ar.read_csv(str(path), delimiter=delim)
        assert frame.columns == ["a", "b", "c"]
        assert frame.shape == (2, 3)

    def test_works_with_scan_csv(self, tmp_path):
        path = self.write_csv(tmp_path, "scan.csv", "a;b;c\n1;2;3\n")
        delim = ar.sniff_delimiter(str(path))
        assert delim == ";"
        schema = ar.scan_csv(str(path), delimiter=delim)
        assert list(schema.keys()) == ["a", "b", "c"]

    def test_explicit_delimiter_overrides_sniff(self, tmp_path):
        path = self.write_csv(tmp_path, "explicit.csv", "a;b;c\n1;2;3\n")
        delim = ar.sniff_delimiter(str(path))
        assert delim == ";"
        frame = ar.read_csv(str(path), delimiter=",")
        assert len(frame.columns) == 1

    def test_decimal_separator_interaction(self, tmp_path):
        path = self.write_csv(tmp_path, "decimal.csv", "a;b\n1,5;2,6\n")
        delim = ar.sniff_delimiter(str(path))
        assert delim == ";"
        frame = ar.read_csv(str(path), delimiter=delim, decimal_separator=",")
        assert frame.columns == ["a", "b"]

    def test_raises_on_mixed_delimiters_consistent_counts(self, tmp_path):
        """sniff_delimiter raises ValueError when delimiter is ambiguous (mixed delimiters, consistent counts)."""
        path = tmp_path / "ambiguous.csv"
        path.write_text("a,b,c\nd;e;f\n")
        with pytest.raises(
            ValueError, match="Could not determine CSV delimiter"
        ):
            ar.sniff_delimiter(str(path))
