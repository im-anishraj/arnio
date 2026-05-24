"""
arnio.frame
ArFrame — the core data container wrapping the C++ Frame.
"""

from __future__ import annotations

import json

import numpy as np

from ._core import _DType, _Frame

#: Dtype strings recognised by ArFrame.select_dtypes().
_VALID_DTYPES: frozenset[str] = frozenset(
    {"int64", "float64", "string", "bool", "null"}
)


class StatsDict(dict):
    def __repr__(self) -> str:
        return json.dumps(self, indent=2)

    def _repr_markdown_(self) -> str:
        return f"```json\n{json.dumps(self, indent=2)}\n```"


class ColumnSummary:
    """Schema summary for a single column.

    Attributes
    ----------
    name : str
        Column name.
    dtype : str
        Inferred dtype string (e.g. ``"int64"``, ``"string"``).
    nullable : bool
        True if the column contains at least one null value, False otherwise.
    """

    __slots__ = ("name", "dtype", "nullable")

    def __init__(self, name: str, dtype: str, nullable: bool) -> None:
        self.name = name
        self.dtype = dtype
        self.nullable = nullable

    def __repr__(self) -> str:
        return (
            f"ColumnSummary(name={self.name!r}, dtype={self.dtype!r},"
            f" nullable={self.nullable})"
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ColumnSummary):
            return NotImplemented
        return (
            self.name == other.name
            and self.dtype == other.dtype
            and self.nullable == other.nullable
        )


class ArFrame:
    """Lightweight columnar data container backed by C++."""

    __slots__ = ("_frame", "_attrs")

    def __init__(self, cpp_frame: _Frame, attrs: dict | None = None) -> None:
        self._frame = cpp_frame
        self._attrs: dict = attrs if attrs is not None else {}

    @classmethod
    def from_records(
        cls,
        records: list,
        columns: list[str] | None = None,
    ) -> ArFrame:
        """Build an ArFrame from a list of records.

        Parameters
        ----------
        records : list
            A non-empty list of dicts, lists, or tuples.
        columns : list[str] or None
            Column names. Required when records are lists or tuples.
            Optional for dicts — inferred from keys if not given.
        Returns
        -------
        ArFrame

        Raises
        ------
        TypeError
            If records is not a list, elements are mixed types, or a
            cell value is a list or dict.
        ValueError
            If records is empty, columns is missing for sequence records,
            or a row's length doesn't match columns.
        """
        import pandas as pd

        from .convert import from_pandas

        if not isinstance(records, list):
            raise TypeError(f"records must be a list, got {type(records).__name__!r}")

        if len(records) == 0:
            raise ValueError("records must be non-empty")

        first = records[0]

        if isinstance(first, dict):
            for i, row in enumerate(records):
                if not isinstance(row, dict):
                    raise TypeError(
                        f"all records must be dicts, but row {i} is {type(row).__name__!r}"
                    )
                for col, val in row.items():
                    if isinstance(val, (list, dict)):
                        raise TypeError(
                            f"nested values are not supported; "
                            f"column {col!r} at row {i} contains a {type(val).__name__!r}"
                        )
            df = pd.DataFrame.from_records(records, columns=columns)

        elif isinstance(first, (list, tuple)):
            if columns is None:
                raise ValueError(
                    "columns must be provided when records are lists or tuples"
                )
            for i, row in enumerate(records):
                if not isinstance(row, (list, tuple)):
                    raise TypeError(
                        f"all records must be the same type, but row {i} is {type(row).__name__!r}"
                    )
                if len(row) != len(columns):
                    raise ValueError(
                        f"row {i} has {len(row)} value(s) but {len(columns)} column(s) were provided"
                    )
                for j, val in enumerate(row):
                    if isinstance(val, (list, dict)):
                        raise TypeError(
                            f"nested values are not supported; "
                            f"column {columns[j]!r} at row {i} contains a {type(val).__name__!r}"
                        )
            df = pd.DataFrame.from_records(records, columns=columns)

        else:
            raise TypeError(
                f"records must contain dicts, lists, or tuples, got {type(first).__name__!r}"
            )

        return from_pandas(df)

    def astype(self, dtype):
        """Cast ArFrame columns to a specified type.

        Parameters
        ----------
        dtype : Any
            The data type to cast to (e.g., str, int, float, or a dict of column names to types).

        Returns
        -------
        ArFrame
            A new ArFrame with the applied type changes.

        Raises
        ------
        TypeError
            If the input dtype is invalid or if conversion fails due to type mismatch.
        ValueError
            If invalid values are passed or column conversion fails.
        """
        from .convert import from_pandas, to_pandas

        if dtype is None:
            raise TypeError("dtype cannot be None")

        try:
            df = to_pandas(self)
        except Exception as e:
            raise RuntimeError(f"Failed to convert ArFrame to pandas for casting: {e}")

        try:
            df_casted = df.astype(dtype)
        except TypeError as te:
            raise TypeError(f"Invalid type conversion requested: {te}")
        except ValueError as ve:
            raise ValueError(f"Value conversion error during astype: {ve}")
        except Exception as e:
            raise ValueError(f"An error occurred during casting: {e}")

        return from_pandas(df_casted)

    # --- Properties ---

    @property
    def shape(self) -> tuple[int, int]:
        """Row and column count.

        Returns
        -------
        tuple[int, int]
            (number_of_rows, number_of_columns)
        """
        return self._frame.shape()

    @property
    def columns(self) -> list[str]:
        """Column names.

        Returns
        -------
        list[str]
            List of column names in order.
        """
        return self._frame.column_names()

    @property
    def dtypes(self) -> dict[str, str]:
        """Column name → inferred type.

        Returns
        -------
        dict[str, str]
            Mapping of column names to their data types.
        """
        return self._frame.dtypes()

    @property
    def schema_summary(self) -> list[ColumnSummary]:
        """Column names, dtypes, and nullability in one place.

        Inspects the C++ frame directly — no pandas conversion triggered.

        Returns
        -------
        list[ColumnSummary]
            One :class:`ColumnSummary` per column, in original column order.
            Each entry has three attributes:

            * ``name`` – column name (``str``)
            * ``dtype`` – inferred dtype string, e.g. ``"int64"`` (``str``)
            * ``nullable`` – ``True`` if the column contains at least one null
              value, ``False`` otherwise (``bool``)

        Examples
        --------
        >>> frame = ar.read_csv("data.csv")
        >>> for col in frame.schema_summary:
        ...     print(col.name, col.dtype, col.nullable)
        id int64 False
        email string True
        score float64 True
        """
        col_dtypes = self.dtypes
        result: list[ColumnSummary] = []
        for i, name in enumerate(self.columns):
            mask = self._frame.column_by_index(i).get_null_mask()
            nullable = bool(mask.any())
            result.append(
                ColumnSummary(name=name, dtype=col_dtypes[name], nullable=nullable)
            )
        return result

    @property
    def is_empty(self) -> bool:
        """Check if frame has zero rows.

        Returns
        -------
        bool
            True if frame contains no rows, False otherwise.

        Examples
        --------
        >>> frame = ar.read_csv("data.csv")
        >>> if frame.is_empty:
        ...     print("No data to process")
        False
        """
        return len(self) == 0

    # --- Methods ---

    def memory_usage(self) -> int:
        """Total bytes consumed in memory.

        Returns
        -------
        int
            Memory usage in bytes.
        """
        return self._frame.memory_usage()

    def head(self, n: int = 5) -> ArFrame:
        """Return the first n rows as an ArFrame.

        Parameters
        ----------
        n : int, optional
            Number of rows to return. Defaults to 5.

        Returns
        -------
        ArFrame
            New ArFrame containing the first n rows.
        """
        if isinstance(n, bool) or not isinstance(n, int) or n < 0:
            raise ValueError(f"`n` must be a non-negative integer, got {n!r}")

        from .convert import from_pandas, to_pandas

        df = to_pandas(self)

        return from_pandas(df.head(n))

    def tail(self, n: int = 5) -> ArFrame:
        """Return the last n rows as an ArFrame.

        Parameters
        ----------
        n : int, optional
            Number of rows to return. Defaults to 5.

        Returns
        -------
        ArFrame
            New ArFrame containing the last n rows.
        """
        if isinstance(n, bool) or not isinstance(n, int) or n < 0:
            raise ValueError(f"`n` must be a non-negative integer, got {n!r}")

        from .convert import from_pandas, to_pandas

        df = to_pandas(self)

        return from_pandas(df.tail(n))

    def to_dict(self) -> dict[str, list]:
        """Export the frame as a Python dictionary.

        Returns
        -------
        dict[str, list]
            A dictionary mapping column names to lists of values.

        Examples
        --------
        >>> frame = ar.read_csv("data.csv")
        >>> frame.to_dict()
        {'name': ['Alice', 'Bob'], 'age': [25, 30]}
        """
        col_names = self.columns
        num_cols = self.shape[1]
        return {
            col_names[i]: [
                self._frame.column_by_index(i).at(r) for r in range(len(self))
            ]
            for i in range(num_cols)
        }

    def select_columns(self, columns: list[str]) -> ArFrame:
        """Return a new ArFrame with only the selected columns.

        Parameters
        ----------
        columns : list[str]
            List of column names to select.

        Returns
        -------
        ArFrame
            New ArFrame containing only the selected columns.

        Raises
        ------
        TypeError
            If columns is not a valid sequence of strings.
        ValueError
            If the selection is empty, contains duplicates,
            or includes unknown columns.
        """
        if isinstance(columns, str):
            raise TypeError("columns must be a sequence of column names, not a string.")

        if not isinstance(columns, (list, tuple)):
            raise TypeError("columns must be a list or tuple of column names.")

        if not columns:
            raise ValueError("Column selection cannot be empty.")

        if any(not isinstance(col, str) for col in columns):
            raise TypeError("All column names must be strings.")

        if len(columns) != len(set(columns)):
            raise ValueError("Duplicate column names are not allowed.")

        missing = [col for col in columns if col not in self.columns]

        if missing:
            raise ValueError(f"Unknown columns: {missing}")

        return ArFrame(self._frame.select_columns(columns))


    def to_numpy(self, fill_value: object = None) -> np.ndarray:
        """Convert a numeric/bool-only ArFrame to a 2D NumPy array.

        Provides a direct export path without routing through pandas,
        suitable for numeric workflows requiring fast array conversion.

        Parameters
        ----------
        fill_value : scalar, optional
            Value used to replace null entries. Must be compatible with
            the column dtype — use int/float for numeric columns, bool
            for bool columns. If ``None`` and any null values are present,
            ``ValueError`` is raised.

        Returns
        -------
        numpy.ndarray
            2D array of shape ``(n_rows, n_cols)`` in column order.
            dtype is preserved when all columns share the same type
            (e.g. all int64, all float64, or all bool). When columns
            have mixed types (e.g. int and float together), NumPy
            promotes to a common dtype (typically float64).
            A zero-row frame returns shape ``(0, n_cols)``.

    def drop_columns(self, cols: list[str]) -> ArFrame:
        """Return a new ArFrame with the specified columns removed.

        Parameters
        ----------
        cols : list[str]
            Column names to drop. Duplicates are silently ignored.
            An empty list returns a copy of the frame unchanged.

        Returns
        -------
        ArFrame
            New ArFrame without the dropped columns. Original column
            order is preserved.


        Raises
        ------
        TypeError

            If any column has a non-numeric, non-bool dtype (e.g. string).
        ValueError
            If any column contains null values and ``fill_value`` is not
            provided.

            If cols is not a list, or contains non-string elements.
        ValueError
            If any name in cols does not exist in the frame.


        Examples
        --------
        >>> frame = ar.read_csv("data.csv")

        >>> arr = frame.to_numpy()
        >>> arr = frame.to_numpy(fill_value=0)
        """
        SUPPORTED_DTYPES = {_DType.INT64, _DType.FLOAT64, _DType.BOOL}

        n_rows, n_cols = self.shape

        if n_cols == 0:
            return np.empty((n_rows, 0))

        columns = []
        for i in range(n_cols):
            col = self._frame.column_by_index(i)
            dtype = col.dtype()

            if dtype not in SUPPORTED_DTYPES:
                if n_rows == 0:
                    return np.empty((0, n_cols), dtype=object)
                raise TypeError(
                    f"to_numpy() requires all columns to be numeric or bool. "
                    f"Column '{col.name()}' has unsupported dtype '{dtype}'."
                )

            mask = col.get_null_mask()
            has_nulls = mask.any()

            if has_nulls and fill_value is None:
                raise ValueError(
                    f"Column '{col.name()}' contains null values. "
                    f"Provide fill_value=... to substitute nulls, "
                    f"e.g. frame.to_numpy(fill_value=0)."
                )

            if dtype == _DType.INT64:
                arr = col.to_numpy_int().copy()
                if has_nulls:
                    arr[mask] = fill_value
            elif dtype == _DType.FLOAT64:
                arr = col.to_numpy_float().copy()
                if has_nulls:
                    arr[mask] = fill_value
            else:
                arr = col.to_numpy_bool().copy()
                if has_nulls:
                    arr[mask] = fill_value

            columns.append(arr)

        if n_rows == 0:
            return np.empty((0, n_cols))

        return np.column_stack(columns)

        >>> smaller = frame.drop_columns(["col1", "col2"])
        """
        if not isinstance(cols, list):
            raise TypeError(
                f"cols must be a list of column names, got {type(cols).__name__!r}"
            )

        if any(not isinstance(col, str) for col in cols):
            raise TypeError("All column names in cols must be strings.")

        # Deduplicate while preserving order
        seen: set[str] = set()
        unique_cols: list[str] = []
        for col in cols:
            if col not in seen:
                seen.add(col)
                unique_cols.append(col)

        # Validate all names exist
        missing = [col for col in unique_cols if col not in self.columns]
        if missing:
            raise ValueError(
                f"Unknown column(s): {missing}. " f"Available columns: {self.columns}"
            )

        # Empty input — return unchanged copy
        if not unique_cols:
            return ArFrame(self._frame.select_columns(self.columns))

        # Preserve original order of remaining columns
        drop_set = set(unique_cols)
        remaining = [col for col in self.columns if col not in drop_set]

        # Dropping all columns — preserve row count
        if not remaining:
            import pandas as pd

            from .convert import from_pandas

            return from_pandas(pd.DataFrame(index=range(len(self))))

        return ArFrame(self._frame.select_columns(remaining))


    def select_dtypes(
        self,
        include: str | list[str] | tuple[str, ...] | None = None,
        exclude: str | list[str] | tuple[str, ...] | None = None,
    ) -> ArFrame:
        """Return a new ArFrame containing only columns whose dtype matches the filter.

        At least one of *include* or *exclude* must be provided.

        Parameters
        ----------
        include : str, list[str], or tuple[str, ...], optional
            One or more dtype strings to keep.
            Accepted values: ``"int64"``, ``"float64"``, ``"string"``,
            ``"bool"``, ``"null"``.
        exclude : str, list[str], or tuple[str, ...], optional
            One or more dtype strings to drop. Applied after *include*.

        Returns
        -------
        ArFrame
            New ArFrame containing only the matched columns, in original
            column order.

        Raises
        ------
        ValueError
            If neither *include* nor *exclude* is provided, if *include*
            and *exclude* overlap, if an unrecognised dtype string is
            passed, or if no columns match the filter.
        TypeError
            If *include* or *exclude* is not a string, list, or tuple of
            strings.

        Examples
        --------
        >>> frame = ar.read_csv("data.csv")
        >>> numeric = frame.select_dtypes(include=["int64", "float64"])
        >>> without_strings = frame.select_dtypes(exclude="string")
        """
        if include is None and exclude is None:
            raise ValueError(
                "select_dtypes() requires at least one of 'include' or 'exclude'."
            )

        def _parse(
            arg: str | list[str] | tuple[str, ...] | None,
            name: str,
        ) -> frozenset[str] | None:
            if arg is None:
                return None
            if isinstance(arg, str):
                values = [arg]
            elif isinstance(arg, (list, tuple)):
                values = list(arg)
                non_strings = [v for v in values if not isinstance(v, str)]
                if non_strings:
                    raise TypeError(
                        f"'{name}' must contain only strings, "
                        f"got {[type(v).__name__ for v in non_strings]}."
                    )
            else:
                raise TypeError(
                    f"'{name}' must be a string, list, or tuple of strings, "
                    f"got {type(arg).__name__!r}."
                )
            unknown = [v for v in values if v not in _VALID_DTYPES]
            if unknown:
                raise ValueError(
                    f"Unrecognised dtype(s) in '{name}': {unknown}. "
                    f"Valid dtypes are: {sorted(_VALID_DTYPES)}."
                )
            return frozenset(values)

        include_set = _parse(include, "include")
        exclude_set = _parse(exclude, "exclude")

        if include_set is not None and exclude_set is not None:
            overlap = include_set & exclude_set
            if overlap:
                raise ValueError(
                    f"'include' and 'exclude' overlap: {sorted(overlap)}. "
                    "A dtype cannot be both included and excluded."
                )

        col_dtypes = self.dtypes
        matched: list[str] = []
        for col in self.columns:
            dtype = col_dtypes[col]
            if include_set is not None and dtype not in include_set:
                continue
            if exclude_set is not None and dtype in exclude_set:
                continue
            matched.append(col)

        if not matched:
            raise ValueError(
                f"No columns match the dtype selection. Frame dtypes: {col_dtypes}."
            )

        return self.select_columns(matched)

    def describe(self) -> dict[str, dict[str, float]]:
        """Generate summary statistics for all numeric and string columns.

        Returns
        -------
        dict[str, dict[str, float]]
            A printable nested dictionary of metrics.
        """
        return StatsDict(self._frame.describe())

    def _truncate_column_names(self, max_length=20):
        return [
            col[:max_length] + "..." if len(col) > max_length else col
            for col in self.columns
        ]

    # --- Dunder methods ---

    def __len__(self) -> int:
        """Return the number of rows."""
        return self._frame.num_rows()

    def __repr__(self) -> str:
        """Return a string representation of the ArFrame."""
        rows, cols = self.shape
        return f"ArFrame({rows} rows × {cols} cols)"

    def __str__(self) -> str:
        """Return a detailed string summary of the ArFrame."""
        lines = [f"ArFrame: {self.shape[0]} rows × {self.shape[1]} columns"]
        lines.append(f"Columns: {self._truncate_column_names()}")
        lines.append(f"DTypes:  {self.dtypes}")
        lines.append(f"Memory:  {self.memory_usage()} bytes")
        return "\n".join(lines)

    def __contains__(self, item: object) -> bool:
        return isinstance(item, str) and item in self.columns

    def __getitem__(self, key: str | list[str]) -> list | ArFrame:
        """Return column data as a list, or a subset ArFrame for list keys.

        Parameters
        ----------
        key : str or list[str]
            A single column name returns the column values as a list.
            A list of column names returns a new multi-column ArFrame.

        Returns
        -------
        list
            Column values when key is a str.
        ArFrame
            Subset frame when key is a list of str.

        Raises
        ------
        TypeError
            If key is not a string or list of strings.
        KeyError
            If a requested column does not exist.

        Examples
        --------
        >>> frame["name"]
        ['Alice', 'Bob', 'Charlie']
        >>> frame[["name", "age"]]
        ArFrame(3 rows × 2 cols)
        """
        if isinstance(key, str):
            if key not in self.columns:
                raise KeyError(
                    f"Column {key!r} not found. Available columns: {self.columns}"
                )
            col_index = self.columns.index(key)
            return [
                self._frame.column_by_index(col_index).at(i) for i in range(len(self))
            ]
        elif isinstance(key, list):
            non_strings = [k for k in key if not isinstance(k, str)]
            if non_strings:
                raise TypeError(
                    f"column list must contain only strings, got {[type(k).__name__ for k in non_strings]}"
                )
            missing = [k for k in key if k not in self.columns]
            if missing:
                raise KeyError(
                    f"Column(s) {missing} not found. Available columns: {self.columns}"
                )
            return self.select_columns(key)
        raise TypeError(
            f"column key must be a str or list of str, got {type(key).__name__!r}"
        )

    def preview(self, n: int = 5) -> str:
        """Return a lightweight string preview of the first ``n`` rows.

        Reads only the first ``n`` rows directly from the C++ frame without
        triggering a full pandas conversion, making it safe to call on very
        large frames from the CLI or a notebook.

        Parameters
        ----------
        n : int, optional
            Number of rows to preview. Must be a positive integer.
            Defaults to 5.

        Returns
        -------
        str
            A formatted string table showing the first ``n`` rows.

        Raises
        ------
        ValueError
            If ``n`` is not a positive integer.

        Examples
        --------
        >>> frame = ar.read_csv("data.csv")
        >>> print(frame.preview())       # first 5 rows
        >>> print(frame.preview(n=10))   # first 10 rows
        """
        if isinstance(n, bool) or not isinstance(n, int) or n < 1:
            raise ValueError(f"`n` must be a positive integer, got {n!r}")

        num_rows, num_cols = self.shape

        if num_rows == 0:
            return "ArFrame preview: (empty frame)"

        actual_n = min(n, num_rows)

        # Pull only the first `actual_n` values per column — no full conversion
        col_names = self.columns
        col_data = [
            [self._frame.column_by_index(i).at(r) for r in range(actual_n)]
            for i in range(num_cols)
        ]

        # Calculate column widths for alignment
        col_widths = [
            max(
                len(col_names[i]),
                max((len(str(col_data[i][r])) for r in range(actual_n)), default=0),
            )
            for i in range(num_cols)
        ]

        # Build header and separator
        header = "  ".join(col_names[i].ljust(col_widths[i]) for i in range(num_cols))
        separator = "  ".join("-" * col_widths[i] for i in range(num_cols))

        # Build rows
        rows = [
            "  ".join(str(col_data[i][r]).ljust(col_widths[i]) for i in range(num_cols))
            for r in range(actual_n)
        ]

        label = f"ArFrame preview (showing {actual_n} of {num_rows} rows):"
        return "\n".join([label, header, separator] + rows)
