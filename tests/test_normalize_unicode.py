"""Regression tests for normalize_unicode form validation (issue #1669)."""

import unicodedata

import pandas as pd
import pytest

import arnio as ar


def make_sample_frame():
    df = pd.DataFrame({"text": ["cafe\u0301"]})
    return ar.from_pandas(df)


class TestNormalizeUnicodeFormValidation:
    def test_non_string_form_raises_typeerror(self):
        frame = make_sample_frame()
        with pytest.raises(TypeError, match="form must be a string"):
            ar.normalize_unicode(frame, form=["NFC"])

    def test_unsupported_string_form_raises_valueerror(self):
        frame = make_sample_frame()
        with pytest.raises(
            ValueError, match="Unsupported normalization form: 'X'"
        ):
            ar.normalize_unicode(frame, form="X")

    def test_unsupported_form_lists_supported_options(self):
        frame = make_sample_frame()
        with pytest.raises(ValueError) as excinfo:
            ar.normalize_unicode(frame, form="X")
        for valid in ("NFC", "NFD", "NFKC", "NFKD"):
            assert valid in str(excinfo.value)

    def test_valid_nfc_form_succeeds(self):
        frame = make_sample_frame()
        result = ar.normalize_unicode(frame, form="NFC")
        result_df = ar.to_pandas(result)
        assert result_df["text"].iloc[0] == unicodedata.normalize("NFC", "cafe\u0301")

    def test_valid_nfd_form_succeeds(self):
        frame = make_sample_frame()
        result = ar.normalize_unicode(frame, form="NFD")
        result_df = ar.to_pandas(result)
        assert (
            unicodedata.normalize("NFD", result_df["text"].iloc[0])
            == result_df["text"].iloc[0]
        )

    def test_valid_nfkc_form_succeeds(self):
        df = pd.DataFrame({"text": ["ﬁle"]})
        frame = ar.from_pandas(df)
        result = ar.normalize_unicode(frame, form="NFKC")
        result_df = ar.to_pandas(result)
        assert result_df["text"].iloc[0] == unicodedata.normalize("NFKC", "ﬁle")

    def test_valid_nfkd_form_succeeds(self):
        df = pd.DataFrame({"text": ["ﬁle"]})
        frame = ar.from_pandas(df)
        result = ar.normalize_unicode(frame, form="NFKD")
        result_df = ar.to_pandas(result)
        assert result_df["text"].iloc[0] == unicodedata.normalize("NFKD", "ﬁle")

    def test_other_non_string_types_also_raise(self):
        frame = make_sample_frame()
        for invalid in (123, 3.14, {"NFC"}, {"form": "NFC"}, b"NFC"):
            with pytest.raises(TypeError, match="form must be a string"):
                ar.normalize_unicode(frame, form=invalid)

    def test_default_form_nfc_works(self):
        frame = make_sample_frame()
        result = ar.normalize_unicode(frame)
        result_df = ar.to_pandas(result)
        assert result_df["text"].iloc[0] == "café"
