"""Auto-detect input data type and return the correct adapter."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pandas as pd

from arnio.adapt._dict import DictAdapter
from arnio.adapt._pandas import PandasAdapter
from arnio.exceptions import AdapterError

if TYPE_CHECKING:
    from arnio.adapt._protocol import DataFrameAdapter


def resolve_adapter(data: Any) -> DataFrameAdapter:
    """Detect the input data type and return an appropriate adapter.

    Args:
        data: The user's data — pandas DataFrame, list of dicts,
              or column-oriented dict.

    Returns:
        A DataFrameAdapter wrapping the input data.

    Raises:
        AdapterError: If the data type is not supported.
    """
    if isinstance(data, pd.DataFrame):
        return PandasAdapter(data)

    if isinstance(data, list) and (not data or isinstance(data[0], dict)):
        return DictAdapter(data)

    if isinstance(data, dict):
        # Column-oriented dict: {"col": [values...]}
        return DictAdapter(data)

    raise AdapterError(data)
