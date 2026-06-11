"""Polars DataFrame import and export helpers for Arnio.

This module provides Arrow-bridge interop between ArFrame and Polars DataFrames.
No pandas intermediate is involved:

    to_polars()   — ArFrame → pa.Table (existing to_arrow()) → pl.DataFrame
    from_polars() — pl.DataFrame → pa.Table (.to_arrow()) → ArFrame
                    (via _from_arrow_table(), reading Arrow column buffers
                    directly without a pandas intermediate)

Both ``polars`` and ``pyarrow`` are required; install both with::

    pip install arnio[polars]

Polars is an optional dependency; both functions raise ImportError with a
clear install hint when it is not available.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import polars as pl

from arnio.frame import ArFrame

# Polars types that map cleanly through Arrow to Arnio's supported dtypes.
# Any other Polars type will be caught during Arrow conversion and surfaced
# as a clear TypeError before any data is moved.
_SUPPORTED_POLARS_TYPES = frozenset(
    [
        "Int8",
        "Int16",
        "Int32",
        "Int64",
        "UInt8",
        "UInt16",
        "UInt32",
        "UInt64",
        "Float32",
        "Float64",
        "Boolean",
        "Utf8",
        "String",  # alias for Utf8 in recent Polars versions
        "Null",
        "LargeUtf8",
    ]
)

# Human-friendly names for the unsupported types that Polars users are most
# likely to hit.  Kept as a set so the check is O(1).
_UNSUPPORTED_POLARS_TYPES = frozenset(
    [
        "Date",
        "Time",
        "Datetime",
        "Duration",
        "List",
        "Array",
        "Struct",
        "Categorical",
        "Enum",
        "Object",
        "Binary",
        "Unknown",
    ]
)


def _check_polars_dtypes(df: pl.DataFrame) -> None:
    """Raise TypeError for any column whose Polars dtype Arnio cannot handle.

    Parameters
    ----------
    df : pl.DataFrame
        The Polars DataFrame whose schema will be inspected.

    Raises
    ------
    TypeError
        When one or more columns carry a dtype that is not supported by the
        Arrow bridge (e.g. Date, Datetime, Duration, List, Struct).
    """
    bad: list[str] = []
    for col_name, dtype in zip(df.columns, df.dtypes):
        type_name = type(dtype).__name__
        if type_name in _UNSUPPORTED_POLARS_TYPES:
            bad.append(
                f"  '{col_name}': {type_name} — "
                + _unsupported_hint(type_name, col_name)
            )

    if bad:
        lines = "\n".join(bad)
        raise TypeError(
            "from_polars() does not support the following column dtype(s):\n"
            f"{lines}\n"
            "Convert those columns to a supported dtype before calling from_polars()."
        )


def _unsupported_hint(type_name: str, col_name: str) -> str:
    """Return a short fix hint for common unsupported Polars dtypes."""
    fixes = {
        "Date": f'df["{col_name}"].cast(pl.Utf8)  # or .dt.strftime("%Y-%m-%d")',
        "Datetime": f'df["{col_name}"].dt.strftime("%Y-%m-%dT%H:%M:%S")',
        "Duration": f'df["{col_name}"].dt.total_seconds().cast(pl.Float64)',
        "List": f'df["{col_name}"].cast(pl.Utf8)  # serialize to string first',
        "Array": f'df["{col_name}"].cast(pl.Utf8)  # serialize to string first',
        "Struct": f'df["{col_name}"].cast(pl.Utf8)  # serialize to string first',
        "Categorical": f'df["{col_name}"].cast(pl.Utf8)',
        "Enum": f'df["{col_name}"].cast(pl.Utf8)',
        "Binary": f'df["{col_name}"].cast(pl.Utf8)  # decode bytes first',
    }
    return fixes.get(
        type_name, "cast to a supported Polars dtype (Int64, Float64, Boolean, Utf8)"
    )


def from_polars(df: pl.DataFrame) -> ArFrame:
    """Convert a Polars DataFrame to an ArFrame.

    Uses the Arrow bridge: ``df.to_arrow()`` produces a ``pyarrow.Table``
    whose buffers are read column-by-column into ArFrame via Arnio's native
    Arrow column reader — no pandas intermediate is involved.

    Parameters
    ----------
    df : pl.DataFrame
        Input Polars DataFrame. All columns must have a dtype that maps
        through Arrow to one of Arnio's native types (int64, float64,
        bool, string, null). See the dtype table in the module docstring.

    Returns
    -------
    ArFrame
        Equivalent ArFrame with inferred types and null values preserved.

    Raises
    ------
    ImportError
        If ``polars`` is not installed.
    ImportError
        If ``pyarrow`` is not installed (required for the Arrow bridge).
    TypeError
        If *df* is not a ``pl.DataFrame``.
    TypeError
        If any column has an unsupported Polars dtype (Date, Datetime,
        Duration, List, Struct, Categorical, Binary, …).

    Examples
    --------
    >>> import polars as pl
    >>> import arnio as ar
    >>> pldf = pl.DataFrame({"name": ["Alice", "Bob"], "age": [25, 30]})
    >>> frame = ar.from_polars(pldf)
    >>> frame.shape
    (2, 2)
    """
    try:
        import polars as pl_mod
    except ImportError as exc:
        raise ImportError(
            "from_polars() requires polars. Install it with: pip install arnio[polars]"
        ) from exc

    if not isinstance(df, pl_mod.DataFrame):
        raise TypeError(
            f"from_polars() expects a polars.DataFrame, got {type(df).__name__}. "
            "Pass a pl.DataFrame."
        )

    # Validate dtypes before touching Arrow so the error is clear and early.
    _check_polars_dtypes(df)

    try:
        import pyarrow as pa  # noqa: F401 — imported for side-effect check
    except ImportError as exc:
        raise ImportError(
            "from_polars() requires pyarrow for the Arrow bridge. "
            "Install it with: pip install arnio[polars]"
        ) from exc

    # df.to_arrow() returns a pa.Table; route it through Arnio's Arrow import.
    arrow_table = df.to_arrow()

    # Import column-by-column directly from the Arrow table buffers into
    # ArFrame — no pandas intermediate frame is created.
    from arnio.convert import _from_arrow_table

    return _from_arrow_table(arrow_table)


def to_polars(frame: ArFrame) -> pl.DataFrame:
    """Convert an ArFrame to a Polars DataFrame.

    Uses the zero-copy Arrow bridge: ``ar.to_arrow(frame)`` produces a
    ``pyarrow.Table`` which is consumed by ``pl.from_arrow()`` without any
    additional serialization.

    Parameters
    ----------
    frame : ArFrame
        Input ArFrame to convert.

    Returns
    -------
    pl.DataFrame
        Equivalent Polars DataFrame.  Arnio's native dtypes map as follows:

        =========  ===========  =============
        Arnio      Arrow        Polars
        =========  ===========  =============
        int64      int64        Int64
        float64    float64      Float64
        bool       bool_        Boolean
        string     string/utf8  Utf8 / String
        null col   null         Null
        =========  ===========  =============

    Raises
    ------
    ImportError
        If ``polars`` or ``pyarrow`` is not installed.
        Install both with: ``pip install arnio[polars]``.
    TypeError
        If *frame* is not an ArFrame.

    Examples
    --------
    >>> import arnio as ar
    >>> frame = ar.read_csv("data.csv")
    >>> pldf = ar.to_polars(frame)
    >>> type(pldf)
    <class 'polars.dataframe.frame.DataFrame'>
    """
    if not isinstance(frame, ArFrame):
        raise TypeError(
            f"to_polars() expects an ArFrame, got {type(frame).__name__}. "
            "Use ar.from_pandas() or ar.read_csv() to create an ArFrame first."
        )

    try:
        import polars as pl_mod
    except ImportError as exc:
        raise ImportError(
            "to_polars() requires polars. Install it with: pip install arnio[polars]"
        ) from exc

    from arnio.convert import to_arrow

    arrow_table = to_arrow(frame)  # raises ImportError if pyarrow is missing

    return pl_mod.from_arrow(arrow_table)
