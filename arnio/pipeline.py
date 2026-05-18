"""
arnio.pipeline
Chained cleaning pipeline.
"""

from __future__ import annotations

from threading import Lock
from time import perf_counter
from typing import Any, Callable

import pandas as pd

from . import cleaning
from .convert import from_pandas, to_pandas
from .exceptions import PipelineStepError, UnknownStepError
from .frame import ArFrame

# Map step names to cleaning functions
_STEP_REGISTRY: dict[str, Callable] = {
    "drop_nulls": cleaning.drop_nulls,
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
_PYTHON_STEP_REGISTRY: dict[str, Callable] = {
    "standardize_missing_tokens": cleaning.standardize_missing_tokens
}


def register_step(name: str, fn: Callable):
    """Register a custom Python pipeline step.

    Parameters
    ----------
    name : str
        Name of the step for use in pipelines.
    fn : Callable
        Function to call for this step. Should accept (df, **kwargs) and return modified df.

    Examples
    --------
    >>> def custom_clean(df, threshold=0.5):
    ...     return df.dropna(thresh=threshold)
    >>> ar.register_step("custom_clean", custom_clean)
    """
    with _REGISTRY_LOCK:

        _PYTHON_STEP_REGISTRY[name] = fn


def _validate_pipeline_steps(
    steps: list[tuple],
    python_step_registry: dict[str, Callable],
) -> None:
    """Validate pipeline steps before execution begins."""

    available_steps = set(_STEP_REGISTRY) | set(python_step_registry)

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
    steps: list[tuple],
    *,
    return_metadata: bool = False,
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

    _validate_pipeline_steps(
        steps,
        python_step_registry,
    )

    result = frame
    step_timings: list[dict[str, Any]] = []
    for step in steps:
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

        if name in _STEP_REGISTRY:
            # C++ backed step - fast path
            fn = _STEP_REGISTRY[name]
            started_at = perf_counter()
            if name in {"rename_columns", "cast_types"} and "mapping" not in kwargs:
                result = fn(result, kwargs)
            else:
                result = fn(result, **kwargs)
            if return_metadata:
                step_timings.append(
                    {
                        "step": name,
                        "seconds": round(perf_counter() - started_at, 9),
                    }
                )
        elif name in python_step_registry:
            # Pure Python step - slower but contributor-friendly
            started_at = perf_counter()
            fn = python_step_registry[name]
            df = to_pandas(result)

            # Isolate genuine custom steps from internal core library functions
            is_builtin = (
                getattr(fn, "__module__", "").startswith("arnio.cleaning")
                or name == "standardize_missing_tokens"
            )

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
            result = from_pandas(returned)
            if return_metadata:
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
        return result, {"step_timings": step_timings}
    return result


register_step("filter_rows", cleaning.filter_rows)
register_step("safe_divide_columns", cleaning.safe_divide_columns)
register_step("replace_values", cleaning.replace_values)
