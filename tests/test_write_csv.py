"""Tests for write_csv delimiter type, newline, and quote-character validation."""

import pandas as pd
import pytest

import arnio as ar


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
        with pytest.raises(ValueError, match="delimiter must not be a newline character"):
            ar.write_csv(frame, str(tmp_path / "out.csv"), delimiter=delimiter)


class TestWriteCsvQuoteCharValidation:
    """Quote-character validation: the CSV quote character must not be used as delimiter."""

    def test_quote_char_as_delimiter_rejected(self, tmp_path):
        frame = ar.from_pandas(pd.DataFrame({"a": [1]}))
        with pytest.raises(ValueError, match="delimiter must not be the CSV quote character"):
            ar.write_csv(frame, str(tmp_path / "out.csv"), delimiter='"')
