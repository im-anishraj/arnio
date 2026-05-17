"""arnio — Fast CSV processing and data cleaning companion for pandas.

import arnio as ar
"""

import importlib
from typing import Any

try:
    from importlib.metadata import version

    __version__ = version("arnio")
except Exception:
    __version__ = "unknown"

# 1. Map public names to their target submodules for lazy loading
_LAZY_MAPPING = {
    # Core class
    "ArFrame": ".frame",
    # I/O
    "read_csv": ".io",
    "scan_csv": ".io",
    # Cleaning
    "drop_nulls": ".cleaning",
    "keep_rows_with_nulls": ".cleaning",
    "fill_nulls": ".cleaning",
    "validate_columns_exist": ".cleaning",
    "filter_rows": ".cleaning",
    "replace_values": ".cleaning",
    "drop_duplicates": ".cleaning",
    "drop_constant_columns": ".cleaning",
    "clip_numeric": ".cleaning",
    "strip_whitespace": ".cleaning",
    "normalize_case": ".cleaning",
    "rename_columns": ".cleaning",
    "round_numeric_columns": ".cleaning",
    "cast_types": ".cleaning",
    "clean": ".cleaning",
    "safe_divide_columns": ".cleaning",
    "trim_column_names": ".cleaning",
    # Conversion
    "to_pandas": ".convert",
    "from_pandas": ".convert",
    # Integrations
    "ArnioPandasAccessor": ".integrations",
    # Pipeline
    "pipeline": ".pipeline",
    "register_step": ".pipeline",
    # Data quality
    "profile": ".quality",
    "suggest_cleaning": ".quality",
    "auto_clean": ".quality",
    "ColumnProfile": ".quality",
    "DataQualityReport": ".quality",
    # Schema validation
    "Schema": ".schema",
    "Field": ".schema",
    "ValidationIssue": ".schema",
    "ValidationResult": ".schema",
    "validate": ".schema",
    "Int64": ".schema",
    "Float64": ".schema",
    "String": ".schema",
    "CountryCode": ".schema",
    "Bool": ".schema",
    "Email": ".schema",
    "URL": ".schema",
    # Exceptions
    "UnknownStepError": ".exceptions",
    "ArnioError": ".exceptions",
    "CsvReadError": ".exceptions",
    "TypeCastError": ".exceptions",
}


def __getattr__(name: str) -> Any:
    """Dynamically import submodules when an attribute is accessed."""
    if name in _LAZY_MAPPING:
        submodule_name = _LAZY_MAPPING[name]
        submodule = importlib.import_module(submodule_name, __name__)
        attribute = getattr(submodule, name)
        # Cache the attribute on the module level to avoid re-importing it next time
        globals()[name] = attribute
        return attribute
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


def __dir__() -> list[str]:
    """Ensure autocomplete options work cleanly in notebooks and IDEs."""
    return sorted(list(globals().keys()) + list(_LAZY_MAPPING.keys()))


__all__ = list(_LAZY_MAPPING.keys()) + ["__version__"]
