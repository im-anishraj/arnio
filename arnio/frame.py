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

    def _repr_html_(self) -> str:
        """Notebook-friendly HTML representation."""
        import html

        rows, cols = self.shape

        preview_columns = self.columns[:5]

        columns_html = "".join(
          f"<li><b>{html.escape(col)}</b>: "
          f"{html.escape(str(self.dtypes.get(col, 'unknown')))}</li>"
          for col in preview_columns
          )

        extra = ""
        if len(self.columns) > 5:
           extra = f"<p>... and {len(self.columns) - 5} more columns</p>"

        return f"""
    <div style="padding:10px;border:1px solid #ccc;border-radius:6px;">
        <h3>ArFrame Preview</h3>
        <p><b>Shape:</b> {rows} rows × {cols} columns</p>
        <ul>
            {columns_html}
        </ul>
        {extra}
    </div>
    """
    def __str__(self) -> str:
        """Return a detailed string summary of the ArFrame."""
        lines = [f"ArFrame: {self.shape[0]} rows × {self.shape[1]} columns"]
        lines.append(f"Columns: {self.columns}")
        lines.append(f"DTypes:  {self.dtypes}")
        lines.append(f"Memory:  {self.memory_usage()} bytes")
        return "\n".join(lines)
