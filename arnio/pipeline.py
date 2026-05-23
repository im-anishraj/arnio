"""
arnio.pipeline
Chained cleaning pipeline.
"""

from __future__ import annotations

import inspect
import warnings
from threading import Lock
from time import perf_counter
from typing import Any, Callable

import pandas as pd

from . import cleaning
from .convert import from_pandas, to_pandas
from .exceptions import PipelineStepError, UnknownStepError
from .frame import ArFrame

StepCallable = Callable[..., Any]
StepSpec = tuple[str, dict[str, Any]]

_BUILTIN_STEP_NAMESPACE = "builtin"
_STEP_NAMESPACE_SEPARATOR = ":"

# Map step names to cleaning functions
_STEP_REGISTRY: dict[str, StepCallable] = {
    "drop_nulls": cleaning.drop_nulls,
    "drop_columns": cleaning.drop_columns,
    "keep_rows_with_nulls": cleaning.keep_rows_with_nulls,
    "fill_nulls": cleaning.fill_nulls,
    "validate_columns_exist": cleaning.validate_columns_exist,
    "drop_duplicates": cleaning.drop_duplicates,
    "drop_constant_columns": cleaning.drop_constant_columns,
    "clip_numeric": cleaning.clip_numeric,
    "strip_whitespace": cleaning.strip_whitespace,
    "parse_bool_strings": cleaning.parse_bool_strings,
    "normalize_case": cleaning.normalize_case,
    "normalize_unicode": cleaning.normalize_unicode,
    "rename_columns": cleaning.rename_columns,
    "cast_types": cleaning.cast_types,
    "round_numeric_columns": cleaning.round_numeric_columns,
    "combine_columns": cleaning.combine_columns,
    "trim_column_names": cleaning.trim_column_names,
}

_REGISTRY_LOCK = Lock()
_DEPRECATED_STEP_ALIASES: dict[str, str] = {}
_PYTHON_STEP_REGISTRY: dict[str, StepCallable] = {
    "standardize_missing_tokens": cleaning.standardize_missing_tokens,
    "coalesce_columns": cleaning.coalesce_columns,
}


def _is_builtin_python_step(name: str, fn: Callable) -> bool:
    """Return True when a Python-registered step is part of Arnio core."""
    return getattr(fn, "__module__", "").startswith("arnio.cleaning") or (
        name == "standardize_missing_tokens"
    )


def _get_builtin_step_registry(
    python_step_registry: dict[str, Callable],
) -> dict[str, Callable]:
    """Return all built-in pipeline steps, including Python-backed ones."""
    builtin_steps = dict(_STEP_REGISTRY)
    builtin_steps.update(
        {
            name: fn
            for name, fn in python_step_registry.items()
            if _is_builtin_python_step(name, fn)
        }
    )
    return builtin_steps


def _get_namespaced_builtin_steps(
    python_step_registry: dict[str, Callable],
) -> dict[str, str]:
    """Map namespaced built-in step names to canonical step names."""
    return {
        f"{_BUILTIN_STEP_NAMESPACE}{_STEP_NAMESPACE_SEPARATOR}{name}": name
        for name in _get_builtin_step_registry(python_step_registry)
    }


def register_step(name: str, fn: StepCallable, overwrite: bool = False) -> None:
    """Register a custom Python pipeline step.

    Parameters
    ----------
    name : str
        Name of the step for use in pipelines.
    fn : Callable
        Function to call for this step. Should accept (df, **kwargs) and return modified df.
    overwrite : bool, default False
        If True, allows replacing an existing custom Python step with the same name.
        Cannot be used to overwrite built-in C++ steps.

    Raises
    ------
    ValueError
        If the step name conflicts with a built-in C++ step name, or if the name
        conflicts with an existing custom Python step and `overwrite` is False.

    Examples
    --------
    >>> def custom_clean(df, threshold=0.5):
    ...     return df.dropna(thresh=threshold)
    >>> ar.register_step("custom_clean", custom_clean)
    # Overwriting an existing custom step intentionally
    >>> def new_custom_clean(df):
    ...     return df
    >>> ar.register_step("custom_clean", new_custom_clean, overwrite=True)
    """
    with _REGISTRY_LOCK:
        if name.startswith(f"{_BUILTIN_STEP_NAMESPACE}{_STEP_NAMESPACE_SEPARATOR}"):
            raise ValueError(
                f"Cannot register '{name}': "
                f"'{_BUILTIN_STEP_NAMESPACE}{_STEP_NAMESPACE_SEPARATOR}' "
                "is reserved for built-in pipeline steps."
            )
        if name in _STEP_REGISTRY:
            raise ValueError(
                f"Cannot register '{name}': conflicts with built-in C++ step. "
                f"Use a different name."
            )
        if name in _DEPRECATED_STEP_ALIASES:
            raise ValueError(
                f"Cannot register '{name}': that name is reserved as a deprecated "
                "pipeline step alias."
            )
        if name in _PYTHON_STEP_REGISTRY and not overwrite:
            raise ValueError(
                f"Step '{name}' is already registered as a custom Python step. "
                "To intentionally overwrite it, set 'overwrite=True'."
            )
        _PYTHON_STEP_REGISTRY[name] = fn


def get_builtin_step_signatures() -> dict[str, inspect.Signature]:
    """Return normalized signatures for built-in pipeline steps.

    The returned signatures exclude the leading frame/dataframe positional
    argument so callers can inspect the kwargs they are expected to pass in
    pipeline step specs.
    """
    with _REGISTRY_LOCK:
        python_step_registry = dict(_PYTHON_STEP_REGISTRY)

    builtin_steps = dict(_STEP_REGISTRY)
    builtin_steps.update(
        {
            name: fn
            for name, fn in python_step_registry.items()
            if getattr(fn, "__module__", "").startswith("arnio.cleaning")
            or name == "standardize_missing_tokens"
        }
    )

    signatures: dict[str, inspect.Signature] = {}
    for name, fn in builtin_steps.items():
        signature = inspect.signature(fn)
        parameters = tuple(list(signature.parameters.values())[1:])
        signatures[name] = signature.replace(parameters=parameters)

    return dict(sorted(signatures.items()))


def list_steps() -> list[str]:
    """Return available pipeline step names in deterministic order."""
    with _REGISTRY_LOCK:
        python_step_names = list(_PYTHON_STEP_REGISTRY)

    return sorted(set(_STEP_REGISTRY) | set(python_step_names))


def _register_deprecated_step_alias(old_name: str, new_name: str) -> None:
    """Register a deprecated step alias that warns and forwards to `new_name`."""
    with _REGISTRY_LOCK:
        available_steps = set(_STEP_REGISTRY) | set(_PYTHON_STEP_REGISTRY)

        if new_name not in available_steps:
            raise UnknownStepError(new_name, sorted(available_steps))
        if old_name in available_steps:
            raise ValueError(
                f"Cannot deprecate '{old_name}': that step name is already registered."
            )

        existing_target = _DEPRECATED_STEP_ALIASES.get(old_name)
        if existing_target is not None and existing_target != new_name:
            raise ValueError(
                f"Deprecated alias '{old_name}' already points to '{existing_target}'."
            )

        _DEPRECATED_STEP_ALIASES[old_name] = new_name


def _resolve_step_name(name: str, deprecated_step_aliases: dict[str, str]) -> str:
    """Resolve deprecated step aliases to their canonical names."""
    canonical_name = deprecated_step_aliases.get(name)
    if canonical_name is None:
        return name

    warnings.warn(
        f"Pipeline step '{name}' is deprecated; use '{canonical_name}' instead.",
        DeprecationWarning,
        stacklevel=3,
    )
    return canonical_name


def _validate_pipeline_steps(
    steps: list[StepSpec],
    python_step_registry: dict[str, StepCallable],
    deprecated_step_aliases: dict[str, str],
) -> None:
    """Validate pipeline steps before execution begins."""

    available_steps = (
        set(_STEP_REGISTRY)
        | set(python_step_registry)
        | set(deprecated_step_aliases)
        | set(_get_namespaced_builtin_steps(python_step_registry))
    )

    for step in steps:
        if not isinstance(step, tuple) or not (1 <= len(step) <= 2):
            raise ValueError(
                f"Invalid step format: {step!r}. " "Expected (name,) or (name, kwargs)"
            )

        name = step[0]

        if not isinstance(name, str):
            raise ValueError(
                f"Invalid pipeline step name: {name!r}. " "Expected a string"
            )

        if len(step) == 2 and not isinstance(step[1], dict):
            raise ValueError(
                f"Invalid step kwargs for '{name}': " f"{step[1]!r}. Expected a dict"
            )

        if name not in available_steps:
            raise UnknownStepError(
                name,
                sorted(available_steps),
            )


def pipeline(
    frame: ArFrame,
    steps: list[StepSpec],
    *,
    return_metadata: bool = False,
    dry_run: bool = False,
) -> ArFrame | tuple[ArFrame, dict[str, Any]]:
    """Apply a list of cleaning steps sequentially.

    Each step is a tuple of (step_name,) or (step_name, kwargs_dict).
    For mapping-based steps (`cast_types`, `rename_columns`), the kwargs dict
    can be used directly as the mapping or passed as {"mapping": {...}}.

    Parameters
    ----------
    frame : ArFrame
        Input data frame.
    steps : list[tuple]
        List of steps to apply. Each step is (name,) or (name, kwargs).
    return_metadata : bool, default False
        When True, also return a metadata dictionary with per-step timing
        information in execution order.

    dry_run : bool, default False
        Validates pipeline structure and step execution without
        returning transformed output.

    Returns
    -------
    ArFrame
        Data frame with all steps applied sequentially.

    Raises
    ------
    ValueError
        If step format is invalid.
    UnknownStepError
        If step name is not registered.

    Examples
    --------
    >>> frame = ar.read_csv("data.csv")
    >>> cleaned = ar.pipeline(frame, [
    ...     ("drop_nulls", {"subset": ["age"]}),
    ...     ("strip_whitespace",),
    ...     ("drop_duplicates", {"keep": "first"}),
    ... ])
    """
    with _REGISTRY_LOCK:
        python_step_registry = dict(_PYTHON_STEP_REGISTRY)
        namespaced_builtin_steps = _get_namespaced_builtin_steps(python_step_registry)
        deprecated_step_aliases = dict(_DEPRECATED_STEP_ALIASES)

    _validate_pipeline_steps(
        steps,
        python_step_registry,
        deprecated_step_aliases,
    )

    result = frame

    step_timings: list[dict[str, Any]] = []
    applied_steps: list[str] = []
    row_counts: list[dict[str, int | str]] = []
    for step in steps:
        if not isinstance(step, tuple):
            raise ValueError(
                f"Invalid step format: {step}. Expected (name,) or (name, kwargs)"
            )

        if len(step) == 1:
            name = step[0]
            kwargs = {}
        elif len(step) == 2:
            name, kwargs = step[0], step[1]
            if not isinstance(kwargs, dict):
                raise ValueError(
                    f"Invalid step kwargs for {name!r}: {kwargs!r}. Expected a dict"
                )
        else:
            raise ValueError(
                f"Invalid step format: {step}. Expected (name,) or (name, kwargs)"
            )

        name = _resolve_step_name(name, deprecated_step_aliases)
        name = namespaced_builtin_steps.get(name, name)

        if name in _STEP_REGISTRY:
            # C++ backed step - fast path
            fn = _STEP_REGISTRY[name]
            rows_before = result.shape[0]

            started_at = perf_counter()
            if name == "rename_columns" and "mapping" not in kwargs:
                step_result = fn(result, mapping=kwargs)

                if not dry_run:
                    result = step_result

            elif name == "cast_types" and "mapping" not in kwargs:
                step_result = fn(result, kwargs)

                if not dry_run:
                    result = step_result

            else:
                target_frame = result

                step_result = fn(target_frame, **kwargs)

                if not dry_run:
                    result = step_result

            if return_metadata:
                applied_steps.append(name)
                row_counts.append(
                    {
                        "step": name,
                        "before": rows_before,
                        "after": step_result.shape[0],
                    }
                )
                step_timings.append(
                    {
                        "step": name,
                        "seconds": round(perf_counter() - started_at, 9),
                    }
                )
        elif name in python_step_registry:
            # Pure Python step - slower but contributor-friendly
            started_at = perf_counter()
            rows_before = result.shape[0]

            fn = python_step_registry[name]

            df = to_pandas(result)

            # Isolate genuine custom steps from internal core library functions
            is_builtin = _is_builtin_python_step(name, fn)

            try:
                returned = fn(df, **kwargs)
            except Exception as e:
                if is_builtin:
                    raise
                raise PipelineStepError(name, e) from e

            if returned is None:
                raise TypeError(
                    f"Custom pipeline step '{name}' returned None. "
                    "Steps must return a pandas DataFrame."
                )
            if not isinstance(returned, pd.DataFrame):
                raise TypeError(
                    f"Custom pipeline step '{name}' returned "
                    f"{type(returned).__name__!r} instead of a pandas DataFrame. "
                    "Steps must return a pandas DataFrame."
                )
            step_result = from_pandas(returned)
            if not dry_run:
                result = step_result

            if return_metadata:
                applied_steps.append(name)
                row_counts.append(
                    {
                        "step": name,
                        "before": rows_before,
                        "after": step_result.shape[0],
                    }
                )
                step_timings.append(
                    {
                        "step": name,
                        "seconds": round(perf_counter() - started_at, 9),
                    }
                )
        else:
            available = list(_STEP_REGISTRY.keys()) + list(python_step_registry.keys())
            raise UnknownStepError(name, available)

    if return_metadata:
        return result, {
            "applied_steps": applied_steps,
            "row_counts": row_counts,
            "step_timings": step_timings,
        }
    return result


register_step("filter_rows", cleaning.filter_rows)
register_step("drop_columns_matching", cleaning.drop_columns_matching)
register_step("safe_divide_columns", cleaning.safe_divide_columns)
register_step("replace_values", cleaning.replace_values)
_BUILTIN_PYTHON_STEP_REGISTRY = dict(_PYTHON_STEP_REGISTRY)


def reset_steps() -> None:
    """Restore the Python pipeline registry to built-in steps only."""
    with _REGISTRY_LOCK:
        _PYTHON_STEP_REGISTRY.clear()
        _PYTHON_STEP_REGISTRY.update(_BUILTIN_PYTHON_STEP_REGISTRY)
