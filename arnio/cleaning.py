"""
arnio.cleaning
Data cleaning functions.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

import numpy as np
import pandas as pd
from pandas.api.types import is_scalar

from ._core import (
    _cast_types,
    _clip_numeric,
    _Column,
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
from .frame import ArFrame, _validate_arframe

# ---------------------------------------------------------------------------
# Report types for errors="report" mode
# ---------------------------------------------------------------------------


@dataclass
class CastFailure:
    """One failed cast: the original value that could not be converted.

    Attributes
    ----------
    column : str
        Column name where the failure occurred.
    row : int
        0-based row index of the failing value.
    value : str
        Original string representation of the value that failed to cast.
    target_dtype : str
        The target dtype string that was requested (e.g. ``"int64"``).
    """

    column: str
    row: int
    value: str
    target_dtype: str


@dataclass
class CastReport:
    """Result of ``cast_types(..., errors="report")``.

    Attributes
    ----------
    frame : ArFrame
        The cast frame. Failures are represented as null values.
    failures : list[CastFailure]
        All values that could not be cast, in row order.

    Examples
    --------
    >>> report = ar.cast_types(frame, {"age": "int64"}, errors="report")
    >>> if report:
    ...     for f in report.failures:
    ...         print(f.column, f.row, f.value)
    """

    frame: ArFrame
    failures: list[CastFailure] = field(default_factory=list)

    def __len__(self) -> int:
        return len(self.failures)

    def __bool__(self) -> bool:
        """``True`` when there is at least one failure."""
        return bool(self.failures)


def _wrap(cpp_result, source: ArFrame) -> ArFrame:
    """Wrap a C++ frame result, carrying over a deep copy of source attrs."""
    return ArFrame(
        cpp_result,
        attrs=copy.deepcopy(source._attrs),
    )


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
    _validate_arframe(frame)
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
    if not isinstance(columns, Sequence) and not isinstance(columns, pd.Index):
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
    reject_duplicates: bool = False,
    missing_error: type[Exception] = KeyError,
    missing_message: Callable[[list[str], str], str] | None = None,
) -> list[str]:
    normalized = _validate_column_sequence(columns, argument_name=argument_name)

    if not normalized and not allow_empty:
        raise ValueError(f"{argument_name} cannot be empty")

    if reject_duplicates:
        seen = set()
        duplicates = []
        for col in normalized:
            if col in seen and col not in duplicates:
                duplicates.append(col)
            seen.add(col)
        if duplicates:
            raise ValueError(
                f"{argument_name} contains duplicate column names: {duplicates}"
            )

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


def _validate_frame(
    frame: ArFrame | pd.DataFrame,
    *,
    allow_pandas: bool = False,
) -> tuple[ArFrame | pd.DataFrame, bool]:
    if isinstance(frame, ArFrame):
        return frame, True
    if allow_pandas and isinstance(frame, pd.DataFrame):
        return frame, False
    if allow_pandas:
        raise TypeError("frame must be an ArFrame or a pandas DataFrame")
    raise TypeError("frame must be an ArFrame")


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
    _validate_arframe(frame)
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
    return _wrap(result, frame)


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
    _validate_arframe(frame)
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
        return frame.drop_columns([])
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
    frame, is_arframe = _validate_frame(frame, allow_pandas=True)
    if isinstance(subset, str):
        raise TypeError(
            f"keep_rows_with_nulls: 'subset' must be a list of column names, "
            f"not a string. Did you mean subset=['{subset}']?"
        )

    from .convert import from_pandas, to_pandas

    df = to_pandas(frame) if is_arframe else frame

    if subset is not None:
        subset = _validate_column_sequence(subset, argument_name="subset")

        if len(subset) == 0:
            raise ValueError(
                "keep_rows_with_nulls: subset cannot be empty; "
                "pass subset=None to check all columns"
            )
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
    """Return a new frame containing only the requested columns.

    Parameters
    ----------
    frame : ArFrame
        Input data frame.
    columns : sequence of str
        Column names to keep.

    Returns
    -------
    ArFrame
        New frame containing only the specified columns, in the order given.

    Raises
    ------
    TypeError
        If columns is a string/bytes value or contains non-string items.
    KeyError
        If any requested column does not exist in the frame.

    Examples
    --------
    >>> frame = ar.read_csv("data.csv")
    >>> subset = ar.select_columns(frame, ["name", "revenue"])
    """
    _validate_arframe(frame)
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
    _validate_arframe(frame)
    if subset is not None:
        subset = _validate_column_sequence(subset, argument_name="subset")
        if len(subset) == 0:
            raise ValueError(
                "fill_nulls: subset cannot be empty; pass subset=None to fill all columns"
            )
        subset = _validate_existing_column_sequence(
            subset,
            available_columns=frame.columns,
            argument_name="subset",
            missing_message=lambda missing, available: (
                f"Missing columns for fill_nulls: {missing}. "
                f"Available columns: {available}"
            ),
        )
    if not isinstance(value, (str, int, float, bool)):
        raise TypeError(
            f"fill value must be a supported scalar (str, int, float, or bool), "
            f"got {type(value).__name__!r}"
        )
    if isinstance(value, bool):
        dtype_map = dict(frame.dtypes)
        target_cols = subset if subset is not None else frame.columns
        for col_name in target_cols:
            if dtype_map.get(col_name) in ("int64", "float64"):
                raise TypeError(
                    f"fill_nulls: fill value {value!r} has type 'bool', which is not "
                    f"compatible with column {col_name!r}. "
                    f"Use an integer value instead."
                )
    result = _fill_nulls(frame._frame, value, subset=subset)
    return _wrap(result, frame)


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
    _validate_arframe(frame)

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
    if frame.shape[1] == 0:
        from ._core import _Frame

        return _wrap(_Frame.from_dict({}, {}, frame.shape[0]), frame)
    result = _drop_duplicates(frame._frame, subset=subset, keep=keep_arg)
    return _wrap(result, frame)


def drop_constant_columns(
    frame: ArFrame | pd.DataFrame,
) -> ArFrame | pd.DataFrame:
    """Remove columns with exactly one unique value.

    Nulls are counted as values when determining whether a column is constant.
    This means columns like ``[None, None]`` are dropped, while columns like
    ``[1, 1, None]`` are kept. Empty columns in zero-row frames are also kept,
    since they have zero unique values rather than one.

    If every column is dropped, the resulting zero-column frame preserves the
    original row count.

    Parameters
    ----------
    frame : ArFrame or pd.DataFrame
        Input data frame.

    Returns
    -------
    ArFrame or pd.DataFrame
        New frame without constant columns.

    Examples
    --------
    >>> frame = ar.read_csv("data.csv")
    >>> reduced = ar.drop_constant_columns(frame)
    """
    from .convert import from_pandas, to_pandas

    frame, is_arframe = _validate_frame(frame, allow_pandas=True)
    df = to_pandas(frame) if is_arframe else frame
    if len(df.index) == 0:
        result_df = df.copy(deep=True)

        if is_arframe:
            result = from_pandas(result_df)

            if getattr(frame, "_attrs", None) is not None:
                result._attrs = copy.deepcopy(frame._attrs)

            return result

        return result_df

    nunique_counts = df.nunique(dropna=False)
    constant_columns = nunique_counts[nunique_counts == 1].index.tolist()
    result_df = df.drop(columns=constant_columns)
    return from_pandas(result_df) if is_arframe else result_df


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
    _validate_arframe(frame)
    from .convert import to_pandas

    if frame.shape[0] == 0:
        attrs = copy.deepcopy(frame._attrs) if frame._attrs is not None else None
        empty_columns_data: dict[str, list[object]] = {}
        empty_dtype_hints: dict[str, _DType] = {}
        for col_name in frame.columns:
            empty_columns_data[col_name] = []
            empty_dtype_hints[col_name] = frame._frame.column_by_name(col_name).dtype()
        return ArFrame(
            _Frame.from_dict(empty_columns_data, empty_dtype_hints, 0), attrs=attrs
        )

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
    _validate_arframe(frame)
    if lower is not None:
        if isinstance(lower, bool) or not isinstance(lower, (int, float)):
            raise TypeError(
                f"clip_numeric(): 'lower' must be an int or float, got {type(lower).__name__!r}."
            )
    if upper is not None:
        if isinstance(upper, bool) or not isinstance(upper, (int, float)):
            raise TypeError(
                f"clip_numeric(): 'upper' must be an int or float, got {type(upper).__name__!r}."
            )
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
        subset = _validate_existing_column_sequence(
            subset,
            available_columns=frame.columns,
            argument_name="subset",
            missing_error=ValueError,
            missing_message=lambda missing, _available: (
                f"Unknown columns in subset: {missing}"
            ),
        )

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
    return _wrap(result, frame)


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

    Examples
    --------
    >>> import arnio as ar
    >>> frame = ar.read_csv("data.csv")
    >>> clean = ar.winsorize_outliers(frame, lower=0.01, upper=0.99, subset=["revenue"])
    """
    _validate_arframe(frame)

    for name, value in (("lower", lower), ("upper", upper)):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise TypeError(f"'{name}' must be an int or float")

        if not math.isfinite(value):
            raise ValueError(f"'{name}' must be finite")

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
        return from_pandas(to_pandas(frame))

    df = to_pandas(frame).copy(deep=False)

    for column in target_columns:
        lower_bound = df[column].quantile(lower)
        upper_bound = df[column].quantile(upper)

        series = df[column].astype("float64")

        df[column] = series.clip(
            lower=lower_bound,
            upper=upper_bound,
        )

    return from_pandas(df)


def normalize_minmax(
    frame: ArFrame,
    *,
    subset: list[str] | None = None,
    feature_range: tuple[float, float] = (0.0, 1.0),
) -> ArFrame:
    """Scale numeric columns to a target range using min-max normalization.

    Null values are preserved and excluded from min/max computation.
    Constant columns (all non-null values identical) map to the lower bound
    of ``feature_range`` without raising or producing NaN.

    Parameters
    ----------
    frame : ArFrame
        Input data frame.
    subset : list[str], optional
        Numeric columns to normalize. If None, applies to all int64/float64 columns.
    feature_range : tuple[float, float], default (0.0, 1.0)
        Target output range as (min, max). Both bounds must be finite and min < max.

    Returns
    -------
    ArFrame
        New frame with normalized numeric columns.

    Raises
    ------
    TypeError
        If feature_range is not a tuple or list of two numbers.
    ValueError
        If feature_range bounds are not finite, or min >= max.
        If subset contains non-numeric columns.
        If any column in subset does not exist in the frame.

    Examples
    --------
    >>> import arnio as ar
    >>> frame = ar.read_csv("data.csv")
    >>> scaled = ar.normalize_minmax(frame, subset=["price", "age"])
    >>> scaled = ar.normalize_minmax(frame, feature_range=(-1.0, 1.0))
    >>> # Pipeline usage
    >>> cleaned = ar.pipeline(frame, [
    ...     ("normalize_minmax", {"subset": ["price"], "feature_range": (0.0, 1.0)}),
    ... ])
    """
    frame, _ = _validate_frame(frame)

    # --- validate feature_range ---
    if not isinstance(feature_range, (tuple, list)):
        raise TypeError(
            f"feature_range must be a tuple or list of two numbers, got {type(feature_range).__name__!r}"
        )

    if len(feature_range) != 2:
        raise ValueError(
            f"feature_range must contain exactly 2 elements, got {len(feature_range)}"
        )
    lo, hi = feature_range

    if isinstance(lo, bool) or isinstance(hi, bool):
        raise TypeError("feature_range bounds must be numeric (int or float), not bool")
    if not isinstance(lo, (int, float)) or not isinstance(hi, (int, float)):
        raise TypeError(
            f"feature_range bounds must be numeric (int or float), "
            f"got {type(lo).__name__!r} and {type(hi).__name__!r}"
        )
    if not math.isfinite(lo) or not math.isfinite(hi):
        raise ValueError("feature_range bounds must be finite")
    if lo >= hi:
        raise ValueError(
            f"feature_range min ({lo}) must be strictly less than max ({hi})"
        )

    # --- resolve target columns  ---
    dtypes = frame.dtypes

    numeric_columns = [
        col for col, dtype in dtypes.items() if dtype in ("int64", "float64")
    ]

    if subset is not None:
        subset = _validate_existing_column_sequence(
            subset,
            available_columns=frame.columns,
            argument_name="subset",
            missing_error=ValueError,
            missing_message=lambda missing, available: (
                f"Unknown columns in subset: {missing}. Available: {available}"
            ),
        )
        non_numeric = [
            col
            for col in subset
            if dtypes.get(col) not in ("int64", "float64")
            and not to_pandas(frame)[col].isna().all()
        ]
        if non_numeric:
            raise ValueError(
                f"normalize_minmax only supports numeric columns: {non_numeric}"
            )
        target_columns = subset
    else:
        target_columns = numeric_columns

    if not target_columns:
        return from_pandas(to_pandas(frame))

    # --- scale  ---
    df = to_pandas(frame).copy(deep=False)
    lo_f = float(lo)
    hi_f = float(hi)
    scale = hi_f - lo_f

    for col in target_columns:
        series = df[col].astype("float64")
        col_min = series.min(skipna=True)
        col_max = series.max(skipna=True)

        if pd.isna(col_min):
            # All-null column — leave unchanged
            continue

        if col_min == col_max:
            # Constant column — map to lower bound, preserve nulls
            df[col] = series.where(series.isna(), lo_f)
        else:
            df[col] = lo_f + (series - col_min) / (col_max - col_min) * scale

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
    _validate_arframe(frame)
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
    return _wrap(result, frame)


def hash_columns(
    frame: ArFrame,
    *,
    subset: list[str],
    algorithm: str = "sha256",
) -> ArFrame:
    """Replace values in string columns with their cryptographic hash digest.

    Hashing is performed using the standard-library :mod:`hashlib` module.
    No homegrown digest code is used.

    Each non-null cell in the specified columns is replaced with the
    lowercase hex-encoded digest of its UTF-8 byte representation.  Null
    cells are preserved as null.  Empty strings are hashed normally (they
    are *not* treated as null).

    .. warning::
        Hashing is deterministic pseudonymization, not encryption.
        ``hash_columns`` does not constitute anonymization under GDPR or
        equivalent regulations.  Consult a qualified privacy engineer
        before relying on this step for compliance purposes.

    .. note::
        ``"md5"`` is provided only for speed-sensitive deduplication
        workloads where cryptographic strength is not required.  Use
        ``"sha256"`` (the default) for all other cases.

    Parameters
    ----------
    frame : ArFrame
        Input data frame.
    subset : list[str]
        Column names to hash.  Every column must exist and must be a
        string column; otherwise an error is raised.
    algorithm : {"sha256", "md5"}, default "sha256"
        Hashing algorithm.  Passed directly to :func:`hashlib.new`.

    Returns
    -------
    ArFrame
        New frame with the specified string columns replaced by their
        hex digests.

    Raises
    ------
    ValueError
        If ``subset`` is empty, contains an unknown column name, or
        ``algorithm`` is not ``"sha256"`` or ``"md5"``.
    TypeError
        If a column listed in ``subset`` is not a string column.

    Examples
    --------
    >>> frame = ar.from_pandas(pd.DataFrame({"email": ["a@b.com", None]}))
    >>> clean = ar.hash_columns(frame, subset=["email"])
    >>> clean = ar.pipeline(frame, [
    ...     ("hash_columns", {"subset": ["email", "user_id"], "algorithm": "sha256"}),
    ... ])
    """
    import hashlib as _hashlib

    _validate_arframe(frame)

    if not subset:
        raise ValueError(
            "hash_columns: subset must be a non-empty list of column names."
        )

    subset = _validate_existing_column_sequence(
        subset,
        available_columns=frame.columns,
        argument_name="subset",
        missing_error=ValueError,
        missing_message=lambda missing, available: (
            f"hash_columns: column(s) not found: {missing}. "
            f"Available columns: {available}"
        ),
    )

    if algorithm not in ("sha256", "md5"):
        raise ValueError(
            f"hash_columns: unsupported algorithm {algorithm!r}. "
            'Supported values: "sha256", "md5".'
        )

    # Non-string column check — friendly Python-level TypeError
    for col_name in subset:
        col_dtype = frame.dtypes.get(col_name)
        if col_dtype != "string":
            raise TypeError(
                f"hash_columns: column {col_name!r} has dtype {col_dtype!r}. "
                "Only string columns can be hashed."
            )

    target_set = set(subset)
    cpp_frame = frame._frame

    # Build a new C++ Frame column-by-column using the existing pybind11 Column API.
    # Hashing is done by the standard-library hashlib — no custom digest code.
    new_frame = _Frame()
    for ci in range(cpp_frame.num_cols()):
        src_col = cpp_frame.column_by_index(ci)
        if src_col.name() in target_set:
            out = _Column(src_col.name(), _DType.STRING)
            for r in range(src_col.size()):
                if src_col.is_null(r):
                    out.push_null()
                else:
                    raw: str = src_col.at(r)
                    kwargs = {"usedforsecurity": False} if algorithm == "md5" else {}
                    digest = _hashlib.new(algorithm, raw.encode(), **kwargs).hexdigest()
                    out.push_back(digest)
            new_frame.add_column(out)
        else:
            new_frame.add_column(src_col)

    return _wrap(new_frame, frame)


def normalize_whitespace(frame, columns=None):
    """Collapse internal whitespace runs to a single space in string columns.
    Also strips leading and trailing whitespace.

    Parameters
    ----------
    frame : ArFrame
        Input data frame.
    columns : list of str, optional
        Column names to process. Defaults to all string (object) columns.

    Returns
    -------
    ArFrame
        New frame with normalized whitespace in the specified columns.

    Examples
    --------
    >>> frame = ar.read_csv("data.csv")
    >>> clean = ar.pipeline(frame, [("normalize_whitespace",)])
    """
    frame, is_arframe = _validate_frame(frame, allow_pandas=True)
    df = to_pandas(frame) if is_arframe else frame.copy(deep=False)

    if columns is not None:
        cols = _validate_existing_column_sequence(
            columns,
            available_columns=df.columns,
            argument_name="columns",
            missing_error=ValueError,
            missing_message=lambda missing, available: (
                f"Missing columns for normalize_whitespace: {missing}. "
                f"Available columns: {available}"
            ),
        )
        cols = [c for c in cols if df[c].dtype in ("object", "string")]
    else:
        cols = list(df.select_dtypes(include=["object", "string"]).columns)

    import re

    def _fix_whitespace(val):
        # Only process actual str values; pass through int, bool, float, None, etc.
        if isinstance(val, str):
            return re.sub(r"\s+", " ", val).strip()
        return val

    for col in cols:
        df[col] = df[col].map(_fix_whitespace)
    return from_pandas(df) if is_arframe else df


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

    _validate_arframe(frame)
    if true_values is not None and isinstance(true_values, (str, bytes)):
        raise TypeError(
            "true_values must be a set/list/tuple of strings, not a bare string"
        )
    if false_values is not None and isinstance(false_values, (str, bytes)):
        raise TypeError(
            "false_values must be a set/list/tuple of strings, not a bare string"
        )
    if true_values is not None and (
        isinstance(true_values, Mapping)
        or not isinstance(true_values, (set, list, tuple))
    ):
        raise TypeError("true_values must be a set, list, or tuple of strings")

    if false_values is not None and (
        isinstance(false_values, Mapping)
        or not isinstance(false_values, (set, list, tuple))
    ):
        raise TypeError("false_values must be a set, list, or tuple of strings")
    df = to_pandas(frame).copy(deep=False)
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

    Raises
    ------
    TypeError
        If case_type is not a string.
    ValueError
        If case_type is not one of the supported options.
    KeyError
        If any column in subset does not exist in the frame.

    Examples
    --------
    >>> frame = ar.read_csv("data.csv")
    >>> lower = ar.normalize_case(frame, case_type="lower")
    """
    _validate_arframe(frame)
    if not isinstance(case_type, str):
        raise TypeError("case_type must be a string")
    valid_cases = {"lower", "upper", "title"}
    if case_type not in valid_cases:
        raise ValueError(f"case_type must be one of {valid_cases}, got {case_type!r}")
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
    return _wrap(result, frame)


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

    Parameters
    ----------
    frame : ArFrame
        Input data frame.
    subset : list[str], optional
        Column names to normalize. If None, applies to all string columns.
    form : str, default "NFC"
        Unicode normalization form. One of "NFC", "NFD", "NFKC", "NFKD".

    Returns
    -------
    ArFrame
        New frame with Unicode-normalized string columns.

    Raises
    ------
    ValueError
        If form is not one of the supported normalization forms.
    KeyError
        If any column in subset does not exist in the frame.

    Examples
    --------
    >>> frame = ar.read_csv("data.csv")
    >>> normalized = ar.normalize_unicode(frame, form="NFC")
    """
    _validate_arframe(frame)
    valid_forms = {"NFC", "NFD", "NFKC", "NFKD"}
    if not isinstance(form, str):
        raise TypeError("form must be a string")
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
    new_cpp_frame = _Frame.from_dict(new_columns, dtype_hints, frame.shape[0])
    return _wrap(new_cpp_frame, frame)


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
    _validate_arframe(frame)
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
    return _wrap(result, frame)


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
    _validate_arframe(frame)
    trimmed = [col.strip() for col in frame.columns]

    if len(trimmed) != len(set(trimmed)):
        raise ValueError(f"Trimming column names would create duplicates: {trimmed}")

    mapping = {
        original: updated
        for original, updated in zip(frame.columns, trimmed)
        if original != updated
    }
    result = _rename_columns(frame._frame, mapping)
    return _wrap(result, frame)



def combine_columns(
    frame: ArFrame,
    columns: list[str],
    output_column: str,
    *,
    separator: str = "",
    drop_original: bool = False,
) -> ArFrame:
    """Build a string column by joining multiple existing columns.

    Parameters
    ----------
    frame : ArFrame
        Input data frame.
    columns : list[str]
        Existing columns to combine in order.
    output_column : str
        Name of the new combined column.
    separator : str, default ""
        String inserted between non-null values.
    drop_original : bool, default False
        Whether to remove the source columns after creating the new column.

    Returns
    -------
    ArFrame
        New frame with the combined string column.

    Examples
    --------
    >>> frame = ar.read_csv("people.csv")
    >>> combined = combine_columns(frame, ["first", "last"], "full_name", separator=" ")
    """
    if not isinstance(columns, Iterable) or isinstance(columns, (str, bytes)):
        raise ValueError("columns must be a non-empty list of column names")

    columns = list(columns)
    if not columns:
        raise ValueError("columns must be a non-empty list of column names")

    if not output_column:
        raise ValueError("output_column must be a non-empty string")

    from .convert import from_pandas, to_pandas
    import pandas as pd

    df = to_pandas(frame)
    missing = [column for column in columns if column not in df.columns]
    if missing:
        raise KeyError(f"Missing columns: {missing}")

    def combine_row(row):
        values = []
        for column in columns:
            value = row[column]
            if value is not None and not pd.isna(value):
                values.append(str(value))
        return separator.join(values)

    df[output_column] = df.apply(combine_row, axis=1)
    if drop_original:
        df = df.drop(columns=columns)

    return from_pandas(df)

def cast_types(
    frame: ArFrame,
    mapping: dict[str, str],
    *,
    errors: str = "raise",
) -> ArFrame | CastReport:
    """Cast columns to specified types via {col: type_str} dict.

    Parameters
    ----------
    frame : ArFrame
        Input data frame.
    mapping : dict[str, str]
        Dictionary mapping column names to target type strings
        (e.g., ``"int64"``, ``"float64"``, ``"bool"``, ``"string"``).
    errors : {"raise", "coerce", "ignore", "report"}, default "raise"
        Policy for handling values that cannot be cast:

        ``"raise"``
            Raise ``TypeCastError`` on the first failure, including the
            column name, row index, original value, and target dtype.
        ``"coerce"``
            Silently replace failures with null. Preserves current behaviour;
            note that this can mask upstream data-quality problems.
        ``"ignore"``
            Leave the entire column unchanged when *any* value in it fails;
            the column keeps its original dtype.
        ``"report"``
            Replace failures with null **and** return a :class:`CastReport`
            instead of a plain ``ArFrame``.  The report's ``.failures``
            list contains one :class:`CastFailure` per bad value, with the
            column name, row index, original value, and target dtype.

    Returns
    -------
    ArFrame
        New frame with columns cast to specified types (all modes except
        ``"report"``).
    CastReport
        Cast frame plus a machine-readable list of failures
        (``errors="report"`` only).

    Examples
    --------
    >>> frame = ar.read_csv("data.csv")
    >>> casted = ar.cast_types(frame, {"age": "int64", "score": "float64"})

    >>> # Collect failures without raising
    >>> report = ar.cast_types(frame, {"age": "int64"}, errors="report")
    >>> if report:
    ...     for f in report.failures:
    ...         print(f.column, f.row, repr(f.value), "->", f.target_dtype)
    """
    _validate_arframe(frame)
    if errors not in {"raise", "coerce", "ignore", "report"}:
        raise ValueError(
            "errors must be one of 'raise', 'coerce', 'ignore', or 'report'"
        )

    mapping = _validate_string_mapping(mapping, argument_name="mapping")
    validate_columns_exist(
        frame,
        _validate_column_sequence(list(mapping), argument_name="mapping keys"),
        operation="cast_types",
    )
    try:
        if errors == "ignore":
            cpp_frame = frame._frame
            for column, dtype in mapping.items():
                try:
                    new_cpp_frame, _ = _cast_types(cpp_frame, {column: dtype}, "raise")
                    cpp_frame = new_cpp_frame
                except ValueError as e:
                    if not str(e).startswith("Cannot cast column "):
                        raise
            return _wrap(cpp_frame, frame)

        if errors == "report":
            cpp_frame, raw_failures = _cast_types(frame._frame, mapping, "report")
            failures = [
                CastFailure(
                    column=f["column"],
                    row=f["row"],
                    value=f["value"],
                    target_dtype=f["target_dtype"],
                )
                for f in raw_failures
            ]
            return CastReport(frame=_wrap(cpp_frame, frame), failures=failures)

        # "raise" or "coerce" — C++ handles both natively
        cpp_frame, _ = _cast_types(frame._frame, mapping, errors)
        return _wrap(cpp_frame, frame)

    except ValueError as e:
        raise TypeCastError(str(e)) from e


def _append_clean_step(
    steps: list[tuple],
    name: str,
    option: bool | dict,
) -> None:
    if option is False:
        return

    if option is True:
        steps.append((name,))
        return

    if isinstance(option, Mapping):
        steps.append((name, dict(option)))
        return
    raise TypeError(f"{name} must be bool or dict, got {type(option).__name__}")


def split_column(
    frame: ArFrame,
    column: str,
    into: list[str],
    *,
    sep: str = ",",
    regex: bool = False,
    maxsplit: int = -1,
    drop: bool = False,
) -> ArFrame:
    """Split one string column into multiple output columns.

    Parameters
    ----------
    frame : ArFrame
        Input data frame.
    column : str
        Name of the source column to split.
    into : list[str]
        Names of the output columns.
    sep : str, default ","
        Delimiter or regex pattern to split on.
    regex : bool, default False
        Whether ``sep`` should be treated as a regular expression.
    maxsplit : int, default -1
        Maximum number of splits. ``-1`` means no explicit limit.
    drop : bool, default False
        Whether to drop the original source column.

    Returns
    -------
    ArFrame
        New frame with the split output columns added.
    """
    if column not in frame.columns:
        raise ValueError(f"Unknown source column: {column!r}")
    if not into:
        raise ValueError("into must contain at least one output column")
    if len(set(into)) != len(into):
        raise ValueError("Output column names in into must be unique")

    existing = set(frame.columns) - ({column} if drop else set())
    collisions = existing.intersection(into)
    if collisions:
        names = ", ".join(sorted(collisions))
        raise ValueError(f"Output column already exists: {names}")

    from .convert import from_pandas, to_pandas

    df = to_pandas(frame)
    source = df[column].astype("string")
    parts = source.str.split(sep, n=maxsplit, expand=True, regex=regex)
    parts = parts.reindex(columns=range(len(into)))

    if drop:
        df = df.drop(columns=[column])
    for index, name in enumerate(into):
        df[name] = parts[index].astype("string")

    return from_pandas(df)


def clean(
    frame: ArFrame,
    *,
    strip_whitespace: bool | dict = True,
    drop_nulls: bool | dict = False,
    drop_duplicates: bool | dict = False,
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
    strip_whitespace : bool or dict, default True
        Whether to trim leading/trailing whitespace from string columns.
        Pass a dict to specify kwargs (e.g., {"subset": ["col1"]}).
    drop_nulls : bool or dict, default False
        Whether to remove rows containing null/empty values.
        Pass a dict to specify kwargs (e.g., {"subset": ["col2"]}).
    drop_duplicates : bool or dict, default False
        Whether to remove duplicate rows.
        Pass a dict to specify kwargs (e.g., {"keep": "last"}).

    Returns
    -------
    ArFrame
        New frame with specified cleaning operations applied.

    Examples
    --------
    >>> frame = ar.read_csv("data.csv")
    >>> # Basic boolean usage
    >>> cleaned = ar.clean(frame, strip_whitespace=True, drop_nulls=True)
    >>> # Advanced dict configuration usage
    >>> cleaned = ar.clean(frame, drop_duplicates={"keep": "last"})
    """
    from .pipeline import pipeline

    steps = []

    _append_clean_step(steps, "strip_whitespace", strip_whitespace)
    _append_clean_step(steps, "drop_nulls", drop_nulls)
    _append_clean_step(steps, "drop_duplicates", drop_duplicates)

    return pipeline(frame, steps)


def filter_rows(
    frame: ArFrame | pd.DataFrame,
    column: str,
    op: str,
    value: object,
) -> ArFrame | pd.DataFrame:
    """Filter rows based on a column condition.

    Parameters
    ----------
    frame : ArFrame or pd.DataFrame
        Input data frame. When an ``ArFrame`` is supplied the return value
        is also an ``ArFrame``; when a ``pd.DataFrame`` is supplied the
        return value is a ``pd.DataFrame``.
    column : str
        Name of the column to filter on.
    op : str
        Comparison operator.  Supported values: ``">"``, ``"<"``,
        ``">="``, ``"<="``, ``"=="``, ``"!="``.
    value : object
        Scalar value to compare each cell against.

    Returns
    -------
    ArFrame or pd.DataFrame
        Filtered frame of the same type as the input.

    Examples
    --------
    >>> frame = ar.read_csv("data.csv")
    >>> filtered = ar.filter_rows(frame, column="age", op=">", value=18)
    """
    from pandas.api.types import is_scalar

    from .convert import from_pandas, to_pandas

    frame, is_arframe = _validate_frame(frame, allow_pandas=True)

    if not isinstance(column, str) or not column.strip():
        raise TypeError(
            f"filter_rows: column must be a non-empty string, got {type(column).__name__!r}"
        )

    if not isinstance(op, str):
        raise TypeError(f"filter_rows: op must be a string, got {type(op).__name__!r}")
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

    if not is_scalar(value):
        raise TypeError("filter_rows value must be a scalar")

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

def coalesce_columns(frame: ArFrame, columns: list[str], output_column: str) -> ArFrame:
    """Create a column from the first non-null value across fallback columns."""
    if not columns:
        raise ValueError("coalesce_columns requires at least one source column")

    from .convert import from_pandas, to_pandas

    df = to_pandas(frame)
    missing = [column for column in columns if column not in df.columns]
    if missing:
        raise KeyError(f"Missing columns for coalesce_columns: {missing}")

    result = df.copy()
    result[output_column] = result[columns].bfill(axis=1).iloc[:, 0]
    return from_pandas(result)
