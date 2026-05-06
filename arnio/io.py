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
    """Read a CSV file into an ArFrame via C++ backend."""
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
    """Return schema (column names + inferred types) without loading data."""
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
