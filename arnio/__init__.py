"""arnio — Fast CSV processing and data cleaning companion for pandas.

import arnio as ar
"""

import ast
import importlib
import os
import sys
from typing import Any

try:
    from importlib.metadata import version

    __version__ = version("arnio")
except Exception:
    __version__ = "unknown"

from .cleaning import (
    cast_types,
    clean,
    clip_numeric,
    coalesce_columns,
    collapse_rare_categories,
    combine_columns,
    drop_columns,
    drop_columns_matching,
    drop_constant_columns,
    drop_duplicates,
    drop_nulls,
    fill_nulls,
    filter_rows,
    normalize_case,
    normalize_unicode,
    normalize_whitespace,
    parse_bool_strings,
    parse_numeric_strings,
    rename_columns,
    rename_columns_matching,
    replace_values,
    rolling_window,
    round_numeric_columns,
    safe_divide_columns,
    strip_whitespace,
    validate_columns_exist,
    winsorize_outliers,
)
from .convert import from_dict, from_pandas, from_polars, to_arrow, to_pandas, to_polars
from .diff import ColumnDiff, DataFrameDiffReport, diff_dataframes
from .exceptions import (
    ArnioError,
    CsvReadError,
    JsonlReadError,
    PipelineStepError,
    RemoteReadError,
    SchemaValidationError,
    TypeCastError,
    UnknownStepError,
)
from .frame import ArFrame, ColumnSummary
from .integrations import ArnioPandasAccessor, register_duckdb
from .io import (
    read_csv,
    read_csv_chunked,
    read_jsonl,
    read_jsonl_chunked,
    read_parquet,
    scan_csv,
    sniff_delimiter,
    write_csv,
    write_parquet,
)
from .pipeline import (
    LineageReport,
    PipelineContext,
    get_builtin_step_signatures,
    list_steps,
    pipeline,
    register_step,
    reset_steps,
    unregister_step,
)
from .convert import from_pandas, to_numpy, to_pandas
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
    UUID,
    Bool,
    Choice,
    CountryCode,
    CurrencyCode,
    Custom,
    Date,
    DateTime,
    Email,
    Field,
    Float64,
    Int64,
    IPAddress,
    LanguageCode,
    PhoneNumber,
    Regex,
    Schema,
    String,
    ValidationIssue,
    ValidationResult,
    validate,
)

__all__ = [
    # Core class
    "ArFrame",
    "ColumnSummary",
    # I/O
    "read_csv",
    "read_csv_chunked",
    "read_jsonl",
    "write_csv",
    "write_parquet",
    "scan_csv",
    "sniff_delimiter",
    # Cleaning
    "drop_nulls",
    "drop_columns",
    "select_columns",
    "keep_rows_with_nulls",
    "fill_nulls",
    "validate_columns_exist",
    "filter_rows",
    "replace_values",
    "drop_duplicates",
    "drop_constant_columns",
    "drop_empty_columns",
    "clip_numeric",
    "winsorize_outliers",
    "normalize_minmax",
    "collapse_rare_categories",
    "coalesce_columns",
    "combine_columns",
    "drop_columns_matching",
    "strip_whitespace",
    "parse_bool_strings",
    "parse_numeric_strings",
    "normalize_case",
    "rename_columns",
    "round_numeric_columns",
    "cast_types",
    "clean",
    "winsorize_outliers",
    "safe_divide_columns",
    "trim_column_names",
    "standardize_missing_tokens",
    "rolling_window",
    "CleaningSuggestion",
    # Conversion
    "to_pandas",
    "to_numpy",
    "from_pandas",
    "from_records",
    # Integrations
    "ArnioPandasAccessor",
    "register_duckdb",
    # Pipeline
    "pipeline",
    "register_step",
    "get_builtin_step_signatures",
    "list_steps",
    "PipelineContext",
    "reset_steps",
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
    "ColumnDiff",
    "DataFrameDiffReport",
    "diff_dataframes",
    "Int64",
    "Float64",
    "String",
    "CountryCode",
    "CurrencyCode",
    "Bool",
    "Email",
    "Choice",
    "URL",
    "PhoneNumber",
    "DateTime",
    "UUID",
    "IPAddress",
    # Exceptions
    "UnknownStepError",
    "ArnioError",
    "CsvReadError",
    "JsonlReadError",
    "TypeCastError",
    "PipelineStepError",
    "normalize_unicode",
    "Regex",
    "Custom",
    "register_validator",
    "Date",
    "schema_to_dict",
    "schema_to_yaml",
]


# This makes it publicly accessible (for the issue #345)
from .cleaning import remove_special_chars 