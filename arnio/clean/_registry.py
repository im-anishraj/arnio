"""Step registry — maps step names to step functions.

Built-in steps are registered at module load time.
Users can register custom steps via ``ar.register_step()``.
"""

from __future__ import annotations

from collections.abc import Callable
from threading import Lock

from arnio.adapt._protocol import DataFrameAdapter
from arnio.clean._steps import (
    step_cast_column,
    step_drop_columns,
    step_drop_duplicates,
    step_drop_nulls,
    step_fill_nulls,
    step_normalize_case,
    step_rename_columns,
    step_replace_values,
    step_slugify_column_names,
    step_standardize_missing,
    step_strip_whitespace,
)
from arnio.exceptions import CleaningError

# Type alias for step functions
StepFn = Callable[..., DataFrameAdapter]

_REGISTRY_LOCK = Lock()

# Built-in steps — these cannot be overwritten
_BUILTIN_STEPS: dict[str, StepFn] = {
    "strip_whitespace": step_strip_whitespace,
    "normalize_case": step_normalize_case,
    "drop_duplicates": step_drop_duplicates,
    "drop_nulls": step_drop_nulls,
    "fill_nulls": step_fill_nulls,
    "slugify_column_names": step_slugify_column_names,
    "standardize_missing": step_standardize_missing,
    "rename_columns": step_rename_columns,
    "drop_columns": step_drop_columns,
    "replace_values": step_replace_values,
    "cast_column": step_cast_column,
}

# User-registered custom steps
_CUSTOM_STEPS: dict[str, StepFn] = {}


def get_step(name: str) -> StepFn:
    """Look up a step function by name.

    Raises:
        CleaningError: If the step name is not found.
    """
    with _REGISTRY_LOCK:
        if name in _BUILTIN_STEPS:
            return _BUILTIN_STEPS[name]
        if name in _CUSTOM_STEPS:
            return _CUSTOM_STEPS[name]

    available = sorted(list_steps())
    raise CleaningError(
        name,
        f"Unknown step. Available steps: {available}\n"
        f"To add a custom step: ar.register_step('{name}', your_fn)",
    )


def register_step(name: str, fn: StepFn) -> None:
    """Register a custom cleaning step.

    The function must accept a DataFrameAdapter as the first argument
    and return a DataFrameAdapter.

    Args:
        name: Step name (used in pipelines and ``ar.clean()``).
        fn: Step function.

    Raises:
        CleaningError: If the name conflicts with a built-in step.
    """
    if name in _BUILTIN_STEPS:
        raise CleaningError(
            name,
            f"Cannot overwrite built-in step {name!r}. "
            f"Choose a different name for your custom step.",
        )
    if not callable(fn):
        raise CleaningError(name, "Step function must be callable")

    with _REGISTRY_LOCK:
        _CUSTOM_STEPS[name] = fn


def unregister_step(name: str) -> None:
    """Remove a custom cleaning step.

    Raises:
        CleaningError: If the step is built-in or not found.
    """
    if name in _BUILTIN_STEPS:
        raise CleaningError(name, "Cannot unregister built-in steps")

    with _REGISTRY_LOCK:
        if name not in _CUSTOM_STEPS:
            raise CleaningError(name, f"Custom step {name!r} not found")
        del _CUSTOM_STEPS[name]


def list_steps() -> list[str]:
    """Return all registered step names (built-in + custom)."""
    with _REGISTRY_LOCK:
        return sorted(set(_BUILTIN_STEPS) | set(_CUSTOM_STEPS))


def reset_custom_steps() -> None:
    """Remove all custom steps. Used in tests."""
    with _REGISTRY_LOCK:
        _CUSTOM_STEPS.clear()
