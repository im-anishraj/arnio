"""Tests for write_csv functionality."""

import os
from pathlib import Path

import pandas as pd
import pytest

import arnio as ar


@pytest.mark.parametrize(
    "bad_input",
    [
        object(),
        None,
        pd.DataFrame({"a": [1, 2]}),
    ],
)
def test_write_csv_invalid_frame(bad_input, tmp_path):
    with pytest.raises(TypeError, match="frame must be an ArFrame"):
        ar.write_csv(bad_input, tmp_path / "out.csv")


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

    def test_non_ascii_output_path_round_trip(self, tmp_path):
        frame = ar.from_pandas(
            pd.DataFrame({"city": ["Łódź", "東京"], "sales": [10, 20]})
        )
        out = tmp_path / "résumé_東京.csv"

        ar.write_csv(frame, str(out))

        assert out.exists()
        round_tripped = ar.to_pandas(ar.read_csv(str(out)))
        pd.testing.assert_frame_equal(round_tripped, ar.to_pandas(frame))

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

    @pytest.mark.parametrize(
        "delimiter",
        [
            pytest.param("\n", id="newline"),
            pytest.param("\r", id="carriage-return"),
            pytest.param("\0", id="NUL"),
            pytest.param('"', id="double-quote"),
        ],
    )
    def test_unsafe_delimiters_rejected(self, tmp_path, delimiter):
        frame = ar.from_pandas(pd.DataFrame({"a": [1]}))
        with pytest.raises(ValueError, match="delimiter"):
            ar.write_csv(frame, str(tmp_path / "out.csv"), delimiter=delimiter)


class TestWriteCsvFormulaEscaping:
    def test_default_preserves_formula_like_strings(self, tmp_path):
        frame = ar.from_pandas(
            pd.DataFrame(
                {
                    "text": ["=SUM(A1:A2)", "+cmd", "-not-a-number", "@user"],
                    "amount": [-10, 25, -3, 4],
                }
            )
        )
        out = tmp_path / "out.csv"

        ar.write_csv(frame, out)

        assert out.read_text(encoding="utf-8").splitlines() == [
            "text,amount",
            "=SUM(A1:A2),-10",
            "+cmd,25",
            "-not-a-number,-3",
            "@user,4",
        ]

    def test_escape_formulas_prefixes_string_cells_only(self, tmp_path):
        frame = ar.from_pandas(
            pd.DataFrame(
                {
                    "text": [
                        "=SUM(A1:A2)",
                        "+cmd",
                        "-not-a-number",
                        "@user",
                        "\tTabbed",
                    ],
                    "amount": [-10, 25, -3, 4, -8],
                }
            )
        )
        out = tmp_path / "out.csv"

        ar.write_csv(frame, out, escape_formulas=True)

        assert out.read_text(encoding="utf-8").splitlines() == [
            "text,amount",
            "'=SUM(A1:A2),-10",
            "'+cmd,25",
            "'-not-a-number,-3",
            "'@user,4",
            "'\tTabbed,-8",
        ]

    def test_escape_formulas_runs_before_csv_quoting(self, tmp_path):
        frame = ar.from_pandas(
            pd.DataFrame({"note": ['=HYPERLINK("http://example.test", "x")']})
        )
        out = tmp_path / "out.csv"

        ar.write_csv(frame, out, escape_formulas=True)

        assert (
            out.read_text(encoding="utf-8")
            == 'note\n"\'=HYPERLINK(""http://example.test"", ""x"")"\n'
        )

    def test_escape_formulas_does_not_modify_headers_nulls_or_empty_strings(
        self, tmp_path
    ):
        frame = ar.from_pandas(
            pd.DataFrame(
                {
                    "=header": ["", None, "safe"],
                    "value": ["=formula", None, ""],
                }
            )
        )
        out = tmp_path / "out.csv"

        ar.write_csv(frame, out, escape_formulas=True)

        assert out.read_text(encoding="utf-8").splitlines() == [
            "=header,value",
            ",'=formula",
            ",",
            "safe,",
        ]

    def test_escape_formulas_respects_delimiter_and_line_terminator(self, tmp_path):
        frame = ar.from_pandas(pd.DataFrame({"a": ["=x"], "b": ["safe"]}))
        out = tmp_path / "out.tsv"

        ar.write_csv(
            frame,
            out,
            delimiter="\t",
            line_terminator="\r\n",
            escape_formulas=True,
        )

        assert out.read_bytes() == b"a\tb\r\n'=x\tsafe\r\n"

    @pytest.mark.parametrize("value", [None, 1, "true"])
    def test_escape_formulas_rejects_non_bool(self, tmp_path, value):
        frame = ar.from_pandas(pd.DataFrame({"a": ["=x"]}))

        with pytest.raises(TypeError, match="escape_formulas"):
            ar.write_csv(frame, tmp_path / "out.csv", escape_formulas=value)


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
        # Arbitrary/custom terminators (e.g. "|") must be rejected.
        frame = ar.from_pandas(pd.DataFrame({"x": [7]}))
        out = tmp_path / "out.csv"
        with pytest.raises(ValueError, match="line_terminator must be one of"):
            ar.write_csv(frame, out, line_terminator="|")

    def test_r_terminator_writes_exact_r_bytes(self, tmp_path):
        # line_terminator="\r" must produce CR bytes verbatim.
        frame = ar.from_pandas(pd.DataFrame({"a": [1, 2]}))
        out = tmp_path / "out.csv"
        ar.write_csv(frame, out, line_terminator="\r")
        raw = out.read_bytes()
        assert raw == b"a\r1\r2\r"

    def test_arbitrary_strings_rejected(self, tmp_path):
        frame = ar.from_pandas(pd.DataFrame({"a": [1, 2]}))
        out = tmp_path / "out.csv"
        for term in ["END", "\n\0", "\0", "\r\r\n"]:
            with pytest.raises(ValueError, match="line_terminator must be one of"):
                ar.write_csv(frame, out, line_terminator=term)

    def test_empty_line_terminator_rejected(self, tmp_path):
        frame = ar.from_pandas(pd.DataFrame({"a": [1, 2]}))
        with pytest.raises(ValueError, match="line_terminator must be one of"):
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


def test_write_csv_rejects_bool_path(tmp_path):
    frame = ar.from_pandas(pd.DataFrame({"a": [1, 2, 3]}))
    with pytest.raises(TypeError, match="path must be a string"):
        ar.write_csv(frame, True)


def test_write_csv_rejects_int_path(tmp_path):
    frame = ar.from_pandas(pd.DataFrame({"a": [1, 2, 3]}))
    with pytest.raises(TypeError, match="path must be a string"):
        ar.write_csv(frame, 42)


class _BytesPathLike:
    def __init__(self, path: bytes) -> None:
        self._path = path

    def __fspath__(self) -> bytes:
        return self._path


def test_write_csv_accepts_bytes_path(tmp_path):
    frame = ar.from_pandas(pd.DataFrame({"a": [1, 2, 3]}))
    out = tmp_path / "out.csv"
    ar.write_csv(frame, os.fsencode(out))
    assert out.exists()


def test_write_csv_accepts_pathlike_bytes_path(tmp_path):
    frame = ar.from_pandas(pd.DataFrame({"a": [1, 2, 3]}))
    out = tmp_path / "out.csv"
    ar.write_csv(frame, _BytesPathLike(os.fsencode(out)))
    assert out.exists()


# ---------------------------------------------------------------------------
# encoding / encoding_errors tests
# ---------------------------------------------------------------------------


class TestWriteCsvEncoding:
    def _simple_frame(self):
        return ar.from_pandas(pd.DataFrame({"name": ["Alice", "Bob"], "score": [1, 2]}))

    def test_default_utf8_unchanged(self, tmp_path):
        """Default encoding="utf-8" writes correct content, existing behavior intact."""
        frame = self._simple_frame()
        out = tmp_path / "out.csv"
        ar.write_csv(frame, str(out))
        content = out.read_text(encoding="utf-8")
        assert "Alice" in content
        assert "Bob" in content

    def test_latin1_output_round_trips(self, tmp_path):
        """latin-1 encoded output round-trips back via read_csv(encoding="latin-1")."""
        frame = ar.from_pandas(pd.DataFrame({"city": ["München", "Zürich"]}))
        out = tmp_path / "out.csv"
        ar.write_csv(frame, str(out), encoding="latin-1")
        result = ar.read_csv(str(out), encoding="latin-1")
        df = ar.to_pandas(result)
        assert list(df["city"]) == ["München", "Zürich"]

    def test_non_default_line_terminator_through_transcoding(self, tmp_path):
        """Non-default line_terminator is preserved through the transcoding path."""
        frame = self._simple_frame()
        out = tmp_path / "out.csv"
        ar.write_csv(frame, str(out), encoding="latin-1", line_terminator="\r\n")
        raw = out.read_bytes()
        assert b"\r\n" in raw

    def test_escape_formulas_unchanged_through_transcoding(self, tmp_path):
        """escape_formulas output is identical through the transcoding path."""
        frame = ar.from_pandas(pd.DataFrame({"cmd": ["=SUM(A1)", "normal"]}))
        out_utf8 = tmp_path / "utf8.csv"
        out_latin1 = tmp_path / "latin1.csv"
        ar.write_csv(frame, str(out_utf8), escape_formulas=True)
        ar.write_csv(frame, str(out_latin1), encoding="latin-1", escape_formulas=True)
        assert out_utf8.read_text(encoding="utf-8") == out_latin1.read_text(
            encoding="latin-1"
        )

    def test_unencodable_character_strict_raises_valueerror(self, tmp_path):
        """Unencodable character with encoding_errors="strict" raises ValueError."""
        frame = ar.from_pandas(pd.DataFrame({"val": ["こんにちは"]}))
        out = tmp_path / "out.csv"
        with pytest.raises(ValueError, match="cannot be encoded"):
            ar.write_csv(frame, str(out), encoding="latin-1", encoding_errors="strict")

    def test_unencodable_character_replace_writes_file(self, tmp_path):
        """encoding_errors="replace" writes replacement characters instead of raising."""
        frame = ar.from_pandas(pd.DataFrame({"val": ["こんにちは"]}))
        out = tmp_path / "out.csv"
        ar.write_csv(frame, str(out), encoding="latin-1", encoding_errors="replace")
        assert out.exists()
        content = out.read_text(encoding="latin-1")
        assert "?" in content  # replacement character

    def test_encoding_non_string_raises_typeerror(self, tmp_path):
        """Non-string encoding raises TypeError before any file I/O."""
        frame = self._simple_frame()
        out = tmp_path / "out.csv"
        with pytest.raises(TypeError, match="encoding"):
            ar.write_csv(frame, str(out), encoding=123)

    def test_encoding_unknown_codec_raises_valueerror(self, tmp_path):
        """Unknown codec raises ValueError before any file I/O."""
        frame = self._simple_frame()
        out = tmp_path / "out.csv"
        with pytest.raises(ValueError, match="Unknown encoding"):
            ar.write_csv(frame, str(out), encoding="not-a-real-codec")

    def test_encoding_errors_non_string_raises_typeerror(self, tmp_path):
        """Non-string encoding_errors raises TypeError."""
        frame = self._simple_frame()
        out = tmp_path / "out.csv"
        with pytest.raises(TypeError, match="encoding_errors"):
            ar.write_csv(frame, str(out), encoding_errors=0)

    def test_encoding_errors_invalid_value_raises_valueerror(self, tmp_path):
        """Unrecognised encoding_errors value raises ValueError."""
        frame = self._simple_frame()
        out = tmp_path / "out.csv"
        with pytest.raises(ValueError, match="encoding_errors"):
            ar.write_csv(frame, str(out), encoding_errors="xmlcharrefreplace")

    def test_utf8_alias_uses_fast_path(self, tmp_path):
        """'utf8' (no hyphen) is recognised as UTF-8 and uses the fast path."""
        frame = self._simple_frame()
        out = tmp_path / "out.csv"
        ar.write_csv(frame, str(out), encoding="utf8")
        assert "Alice" in out.read_text(encoding="utf-8")

    def test_temp_file_cleaned_up_after_success(self, tmp_path):
        """No stray temp files remain in tmp_path after a successful transcoding write."""
        import glob

        frame = ar.from_pandas(pd.DataFrame({"city": ["München"]}))
        out = tmp_path / "out.csv"
        before = set(glob.glob(str(tmp_path / "*.csv")))
        ar.write_csv(frame, str(out), encoding="latin-1")
        after = set(glob.glob(str(tmp_path / "*.csv")))
        assert after - before == {str(out)}
