"""
arnio.cleaning
Data cleaning functions.
"""

from __future__ import annotations

from collections.abc import Sequence
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


def validate_columns_exist(
    frame: ArFrame,
    columns: Sequence[str],
    *,
    operation: str | None = None,
) -> ArFrame:
    """Validate that all requested columns exist in a frame.

    Parameters
    ----------
    frame : ArFrame
        Input data frame.
    columns : sequence of str
        Column names that must exist.
    operation : str, optional
        Operation name to include in the error message.

    Returns
    -------
    ArFrame
        The original frame, unchanged. This makes the helper pipeline-friendly.

    Raises
    ------
    TypeError
        If columns is a string/bytes value or contains non-string items.
    KeyError
        If any requested column is missing.
    """
    requested_columns = _validate_column_sequence(columns, argument_name="columns")
    missing = [column for column in requested_columns if column not in frame.columns]
    if missing:
        available = ", ".join(frame.columns) or "<none>"
        context = f" for {operation}" if operation else ""
        raise KeyError(
            f"Missing columns{context}: {missing}. Available columns: {available}"
        )
    return frame


def _validate_column_sequence(
    columns: Sequence[str],
    *,
    argument_name: str,
) -> list[str]:
    if isinstance(columns, (str, bytes)):
        raise TypeError(
            f"{argument_name} must be a sequence of column names, not a string"
        )
    if not isinstance(columns, Sequence):
        raise TypeError(f"{argument_name} must be a sequence of column names")

    normalized = list(columns)
    invalid_columns = [column for column in normalized if not isinstance(column, str)]
    if invalid_columns:
        raise TypeError(f"{argument_name} must contain only string column names")

    return normalized


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
    if subset is not None:
        validate_columns_exist(
            frame,
            _validate_column_sequence(subset, argument_name="subset"),
            operation="drop_nulls",
        )
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
    if subset is not None:
        validate_columns_exist(
            frame,
            _validate_column_sequence(subset, argument_name="subset"),
            operation="fill_nulls",
        )
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
    if subset is not None:
        validate_columns_exist(
            frame,
            _validate_column_sequence(subset, argument_name="subset"),
            operation="drop_duplicates",
        )
    keep_arg = "none" if keep is False else keep
    result = _drop_duplicates(frame._frame, subset=subset, keep=keep_arg)
    return ArFrame(result)


def drop_constant_columns(frame: ArFrame) -> ArFrame:
    """Remove columns with exactly one unique value.

    Nulls are counted as values when determining whether a column is constant.
    This means columns like ``[None, None]`` are dropped, while columns like
    ``[1, 1, None]`` are kept. Empty columns in zero-row frames are also kept,
    since they have zero unique values rather than one.

    If every column is dropped, the zero-column pandas result is converted back
    to an ``ArFrame``. Arnio currently derives row count from stored columns, so
    that converted frame may report zero rows.

    Parameters
    ----------
    frame : ArFrame
        Input data frame.

    Returns
    -------
    ArFrame
        New frame without constant columns.

    Examples
    --------
    >>> frame = ar.read_csv("data.csv")
    >>> reduced = ar.drop_constant_columns(frame)
    """
    from .convert import from_pandas, to_pandas

    df = to_pandas(frame)
    if len(df.index) == 0:
        return frame

    constant_columns = [
        column for column in df.columns if df[column].nunique(dropna=False) == 1
    ]
    return from_pandas(df.drop(columns=constant_columns))


def clip_numeric(
    frame: ArFrame,
    *,
    lower: int | float | None = None,
    upper: int | float | None = None,
    subset: list[str] | None = None,
) -> ArFrame:
    """Clip numeric columns to lower and/or upper bounds.

    Parameters
    ----------
    frame : ArFrame
        Input data frame.
    lower : int or float, optional
        Lower bound. Values below this are raised to the bound.
    upper : int or float, optional
        Upper bound. Values above this are lowered to the bound.
    subset : list[str], optional
        Numeric columns to clip. If None, applies to all numeric columns except bools.

    Returns
    -------
    ArFrame
        New frame with clipped numeric values.

    Raises
    ------
    ValueError
        If no bounds are provided, bounds are inverted, subset contains unknown
        columns, or subset contains non-numeric columns.

    Examples
    --------
    >>> frame = ar.read_csv("data.csv")
    >>> clipped = ar.clip_numeric(frame, lower=0, upper=100)
    """
    from pandas.api.types import is_bool_dtype, is_numeric_dtype

    from .convert import from_pandas, to_pandas

    if lower is None and upper is None:
        raise ValueError("At least one of 'lower' or 'upper' must be provided")
    if lower is not None and upper is not None and lower > upper:
        raise ValueError("lower cannot be greater than upper")

    df = to_pandas(frame)

    def _is_supported_numeric(column_name: str) -> bool:
        series = df[column_name]
        return is_numeric_dtype(series) and not is_bool_dtype(series)

    if subset is None:
        target_columns = [
            column for column in df.columns if _is_supported_numeric(column)
        ]
    else:
        unknown_columns = [column for column in subset if column not in df.columns]
        if unknown_columns:
            raise ValueError(f"Unknown columns in subset: {unknown_columns}")

        non_numeric_columns = [
            column for column in subset if not _is_supported_numeric(column)
        ]
        if non_numeric_columns:
            raise ValueError(
                "clip_numeric only supports numeric columns: " f"{non_numeric_columns}"
            )
        target_columns = subset

    if not target_columns:
        return frame

    clipped = df.copy()
    clipped[target_columns] = clipped[target_columns].clip(lower=lower, upper=upper)
    return from_pandas(clipped)


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
    if subset is not None:
        validate_columns_exist(
            frame,
            _validate_column_sequence(subset, argument_name="subset"),
            operation="strip_whitespace",
        )
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
    if subset is not None:
        validate_columns_exist(
            frame,
            _validate_column_sequence(subset, argument_name="subset"),
            operation="normalize_case",
        )
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
    validate_columns_exist(
        frame,
        _validate_column_sequence(list(mapping), argument_name="mapping keys"),
        operation="rename_columns",
    )
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
    validate_columns_exist(
        frame,
        _validate_column_sequence(list(mapping), argument_name="mapping keys"),
        operation="cast_types",
    )
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


def round_numeric_columns(
    frame,
    *,
    subset: list[str] | None = None,
    decimals: int = 0,
):
    """Round numeric columns to specified decimal places.

    Non-numeric columns included in subset are ignored safely.

    Parameters
    ----------
    frame : ArFrame or pd.DataFrame
        Input data frame.
    subset : list[str], optional
        Column names to round. If None, applies to all numeric columns.
    decimals : int, default 0
        Number of decimal places to round to.

    Returns
    -------
    ArFrame or pd.DataFrame
        New frame with numeric columns rounded.

    Examples
    --------
    >>> frame = ar.read_csv("data.csv")
    >>> rounded = ar.round_numeric_columns(frame, decimals=2)
    """
    import pandas as pd

    from .convert import from_pandas, to_pandas

    if subset is not None and not isinstance(subset, list):
        raise TypeError("subset must be a list of column names")
    if isinstance(decimals, bool) or not isinstance(decimals, int):
        raise TypeError("decimals must be an integer")

    is_arframe = not isinstance(frame, pd.DataFrame)
    df = to_pandas(frame) if is_arframe else frame.copy()

    if subset is not None:
        missing = [col for col in subset if col not in df.columns]
        if missing:
            raise IndexError(f"Column not found: {missing[0]}")
        cols_to_round = subset
    else:
        cols_to_round = df.select_dtypes(include=["number"]).columns

    for col in cols_to_round:
        if pd.api.types.is_numeric_dtype(df[col]):
            df[col] = df[col].round(decimals)

    return from_pandas(df) if is_arframe else df


def safe_divide_columns(
    frame, numerator: str, denominator: str, output_column: str, fill_value: float = 0.0
):
    """Divide one column by another, handling division by zero and nulls explicitly.

    When the denominator is zero or null, the result is replaced with
    fill_value instead of raising an error or producing NaN/Inf.

    Parameters
    ----------
    frame : ArFrame
        Input data frame.
    numerator : str
        Column name to use as the numerator.
    denominator : str
        Column name to use as the denominator.
    output_column : str
        Name of the new column to store the division result. Must be a
        non-empty string. If the column already exists, it will be
        overwritten and a ``UserWarning`` is raised.
    fill_value : float, optional
        Value to use when denominator is zero or null. Defaults to 0.0.

    Returns
    -------
    ArFrame

    Examples
    --------
    >>> frame = ar.read_csv("data.csv")
    >>> result = ar.safe_divide_columns(frame, numerator="revenue", denominator="cost", output_column="ratio")
    """
    import pandas as pd

    from .convert import from_pandas, to_pandas

    is_arframe = not isinstance(frame, pd.DataFrame)
    df = to_pandas(frame) if is_arframe else frame

    if numerator not in df.columns:
        raise ValueError(f"Numerator column '{numerator}' not found in frame.")
    if denominator not in df.columns:
        raise ValueError(f"Denominator column '{denominator}' not found in frame.")
    if not isinstance(output_column, str) or not output_column.strip():
        raise ValueError("output_column must be a non-empty string.")
    if output_column in df.columns:
        import warnings

        warnings.warn(
            f"Output column '{output_column}' already exists and will be overwritten.",
            UserWarning,
            stacklevel=2,
        )

    safe_denom = df[denominator].replace(0, float("nan"))
    result = df[numerator] / safe_denom
    df = df.copy()
    df[output_column] = result.fillna(fill_value)

    return from_pandas(df) if is_arframe else df


def slugify_column_names(
    frame: ArFrame,
    *,
    duplicates: str = "raise",
) -> ArFrame:
    """Normalize column names to predictable snake_case.

    Transforms every column name so that downstream Python workflows get
    consistent, attribute-safe identifiers:

    * Leading/trailing whitespace is stripped.
    * Any run of whitespace or hyphens is collapsed to a single underscore.
    * Special characters (anything not alphanumeric or underscore) are removed.
    * Multiple consecutive underscores are collapsed to one.
    * Leading/trailing underscores are stripped.
    * The result is lowercased.

    Already-clean names (e.g. ``revenue``, ``user_id``) pass through unchanged,
    so this step is safe to include in every pipeline.

    Parameters
    ----------
    frame : ArFrame
        Input data frame.
    duplicates : {"raise", "ignore"}, default "raise"
        What to do when two or more columns map to the same slug.

        * ``"raise"``  — raise ``ValueError`` listing the collision.
        * ``"ignore"`` — keep the first occurrence of each slug and drop the
          later columns that collide.

    Returns
    -------
    ArFrame
        New frame with slugified column names and identical column order.

    Raises
    ------
    ValueError
        If *duplicates* is ``"raise"`` and a slug collision is detected, or if
        an unrecognised *duplicates* value is passed.

    Examples
    --------
    >>> frame = ar.read_csv("messy.csv")   # columns: ["First Name", "Revenue ($)", "ID"]
    >>> clean = ar.slugify_column_names(frame)
    >>> clean.columns
    ['first_name', 'revenue', 'id']

    Inside a pipeline:

    >>> clean = ar.pipeline(frame, [
    ...     ("slugify_column_names",),
    ...     ("strip_whitespace",),
    ... ])
    """
    import re

    from .convert import from_pandas, to_pandas

    if duplicates not in ("raise", "ignore"):
        raise ValueError(
            f"duplicates must be 'raise' or 'ignore', got {duplicates!r}"
        )
    def _slugify(name: str) -> str:
        name = name.strip()
        # Replace whitespace and hyphens with underscores
        name = re.sub(r"[\s\-]+", "_", name)
        # Remove anything that is not alphanumeric or underscore
        name = re.sub(r"[^\w]", "", name)
        # Collapse multiple underscores
        name = re.sub(r"_+", "_", name)
        # Strip leading/trailing underscores
        name = name.strip("_")
        return name.lower()

    df = to_pandas(frame)
    original_columns = list(df.columns)
    slugs = [_slugify(col) for col in original_columns]

    # Detect collisions
    seen: dict[str, str] = {}       # slug -> first original name
    collisions: list[str] = []
    drop_indices: list[int] = []

    for idx, (original, slug) in enumerate(zip(original_columns, slugs)):
        if slug in seen:
            if duplicates == "raise":
                collisions.append(
                    f"  {original!r} and {seen[slug]!r} both map to {slug!r}"
                )
            else:  # "ignore" — drop the later duplicate
                drop_indices.append(idx)
        else:
            seen[slug] = original

    if collisions:
        raise ValueError(
            "slugify_column_names produced duplicate column names:\n"
            + "\n".join(collisions)
        )

    # Build the rename mapping (only columns that survive)
    surviving = [
        (orig, slug)
        for idx, (orig, slug) in enumerate(zip(original_columns, slugs))
        if idx not in drop_indices
    ]

    result_df = df.drop(
        columns=[original_columns[i] for i in drop_indices]
    ).rename(columns=dict(surviving))

    # Preserve original column order (minus any dropped duplicates)
    result_df = result_df[[slug for _, slug in surviving]]

    return from_pandas(result_df)