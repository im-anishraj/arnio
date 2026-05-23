"""
arnio.cleaning
Data cleaning functions.
"""

from __future__ import annotations

import copy
import unicodedata
from collections.abc import Callable, Mapping, Sequence
from typing import Any

import numpy as np
import pandas as pd
from pandas.api.types import is_scalar

from ._core import (
    _cast_types,
    _clip_numeric,
    _drop_duplicates,
    _drop_nulls,
    _DType,
    _fill_nulls,
    _Frame,
    _normalize_case,
    _rename_columns,
    _safe_divide_columns,
    _strip_whitespace,
)
from .convert import from_pandas, to_pandas
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
    _validate_existing_column_sequence(
        columns,
        available_columns=frame.columns,
        argument_name="columns",
        missing_message=lambda missing, available: (
            f"Missing columns{f' for {operation}' if operation else ''}: {missing}. "
            f"Available columns: {available}"
        ),
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


def _validate_mapping(
    mapping: Mapping[Any, Any],
    *,
    argument_name: str,
    allow_empty: bool = True,
    non_mapping_message: str | None = None,
) -> dict[Any, Any]:
    if not isinstance(mapping, Mapping):
        raise TypeError(non_mapping_message or f"{argument_name} must be a mapping")

    normalized = dict(mapping)
    if not normalized and not allow_empty:
        raise ValueError(f"{argument_name} must not be empty")

    return normalized


def _validate_existing_column_sequence(
    columns: Sequence[str],
    *,
    available_columns: Sequence[str],
    argument_name: str,
    allow_empty: bool = True,
    missing_error: type[Exception] = KeyError,
    missing_message: Callable[[list[str], str], str] | None = None,
) -> list[str]:
    normalized = _validate_column_sequence(columns, argument_name=argument_name)

    if not normalized and not allow_empty:
        raise ValueError(f"{argument_name} cannot be empty")

    missing = [column for column in normalized if column not in available_columns]
    if missing:
        available = ", ".join(map(str, available_columns)) or "<none>"
        if missing_message is None:
            message = f"Missing columns: {missing}. Available columns: {available}"
        else:
            message = missing_message(missing, available)
        raise missing_error(message)

    return normalized


def _validate_string_mapping(
    mapping: Mapping[str, str],
    *,
    argument_name: str,
    allow_empty: bool = True,
) -> dict[str, str]:
    if not isinstance(mapping, Mapping):
        raise TypeError(
            f"{argument_name} must be a mapping of string keys to strings, "
            f"got {type(mapping).__name__!r}"
        )

    normalized = dict(mapping)
    if not normalized and not allow_empty:
        raise ValueError(f"{argument_name} must not be empty")

    invalid_keys = [key for key in normalized if not isinstance(key, str)]
    if invalid_keys:
        raise TypeError(f"{argument_name} keys must contain only string column names")

    invalid_values = [
        value
        for value in normalized.values()
        if not isinstance(value, str) or not value.strip()
    ]
    if invalid_values:
        raise TypeError(f"{argument_name} values must be non-empty strings")

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
        subset = _validate_column_sequence(subset, argument_name="subset")
        if len(subset) == 0:
            raise ValueError(
                "drop_nulls: subset cannot be empty; pass subset=None to check all columns"
            )
        subset = _validate_existing_column_sequence(
            subset,
            available_columns=frame.columns,
            argument_name="subset",
            missing_message=lambda missing, available: (
                f"Missing columns for drop_nulls: {missing}. "
                f"Available columns: {available}"
            ),
        )
    result = _drop_nulls(frame._frame, subset=subset)
    return ArFrame(result)


def drop_columns(frame: ArFrame, columns: Sequence[str]) -> ArFrame:
    """Return a new frame without the requested columns.

    Parameters
    ----------
    frame : ArFrame
        Input data frame.
    columns : sequence of str
        Column names to remove.

    Returns
    -------
    ArFrame
        New frame with the requested columns removed.

    Raises
    ------
    TypeError
        If columns is a string/bytes value or contains non-string items.
    ValueError
        If any requested column is missing.

    Examples
    --------
    >>> frame = ar.drop_columns(frame, ["debug_col"])
    """
    requested_columns = _validate_existing_column_sequence(
        columns,
        available_columns=frame.columns,
        argument_name="columns",
        missing_error=ValueError,
        missing_message=lambda missing, _available: (
            f"Columns not found in frame: {missing}"
        ),
    )
    if len(requested_columns) == 0:
        return frame
    if len(requested_columns) == len(frame.columns):
        raise ValueError("drop_columns cannot remove all columns from the frame")

    requested_set = set(requested_columns)
    remaining_columns = [
        column for column in frame.columns if column not in requested_set
    ]

    from .convert import from_pandas, to_pandas

    df = to_pandas(frame)
    return from_pandas(df.loc[:, remaining_columns])


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
    KeyError
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

    if subset is not None:
        cols = _validate_existing_column_sequence(
            subset,
            available_columns=df.columns,
            argument_name="subset",
            missing_message=lambda missing, available: (
                f"Missing columns for keep_rows_with_nulls: {missing}. "
                f"Available columns: {available}"
            ),
        )
    else:
        cols = df.columns.tolist()

    mask = df[cols].isnull().any(axis=1)
    result = df[mask].reset_index(drop=True)

    return from_pandas(result) if is_arframe else result


def select_columns(frame: ArFrame, columns: Sequence[str]) -> ArFrame:
    """Return a new frame containing only the requested columns."""
    return frame.select_columns(columns)


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
        subset = _validate_existing_column_sequence(
            subset,
            available_columns=frame.columns,
            argument_name="subset",
            missing_message=lambda missing, available: (
                f"Missing columns for fill_nulls: {missing}. "
                f"Available columns: {available}"
            ),
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
        subset = _validate_column_sequence(subset, argument_name="subset")
        if len(subset) == 0:
            raise ValueError(
                "drop_duplicates: subset cannot be empty; pass subset=None to compare all columns"
            )
        subset = _validate_existing_column_sequence(
            subset,
            available_columns=frame.columns,
            argument_name="subset",
            missing_message=lambda missing, available: (
                f"Missing columns for drop_duplicates: {missing}. "
                f"Available columns: {available}"
            ),
        )
    if keep is True:
        raise ValueError("keep must be one of 'first', 'last', 'none', or False")
    keep_arg = "none" if keep is False else keep
    if keep_arg not in {"first", "last", "none"}:
        raise ValueError("keep must be one of 'first', 'last', 'none', or False")
    result = _drop_duplicates(frame._frame, subset=subset, keep=keep_arg)
    return ArFrame(result)


def drop_constant_columns(frame: ArFrame) -> ArFrame:
    """Remove columns with exactly one unique value.

    Nulls are counted as values when determining whether a column is constant.
    This means columns like ``[None, None]`` are dropped, while columns like
    ``[1, 1, None]`` are kept. Empty columns in zero-row frames are also kept,
    since they have zero unique values rather than one.

    If every column is dropped, the resulting zero-column frame preserves the
    original row count.

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


def drop_empty_columns(frame: ArFrame) -> ArFrame:
    """Remove columns whose values are entirely null or empty strings.

    String values containing only whitespace are treated as empty.

    Parameters
    ----------
    frame : ArFrame
        Input data frame.

    Returns
    -------
    ArFrame
        New frame without fully empty columns.

    Examples
    --------
    >>> frame = ar.read_csv("data.csv")
    >>> reduced = ar.drop_empty_columns(frame)
    """
    from .convert import to_pandas

    df = to_pandas(frame)
    empty_columns: list[str] = []
    for column in df.columns:
        series = df[column]
        is_empty = series.isna() | (
            series.map(lambda value: isinstance(value, str) and value.strip() == "")
        )
        if bool(is_empty.all()):
            empty_columns.append(column)

    remaining_columns = [
        column for column in frame.columns if column not in empty_columns
    ]
    attrs = copy.deepcopy(frame._attrs) if frame._attrs is not None else None
    if remaining_columns:
        columns_data: dict[str, list[object]] = {}
        dtype_hints: dict[str, _DType] = {}
        for column in remaining_columns:
            cpp_column = frame._frame.column_by_name(column)
            columns_data[column] = cpp_column.to_python_list()
            dtype_hints[column] = cpp_column.dtype()
        return ArFrame(_Frame.from_dict(columns_data, dtype_hints), attrs=attrs)

    try:
        return ArFrame(_Frame.from_dict({}, {}, frame.shape[0]), attrs=attrs)
    except TypeError:
        return ArFrame(_Frame(), attrs=attrs)


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
    if lower is None and upper is None:
        raise ValueError("At least one of 'lower' or 'upper' must be provided")
    if lower is not None and upper is not None and lower > upper:
        raise ValueError("lower cannot be greater than upper")

    # Validate subset columns and their types against the frame's own dtype map,
    # avoiding any pandas conversion for the validation step.
    dtypes = frame.dtypes  # dict[str, str] — pure C++ metadata, no round-trip

    def _is_supported_numeric(col_name: str) -> bool:
        return dtypes.get(col_name) in ("int64", "float64")

    if subset is not None:
        unknown_columns = [col for col in subset if col not in dtypes]
        if unknown_columns:
            raise ValueError(f"Unknown columns in subset: {unknown_columns}")

        non_numeric_columns = [col for col in subset if not _is_supported_numeric(col)]
        if non_numeric_columns:
            raise ValueError(
                f"clip_numeric only supports numeric columns: {non_numeric_columns}"
            )

        # Empty subset — nothing to clip, return the frame unchanged.
        # This preserves the behaviour of the previous pandas-based implementation
        # which returned early when target_columns was empty.
        if len(subset) == 0:
            return frame
    else:
        # When no subset is given, check whether there are any clippable columns.
        # If none exist, return the frame unchanged without touching C++.
        if not any(_is_supported_numeric(col) for col in dtypes):
            return frame

    # Validate that bounds supplied for INT64 columns are integral.
    # The C++ path silently truncates float bounds via static_cast<int64_t>, which
    # would change semantics (e.g. lower=1.5 becoming 1).  Raise early so callers
    # get an explicit error rather than silent data mutation.
    int64_cols = [
        col
        for col in (subset if subset is not None else dtypes)
        if dtypes.get(col) == "int64"
    ]
    if int64_cols:
        if lower is not None and lower != int(lower):
            raise ValueError(
                f"lower bound {lower!r} is not an integer value; "
                "clip_numeric does not truncate bounds for int64 columns. "
                "Cast the column to float64 first, or use an integral bound."
            )
        if upper is not None and upper != int(upper):
            raise ValueError(
                f"upper bound {upper!r} is not an integer value; "
                "clip_numeric does not truncate bounds for int64 columns. "
                "Cast the column to float64 first, or use an integral bound."
            )

    # Hot path: delegate entirely to the native C++ implementation.
    # No pandas conversion, no DataFrame copy — operates directly on the
    # columnar C++ Frame and returns a new Frame.
    result = _clip_numeric(
        frame._frame,
        lower=float(lower) if lower is not None else None,
        upper=float(upper) if upper is not None else None,
        subset=subset,
    )
    return ArFrame(result)


def winsorize_outliers(
    frame: ArFrame,
    *,
    lower: float = 0.05,
    upper: float = 0.95,
    subset: list[str] | None = None,
) -> ArFrame:
    """Winsorize numeric columns using quantile-based clipping.

    Parameters
    ----------
    frame : ArFrame
        Input data frame.
    lower : float, default 0.05
        Lower quantile bound.
    upper : float, default 0.95
        Upper quantile bound.
    subset : list[str], optional
        Numeric columns to winsorize. If None, applies to all numeric columns.

    Returns
    -------
    ArFrame
        New frame with winsorized numeric values.
    """

    if lower < 0 or upper > 1:
        raise ValueError("lower and upper must be between 0 and 1")

    if lower >= upper:
        raise ValueError("lower must be less than upper")

    dtypes = frame.dtypes

    numeric_columns = [
        col for col, dtype in dtypes.items() if dtype in ("int64", "float64")
    ]

    if subset is not None:
        unknown_columns = [col for col in subset if col not in dtypes]
        if unknown_columns:
            raise ValueError(f"Unknown columns in subset: {unknown_columns}")

        non_numeric_columns = [
            col for col in subset if dtypes.get(col) not in ("int64", "float64")
        ]
        if non_numeric_columns:
            raise ValueError(
                "winsorize_outliers only supports numeric columns: "
                f"{non_numeric_columns}"
            )

        target_columns = subset
    else:
        target_columns = numeric_columns

    if not target_columns:
        return frame

    df = to_pandas(frame).copy()

    for column in target_columns:
        lower_bound = df[column].quantile(lower)
        upper_bound = df[column].quantile(upper)

        series = df[column].astype("float64")

        df[column] = series.clip(
            lower=lower_bound,
            upper=upper_bound,
        )

    return from_pandas(df)


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
        subset = _validate_existing_column_sequence(
            subset,
            available_columns=frame.columns,
            argument_name="subset",
            missing_message=lambda missing, available: (
                f"Missing columns for strip_whitespace: {missing}. "
                f"Available columns: {available}"
            ),
        )
    result = _strip_whitespace(frame._frame, subset=subset)
    return ArFrame(result)


def parse_bool_strings(
    frame: ArFrame,
    *,
    subset: Sequence[str] | None = None,
    true_values: set[str] | None = None,
    false_values: set[str] | None = None,
) -> ArFrame:
    """Convert common boolean-like string values into actual booleans.

    Parameters
    ----------
    frame : ArFrame
        Input Arnio frame.
    subset : sequence of str, optional
        Columns to apply conversion on. If None, applies to all object/string columns.
    true_values : set[str], optional
        String values treated as True.
    false_values : set[str], optional
        String values treated as False.

    Returns
    -------
    ArFrame
        New frame with parsed boolean values.

    Notes
    -----
    Columns containing both parsed boolean values and unsupported string values
    may round-trip as strings because of ArFrame column typing semantics.
    Unsupported values are preserved unchanged.

    Examples
    --------
    >>> parsed = ar.parse_bool_strings(frame)
    """
    from .convert import from_pandas, to_pandas

    df = to_pandas(frame).copy()
    if true_values is None:
        true_values = {"true", "yes", "y", "1"}
    else:
        invalid = [v for v in true_values if not isinstance(v, str)]
        if invalid:
            raise TypeError(
                f"true_values must contain only strings, got "
                f"{type(invalid[0]).__name__}"
            )

    if false_values is None:
        false_values = {"false", "no", "n", "0"}
    else:
        invalid = [v for v in false_values if not isinstance(v, str)]
        if invalid:
            raise TypeError(
                f"false_values must contain only strings, got "
                f"{type(invalid[0]).__name__}"
            )

    true_values = {v.strip().lower() for v in true_values}
    false_values = {v.strip().lower() for v in false_values}
    overlap = true_values & false_values

    if overlap:
        raise ValueError(
            f"true_values and false_values overlap after normalization: {overlap}"
        )

    if subset is not None:
        validated_columns = _validate_existing_column_sequence(
            subset,
            available_columns=df.columns,
            argument_name="subset",
            allow_empty=False,
            missing_error=ValueError,
            missing_message=lambda missing, _available: (
                f"Columns not found in frame: {missing}"
            ),
        )

        columns = [
            col for col in validated_columns if not pd.api.types.is_bool_dtype(df[col])
        ]
    else:
        columns = df.select_dtypes(include=["object", "string"]).columns.tolist()

    for col in columns:
        df[col] = df[col].apply(
            lambda x: (
                True
                if isinstance(x, str) and x.strip().lower() in true_values
                else (
                    False
                    if isinstance(x, str) and x.strip().lower() in false_values
                    else x
                )
            )
        )

    return from_pandas(df)


def normalize_case(
    frame: ArFrame,
    *,
    subset: list[str] | None = None,
    case_type: str = "lower",
) -> ArFrame:
    """Normalize ASCII letters in string columns to lower/upper/title case.

    Non-ASCII UTF-8 bytes are preserved unchanged. This keeps accented text,
    CJK characters, emoji, and other multibyte data valid while avoiding a
    heavyweight Unicode case-folding dependency.

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
        subset = _validate_existing_column_sequence(
            subset,
            available_columns=frame.columns,
            argument_name="subset",
            missing_message=lambda missing, available: (
                f"Missing columns for normalize_case: {missing}. "
                f"Available columns: {available}"
            ),
        )
    result = _normalize_case(frame._frame, subset=subset, case_type=case_type)
    return ArFrame(result)


def normalize_unicode(
    frame: ArFrame,
    *,
    subset: list[str] | None = None,
    form: str = "NFC",
) -> ArFrame:
    """Normalize Unicode text columns.

    This implementation operates natively on the ArFrame's internal columnar
    representation, avoiding a full pandas roundtrip. Only STRING columns are
    processed; all other column types are cloned unchanged.
    """
    valid_forms = {"NFC", "NFD", "NFKC", "NFKD"}
    if form not in valid_forms:
        raise ValueError(f"Unsupported Unicode normalization form: {form}")
    if subset is not None:
        subset = _validate_existing_column_sequence(
            subset,
            available_columns=frame.columns,
            argument_name="subset",
            missing_message=lambda missing, available: (
                f"Missing columns for normalize_unicode: {missing}. "
                f"Available columns: {available}"
            ),
        )
    cpp_frame = frame._frame
    num_cols = cpp_frame.num_cols()
    target_names: set[str] = (
        set(subset)
        if subset is not None
        else {
            cpp_frame.column_by_index(i).name()
            for i in range(num_cols)
            if cpp_frame.column_by_index(i).dtype() == _DType.STRING
        }
    )
    new_columns: dict[str, list[object]] = {}
    dtype_hints: dict[str, _DType] = {}
    _normalize = unicodedata.normalize
    for i in range(num_cols):
        col = cpp_frame.column_by_index(i)
        name = col.name()
        dtype = col.dtype()
        if name in target_names and dtype == _DType.STRING:
            values = col.to_python_list()
            new_columns[name] = [
                _normalize(form, v) if v is not None else None for v in values
            ]
            dtype_hints[name] = _DType.STRING
        else:
            new_columns[name] = col.to_python_list()
            dtype_hints[name] = dtype
    new_cpp_frame = _Frame.from_dict(new_columns, dtype_hints)
    return ArFrame(
        new_cpp_frame,
        attrs=copy.deepcopy(frame._attrs) if frame._attrs is not None else None,
    )


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
    mapping = _validate_string_mapping(mapping, argument_name="mapping")
    validate_columns_exist(
        frame,
        _validate_column_sequence(list(mapping), argument_name="mapping keys"),
        operation="rename_columns",
    )

    target_names = list(mapping.values())
    duplicate_targets = sorted(
        {name for name in target_names if target_names.count(name) > 1}
    )
    if duplicate_targets:
        raise ValueError(
            f"rename_columns target names would create duplicates: {duplicate_targets}"
        )

    mapped_sources = set(mapping)
    unmapped_columns = set(frame.columns) - mapped_sources
    collisions = sorted(name for name in target_names if name in unmapped_columns)
    if collisions:
        raise ValueError(
            "rename_columns target names collide with existing columns that are not "
            f"being renamed: {collisions}"
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
    trimmed = [col.strip() for col in frame.columns]

    if len(trimmed) != len(set(trimmed)):
        raise ValueError(f"Trimming column names would create duplicates: {trimmed}")

    mapping = {
        original: updated
        for original, updated in zip(frame.columns, trimmed)
        if original != updated
    }
    result = _rename_columns(frame._frame, mapping)
    return ArFrame(result)


def cast_types(
    frame: ArFrame,
    mapping: dict[str, str],
    *,
    errors: str = "raise",
) -> ArFrame:
    """Cast columns to specified types via {col: type_str} dict.

    Parameters
    ----------
    frame : ArFrame
        Input data frame.
    mapping : dict[str, str]
        Dictionary mapping column names to target type strings (e.g., "int64", "float64", "bool", "string").
    errors : {"raise", "coerce"}, default "raise"
        Whether invalid casts raise ``TypeCastError`` or become null values.

    Returns
    -------
    ArFrame
        New frame with columns cast to specified types.

    Examples
    --------
    >>> frame = ar.read_csv("data.csv")
    >>> casted = ar.cast_types(frame, {"age": "int64", "score": "float64"})
    """
    if errors not in {"raise", "coerce"}:
        raise ValueError("errors must be either 'raise' or 'coerce'")

    mapping = _validate_string_mapping(mapping, argument_name="mapping")
    validate_columns_exist(
        frame,
        _validate_column_sequence(list(mapping), argument_name="mapping keys"),
        operation="cast_types",
    )
    try:
        result = _cast_types(
            frame._frame,
            mapping,
            errors == "coerce",
        )
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

    try:
        mask = getattr(df[column], ops[op])(value)
    except TypeError as exc:
        raise TypeError(
            f"filter_rows: cannot compare column {column!r} with value "
            f"{value!r} using operator {op!r}: {exc}"
        ) from exc

    mask = mask.fillna(False).astype(bool)
    filtered = df[mask]
    if is_arframe:
        filtered = filtered.reset_index(drop=True)

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
        cols_to_round = _validate_existing_column_sequence(
            subset,
            available_columns=df.columns,
            argument_name="subset",
            missing_error=ValueError,
            missing_message=lambda missing, _available: (
                "round_numeric_columns: unknown column(s) in subset: "
                f"{missing}. Available columns: {list(df.columns)}"
            ),
        )
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

    from .frame import ArFrame

    if not isinstance(separator, str):
        raise TypeError("separator must be a string")
    if not isinstance(output_column, str) or not output_column.strip():
        raise ValueError("output_column must be a non-empty string")

    is_arframe = isinstance(frame, ArFrame)
    if not is_arframe and not isinstance(frame, pd.DataFrame):
        raise TypeError("frame must be an ArFrame or a pandas DataFrame")

    column_names = list(frame.columns)

    if subset is None:
        subset_columns = list(column_names)
    else:
        subset_columns = _validate_existing_column_sequence(
            subset,
            available_columns=column_names,
            argument_name="subset",
            missing_message=lambda missing, available: (
                f"Missing columns for combine_columns: {missing}. "
                f"Available columns: {available}"
            ),
        )

    if not subset_columns:
        raise ValueError("subset must contain at least one column")

    if output_column in column_names:
        raise ValueError(f"Output column '{output_column}' already exists.")

    if is_arframe:
        from ._arnio_cpp import combine_columns as _combine_columns

        result = _combine_columns(
            frame._frame, subset_columns, separator, output_column
        )
        return ArFrame(result)

    # Pandas fallback
    df = frame.copy()
    combined = (
        df[subset_columns].astype("string").fillna("").agg(separator.join, axis=1)
    )
    null_mask = df[subset_columns].isna().all(axis=1)
    combined = combined.mask(null_mask, pd.NA)

    df[output_column] = combined

    return df


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

    is_arframe = isinstance(frame, ArFrame)

    columns = frame.columns if is_arframe else frame.columns

    if numerator not in columns:
        raise ValueError(f"Numerator column '{numerator}' not found in frame.")
    if denominator not in columns:
        raise ValueError(f"Denominator column '{denominator}' not found in frame.")
    if not isinstance(output_column, str) or not output_column.strip():
        raise ValueError("output_column must be a non-empty string.")
    if output_column in columns:
        import warnings

        warnings.warn(
            f"Output column '{output_column}' already exists and will be overwritten.",
            UserWarning,
            stacklevel=2,
        )

    if is_arframe:
        numerator_dtype = frame.dtypes.get(numerator)
        denominator_dtype = frame.dtypes.get(denominator)

        numeric_types = {"int64", "float64"}

        if numerator_dtype in numeric_types and denominator_dtype in numeric_types:
            return ArFrame(
                _safe_divide_columns(
                    frame._frame,
                    numerator,
                    denominator,
                    output_column,
                    fill_value,
                )
            )

    df = to_pandas(frame) if is_arframe else frame

    numerator_series = df[numerator]
    denominator_series = df[denominator]

    # Always coerce through pd.to_numeric so that numeric-looking strings
    # ("0", "0.0", "2.5") are handled identically to their numeric equivalents.
    # This fixes the bug where string "0" was not caught as a zero denominator.
    numerator_values = pd.to_numeric(numerator_series, errors="coerce")
    denominator_values = pd.to_numeric(denominator_series, errors="coerce")

    # Distinguish null originals (None / pd.NA → use fill_value) from
    # invalid non-null strings ("abc" → raise ValueError).
    # A value is "bad" if pd.to_numeric produced NaN but the original was
    # not null — i.e. it was a non-null, non-numeric string.
    bad_numerator = numerator_values.isna() & numerator_series.notna()
    bad_denominator = denominator_values.isna() & denominator_series.notna()

    if bad_numerator.any():
        bad_values = df.loc[bad_numerator, numerator].head(3).tolist()
        raise ValueError(
            f"Numerator column '{numerator}' contains non-numeric values: {bad_values}"
        )
    if bad_denominator.any():
        bad_values = df.loc[bad_denominator, denominator].head(3).tolist()
        raise ValueError(
            f"Denominator column '{denominator}' contains non-numeric values: {bad_values}"
        )

    # Mask zero and null denominators — both numeric 0 and string "0" / "0.0"
    # are caught here because denominator_values is already coerced to float.
    is_zero_or_null = denominator_values.isna() | (denominator_values == 0)
    safe_denom = denominator_values.mask(is_zero_or_null)
    result = numerator_values / safe_denom
    df = df.copy()
    df[output_column] = result.fillna(fill_value)

    return from_pandas(df) if is_arframe else df


def drop_columns_matching(frame, pattern):
    """Drop columns whose names match a given pattern.

    Parameters
    ----------
    frame : ArFrame or pd.DataFrame
        Input data frame.
    pattern : str
        Regex pattern to match column names against.

    Returns
    -------
    ArFrame or pd.DataFrame
        Data frame with matching columns removed.

    Raises
    ------
    TypeError
        If pattern is not a string.
    re.error
        If pattern is not a valid regex.
    ValueError
        If pattern matches all columns.

    Examples
    --------
    >>> frame = ar.read_csv("data.csv")
    >>> cleaned = drop_columns_matching(frame, "^temp_")
    """
    import re

    import pandas as pd

    from .convert import from_pandas, to_pandas

    if not isinstance(pattern, str):
        raise TypeError(f"pattern must be a string, got {type(pattern).__name__}")

    try:
        re.compile(pattern)
    except re.error as e:
        raise re.error(f"Invalid regex pattern: {pattern!r}") from e

    is_arframe = not isinstance(frame, pd.DataFrame)
    df = to_pandas(frame) if is_arframe else frame

    cols_to_drop = [col for col in df.columns if re.search(pattern, col)]

    if len(cols_to_drop) == len(df.columns):
        raise ValueError(
            "Pattern matches all columns. At least one column must remain."
        )

    result = df.drop(columns=cols_to_drop)

    return from_pandas(result) if is_arframe else result


def _is_null_mapping_key(value):
    """
    Return True when a mapping key represents a scalar null value.

    Prevents ambiguous truth-value evaluation for tuple/list/array-like
    objects when using pandas.isna().
    """
    if value is None:
        return True

    # Avoid calling pd.isna on tuple/list/array-like values
    if not is_scalar(value):
        return False

    return bool(pd.isna(value))


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

    mapping = _validate_mapping(
        mapping,
        argument_name="mapping",
        allow_empty=False,
        non_mapping_message=(
            "mapping must be a dict-like mapping of {old_value: new_value}, "
            f"not {type(mapping).__name__}."
        ),
    )
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
        # Handle scalar null-like keys safely without evaluating
        # tuple/list/array-like objects in boolean context.
        if _is_null_mapping_key(k):
            null_key_present = True
            null_replacement = v
        # Exclude tuple/list/ndarray/series/index keys which pandas.replace
        # does not support and can raise confusing errors (e.g. operand
        # length mismatch). Treat strings and true scalars as valid keys.
        elif is_scalar(k) and not isinstance(
            k, (tuple, list, np.ndarray, pd.Series, pd.Index)
        ):
            normalized_mapping[k] = v
        else:
            # pandas replace does not support non-scalar mapping keys like tuples
            # and lists. Ignore those keys rather than raising a user-facing error.
            continue

    if column:
        s = df[column]
        original_null_mask = s.isna() if null_key_present else None
        if normalized_mapping:
            s = s.replace(normalized_mapping)
        if null_key_present:
            # Replace only values that were already null before replacement so
            # null-valued mapping results remain real nulls.
            s = s.where(~original_null_mask, null_replacement)
        df[column] = s
    else:
        original_null_mask = df.isna() if null_key_present else None
        if normalized_mapping:
            df = df.replace(normalized_mapping)
        if null_key_present:
            # Replace only values that were already null before replacement so
            # null-valued mapping results remain real nulls.
            df = df.where(~original_null_mask, null_replacement)

    return from_pandas(df) if is_arframe else df


def standardize_missing_tokens(frame, tokens=None, subset=None):
    """Converting missing tokens in the DataFrame to the standard form NaN

    Parameters
    ----------
    frame : ArFrame
        Input data frame.
    tokens : list[str], optional
        List of strings to treat as missing. If None, then a built-in default tokens list is used
    subset : list[str], optional
        Column names to replace missing tokens in. If None, applies to all columns.

    Returns
    -------
    ArFrame
        New frame with missing token values replaced by NaN.

    Examples
    --------
    >>> frame = ar.from_pandas(pd.DataFrame({"value": [1, 2, "N/A"]}))
    >>> result = ar.standardize_missing_tokens(frame)
    """

    import pandas as pd

    from .convert import from_pandas, to_pandas

    is_arframe = not isinstance(frame, pd.DataFrame)
    df = to_pandas(frame) if is_arframe else frame

    df = df.copy()
    if isinstance(subset, str):
        raise TypeError(
            f"subset must be a list of column names, not a string. "
            f"Did you mean subset=['{subset}']?"
        )

    default_tokens = ["N/A", "NA", "n/a", "na", "-", "none", "nil", "null", "", "?"]

    if subset is None:
        if tokens is None:
            df = df.replace(default_tokens, float("nan"))
        else:
            df = df.replace(tokens, float("nan"))

    else:
        subset_columns = _validate_existing_column_sequence(
            subset,
            available_columns=df.columns,
            argument_name="subset",
            missing_error=ValueError,
            missing_message=lambda missing, _available: (
                f"Unknown columns in subset: {missing}"
            ),
        )
        if tokens is None:
            df[subset_columns] = df[subset_columns].replace(
                default_tokens, float("nan")
            )
        else:
            df[subset_columns] = df[subset_columns].replace(tokens, float("nan"))

    return from_pandas(df) if is_arframe else df


def coalesce_columns(
    frame,
    *,
    subset: list[str],
    output_column: str = "coalesced",
):
    """Select the first non-null value from a list of columns.

    Parameters
    ----------
    frame : ArFrame or pd.DataFrame
        Input data frame.
    subset : list[str]
        List of columns to check in order.
    output_column : str, default "coalesced"
        Name of the new column to store coalesced values.

    Returns
    -------
    ArFrame or pd.DataFrame
        New frame with coalesced column.
    """
    import pandas as pd

    from .convert import from_pandas, to_pandas
    from .frame import ArFrame

    if not isinstance(subset, list):
        raise TypeError("subset must be a list of column names")
    if not subset:
        raise ValueError("subset must contain at least one column")
    if not isinstance(output_column, str) or not output_column.strip():
        raise ValueError("output_column must be a non-empty string")

    is_arframe = isinstance(frame, ArFrame)
    if not is_arframe and not isinstance(frame, pd.DataFrame):
        raise TypeError("frame must be an ArFrame or a pandas DataFrame")

    column_names = list(frame.columns)
    subset_columns = _validate_existing_column_sequence(
        subset,
        available_columns=column_names,
        argument_name="subset",
        missing_message=lambda missing, available: (
            f"Missing columns for coalesce_columns: {missing}. "
            f"Available columns: {available}"
        ),
    )

    if output_column in column_names:
        raise ValueError(f"Output column '{output_column}' already exists.")

    df = to_pandas(frame) if is_arframe else frame.copy()

    # Select the first non-null/non-NaN/non-None value per row
    df[output_column] = df[subset_columns].bfill(axis=1).iloc[:, 0]

    return from_pandas(df) if is_arframe else df
