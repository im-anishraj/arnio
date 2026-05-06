"""
arnio.convert
Pandas conversion functions.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from ._core import _Frame, _DType
from .frame import ArFrame


def to_pandas(frame: ArFrame) -> pd.DataFrame:
    """Convert ArFrame to pandas.DataFrame."""
    cpp_frame = frame._frame
    data = {}

    for i in range(cpp_frame.num_cols()):
        col = cpp_frame.column_by_index(i)
        name = col.name()
        dtype = col.dtype()
        mask = col.get_null_mask()

        if dtype == _DType.INT64:
            arr = col.to_numpy_int()
            # pandas Int64Dtype handles nulls via mask
            series = pd.Series(arr, dtype=pd.Int64Dtype())
            series[mask] = pd.NA
            data[name] = series
        elif dtype == _DType.FLOAT64:
            arr = col.to_numpy_float().copy()
            arr[mask] = np.nan
            data[name] = arr
        elif dtype == _DType.BOOL:
            arr = col.to_numpy_bool()
            series = pd.Series(arr, dtype=pd.BooleanDtype())
            series[mask] = pd.NA
            data[name] = series
        else:
            # STRING or unknown
            values = col.to_python_list()
            series = pd.Series(values, dtype=pd.StringDtype())
            series[mask] = pd.NA
            data[name] = series

    return pd.DataFrame(data)


def from_pandas(df: pd.DataFrame) -> ArFrame:
    """Convert pandas.DataFrame to ArFrame."""
    columns = {}
    for col_name in df.columns:
        series = df[col_name]
        if series.dtype == object:
            for val in series:
                if isinstance(val, (list, dict, tuple, set, np.ndarray)):
                    raise TypeError(
                        f"Unsupported nested/complex type in column '{col_name}': {type(val).__name__}"
                    )

        # Convert pandas series to python list.
        # This handles pd.NA natively by converting to None in the resulting list.
        # It takes one boundary crossing per column.
        columns[str(col_name)] = series.replace({pd.NA: None, np.nan: None}).tolist()

    cpp_frame = _Frame.from_dict(columns)
    return ArFrame(cpp_frame)
