"""
arnio.frame
ArFrame — the core data container wrapping the C++ Frame.
"""

from __future__ import annotations

from ._core import _Frame


class ArFrame:
    """Lightweight columnar data container backed by C++."""

    __slots__ = ("_frame",)

    def __init__(self, cpp_frame: _Frame) -> None:
        self._frame = cpp_frame

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
            If False (default), counts only the fixed struct overhead for
            each column (e.g. ``sizeof(std::string) * capacity`` for string
            columns). This is a fast, O(1) lower-bound estimate.

            .. note::
               **Behavior Change:** Previously, the default memory calculation
               iterated through all strings to sum their capacities. To align
               with pandas and provide fast O(1) estimates, `deep=False` now
               strictly excludes string character heap storage.

            If True, also iterates every string element and adds its actual
            character byte count (``s.size()``), giving a precise total
            that includes heap-allocated string data.

            For numeric columns (int64, float64, bool) the result is the
            same regardless of *deep*, because those types store all data
            inline.

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
