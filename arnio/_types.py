"""Internal type aliases and protocols for arnio."""

from __future__ import annotations

from typing import Any

import pandas as pd

# ---------------------------------------------------------------------------
# Public type alias for any data that arnio can accept
# ---------------------------------------------------------------------------

DataFrame = pd.DataFrame | dict[str, list[Any]] | list[dict[str, Any]]
"""Supported input types for arnio's public API.

- ``pd.DataFrame`` — pandas DataFrame (primary)
- ``dict[str, list]`` — column-oriented dict
- ``list[dict]`` — row-oriented list of dicts

Polars DataFrames will be added in v2.1 via the adapter layer.
"""

ColumnName = str
"""Type alias for column name strings, used for clarity in signatures."""
