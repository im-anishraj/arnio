"""
Mock for arnio._arnio_cpp — lets the pipeline tests run without the compiled
C++ extension.  Import this module before importing arnio.

The mock is intentionally minimal: it only implements the surface area that
pipeline.py, convert.py, and frame.py actually exercise during the custom-step
return-type tests.  All data is stored as a plain pandas DataFrame inside a
thin _Frame wrapper.
"""

from __future__ import annotations

import sys
import types
from enum import Enum, auto
from typing import Any

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Minimal _DType enum
# ---------------------------------------------------------------------------

class _DType(Enum):
    INT64 = auto()
    FLOAT64 = auto()
    BOOL = auto()
    STRING = auto()
    NULL = auto()


# ---------------------------------------------------------------------------
# Minimal _Column
# ---------------------------------------------------------------------------

class _Column:
    def __init__(self, name: str, series: pd.Series, dtype: _DType) -> None:
        self._name = name
        self._series = series
        self._dtype = dtype

    def name(self) -> str:
        return self._name

    def dtype(self) -> _DType:
        return self._dtype

    def get_null_mask(self) -> np.ndarray:
        return self._series.isna().to_numpy()

    def to_numpy_int(self) -> np.ndarray:
        return self._series.fillna(0).to_numpy(dtype=np.int64)

    def to_numpy_float(self) -> np.ndarray:
        return self._series.to_numpy(dtype=np.float64)

    def to_numpy_bool(self) -> np.ndarray:
        return self._series.fillna(False).to_numpy(dtype=bool)

    def to_python_list(self) -> list:
        return [None if pd.isna(v) else v for v in self._series.tolist()]

    def at(self, row: int) -> Any:
        v = self._series.iloc[row]
        return None if pd.isna(v) else v


# ---------------------------------------------------------------------------
# Minimal _Frame
# ---------------------------------------------------------------------------

_DTYPE_MAP = {
    "int64": _DType.INT64,
    "Int64": _DType.INT64,
    "float64": _DType.FLOAT64,
    "Float64": _DType.FLOAT64,
    "bool": _DType.BOOL,
    "boolean": _DType.BOOL,
    "object": _DType.STRING,
    "string": _DType.STRING,
}


def _infer_dtype(series: pd.Series) -> _DType:
    dtype_str = str(series.dtype)
    for key, val in _DTYPE_MAP.items():
        if dtype_str.startswith(key):
            return val
    return _DType.STRING


class _Frame:
    def __init__(self, df: pd.DataFrame) -> None:
        self._df = df.reset_index(drop=True)

    @classmethod
    def from_dict(
        cls,
        columns: dict[str, list],
        dtype_hints: dict | None = None,
    ) -> "_Frame":
        df = pd.DataFrame(columns)
        return cls(df)

    def shape(self) -> tuple[int, int]:
        return (len(self._df), len(self._df.columns))

    def num_rows(self) -> int:
        return len(self._df)

    def num_cols(self) -> int:
        return len(self._df.columns)

    def column_names(self) -> list[str]:
        return list(self._df.columns)

    def dtypes(self) -> dict[str, str]:
        result = {}
        for col in self._df.columns:
            dt = _infer_dtype(self._df[col])
            result[col] = dt.name.lower()
        return result

    def memory_usage(self) -> int:
        return int(self._df.memory_usage(deep=True).sum())

    def column_by_index(self, i: int) -> _Column:
        col = self._df.columns[i]
        series = self._df[col]
        return _Column(col, series, _infer_dtype(series))

    def column_by_name(self, name: str) -> _Column:
        series = self._df[name]
        return _Column(name, series, _infer_dtype(series))


# ---------------------------------------------------------------------------
# Minimal stubs for C++ cleaning functions (identity pass-throughs)
# These are only called by the C++ fast-path in pipeline; the custom-step
# tests only exercise the Python slow-path, so these never actually run.
# ---------------------------------------------------------------------------

def _drop_nulls(frame: _Frame, *, subset=None) -> _Frame:
    df = frame._df.dropna(subset=subset).reset_index(drop=True)
    return _Frame(df)


def _fill_nulls(frame: _Frame, value: Any, *, subset=None) -> _Frame:
    df = frame._df.copy()
    cols = subset if subset is not None else df.columns.tolist()
    df[cols] = df[cols].fillna(value)
    return _Frame(df)


def _drop_duplicates(frame: _Frame, *, subset=None, keep="first") -> _Frame:
    df = frame._df.drop_duplicates(subset=subset, keep=keep).reset_index(drop=True)
    return _Frame(df)


def _strip_whitespace(frame: _Frame, *, subset=None) -> _Frame:
    df = frame._df.copy()
    cols = subset if subset is not None else df.select_dtypes("object").columns
    for c in cols:
        if df[c].dtype == object:
            df[c] = df[c].str.strip()
    return _Frame(df)


def _normalize_case(frame: _Frame, *, subset=None, case_type="lower") -> _Frame:
    df = frame._df.copy()
    cols = subset if subset is not None else df.select_dtypes("object").columns
    for c in cols:
        if case_type == "lower":
            df[c] = df[c].str.lower()
        elif case_type == "upper":
            df[c] = df[c].str.upper()
        else:
            df[c] = df[c].str.title()
    return _Frame(df)


def _rename_columns(frame: _Frame, mapping: dict) -> _Frame:
    return _Frame(frame._df.rename(columns=mapping))


def _cast_types(frame: _Frame, mapping: dict) -> _Frame:
    df = frame._df.copy()
    for col, dtype in mapping.items():
        df[col] = df[col].astype(dtype)
    return _Frame(df)


# ---------------------------------------------------------------------------
# Stub classes required by _core imports
# ---------------------------------------------------------------------------

class _CsvConfig:
    pass


class _CsvReader:
    pass


class _CsvWriteConfig:
    pass


class _CsvWriter:
    pass


# ---------------------------------------------------------------------------
# Install the mock module into sys.modules BEFORE arnio is imported
# ---------------------------------------------------------------------------

def install() -> None:
    """Register the mock as arnio._arnio_cpp in sys.modules."""
    mod = types.ModuleType("arnio._arnio_cpp")
    mod.Column = _Column
    mod.Frame = _Frame
    mod.DType = _DType
    mod.CsvConfig = _CsvConfig
    mod.CsvReader = _CsvReader
    mod.CsvWriteConfig = _CsvWriteConfig
    mod.CsvWriter = _CsvWriter
    mod.cast_types = _cast_types
    mod.drop_duplicates = _drop_duplicates
    mod.drop_nulls = _drop_nulls
    mod.fill_nulls = _fill_nulls
    mod.normalize_case = _normalize_case
    mod.rename_columns = _rename_columns
    mod.strip_whitespace = _strip_whitespace
    sys.modules["arnio._arnio_cpp"] = mod
