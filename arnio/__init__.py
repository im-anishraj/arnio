"""
Arnio — High-performance C++ Data Cleaning for Python.

Arnio is a compiled C++ engine designed to handle messy data ingestion and cleaning
BEFORE it reaches pandas. It minimizes memory spikes and maximizes speed by
performing heavy lifting natively in columnar memory.

Key Features:
- 🚀 Fast C++ CSV parser with type inference.
- 🧹 Declarative cleaning pipelines (drop_nulls, strip_whitespace, etc.).
- 📊 Data profiling and quality reporting.
- ✅ Schema validation for production data contracts.
- ⚡ Zero-copy bridge to pandas/NumPy.

Quickstart:
    >>> import arnio as ar
    >>> frame = ar.read_csv("data.csv")
    >>> clean = ar.pipeline(frame, [("strip_whitespace",), ("drop_duplicates",)])
    >>> df = ar.to_pandas(clean)
"""

try:
    from importlib.metadata import version

    __version__ = version("arnio")
except Exception:
    __version__ = "unknown"

from .cleaning import (
    cast_types,
    clean,
    clip_numeric,
    drop_constant_columns,
    drop_duplicates,
    drop_nulls,
    fill_nulls,
    filter_rows,
    keep_rows_with_nulls,
    normalize_case,
    rename_columns,
    round_numeric_columns,
    safe_divide_columns,
    strip_whitespace,
    trim_column_names,
    validate_columns_exist,
)
from .convert import from_pandas, to_pandas
from .exceptions import ArnioError, CsvReadError, TypeCastError, UnknownStepError
from .frame import ArFrame
from .integrations import ArnioPandasAccessor
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
    "keep_rows_with_nulls",
    "fill_nulls",
    "validate_columns_exist",
    "filter_rows",
    "drop_duplicates",
    "drop_constant_columns",
    "clip_numeric",
    "strip_whitespace",
    "normalize_case",
    "rename_columns",
    "round_numeric_columns",
    "cast_types",
    "clean",
    "safe_divide_columns",
    "trim_column_names",
    # Conversion
    "to_pandas",
    "from_pandas",
    # Integrations
    "ArnioPandasAccessor",
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
