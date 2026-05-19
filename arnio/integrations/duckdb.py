"""
arnio.integrations.duckdb
DuckDB integration helpers for ArFrame.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import duckdb

from ..convert import to_pandas
from ..frame import ArFrame


def register_duckdb(
    frame: ArFrame,
    conn: duckdb.DuckDBPyConnection,
    name: str,
) -> None:
    """Register an ArFrame as a DuckDB relation.

    Parameters
    ----------
    frame : ArFrame
        The frame to register.
    conn : duckdb.DuckDBPyConnection
        An open DuckDB connection.
    name : str
        The relation name to use in SQL queries.

    Raises
    ------
    TypeError
        If frame is not an ArFrame or name is not a string.
    ValueError
        If name is empty.

    Examples
    --------
    >>> import duckdb
    >>> import arnio as ar
    >>> frame = ar.read_csv("data.csv")
    >>> conn = duckdb.connect()
    >>> ar.register_duckdb(frame, conn, "my_table")
    >>> conn.execute("SELECT * FROM my_table").fetchdf()
    """
    if not isinstance(frame, ArFrame):
        raise TypeError("frame must be an ArFrame")
    if not isinstance(name, str):
        raise TypeError("name must be a string")
    if not name:
        raise ValueError("name must not be empty")

    df = to_pandas(frame)
    conn.register(name, df)
