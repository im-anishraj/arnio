"""
arnio.io
CSV reading functions.
"""

from __future__ import annotations

import os
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager

from ._core import _CsvConfig, _CsvReader
from .exceptions import CsvReadError
from .frame import ArFrame


@contextmanager
def _utf8_csv_path(path: str, encoding: str) -> Iterator[str]:
    """Return a UTF-8 file path for the C++ reader.

    The native reader currently consumes UTF-8 bytes. For other encodings,
    transcode through a temporary UTF-8 file so the public encoding parameter is
    honored without leaking platform-specific decoding behavior through pybind.
    """
    if encoding.lower().replace("_", "-") in {"utf-8", "utf8"}:
        yield path
        return

    tmp_name: str | None = None
    try:
        with open(path, encoding=encoding, newline="") as src:
            with tempfile.NamedTemporaryFile(
                "w", encoding="utf-8", newline="", suffix=".csv", delete=False
            ) as tmp:
                tmp.write(src.read())
                tmp_name = tmp.name
        yield tmp_name
    except LookupError as e:
        raise ValueError(f"Unknown encoding: {encoding}") from e
    except UnicodeDecodeError as e:
        raise CsvReadError(
            f"Could not decode {path!r} using encoding {encoding!r}"
        ) from e
    except OSError as e:
        raise CsvReadError(str(e)) from e
    finally:
        if tmp_name is not None:
            try:
                os.unlink(tmp_name)
            except OSError:
                pass


def read_csv(
    path: str | os.PathLike[str],
    *,
    delimiter: str = ",",
    has_header: bool = True,
    usecols: list[str] | None = None,
    nrows: int | None = None,
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
    path = os.fspath(path)
    path_lower = path.lower()
    if not (
        path_lower.endswith(".csv")
        or path_lower.endswith(".txt")
        or path_lower.endswith(".tsv")
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
    try:
        with _utf8_csv_path(path, encoding) as native_path:
            cpp_frame = reader.read(native_path)
    except ValueError:
        raise
    except CsvReadError:
        raise
    except RuntimeError as e:
        raise CsvReadError(str(e)) from e
    return ArFrame(cpp_frame)


def scan_csv(
    path: str | os.PathLike[str],
    *,
    delimiter: str = ",",
    encoding: str = "utf-8",
) -> dict[str, str]:
    """Return schema (column names + inferred types) without loading data.

    Parameters
    ----------
    path : str
        Path to the CSV file. Supports .csv, .txt, and .tsv extensions.
    delimiter : str, default ","
        Field delimiter character.
    encoding : str, default "utf-8"
        File encoding. Non-UTF-8 inputs are transcoded before native scanning.

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
    path = os.fspath(path)
    path_lower = path.lower()
    if not (
        path_lower.endswith(".csv")
        or path_lower.endswith(".txt")
        or path_lower.endswith(".tsv")
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
    config.encoding = encoding
    reader = _CsvReader(config)
    try:
        with _utf8_csv_path(path, encoding) as native_path:
            return reader.scan_schema(native_path)
    except RuntimeError as e:
        raise CsvReadError(str(e)) from e
