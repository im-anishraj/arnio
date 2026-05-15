"""
arnio.frame
ArFrame — the core data container wrapping the C++ Frame.
"""

from __future__ import annotations

import numpy as np

from ._core import _DType, _Frame


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

        Raises
        ------
        TypeError
            If any column has a non-numeric, non-bool dtype (e.g. string).
        ValueError
            If any column contains null values and ``fill_value`` is not
            provided.

        Examples
        --------
        >>> frame = ar.read_csv("data.csv")
        >>> arr = frame.to_numpy()
        >>> arr = frame.to_numpy(fill_value=0)
        """

        SUPPORTED_DTYPES = {_DType.INT64, _DType.FLOAT64, _DType.BOOL}

        n_rows, n_cols = self.shape

        # Zero-column frame
        if n_cols == 0:
            return np.empty((n_rows, 0))

        # Validate dtypes and collect columns
        columns = []
        for i in range(n_cols):
            col = self._frame.column_by_index(i)
            dtype = col.dtype()

            if dtype not in SUPPORTED_DTYPES:
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

            # Extract with correct dtype — no forced float conversion
            if dtype == _DType.INT64:
                arr = col.to_numpy_int().copy()
                if has_nulls:
                    arr[mask] = fill_value
            elif dtype == _DType.FLOAT64:
                arr = col.to_numpy_float().copy()
                if has_nulls:
                    arr[mask] = fill_value
            else:  # BOOL
                arr = col.to_numpy_bool().copy()
                if has_nulls:
                    arr[mask] = fill_value

            columns.append(arr)

        # Zero-row frame — return correct shape (0, n_cols)
        if n_rows == 0:
            return np.empty((0, n_cols))

        return np.column_stack(columns)

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
