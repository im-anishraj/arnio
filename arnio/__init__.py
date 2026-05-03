"""
arnio — Fast CSV processing and data cleaning companion for pandas.

import arnio as ar
"""

__version__ = "0.1.1"

from .frame import ArFrame
from .io import read_csv, scan_csv
from .cleaning import (
    drop_nulls,
    fill_nulls,
    drop_duplicates,
    strip_whitespace,
    normalize_case,
    rename_columns,
    cast_types,
)
from .convert import to_pandas, from_pandas
from .pipeline import pipeline

__all__ = [
    # Core class
    "ArFrame",
    # I/O
    "read_csv",
    "scan_csv",
    # Cleaning
    "drop_nulls",
    "fill_nulls",
    "drop_duplicates",
    "strip_whitespace",
    "normalize_case",
    "rename_columns",
    "cast_types",
    # Conversion
    "to_pandas",
    "from_pandas",
    # Pipeline
    "pipeline",
]
