"""
arnio.frame
ArFrame — the core data container wrapping the C++ Frame.
"""

from __future__ import annotations

from ._core import _Frame


class ArFrame:
    """Lightweight columnar data container backed by C++."""

    __slots__ = ("_frame", "_attrs")

    def __init__(self, cpp_frame: _Frame, attrs: dict | None = None) -> None:
        self._frame = cpp_frame
        self._attrs: dict = attrs if attrs is not None else {}

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

    # --- Methods ---

    def memory_usage(self, deep: bool = False) -> int:
        """Total bytes consumed in memory.

        Parameters
        ----------
        deep : bool, optional
            If ``False`` (default), counts only the fixed struct overhead for
            each column — for string columns this is
            ``sizeof(std::string) * capacity``, which excludes the
            heap-allocated character buffers. This is a fast O(1)
            lower-bound estimate.

            .. note::
               **Intentional behavior change from pre-deep API:** The original
               ``memory_usage()`` iterated each string and added
               ``s.capacity()`` to the total. With ``deep=False`` that
               per-string iteration is skipped, so the default result will be
               smaller than the old API for string-heavy frames. This change
               was made deliberately to make the default path O(1).

            If ``True``, iterates every string element and adds its allocated
            buffer size (``s.capacity()``), which is the number of bytes the
            OS actually reserved for that string — always ≥ the character
            count. This gives a precise upper-bound of the heap footprint.

            For numeric columns (``int64``, ``float64``, ``bool``) the result
            is identical regardless of *deep* because those types store data
            inline with no extra heap allocation.

        Returns
        -------
        int
            Total memory usage in bytes.

        Examples
        --------
        >>> frame = ar.read_csv("data.csv")
        >>> frame.memory_usage()          # fast shallow estimate
        1024
        >>> frame.memory_usage(deep=True) # precise, includes string chars
        3072
        """
        return self._frame.memory_usage(deep)

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

        from .convert import from_pandas, to_pandas

        df = to_pandas(self)
        selected_df = df[columns]

        return from_pandas(selected_df)

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
        lines.append(f"Columns: {self.columns}")
        lines.append(f"DTypes:  {self.dtypes}")
        lines.append(f"Memory:  {self.memory_usage()} bytes")
        return "\n".join(lines)

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
