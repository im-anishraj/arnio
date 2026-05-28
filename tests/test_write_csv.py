"""Tests for write_csv functionality."""

from pathlib import Path

import pandas as pd
import pytest

import arnio as ar


class TestWriteCsv:
    def test_basic_write(self, tmp_path, sample_csv):
        frame = ar.read_csv(sample_csv)
        out = str(tmp_path / "out.csv")
        ar.write_csv(frame, out)
        assert Path(out).exists()

    def test_round_trip(self, tmp_path, sample_csv):
        frame = ar.read_csv(sample_csv)
        out = str(tmp_path / "out.csv")
        ar.write_csv(frame, out)
        frame2 = ar.read_csv(out)
        df1 = ar.to_pandas(frame)
        df2 = ar.to_pandas(frame2)
        pd.testing.assert_frame_equal(df1, df2)

    def test_quotes_escaped(self, tmp_path):
        frame = ar.from_pandas(pd.DataFrame({"name": ['say "hello"', "normal"]}))
        out = str(tmp_path / "quoted.csv")
        ar.write_csv(frame, out)
        frame2 = ar.read_csv(out)
        df = ar.to_pandas(frame2)
        assert df["name"].iloc[0] == 'say "hello"'

    def test_comma_in_field(self, tmp_path):
        frame = ar.from_pandas(pd.DataFrame({"name": ["Smith, John", "Jane"]}))
        out = str(tmp_path / "comma.csv")
        ar.write_csv(frame, out)
        frame2 = ar.read_csv(out)
        df = ar.to_pandas(frame2)
        assert df["name"].iloc[0] == "Smith, John"

    def test_write_no_header(self, tmp_path, sample_csv):
        frame = ar.read_csv(sample_csv)
        out = str(tmp_path / "noheader.csv")
        ar.write_csv(frame, out, write_header=False)
        content = Path(out).read_text()
        assert "name" not in content.splitlines()[0]

    def test_custom_delimiter(self, tmp_path):
        frame = ar.from_pandas(pd.DataFrame({"a": [1, 2], "b": ["x", "y"]}))
        out = str(tmp_path / "out.tsv")
        ar.write_csv(frame, out, delimiter="\t")
        content = Path(out).read_text()
        assert "\t" in content

    def test_unsupported_extension(self, tmp_path):
        frame = ar.from_pandas(pd.DataFrame({"a": [1]}))
        with pytest.raises(ValueError, match="Unsupported file format"):
            ar.write_csv(frame, str(tmp_path / "out.json"))

    def test_pathlike_input(self, tmp_path, sample_csv):
        frame = ar.read_csv(sample_csv)
        out = tmp_path / "out.csv"
        ar.write_csv(frame, out)
        assert out.exists()

    def test_high_precision_float_round_trip(self, tmp_path):
        frame = ar.from_pandas(pd.DataFrame({"val": [1.23456789012345678]}))
        out = str(tmp_path / "float.csv")
        ar.write_csv(frame, out)
        frame2 = ar.read_csv(out)
        df = ar.to_pandas(frame2)
        assert abs(df["val"].iloc[0] - 1.23456789012345678) < 1e-15

    def test_invalid_delimiter(self, tmp_path):
        frame = ar.from_pandas(pd.DataFrame({"a": [1]}))
        with pytest.raises(ValueError, match="delimiter must be a single character"):
            ar.write_csv(frame, str(tmp_path / "out.csv"), delimiter=",,")

    def test_non_string_delimiter_rejected(self, tmp_path):
        frame = ar.from_pandas(pd.DataFrame({"a": [1]}))
        with pytest.raises(TypeError, match="delimiter must be a string"):
            ar.write_csv(frame, str(tmp_path / "out.csv"), delimiter=1)

    @pytest.mark.parametrize("delimiter", ["\n", "\r"])
    def test_newline_delimiters_rejected(self, tmp_path, delimiter):
        frame = ar.from_pandas(pd.DataFrame({"a": [1]}))
        with pytest.raises(
            ValueError, match="delimiter must not be a newline character"
        ):
            ar.write_csv(frame, str(tmp_path / "out.csv"), delimiter=delimiter)

    def test_quote_character_delimiter_rejected(self, tmp_path):
        frame = ar.from_pandas(pd.DataFrame({"a": [1]}))
        with pytest.raises(
            ValueError, match="delimiter must not be the CSV quote character"
        ):
            ar.write_csv(frame, str(tmp_path / "out.csv"), delimiter='"')


class TestWriteCsvLineTerminatorBytes:
    """Raw-byte regression tests for line_terminator.

    These tests read the output file in binary mode and assert the exact bytes
    written.  They guard against platform newline translation (e.g. Windows
    text-mode expanding \\n to \\r\\n) and ensure the configured terminator is
    emitted verbatim on every OS.
    """

    def test_default_lf_writes_exact_lf_bytes(self, tmp_path):
        # Default line_terminator="\n" must produce LF bytes, not CRLF.
        frame = ar.from_pandas(pd.DataFrame({"a": [1, 2]}))
        out = tmp_path / "out.csv"
        ar.write_csv(frame, out)
        raw = out.read_bytes()
        # Header + 2 data rows, each terminated by a single LF.
        assert raw == b"a\n1\n2\n"
        assert b"\r" not in raw

    def test_crlf_terminator_writes_exact_crlf_bytes(self, tmp_path):
        # line_terminator="\r\n" must produce exactly CRLF, not CRCRLF.
        frame = ar.from_pandas(pd.DataFrame({"a": [1, 2]}))
        out = tmp_path / "out.csv"
        ar.write_csv(frame, out, line_terminator="\r\n")
        raw = out.read_bytes()
        assert raw == b"a\r\n1\r\n2\r\n"
        # No double-CR corruption.
        assert b"\r\r" not in raw

    def test_custom_terminator_writes_exact_bytes(self, tmp_path):
        # An arbitrary terminator (e.g. "|") must be written verbatim.
        frame = ar.from_pandas(pd.DataFrame({"x": [7]}))
        out = tmp_path / "out.csv"
        ar.write_csv(frame, out, line_terminator="|")
        raw = out.read_bytes()
        assert raw == b"x|7|"

    def test_empty_line_terminator_rejected(self, tmp_path):
        frame = ar.from_pandas(pd.DataFrame({"a": [1, 2]}))
        with pytest.raises(ValueError, match="line_terminator must not be empty"):
            ar.write_csv(frame, tmp_path / "out.csv", line_terminator="")

    def test_non_string_line_terminator_rejected(self, tmp_path):
        frame = ar.from_pandas(pd.DataFrame({"a": [1, 2]}))
        with pytest.raises(TypeError, match="line_terminator must be a string"):
            ar.write_csv(frame, tmp_path / "out.csv", line_terminator=None)

    def test_quoted_multiline_field_round_trips(self, tmp_path):
        # A field containing an embedded newline must be quoted and survive a
        # write → read round-trip with the default LF terminator.
        frame = ar.from_pandas(pd.DataFrame({"note": ["line1\nline2", "plain"]}))
        out = tmp_path / "out.csv"
        ar.write_csv(frame, out)
        raw = out.read_bytes()
        # The embedded newline lives inside quotes; the row terminator is the
        # bare LF that follows the closing quote.
        assert b'"line1\nline2"' in raw
        # Round-trip: values survive a read back.
        frame2 = ar.read_csv(out)
        df = ar.to_pandas(frame2)
        assert df["note"].iloc[0] == "line1\nline2"
        assert df["note"].iloc[1] == "plain"


class TestBooleanOptionValidation:
    """Tests for strict bool validation on has_header, trim_headers, write_header."""

    # --- write_csv: write_header ---

    def test_write_header_none_rejected(self, tmp_path):
        frame = ar.from_pandas(pd.DataFrame({"a": [1]}))
        with pytest.raises(TypeError, match="write_header"):
            ar.write_csv(frame, str(tmp_path / "out.csv"), write_header=None)

    def test_write_header_int_zero_rejected(self, tmp_path):
        frame = ar.from_pandas(pd.DataFrame({"a": [1]}))
        with pytest.raises(TypeError, match="write_header"):
            ar.write_csv(frame, str(tmp_path / "out.csv"), write_header=0)

    def test_write_header_int_one_rejected(self, tmp_path):
        frame = ar.from_pandas(pd.DataFrame({"a": [1]}))
        with pytest.raises(TypeError, match="write_header"):
            ar.write_csv(frame, str(tmp_path / "out.csv"), write_header=1)

    def test_write_header_string_rejected(self, tmp_path):
        frame = ar.from_pandas(pd.DataFrame({"a": [1]}))
        with pytest.raises(TypeError, match="write_header"):
            ar.write_csv(frame, str(tmp_path / "out.csv"), write_header="true")

    def test_write_header_true_accepted(self, tmp_path):
        frame = ar.from_pandas(pd.DataFrame({"a": [1]}))
        ar.write_csv(frame, str(tmp_path / "out.csv"), write_header=True)

    def test_write_header_false_accepted(self, tmp_path):
        frame = ar.from_pandas(pd.DataFrame({"a": [1]}))
        ar.write_csv(frame, str(tmp_path / "out.csv"), write_header=False)

    # --- read_csv: has_header and trim_headers ---

    def test_has_header_none_rejected(self, tmp_path):
        p = tmp_path / "f.csv"
        p.write_text("a,b\n1,2\n")
        with pytest.raises(TypeError, match="has_header"):
            ar.read_csv(str(p), has_header=None)

    def test_has_header_int_rejected(self, tmp_path):
        p = tmp_path / "f.csv"
        p.write_text("a,b\n1,2\n")
        with pytest.raises(TypeError, match="has_header"):
            ar.read_csv(str(p), has_header=0)

    def test_has_header_string_rejected(self, tmp_path):
        p = tmp_path / "f.csv"
        p.write_text("a,b\n1,2\n")
        with pytest.raises(TypeError, match="has_header"):
            ar.read_csv(str(p), has_header="yes")

    def test_trim_headers_none_rejected(self, tmp_path):
        p = tmp_path / "f.csv"
        p.write_text("a,b\n1,2\n")
        with pytest.raises(TypeError, match="trim_headers"):
            ar.read_csv(str(p), trim_headers=None)

    def test_trim_headers_int_rejected(self, tmp_path):
        p = tmp_path / "f.csv"
        p.write_text("a,b\n1,2\n")
        with pytest.raises(TypeError, match="trim_headers"):
            ar.read_csv(str(p), trim_headers=1)

    def test_has_header_true_accepted(self, tmp_path):
        p = tmp_path / "f.csv"
        p.write_text("a,b\n1,2\n")
        frame = ar.read_csv(str(p), has_header=True)
        assert frame is not None

    def test_has_header_false_accepted(self, tmp_path):
        p = tmp_path / "f.csv"
        p.write_text("1,2\n3,4\n")
        frame = ar.read_csv(str(p), has_header=False)
        assert frame is not None

    # --- scan_csv: trim_headers ---

    def test_scan_csv_trim_headers_none_rejected(self, tmp_path):
        p = tmp_path / "f.csv"
        p.write_text("a,b\n1,2\n")
        with pytest.raises(TypeError, match="trim_headers"):
            ar.scan_csv(str(p), trim_headers=None)

    def test_scan_csv_trim_headers_int_rejected(self, tmp_path):
        p = tmp_path / "f.csv"
        p.write_text("a,b\n1,2\n")
        with pytest.raises(TypeError, match="trim_headers"):
            ar.scan_csv(str(p), trim_headers=1)

    def test_scan_csv_trim_headers_string_rejected(self, tmp_path):
        p = tmp_path / "f.csv"
        p.write_text("a,b\n1,2\n")
        with pytest.raises(TypeError, match="trim_headers"):
            ar.scan_csv(str(p), trim_headers="yes")

    def test_scan_csv_trim_headers_true_accepted(self, tmp_path):
        p = tmp_path / "f.csv"
        p.write_text("a,b\n1,2\n")
        result = ar.scan_csv(str(p), trim_headers=True)
        assert result is not None

    def test_scan_csv_trim_headers_false_accepted(self, tmp_path):
        p = tmp_path / "f.csv"
        p.write_text("a,b\n1,2\n")
        result = ar.scan_csv(str(p), trim_headers=False)
        assert result is not None


class TestWriteCsvDelimiterValidation:
    """Delimiter type validation: non-string values must be rejected."""

    @pytest.mark.parametrize("delimiter", [1, None, []])
    def test_non_string_delimiter_rejected(self, tmp_path, delimiter):
        frame = ar.from_pandas(pd.DataFrame({"a": [1]}))
        with pytest.raises(TypeError, match="delimiter must be a string"):
            ar.write_csv(frame, str(tmp_path / "out.csv"), delimiter=delimiter)


class TestWriteCsvDelimiterNewlineRejection:
    """Delimiter newline rejection: newline characters must not be used as delimiter."""

    @pytest.mark.parametrize("delimiter", ["\n", "\r"])
    def test_newline_delimiter_rejected(self, tmp_path, delimiter):
        frame = ar.from_pandas(pd.DataFrame({"a": [1]}))
        with pytest.raises(
            ValueError, match="delimiter must not be a newline character"
        ):
            ar.write_csv(frame, str(tmp_path / "out.csv"), delimiter=delimiter)


class TestWriteCsvQuoteCharValidation:
    """Quote-character validation: the CSV quote character must not be used as delimiter."""

    def test_quote_char_as_delimiter_rejected(self, tmp_path):
        frame = ar.from_pandas(pd.DataFrame({"a": [1]}))
        with pytest.raises(
            ValueError, match="delimiter must not be the CSV quote character"
        ):
            ar.write_csv(frame, str(tmp_path / "out.csv"), delimiter='"')


class TestWriteCsvControlCharValidation:
    """Control character validation: unsafe control characters must be rejected."""

    @pytest.mark.parametrize("delimiter", ["\0", "\x1f", "\x7f"])
    def test_control_character_delimiter_rejected(self, tmp_path, delimiter):
        frame = ar.from_pandas(pd.DataFrame({"a": [1]}))
        with pytest.raises(
            ValueError, match="delimiter must not be a control character"
        ):
            ar.write_csv(frame, str(tmp_path / "out.csv"), delimiter=delimiter)
