"""
arnio.pipeline
Chained cleaning pipeline.
"""

from __future__ import annotations

import copy as copylib
import inspect
import logging
import warnings
from dataclasses import dataclass
from threading import Lock
from time import perf_counter
from typing import Any, Callable

import pandas as pd

from . import cleaning
from .convert import from_pandas, to_pandas
from .exceptions import PipelineStepError, UnknownStepError
from .frame import ArFrame

logger = logging.getLogger("arnio")
_BUILTIN_STEP_NAMESPACE = "builtin"
_STEP_NAMESPACE_SEPARATOR = ":"

# Map step names to cleaning functions
_STEP_REGISTRY: dict[str, Callable] = {
    "drop_nulls": cleaning.drop_nulls,
    "drop_columns": cleaning.drop_columns,
    "select_columns": cleaning.select_columns,
    "keep_rows_with_nulls": cleaning.keep_rows_with_nulls,
    "fill_nulls": cleaning.fill_nulls,
    "validate_columns_exist": cleaning.validate_columns_exist,
    "drop_duplicates": cleaning.drop_duplicates,
    "drop_constant_columns": cleaning.drop_constant_columns,
    "drop_empty_columns": cleaning.drop_empty_columns,
    "clip_numeric": cleaning.clip_numeric,
    "winsorize_outliers": cleaning.winsorize_outliers,
    "strip_whitespace": cleaning.strip_whitespace,
    "parse_bool_strings": cleaning.parse_bool_strings,
    "normalize_case": cleaning.normalize_case,
    "normalize_unicode": cleaning.normalize_unicode,
    "rename_columns": cleaning.rename_columns,
    "cast_types": cleaning.cast_types,
    "round_numeric_columns": cleaning.round_numeric_columns,
    "combine_columns": cleaning.combine_columns,
    "slugify_column_names": cleaning.slugify_column_names,
    "trim_column_names": cleaning.trim_column_names,
    "clean_column_names": cleaning.clean_column_names,
}

_REGISTRY_LOCK = Lock()
_DEPRECATED_STEP_ALIASES: dict[str, str] = {}
_PYTHON_STEP_REGISTRY: dict[str, Callable] = {
    "standardize_missing_tokens": cleaning.standardize_missing_tokens,
    "coalesce_columns": cleaning.coalesce_columns,
    "normalize_whitespace": cleaning.normalize_whitespace,
}
_BUILTIN_PYTHON_STEP_REGISTRY: dict[str, Callable] = {}


_LINEAGE_SENTINEL_COL = "__arnio_lineage_id__"


@dataclass(frozen=True)
class PipelineContext:
    """Execution context passed to opt-in Python pipeline steps."""

    step_name: str
    step_index: int
    total_steps: int
    dry_run: bool


@dataclass(frozen=True)
class LineageReport:
    """Maps dropped rows back to their original indices and the step that dropped them.

    Returned by :func:`pipeline` when ``track_lineage=True``.

    Attributes
    ----------
    dropped_by_step : dict[str, list[int]]
        Mapping from step name to a sorted list of original row indices that
        were dropped by that step.  Steps that dropped no rows have an empty
        list.

        When the same step name appears more than once in the pipeline, all
        drops from every invocation of that step are merged under the single
        key in sorted order.  Use ``track_lineage=True`` together with
        per-step timing from ``return_metadata=True`` if you need to
        distinguish individual invocations.
    total_dropped : int
        Total number of rows dropped across all steps.

    Examples
    --------
    >>> result, lineage = ar.pipeline(frame, steps, track_lineage=True)
    >>> lineage.dropped_by_step
    {"drop_nulls": [1, 2], "drop_duplicates": [4]}
    >>> lineage.total_dropped
    3
    >>> lineage.to_pandas()
       original_index          step
    0               1    drop_nulls
    1               2    drop_nulls
    2               4  drop_duplicates
    """

    dropped_by_step: dict[str, list[int]]
    total_dropped: int

    def to_pandas(self) -> pd.DataFrame:
        """Return a flat DataFrame with columns ``original_index`` and ``step``."""
        rows = [
            {"original_index": idx, "step": step_name}
            for step_name, indices in self.dropped_by_step.items()
            for idx in indices
        ]
        return pd.DataFrame(rows, columns=["original_index", "step"])


class _WritablePipelineSeries(pd.Series):
    @property
    def _constructor(self):
        return _WritablePipelineSeries

    @property
    def _constructor_expanddim(self):
        return _WritablePipelineDataFrame

    def to_numpy(self, *args, **kwargs):
        values = super().to_numpy(*args, **kwargs)
        try:
            values.setflags(write=True)
        except ValueError:
            pass
        return values


class _WritablePipelineDataFrame(pd.DataFrame):
    @property
    def _constructor(self):
        return _WritablePipelineDataFrame

    @property
    def _constructor_sliced(self):
        return _WritablePipelineSeries


def _to_writable_pipeline_dataframe(frame: ArFrame) -> pd.DataFrame:
    base = to_pandas(frame, copy=True)
    writable = _WritablePipelineDataFrame(base, copy=False)
    writable.attrs = copylib.deepcopy(base.attrs)
    return writable


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
    with _REGISTRY_LOCK:
        if not isinstance(name, str) or not name or not name.strip():
            raise ValueError("parameter 'name' must be a non-empty string")
        if not callable(fn):
            raise TypeError("parameter 'fn' must be a callable object")
        if not isinstance(overwrite, bool):
            raise TypeError(
                f"parameter 'overwrite' must be a bool, not {type(overwrite).__name__}"
            )

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
        if name in _BUILTIN_PYTHON_STEP_REGISTRY:
            raise ValueError(
                f"Cannot register '{name}': conflicts with built-in Python step. "
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


def unregister_step(name: str) -> None:
    """Unregister a custom Python pipeline step."""
    with _REGISTRY_LOCK:
        if not isinstance(name, str):
            raise TypeError(
                f"parameter 'name' must be a string, not {type(name).__name__}"
            )
        if not name:
            raise ValueError("parameter 'name' must be a non-empty string")

        if name not in _PYTHON_STEP_REGISTRY:
            available_steps = sorted(set(_STEP_REGISTRY) | set(_PYTHON_STEP_REGISTRY))
            raise UnknownStepError(name, available_steps)

        # Protect only names that were registered as built-ins at module load
        # time (i.e. present in _BUILTIN_PYTHON_STEP_REGISTRY).  Do NOT use
        # _is_builtin_python_step here: that helper checks the function's
        # __module__, which would wrongly block user-defined aliases whose
        # underlying callable happens to live in arnio.cleaning.
        if name in _BUILTIN_PYTHON_STEP_REGISTRY:
            available_steps = sorted(set(_STEP_REGISTRY) | set(_PYTHON_STEP_REGISTRY))
            raise ValueError(
                f"Cannot unregister built-in step '{name}'. Only custom user-registered steps can be unregistered."
            )
        del _PYTHON_STEP_REGISTRY[name]


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


def _validate_pipeline_step_container(steps: Any) -> None:
    if steps is None:
        raise TypeError("steps must be a list of step tuples, got None")

    if isinstance(steps, (str, bytes)):
        raise TypeError(
            f"steps must be a list of step tuples, got {type(steps).__name__}. "
            "Each step must be (name,) or (name, kwargs), for example "
            '[("drop_nulls",)].'
        )
    if isinstance(steps, tuple):
        raise TypeError(
            f"steps must be a list of step tuples, got bare step tuple {steps!r}. "
            f"Use [{steps!r}] instead."
        )
    if not isinstance(steps, list):
        raise TypeError(
            f"steps must be a list of step tuples, got {type(steps).__name__}. "
        )


def _validate_pipeline_steps(
    steps: list[tuple],
    python_step_registry: dict[str, Callable],
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
    verbose: bool = False,
    track_lineage: bool = False,
) -> ArFrame | tuple[ArFrame, dict[str, Any]] | tuple[ArFrame, LineageReport]:
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

        Cannot be combined with ``track_lineage=True``.  If you need both
        row-level lineage and per-step timings, run the pipeline twice: once
        with ``track_lineage=True`` and once with ``return_metadata=True``.

    verbose : bool, default False
        Enable lightweight diagnostic logging through the ``arnio`` logger.
        Logs step index, step name, execution path, elapsed execution
        time, and row-count changes for each pipeline step.

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
    if not isinstance(frame, ArFrame):
        raise TypeError("frame must be an ArFrame")
    if not isinstance(return_metadata, bool):
        raise TypeError(
            f"return_metadata must be a bool, got {type(return_metadata).__name__!r}"
        )
    if not isinstance(dry_run, bool):
        raise TypeError(f"dry_run must be a bool, got {type(dry_run).__name__!r}")
    if not isinstance(verbose, bool):
        raise TypeError(f"verbose must be a bool, got {type(verbose).__name__!r}")
    if not isinstance(track_lineage, bool):
        raise TypeError(
            f"track_lineage must be a bool, got {type(track_lineage).__name__!r}"
        )

    # Fix 1: reject the track_lineage + return_metadata combination upfront
    # rather than silently ignoring return_metadata.
    if track_lineage and return_metadata:
        raise ValueError(
            "track_lineage=True and return_metadata=True cannot be used together. "
            "Run the pipeline twice if you need both row-level lineage and "
            "per-step timings: once with track_lineage=True and once with "
            "return_metadata=True."
        )

    with _REGISTRY_LOCK:
        python_step_registry = dict(_PYTHON_STEP_REGISTRY)
        namespaced_builtin_steps = _get_namespaced_builtin_steps(python_step_registry)
        deprecated_step_aliases = dict(_DEPRECATED_STEP_ALIASES)

    _validate_pipeline_step_container(steps)

    _validate_pipeline_steps(
        steps,
        python_step_registry,
        deprecated_step_aliases,
    )

    result = frame
    working_frame = frame

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
    applied_steps: list[str] = []
    row_counts: list[dict[str, int | str]] = []
    total_steps = len(steps)
    for step_index, step in enumerate(steps):
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

        # --- lineage: sentinel compatibility for drop_duplicates -----------
        # The sentinel column has a unique value per row.  Without this fix,
        # drop_duplicates would see every row as distinct and drop nothing.
        # We auto-restrict its subset to user-visible columns only.
        if track_lineage and name == "drop_duplicates":
            _user_cols = [
                c
                for c in to_pandas(working_frame).columns
                if c != _LINEAGE_SENTINEL_COL
            ]
            kwargs = {
                **kwargs,
                "subset": [
                    c
                    for c in kwargs.get("subset", _user_cols)
                    if c != _LINEAGE_SENTINEL_COL
                ],
            }
        # ------------------------------------------------------------------

        if name in _STEP_REGISTRY:
            # C++ backed step - fast path
            fn = _STEP_REGISTRY[name]
            rows_before = result.shape[0]

            started_at = perf_counter()
            if name == "rename_columns" and (
                "mapping" not in kwargs or not isinstance(kwargs["mapping"], dict)
            ):
                step_result = fn(working_frame, mapping=kwargs)

                if not dry_run:
                    result = step_result
                working_frame = step_result

            elif name == "cast_types":
                reserved_kwargs = {"mapping", "errors"}

                has_reserved_kwargs = any(
                    key in kwargs for key in reserved_kwargs - {"mapping"}
                )

                if (
                    "mapping" in kwargs
                    and isinstance(kwargs["mapping"], dict)
                ):
                    step_result = fn(working_frame, **kwargs)

                elif has_reserved_kwargs:
                    raise ValueError(
                        "cast_types shorthand mapping cannot be mixed with "
                        "reserved keyword arguments. Use "
                        "{'mapping': {...}, ...} form instead."
                    )

                else:
                    step_result = fn(working_frame, kwargs)

                if not dry_run:
                    result = step_result

                working_frame = step_result

            else:
                target_frame = working_frame

                step_result = fn(target_frame, **kwargs)

                if not dry_run:
                    result = step_result
                working_frame = step_result

            elapsed_sec = perf_counter() - started_at
            elapsed_ms = elapsed_sec * 1000

            if verbose:
                execution_path = f"{fn.__module__}.{fn.__name__}"

                logger.info(
                    "[%s/%s] %s | path=%s | rows: %s -> %s | %.2fms",
                    step_index + 1,
                    total_steps,
                    name,
                    execution_path,
                    rows_before,
                    step_result.shape[0],
                    elapsed_ms,
                )

            if return_metadata:
                applied_steps.append(name)
                row_counts.append(
                    {
                        "step": name,
                        "before": rows_before,
                        "after": rows_before if dry_run else step_result.shape[0],
                        "dry_run": dry_run,
                    }
                )
                step_timings.append(
                    {
                        "step": name,
                        "seconds": round(elapsed_sec, 9),
                        "dry_run": dry_run,
                    }
                )
        elif name in python_step_registry:
            # Pure Python step - slower but contributor-friendly
            started_at = perf_counter()
            rows_before = result.shape[0]

            fn = python_step_registry[name]

            # Isolate genuine custom steps from internal core library functions
            is_builtin = _is_builtin_python_step(name, fn)
            if is_builtin:
                df = to_pandas(working_frame)
            else:
                df = _to_writable_pipeline_dataframe(working_frame)
            signature = inspect.signature(fn)
            call_kwargs = dict(kwargs)
            if "context" in signature.parameters and "context" not in call_kwargs:
                call_kwargs["context"] = PipelineContext(
                    step_name=name,
                    step_index=step_index,
                    total_steps=total_steps,
                    dry_run=dry_run,
                )

            try:
                returned = fn(df, **call_kwargs)
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
            working_frame = step_result

            elapsed_sec = perf_counter() - started_at
            elapsed_ms = elapsed_sec * 1000

            if verbose:
                step_name = getattr(fn, "__name__", name)
                execution_path = f"{fn.__module__}.{step_name}"

                logger.info(
                    "[%s/%s] %s | path=%s | rows: %s -> %s | %.2fms",
                    step_index + 1,
                    total_steps,
                    name,
                    execution_path,
                    rows_before,
                    step_result.shape[0],
                    elapsed_ms,
                )

            if return_metadata:
                applied_steps.append(name)
                row_counts.append(
                    {
                        "step": name,
                        "before": rows_before,
                        "after": rows_before if dry_run else step_result.shape[0],
                        "dry_run": dry_run,
                    }
                )
                step_timings.append(
                    {
                        "step": name,
                        "seconds": round(elapsed_sec, 9),
                        "dry_run": dry_run,
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
        return result, {
            "applied_steps": applied_steps,
            "row_counts": row_counts,
            "step_timings": step_timings,
        }
    return result


register_step("filter_rows", cleaning.filter_rows)
register_step("drop_columns_matching", cleaning.drop_columns_matching)
register_step("rename_columns_matching", cleaning.rename_columns_matching)
register_step("safe_divide_columns", cleaning.safe_divide_columns)
register_step("replace_values", cleaning.replace_values)
_BUILTIN_PYTHON_STEP_REGISTRY.update(_PYTHON_STEP_REGISTRY)


def reset_steps() -> None:
    """Restore the Python pipeline registry to built-in steps only."""
    with _REGISTRY_LOCK:
        _PYTHON_STEP_REGISTRY.clear()
        _PYTHON_STEP_REGISTRY.update(_BUILTIN_PYTHON_STEP_REGISTRY)
