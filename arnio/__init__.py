"""arnio — Fast CSV processing and data cleaning companion for pandas.

import arnio as ar
"""

from ._version import __version__ as __version__

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

try:
    from .cleaning import (
        CastFailure,
        CastReport,
        cast_types,
        clean,
        clean_column_names,
        clip_numeric,
        coalesce_columns,
        combine_columns,
        drop_columns,
        drop_columns_matching,
        drop_constant_columns,
        drop_duplicates,
        drop_empty_columns,
        drop_nulls,
        fill_nulls,
        filter_rows,
        find_fuzzy_duplicates,
        keep_rows_with_nulls,
        normalize_case,
        normalize_minmax,
        normalize_unicode,
        normalize_whitespace,
        parse_bool_strings,
        rename_columns,
        rename_columns_matching,
        replace_values,
        round_numeric_columns,
        safe_divide_columns,
        select_columns,
        slugify_column_names,
        standardize_missing_tokens,
        strip_whitespace,
        trim_column_names,
        validate_columns_exist,
        winsorize_outliers,
    )
    from .convert import from_dict, from_pandas, from_polars, to_arrow, to_pandas, to_polars
    from .encode_categorical import encode_categorical
    from .exceptions import (
        ArnioError,
        CsvReadError,
        JsonlReadError,
        PipelineSerializationError,
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
        write_json,
        write_parquet,
    )
    from .pipeline import (
        LineageReport,
        PipelineContext,
        get_builtin_step_signatures,
        list_steps,
        load_pipeline,
        pipeline,
        register_step,
        reset_steps,
        save_pipeline,
        unregister_step,
    )
    from .quality import (
        CleanExplanation,
        CleaningSuggestion,
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
        LanguageCode,
        PhoneNumber,
        Regex,
        Schema,
        SchemaDiff,
        SchemaDiffEntry,
        String,
        TimeZone,
        ValidationIssue,
        ValidationResult,
        diff_schema,
        register_validator,
        validate,
        validate_chunked,
    )
    from .schema_export import schema_from_yaml, schema_to_dict, schema_to_yaml

    from_records = ArFrame.from_records

except ImportError as e:
    _import_err = e

    class _DummyPlaceholder:
        def __init__(self, *args, **kwargs):
            raise _import_err
        def __call__(self, *args, **kwargs):
            raise _import_err
        def __getattr__(self, name):
            raise _import_err

    _placeholder = _DummyPlaceholder()
    for _name in __all__:
        if _name != "from_records":
            globals()[_name] = _placeholder
    from_records = _placeholder
