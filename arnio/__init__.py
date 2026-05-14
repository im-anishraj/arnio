"""
arnio — Fast CSV processing and data cleaning companion for pandas.

import arnio as ar
"""

try:
    from importlib.metadata import version

    __version__ = version("arnio")
except Exception:
    __version__ = "unknown"

from .cleaning import (
    cast_types,
    clean,
    drop_duplicates,
    drop_nulls,
    fill_nulls,
    normalize_case,
    rename_columns,
    strip_whitespace,
)
from .convert import from_pandas, to_pandas
from .exceptions import ArnioError, CsvReadError, TypeCastError, UnknownStepError
from .frame import ArFrame
from .io import read_csv, scan_csv
from .pipeline import pipeline, register_step

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
    "ArnioError",
    "CsvReadError",
    "TypeCastError",
]
