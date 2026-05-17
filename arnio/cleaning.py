"""
arnio.cleaning
Data cleaning functions.
"""

from __future__ import annotations

import unicodedata
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


def keep_rows_with_nulls(
    frame: ArFrame,
    *,
    subset: list[str] | None = None,
) -> ArFrame:
    """Keep only rows that contain at least one null/empty value.

    Parameters
    ----------
    frame : ArFrame
        Input data frame.
    subset : list[str], optional
        Column names to check for nulls. If None, checks all columns.
        A row is kept if ANY column in the subset contains a null.

    Returns
    -------
    ArFrame
        New frame containing only rows with at least one null value.

    Raises
    ------
    TypeError
        If subset is passed as a string instead of a list.
    ValueError
        If any column in subset does not exist in the frame.

    Examples
    --------
    >>> frame = ar.read_csv("data.csv")
    >>> nulls = ar.keep_rows_with_nulls(frame)
    >>> nulls_age = ar.keep_rows_with_nulls(frame, subset=["age"])
    """

    if isinstance(subset, str):
        raise TypeError(
            f"keep_rows_with_nulls: 'subset' must be a list of column names, "
            f"not a string. Did you mean subset=['{subset}']?"
        )

    import pandas as pd

    from .convert import from_pandas, to_pandas

    is_arframe = not isinstance(frame, pd.DataFrame)
    df = to_pandas(frame) if is_arframe else frame

    cols = subset if subset is not None else df.columns.tolist()

    # validate that all subset columns actually exist
    unknown = [c for c in cols if c not in df.columns]
    if unknown:
        raise ValueError(
            f"keep_rows_with_nulls: unknown column(s) in subset: {unknown}. "
            f"Available columns: {df.columns.tolist()}"
        )

    mask = df[cols].isnull().any(axis=1)
    result = df[mask].reset_index(drop=True)

    return from_pandas(result) if is_arframe else result


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


def normalize_unicode(
    frame: ArFrame,
    *,
    subset: list[str] | None = None,
    form: str = "NFC",
) -> ArFrame:
    """Normalize Unicode text columns."""

    from .convert import from_pandas, to_pandas

    valid_forms = {"NFC", "NFD", "NFKC", "NFKD"}

    if form not in valid_forms:
        raise ValueError(f"Unsupported Unicode normalization form: {form}")

    if subset is not None:
        validate_columns_exist(
            frame,
            _validate_column_sequence(subset, argument_name="subset"),
            operation="normalize_unicode",
        )

    df = to_pandas(frame).copy()

    columns = (
        subset
        if subset is not None
        else df.select_dtypes(include=["object", "string"]).columns
    )

    for col in columns:
        df[col] = df[col].apply(
            lambda x: unicodedata.normalize(form, x) if isinstance(x, str) else x
        )

    return from_pandas(df)


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


def trim_column_names(frame: ArFrame) -> ArFrame:
    """Strip leading and trailing whitespace from column names.

    Parameters
    ----------
    frame : ArFrame
        Input data frame.

    Returns
    -------
    ArFrame
        New frame with trimmed column names.

    Raises
    ------
    ValueError
        If trimming would create duplicate column names.

    Examples
    --------
    >>> frame = ar.read_csv("data.csv")  # columns: [" name ", " age "]
    >>> clean = ar.trim_column_names(frame)  # columns: ["name", "age"]
    """
    from .convert import from_pandas, to_pandas

    df = to_pandas(frame)
    trimmed = [col.strip() for col in df.columns]

    if len(trimmed) != len(set(trimmed)):
        raise ValueError(f"Trimming column names would create duplicates: {trimmed}")

    df = df.copy()
    df.columns = trimmed
    return from_pandas(df)


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

    if column not in df.columns:
        raise ValueError(f"Unknown column: {column}")

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


def combine_columns(
    frame,
    *,
    subset: list[str] | None = None,
    separator: str = " ",
    output_column: str = "combined",
):
    """Combine multiple columns into a single output column.

    Parameters
    ----------
    frame : ArFrame or pd.DataFrame
        Input data frame.
    subset : list[str], optional
        Columns to combine. If None, all columns are used.
    separator : str
        String used to separate values in the output column.
    output_column : str
        Name of the new column to store combined values.

    Returns
    -------
    ArFrame or pd.DataFrame
        Frame with the combined output column appended.
    """
    import pandas as pd

    from .convert import from_pandas, to_pandas

    if not isinstance(separator, str):
        raise TypeError("separator must be a string")
    if not isinstance(output_column, str) or not output_column.strip():
        raise ValueError("output_column must be a non-empty string")

    is_arframe = not isinstance(frame, pd.DataFrame)
    df = to_pandas(frame) if is_arframe else frame.copy()

    if subset is None:
        subset_columns = list(df.columns)
    else:
        subset_columns = _validate_column_sequence(subset, argument_name="subset")
        missing = [column for column in subset_columns if column not in df.columns]
        if missing:
            available = ", ".join(df.columns) or "<none>"
            raise KeyError(
                f"Missing columns for combine_columns: {missing}. Available columns: {available}"
            )

    if not subset_columns:
        raise ValueError("subset must contain at least one column")

    if output_column in df.columns:

        raise ValueError(f"Output column '{output_column}' already exists.")

    combined = (
        df[subset_columns].astype("string").fillna("").agg(separator.join, axis=1)
    )
    null_mask = df[subset_columns].isna().all(axis=1)
    combined = combined.mask(null_mask, pd.NA)

    df = df.copy()
    df[output_column] = combined

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


def replace_values(frame, mapping, column=None):
    """Replace values based on a mapping dict.

    If column is None, applies to all columns.

    Handles None/NaN in mappings:
    - If mapping has a null-like key (None / NaN / pd.NA), this replaces existing nulls via fillna.
    - If mapping maps to a null-like value, the replacement will result in real nulls (NaN/NA).

    Parameters
    ----------
    frame : ArFrame
        Input data frame.
    mapping : dict
        Mapping of values to replace.
    column : str, optional
        Specific column to apply replacements to. If None, applies to all columns.

    Returns
    -------
    ArFrame
        New frame with values replaced.

    Examples
    --------
    >>> frame = ar.read_csv("data.csv")
    >>> replaced = ar.replace_values(frame, {"old_value": "new_value"}, column="name")
    """
    import pandas as pd

    from .convert import from_pandas, to_pandas

    if not isinstance(mapping, dict):
        raise TypeError(
            "mapping must be a dict-like mapping of {old_value: new_value}, "
            f"not {type(mapping).__name__}."
        )
    if not mapping:
        raise ValueError("mapping must not be empty")

    is_arframe = not isinstance(frame, pd.DataFrame)
    # Avoid mutating the caller's DataFrame in the direct pandas API path.
    df = to_pandas(frame) if is_arframe else frame.copy()

    if column is not None:
        if not isinstance(column, str) or not column.strip():
            raise TypeError("column must be a non-empty string when provided")
        if column not in df.columns:
            available = ", ".join(map(str, df.columns)) or "<none>"
            raise KeyError(
                f"Column '{column}' not found. Available columns: {available}"
            )

    # Normalize mapping and separate null-key handling because NaN != NaN
    null_key_present = False
    null_replacement = None
    normalized_mapping = {}

    for k, v in mapping.items():
        # detect null-like keys (None, NaN, pd.NA)
        if k is None or pd.isna(k):
            null_key_present = True
            null_replacement = v
        else:
            normalized_mapping[k] = v

    if column:
        s = df[column]
        if normalized_mapping:
            s = s.replace(normalized_mapping)
        if null_key_present:
            # replace existing nulls (NaN/None/pd.NA) in the series
            s = s.fillna(null_replacement)
        df[column] = s
    else:
        if normalized_mapping:
            df = df.replace(normalized_mapping)
        if null_key_present:
            # replace existing nulls anywhere in the dataframe
            df = df.fillna(null_replacement)

    return from_pandas(df) if is_arframe else df


def standardize_missing_tokens(frame, tokens=None, subset=None):
    """Converting missing tokens in the DataFrame to the standard form NaN"""

    import pandas as pd

    from .convert import from_pandas, to_pandas

    is_arframe = not isinstance(frame, pd.DataFrame)
    df = to_pandas(frame) if is_arframe else frame

    df = df.copy()

    default_tokens = ["N/A", "NA", "n/a", "na", "-", "none", "nil", "null", "", "?"]

    # check if the user has passed their own tokens or not
    # Case 1 : when user does not pass a subset
    if subset is None:
        if tokens is None:
            df = df.replace(default_tokens, float("nan"))
        else:
            df = df.replace(tokens, float("nan"))

    # Case 2 : when user passes a subset
    else:
        # check if the subset column is valid or not
        unknown_columns = [column for column in subset if column not in df.columns]
        if unknown_columns:
            raise ValueError(f"Unknown columns in subset: {unknown_columns}")
        if tokens is None:
            df[subset] = df[subset].replace(default_tokens, float("nan"))
        else:
            df[subset] = df[subset].replace(tokens, float("nan"))

    return from_pandas(df) if is_arframe else df
