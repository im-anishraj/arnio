"""
arnio.pipeline
Chained cleaning pipeline.
"""

from __future__ import annotations

from typing import Callable

from .frame import ArFrame
from . import cleaning


# Map step names to cleaning functions
_STEP_REGISTRY: dict[str, Callable] = {
    "drop_nulls": cleaning.drop_nulls,
    "fill_nulls": cleaning.fill_nulls,
    "drop_duplicates": cleaning.drop_duplicates,
    "strip_whitespace": cleaning.strip_whitespace,
    "normalize_case": cleaning.normalize_case,
    "rename_columns": cleaning.rename_columns,
    "cast_types": cleaning.cast_types,
}


_PYTHON_STEP_REGISTRY: dict[str, Callable] = {}

def register_step(name: str, fn: Callable):
    """Register a custom Python pipeline step."""
    _PYTHON_STEP_REGISTRY[name] = fn

def pipeline(
    frame: ArFrame,
    steps: list[tuple],
) -> ArFrame:
    """Apply a list of cleaning steps sequentially.

    Each step is a tuple of (step_name,) or (step_name, kwargs_dict).

    Example:
        ar.pipeline(frame, [
            ("drop_nulls", {"subset": ["age"]}),
            ("strip_whitespace",),
            ("drop_duplicates", {"keep": "first"}),
        ])
    """
    from .exceptions import UnknownStepError
    from .convert import to_pandas, from_pandas

    result = frame
    for step in steps:
        if len(step) == 1:
            name = step[0]
            kwargs = {}
        elif len(step) == 2:
            name, kwargs = step[0], step[1]
        else:
            raise ValueError(f"Invalid step format: {step}. Expected (name,) or (name, kwargs)")

        if name in _STEP_REGISTRY:
            # C++ backed step - fast path
            fn = _STEP_REGISTRY[name]
            result = fn(result, **kwargs)
        elif name in _PYTHON_STEP_REGISTRY:
            # Pure Python step - slower but contributor-friendly
            df = to_pandas(result)
            df = _PYTHON_STEP_REGISTRY[name](df, **kwargs)
            result = from_pandas(df)
        else:
            available = list(_STEP_REGISTRY.keys()) + list(_PYTHON_STEP_REGISTRY.keys())
            raise UnknownStepError(name, available)

    return result
