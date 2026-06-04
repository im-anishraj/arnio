"""
arnio.frame
ArFrame — the core data container wrapping the C++ Frame.
"""

from __future__ import annotations

import copy
import json
import math

from ._core import _Frame

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
        if not isinstance(name, str):
            raise TypeError("name must be a str")
        if not isinstance(dtype, str):
            raise TypeError("dtype must be a str")
        if not isinstance(nullable, bool):
            raise TypeError("nullable must be a bool")
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
        # SAFETY: unwrap accidental tuple-wrapped frame
        if isinstance(cpp_frame, tuple):
            cpp_frame = cpp_frame[0]

        self._frame = cpp_frame
        self._attrs: dict = attrs if attrs is not None else {}

    @classmethod
    def from_dict(cls, data: dict) -> ArFrame:
        from .convert import from_dict as _from_dict

        return _from_dict(data)

    @classmethod
    def from_pandas(cls, df) -> ArFrame:
        """Build an ArFrame from a pandas DataFrame."""
        from .convert import from_pandas as _from_pandas

        return _from_pandas(df)

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

        if columns is not None:
            if isinstance(columns, (str, bytes)):
                raise TypeError(
                    "columns must be a list or tuple of strings, not a string or bytes"
                )

            if not isinstance(columns, (list, tuple)):
                raise TypeError("columns must be a list or tuple of strings")

            non_strings = [col for col in columns if not isinstance(col, str)]

            if non_strings:
                raise TypeError("columns must contain only strings")

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
            if columns is not None and len(columns) == 0:
                raise ValueError(
                    "columns must not be empty when records are dicts; "
                    "pass columns=None to infer column names from the record keys"
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
        import numpy as np
        import pandas as pd

        from .convert import from_pandas, to_pandas

        def _validate_dtype_value(value):
            if isinstance(value, (list, tuple, set, dict)):
                raise TypeError(
                    "dtype must be a string, Python type, "
                    "NumPy/pandas dtype, or mapping "
                    "of column names to dtypes"
                )

            if value in (object, "object"):
                raise TypeError(
                    "dtype must be a string, Python type, "
                    "NumPy/pandas dtype, or mapping "
                    "of column names to dtypes"
                )

            try:
                resolved = pd.api.types.pandas_dtype(value)

                if resolved == np.dtype("O"):
                    raise TypeError(
                        "dtype must be a string, Python type, "
                        "NumPy/pandas dtype, or mapping "
                        "of column names to dtypes"
                    )

            except (TypeError, ValueError):
                raise TypeError(
                    "dtype must be a string, Python type, "
                    "NumPy/pandas dtype, or mapping "
                    "of column names to dtypes"
                )

        if dtype is None:
            raise TypeError("dtype cannot be None")

        if isinstance(dtype, dict):
            missing = [col for col in dtype if col not in self.columns]

            if missing:
                raise ValueError(f"Unknown column(s) in dtype mapping: {missing}")

            for value in dtype.values():
                _validate_dtype_value(value)

        elif isinstance(dtype, (list, tuple, set)):
            raise TypeError(
                "dtype must be a string, Python type, "
                "NumPy/pandas dtype, or mapping "
                "of column names to dtypes"
            )

        else:
            _validate_dtype_value(dtype)

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

        actual_n = min(n, len(self))

        return ArFrame(
            self._frame.select_rows(0, actual_n), attrs=copy.deepcopy(self._attrs)
        )

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

        actual_n = min(n, len(self))
        start = max(0, len(self) - actual_n)

        return ArFrame(
            self._frame.select_rows(start, actual_n), attrs=copy.deepcopy(self._attrs)
        )

    def to_dict(
        self,
        orient: str = "list",
    ):
        """Export the frame as a Python dictionary.

        Parameters
        ----------
        orient : str, default "list"
            Output format. Supported values are
            "list", "records", and "split".

        Returns
        -------
        dict | list
            Frame data in the requested orientation.

        Examples
        --------
        >>> frame = ar.read_csv("data.csv")
        >>> frame.to_dict()
        {'name': ['Alice', 'Bob'], 'age': [25, 30]}
        """
        col_names = self.columns
        num_cols = self.shape[1]
        data = {
            col_names[i]: [
                self._frame.column_by_index(i).at(r) for r in range(len(self))
            ]
            for i in range(num_cols)
        }
        supported = {"list", "records", "split"}
        if orient not in supported:
            raise ValueError("orient must be one of: list, records, split")

        if orient == "list":
            return data

        if orient == "records":
            row_count = len(self)

            return [
                {column: data[column][row] for column in col_names}
                for row in range(row_count)
            ]

        if orient == "split":
            row_count = len(self)

            return {
                "columns": list(col_names),
                "data": [
                    [data[column][row] for column in col_names]
                    for row in range(row_count)
                ],
            }

    def to_csv(
        self,
        path,
        *,
        delimiter: str = ",",
        write_header: bool = True,
        **kwargs,
    ) -> None:
        """Write the ArFrame to a CSV file.

        This is a convenience wrapper around :func:`arnio.write_csv`.

        Parameters
        ----------
        path : str or file-like
            Destination file path.
        delimiter : str, default ","
            Field delimiter character.
        write_header : bool, default True
            Whether to write the column header row.
        **kwargs
            Additional arguments passed to :func:`arnio.write_csv` such as `line_terminator`.

        Examples
        --------
        >>> frame.to_csv("output.csv")
        """
        from .io import write_csv

        write_csv(
            self,
            path,
            delimiter=delimiter,
            write_header=write_header,
            **kwargs,
        )

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

        return ArFrame(
            self._frame.select_columns(columns), attrs=copy.deepcopy(self._attrs)
        )

    def drop_columns(self, cols: list[str] | tuple[str, ...]) -> ArFrame:
        """Return a new ArFrame with the specified columns removed.

        Parameters
        ----------
        cols : list[str] | tuple[str, ...]
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
            If cols is not a list, or contains non-string elements.
        ValueError
            If any name in cols does not exist in the frame.

        Examples
        --------
        >>> frame = ar.read_csv("data.csv")
        >>> smaller = frame.drop_columns(["col1", "col2"])
        >>> smaller = frame.drop_columns(("col1", "col2"))
        """
        if not isinstance(cols, (list, tuple)):
            raise TypeError(
                f"cols must be a list or tuple of column names, got {type(cols).__name__!r}"
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
            return ArFrame(
                self._frame.select_columns(self.columns),
                attrs=copy.deepcopy(self._attrs),
            )

        # Preserve original order of remaining columns
        drop_set = set(unique_cols)
        remaining = [col for col in self.columns if col not in drop_set]

        # Dropping all columns is not supported
        if not remaining:
            raise ValueError("drop_columns cannot remove all columns from the frame")

        return ArFrame(
            self._frame.select_columns(remaining), attrs=copy.deepcopy(self._attrs)
        )

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
            and *exclude* overlap, or if an unrecognised dtype string is
            passed.
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
        for col in self.columns:  # iterate columns to preserve original order
            dtype = col_dtypes[col]
            if include_set is not None and dtype not in include_set:
                continue
            if exclude_set is not None and dtype in exclude_set:
                continue
            matched.append(col)

        if not matched:
            return ArFrame(_Frame(len(self)), attrs=self._attrs.copy())

        return self.select_columns(matched)

    def describe(self) -> dict[str, dict[str, float]]:
        """Generate summary statistics for numeric, string, and boolean columns.

        Numeric columns include ``count``, ``nulls``, ``mean``, ``min``, and
        ``max``. String columns include ``count``, ``nulls``, and ``unique``.
        Boolean columns include ``count``, ``nulls``, ``true``, ``false``, and
        ``true_ratio``.

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

    @staticmethod
    def _values_equal(a, b):
        if a is None and b is None:
            return True
        if isinstance(a, float) and isinstance(b, float):
            if math.isnan(a) and math.isnan(b):
                return True
        return a == b

    # --- Dunder methods ---

    def __len__(self) -> int:
        """Return the number of rows."""
        return self._frame.num_rows()

    def __repr__(self) -> str:
        """Return a string representation of the ArFrame."""
        rows, cols = self.shape
        return f"ArFrame({rows} rows × {cols} cols)"

    def __str__(self) -> str:
        """Return a detailed string summary of the ArFrame with data preview."""
        rows, cols = self.shape
        header = f"ArFrame: {rows} rows × {cols} columns"
        truncated_names = self._truncate_column_names()

        if rows == 0:
            return f"{header}\nColumns: {truncated_names}\n(empty frame)"

        if cols == 0:
            dtypes_line = f"DTypes: {self.dtypes}"
            memory_line = f"Memory: {self.memory_usage()} bytes"
            return (
                f"{header}\nColumns: {truncated_names}\n{dtypes_line}\n"
                f"{memory_line}\n(no columns to display)"
            )

        actual_n = min(5, rows)
        col_data = [
            [self._frame.column_by_index(i).at(r) for r in range(actual_n)]
            for i in range(cols)
        ]

        col_widths = [
            max(
                len(truncated_names[i]),
                max((len(str(col_data[i][r])) for r in range(actual_n)), default=0),
            )
            for i in range(cols)
        ]

        col_header = "  ".join(
            truncated_names[i].ljust(col_widths[i]) for i in range(cols)
        )
        separator = "  ".join("-" * col_widths[i] for i in range(cols))
        data_rows = [
            "  ".join(str(col_data[i][r]).ljust(col_widths[i]) for i in range(cols))
            for r in range(actual_n)
        ]

        suffix = f"\n... ({rows - actual_n} more rows)" if rows > actual_n else ""
        columns_line = f"Columns: {truncated_names}"
        dtypes_line = f"DTypes: {self.dtypes}"
        memory_line = f"Memory: {self.memory_usage()} bytes"

        parts = [
            header,
            columns_line,
            dtypes_line,
            memory_line,
            col_header,
            separator,
        ] + data_rows

        return "\n".join(parts) + suffix

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

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ArFrame):
            return NotImplemented

        if (
            self.shape != other.shape
            or self.columns != other.columns
            or self.dtypes != other.dtypes
        ):
            return False

        for i in range(self._frame.num_cols()):
            left = self._frame.column_by_index(i).to_python_list()
            right = other._frame.column_by_index(i).to_python_list()

            for lval, rval in zip(left, right):
                if not self._values_equal(lval, rval):
                    return False

        return True

    def __copy__(self) -> ArFrame:
        return ArFrame(self._frame.clone(), attrs=self._attrs.copy())

    def __deepcopy__(self, memo: dict) -> ArFrame:
        if id(self) in memo:
            return memo[id(self)]
        copied = ArFrame(self._frame.clone(), attrs={})
        memo[id(self)] = copied
        copied._attrs = copy.deepcopy(self._attrs, memo)
        return copied

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
        if num_rows > 0 and num_cols == 0:
            return (
                f"ArFrame preview: {num_rows} rows x 0 columns "
                "(no columns to display)"
            )

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

    def _repr_html_(self) -> str:
        """Return a bounded HTML table for Jupyter/IPython display.

        Jupyter calls this automatically when an ArFrame is the last
        expression in a cell. Output is always bounded to 10 rows.

        Returns
        -------
        str
            HTML string with shape/dtype summary, up to 10 data rows,
            HTML-escaped content, and a truncation notice when needed.
        """
        import html as _html

        _REPR_HTML_MAX_ROWS = 10

        num_rows, num_cols = self.shape
        col_names = self.columns
        dtypes = self.dtypes

        # ── summary line ──────────────────────────────────────────────────
        dtype_parts = ", ".join(
            f"{_html.escape(c)}: {_html.escape(dtypes.get(c, '?'))}" for c in col_names
        )
        summary = (
            '<p style="font-family:monospace;font-size:0.85em;'
            'color:#555;margin:0 0 4px 0;">'
            f"ArFrame [{num_rows} rows \u00d7 {num_cols} cols]"
            + (f"&nbsp;&nbsp;|&nbsp;&nbsp;{dtype_parts}" if dtype_parts else "")
            + "</p>"
        )

        # ── empty-frame fast path ─────────────────────────────────────────
        if num_rows == 0:
            return summary + "<p><em>(empty)</em></p>"
        if num_cols == 0:
            return summary + "<p><em>(no columns to display)</em></p>"

        # ── column header ─────────────────────────────────────────────────
        th_style = (
            "style='padding:4px 10px;text-align:left;"
            "background:#f0f0f0;border:1px solid #ccc;"
            "font-family:monospace;font-size:0.9em;'"
        )
        header_cells = "".join(
            f"<th {th_style}>{_html.escape(c)}</th>" for c in col_names
        )
        header = f"<thead><tr>{header_cells}</tr></thead>"

        # Read only the rows needed for display; do not convert the full frame.
        preview_rows = min(num_rows, _REPR_HTML_MAX_ROWS)

        try:
            preview_values = [
                [
                    self._frame.column_by_index(col_idx).at(row_idx)
                    for col_idx in range(num_cols)
                ]
                for row_idx in range(preview_rows)
            ]
        except Exception as exc:
            return (
                summary
                + "<p><em>HTML preview unavailable: "
                + _html.escape(str(exc))
                + "</em></p>"
            )

        td_style = (
            "style='padding:4px 10px;border:1px solid #ddd;"
            "font-family:monospace;font-size:0.9em;white-space:nowrap;'"
        )
        rows_html = ""
        for row in preview_values:
            cells = "".join(
                f"<td {td_style}>"
                + _html.escape("" if value is None else str(value))
                + "</td>"
                for value in row
            )
            rows_html += f"<tr>{cells}</tr>"

        tbody = f"<tbody>{rows_html}</tbody>"
        table = (
            "<table style='border-collapse:collapse;'>" f"{header}{tbody}" "</table>"
        )

        # ── truncation notice ─────────────────────────────────────────────
        notice = ""
        if num_rows > _REPR_HTML_MAX_ROWS:
            notice = (
                '<p style="font-size:0.82em;color:#888;margin:4px 0 0 0;">'
                f"Showing {_REPR_HTML_MAX_ROWS} of {num_rows} rows"
                "</p>"
            )

        return summary + table + notice
