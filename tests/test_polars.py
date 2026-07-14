"""Tests for arnio Polars interop (from_polars / to_polars).

Run with:
    pip install arnio[polars,arrow]
    pytest tests/test_polars.py -v
"""

from __future__ import annotations

import sys
from unittest.mock import patch

import pandas as pd
import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_arframe():
    """Return a small ArFrame with all four native Arnio dtypes."""
    import arnio as ar

    return ar.from_pandas(
        pd.DataFrame(
            {
                "name": pd.array(["Alice", "Bob", None], dtype=pd.StringDtype()),
                "age": pd.array([25, 30, None], dtype=pd.Int64Dtype()),
                "score": pd.array([9.5, 7.0, None], dtype=pd.Float64Dtype()),
                "active": pd.array([True, False, None], dtype=pd.BooleanDtype()),
            }
        )
    )


# ---------------------------------------------------------------------------
# to_polars basic
# ---------------------------------------------------------------------------


class TestToPolarsBasic:
    """ar.to_polars() happy-path tests."""

    @pytest.fixture(autouse=True)
    def skip_if_missing(self):
        pytest.importorskip("polars")
        pytest.importorskip("pyarrow")

    def test_returns_polars_dataframe(self):
        import polars as pl

        import arnio as ar

        frame = _make_arframe()
        result = ar.to_polars(frame)
        assert isinstance(result, pl.DataFrame)

    def test_column_names_preserved(self):
        import arnio as ar

        frame = _make_arframe()
        result = ar.to_polars(frame)
        assert result.columns == ["name", "age", "score", "active"]

    def test_row_count(self):
        import arnio as ar

        frame = _make_arframe()
        result = ar.to_polars(frame)
        assert len(result) == 3

    def test_int64_dtype(self):
        import polars as pl

        import arnio as ar

        frame = _make_arframe()
        result = ar.to_polars(frame)
        assert result["age"].dtype == pl.Int64

    def test_float64_dtype(self):
        import polars as pl

        import arnio as ar

        frame = _make_arframe()
        result = ar.to_polars(frame)
        assert result["score"].dtype == pl.Float64

    def test_bool_dtype(self):
        import polars as pl

        import arnio as ar

        frame = _make_arframe()
        result = ar.to_polars(frame)
        assert result["active"].dtype == pl.Boolean

    def test_string_dtype(self):
        import polars as pl

        import arnio as ar

        frame = _make_arframe()
        result = ar.to_polars(frame)
        # Polars uses Utf8 (or String alias in ≥0.19) for string columns
        assert result["name"].dtype in (pl.Utf8, pl.String)

    def test_values_correct(self):
        import arnio as ar

        frame = _make_arframe()
        result = ar.to_polars(frame)
        assert result["age"][0] == 25
        assert result["score"][1] == pytest.approx(7.0)
        assert result["active"][0] is True


# ---------------------------------------------------------------------------
# from_polars basic
# ---------------------------------------------------------------------------


class TestFromPolarsBasic:
    """ar.from_polars() happy-path tests."""

    @pytest.fixture(autouse=True)
    def skip_if_missing(self):
        pytest.importorskip("polars")
        pytest.importorskip("pyarrow")

    def test_returns_arframe(self):
        import polars as pl

        import arnio as ar
        from arnio.frame import ArFrame

        pldf = pl.DataFrame({"x": [1, 2, 3], "y": ["a", "b", "c"]})
        result = ar.from_polars(pldf)
        assert isinstance(result, ArFrame)

    def test_column_names_preserved(self):
        import polars as pl

        import arnio as ar

        pldf = pl.DataFrame({"x": [1, 2], "y": ["a", "b"]})
        frame = ar.from_polars(pldf)
        assert frame.columns == ["x", "y"]

    def test_row_count(self):
        import polars as pl

        import arnio as ar

        pldf = pl.DataFrame({"x": [1, 2, 3]})
        frame = ar.from_polars(pldf)
        assert frame.shape[0] == 3


# ---------------------------------------------------------------------------
# Round-trip dtype fidelity
# ---------------------------------------------------------------------------


class TestRoundTripDtypeFidelity:
    """int64 / float64 / bool / string survive from_polars → to_polars."""

    @pytest.fixture(autouse=True)
    def skip_if_missing(self):
        pytest.importorskip("polars")
        pytest.importorskip("pyarrow")

    def test_int64_round_trip(self):
        import polars as pl

        import arnio as ar

        pldf = pl.DataFrame({"n": pl.Series([1, 2, 3], dtype=pl.Int64)})
        result = ar.to_polars(ar.from_polars(pldf))
        assert result["n"].dtype == pl.Int64
        assert result["n"].to_list() == [1, 2, 3]

    def test_float64_round_trip(self):
        import polars as pl

        import arnio as ar

        pldf = pl.DataFrame({"f": pl.Series([1.1, 2.2, 3.3], dtype=pl.Float64)})
        result = ar.to_polars(ar.from_polars(pldf))
        assert result["f"].dtype == pl.Float64
        assert result["f"][0] == pytest.approx(1.1)

    def test_bool_round_trip(self):
        import polars as pl

        import arnio as ar

        pldf = pl.DataFrame({"b": pl.Series([True, False, True], dtype=pl.Boolean)})
        result = ar.to_polars(ar.from_polars(pldf))
        assert result["b"].dtype == pl.Boolean
        assert result["b"].to_list() == [True, False, True]

    def test_string_round_trip(self):
        import polars as pl

        import arnio as ar

        pldf = pl.DataFrame({"s": ["hello", "world"]})
        result = ar.to_polars(ar.from_polars(pldf))
        assert result["s"].to_list() == ["hello", "world"]

    def test_full_round_trip_values(self):
        import polars as pl

        import arnio as ar

        pldf = pl.DataFrame(
            {
                "name": ["Alice", "Bob"],
                "age": pl.Series([25, 30], dtype=pl.Int64),
                "score": pl.Series([9.5, 7.0], dtype=pl.Float64),
                "active": pl.Series([True, False], dtype=pl.Boolean),
            }
        )
        result = ar.to_polars(ar.from_polars(pldf))
        assert result["name"].to_list() == ["Alice", "Bob"]
        assert result["age"].to_list() == [25, 30]
        assert result["score"][0] == pytest.approx(9.5)
        assert result["active"].to_list() == [True, False]


# ---------------------------------------------------------------------------
# Null preservation
# ---------------------------------------------------------------------------


class TestNullsPreserved:
    @pytest.fixture(autouse=True)
    def skip_if_missing(self):
        pytest.importorskip("polars")
        pytest.importorskip("pyarrow")

    def test_to_polars_nulls_preserved(self):
        import arnio as ar

        frame = _make_arframe()
        result = ar.to_polars(frame)
        # third row is None for all columns
        assert result["name"][2] is None
        assert result["age"][2] is None
        assert result["score"][2] is None
        assert result["active"][2] is None

    def test_from_polars_nulls_preserved(self):
        import polars as pl

        import arnio as ar

        pldf = pl.DataFrame(
            {
                "x": pl.Series([1, None, 3], dtype=pl.Int64),
                "y": ["a", None, "c"],
            }
        )
        frame = ar.from_polars(pldf)
        pd_df = ar.to_pandas(frame)
        assert pd.isna(pd_df["x"].iloc[1])
        assert pd.isna(pd_df["y"].iloc[1])


# ---------------------------------------------------------------------------
# Unsupported dtype
# ---------------------------------------------------------------------------


class TestUnsupportedDtype:
    @pytest.fixture(autouse=True)
    def skip_if_missing(self):
        pytest.importorskip("polars")
        pytest.importorskip("pyarrow")

    def test_from_polars_date_raises_typeerror(self):
        from datetime import date

        import polars as pl

        import arnio as ar

        pldf = pl.DataFrame({"d": pl.Series([date(2024, 1, 1), date(2024, 6, 1)])})
        with pytest.raises(TypeError, match="Date"):
            ar.from_polars(pldf)

    def test_from_polars_datetime_raises_typeerror(self):
        from datetime import datetime

        import polars as pl

        import arnio as ar

        pldf = pl.DataFrame({"dt": [datetime(2024, 1, 1), datetime(2024, 6, 1)]})
        with pytest.raises(TypeError, match="Datetime"):
            ar.from_polars(pldf)

    def test_from_polars_list_raises_typeerror(self):
        import polars as pl

        import arnio as ar

        pldf = pl.DataFrame({"lst": [[1, 2], [3, 4]]})
        with pytest.raises(TypeError, match="List"):
            ar.from_polars(pldf)

    def test_error_message_contains_fix_hint(self):
        from datetime import date

        import polars as pl

        import arnio as ar

        pldf = pl.DataFrame({"d": pl.Series([date(2024, 1, 1)])})
        with pytest.raises(TypeError, match="cast"):
            ar.from_polars(pldf)


# ---------------------------------------------------------------------------
# Missing polars → ImportError
# ---------------------------------------------------------------------------


class TestMissingPolars:
    def test_to_polars_missing_polars_raises_importerror(self):
        import arnio as ar

        frame = ar.from_pandas(pd.DataFrame({"x": [1, 2]}))
        with patch.dict(sys.modules, {"polars": None}):
            with pytest.raises(ImportError, match="polars"):
                ar.to_polars(frame)

    def test_from_polars_missing_polars_raises_importerror(self):
        import arnio as ar

        dummy = (
            object()
        )  # not a pl.DataFrame — doesn't matter, polars import fails first
        with patch.dict(sys.modules, {"polars": None}):
            with pytest.raises(ImportError, match="polars"):
                ar.from_polars(dummy)


# ---------------------------------------------------------------------------
# Install contract: pyarrow is bundled in arnio[polars]
# ---------------------------------------------------------------------------


class TestInstallContract:
    """Verify that missing pyarrow surfaces the correct arnio[polars] hint."""

    def test_from_polars_missing_pyarrow_hints_polars_extra(self):
        """When pyarrow is absent, the ImportError should say arnio[polars]."""
        import arnio as ar

        with patch.dict(sys.modules, {"pyarrow": None}):
            # polars must be present for the pyarrow check to be reached;
            # skip if polars is not installed in this environment.
            try:
                import polars as pl

                pldf = pl.DataFrame({"x": [1, 2]})
            except ImportError:
                pytest.skip("polars not installed")

            with pytest.raises(ImportError, match=r"arnio\[polars\]"):
                ar.from_polars(pldf)

    def test_to_polars_missing_pyarrow_surfaces_error(self):
        """to_polars() delegates to to_arrow() which raises ImportError for pyarrow."""
        import arnio as ar

        frame = ar.from_pandas(pd.DataFrame({"x": [1, 2]}))
        with patch.dict(sys.modules, {"pyarrow": None}):
            with pytest.raises(ImportError):
                ar.to_polars(frame)


# ---------------------------------------------------------------------------
# Arrow bridge: from_polars does NOT go through pandas
# ---------------------------------------------------------------------------


class TestArrowBridgeNoPandas:
    """Verify that from_polars() uses _from_arrow_table, not from_pandas."""

    @pytest.fixture(autouse=True)
    def skip_if_missing(self):
        pytest.importorskip("polars")
        pytest.importorskip("pyarrow")

    def test_from_polars_does_not_call_from_pandas(self):
        """from_polars() must not invoke from_pandas() internally."""
        import polars as pl

        import arnio as ar
        from arnio import convert as _convert_mod

        pldf = pl.DataFrame({"x": pl.Series([1, 2, 3], dtype=pl.Int64)})

        with patch.object(
            _convert_mod, "from_pandas", wraps=_convert_mod.from_pandas
        ) as mock_fp:
            result = ar.from_polars(pldf)
            mock_fp.assert_not_called()

        assert result.shape == (3, 1)

    def test_from_polars_calls_from_arrow_table(self):
        """from_polars() must route through _from_arrow_table()."""
        import polars as pl

        import arnio as ar
        from arnio import convert as _convert_mod

        pldf = pl.DataFrame({"a": [1, 2], "b": ["x", "y"]})

        with patch.object(
            _convert_mod, "_from_arrow_table", wraps=_convert_mod._from_arrow_table
        ) as mock_fat:
            ar.from_polars(pldf)
            mock_fat.assert_called_once()

    def test_int_columns_via_arrow_bridge(self):
        import polars as pl

        import arnio as ar

        pldf = pl.DataFrame({"n": pl.Series([10, 20, 30], dtype=pl.Int64)})
        frame = ar.from_polars(pldf)
        pd_out = ar.to_pandas(frame)
        assert pd_out["n"].tolist() == [10, 20, 30]

    def test_float_columns_via_arrow_bridge(self):
        import polars as pl

        import arnio as ar

        pldf = pl.DataFrame({"f": pl.Series([1.5, 2.5], dtype=pl.Float64)})
        frame = ar.from_polars(pldf)
        pd_out = ar.to_pandas(frame)
        assert pd_out["f"][0] == pytest.approx(1.5)

    def test_bool_columns_via_arrow_bridge(self):
        import polars as pl

        import arnio as ar

        pldf = pl.DataFrame({"b": pl.Series([True, False, True], dtype=pl.Boolean)})
        frame = ar.from_polars(pldf)
        pd_out = ar.to_pandas(frame)
        assert list(pd_out["b"]) == [True, False, True]

    def test_string_columns_via_arrow_bridge(self):
        import polars as pl

        import arnio as ar

        pldf = pl.DataFrame({"s": ["hello", "world"]})
        frame = ar.from_polars(pldf)
        pd_out = ar.to_pandas(frame)
        assert list(pd_out["s"]) == ["hello", "world"]

    def test_nulls_preserved_via_arrow_bridge(self):
        import polars as pl

        import arnio as ar

        pldf = pl.DataFrame(
            {
                "x": pl.Series([1, None, 3], dtype=pl.Int64),
                "y": ["a", None, "c"],
            }
        )
        frame = ar.from_polars(pldf)
        pd_out = ar.to_pandas(frame)
        assert pd.isna(pd_out["x"].iloc[1])
        assert pd.isna(pd_out["y"].iloc[1])


class TestWrongType:
    @pytest.fixture(autouse=True)
    def skip_if_missing(self):
        pytest.importorskip("polars")
        pytest.importorskip("pyarrow")

    def test_from_polars_dict_raises_typeerror(self):
        import arnio as ar

        with pytest.raises(TypeError, match="polars.DataFrame"):
            ar.from_polars({"x": [1, 2]})

    def test_from_polars_pandas_df_raises_typeerror(self):
        import arnio as ar

        with pytest.raises(TypeError, match="polars.DataFrame"):
            ar.from_polars(pd.DataFrame({"x": [1, 2]}))

    def test_to_polars_pandas_df_raises_typeerror(self):
        import arnio as ar

        with pytest.raises(TypeError, match="ArFrame"):
            ar.to_polars(pd.DataFrame({"x": [1, 2]}))

    def test_to_polars_none_raises_typeerror(self):
        import arnio as ar

        with pytest.raises(TypeError, match="ArFrame"):
            ar.to_polars(None)
