"""
arnio.io
CSV reading functions.
"""

from __future__ import annotations

from typing import Optional

from ._core import _CsvConfig, _CsvReader
from .exceptions import CsvReadError
from .frame import ArFrame


def _normalize_encoding(encoding: str) -> str:
    """Normalize an encoding name for comparison."""
    return encoding.lower().replace("-", "").replace("_", "")


_SUPPORTED_ENCODINGS = frozenset({"utf8", "utf-8"})


def _validate_encoding(encoding: str) -> None:
    """Validate that the requested encoding is supported.

    Raises:
        CsvReadError: If the encoding is not UTF-8.
    """
    normalized = _normalize_encoding(encoding)
    if normalized not in _SUPPORTED_ENCODINGS:
        raise CsvReadError(
            f"Encoding '{encoding}' is not yet supported. "
            "Only UTF-8 is currently supported."
        )


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

    Args:
        path: Path to the CSV file.
        delimiter: Field delimiter (default: ",").
        has_header: Whether the file has a header row (default: True).
        usecols: Columns to load (default: all).
        nrows: Number of rows to read (default: all).
        encoding: File encoding (default: "utf-8"). Only UTF-8 is currently
            supported by the C++ backend.

    Raises:
        CsvReadError: If a non-UTF-8 encoding is specified.
        ValueError: If the file format is unsupported or the file appears binary.
    """
    _validate_encoding(encoding)

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
