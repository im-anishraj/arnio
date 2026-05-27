"""Comprehensive tests for combine_columns in arnio.cleaning."""

import pandas as pd
import pytest

import arnio as ar


class TestCombineColumnsComprehensive:
    """Test suite for validating combine_columns helper logic."""

    def test_combine_columns_with_various_separators(self):
        """Test combine_columns with multiple separator inputs."""
        df = pd.DataFrame({"col1": ["A", "B"], "col2": ["X", "Y"]})
        frame = ar.from_pandas(df)

        for sep in (" ", "-", "|", "::"):
            result = ar.combine_columns(
                frame,
                subset=["col1", "col2"],
                separator=sep,
                output_column="out",
            )
            res_df = ar.to_pandas(result)
            expected = [f"A{sep}X", f"B{sep}Y"]
            assert list(res_df["out"]) == expected

    def test_combine_columns_mixed_types(self):
        """Test combine_columns with mixed numeric, boolean, and string types."""
        df = pd.DataFrame(
            {
                "str_col": ["val", "val"],
                "int_col": [42, 100],
                "float_col": [3.5, 0.25],
                "bool_col": [True, False],
            }
        )
        frame = ar.from_pandas(df)
        result = ar.combine_columns(
            frame,
            subset=["str_col", "int_col", "float_col", "bool_col"],
            separator="_",
            output_column="combined",
        )
        res_df = ar.to_pandas(result)
        assert list(res_df["combined"]) == ["val_42_3.5_True", "val_100_0.25_False"]

    def test_combine_columns_subset_selection(self):
        """Test combine_columns with a custom subset of columns, leaving others unchanged."""
        df = pd.DataFrame(
            {
                "keep1": ["yes", "no"],
                "combine1": ["A", "B"],
                "combine2": ["1", "2"],
                "keep2": [10.5, 20.5],
            }
        )
        frame = ar.from_pandas(df)
        result = ar.combine_columns(
            frame,
            subset=["combine1", "combine2"],
            separator="-",
            output_column="merged",
        )
        res_df = ar.to_pandas(result)
        assert "merged" in res_df.columns
        assert list(res_df["merged"]) == ["A-1", "B-2"]
        assert list(res_df["keep1"]) == ["yes", "no"]
        assert list(res_df["keep2"]) == [10.5, 20.5]

    def test_combine_columns_partial_null_handling(self):
        """Test combine_columns where some rows contain a mixture of nulls and valid values."""
        df = pd.DataFrame(
            {
                "col1": ["A", None, "C", None],
                "col2": ["B", "Y", None, None],
            }
        )
        frame = ar.from_pandas(df)
        result = ar.combine_columns(
            frame,
            subset=["col1", "col2"],
            separator="-",
            output_column="combined",
        )
        res_df = ar.to_pandas(result)
        # partial nulls: the null values are stringified as empty string "" by pandas astype("string").fillna("") mapping
        assert res_df["combined"].iloc[0] == "A-B"
        assert res_df["combined"].iloc[1] == "-Y"
        assert res_df["combined"].iloc[2] == "C-"
        assert pd.isna(res_df["combined"].iloc[3])  # All nulls in a row propagates pd.NA
