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
    
    def compare_schema(self, other: "ArFrame", strict: bool = False) -> bool:
        """Compare the schema (columns and data types) with another ArFrame.
        Parameters
        ----------
        other : ArFrame
            The other frame to compare against.
        strict : bool, default False
            If True, enforces identical column sequence/order.
            If False, verifies column existence regardless of sequence.

        Returns
        bool
            True if schemas match, False otherwise.
        """
        # 1. Invalid Input Check: Safely handle non-ArFrame inputs
        if not isinstance(other, ArFrame):
            raise TypeError("The 'other' object must be an instance of ArFrame.")

        # 2. Strict Mode: Exact matching of both column order and dtypes
        if strict:
            return (self.columns == other.columns) and (self.dtypes == other.dtypes)

        # 3. Non-Strict Mode (Step A): Check if the column sets match completely
        if set(self.columns) != set(other.columns):
            return False

        # 4. Non-Strict Mode (Step B): Map columns to verify their values share identical data types
        return all(self.dtypes[col] == other.dtypes[col] for col in self.columns)
    
    