"""
arnio.convert
Pandas conversion functions.
"""

from __future__ import annotations

import copy as copylib
import decimal
import math
from typing import Any

import numpy as np
import pandas as pd

from ._core import _DType, _Frame
from .frame import ArFrame


def _is_nested(value: object) -> bool:
    return isinstance(value, (list, dict, tuple, set, np.ndarray))


def _to_binding_safe(value: Any) -> Any:
    """
    Internal helper that normalizes scalars for the C++ binding layer.

    Parameters
    ----------
    value : Any
        Input value to convert.

    Returns
    -------
    Any
        Value safe for C++ binding. Decimal inputs are preserved as exact
        strings. Float inputs are converted to binary float. NaN/Infinity are
        rejected.

    Raises
    ------
    ValueError
        If the value is NaN or infinite.
    """
    if isinstance(value, decimal.Decimal):
        if value.is_nan() or value.is_infinite():
            raise ValueError("Invalid financial value: NaN or Infinity.")
        return str(value)

    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            raise ValueError("Invalid financial value: NaN or Infinity.")
        return float(value)

    return value


def _check_unsupported_dtype(col_name: object, series: pd.Series) -> None:
    """Raise a clear TypeError for dtypes that arnio cannot convert."""
    dtype = series.dtype
    dtype_str = str(dtype)
    name = repr(str(col_name))

    if hasattr(dtype, "tz") or dtype_str.startswith("datetime64"):
        raise TypeError(
            f"Column {name} has unsupported dtype '{dtype_str}'.\n"
            f"  Fix: df[{name}] = df[{name}].astype(str)  "
            f"# or use .dt.strftime('%Y-%m-%d') for formatted dates"
        )

    if dtype_str.startswith("timedelta"):
        raise TypeError(
            f"Column {name} has unsupported dtype '{dtype_str}'.\n"
            f"  Fix: df[{name}] = df[{name}].dt.total_seconds()"
        )

    if hasattr(dtype, "categories"):
        raise TypeError(
            f"Column {name} has unsupported dtype 'category'.\n"
            f"  Fix: df[{name}] = df[{name}].astype(str)"
        )

    if dtype_str in ("complex128", "complex64"):
        raise TypeError(
            f"Column {name} has unsupported dtype '{dtype_str}'.\n"
            f"  Fix: df[{name}] = df[{name}].apply(str)"
        )


def _normalize_scalar(value: object) -> object:
    if isinstance(value, decimal.Decimal):
        return _to_binding_safe(value)
    if pd.isna(value):
        return None
    if isinstance(value, np.generic):
        value = value.item()
    if isinstance(value, float):
        return _to_binding_safe(value)
    if not isinstance(value, (bool, int, str)):
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

        if isinstance(raw, pd.Timestamp):
            raise TypeError(
                f"Column '{col_name}' contains unsupported scalar value "
                f"of type 'Timestamp' at value {raw!r}. "
                f'Fix: df["{col_name}"] = df["{col_name}"].astype(str)'
            )

        if isinstance(raw, pd.Timedelta):
            raise TypeError(
                f"Column '{col_name}' contains unsupported scalar value "
                f"of type 'Timedelta' at value {raw!r}. "
                f'Fix: convert df["{col_name}"] to strings or a supported '
                "numeric duration before from_pandas()"
            )

        if isinstance(raw, complex):
            raise TypeError(
                f"Column '{col_name}' contains unsupported scalar value "
                f"of type 'complex' at value {raw!r}. "
                f'Fix: split df["{col_name}"] into real/imag columns or '
                "convert it to strings before from_pandas()"
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
        When False, preserve the fast zero-copy path where supported. Some
        columns still require copies because of null-mask handling, Python
        object creation, or binding limitations. When True, return defensive
        pandas-owned copies of supported column buffers.

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
    if str(dtype) == "float64":
        return _DType.FLOAT64
    return None


def _validate_unique_column_labels(labels: pd.Index) -> None:
    seen: set[object] = set()
    dupes: list[object] = []
    for label in labels:
        if label in seen and label not in dupes:
            dupes.append(label)
        seen.add(label)
    if dupes:
        raise ValueError(
            "from_pandas() does not support duplicate column labels: "
            f"{[repr(label) for label in dupes]}"
        )

    normalized: dict[str, object] = {}
    collisions: dict[str, list[object]] = {}
    for label in labels:
        name = str(label)
        if name in normalized:
            collisions.setdefault(name, [normalized[name]]).append(label)
        else:
            normalized[name] = label

    if collisions:
        details = ", ".join(
            f"{name!r}: {[repr(label) for label in labels]}"
            for name, labels in collisions.items()
        )
        raise ValueError(
            "from_pandas() column labels must remain unique after string "
            f"conversion: {details}"
        )


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
    _validate_unique_column_labels(df.columns)

    columns = {}
    dtype_hints = {}

    for col_name in df.columns:
        series = df[col_name]
        name = str(col_name)

        _check_unsupported_dtype(col_name, series)  # NEW: check before converting

        columns[name] = _series_to_python_values(series, col_name)

        dtype_hint = _pandas_dtype_to_arnio(series.dtype)
        if dtype_hint is not None:
            dtype_hints[name] = dtype_hint

    cpp_frame = _Frame.from_dict(columns, dtype_hints)
    return ArFrame(cpp_frame, attrs=copylib.deepcopy(df.attrs))
