"""Tests for the on_bad_lines parameter on read_csv / read_csv_chunked.

Covers:
- error / warn / skip semantics for both narrow and wide width mismatches
- interaction with the legacy `mode` parameter (strict vs permissive)
- UserWarning content and truncation
- chunked-reader behavior including trailing-bad-rows-at-EOF
- nrows budgeting counts bad rows
- argument validation
"""

from __future__ import annotations

import warnings

import pytest

import arnio as ar
from arnio.io import _PREVIEW_BAD_ROWS


class TestOnBadLinesValidation:
    def test_invalid_value_rejected_before_read(self, tmp_path):
        csv_path = tmp_path / "ok.csv"
        csv_path.write_text("a,b\n1,2\n")
        with pytest.raises(
            ValueError, match="on_bad_lines must be either 'error', 'warn', 'skip'"
        ):
            ar.read_csv(csv_path, on_bad_lines="raise")

    def test_invalid_value_rejected_in_chunked(self, tmp_path):
        csv_path = tmp_path / "ok.csv"
        csv_path.write_text("a,b\n1,2\n")
        with pytest.raises(ValueError, match="on_bad_lines must be either"):
            list(ar.read_csv_chunked(csv_path, on_bad_lines="ignore"))

    def test_non_string_rejected(self, tmp_path):
        csv_path = tmp_path / "ok.csv"
        csv_path.write_text("a,b\n1,2\n")
        with pytest.raises(TypeError, match="on_bad_lines must be a string"):
            ar.read_csv(csv_path, on_bad_lines=None)


class TestReadCsvOnBadLinesError:
    def test_error_is_default(self, tmp_path):
        csv_path = tmp_path / "narrow.csv"
        csv_path.write_text("a,b,c\n1,2,3\n4,5\n")
        with pytest.raises(ar.CsvReadError, match="CSV row 3 has 2 fields; expected 3"):
            ar.read_csv(csv_path)

    def test_explicit_error_matches_default(self, tmp_path):
        csv_path = tmp_path / "narrow.csv"
        csv_path.write_text("a,b,c\n1,2,3\n4,5\n")
        with pytest.raises(ar.CsvReadError, match="CSV row 3 has 2 fields; expected 3"):
            ar.read_csv(csv_path, on_bad_lines="error")

    def test_error_raises_on_wide_row(self, tmp_path):
        csv_path = tmp_path / "wide.csv"
        csv_path.write_text("a,b\n1,2\n3,4,5\n")
        with pytest.raises(ar.CsvReadError, match="CSV row 3 has 3 fields; expected 2"):
            ar.read_csv(csv_path, on_bad_lines="error")

    def test_error_raises_on_first_bad_row(self, tmp_path):
        """Multiple bad rows — error stops at the first."""
        csv_path = tmp_path / "many.csv"
        csv_path.write_text("a,b,c\n1,2,3\n4,5\n6,7,8,9\n")
        with pytest.raises(ar.CsvReadError, match="CSV row 3 has 2 fields; expected 3"):
            ar.read_csv(csv_path, on_bad_lines="error")


class TestReadCsvOnBadLinesWarn:
    def test_warn_drops_bad_row_and_emits_warning(self, tmp_path):
        csv_path = tmp_path / "warn.csv"
        csv_path.write_text("a,b,c\n1,2,3\n4,5\n6,7,8\n")
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            frame = ar.read_csv(csv_path, on_bad_lines="warn")

        assert frame.shape == (2, 3)
        assert len(caught) == 1
        assert caught[0].category is UserWarning
        msg = str(caught[0].message)
        assert "1 malformed CSV row(s)" in msg
        assert "CSV row 3 has 2 fields; expected 3" in msg

    def test_warn_collects_all_bad_rows(self, tmp_path):
        """warn does NOT short-circuit — all bad rows surface in one warning."""
        csv_path = tmp_path / "many_bad.csv"
        csv_path.write_text(
            "a,b,c\n"
            "1,2,3\n"  # good
            "4,5\n"  # narrow
            "6,7,8,9\n"  # wide
            "10,11,12\n"  # good
            "13,14\n"  # narrow
        )
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            frame = ar.read_csv(csv_path, on_bad_lines="warn")

        assert frame.shape == (2, 3)
        assert len(caught) == 1
        msg = str(caught[0].message)
        assert "3 malformed CSV row(s)" in msg
        assert "CSV row 3 has 2 fields; expected 3" in msg
        assert "CSV row 4 has 4 fields; expected 3" in msg
        assert "CSV row 6 has 2 fields; expected 3" in msg

    def test_warn_no_warning_when_file_is_clean(self, tmp_path):
        csv_path = tmp_path / "clean.csv"
        csv_path.write_text("a,b,c\n1,2,3\n4,5,6\n")
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            frame = ar.read_csv(csv_path, on_bad_lines="warn")

        assert frame.shape == (2, 3)
        assert [w for w in caught if w.category is UserWarning] == []

    def test_warn_message_uses_cpp_error_format(self, tmp_path):
        """Per-row entries should match the C++ error message format exactly."""
        csv_path = tmp_path / "format.csv"
        csv_path.write_text("a,b,c\n1,2,3\n4,5\n")
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            ar.read_csv(csv_path, on_bad_lines="warn")

        msg = str(caught[0].message)
        # Same shape as throw std::runtime_error("CSV row N has X fields; expected Y")
        assert "CSV row 3 has 2 fields; expected 3" in msg

    def test_warn_truncates_preview_with_more_indicator(self, tmp_path):
        n_bad = _PREVIEW_BAD_ROWS + 3
        rows = ["a,b,c", "1,2,3"]
        rows.extend(f"bad_{i},only_two" for i in range(n_bad))
        rows.append("9,9,9")
        csv_path = tmp_path / "many.csv"
        csv_path.write_text("\n".join(rows) + "\n")

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            frame = ar.read_csv(csv_path, on_bad_lines="warn")

        assert frame.shape == (2, 3)
        msg = str(caught[0].message)
        assert f"{n_bad} malformed CSV row(s)" in msg
        assert f"(+{n_bad - _PREVIEW_BAD_ROWS} more)" in msg
        # First preview entry is present, last one beyond the preview is not.
        assert "bad_0" not in msg  # field contents are not included
        # The (PREVIEW+1)-th bad row should not appear by row-number either.
        assert f"CSV row {_PREVIEW_BAD_ROWS + 2 + 1} has 2 fields" not in msg


class TestReadCsvOnBadLinesSkip:
    def test_skip_drops_bad_rows_silently(self, tmp_path):
        csv_path = tmp_path / "skip.csv"
        csv_path.write_text("a,b,c\n1,2,3\n4,5\n6,7,8,9\n10,11,12\n")
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            frame = ar.read_csv(csv_path, on_bad_lines="skip")

        assert frame.shape == (2, 3)
        assert [w for w in caught if w.category is UserWarning] == []


class TestOnBadLinesModeInteraction:
    def test_permissive_narrow_rows_do_not_reach_on_bad_lines(self, tmp_path):
        """In permissive mode, narrow rows are padded silently regardless of
        on_bad_lines — they never appear in bad_rows / warnings."""
        csv_path = tmp_path / "permissive_narrow.csv"
        csv_path.write_text("a,b,c\n1,2,3\n4,5\n6,7,8\n")
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            frame = ar.read_csv(csv_path, mode="permissive", on_bad_lines="warn")

        # Narrow row is padded and kept.
        assert frame.shape == (3, 3)
        # No warnings because the narrow row is not "bad" under permissive mode.
        assert [w for w in caught if w.category is UserWarning] == []

    def test_permissive_wide_rows_surface_to_on_bad_lines(self, tmp_path):
        """Wide rows are always bad — permissive + warn drops them with a
        UserWarning."""
        csv_path = tmp_path / "permissive_wide.csv"
        csv_path.write_text("a,b\n1,2\n3,4,5\n6,7\n")
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            frame = ar.read_csv(csv_path, mode="permissive", on_bad_lines="warn")

        assert frame.shape == (2, 2)
        msg = str(caught[0].message)
        assert "CSV row 3 has 3 fields; expected 2" in msg

    def test_strict_with_warn_surfaces_both_narrow_and_wide(self, tmp_path):
        csv_path = tmp_path / "strict_warn.csv"
        csv_path.write_text("a,b,c\n1,2,3\n4,5\n6,7,8,9\n")
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            frame = ar.read_csv(csv_path, mode="strict", on_bad_lines="warn")

        assert frame.shape == (1, 3)
        msg = str(caught[0].message)
        assert "CSV row 3 has 2 fields; expected 3" in msg
        assert "CSV row 4 has 4 fields; expected 3" in msg

    def test_permissive_with_default_error_preserves_legacy(self, tmp_path):
        """mode=permissive + on_bad_lines=error: narrow rows pad silently,
        wide rows raise. Matches pre-on_bad_lines behavior exactly."""
        csv_path = tmp_path / "legacy.csv"
        csv_path.write_text("a,b,c\n1,2,3\n4,5\n")
        frame = ar.read_csv(csv_path, mode="permissive")  # default on_bad_lines
        assert frame.shape == (2, 3)

        csv_path.write_text("a,b\n1,2\n3,4,5\n")
        with pytest.raises(ar.CsvReadError, match="CSV row 3 has 3 fields; expected 2"):
            ar.read_csv(csv_path, mode="permissive")


class TestNrowsBudgeting:
    def test_bad_rows_count_toward_nrows(self, tmp_path):
        csv_path = tmp_path / "nrows.csv"
        csv_path.write_text(
            "a,b,c\n"
            "1,2,3\n"  # row 2: good
            "4,5\n"  # row 3: bad
            "6,7,8\n"  # row 4: good
            "9,10,11\n"  # row 5: good (should be excluded by nrows=3)
        )
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            frame = ar.read_csv(csv_path, nrows=3, on_bad_lines="warn")

        # nrows=3 covers rows 2, 3, 4 in input order; row 3 is bad and dropped,
        # so the frame holds 2 good rows.
        assert frame.shape == (2, 3)
        msg = str(caught[0].message)
        assert "CSV row 3 has 2 fields; expected 3" in msg


class TestReadCsvChunkedOnBadLines:
    def test_chunked_error_raises_on_first_bad_row(self, tmp_path):
        csv_path = tmp_path / "chunked_err.csv"
        csv_path.write_text("a,b\n1,2\n3,4,5\n6,7\n")
        with pytest.raises(ar.CsvReadError, match="CSV row 3 has 3 fields; expected 2"):
            list(ar.read_csv_chunked(csv_path, chunksize=10, on_bad_lines="error"))

    def test_chunked_warn_emits_warning(self, tmp_path):
        csv_path = tmp_path / "chunked_warn.csv"
        csv_path.write_text("a,b,c\n1,2,3\n4,5\n6,7,8\n")
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            frames = list(
                ar.read_csv_chunked(csv_path, chunksize=10, on_bad_lines="warn")
            )

        assert len(frames) == 1
        assert frames[0].shape == (2, 3)
        assert any(w.category is UserWarning for w in caught)

    def test_chunked_skip_silent(self, tmp_path):
        csv_path = tmp_path / "chunked_skip.csv"
        csv_path.write_text("a,b,c\n1,2,3\n4,5\n6,7,8\n")
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            frames = list(
                ar.read_csv_chunked(csv_path, chunksize=10, on_bad_lines="skip")
            )
        assert sum(f.shape[0] for f in frames) == 2
        assert [w for w in caught if w.category is UserWarning] == []

    def test_chunked_trailing_bad_row_at_eof_is_surfaced(self, tmp_path):
        """Regression: bad row at EOF used to be silently dropped because
        next_chunk returned nullopt when raw_data was empty."""
        csv_path = tmp_path / "trailing.csv"
        csv_path.write_text(
            "a,b,c\n"
            "1,2,3\n"  # good
            "4,5\n"  # bad
            "6,7,8,9\n"  # bad
            "10,11,12\n"  # good
            "13,14\n"  # bad, trailing
        )
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            frames = list(
                ar.read_csv_chunked(csv_path, chunksize=2, on_bad_lines="warn")
            )

        # All three bad rows must appear in the aggregated warnings.
        joined = "\n".join(str(w.message) for w in caught)
        assert "CSV row 3 has 2 fields; expected 3" in joined
        assert "CSV row 4 has 4 fields; expected 3" in joined
        assert "CSV row 6 has 2 fields; expected 3" in joined
        # And both good rows must be kept across the yielded chunks.
        assert sum(f.shape[0] for f in frames) == 2

    def test_chunked_all_bad_after_header_yields_empty_frame_with_warning(
        self, tmp_path
    ):
        """Header sets expected_cols but every data row is malformed. The
        reader must still surface the bad rows via a final empty-frame chunk."""
        csv_path = tmp_path / "all_bad.csv"
        csv_path.write_text("a,b,c\nx,y\np,q,r,s\n")
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            frames = list(
                ar.read_csv_chunked(csv_path, chunksize=10, on_bad_lines="warn")
            )

        assert len(frames) == 1
        assert frames[0].shape == (0, 3)
        assert frames[0].columns == ["a", "b", "c"]
        msg = "\n".join(str(w.message) for w in caught)
        assert "CSV row 2 has 2 fields; expected 3" in msg


class TestOnBadLinesQuotedDelimiters:
    def test_quoted_delimiter_is_not_classified_bad(self, tmp_path):
        csv_path = tmp_path / "quoted.csv"
        # The first data row contains a comma *inside* a quoted field — it must
        # parse as 3 fields, not 4.
        csv_path.write_text('a,b,c\n"x,y",p,q\n1,2,3\n')
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            frame = ar.read_csv(csv_path, on_bad_lines="warn")

        assert frame.shape == (2, 3)
        assert [w for w in caught if w.category is UserWarning] == []
        import arnio as _ar  # noqa: F401  (frame ops happen via ar.to_pandas)

        df = ar.to_pandas(frame)
        assert df["a"].iloc[0] == "x,y"

    def test_bad_row_among_quoted_rows_still_caught(self, tmp_path):
        """Mix quoted-delimiter rows (good) with a genuinely malformed row;
        only the malformed row should appear in the warning."""
        csv_path = tmp_path / "mixed_quoted.csv"
        csv_path.write_text(
            "a,b,c\n"
            '"x,y",p,q\n'  # row 2: good (quoted comma)
            "1,2\n"  # row 3: bad narrow
            '"w",e,r\n'  # row 4: good (lone-quoted field)
        )
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            frame = ar.read_csv(csv_path, on_bad_lines="warn")

        assert frame.shape == (2, 3)
        msg = str(caught[0].message)
        assert "1 malformed CSV row(s)" in msg
        assert "CSV row 3 has 2 fields; expected 3" in msg

    def test_empty_quoted_field_not_classified_bad(self, tmp_path):
        csv_path = tmp_path / "empty_quoted.csv"
        csv_path.write_text("a,b,c\n" '"",2,3\n' "4,5\n" "6,7,8\n")

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            frame = ar.read_csv(csv_path, on_bad_lines="warn")

        assert frame.shape == (2, 3)

        msg = str(caught[0].message)

        assert "1 malformed CSV row(s)" in msg
        assert "CSV row 3 has 2 fields; expected 3" in msg

        df = ar.to_pandas(frame)
        assert df["a"].iloc[0] == ""


class TestOnBadLinesMultilineRecords:
    def test_multiline_record_is_not_classified_bad(self, tmp_path):
        csv_path = tmp_path / "multiline_good.csv"
        csv_path.write_bytes(b'a,b,c\n"line1\nline2",p,q\n1,2,3\n')
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            frame = ar.read_csv(csv_path, on_bad_lines="warn")

        assert frame.shape == (2, 3)
        assert [w for w in caught if w.category is UserWarning] == []
        df = ar.to_pandas(frame)
        assert df["a"].iloc[0] == "line1\nline2"

    def test_bad_row_after_multiline_uses_logical_row_number(self, tmp_path):
        """Row-number accounting must increment by logical records, not by
        physical lines. A bad row after a 3-line multiline record at the top
        is still 'row 3' in 1-based logical numbering (header is row 1)."""
        csv_path = tmp_path / "multiline_bad.csv"
        csv_path.write_text(
            "a,b,c\n"  # logical row 1 (header)
            '"line1\nline2\nline3",p,q\n'  # logical row 2 (good, spans 3 physical lines)
            "4,5\n"  # logical row 3 (bad narrow)
        )
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            frame = ar.read_csv(csv_path, on_bad_lines="warn")

        assert frame.shape == (1, 3)
        msg = str(caught[0].message)
        # The number reported is the logical record (3), not the physical
        # line in the file (which would be 5).
        assert "CSV row 3 has 2 fields; expected 3" in msg

    def test_multiline_record_across_chunk_boundaries(self, tmp_path):
        """A multiline record must remain atomic — never split across chunks —
        and any bad row that follows must still be reported with its global
        logical row number."""
        csv_path = tmp_path / "multiline_chunked.csv"
        csv_path.write_text(
            "a,b,c\n"  # logical row 1
            "1,2,3\n"  # logical row 2 (good)
            '"x\ny\nz",p,q\n'  # logical row 3 (good, multiline)
            "4,5\n"  # logical row 4 (bad narrow)
            "6,7,8\n"  # logical row 5 (good)
        )
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            frames = list(
                ar.read_csv_chunked(csv_path, chunksize=2, on_bad_lines="warn")
            )

        # 3 good logical rows preserved across chunks.
        assert sum(f.shape[0] for f in frames) == 3
        joined = "\n".join(str(w.message) for w in caught)
        # Bad row reports its file-global logical row number.
        assert "CSV row 4 has 2 fields; expected 3" in joined


class TestOnBadLinesUsecols:
    def test_bad_row_detected_before_usecols_projection(self, tmp_path):
        """Header has 4 columns; user selects 2 via usecols. A row with 3
        fields is still bad (expected=4), even though both selected columns
        happen to be present in the truncated row."""
        csv_path = tmp_path / "usecols_bad.csv"
        csv_path.write_text(
            "a,b,c,d\n"
            "1,2,3,4\n"  # row 2: good (4 fields)
            "5,6,7\n"  # row 3: bad (3 fields; even though usecols=[a,b]
            #          would only see 'a','b', expected is 4)
            "8,9,10,11\n"  # row 4: good
        )
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            frame = ar.read_csv(csv_path, usecols=["a", "b"], on_bad_lines="warn")

        # Projection happens AFTER bad-row dispatch — frame has the requested
        # 2 columns, with the 2 good rows kept.
        assert frame.shape == (2, 2)
        assert frame.columns == ["a", "b"]
        msg = str(caught[0].message)
        # The expected count reflects the full header width (4), not the
        # usecols subset (2).
        assert "CSV row 3 has 3 fields; expected 4" in msg

    def test_usecols_error_mode_uses_full_width(self, tmp_path):
        """In error mode, the raise message must report the full expected
        width, not the usecols-projected width."""
        csv_path = tmp_path / "usecols_err.csv"
        csv_path.write_text("a,b,c,d\n1,2,3,4\n5,6,7\n")
        with pytest.raises(ar.CsvReadError, match="CSV row 3 has 3 fields; expected 4"):
            ar.read_csv(csv_path, usecols=["a", "b"])

    def test_usecols_with_chunked_warn(self, tmp_path):
        csv_path = tmp_path / "usecols_chunked.csv"
        csv_path.write_text("a,b,c,d\n" "1,2,3,4\n" "5,6,7\n" "8,9,10,11\n")
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            frames = list(
                ar.read_csv_chunked(
                    csv_path,
                    usecols=["a", "d"],
                    chunksize=10,
                    on_bad_lines="warn",
                )
            )

        assert sum(f.shape[0] for f in frames) == 2
        assert frames[0].columns == ["a", "d"]
        joined = "\n".join(str(w.message) for w in caught)
        assert "CSV row 3 has 3 fields; expected 4" in joined


class TestScanCsvOnBadLines:
    def test_default_error_raises(self, tmp_path):
        csv_path = tmp_path / "bad.csv"
        csv_path.write_text("a,b\n1,2\nbad_row\n3,4\n")
        with pytest.raises(ar.CsvReadError):
            ar.scan_csv(csv_path)

    def test_warn_skips_bad_rows(self, tmp_path):
        csv_path = tmp_path / "bad.csv"
        csv_path.write_text("a,b\n1,2\nbad_row\n3,4\n")
        schema = ar.scan_csv(csv_path, on_bad_lines="warn")
        assert schema == {"a": "int64", "b": "int64"}

    def test_skip_skips_bad_rows(self, tmp_path):
        csv_path = tmp_path / "bad.csv"
        csv_path.write_text("a,b\n1,2\nbad_row\n3,4\n")
        schema = ar.scan_csv(csv_path, on_bad_lines="skip")
        assert schema == {"a": "int64", "b": "int64"}

    def test_invalid_on_bad_lines_raises(self, tmp_path):
        csv_path = tmp_path / "good.csv"
        csv_path.write_text("a,b\n1,2\n")
        with pytest.raises(ValueError):
            ar.scan_csv(csv_path, on_bad_lines="invalid")

    def test_warn_emits_user_warning(self, tmp_path):
        csv_path = tmp_path / "bad.csv"
        csv_path.write_text("a,b\n1,2\nbad_row\n3,4\n")
        with pytest.warns(UserWarning, match="malformed CSV row"):
            ar.scan_csv(csv_path, on_bad_lines="warn")

    def test_skip_does_not_emit_warning(self, tmp_path):
        csv_path = tmp_path / "bad.csv"
        csv_path.write_text("a,b\n1,2\nbad_row\n3,4\n")
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            ar.scan_csv(csv_path, on_bad_lines="skip")
        assert [w for w in caught if w.category is UserWarning] == []

    def test_warn_quoted_delimiter_not_classified_bad(self, tmp_path):
        """A quoted field containing the delimiter must not be reported as malformed."""
        csv_path = tmp_path / "quoted.csv"
        csv_path.write_text('a,b\n"x,y",2\n1,2\n')
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            schema = ar.scan_csv(csv_path, on_bad_lines="warn")
        assert schema == {"a": "string", "b": "int64"}
        assert [w for w in caught if w.category is UserWarning] == []

    def test_warn_real_bad_row_among_quoted_still_caught(self, tmp_path):
        """Real malformed row warns while quoted-delimiter rows pass through."""
        csv_path = tmp_path / "mixed.csv"
        csv_path.write_text('a,b\n"x,y",2\nbad_row\n1,2\n')
        with pytest.warns(UserWarning, match="malformed CSV row"):
            schema = ar.scan_csv(csv_path, on_bad_lines="warn")
        assert schema == {"a": "string", "b": "int64"}

    def test_warn_multiple_bad_rows_correct_row_numbers(self, tmp_path):
        """Row numbers in warning must reflect physical CSV row, not accepted-row count."""
        csv_path = tmp_path / "multi_bad.csv"
        csv_path.write_text(
            "a,b\n"
            "1,2\n"  # row 2: good
            "bad\n"  # row 3: bad
            "3,4\n"  # row 4: good
            "also_bad\n"  # row 5: bad
            "5,6\n"  # row 6: good
        )
        with pytest.warns(UserWarning) as caught:
            schema = ar.scan_csv(csv_path, on_bad_lines="warn")
        msg = str(caught[0].message)
        assert "CSV row 3 has 1 fields; expected 2" in msg
        assert "CSV row 5 has 1 fields; expected 2" in msg
        assert schema == {"a": "int64", "b": "int64"}

    def test_warn_blank_row_before_bad_row_correct_number(self, tmp_path):
        """Blank line before malformed row must not shift the reported row number."""
        csv_path = tmp_path / "blank_before_bad.csv"
        csv_path.write_text(
            "a,b\n"
            "1,2\n"  # row 2: good
            "\n"  # row 3: blank
            "bad\n"  # row 4: bad
            "3,4\n"  # row 5: good
        )
        with pytest.warns(UserWarning) as caught:
            ar.scan_csv(csv_path, on_bad_lines="warn")
        assert "CSV row 4 has 1 fields; expected 2" in str(caught[0].message)

    def test_warn_has_header_false_row_numbering(self, tmp_path):
        """has_header=False: first record is row 1, malformed rows report correctly."""
        csv_path = tmp_path / "no_header.csv"
        csv_path.write_text(
            "1,2\n"  # row 1: good (first record, used as data)
            "bad\n"  # row 2: bad
            "3,4\n"  # row 3: good
        )
        with pytest.warns(UserWarning) as caught:
            ar.scan_csv(csv_path, on_bad_lines="warn", has_header=False)
        assert "CSV row 2 has 1 fields; expected 2" in str(caught[0].message)
