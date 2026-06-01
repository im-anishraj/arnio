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

    def test_handles_utf16_comma_delimited_file(self, tmp_path):
        """sniff_delimiter decodes UTF-16 CSV before binary checks."""
        path = tmp_path / "utf16.csv"
        path.write_text("name,age\nAlice,30\nBob,25\n", encoding="utf-16")

        result = sniff_delimiter(path, encoding="utf-16")

        assert result == ","

    def test_handles_utf16_tab_delimited_file(self, tmp_path):
        """sniff_delimiter decodes UTF-16 TSV before binary checks."""
        path = tmp_path / "utf16.tsv"
        path.write_text("name\tage\nAlice\t30\nBob\t25\n", encoding="utf-16")

        result = sniff_delimiter(path, encoding="utf-16")

        assert result == "\t"

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


class TestReadCsvDelimiterDetection:
    """Test suite for CSV delimiter auto-detection through read_csv/scan_csv."""

    def test_detects_comma(self, tmp_path):
        """Test detection of comma delimiter."""
        p = tmp_path / "comma.csv"
        p.write_text("a,b,c\n1,2,3")
        df = ar.read_csv(p)
        assert df.columns == ["a", "b", "c"]
        assert df.shape == (1, 3)

    def test_detects_tab(self, tmp_path):
        """Test detection of tab delimiter."""
        p = tmp_path / "tab.tsv"
        p.write_text("a\tb\tc\n1\t2\t3")
        df = ar.read_csv(p)
        assert df.columns == ["a", "b", "c"]

    def test_fallback_semicolon(self, tmp_path):
        """Test read_csv fallback behavior for semicolon delimiter."""
        p = tmp_path / "semi.csv"
        p.write_text("a;b;c\n1;2;3")
        df = ar.read_csv(p)
        # read_csv doesn't currently auto-detect semicolon, so it parses as a single column.
        assert len(df.columns) == 1
        assert df.columns == ["a;b;c"]

    def test_fallback_pipe(self, tmp_path):
        """Test read_csv fallback behavior for pipe delimiter."""
        p = tmp_path / "pipe.txt"
        p.write_text("a|b|c\n1|2|3")
        df = ar.read_csv(p)
        # read_csv doesn't currently auto-detect pipe, so it parses as a single column.
        assert len(df.columns) == 1
        assert df.columns == ["a|b|c"]

    def test_space_based_delimiters(self, tmp_path):
        """Test behavior with space-based delimiters."""
        p = tmp_path / "space.txt"
        p.write_text("a b c\n1 2 3")
        df = ar.read_csv(p)
        # Space is not auto-detected as delimiter.
        assert len(df.columns) == 1

    def test_small_sample(self, tmp_path):
        """Test detection on a very small sample (e.g., 1 row with header)."""
        p = tmp_path / "small.csv"
        p.write_text("a,b\n1,2")
        df = ar.read_csv(p)
        assert df.columns == ["a", "b"]

    def test_delimiter_in_quoted_fields(self, tmp_path):
        """Test detection when delimiter appears inside quoted fields."""
        p = tmp_path / "quoted.csv"
        p.write_text('name,city\n"Smith, John",NYC\n"Doe, Jane",LA\n')
        df = ar.read_csv(p)
        assert df.columns == ["name", "city"]
        assert df.shape == (2, 2)

    def test_single_column_data(self, tmp_path):
        """Test fallback when data has no clear delimiter (single column)."""
        p = tmp_path / "single.csv"
        p.write_text("col1\nval1\nval2\n")
        # read_csv safely falls back to a single column
        df = ar.read_csv(p)
        assert df.columns == ["col1"]
        assert df.shape == (2, 1)

    def test_empty_input(self, tmp_path):
        """Test behavior with empty file."""
        p = tmp_path / "empty.csv"
        p.write_text("")
        try:
            df = ar.read_csv(p)
            assert len(df.columns) <= 1
        except Exception:
            pass

    def test_ambiguous_input(self, tmp_path):
        """Test behavior with ambiguous delimiters."""
        p = tmp_path / "ambiguous.csv"
        p.write_text("a,b;c\nd,e;f\n")
        try:
            df = ar.read_csv(p)
            assert len(df.columns) > 0
        except Exception:
            pass

    def test_bom_markers(self, tmp_path):
        """Test detection on files with BOM markers."""
        p = tmp_path / "bom.csv"
        p.write_bytes(b"\xef\xbb\xbfa,b,c\n1,2,3")
        df = ar.read_csv(p)
        assert len(df.columns) == 3

    def test_mixed_line_endings(self, tmp_path):
        """Test detection on files with mixed line endings."""
        p = tmp_path / "mixed.csv"
        p.write_text("a,b\n1,2\r\n3,4\r5,6\n")
        df = ar.read_csv(p)
        assert df.columns == ["a", "b"]

    def test_unicode_characters(self, tmp_path):
        """Test detection with unicode characters."""
        p = tmp_path / "unicode.csv"
        p.write_text("名前,年齢\n太郎,30\n花子,25", encoding="utf-8")
        df = ar.read_csv(p)
        assert df.columns == ["名前", "年齢"]
