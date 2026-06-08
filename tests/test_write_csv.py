"""Tests for write_csv functionality."""

import os
from pathlib import Path

import pandas as pd
import pytest

import arnio as ar
import arnio.io


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
    def test_atomic_write_success(self, tmp_path, sample_csv):
        frame = ar.read_csv(sample_csv)
        out = str(tmp_path / "out.csv")
        ar.write_csv(frame, out)
        assert Path(out).exists()
        frame2 = ar.read_csv(out)
        pd.testing.assert_frame_equal(ar.to_pandas(frame), ar.to_pandas(frame2))

    def test_atomic_write_preserves_dest_on_failure(self, tmp_path, monkeypatch):
        frame = ar.from_pandas(pd.DataFrame({"a": [1, 2, 3]}))
        out = str(tmp_path / "out.csv")
        ar.write_csv(frame, out)
        original_content = Path(out).read_text()

        orig_write = arnio.io._CsvWriter.write
        def failing_write(self_, f, p):
            raise RuntimeError("Writer failed")

        monkeypatch.setattr(arnio.io._CsvWriter, "write", failing_write)

        with pytest.raises(RuntimeError, match="Writer failed"):
            ar.write_csv(frame, out)
        assert Path(out).read_text() == original_content

    def test_atomic_write_cleans_up_temp_on_failure(self, tmp_path, monkeypatch):
        frame = ar.from_pandas(pd.DataFrame({"a": [1, 2, 3]}))
        out = str(tmp_path / "out.csv")

        orig_write = arnio.io._CsvWriter.write
        def failing_write(self_, f, p):
            raise RuntimeError("Writer failed")

        monkeypatch.setattr(arnio.io._CsvWriter, "write", failing_write)

        with pytest.raises(RuntimeError, match="Writer failed"):
            ar.write_csv(frame, out)
        leftovers = [p for p in tmp_path.iterdir() if p.name.startswith(".out.csv")]
        assert len(leftovers) == 0

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

    def test_high_precision_float_writes_max_digits10(self, tmp_path):
        frame = ar.from_pandas(pd.DataFrame({"val": [1.2345678901234567]}))
        out = tmp_path / "float.csv"

        ar.write_csv(frame, out)

        assert out.read_text(encoding="utf-8") == "val\n1.2345678901234567\n"

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


class TestWriteCsvSafeForSpreadsheet:
    """Tests for the safe_for_spreadsheet CSV export mode (issue #681)."""

    def test_prefixes_formula_cells(self, tmp_path):
        """Dangerous formula triggers are prefixed with a single-quote."""
        frame = ar.from_pandas(
            pd.DataFrame(
                {
                    "data": [
                        "=SUM(A1:A10)",
                        "+cmd|'/C calc'!A0",
                        "-1+1",
                        "@SUM(A1)",
                    ]
                }
            )
        )
        out = tmp_path / "safe.csv"
        ar.write_csv(frame, out, safe_for_spreadsheet=True)
        frame2 = ar.read_csv(out)
        df = ar.to_pandas(frame2)
        assert df["data"].iloc[0] == "'=SUM(A1:A10)"
        assert df["data"].iloc[1] == "'+cmd|'/C calc'!A0"
        assert df["data"].iloc[2] == "'-1+1"
        assert df["data"].iloc[3] == "'@SUM(A1)"

    def test_leaves_non_dangerous_strings(self, tmp_path):
        """Normal strings without dangerous prefixes are unchanged."""
        frame = ar.from_pandas(pd.DataFrame({"name": ["Alice", "Bob", "hello world"]}))
        out = tmp_path / "safe.csv"
        ar.write_csv(frame, out, safe_for_spreadsheet=True)
        frame2 = ar.read_csv(out)
        df = ar.to_pandas(frame2)
        assert list(df["name"]) == ["Alice", "Bob", "hello world"]

    def test_skips_numeric_and_bool_columns(self, tmp_path):
        """Non-string columns (int, float, bool) are not modified."""
        frame = ar.from_pandas(
            pd.DataFrame({"val": [-1, 0, 1], "flag": [True, False, True]})
        )
        out = tmp_path / "safe.csv"
        ar.write_csv(frame, out, safe_for_spreadsheet=True)
        frame2 = ar.read_csv(out)
        df = ar.to_pandas(frame2)
        assert list(df["val"]) == [-1, 0, 1]
        assert list(df["flag"]) == [True, False, True]

    def test_handles_nulls(self, tmp_path):
        """Null values are not corrupted; dangerous cells are still prefixed."""
        frame = ar.from_pandas(pd.DataFrame({"data": ["=cmd", None, "safe"]}))
        out = tmp_path / "safe.csv"
        ar.write_csv(frame, out, safe_for_spreadsheet=True)
        raw = out.read_text()
        # The dangerous cell must be prefixed in the raw output
        assert "'=cmd" in raw
        # The safe cell must appear unchanged
        assert "safe" in raw

    def test_round_trip_content(self, tmp_path):
        """Written content is readable and matches expectations."""
        frame = ar.from_pandas(pd.DataFrame({"a": ["=1", "normal"], "b": [10, 20]}))
        out = tmp_path / "rt.csv"
        ar.write_csv(frame, out, safe_for_spreadsheet=True)
        raw = out.read_text()
        # The prefixed cell should appear as '=1 in the raw CSV
        assert "'=1" in raw
        assert "normal" in raw

    def test_default_is_false(self, tmp_path):
        """Default write_csv does NOT prefix dangerous strings."""
        frame = ar.from_pandas(pd.DataFrame({"data": ["=SUM(A1)"]}))
        out = tmp_path / "default.csv"
        ar.write_csv(frame, out)
        frame2 = ar.read_csv(out)
        df = ar.to_pandas(frame2)
        assert df["data"].iloc[0] == "=SUM(A1)"

    def test_tab_and_cr_prefixed(self, tmp_path):
        """Tab and carriage-return leading characters are prefixed."""
        frame = ar.from_pandas(pd.DataFrame({"data": ["\tcmd", "\rmalicious"]}))
        out = tmp_path / "special.csv"
        ar.write_csv(frame, out, safe_for_spreadsheet=True)
        frame2 = ar.read_csv(out)
        df = ar.to_pandas(frame2)
        assert df["data"].iloc[0].startswith("'")
        assert df["data"].iloc[1].startswith("'")

    def test_strict_bool_rejects_none(self, tmp_path):
        """safe_for_spreadsheet=None raises TypeError."""
        frame = ar.from_pandas(pd.DataFrame({"a": ["hello"]}))
        out = tmp_path / "out.csv"
        with pytest.raises(TypeError):
            ar.write_csv(frame, out, safe_for_spreadsheet=None)

    def test_strict_bool_rejects_int(self, tmp_path):
        """safe_for_spreadsheet=1 or 0 raises TypeError."""
        frame = ar.from_pandas(pd.DataFrame({"a": ["hello"]}))
        out = tmp_path / "out.csv"
        with pytest.raises(TypeError):
            ar.write_csv(frame, out, safe_for_spreadsheet=1)
        with pytest.raises(TypeError):
            ar.write_csv(frame, out, safe_for_spreadsheet=0)

    def test_strict_bool_rejects_string(self, tmp_path):
        """safe_for_spreadsheet='true' raises TypeError."""
        frame = ar.from_pandas(pd.DataFrame({"a": ["hello"]}))
        out = tmp_path / "out.csv"
        with pytest.raises(TypeError):
            ar.write_csv(frame, out, safe_for_spreadsheet="true")
