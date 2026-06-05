"""
arnio.cleaning
Data cleaning functions.
"""

from __future__ import annotations

import copy
import math
import unicodedata
from collections.abc import Mapping, Sequence
from typing import Any

from ._core import (
    _cast_types,
    _clip_numeric,
    _Column,
    _drop_duplicates,
    _drop_nulls,
    _DType,
    _fill_nulls,
    _make_column_names_unique,
    _Frame,
    _normalize_case,
    _remove_control_characters,
    _rename_columns,
    _safe_divide_columns,
    _strip_whitespace,
    create_rolling_windows,
)
from .exceptions import TypeCastError
from .frame import ArFrame

import pandas as pd
from .convert import from_pandas, to_pandas
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


def _validate_string_mapping(
    mapping: Mapping[str, str],
    *,
    argument_name: str,
    allow_empty: bool = True,
) -> dict[str, str]:
    if not isinstance(mapping, Mapping):
        raise TypeError(f"{argument_name} must be a mapping of string keys to strings")

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
        validate_columns_exist(
            frame,
            _validate_column_sequence(subset, argument_name="subset"),
            operation="drop_nulls",
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
    requested_columns = _validate_column_sequence(columns, argument_name="columns")
    if len(requested_columns) == 0:
        return frame

    missing = [column for column in requested_columns if column not in frame.columns]
    if missing:
        raise ValueError(f"Columns not found in frame: {missing}")
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

    cols = subset if subset is not None else df.columns.tolist()

    # validate that all subset columns actually exist
    if subset is not None:
        validate_columns_exist(
            frame,
            _validate_column_sequence(subset, argument_name="subset"),
            operation="keep_rows_with_nulls",
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
    if subset is not None:
        validate_columns_exist(
            frame,
            _validate_column_sequence(subset, argument_name="subset"),
            operation="drop_duplicates",
        )
    keep_arg = "none" if keep is False else keep
    if keep_arg not in {"first", "last", "none"}:
        raise ValueError("keep must be one of 'first', 'last', 'none', or False")
    if frame.shape[1] == 0:
        from ._core import _Frame

        return _wrap(_Frame.from_dict({}, {}, frame.shape[0]), frame)
    result = _drop_duplicates(frame._frame, subset=subset, keep=keep_arg)
    return _wrap(result, frame)


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
        If no bounds are provided, bounds are non-finite (NaN or Inf), bounds are
        inverted, subset contains unknown columns, or subset contains non-numeric
        columns.

    Examples
    --------
    >>> frame = ar.read_csv("data.csv")
    >>> clipped = ar.clip_numeric(frame, lower=0, upper=100)
    """
    if lower is None and upper is None:
        raise ValueError("At least one of 'lower' or 'upper' must be provided")
    if lower is not None and upper is not None and lower > upper:
        raise ValueError("lower cannot be greater than upper")
    if lower is not None and not math.isfinite(lower):
        raise ValueError(
            f"clip_numeric bounds must be finite numbers; got lower={lower!r}"
        )
    if upper is not None and not math.isfinite(upper):
        raise ValueError(
            f"clip_numeric bounds must be finite numbers; got upper={upper!r}"
        )

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

    Examples
    --------
    >>> import arnio as ar
    >>> frame = ar.read_csv("data.csv")
    >>> clean = ar.winsorize_outliers(frame, lower=0.01, upper=0.99, subset=["revenue"])
    """

    if isinstance(lower, bool):
        raise TypeError("lower must not be bool")

    if isinstance(upper, bool):
        raise TypeError("upper must not be bool")

    if not isinstance(lower, (int, float)):
        raise TypeError("lower must be a numeric value")

    if not isinstance(upper, (int, float)):
        raise TypeError("upper must be a numeric value")

    frame, _ = _validate_frame(frame)

    if lower < 0 or upper > 1:
        raise ValueError("lower and upper must be between 0 and 1")

    if lower >= upper:
        raise ValueError("lower must be less than upper")

    dtypes = frame.dtypes

    numeric_columns = [
        col for col, dtype in dtypes.items() if dtype in ("int64", "float64")
    ]

    if subset is not None:
        subset = _validate_column_sequence(
            subset,
            argument_name="subset",
        )

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
        validate_columns_exist(
            frame,
            _validate_column_sequence(subset, argument_name="subset"),
            operation="strip_whitespace",
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
        columns = _validate_column_sequence(subset, argument_name="subset")

        if len(columns) == 0:
            raise ValueError("subset cannot be empty")

        missing = [col for col in columns if col not in df.columns]

        if missing:
            raise ValueError(f"Columns not found in frame: {missing}")
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


def remove_control_characters(
    frame: ArFrame,
    *,
    subset: list[str] | None = None,
) -> ArFrame:
    """Remove control characters from string columns.

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
    >>> clean = ar.remove_control_characters(frame, subset=["name"])
    """
    result = _remove_control_characters(frame._frame, subset=subset)
    return ArFrame(result)


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
        validate_columns_exist(
            frame,
            _validate_column_sequence(subset, argument_name="subset"),
            operation="normalize_case",
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
    """
    valid_forms = {"NFC", "NFD", "NFKC", "NFKD"}
    if not isinstance(form, str):
        raise TypeError("form must be a string")
    if form not in valid_forms:
        raise ValueError(f"Unsupported normalization form: '{form}'. Supported forms: {', '.join(sorted(valid_forms))}")
    if subset is not None:
        validate_columns_exist(
            frame,
            _validate_column_sequence(subset, argument_name="subset"),
            operation="normalize_unicode",
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
    result = _rename_columns(frame._frame, mapping)
    return ArFrame(result)

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
        (e.g., "int64", "float64", "bool", "string").
        Dictionary mapping column names to target type strings (e.g., "int64", "float64", "bool", "string").
    errors : {"raise", "coerce"}, default "raise"
        Whether invalid casts raise ``TypeCastError`` or become null values.

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
    """
    if errors not in {"raise", "coerce"}:
        raise ValueError("errors must be either 'raise' or 'coerce'")

    >>> # Collect failures without raising
    >>> report = ar.cast_types(frame, {"age": "int64"}, errors="report")
    >>> if report:
    ...     for f in report.failures:
    ...         print(f.column, f.row, repr(f.value), "->", f.target_dtype)
    """
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
    except ValueError as exc:
        raise TypeCastError(
            f"filter_rows: cannot compare column {column!r} with value "
            f"{value!r} using operator {op!r}: {exc}"
        ) from exc

    mask = mask.fillna(False).astype(bool)
    filtered = df[mask]
    if is_arframe:
        filtered = filtered.reset_index(drop=True)

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

    is_arframe = isinstance(frame, ArFrame)
    df = to_pandas(frame) if is_arframe else frame.copy()

    cols_to_process = subset if subset is not None else df.columns.tolist()

    if subset is not None:
        unknown = [col for col in subset if col not in df.columns]
        if unknown:
            raise ValueError(f"Unknown columns in subset: {unknown}")

    for col in cols_to_process:
        if col not in df.columns:
            continue
        if not pd.api.types.is_numeric_dtype(df[col]):
            continue
        df[col] = df[col].astype("float64")
        lower_bound = df[col].quantile(lower)
        upper_bound = df[col].quantile(upper)
        df[col] = df[col].clip(lower=lower_bound, upper=upper_bound)

    return from_pandas(df) if is_arframe else df


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
            raise ValueError(
                f"round_numeric_columns: unknown column(s) in subset: {missing}. "
                f"Available columns: {list(df.columns)}"
            )
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
        subset_columns = _validate_column_sequence(subset, argument_name="subset")
        missing = [column for column in subset_columns if column not in column_names]
        if missing:
            available = ", ".join(column_names) or "<none>"
            raise KeyError(
                f"Missing columns for combine_columns: {missing}. Available columns: {available}"
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

    def join_row(row):
        non_null = [str(v) for v in row if pd.notna(v)]
        if not non_null:
            return pd.NA
        return separator.join(non_null)

    combined = df[subset_columns].apply(join_row, axis=1)

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

    if pd.api.types.is_numeric_dtype(
        numerator_series
    ) and pd.api.types.is_numeric_dtype(denominator_series):
        numerator_values = numerator_series
        denominator_values = denominator_series
        bad_numerator = numerator_values.isna() & numerator_series.notna()
        bad_denominator = denominator_values.isna() & denominator_series.notna()
    else:
        numerator_values = pd.to_numeric(numerator_series, errors="coerce")
        denominator_values = pd.to_numeric(denominator_series, errors="coerce")

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

    safe_denom = denominator_values.mask(
        denominator_values.isna() | denominator_values.eq(0)
    )
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

    if column is not None:
        if not isinstance(column, str) or not column.strip():
            raise TypeError("column must be a non-empty string when provided")

        available_cols = frame.columns if is_arframe else frame.columns.tolist()
        if column not in available_cols:
            available = ", ".join(map(str, available_cols)) or "<none>"
            raise KeyError(
                f"Column '{column}' not found. Available columns: {available}"
            )

    null_key_present = False
    null_replacement = None
    normalized_mapping = {}

    for k, v in mapping.items():
        if k is None or pd.isna(k):
            null_key_present = True
            null_replacement = v
        else:
            normalized_mapping[k] = v

    df = to_pandas(frame) if is_arframe else frame.copy()

    if column:
        s = df[column]
        if normalized_mapping:
            s = s.replace(normalized_mapping)
        if null_key_present:
            s = s.where(~original_null_mask, null_replacement)
        df[column] = s
    else:
        if normalized_mapping:
            df = df.replace(normalized_mapping)
        if null_key_present:
            df = df.where(~original_null_mask, null_replacement)

    return from_pandas(df) if is_arframe else df


def standardize_missing_tokens(frame, tokens=None, subset=None):
    """Converting missing tokens in the DataFrame to the standard form NaN.

    Parameters:
        df (pd.DataFrame): Input dataframe
        columns (list, optional): Columns to clean. If None, all string columns are used.

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
        unknown_columns = [column for column in subset if column not in df.columns]
        if unknown_columns:
            raise ValueError(f"Unknown columns in subset: {unknown_columns}")
        if tokens is None:
            df[subset] = df[subset].replace(default_tokens, float("nan"))
        else:
            df[subset] = df[subset].replace(tokens, float("nan"))

    return from_pandas(df) if is_arframe else df


def coalesce_columns(
    frame,
    *,
    subset: Sequence[str],
    output_column: str = "coalesced",
):
    """Select the first non-null value from a list of columns.

    Parameters
    ----------
    frame : ArFrame or pd.DataFrame
        Input data frame.
    subset : sequence of str
        Sequence of columns to check in order.
    output_column : str, default "coalesced"
        Name of the new column to store coalesced values.

    Returns
    -------
    ArFrame or pd.DataFrame
        New frame with coalesced column.

    Raises
    ------
    TypeError
        If subset is not a list, or frame is not an ArFrame or DataFrame.
    ValueError
        If subset is empty, output_column is empty, or output_column already
        exists in the frame.
    KeyError
        If any column in subset does not exist in the frame.

    Examples
    --------
    >>> frame = ar.read_csv("data.csv")
    >>> result = ar.coalesce_columns(frame, subset=["col_a", "col_b"],
    ...                              output_column="first_non_null")
    """
    from .convert import from_pandas, to_pandas

    frame, is_arframe = _validate_frame(frame, allow_pandas=True)

    if not isinstance(output_column, str) or not output_column.strip():
        raise ValueError("output_column must be a non-empty string")

    column_names = list(frame.columns)
    subset_columns = _validate_existing_column_sequence(
        subset,
        available_columns=column_names,
        argument_name="subset",
        reject_duplicates=True,
        missing_message=lambda missing, available: (
            f"Missing columns for coalesce_columns: {missing}. "
            f"Available columns: {available}"
        ),
    )

    if not subset_columns:
        raise ValueError("subset must contain at least one column")

    if output_column in column_names:
        raise ValueError(f"Output column '{output_column}' already exists.")

    df = to_pandas(frame) if is_arframe else frame.copy(deep=False)

    # Select the first non-null/non-NaN/non-None value per row
    df[output_column] = df[subset_columns].bfill(axis=1).iloc[:, 0]

    return from_pandas(df) if is_arframe else df


def rolling_window(
    data: list[float], window_size: int, stride: int = 1
) -> list[list[float]]:
    """
    Transforms a sequential dataset into overlapping rolling windows.

    Args:
        data: A 1D list of numeric values.
        window_size: The number of elements to include in each window.
        stride: The step size between windows (default is 1).

    Returns:
        A list of sequential window arrays.
    """
    if not isinstance(window_size, int) or isinstance(window_size, bool):
        raise TypeError("window_size must be an integer")
    if not isinstance(stride, int) or isinstance(stride, bool):
        raise TypeError("stride must be an integer")

    return create_rolling_windows(data, window_size, stride)


def clean_column_names(
    frame: ArFrame,
    *,
    subset: list[str] | None = None,
    errors: str = "coerce",
) -> ArFrame:
    """Parse string columns containing numeric characters, currency symbols, or percentages into floats.

    Parameters
    ----------
    frame : ArFrame
        Input data frame.
    subset : list[str], optional
        Column names to parse. If None, applies to all string/object columns.
    errors : str, default "coerce"
        If 'raise', invalid parsing will raise an exception.
        If 'coerce', then invalid parsing will be set as NaN/null.

    Returns
    -------
    ArFrame
        New frame with cleaned column names.

    Raises
    ------
    TypeError
        If case_type is not a string.
    ValueError
        If case_type is invalid or if cleaning would create duplicate column names.
    """
    _validate_arframe(frame)
    if not isinstance(case_type, str):
        raise TypeError("case_type must be a string")
    if case_type not in {"lower", "upper", "none"}:
        raise ValueError("case_type must be one of 'lower', 'upper', or 'none'")

    import re

    cleaned = []
    for col in frame.columns:
        # Replace non-alphanumeric characters with underscores
        name = re.sub(r"[^a-zA-Z0-9_]", "_", col)
        # Trim consecutive underscores
        name = re.sub(r"_+", "_", name)
        # Trim boundary underscores
        name = name.strip("_")
        # Normalize case
        if case_type == "lower":
            name = name.lower()
        elif case_type == "upper":
            name = name.upper()

        if not name:
            name = "column"
        cleaned.append(name)

    if len(cleaned) != len(set(cleaned)):
        raise ValueError(f"Cleaning column names would create duplicates: {cleaned}")

    mapping = {
        original: updated
        for original, updated in zip(frame.columns, cleaned)
        if original != updated
    }
    if not mapping:
        return copy.deepcopy(frame)

    result = _rename_columns(frame._frame, mapping)
    return ArFrame(result)


def slugify_column_names(frame, on_duplicates="raise"):
    import re

    import pandas as pd

    from .convert import from_pandas, to_pandas
    from .frame import ArFrame

    if on_duplicates not in ("raise",):
        raise ValueError("on_duplicates must be 'raise'")

    is_arframe = isinstance(frame, ArFrame)
    if not is_arframe and not isinstance(frame, pd.DataFrame):
        raise TypeError("frame must be an ArFrame or pandas.DataFrame")

    df = to_pandas(frame) if is_arframe else frame

    new_cols = []
    for col in df.columns:
        slug = col.strip()
        slug = re.sub(r"[\s\-]+", "_", slug)
        slug = re.sub(r"[^\w]", "", slug)
        slug = re.sub(r"_+", "_", slug)
        slug = slug.strip("_")
        slug = slug.lower()
        if not slug:
            raise ValueError(f"Column name {col!r} slugifies to an empty string.")
        new_cols.append(slug)

    if len(new_cols) != len(set(new_cols)):
        dupes = [c for c in new_cols if new_cols.count(c) > 1]
        raise ValueError(f"Duplicate slugs after slugifying: {set(dupes)}")

    df = df.copy()
    df.columns = new_cols
    return from_pandas(df) if is_arframe else df

def parse_numeric_strings(
    frame: ArFrame,
    *,
    subset: list[str] | None = None,
    errors: str = "coerce",
) -> ArFrame:
    """Parse string columns containing numeric characters, currency symbols, or percentages into floats.

    Parameters
    ----------
    frame : ArFrame
        Input data frame.
    subset : list[str], optional
        Column names to parse. If None, applies to all string/object columns.
    errors : str, default "coerce"
        If 'raise', invalid parsing will raise an exception.
        If 'coerce', then invalid parsing will be set as NaN/null.

    Returns
    -------
    ArFrame
        New frame with parsed numeric columns.

    Examples
    --------
    >>> frame = ar.read_csv("data.csv")
    >>> cleaned = ar.parse_numeric_strings(frame, subset=["price", "discount"])
    """
    if errors not in ("coerce", "raise"):
        raise ValueError(f"errors parameter must be 'coerce' or 'raise', not '{errors}'")

    if subset is not None:
        validate_columns_exist(
            frame,
            _validate_column_sequence(subset, argument_name="subset"),
            operation="parse_numeric_strings",
        )

    is_arframe = not isinstance(frame, pd.DataFrame)
    df = to_pandas(frame) if is_arframe else frame.copy()

    if subset is not None:
        target_columns = subset
    else:
        target_columns = df.select_dtypes(include=["object", "string"]).columns.tolist()

    if not target_columns:
        return frame

    for col in target_columns:
        if pd.api.types.is_string_dtype(df[col]) or pd.api.types.is_object_dtype(df[col]):
            cleaned_series = df[col].astype(str).str.strip()
            cleaned_series = cleaned_series.str.replace(r"[$,£€]", "", regex=True)
            is_percent = cleaned_series.str.endswith("%")
            cleaned_series = cleaned_series.str.replace("%", "", regex=False)
            numeric_series = pd.to_numeric(cleaned_series, errors=errors)
            numeric_series.loc[is_percent] = numeric_series.loc[is_percent] / 100.0
            df[col] = numeric_series

    return from_pandas(df) if is_arframe else df

def find_fuzzy_duplicates(
    frame,
    *,
    subset: list[str] | None = None,
    threshold: float = 0.85,
    ignore_case: bool = True,
    normalize_whitespace: bool = True,
) -> list[list[int]]:
    """Return groups of near-duplicate row indices using similarity matching.

    Uses ``difflib.SequenceMatcher`` from the Python standard library —
    no new dependencies are required.

    Row similarity is computed as the average ``SequenceMatcher.ratio()``
    across the comparison columns (string columns only).  Numeric and bool
    columns use exact equality.  Only groups of two or more rows are returned.

    Parameters
    ----------
    frame : ArFrame or pd.DataFrame
        Input data frame.
    subset : list[str], optional
        Column names to compare.  ``None`` (default) uses all string columns.
    threshold : float, default 0.85
        Minimum similarity in [0.0, 1.0] to treat two rows as near-duplicates.
        Use ``1.0`` for exact duplicates only.
    ignore_case : bool, default True
        Normalize string values to lowercase before comparison.
    normalize_whitespace : bool, default True
        Collapse consecutive whitespace characters to a single space and strip
        leading/trailing whitespace before comparison.

    Returns
    -------
    list[list[int]]
        Each inner list is a group of row indices (0-based) that are
        near-duplicates of each other.  Exact duplicates (similarity = 1.0)
        are always included regardless of threshold.

    Raises
    ------
    ValueError
        If ``threshold`` is outside [0.0, 1.0].
    ValueError
        If ``subset`` is empty or contains non-existent column names.
    ValueError
        If the frame has more than 50,000 rows and no ``subset`` is provided,
        to avoid accidental O(n²) execution on large datasets.

    Examples
    --------
    >>> groups = ar.find_fuzzy_duplicates(frame, threshold=0.85)
    >>> for group in groups:
    ...     print(group)   # e.g. [0, 2] means rows 0 and 2 are near-duplicates

    >>> # Only compare the "name" column, case-insensitively
    >>> groups = ar.find_fuzzy_duplicates(frame, subset=["name"], threshold=0.9)
    """
    import difflib
    import re

    from .convert import to_pandas
    from .frame import ArFrame

    # --- validate threshold -------------------------------------------------
    if not (0.0 <= threshold <= 1.0):
        raise ValueError(f"threshold must be between 0.0 and 1.0, got {threshold!r}")

    # --- validate and normalise input to pandas ----------------------------
    is_arframe = isinstance(frame, ArFrame)
    if not is_arframe and not isinstance(frame, pd.DataFrame):
        raise TypeError(
            f"find_fuzzy_duplicates() expects an ArFrame or pandas DataFrame, "
            f"got {type(frame).__name__!r}"
        )
    df = to_pandas(frame) if is_arframe else frame.copy()

    # --- validate / resolve subset BEFORE early-return checks ---------------
    if subset is not None:
        if len(subset) == 0:
            raise ValueError(
                "find_fuzzy_duplicates: subset cannot be empty; "
                "pass subset=None to compare all string columns."
            )
        missing = [c for c in subset if c not in df.columns]
        if missing:
            raise ValueError(
                f"find_fuzzy_duplicates: column(s) not found: {missing}. "
                f"Available: {list(df.columns)}"
            )
        compare_cols = list(subset)

    n_rows = len(df)
    if n_rows == 0:
        return []
    if n_rows == 1:
        return []

    if subset is not None:
        pass  # already resolved above

    else:
        # default: all object/string columns
        compare_cols = df.select_dtypes(include=["object", "string"]).columns.tolist()
        if not compare_cols:
            # fall back to all columns if no string columns found
            compare_cols = list(df.columns)

    # --- size guard ---------------------------------------------------------
    if n_rows > 50_000 and subset is None:
        raise ValueError(
            f"find_fuzzy_duplicates: frame has {n_rows:,} rows. "
            "Pairwise comparison is O(n²) and may be slow for large frames. "
            "Pass subset= to limit the comparison columns, or filter the "
            "frame to a smaller working set first."
        )

    # --- pre-process rows into normalised string tuples --------------------
    def _normalise(val: object) -> str:
        s = "" if val is None or (isinstance(val, float) and val != val) else str(val)
        if ignore_case:
            s = s.lower()
        if normalize_whitespace:
            s = re.sub(r"\s+", " ", s).strip()
        return s

    rows: list[tuple] = []
    for i in range(n_rows):
        row_vals = []
        for col in compare_cols:
            raw = df[col].iloc[i]
            # Numeric / bool columns (including nullable extension types):
            # keep as-is for exact equality comparison
            import pandas as _pd

            if _pd.api.types.is_numeric_dtype(df[col]) or _pd.api.types.is_bool_dtype(
                df[col]
            ):
                row_vals.append(raw)
            else:
                row_vals.append(_normalise(raw))
        rows.append(tuple(row_vals))

    # --- pairwise similarity + Union-Find ----------------------------------
    parent = list(range(n_rows))

    def _find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def _union(x: int, y: int) -> None:
        parent[_find(x)] = _find(y)

    def _row_similarity(a: tuple, b: tuple) -> float:
        scores: list[float] = []
        for va, vb in zip(a, b):
            if isinstance(va, str) and isinstance(vb, str):
                scores.append(difflib.SequenceMatcher(None, va, vb).ratio())
            else:
                # Handle pd.NA and other missing sentinels before equality
                # to avoid "boolean value of NA is ambiguous" TypeError.
                import pandas as _pd

                va_null = (
                    va is None or va is _pd.NA or (isinstance(va, float) and va != va)
                )
                vb_null = (
                    vb is None or vb is _pd.NA or (isinstance(vb, float) and vb != vb)
                )
                if va_null and vb_null:
                    scores.append(1.0)  # both missing → exact match
                elif va_null or vb_null:
                    scores.append(0.0)  # one missing → mismatch
                else:
                    scores.append(1.0 if va == vb else 0.0)
        return sum(scores) / len(scores) if scores else 0.0

    for i in range(n_rows):
        for j in range(i + 1, n_rows):
            if _row_similarity(rows[i], rows[j]) >= threshold:
                _union(i, j)

    # --- collect groups with 2+ members ------------------------------------
    from collections import defaultdict

    groups: dict[int, list[int]] = defaultdict(list)
    for i in range(n_rows):
        groups[_find(i)].append(i)

    return [sorted(g) for g in groups.values() if len(g) >= 2]
