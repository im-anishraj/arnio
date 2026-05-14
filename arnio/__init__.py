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
    filter_rows,
    normalize_case,
    parse_bool_strings,
    rename_columns,
    strip_whitespace,
)
from .convert import from_pandas, to_pandas
from .exceptions import ArnioError, CsvReadError, TypeCastError, UnknownStepError
from .frame import ArFrame
from .io import read_csv, scan_csv
from .pipeline import pipeline, register_step
from .quality import (
    ColumnProfile,
    DataQualityReport,
    auto_clean,
    profile,
    suggest_cleaning,
)
from .schema import (
    URL,
    Bool,
    Email,
    Field,
    Float64,
    Int64,
    Schema,
    String,
    ValidationIssue,
    ValidationResult,
    validate,
)

__all__ = [
    # Core class
    "ArFrame",
    # I/O
    "read_csv",
    "scan_csv",
    # Cleaning
    "drop_nulls",
    "fill_nulls",
    "filter_rows",
    "drop_duplicates",
    "strip_whitespace",
    "parse_bool_strings",
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
    # Data quality
    "profile",
    "suggest_cleaning",
    "auto_clean",
    "ColumnProfile",
    "DataQualityReport",
    # Schema validation
    "Schema",
    "Field",
    "ValidationIssue",
    "ValidationResult",
    "validate",
    "Int64",
    "Float64",
    "String",
    "Bool",
    "Email",
    "URL",
    # Exceptions
    "UnknownStepError",
    "ArnioError",
    "CsvReadError",
    "TypeCastError",
]
