"""
arnio.convert
Pandas conversion functions.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from ._core import _Frame, _Column, _DType
from .frame import ArFrame


def to_pandas(frame: ArFrame) -> pd.DataFrame:
    """Convert ArFrame to pandas.DataFrame."""
    cpp_frame = frame._frame
    data: dict[str, np.ndarray] = {}

    for i in range(cpp_frame.num_cols()):
        col = cpp_frame.column_by_index(i)
        name = col.name()
        size = col.size()
        dtype = col.dtype()

        if dtype == _DType.INT64:
            # Use nullable integer to handle nulls
            values = []
            for r in range(size):
                values.append(col.at(r))
            data[name] = pd.array(values, dtype=pd.Int64Dtype())
        elif dtype == _DType.FLOAT64:
            arr = np.empty(size, dtype=np.float64)
            for r in range(size):
                val = col.at(r)
                arr[r] = float(val) if val is not None else np.nan
            data[name] = arr
        elif dtype == _DType.BOOL:
            values = []
            for r in range(size):
                values.append(col.at(r))
            data[name] = pd.array(values, dtype=pd.BooleanDtype())
        else:
            # STRING or unknown
            values = []
            for r in range(size):
                val = col.at(r)
                values.append(val if val is not None else None)
            data[name] = pd.array(values, dtype=pd.StringDtype())

    return pd.DataFrame(data)


def from_pandas(df: pd.DataFrame) -> ArFrame:
    """Convert pandas.DataFrame to ArFrame."""
    cpp_frame = _Frame()

    for col_name in df.columns:
        series = df[col_name]
        col_dtype = series.dtype

        # Determine target DType
        if pd.api.types.is_integer_dtype(col_dtype):
            target = _DType.INT64
        elif pd.api.types.is_float_dtype(col_dtype):
            target = _DType.FLOAT64
        elif pd.api.types.is_bool_dtype(col_dtype):
            target = _DType.BOOL
        else:
            target = _DType.STRING

        col = _Column(str(col_name), target)

        for val in series:
            if isinstance(val, (list, dict, tuple, set, np.ndarray)):
                raise TypeError(f"Unsupported nested/complex type in column '{col_name}': {type(val).__name__}")
            if pd.isna(val):
                col.push_null()
            elif target == _DType.INT64:
                col.push_back(int(val))
            elif target == _DType.FLOAT64:
                col.push_back(float(val))
            elif target == _DType.BOOL:
                col.push_back(bool(val))
            else:
                col.push_back(str(val))

        cpp_frame.add_column(col)

    return ArFrame(cpp_frame)
