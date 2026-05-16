"""
arnio.cleaning
Data cleaning functions.
"""

from __future__ import annotations

from typing import Any

from ._core import (
    _cast_types,
    _drop_duplicates,
    _drop_nulls,
    _fill_nulls,
    _normalize_case,
    _rename_columns,
    _strip_whitespace,
)
from .exceptions import TypeCastError
from .frame import ArFrame


def drop_nulls(
    frame: ArFrame,
    *,
    subset: list[str] | None = None,
) -> ArFrame:
    """Remove rows containing null/empty values.

    Parameters
    ----------
    frame : ArFrame
        Input data frame.
    subset : list[str], optional
        Column names to check for nulls. If None, checks all columns.
        A row is dropped if ANY column in the subset contains a null.

    Returns
    -------
    ArFrame
        New frame with null-containing rows removed.

    Examples
    --------
    >>> frame = ar.read_csv("data.csv")
    >>> clean = ar.drop_nulls(frame, subset=["age", "name"])
    """
    result = _drop_nulls(frame._frame, subset=subset)
    return ArFrame(result)


def fill_nulls(
    frame: ArFrame,
    value: Any,
    *,
    subset: list[str] | None = None,
) -> ArFrame:
    """Replace null/empty values with a given fill value.

    Parameters
    ----------
    frame : ArFrame
        Input data frame.
    value : Any
        Value to replace nulls with. Can be a scalar or compatible type.
    subset : list[str], optional
        Column names to fill nulls in. If None, fills all columns.

    Returns
    -------
    ArFrame
        New frame with null values replaced.

    Examples
    --------
    >>> frame = ar.read_csv("data.csv")
    >>> filled = ar.fill_nulls(frame, 0, subset=["age"])
    """
    result = _fill_nulls(frame._frame, value, subset=subset)
    return ArFrame(result)


def drop_duplicates(
    frame: ArFrame,
    *,
    subset: list[str] | None = None,
    keep: str | bool = "first",
) -> ArFrame:
    """Remove duplicate rows.

    Parameters
    ----------
    frame : ArFrame
        Input data frame.
    subset : list[str], optional
        Column names to consider for duplicates. If None, uses all columns.
    keep : str or bool, default "first"
        Which duplicate to keep. Options: "first", "last", "none", or False
        (drop all duplicates).

    Returns
    -------
    ArFrame
        New frame with duplicate rows removed.

    Examples
    --------
    >>> frame = ar.read_csv("data.csv")
    >>> unique = ar.drop_duplicates(frame, subset=["name"], keep="first")
    """
    keep_arg = "none" if keep is False else keep
    result = _drop_duplicates(frame._frame, subset=subset, keep=keep_arg)
    return ArFrame(result)


def strip_whitespace(
    frame: ArFrame,
    *,
    subset: list[str] | None = None,
) -> ArFrame:
    """Trim leading/trailing whitespace from string columns.

    Parameters
    ----------
    frame : ArFrame
        Input data frame.
    subset : list[str], optional
        Column names to strip whitespace from. If None, applies to all string columns.

    Returns
    -------
    ArFrame
        New frame with whitespace trimmed from string columns.

    Examples
    --------
    >>> frame = ar.read_csv("data.csv")
    >>> clean = ar.strip_whitespace(frame, subset=["name"])
    """
    result = _strip_whitespace(frame._frame, subset=subset)
    return ArFrame(result)


def normalize_case(
    frame: ArFrame,
    *,
    subset: list[str] | None = None,
    case_type: str = "lower",
) -> ArFrame:
    """Normalize string columns to lower/upper/title case.

    Parameters
    ----------
    frame : ArFrame
        Input data frame.
    subset : list[str], optional
        Column names to normalize. If None, applies to all string columns.
    case_type : str, default "lower"
        Case to normalize to. Options: "lower", "upper", "title".

    Returns
    -------
    ArFrame
        New frame with string columns normalized to specified case.

    Examples
    --------
    >>> frame = ar.read_csv("data.csv")
    >>> lower = ar.normalize_case(frame, case_type="lower")
    """
    result = _normalize_case(frame._frame, subset=subset, case_type=case_type)
    return ArFrame(result)


def rename_columns(
    frame: ArFrame,
    mapping: dict[str, str],
) -> ArFrame:
    """Rename columns via a {old: new} dict.

    Parameters
    ----------
    frame : ArFrame
        Input data frame.
    mapping : dict[str, str]
        Dictionary mapping old column names to new names.

    Returns
    -------
    ArFrame
        New frame with columns renamed.

    Examples
    --------
    >>> frame = ar.read_csv("data.csv")
    >>> renamed = ar.rename_columns(frame, {"old_name": "new_name"})
    """
    result = _rename_columns(frame._frame, mapping)
    return ArFrame(result)


def cast_types(
    frame: ArFrame,
    mapping: dict[str, str],
) -> ArFrame:
    """Cast columns to specified types via {col: type_str} dict.

    Parameters
    ----------
    frame : ArFrame
        Input data frame.
    mapping : dict[str, str]
        Dictionary mapping column names to target type strings (e.g., "int64", "float64", "bool", "string").

    Returns
    -------
    ArFrame
        New frame with columns cast to specified types.

    Examples
    --------
    >>> frame = ar.read_csv("data.csv")
    >>> casted = ar.cast_types(frame, {"age": "int64", "score": "float64"})
    """
    try:
        result = _cast_types(frame._frame, mapping)
    except ValueError as e:
        raise TypeCastError(str(e)) from e
    return ArFrame(result)


def clean(
    frame: ArFrame,
    *,
    strip_whitespace: bool = True,
    drop_nulls: bool = False,
    drop_duplicates: bool = False,
) -> ArFrame:
    """Convenience function to apply common cleaning operations.

    Operations are applied in this order (if enabled):
    1. strip_whitespace
    2. drop_nulls
    3. drop_duplicates

    Parameters
    ----------
    frame : ArFrame
        Input data frame.
    strip_whitespace : bool, default True
        Whether to trim leading/trailing whitespace from string columns.
    drop_nulls : bool, default False
        Whether to remove rows containing null/empty values.
    drop_duplicates : bool, default False
        Whether to remove duplicate rows.

    Returns
    -------
    ArFrame
        New frame with specified cleaning operations applied.

    Examples
    --------
    >>> frame = ar.read_csv("data.csv")
    >>> cleaned = ar.clean(frame, strip_whitespace=True, drop_nulls=True)
    """
    from .pipeline import pipeline

    steps = []
    if strip_whitespace:
        steps.append(("strip_whitespace",))
    if drop_nulls:
        steps.append(("drop_nulls",))
    if drop_duplicates:
        steps.append(("drop_duplicates",))

    if not steps:
        return frame

    return pipeline(frame, steps)


def filter_rows(frame, column, op, value):
    """Filter rows based on a column condition."""

    import pandas as pd

    from .convert import from_pandas, to_pandas

    is_arframe = not isinstance(frame, pd.DataFrame)

    df = to_pandas(frame) if is_arframe else frame

    ops = {
        ">": "gt",
        "<": "lt",
        ">=": "ge",
        "<=": "le",
        "==": "eq",
        "!=": "ne",
    }

    if op not in ops:
        raise ValueError(f"Unsupported operator: {op}")

    filtered = df[getattr(df[column], ops[op])(value)]

    return from_pandas(filtered) if is_arframe else filtered


def winsorize_outliers(
    frame: ArFrame,
    *,
    lower: float = 0.05,
    upper: float = 0.95,
    subset: list[str] | None = None,
) -> ArFrame:
    """Cap extreme outlier values at the given percentile boundaries.

    Values below the ``lower`` percentile are raised to that percentile value.
    Values above the ``upper`` percentile are lowered to that percentile value.
    Only numeric columns are affected; string columns are left unchanged.

    Parameters
    ----------
    frame : ArFrame
        Input data frame.
    lower : float, default 0.05
        Lower percentile boundary (between 0 and 1). Values below this
        percentile are capped up to this boundary.
    upper : float, default 0.95
        Upper percentile boundary (between 0 and 1). Values above this
        percentile are capped down to this boundary.
    subset : list[str], optional
        Column names to apply winsorizing to. If None, applies to all
        numeric columns. Non-numeric columns in subset are silently skipped.

    Returns
    -------
    ArFrame
        New frame with outlier values capped at the given percentile bounds.

    Raises
    ------
    ValueError
        If ``lower`` or ``upper`` are not between 0 and 1, or if
        ``lower`` is greater than or equal to ``upper``.

    Notes
    -----
    Winsorizing works best on large datasets. On small datasets the
    percentile boundaries may still appear extreme because they are
    computed from the data itself. For example, with only 5 rows,
    the 95th percentile may still be close to the outlier value.

    Examples
    --------
    >>> frame = ar.read_csv("data.csv")
    >>> clean = ar.winsorize_outliers(frame, lower=0.05, upper=0.95)
    >>> clean = ar.winsorize_outliers(frame, lower=0.1, upper=0.9, subset=["price"])
    """
    if not (0 <= lower < upper <= 1):
        raise ValueError(
            f"`lower` must be less than `upper` and both must be between 0 and 1, "
            f"got lower={lower!r}, upper={upper!r}"
        )

    import pandas as pd

    from .convert import from_pandas, to_pandas

    # Handle both ArFrame and DataFrame (when called from pipeline)
    is_arframe = isinstance(frame, ArFrame)
    df = to_pandas(frame) if is_arframe else frame

    cols_to_process = subset if subset is not None else df.columns.tolist()

    for col in cols_to_process:
        if col not in df.columns:
            continue
        if not pd.api.types.is_numeric_dtype(df[col]):
            continue

        # Cast to float64 before clipping so percentile
        # values (which are floats) can be assigned back without TypeError
        df[col] = df[col].astype("float64")

        lower_bound = df[col].quantile(lower)
        upper_bound = df[col].quantile(upper)
        df[col] = df[col].clip(lower=lower_bound, upper=upper_bound)

    return from_pandas(df) if is_arframe else df
