"""
Smoke tests: nullable pandas extension dtype round-trip behavior.
Covers the compatibility contract documented in docs/nullable_dtype_compat.md.
"""

import pandas as pd
import pytest

import arnio as ar


class TestNullableDtypeRoundtrip:
    """Verify from_pandas -> to_pandas preserves nullable extension dtypes."""

    def test_int64_with_na_preserves_dtype(self):
        df = pd.DataFrame({"col": pd.array([1, 2, None], dtype="Int64")})
        result = ar.to_pandas(ar.from_pandas(df))
        assert str(result["col"].dtype) == "Int64"

    def test_int64_na_values_survive(self):
        df = pd.DataFrame({"col": pd.array([1, None, 3], dtype="Int64")})
        result = ar.to_pandas(ar.from_pandas(df))
        assert result["col"].isna().tolist() == [False, True, False]
        assert result["col"].iloc[0] == 1
        assert result["col"].iloc[2] == 3

    def test_boolean_with_na_preserves_dtype(self):
        df = pd.DataFrame({"col": pd.array([True, None, False], dtype="boolean")})
        result = ar.to_pandas(ar.from_pandas(df))
        assert str(result["col"].dtype) == "boolean"

    def test_boolean_na_values_survive(self):
        df = pd.DataFrame({"col": pd.array([True, None, False], dtype="boolean")})
        result = ar.to_pandas(ar.from_pandas(df))
        assert result["col"].isna().tolist() == [False, True, False]
        assert result["col"].iloc[0]
        assert not result["col"].iloc[2]

    def test_string_with_na_preserves_dtype(self):
        df = pd.DataFrame({"col": pd.array(["a", None, "c"], dtype="string")})
        result = ar.to_pandas(ar.from_pandas(df))
        assert str(result["col"].dtype) == "string"

    def test_string_na_values_survive(self):
        df = pd.DataFrame({"col": pd.array(["a", None, "c"], dtype="string")})
        result = ar.to_pandas(ar.from_pandas(df))
        assert result["col"].isna().tolist() == [False, True, False]

    def test_float64_extension_na_values_survive(self):
        """Float64 -> float64 on round-trip; NA positions must be preserved."""
        df = pd.DataFrame({"col": pd.array([1.5, None, 3.7], dtype="Float64")})
        result = ar.to_pandas(ar.from_pandas(df))
        assert result["col"].isna().tolist() == [False, True, False]
        assert result["col"].iloc[0] == pytest.approx(1.5)
        assert result["col"].iloc[2] == pytest.approx(3.7)

    def test_multi_column_nullable_roundtrip(self):
        """All nullable dtypes together in one DataFrame."""
        df = pd.DataFrame(
            {
                "int_col": pd.array([1, None, 3], dtype="Int64"),
                "bool_col": pd.array([True, None, False], dtype="boolean"),
                "str_col": pd.array(["a", None, "c"], dtype="string"),
            }
        )
        result = ar.to_pandas(ar.from_pandas(df))
        assert str(result["int_col"].dtype) == "Int64"
        assert str(result["bool_col"].dtype) == "boolean"
        assert str(result["str_col"].dtype) == "string"
        assert result["int_col"].isna().tolist() == [False, True, False]
        assert result["bool_col"].isna().tolist() == [False, True, False]
        assert result["str_col"].isna().tolist() == [False, True, False]
