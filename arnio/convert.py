"""
arnio.convert
Pandas conversion functions.
"""

from __future__ import annotations

import copy

import numpy as np
import pandas as pd

if TYPE_CHECKING:
    import pyarrow as pa

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


INT64_MIN = -(2**63)
INT64_MAX = 2**63 - 1


def _normalize_scalar(value: object) -> object:
    if isinstance(value, decimal.Decimal):
        return _to_binding_safe(value)
    if pd.isna(value):
        return None
    if isinstance(value, np.generic):
        value = value.item()
    if isinstance(value, int) and not isinstance(value, bool):
        if value < -9223372036854775808 or value > 9223372036854775807:
            raise ValueError(
                f"Integer value {value} is out of bounds for signed 64-bit integer. "
                "arnio only supports signed 64-bit integers (-9223372036854775808 to 9223372036854775807)."
            )
    if isinstance(value, float):
        return _to_binding_safe(value)
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        if value < INT64_MIN or value > INT64_MAX:
            raise ValueError(
                f"Integer value {value!r} is outside the signed int64 range "
                f"[{INT64_MIN}, {INT64_MAX}]. "
                "Convert the column to string first: df[col] = df[col].astype(str)"
            )
        return value
    if not isinstance(value, str):
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

    _ALLOWED_SCALAR_TYPES = (str, int, float, bool, decimal.Decimal)

    for raw in series.tolist():
        if _is_nested(raw):
            raise TypeError(
                f"Column '{col_name}' contains unsupported nested value "
                f"of type '{type(raw).__name__}' at value {raw!r}. "
                "Convert nested objects to strings or flatten them first."
            )
        try:
            value = _normalize_scalar(raw)
        except ValueError as e:
            raise ValueError(f"Column '{col_name}': {e}") from e

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

    if not isinstance(frame, ArFrame):
        raise TypeError(
            f"to_pandas() expects an ArFrame, got {type(frame).__name__}. Use arnio.from_pandas() first."
        )

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
            if copy:
                arr = arr.copy()
            series = pd.Series(arr, dtype=pd.Float64Dtype())
            series[mask] = pd.NA
            data[name] = series
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

    if not data:
        result = pd.DataFrame(index=pd.RangeIndex(cpp_frame.num_rows()))
    else:
        result = pd.DataFrame(data)
    
    # Always preserve attrs (DO NOT condition on index)
    if frame._attrs:
        result.attrs = copylib.deepcopy(frame._attrs)

    # Restore index only if explicitly stored
    saved_index = frame._attrs.get("_arnio_index") if frame._attrs else None

    if saved_index is not None:
        result.index = saved_index.copy()

    return result


def _pandas_dtype_to_arnio(dtype: object) -> _DType | None:
    if dtype == pd.Int64Dtype():
        return _DType.INT64
    if dtype == pd.Float64Dtype() or dtype == np.dtype("float64"):
        return _DType.FLOAT64

    if dtype == pd.BooleanDtype() or dtype == np.dtype("bool"):
        return _DType.BOOL
    if dtype == pd.StringDtype():
        return _DType.STRING
    # object dtype is intentionally left to value-based inference
    if dtype == pd.BooleanDtype() or str(dtype) == "bool":
        return _DType.BOOL

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
        If the input is not a pandas DataFrame, or if DataFrame contains
        unsupported nested/complex types.

    Examples
    --------
    >>> import pandas as pd
    >>> df = pd.DataFrame({"name": ["Alice"], "age": [25]})
    >>> frame = ar.from_pandas(df)
    """
    if not isinstance(df, pd.DataFrame):
        raise TypeError(
            f"from_pandas() expects a pandas DataFrame, got {type(df).__name__}"
        )

    _validate_unique_column_labels(df.columns)

    columns = {}
    dtype_hints = {}

    for col_name in df.columns:
        series = df[col_name]
        name = str(col_name)

        _check_unsupported_dtype(col_name, series)

        columns[name] = _series_to_python_values(series, col_name)

        dtype_hint = _pandas_dtype_to_arnio(series.dtype)
        if dtype_hint is not None:
            dtype_hints[name] = dtype_hint

    cpp_frame = _Frame.from_dict(columns, dtype_hints, len(df))
    
    attrs = copylib.deepcopy(df.attrs)

    # Store index ONLY if it's not default RangeIndex

    if not isinstance(df.index, pd.RangeIndex):
        attrs["_arnio_index"] = df.index.copy()

    return ArFrame(cpp_frame, attrs=attrs)


def from_dict(data: dict) -> ArFrame:
    """Converts a dictionary into a structured ArFrame.

    Args:
        data: A dictionary where keys are column names and values are lists of data.

    Returns:
        An ArFrame representation of the input dictionary.
    """

    if not isinstance(data, dict):
        raise TypeError(f"Expected dict datatype but instead got {type(data).__name__}")
    if not all(isinstance(k, str) for k in data.keys()):
        raise TypeError("All dictionary keys must be strings")

    lengths = {}

    for col_name, value in data.items():
        if isinstance(value, dict):
            raise ValueError(f"Nested objects are not supported in column '{col_name}'")

        if isinstance(value, (str, bytes)):
            raise TypeError(
                f"Column '{col_name}' must be a sequence of values, not {type(value).__name__}"
            )

        if not hasattr(value, "__len__"):
            raise TypeError(
                f"Column '{col_name}' must be a sequence of values, not {type(value).__name__}"
            )

        lengths[col_name] = len(value)

    if lengths:
        unique_lengths = set(lengths.values())

        if len(unique_lengths) > 1:
            details = ", ".join(f"{name}={length}" for name, length in lengths.items())

            raise ValueError(f"from_dict() column lengths differ: {details}")

    df = pd.DataFrame(data)

    for col_name in df.columns:
        _check_unsupported_dtype(col_name, df[col_name])

    return from_pandas(df)
    
