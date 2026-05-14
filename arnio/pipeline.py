"""
arnio.pipeline
Chained cleaning pipeline.
"""

from __future__ import annotations

from typing import Callable

from . import cleaning
from .frame import ArFrame

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
    _PYTHON_STEP_REGISTRY[name] = fn


def pipeline(
    frame: ArFrame,
    steps: list[tuple],
) -> ArFrame:
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
    from .convert import from_pandas, to_pandas
    from .exceptions import UnknownStepError

    result = frame
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
            if name in {"rename_columns", "cast_types"} and "mapping" not in kwargs:
                result = fn(result, kwargs)
            else:
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
