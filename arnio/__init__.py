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

# 1. Base fallback dictionary containing the absolute known public surface of arnio
_LAZY_MAPPING: dict[str, str] = {
    "ArFrame": ".frame",
    "read_csv": ".io",
    "scan_csv": ".io",
    "combine_columns": ".cleaning",
    "drop_nulls": ".cleaning",
    "keep_rows_with_nulls": ".cleaning",
    "fill_nulls": ".cleaning",
    "validate_columns_exist": ".cleaning",
    "filter_rows": ".cleaning",
    "replace_values": ".cleaning",
    "drop_duplicates": ".cleaning",
    "constant_columns": ".cleaning",
    "drop_constant_columns": ".cleaning",
    "clip_numeric": ".cleaning",
    "strip_whitespace": ".cleaning",
    "normalize_case": ".cleaning",
    "normalize_unicode": ".cleaning",
    "rename_columns": ".cleaning",
    "round_numeric_columns": ".cleaning",
    "cast_types": ".cleaning",
    "clean": ".cleaning",
    "safe_divide_columns": ".cleaning",
    "trim_column_names": ".cleaning",
    "to_pandas": ".convert",
    "from_pandas": ".convert",
    "ArnioPandasAccessor": ".integrations",
    "pipeline": ".pipeline",
    "register_step": ".pipeline",
    "profile": ".quality",
    "suggest_cleaning": ".quality",
    "auto_clean": ".quality",
    "ColumnProfile": ".quality",
    "DataQualityReport": ".quality",
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
    "DateTime": ".schema",
    "UnknownStepError": ".exceptions",
    "ArnioError": ".exceptions",
    "CsvReadError": ".exceptions",
    "TypeCastError": ".exceptions",
}

# 2. Track package folders to dynamically scan for updates without running them
_SUBMODULES = [
    ".frame",
    ".io",
    ".cleaning",
    ".convert",
    ".integrations",
    ".pipeline",
    ".quality",
    ".schema",
    ".exceptions",
]

# 3. Textual AST parsing to pull new developer additions without memory leaks
_CURRENT_DIR = os.path.dirname(__file__)
for submodule_path in _SUBMODULES:
    filename = submodule_path.lstrip(".") + ".py"
    filepath = os.path.join(_CURRENT_DIR, filename)

    if not os.path.exists(filepath):
        continue

    try:
        with open(filepath, encoding="utf-8") as f:
            tree = ast.parse(f.read(), filename=filepath)

        for node in tree.body:
            if (
                isinstance(node, ast.Assign)
                and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)
                and node.targets[0].id == "__all__"
            ):
                if isinstance(node.value, (ast.List, ast.Tuple)):
                    for elt in node.value.elts:
                        if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                            if elt.value not in _LAZY_MAPPING:
                                _LAZY_MAPPING[elt.value] = submodule_path
                        elif isinstance(elt, ast.Str):
                            if elt.s not in _LAZY_MAPPING:
                                _LAZY_MAPPING[elt.s] = submodule_path
    except Exception:
        continue

_INTEGRATIONS_LOADED = False


# 4. Use a robust Proxy class module replacement pattern
class _LazyModuleProxy:
    def __init__(self, orig_module: Any):
        self.__dict__["_orig_module"] = orig_module

    def __getattr__(self, name: str) -> Any:
        global _INTEGRATIONS_LOADED

        # Automatically bind pandas integrations ONLY if pandas is already actively running
        if "pandas" in sys.modules and not _INTEGRATIONS_LOADED:
            _INTEGRATIONS_LOADED = True
            try:
                importlib.import_module(
                    ".integrations", self.__dict__["_orig_module"].__name__
                )
            except Exception:
                pass

        if name in _LAZY_MAPPING:
            submodule_name = _LAZY_MAPPING[name]
            submodule = importlib.import_module(
                submodule_name, self.__dict__["_orig_module"].__name__
            )

            if hasattr(submodule, name):
                attr = getattr(submodule, name)
                if isinstance(attr, type(sys)) and attr.__name__.endswith(f".{name}"):
                    if hasattr(attr, name):
                        return getattr(attr, name)
                return attr
            return submodule

        return getattr(self.__dict__["_orig_module"], name)

    def __setattr__(self, name: str, value: Any) -> None:
        setattr(self.__dict__["_orig_module"], name, value)

    def __dir__(self) -> list[str]:
        return sorted(list(_LAZY_MAPPING.keys()) + ["__version__", "__all__"])


# Fetch the raw original module layout
_orig_module = sys.modules[__name__]
__all__ = list(_LAZY_MAPPING.keys()) + ["__version__"]

# Overwrite system module table entry safely using the proxy boundary shell
sys.modules[__name__] = _LazyModuleProxy(_orig_module)  # type: ignore
