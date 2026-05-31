"""Integration helpers for the Python data ecosystem."""

import importlib

from .duckdb import register_duckdb
from .pandas import ArnioPandasAccessor

__all__ = ["ArnioPandasAccessor", "register_duckdb", "ArnioCleaner"]

# Lazy import: ArnioCleaner is only available when scikit-learn is installed.
# This keeps the base `arnio` import free of any sklearn dependency.
_LAZY_IMPORTS = {
    "ArnioCleaner": ("arnio.integrations.sklearn", "ArnioCleaner"),
}


def __getattr__(name: str):
    if name in _LAZY_IMPORTS:
        module_path, attr = _LAZY_IMPORTS[name]
        try:
            module = importlib.import_module(module_path)
            return getattr(module, attr)
        except ImportError:
            raise ImportError(
                f"'{name}' requires scikit-learn. "
                "Install it with: pip install arnio[sklearn]"
            ) from None
    raise AttributeError(f"module 'arnio.integrations' has no attribute {name!r}")
