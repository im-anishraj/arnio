"""Integration helpers for the Python data ecosystem."""

import importlib

from .duckdb import register_duckdb
from .pandas import ArnioPandasAccessor

__all__ = [
    "ArnioPandasAccessor",
    "register_duckdb",
    "ArnioCleaner",
    "from_polars",
    "to_polars",
]

# Lazy imports: these are only available when the optional dependency is installed.
# This keeps the base `arnio` import free of any sklearn or polars dependency.
_LAZY_IMPORTS = {
    "ArnioCleaner": ("arnio.integrations.sklearn", "ArnioCleaner"),
    "from_polars": ("arnio.integrations.polars", "from_polars"),
    "to_polars": ("arnio.integrations.polars", "to_polars"),
}


def __getattr__(name: str):
    if name in _LAZY_IMPORTS:
        module_path, attr = _LAZY_IMPORTS[name]
        try:
            module = importlib.import_module(module_path)
            return getattr(module, attr)
        except ImportError:
            if name in ("from_polars", "to_polars"):
                raise ImportError(
                    f"'{name}' requires polars. "
                    "Install it with: pip install arnio[polars]"
                ) from None
            raise ImportError(
                f"'{name}' requires scikit-learn. "
                "Install it with: pip install arnio[sklearn]"
            ) from None
    raise AttributeError(f"module 'arnio.integrations' has no attribute {name!r}")
