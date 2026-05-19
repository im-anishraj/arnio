"""
arnio.pipeline
Chained cleaning pipeline.
"""

from __future__ import annotations

import json
from pathlib import Path
from threading import Lock
from time import perf_counter
from typing import Any, Callable

import pandas as pd

from . import cleaning
from .convert import from_pandas, to_pandas
from .exceptions import PipelineStepError, UnknownStepError
from .frame import ArFrame

try:
    import yaml

    HAS_YAML = True
except ImportError:
    HAS_YAML = False

# Map step names to cleaning functions
_STEP_REGISTRY: dict[str, Callable] = {
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
                f"Invalid step format: {step!r}. Expected (name,) or (name, kwargs)"
            )

        name = step[0]

        if not isinstance(name, str):
            raise ValueError(f"Invalid pipeline step name: {name!r}. Expected a string")

        if len(step) == 2 and not isinstance(step[1], dict):
            raise ValueError(
                f"Invalid step kwargs for '{name}': {step[1]!r}. Expected a dict"
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
    dry_run: bool = False,
    return_metadata: bool = False,
) -> ArFrame | tuple[ArFrame, dict[str, Any]]:
    """Apply a list of cleaning steps sequentially.

    Parameters
    ----------
    frame : ArFrame
        Input data frame.
    steps : list[tuple]
        List of steps to apply. Each step is (name,) or (name, kwargs).
    dry_run : bool, default False
        When True, validates all steps against the registry without executing them.
    return_metadata : bool, default False
        When True, returns structural execution metadata.
    """
    with _REGISTRY_LOCK:
        python_step_registry = dict(_PYTHON_STEP_REGISTRY)

    _validate_pipeline_steps(
        steps,
        python_step_registry,
    )

    if dry_run:
        if return_metadata:
            return frame, {
                "dry_run": True,
                "step_count": len(steps),
                "step_timings": [],
            }
        return frame

    result = frame
    step_timings: list[dict[str, Any]] = []
    for step in steps:
        if len(step) == 1:
            name = step[0]
            kwargs = {}
        else:
            name, kwargs = step[0], step[1]

        if name in _STEP_REGISTRY:
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
            started_at = perf_counter()
            fn = python_step_registry[name]
            df = to_pandas(result)

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
                    f"Custom pipeline step '{name}' returned None. Steps must return a pandas DataFrame."
                )
            if not isinstance(returned, pd.DataFrame):
                raise TypeError(
                    f"Custom pipeline step '{name}' returned {type(returned).__name__!r} instead of a pandas DataFrame."
                )
            result = from_pandas(returned)
            if return_metadata:
                step_timings.append(
                    {
                        "step": name,
                        "seconds": round(perf_counter() - started_at, 9),
                    }
                )

    if return_metadata:
        return result, {"step_timings": step_timings}
    return result


register_step("filter_rows", cleaning.filter_rows)
register_step("drop_columns_matching", cleaning.drop_columns_matching)
register_step("safe_divide_columns", cleaning.safe_divide_columns)
register_step("replace_values", cleaning.replace_values)


def save_pipeline(steps: list[tuple], filepath: str | Path) -> None:
    """Save a list of pipeline steps to a JSON or YAML file for reproducible jobs."""
    from .exceptions import PipelineSerializationError

    if not isinstance(steps, list):
        raise PipelineSerializationError("Pipeline steps must be a list of tuples.")

    path = Path(filepath)
    try:
        if path.suffix == ".json":
            with open(path, "w", encoding="utf-8") as f:
                json.dump(steps, f, indent=4, sort_keys=True)
        elif path.suffix in [".yaml", ".yml"]:
            if not HAS_YAML:
                raise PipelineSerializationError(
                    "PyYAML is required for YAML support. Please install it."
                )
            with open(path, "w", encoding="utf-8") as f:
                yaml.safe_dump(steps, f, sort_keys=True)
        else:
            raise PipelineSerializationError(
                f"Unsupported format: {path.suffix}. Use .json or .yaml"
            )
    except Exception as e:
        if isinstance(e, PipelineSerializationError):
            raise
        raise PipelineSerializationError(f"Failed to save pipeline: {e}")


def load_pipeline(filepath: str | Path) -> list[tuple]:
    """Load a list of pipeline steps from a JSON or YAML file."""
    from .exceptions import PipelineSerializationError

    path = Path(filepath)
    if not path.exists():
        raise PipelineSerializationError(f"File not found: {filepath}")

    try:
        if path.suffix == ".json":
            with open(path, encoding="utf-8") as f:
                content = f.read().strip()
                if not content:
                    raise PipelineSerializationError(
                        "Malformed pipeline file: file is empty."
                    )
                loaded_steps = json.loads(content)
        elif path.suffix in [".yaml", ".yml"]:
            if not HAS_YAML:
                raise PipelineSerializationError(
                    "PyYAML is required for YAML support. Please install it."
                )
            with open(path, encoding="utf-8") as f:
                content = f.read().strip()
                if not content:
                    raise PipelineSerializationError(
                        "Malformed pipeline file: file is empty."
                    )
                loaded_steps = yaml.safe_load(content)
        else:
            raise PipelineSerializationError(
                f"Unsupported format: {path.suffix}. Use .json or .yaml"
            )

        if loaded_steps is None:
            raise PipelineSerializationError(
                "Malformed pipeline file: file is empty or null."
            )
        if not isinstance(loaded_steps, list):
            raise PipelineSerializationError(
                "Malformed pipeline file: root element must be a list."
            )

        validated_steps = []
        for idx, step in enumerate(loaded_steps):
            if not isinstance(step, list):
                raise PipelineSerializationError(
                    f"Malformed pipeline step at index {idx}: step entry must be a list/tuple format."
                )
            if len(step) == 0 or len(step) > 2:
                raise PipelineSerializationError(
                    f"Malformed pipeline step at index {idx}: entry must match (name,) or (name, kwargs)."
                )
            if not isinstance(step[0], str):
                raise PipelineSerializationError(
                    f"Malformed pipeline step at index {idx}: step name must be a string."
                )
            if len(step) == 2 and not isinstance(step[1], dict):
                raise PipelineSerializationError(
                    f"Malformed pipeline step at index {idx}: kwargs must be a dictionary structure."
                )
            validated_steps.append(tuple(step))

        return validated_steps
    except Exception as e:
        if isinstance(e, PipelineSerializationError):
            raise
        raise PipelineSerializationError(f"Failed to load pipeline: {e}")
