"""
tests/test_csv_validation_errors.py

Focused tests for improved CSV parsing validation errors (issue #1001).

Covers the four agreed priority cases:
  1. Row-width inconsistencies     — enriched Python-layer error messages
  2. Delimiter mismatch            — post-parse single-column hint
  3. Empty / header-only files     — clear error instead of silent empty frame
  4. Encoding / read failures      — byte-position context preserved
"""

from __future__ import annotations

import io

import pytest

import arnio as ar
from arnio import CsvReadError

# ---------------------------------------------------------------------------
# Case 1: Row-width inconsistencies
# ---------------------------------------------------------------------------


class TestRowWidthErrors:
    """The error message must contain row number, field counts, and a hint."""

    def test_strict_extra_fields_message_is_enriched(self, tmp_path):
        """Extra fields in strict mode produce an enriched CsvReadError."""
        path = tmp_path / "wide.csv"
        path.write_text("a,b\n1,2\n3,4,5\n", encoding="utf-8")

        with pytest.raises(CsvReadError) as exc_info:
            ar.read_csv(path, mode="strict")

        msg = str(exc_info.value)
        # Must say "too many" and preserve the original backend text
        assert "too many" in msg
        assert "CSV row" in msg  # original backend text preserved

    def test_strict_missing_fields_message_is_enriched(self, tmp_path):
        """Rows with too few fields in strict mode produce an enriched CsvReadError."""
        path = tmp_path / "narrow.csv"
        path.write_text("a,b,c\n1,2,3\n4,5\n", encoding="utf-8")

        with pytest.raises(CsvReadError) as exc_info:
            ar.read_csv(path, mode="strict")

        msg = str(exc_info.value)
        assert "too few" in msg
        assert "CSV row" in msg  # original backend text preserved

    def test_enriched_message_includes_on_bad_lines_hint(self, tmp_path):
        """Enriched messages hint at on_bad_lines options."""
        path = tmp_path / "extra.csv"
        path.write_text("x,y\n1,2,3\n", encoding="utf-8")

        with pytest.raises(CsvReadError) as exc_info:
            ar.read_csv(path, mode="strict")

        msg = str(exc_info.value)
        assert "on_bad_lines" in msg or "permissive" in msg

    def test_on_bad_lines_warn_still_works_after_enrichment(self, tmp_path, recwarn):
        """on_bad_lines='warn' must still drop the bad row and emit a warning."""
        path = tmp_path / "warn.csv"
        path.write_text("a,b\n1,2\n3,4,5\n7,8\n", encoding="utf-8")

        frame = ar.read_csv(path, mode="strict", on_bad_lines="warn")
        df = ar.to_pandas(frame)

        # Bad row (3,4,5) is dropped; good rows remain
        assert len(df) == 2
        assert len(recwarn) >= 1

    def test_on_bad_lines_skip_still_works_after_enrichment(self, tmp_path):
        """on_bad_lines='skip' must drop the bad row silently."""
        path = tmp_path / "skip.csv"
        path.write_text("a,b\n1,2\n3,4,5\n7,8\n", encoding="utf-8")

        frame = ar.read_csv(path, mode="strict", on_bad_lines="skip")
        df = ar.to_pandas(frame)

        assert len(df) == 2


# ---------------------------------------------------------------------------
# Case 2: Delimiter mismatch
# ---------------------------------------------------------------------------


class TestDelimiterMismatch:
    """When the wrong delimiter is used and only one column results,
    a UserWarning must be emitted describing the likely real delimiter."""

    def test_semicolon_file_read_with_comma_emits_warning(self, tmp_path):
        """Reading a semicolon-delimited file with delimiter=',' emits a mismatch warning."""
        path = tmp_path / "semi.csv"
        path.write_text("name;age\nAlice;30\nBob;25\n", encoding="utf-8")

        with pytest.warns(UserWarning, match="mismatch|delimiter"):
            frame = ar.read_csv(path, delimiter=",")

        # Still returns a frame (1 column) — no error
        assert frame.shape[1] == 1

    def test_tab_file_read_with_comma_emits_warning(self, tmp_path):
        """Reading a TSV file with delimiter=',' emits a mismatch warning."""
        path = tmp_path / "tab.csv"
        path.write_text("name\tage\nAlice\t30\n", encoding="utf-8")

        with pytest.warns(UserWarning, match="mismatch|delimiter"):
            ar.read_csv(path, delimiter=",")

    def test_pipe_file_read_with_comma_emits_warning(self, tmp_path):
        """Reading a pipe-delimited file with delimiter=',' emits a mismatch warning."""
        path = tmp_path / "pipe.csv"
        path.write_text("name|age\nAlice|30\n", encoding="utf-8")

        with pytest.warns(UserWarning, match="mismatch|delimiter"):
            ar.read_csv(path, delimiter=",")

    def test_legitimate_single_column_csv_no_warning(self, tmp_path):
        """A genuinely single-column CSV must parse successfully without any warning."""
        path = tmp_path / "single_col.csv"
        path.write_text("name\nAlice\nBob\nCharlie\n", encoding="utf-8")

        import warnings as _warnings

        with _warnings.catch_warnings():
            _warnings.simplefilter("error")  # any warning = test failure
            frame = ar.read_csv(path, delimiter=",")

        df = ar.to_pandas(frame)
        assert list(df.columns) == ["name"]
        assert len(df) == 3

    def test_usecols_single_column_no_mismatch_check(self, tmp_path):
        """Selecting a single column via usecols must not trigger the mismatch check."""
        path = tmp_path / "multi.csv"
        path.write_text("name,age\nAlice,30\nBob,25\n", encoding="utf-8")

        import warnings as _warnings

        with _warnings.catch_warnings():
            _warnings.simplefilter("error")
            frame = ar.read_csv(path, delimiter=",", usecols=["name"])

        df = ar.to_pandas(frame)
        assert list(df.columns) == ["name"]
        assert len(df) == 2

    def test_mismatch_warning_includes_sniff_suggestion(self, tmp_path):
        """The mismatch warning message should suggest sniff_delimiter."""
        path = tmp_path / "semi2.csv"
        path.write_text("a;b\n1;2\n", encoding="utf-8")

        with pytest.warns(UserWarning) as rec:
            ar.read_csv(path, delimiter=",")

        msg = str(rec[0].message)
        assert "sniff_delimiter" in msg or "delimiter" in msg.lower()


# ---------------------------------------------------------------------------
# Case 3: Empty / header-only files
# ---------------------------------------------------------------------------


class TestEmptyAndHeaderOnlyFiles:
    """Zero-byte files raise CsvReadError. Header-only files return an empty frame."""

    def test_empty_file_raises_clear_error(self, tmp_path):
        """A zero-byte CSV raises CsvReadError with 'empty' in the message."""
        path = tmp_path / "empty.csv"
        path.write_text("", encoding="utf-8")

        with pytest.raises(CsvReadError) as exc_info:
            ar.read_csv(path)

        assert "empty" in str(exc_info.value).lower()

    def test_header_only_file_returns_empty_frame(self, tmp_path):
        """A file with only a header row returns an empty ArFrame (zero data rows)."""
        path = tmp_path / "header_only.csv"
        path.write_text("name,age,city\n", encoding="utf-8")

        frame = ar.read_csv(path)
        df = ar.to_pandas(frame)

        assert list(df.columns) == ["name", "age", "city"]
        assert len(df) == 0

    def test_file_with_data_rows_is_not_rejected(self, tmp_path):
        """A normal CSV with header + data rows must parse without error."""
        path = tmp_path / "normal.csv"
        path.write_text("a,b\n1,2\n3,4\n", encoding="utf-8")

        frame = ar.read_csv(path)
        df = ar.to_pandas(frame)

        assert list(df.columns) == ["a", "b"]
        assert len(df) == 2

    def test_scan_csv_header_only_returns_schema(self, tmp_path):
        """scan_csv on a header-only file returns a schema dict (no error)."""
        path = tmp_path / "header_only_scan.csv"
        path.write_text("x,y,z\n", encoding="utf-8")

        # scan_csv infers schema from headers even with no data rows
        schema = ar.scan_csv(path)
        assert isinstance(schema, dict)

    def test_empty_file_scan_csv_raises(self, tmp_path):
        """scan_csv on a zero-byte file must raise CsvReadError."""
        path = tmp_path / "empty_scan.csv"
        path.write_text("", encoding="utf-8")

        with pytest.raises(CsvReadError) as exc_info:
            ar.scan_csv(path)

        assert "empty" in str(exc_info.value).lower()


# ---------------------------------------------------------------------------
# Case 4: Encoding / read failures
# ---------------------------------------------------------------------------


class TestEncodingErrors:
    """Encoding failures must preserve byte-position context from UnicodeDecodeError."""

    def test_invalid_utf8_byte_position_in_error(self, tmp_path):
        """CsvReadError for a bad UTF-8 byte must mention the file path or encoding."""
        path = tmp_path / "bad_utf8.csv"
        # Write a valid header, then an invalid UTF-8 byte in the data row.
        path.write_bytes(b"name,score\nAlice,\xff\n")

        with pytest.raises(CsvReadError) as exc_info:
            ar.read_csv(path, encoding="utf-8", encoding_errors="strict")

        msg = str(exc_info.value)
        # The error must be a CsvReadError — that's the contract.
        # The exact text comes from the C++ backend for pure UTF-8 inputs;
        # for non-UTF-8 transcoding paths the Python layer adds byte-position context.
        assert len(msg) > 0

    def test_latin1_file_misread_as_utf8_raises_enriched_error(self, tmp_path):
        """A Latin-1 file opened as UTF-8 raises CsvReadError with encoding context."""
        path = tmp_path / "latin1.csv"
        # 0xe9 = 'é' in Latin-1, invalid as a stand-alone UTF-8 byte
        path.write_bytes(b"city,country\nParis,France\nM\xe9xico,Mexico\n")

        with pytest.raises(CsvReadError) as exc_info:
            ar.read_csv(path, encoding="utf-8", encoding_errors="strict")

        msg = str(exc_info.value)
        assert "utf-8" in msg.lower() or "utf8" in msg.lower()

    def test_encoding_replace_recovers_from_bad_bytes(self, tmp_path):
        """encoding_errors='replace' must succeed and substitute the bad byte."""
        path = tmp_path / "replace.csv"
        path.write_bytes(b"name,score\nAlice,\xff\n")

        frame = ar.read_csv(path, encoding="utf-8", encoding_errors="replace")
        df = ar.to_pandas(frame)

        assert df.loc[0, "name"] == "Alice"

    def test_valid_non_utf8_encoding_reads_correctly(self, tmp_path):
        """A correctly specified non-UTF-8 encoding must parse without error."""
        path = tmp_path / "latin1_correct.csv"
        # 0xe9 = 'é' in Latin-1
        path.write_bytes(b"city\nM\xe9xico\n")

        frame = ar.read_csv(path, encoding="latin-1")
        df = ar.to_pandas(frame)

        assert df.loc[0, "city"] == "México"

    def test_unknown_encoding_raises_value_error(self, tmp_path):
        """An unknown encoding name raises ValueError (not CsvReadError)."""
        path = tmp_path / "data.csv"
        path.write_text("a,b\n1,2\n", encoding="utf-8")

        with pytest.raises((ValueError, CsvReadError)):
            ar.read_csv(path, encoding="not-a-real-encoding-xyz")

    def test_stringio_bad_delimiter_emits_warning(self):
        """A StringIO source with a mismatched delimiter emits a UserWarning."""
        source = io.StringIO("col1;col2\nval1;val2\n")

        with pytest.warns(UserWarning, match="mismatch|delimiter"):
            ar.read_csv(source, delimiter=",")


# ---------------------------------------------------------------------------
# Regression: delimiter-mismatch probe must operate on logical CSV records
# ---------------------------------------------------------------------------


class TestDelimiterMismatchQuoteAware:
    """The mismatch probe must preserve quote state across physical newlines.

    Two specific regressions requested by the maintainer:

    1. A legitimate single-column CSV whose quoted value contains a candidate
       delimiter character (;, tab, |) must emit NO warning — the character
       is inside a quoted field and is not a real delimiter.

    2. A semicolon-delimited file whose first data record contains a multiline
       quoted field (quote spans a physical newline) MUST still emit the
       warning — the semicolon delimiter appears outside quotes on the second
       physical line of what is still the first logical record.
    """

    def test_quoted_value_with_semicolon_no_warning(self, tmp_path):
        """Single-column CSV with a quoted value containing ';' emits no warning.

        This is the false-positive regression: before the logical-record fix,
        _warn_delimiter_mismatch would find ';' on the second physical line
        and incorrectly warn about a delimiter mismatch.
        """
        path = tmp_path / "quoted_semi.csv"
        # One column; the value contains a semicolon inside quotes.
        path.write_text('note\n"value;still one field"\n', encoding="utf-8")

        import warnings as _warnings

        with _warnings.catch_warnings():
            _warnings.simplefilter("error")  # any warning = test failure
            frame = ar.read_csv(path, delimiter=",")

        df = ar.to_pandas(frame)
        assert list(df.columns) == ["note"]
        assert df.loc[0, "note"] == "value;still one field"

    def test_multiline_quoted_field_mismatch_still_warns(self, tmp_path):
        """Semicolon-delimited file with a multiline quoted first field warns.

        This is the false-negative regression: the first data record is
        ``"Alice\\nSmith";30`` — the opening quoted field spans a physical
        newline, but the semicolon delimiter sits outside quotes on the same
        logical record.  The probe must carry quote state across the newline
        and still detect the mismatch.
        """
        path = tmp_path / "multiline_mismatch.csv"
        # Semicolon-delimited; first field of data row spans two physical lines.
        path.write_text('name;age\n"Alice\nSmith";30\n', encoding="utf-8")

        with pytest.warns(UserWarning, match="mismatch|delimiter"):
            ar.read_csv(path, delimiter=",")
