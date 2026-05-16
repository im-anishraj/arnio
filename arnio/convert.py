"""
arnio.convert
Pandas conversion functions.
"""

from __future__ import annotations

import copy as copylib

import numpy as np
import pandas as pd

from ._core import _DType, _Frame
from .frame import ArFrame


def _is_nested(value: object) -> bool:
    return isinstance(value, (list, dict, tuple, set, np.ndarray))


def _normalize_scalar(value: object) -> object:
    if pd.isna(value):
        return None
    if isinstance(value, np.generic):
        return value.item()
    if not isinstance(value, (bool, int, float, str)):
        return str(value)
    return value


def _scalar_kind(value: object) -> str:
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int):
        return "int"
    if isinstance(value, float):
        return "float"
    return "string"


def _series_to_python_values(series: pd.Series, col_name: object) -> list[object]:
    values: list[object] = []
    kinds: set[str] = set()

    for raw in series.tolist():
        if _is_nested(raw):
            raise TypeError(
                f"Column '{col_name}' contains unsupported nested value "
                f"of type '{type(raw).__name__}' at value {raw!r}. "
                "Convert nested objects to strings or flatten them first."
            )

        value = _normalize_scalar(raw)
        values.append(value)
        if value is not None:
            kinds.add(_scalar_kind(value))

    if "string" in kinds and len(kinds) > 1:
        return [None if value is None else str(value) for value in values]

    if "bool" in kinds and len(kinds) > 1:
        return [None if value is None else str(value) for value in values]

    if kinds == {"int", "float"}:
        return [None if value is None else float(value) for value in values]

    return values


def to_pandas(frame: ArFrame, *, copy: bool = False) -> pd.DataFrame:
    """Convert ArFrame to pandas.DataFrame.

    Parameters
    ----------
    frame : ArFrame
        Input ArFrame to convert.
    copy : bool, default False
        When False, use zero-copy buffers for supported numeric and boolean
        columns where possible. When True, return defensive copies of
        supported column buffers.

    Returns
    -------
    pd.DataFrame
        Equivalent pandas DataFrame with proper dtypes and null handling.
        If the ArFrame was created via ``from_pandas()``, any ``attrs``
        metadata from the original DataFrame is restored on the result.

    Examples
    --------
    >>> frame = ar.read_csv("data.csv")
    >>> df = ar.to_pandas(frame)
    >>> defensive_df = ar.to_pandas(frame, copy=True)
    """
    if not isinstance(copy, bool):
        raise TypeError("copy must be a bool")

    cpp_frame = frame._frame
    data = {}

    for i in range(cpp_frame.num_cols()):
        col = cpp_frame.column_by_index(i)
        name = col.name()
        dtype = col.dtype()
        mask = col.get_null_mask()

        if dtype == _DType.INT64:
            arr = col.to_numpy_int()
            if copy:
                arr = arr.copy()
            # pandas Int64Dtype handles nulls via mask
            series = pd.Series(arr, dtype=pd.Int64Dtype())
            series[mask] = pd.NA
            data[name] = series
        elif dtype == _DType.FLOAT64:
            arr = col.to_numpy_float()
            if copy or mask.any():
                arr = arr.copy()
            if mask.any():
                arr[mask] = np.nan
            data[name] = arr
        elif dtype == _DType.BOOL:
            arr = col.to_numpy_bool()
            if copy:
                arr = arr.copy()
            series = pd.Series(arr, dtype=pd.BooleanDtype())
            series[mask] = pd.NA
            data[name] = series
        else:
            # STRING or unknown
            values = col.to_python_list()
            series = pd.Series(values, dtype=pd.StringDtype())
            series[mask] = pd.NA
            data[name] = series

    result = pd.DataFrame(data)
    if frame._attrs:
        result.attrs = copylib.deepcopy(frame._attrs)
    return result


def _pandas_dtype_to_arnio(dtype: object) -> _DType | None:
    if dtype == pd.Int64Dtype():
        return _DType.INT64
    return None


def from_pandas(df: pd.DataFrame) -> ArFrame:
    """Convert pandas.DataFrame to ArFrame.

    Parameters
    ----------
    df : pd.DataFrame
        Input pandas DataFrame to convert.

    Returns
    -------
    ArFrame
        Equivalent ArFrame with inferred types.

    Raises
    ------
    TypeError
        If DataFrame contains unsupported nested/complex types.

    Examples
    --------
    >>> import pandas as pd
    >>> df = pd.DataFrame({"name": ["Alice"], "age": [25]})
    >>> frame = ar.from_pandas(df)
    """
    columns = {}
    dtype_hints = {}

    for col_name in df.columns:
        series = df[col_name]
        name = str(col_name)

        columns[name] = _series_to_python_values(series, col_name)

        dtype_hint = _pandas_dtype_to_arnio(series.dtype)
        if dtype_hint is not None:
            dtype_hints[name] = dtype_hint

    cpp_frame = _Frame.from_dict(columns, dtype_hints)
    return ArFrame(cpp_frame, attrs=copylib.deepcopy(df.attrs))
