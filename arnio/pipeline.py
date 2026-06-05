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
    "drop_columns": cleaning.drop_columns,
    "keep_rows_with_nulls": cleaning.keep_rows_with_nulls,
    "fill_nulls": cleaning.fill_nulls,
    "validate_columns_exist": cleaning.validate_columns_exist,
    "drop_duplicates": cleaning.drop_duplicates,
    "drop_constant_columns": cleaning.drop_constant_columns,
    "clip_numeric": cleaning.clip_numeric,
    "strip_whitespace": cleaning.strip_whitespace,
    "hash_columns": cleaning.hash_columns,
    "parse_bool_strings": cleaning.parse_bool_strings,
    "normalize_case": cleaning.normalize_case,
    "normalize_unicode": cleaning.normalize_unicode,
    "rename_columns": cleaning.rename_columns,
    "cast_types": cleaning.cast_types,
    "round_numeric_columns": cleaning.round_numeric_columns,
    "combine_columns": cleaning.combine_columns,
    "collapse_rare_categories": cleaning.collapse_rare_categories,
    "slugify_column_names": cleaning.slugify_column_names,
    "trim_column_names": cleaning.trim_column_names,
    "clean_column_names": cleaning.clean_column_names,
    "parse_numeric_strings": cleaning.parse_numeric_strings,
}

_REGISTRY_LOCK = Lock()
_PYTHON_STEP_REGISTRY: dict[str, Callable] = {
    "standardize_missing_tokens": cleaning.standardize_missing_tokens
}


def register_step(name: str, fn: Callable, overwrite: bool = False):
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
    # 1. Validate the step name
    if not isinstance(name, str) or not name.strip():
        raise ValueError(
            f"Invalid pipeline step name: {name!r}. Expected a non-empty string."
        )

    # 2. Validate that the object is a callable (Fix for Issue #721)
    if not callable(fn):
        raise TypeError(
            f"Could not register custom step {name!r}: "
            f"expected a callable (function or class), but got {type(fn).__name__!r}."
        )

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

    track_lineage : bool, default False
        When True, inject a hidden sentinel column to track which original row
        indices are dropped by each step, then return ``(ArFrame, LineageReport)``
        instead of a bare ``ArFrame``.  The sentinel column is always stripped
        from the returned frame before it is handed back to the caller.

        When the same step name appears more than once in the pipeline, all
        drops from every invocation of that step are merged under the single
        key in ``LineageReport.dropped_by_step``, in sorted order.

        **Incompatible with** ``return_metadata=True``.  Combining both raises
        ``ValueError``.

        **Input column constraint**: the input frame must not already contain a
        column named ``__arnio_lineage_id__``.  If it does, ``pipeline`` raises
        ``ValueError`` before any steps are executed.

        **Custom step contract**: custom Python steps that are used with
        ``track_lineage=True`` must not drop or rename the sentinel column
        ``__arnio_lineage_id__``.  If a custom step removes the sentinel, a
        ``PipelineStepError`` is raised immediately after that step completes.

        Cannot be combined with ``return_metadata=True``.

    Returns
    -------
    ArFrame
        Data frame with all steps applied sequentially (default).
    tuple[ArFrame, LineageReport]
        Frame and lineage report when ``track_lineage=True``.
    tuple[ArFrame, dict]
        Frame and metadata dict when ``return_metadata=True``.

    Raises
    ------
    TypeError
        If any parameter has an unexpected type.
    ValueError
        If ``track_lineage=True`` and ``return_metadata=True`` are both set.
        If ``track_lineage=True`` and the input frame already contains a column
        named ``__arnio_lineage_id__``.
        If step format is invalid.
    UnknownStepError
        If step name is not registered.
    PipelineStepError
        If a custom step removes the internal lineage sentinel column while
        ``track_lineage=True`` is active.

    Examples
    --------
    >>> frame = ar.read_csv("data.csv")
    >>> cleaned = ar.pipeline(frame, [
    ...     ("drop_nulls", {"subset": ["age"]}),
    ...     ("strip_whitespace",),
    ...     ("drop_duplicates", {"keep": "first"}),
    ... ])

    Row lineage tracking:

    >>> result, lineage = ar.pipeline(frame, [
    ...     ("drop_nulls",),
    ...     ("drop_duplicates",),
    ... ], track_lineage=True)
    >>> lineage.dropped_by_step
    {"drop_nulls": [1, 4], "drop_duplicates": [7]}
    >>> lineage.total_dropped
    3
    """
    with _REGISTRY_LOCK:
        python_step_registry = dict(_PYTHON_STEP_REGISTRY)

    _validate_pipeline_step_container(steps)

    _validate_pipeline_steps(
        steps,
        python_step_registry,
    )

    result = frame

    # --- lineage tracking setup -------------------------------------------
    # Inject a hidden int64 sentinel column (values 0..n-1) so we can track
    # exactly which original row indices survive each row-dropping step.
    # The C++ engine treats it as an ordinary column and filters/deduplicates
    # it correctly alongside all other columns.
    #
    # Fix 3a: guard against sentinel column name collision in the input frame.
    # DataFrame.insert would raise a raw pandas ValueError; we replace that
    # with a clear Arnio-level error before any steps run.
    #
    # Fix 2: accumulate drops per step name using a dict[str, list[int]] where
    # repeated step names extend (not overwrite) the existing list.
    _lineage_dropped_by_step: dict[str, list[int]] = {}
    _lineage_current_ids: set[int] = set()
    if track_lineage:
        _input_df = to_pandas(frame)
        if _LINEAGE_SENTINEL_COL in _input_df.columns:
            raise ValueError(
                f"track_lineage=True requires that the input frame does not already "
                f"contain a column named {_LINEAGE_SENTINEL_COL!r}.  "
                f"Please rename or drop that column before calling pipeline()."
            )
        _sentinel_df = _input_df.copy()
        _sentinel_df.insert(0, _LINEAGE_SENTINEL_COL, range(len(_sentinel_df)))
        _sentinel_frame = from_pandas(_sentinel_df)
        result = _sentinel_frame
        working_frame = _sentinel_frame
        _lineage_current_ids = set(range(len(_sentinel_df)))
    # -----------------------------------------------------------------------

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
                step_timings.append(
                    {
                        "step": name,
                        "seconds": round(perf_counter() - started_at, 9),
                    }
                )
                _step_diagnostics.append(
                    {
                        "name": name,
                        "status": "success",
                        "runtime_ms": round(elapsed_ms, 3),
                        "rows_before": rows_before,
                        "rows_after": rows_before if dry_run else step_result.shape[0],
                        "rows_affected": (
                            0 if dry_run else rows_before - step_result.shape[0]
                        ),
                        "columns_before": columns_before,
                        "columns_after": columns_after,
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

            columns_before = working_frame.shape[1]
            try:
                returned = fn(df, **kwargs)
            except Exception as e:
                elapsed_sec = perf_counter() - started_at
                if return_metadata:
                    step_timings.append(
                        {
                            "step": name,
                            "seconds": round(elapsed_sec, 9),
                            "dry_run": dry_run,
                        }
                    )
                    row_counts.append(
                        {
                            "step": name,
                            "before": rows_before,
                            "after": rows_before,
                            "dry_run": dry_run,
                        }
                    )

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
            columns_after = step_result.shape[1]
            if not dry_run:
                result = step_result

            if return_metadata:
                step_timings.append(
                    {
                        "step": name,
                        "seconds": round(perf_counter() - started_at, 9),
                    }
                )
                _step_diagnostics.append(
                    {
                        "name": name,
                        "status": "success",
                        "runtime_ms": round(elapsed_ms, 3),
                        "rows_before": rows_before,
                        "rows_after": rows_before if dry_run else step_result.shape[0],
                        "rows_affected": (
                            0 if dry_run else rows_before - step_result.shape[0]
                        ),
                        "columns_before": columns_before,
                        "columns_after": columns_after,
                    }
                )
        else:
            available = list(_STEP_REGISTRY.keys()) + list(python_step_registry.keys())
            raise UnknownStepError(name, available)

        # --- per-step lineage diff ----------------------------------------
        # After each step (C++ or Python), check which sentinel IDs survived.
        # Non-dropping steps produce an empty diff naturally — no special-casing.
        #
        # Fix 3b: detect custom steps that removed the sentinel column and raise
        # a clear PipelineStepError rather than letting a raw KeyError surface.
        #
        # Fix 2: extend rather than overwrite when the same step name appears
        # more than once; keep the merged list in sorted order.
        if track_lineage:
            _after_pdf = to_pandas(working_frame)
            if _LINEAGE_SENTINEL_COL not in _after_pdf.columns:
                raise PipelineStepError(
                    name,
                    KeyError(
                        f"Custom pipeline step '{name}' removed the internal lineage "
                        f"sentinel column {_LINEAGE_SENTINEL_COL!r}.  Custom steps "
                        f"must not drop or rename this column when track_lineage=True."
                    ),
                )
            _surviving_ids: set[int] = set(_after_pdf[_LINEAGE_SENTINEL_COL].tolist())
            _newly_dropped = sorted(_lineage_current_ids - _surviving_ids)
            if name in _lineage_dropped_by_step:
                # Same step name used more than once: merge and re-sort so the
                # combined list remains ordered by original index.
                _lineage_dropped_by_step[name] = sorted(
                    _lineage_dropped_by_step[name] + _newly_dropped
                )
            else:
                _lineage_dropped_by_step[name] = _newly_dropped
            _lineage_current_ids = _surviving_ids
        # ------------------------------------------------------------------

    # --- lineage return path -----------------------------------------------
    # Strip the hidden sentinel column from the result before returning so
    # callers never see it, then build and return the LineageReport.
    if track_lineage:
        _result_pdf = to_pandas(result)
        result = from_pandas(_result_pdf.drop(columns=[_LINEAGE_SENTINEL_COL]))
        _lineage_report = LineageReport(
            dropped_by_step=_lineage_dropped_by_step,
            total_dropped=sum(
                len(indices) for indices in _lineage_dropped_by_step.values()
            ),
        )
        return result, _lineage_report
    # -----------------------------------------------------------------------

    if return_metadata:
        return result, {"step_timings": step_timings}
    return result


register_step("filter_rows", cleaning.filter_rows)
register_step("winsorize_outliers", cleaning.winsorize_outliers)

register_step("drop_columns_matching", cleaning.drop_columns_matching)
register_step("safe_divide_columns", cleaning.safe_divide_columns)
register_step("replace_values", cleaning.replace_values)
register_step("parse_numeric_strings", cleaning.parse_numeric_strings)
