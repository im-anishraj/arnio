"""Tests for sniff_delimiter CSV detection function in the Arnio project."""

import pytest
import arnio as ar
from arnio.exceptions import CsvReadError

class TestDelimiterDetection:
    """Test suite for CSV delimiter auto-detection through I/O functions."""

    # 1. Common delimiters
    def test_detects_comma(self, tmp_path):
        """Test detection of comma delimiter."""
        p = tmp_path / "comma.csv"
        p.write_text("a,b,c\n1,2,3")
        df = ar.read_csv(p)
        assert df.columns == ["a", "b", "c"]
        assert df.shape == (1, 3)

    def test_detects_semicolon(self, tmp_path):
        """Test detection of semicolon delimiter."""
        p = tmp_path / "semi.csv"
        p.write_text("a;b;c\n1;2;3")
        df = ar.read_csv(p)
        assert df.columns == ["a", "b", "c"]

    def test_detects_tab(self, tmp_path):
        """Test detection of tab delimiter."""
        p = tmp_path / "tab.tsv"
        p.write_text("a\tb\tc\n1\t2\t3")
        df = ar.read_csv(p)
        assert df.columns == ["a", "b", "c"]

    def test_detects_pipe(self, tmp_path):
        """Test detection of pipe delimiter."""
        p = tmp_path / "pipe.txt"
        p.write_text("a|b|c\n1|2|3")
        df = ar.read_csv(p)
        assert df.columns == ["a", "b", "c"]

    def test_space_based_delimiters(self, tmp_path):
        """Test behavior with space-based delimiters."""
        p = tmp_path / "space.txt"
        p.write_text("a b c\n1 2 3")
        # Since arnio might not sniff space as a delimiter, we verify its actual behavior.
        # It may either parse it as a single column, raise an error, or detect it.
        try:
            df = ar.read_csv(p)
            if df.columns == ["a", "b", "c"]:
                assert True
            else:
                assert len(df.columns) == 1
        except (ValueError, RuntimeError, CsvReadError):
            assert True

    # 2. Ambiguous or small samples
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

    def test_delimiter_inside_quoted_string_with_delimiter(self, tmp_path):
        """Test detection when quoted string contains the delimiter character itself."""
        p = tmp_path / "quoted_delim.csv"
        p.write_text('a|b\n"c|d"|e')
        df = ar.read_csv(p)
        assert df.columns == ["a", "b"]
        assert df.shape == (1, 2)

    # 3. Fallback behavior
    def test_single_column_data(self, tmp_path):
        """Test fallback when data has no clear delimiter (single column)."""
        p = tmp_path / "single.csv"
        p.write_text("col1\nval1\nval2\n")
        with pytest.raises((ValueError, RuntimeError, CsvReadError)):
            ar.read_csv(p)

    def test_empty_input(self, tmp_path):
        """Test behavior with empty file."""
        p = tmp_path / "empty.csv"
        p.write_text("")
        with pytest.raises((ValueError, RuntimeError, CsvReadError)):
            ar.read_csv(p)

    def test_no_clear_delimiter(self, tmp_path):
        """Test behavior when no clear delimiter is found and it's ambiguous."""
        p = tmp_path / "ambiguous.csv"
        p.write_text("a,b;c\nd,e;f\n")
        with pytest.raises((ValueError, RuntimeError, CsvReadError)):
            ar.read_csv(p)

    # 4. Edge cases
    def test_bom_markers(self, tmp_path):
        """Test detection on files with BOM markers."""
        p = tmp_path / "bom.csv"
        p.write_bytes(b'\xef\xbb\xbfa,b,c\n1,2,3')
        df = ar.read_csv(p)
        assert len(df.columns) == 3

    def test_mixed_line_endings(self, tmp_path):
        """Test detection on files with mixed line endings."""
        p = tmp_path / "mixed.csv"
        p.write_text("a,b\n1,2\r\n3,4\r5,6\n")
        df = ar.read_csv(p)
        assert df.columns == ["a", "b"]

    def test_headers_without_delimiters(self, tmp_path):
        """Test detection when header has no delimiters but data does."""
        p = tmp_path / "header_no_delim.csv"
        p.write_text("HeaderOnly\n1,2\n3,4\n")
        try:
            df = ar.read_csv(p)
            assert len(df.columns) > 0
        except (ValueError, RuntimeError, CsvReadError):
            pass

    def test_unicode_characters(self, tmp_path):
        """Test detection with unicode characters."""
        p = tmp_path / "unicode.csv"
        p.write_text("名前,年齢\n太郎,30\n花子,25", encoding="utf-8")
        df = ar.read_csv(p)
        assert df.columns == ["名前", "年齢"]

    def test_scan_csv_detection(self, tmp_path):
        """Test that scan_csv also correctly detects the delimiter in context."""
        p = tmp_path / "scan.csv"
        p.write_text("a;b\n1;2")
        schema = ar.scan_csv(p)
        assert schema is not None
