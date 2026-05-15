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

    def memory_usage(self) -> int:
        """Total bytes consumed in memory.

        Returns
        -------
        int
            Memory usage in bytes.
        """
        return self._frame.memory_usage()
    
    def drop_columns(self, cols: list[str]) -> "ArFrame":
        """Return a new ArFrame without the specified columns.
         Parameters
        ----------
        cols : list[str]
            Column names to drop. Pass an empty list to return a copy.

        Returns
        -------
        ArFrame
            A new frame with the specified columns removed.

        Raises
        ------
        KeyError
            If any column in cols does not exist in the frame."""
        if not cols:
            return ArFrame(self._frame.clone())

        current_cols = self.columns
        missing = [c for c in cols if c not in current_cols]
        if missing:
            raise KeyError(
                f"Column(s) not found: {missing}. "
                f"Available columns: {current_cols}"
            )

        keep = [c for c in current_cols if c not in cols]
        result = _Frame()
        for col in keep:
            result.add_column(self._frame.column_by_name(col))
        return ArFrame(result)
   

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
