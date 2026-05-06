"""
arnio — Fast CSV processing and data cleaning companion for pandas.

import arnio as ar
"""

try:
    from importlib.metadata import version
    __version__ = version("arnio")
except Exception:
    __version__ = "unknown"

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
    clean,
)
from .convert import to_pandas, from_pandas
from .pipeline import pipeline, register_step
from .exceptions import ArnioError, UnknownStepError, CsvReadError, TypeCastError

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
    "clean",
    # Conversion
    "to_pandas",
    "from_pandas",
    # Pipeline
    "pipeline",
    "register_step",
    # Exceptions
    "UnknownStepError",
]
