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
    clip_numeric,
    combine_columns,
    drop_columns,
    drop_columns_matching,
    drop_constant_columns,
    drop_duplicates,
    drop_nulls,
    fill_nulls,
    filter_rows,
    keep_rows_with_nulls,
    normalize_case,
    normalize_unicode,
    parse_bool_strings,
    rename_columns,
    replace_values,
    round_numeric_columns,
    safe_divide_columns,
    standardize_missing_tokens,
    strip_whitespace,
    trim_column_names,
    validate_columns_exist,
)
from .convert import from_pandas, to_pandas
from .exceptions import (
    ArnioError,
    CsvReadError,
    PipelineStepError,
    TypeCastError,
    UnknownStepError,
)
from .frame import ArFrame
from .integrations import ArnioPandasAccessor
from .io import read_csv, scan_csv, write_csv
from .pipeline import pipeline, register_step
from .quality import (
    CleanExplanation,
    CleanStepRecord,
    ColumnProfile,
    DataQualityReport,
    ProfileComparison,
    QualityGateIssue,
    QualityGateResult,
    auto_clean,
    check_quality_gates,
    compare_profiles,
    profile,
    suggest_cleaning,
)
from .schema import (
    URL,
    Bool,
    CountryCode,
    CurrencyCode,
    Custom,
    Date,
    DateTime,
    Email,
    Field,
    Float64,
    Int64,
    PhoneNumber,
    Regex,
    Schema,
    SchemaDiff,
    SchemaDiffEntry,
    String,
    ValidationIssue,
    ValidationResult,
    diff_schema,
    register_validator,
    validate,
)

__all__ = [
    # Core class
    "ArFrame",
    # I/O
    "read_csv",
    "write_csv",
    "scan_csv",
    # Cleaning
    "drop_nulls",
    "drop_columns",
    "keep_rows_with_nulls",
    "fill_nulls",
    "validate_columns_exist",
    "filter_rows",
    "replace_values",
    "drop_duplicates",
    "drop_constant_columns",
    "clip_numeric",
    "combine_columns",
    "drop_columns_matching",
    "strip_whitespace",
    "parse_bool_strings",
    "normalize_case",
    "rename_columns",
    "round_numeric_columns",
    "cast_types",
    "clean",
    "safe_divide_columns",
    "trim_column_names",
    "standardize_missing_tokens",
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
    "compare_profiles",
    "check_quality_gates",
    "suggest_cleaning",
    "auto_clean",
    "ColumnProfile",
    "DataQualityReport",
    "CleanStepRecord",
    "CleanExplanation",
    "ProfileComparison",
    "QualityGateIssue",
    "QualityGateResult",
    # Schema validation
    "Schema",
    "SchemaDiff",
    "SchemaDiffEntry",
    "Field",
    "ValidationIssue",
    "ValidationResult",
    "validate",
    "diff_schema",
    "Int64",
    "Float64",
    "String",
    "CountryCode",
    "CurrencyCode",
    "Bool",
    "Email",
    "URL",
    "PhoneNumber",
    "DateTime",
    # Exceptions
    "UnknownStepError",
    "ArnioError",
    "CsvReadError",
    "TypeCastError",
    "PipelineStepError",
    "normalize_unicode",
    "Regex",
    "Custom",
    "register_validator",
    "Date",
]
