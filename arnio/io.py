"""
arnio.io
CSV reading functions.
"""

from __future__ import annotations

from typing import Optional

from ._core import _CsvConfig, _CsvReader
from .frame import ArFrame


def read_csv(
    path: str,
    *,
    delimiter: str = ",",
    has_header: bool = True,
    usecols: Optional[list[str]] = None,
    nrows: Optional[int] = None,
    encoding: str = "utf-8",
) -> ArFrame:
    """Read a CSV file into an ArFrame via C++ backend.

    Parameters
    ----------
    path : str
        Path to the CSV file. Supports .csv, .txt, and .tsv extensions.
    delimiter : str, default ","
        Field delimiter character.
    has_header : bool, default True
        Whether the file has a header row.
    usecols : list[str], optional
        Columns to read. If None, reads all columns.
    nrows : int, optional
        Number of rows to read. If None, reads all rows.
    encoding : str, default "utf-8"
        File encoding.

    Returns
    -------
    ArFrame
        Data frame containing the CSV data.

    Raises
    ------
    ValueError
        If file format is unsupported or file appears binary.

    Examples
    --------
    >>> frame = ar.read_csv("data.csv", delimiter=",", has_header=True)
    """
    path_str = str(path).lower()
    if not (
        path_str.endswith(".csv")
        or path_str.endswith(".txt")
        or path_str.endswith(".tsv")
    ):
        raise ValueError(
            f"Unsupported file format: {path}. Only .csv, .txt, and .tsv are supported."
        )

    try:
        with open(path, "rb") as f:
            if b"\0" in f.read(1024):
                raise ValueError(
                    f"File appears to be binary: {path}. Only text-based CSV files are supported."
                )
    except FileNotFoundError:
        pass  # Let C++ backend handle or raise standard error

    config = _CsvConfig()
    config.delimiter = delimiter
    config.has_header = has_header
    config.encoding = encoding

    if usecols is not None:
        config.usecols = usecols
    if nrows is not None:
        config.nrows = nrows

    reader = _CsvReader(config)
    cpp_frame = reader.read(path)
    return ArFrame(cpp_frame)


def scan_csv(
    path: str,
    *,
    delimiter: str = ",",
) -> dict[str, str]:
    """Return schema (column names + inferred types) without loading data.

    Parameters
    ----------
    path : str
        Path to the CSV file. Supports .csv, .txt, and .tsv extensions.
    delimiter : str, default ","
        Field delimiter character.

    Returns
    -------
    dict[str, str]
        Dictionary mapping column names to inferred type strings.

    Raises
    ------
    ValueError
        If file format is unsupported or file appears binary.

    Examples
    --------
    >>> schema = ar.scan_csv("data.csv")
    >>> print(schema)
    {'name': 'string', 'age': 'int64'}
    """
    path_str = str(path).lower()
    if not (
        path_str.endswith(".csv")
        or path_str.endswith(".txt")
        or path_str.endswith(".tsv")
    ):
        raise ValueError(
            f"Unsupported file format: {path}. Only .csv, .txt, and .tsv are supported."
        )

    try:
        with open(path, "rb") as f:
            if b"\0" in f.read(1024):
                raise ValueError(
                    f"File appears to be binary: {path}. Only text-based CSV files are supported."
                )
    except FileNotFoundError:
        pass

    config = _CsvConfig()
    config.delimiter = delimiter
    reader = _CsvReader(config)
    return reader.scan_schema(path)
