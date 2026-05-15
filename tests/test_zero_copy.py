"""
Regression tests for zero-copy lifetime safety.

Verifies that NumPy arrays and pandas Series derived from ArFrame columns
remain valid and correct after the source ArFrame (or its C++ backing) is
deleted and garbage collected.

Issue: #242
"""

import gc

import numpy as np
import pandas as pd
import pytest

import arnio as ar


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_frame_int():
    return ar.from_pandas(pd.DataFrame({"a": [1, 2, 3], "b": [10, 20, 30]}))


def make_frame_float():
    return ar.from_pandas(pd.DataFrame({"x": [1.1, 2.2, 3.3]}))


def make_frame_bool():
    return ar.from_pandas(
        pd.DataFrame({"flag": pd.Series([True, False, True], dtype="boolean")})
    )


def make_frame_with_nulls():
    return ar.from_pandas(
        pd.DataFrame(
            {
                "score": pd.array([10, None, 30], dtype=pd.Int64Dtype()),
                "ratio": [1.0, float("nan"), 3.0],
                "active": pd.array([True, None, False], dtype=pd.BooleanDtype()),
            }
        )
    )


def make_frame_single_row():
    return ar.from_pandas(pd.DataFrame({"v": [42]}))


def make_frame_empty():
    return ar.from_pandas(pd.DataFrame({"v": pd.Series([], dtype="int64")}))


# ---------------------------------------------------------------------------
# INT64 lifetime tests
# ---------------------------------------------------------------------------

class TestIntLifetime:
    def test_int_values_survive_frame_deletion(self):
        """INT64 column values remain correct after ArFrame is GC'd."""
        frame = make_frame_int()
        df = ar.to_pandas(frame)
        del frame
        gc.collect()
        assert list(df["a"]) == [1, 2, 3]
        assert list(df["b"]) == [10, 20, 30]

    def test_int_values_survive_multiple_gc_cycles(self):
        """Values stay correct across repeated GC passes."""
        frame = make_frame_int()
        df = ar.to_pandas(frame)
        del frame
        for _ in range(5):
            gc.collect()
        assert list(df["a"]) == [1, 2, 3]

    def test_int_mutation_does_not_corrupt_second_conversion(self):
        """Mutating one derived DataFrame must not affect a second conversion."""
        frame = make_frame_int()
        df1 = ar.to_pandas(frame)
        df2 = ar.to_pandas(frame)
        # mutate df1 in place
        df1["a"].iloc[0] = 999
        # df2 must be unaffected
        assert df2["a"].iloc[0] == 1

    def test_int_dtype_preserved_after_gc(self):
        """Nullable Int64 dtype survives GC of source frame."""
        frame = make_frame_int()
        df = ar.to_pandas(frame)
        del frame
        gc.collect()
        assert str(df["a"].dtype) == "Int64"


# ---------------------------------------------------------------------------
# FLOAT64 lifetime tests
# ---------------------------------------------------------------------------

class TestFloatLifetime:
    def test_float_values_survive_frame_deletion(self):
        """FLOAT64 column values remain correct after ArFrame is GC'd."""
        frame = make_frame_float()
        df = ar.to_pandas(frame)
        del frame
        gc.collect()
        assert pytest.approx(list(df["x"])) == [1.1, 2.2, 3.3]

    def test_float_copy_is_independent(self):
        """to_pandas makes a .copy() of float arrays — mutations are isolated."""
        frame = make_frame_float()
        df1 = ar.to_pandas(frame)
        df2 = ar.to_pandas(frame)
        df1["x"].iloc[0] = -999.0
        assert pytest.approx(df2["x"].iloc[0]) == 1.1

    def test_float_values_survive_multiple_gc_cycles(self):
        frame = make_frame_float()
        df = ar.to_pandas(frame)
        del frame
        for _ in range(5):
            gc.collect()
        assert pytest.approx(list(df["x"])) == [1.1, 2.2, 3.3]


# ---------------------------------------------------------------------------
# BOOL lifetime tests
# ---------------------------------------------------------------------------

class TestBoolLifetime:
    def test_bool_values_survive_frame_deletion(self):
        """BOOL column values remain correct after ArFrame is GC'd."""
        frame = make_frame_bool()
        df = ar.to_pandas(frame)
        del frame
        gc.collect()
        assert list(df["flag"]) == [True, False, True]

    def test_bool_dtype_preserved_after_gc(self):
        """Nullable boolean dtype survives GC of source frame."""
        frame = make_frame_bool()
        df = ar.to_pandas(frame)
        del frame
        gc.collect()
        assert str(df["flag"].dtype) == "boolean"

    def test_bool_values_survive_multiple_gc_cycles(self):
        frame = make_frame_bool()
        df = ar.to_pandas(frame)
        del frame
        for _ in range(5):
            gc.collect()
        assert list(df["flag"]) == [True, False, True]


# ---------------------------------------------------------------------------
# Null mask lifetime tests
# ---------------------------------------------------------------------------

class TestNullMaskLifetime:
    def test_null_mask_int_survives_gc(self):
        """Null positions in INT64 columns survive GC of source frame."""
        frame = make_frame_with_nulls()
        df = ar.to_pandas(frame)
        del frame
        gc.collect()
        assert pd.isna(df["score"].iloc[1])
        assert df["score"].iloc[0] == 10
        assert df["score"].iloc[2] == 30

    def test_null_mask_float_survives_gc(self):
        """NaN positions in FLOAT64 columns survive GC of source frame."""
        frame = make_frame_with_nulls()
        df = ar.to_pandas(frame)
        del frame
        gc.collect()
        assert np.isnan(df["ratio"].iloc[1])
        assert pytest.approx(df["ratio"].iloc[0]) == 1.0

    def test_null_mask_bool_survives_gc(self):
        """Null positions in BOOL columns survive GC of source frame."""
        frame = make_frame_with_nulls()
        df = ar.to_pandas(frame)
        del frame
        gc.collect()
        assert pd.isna(df["active"].iloc[1])
        assert df["active"].iloc[0] == True  # noqa: E712
        assert df["active"].iloc[2] == False  # noqa: E712

    def test_all_null_column_survives_gc(self):
        """A fully-null column produces all-NA after GC."""
        df_in = pd.DataFrame(
            {"empty_col": pd.array([None, None, None], dtype=pd.Int64Dtype())}
        )
        frame = ar.from_pandas(df_in)
        df = ar.to_pandas(frame)
        del frame
        gc.collect()
        assert df["empty_col"].isna().all()


# ---------------------------------------------------------------------------
# Edge case lifetime tests
# ---------------------------------------------------------------------------

class TestEdgeCaseLifetime:
    def test_single_row_int_survives_gc(self):
        """Single-row INT64 frame survives GC."""
        frame = make_frame_single_row()
        df = ar.to_pandas(frame)
        del frame
        gc.collect()
        assert df["v"].iloc[0] == 42

    def test_empty_frame_survives_gc(self):
        """Empty frame (0 rows) converts without error and survives GC."""
        frame = make_frame_empty()
        df = ar.to_pandas(frame)
        del frame
        gc.collect()
        assert len(df) == 0
        assert "v" in df.columns

    def test_multiple_independent_conversions_stay_isolated(self):
        """Three independent to_pandas() calls produce isolated DataFrames."""
        frame = make_frame_int()
        dfs = [ar.to_pandas(frame) for _ in range(3)]
        del frame
        gc.collect()
        # mutate first, rest untouched
        dfs[0]["a"].iloc[0] = 999
        assert dfs[1]["a"].iloc[0] == 1
        assert dfs[2]["a"].iloc[0] == 1

    def test_roundtrip_after_gc(self):
        """from_pandas → to_pandas → del → gc → values correct."""
        original = pd.DataFrame({"p": [7, 8, 9], "q": [0.1, 0.2, 0.3]})
        frame = ar.from_pandas(original)
        result = ar.to_pandas(frame)
        del frame
        gc.collect()
        assert list(result["p"]) == [7, 8, 9]
        assert pytest.approx(list(result["q"])) == [0.1, 0.2, 0.3]