"""
arnio.io
CSV reading functions.
"""

from __future__ import annotations

import csv
import os
import shutil
import tempfile
from collections.abc import Iterator, Sequence
from contextlib import contextmanager

from ._core import _CsvConfig, _CsvReader
from .exceptions import CsvReadError
from .frame import ArFrame


def _is_utf8_encoding(encoding: str) -> bool:
    """Return whether the encoding should be treated as raw UTF-8 input."""
    return encoding.lower().replace("_", "-") in {"utf-8", "utf8"}


@contextmanager
def _utf8_csv_path(
    path: str,
    encoding: str,
    delimiter: str = ",",
    sample_rows: int | None = None,
) -> Iterator[str]:
    """Return a UTF-8 file path for the C++ reader.

    The native reader currently consumes UTF-8 bytes. For other encodings,
    transcode through a temporary UTF-8 file so the public encoding parameter is
    honored without leaking platform-specific decoding behavior through pybind.
    """
    if _is_utf8_encoding(encoding):
        yield path
        return

    tmp_name: str | None = None
    try:
        with open(path, encoding=encoding, newline="") as src:
            with tempfile.NamedTemporaryFile(
                "w", encoding="utf-8", newline="", suffix=".csv", delete=False
            ) as tmp:
                if sample_rows is not None:
                    # Use csv.reader so we advance through complete CSV records
                    # rather than raw physical lines. This prevents a quoted
                    # multiline field from being split at the sampling boundary,
                    # which would produce an invalid partial CSV for scan_schema.
                    reader = csv.reader(src, delimiter=delimiter)
                    writer = csv.writer(tmp, delimiter=delimiter)
                    for row_count, row in enumerate(reader):
                        writer.writerow(row)
                        if row_count >= sample_rows:
                            break
                else:
                    shutil.copyfileobj(src, tmp)
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


def _validate_thousands_separator(
    thousands_separator: str | None,
) -> None:
    if thousands_separator is None:
        return
    if not isinstance(thousands_separator, str):
        raise TypeError("thousands_separator must be a string or None")
    if len(thousands_separator) != 1:
        raise ValueError("thousands_separator must be a single character")
    if thousands_separator.isalnum() or thousands_separator in {'"', "\n", "\r"}:
        raise ValueError(
            "thousands_separator must be a single non-alphanumeric character"
        )


def _validate_delimiter(delimiter: str) -> str:
    """Validate CSV delimiter."""
    if not isinstance(delimiter, str):
        raise TypeError("delimiter must be a string")

    if len(delimiter) != 1:
        raise ValueError("delimiter must be exactly one character")

    return delimiter


def _validate_usecols(usecols: Sequence[str]) -> list[str]:
    """Validate usecols parameter."""
    if isinstance(usecols, str):
        raise TypeError("usecols must be a sequence of column names, not a string")

    if not isinstance(usecols, Sequence):
        raise TypeError("usecols must be a sequence of strings")

    for col in usecols:
        if not isinstance(col, str):
            raise TypeError("usecols must contain only strings")

    if len(set(usecols)) != len(usecols):
        raise ValueError("usecols must not contain duplicate column names")

    return list(usecols)


def _validate_nrows(nrows: int) -> int:
    """Validate nrows parameter."""
    if isinstance(nrows, bool) or not isinstance(nrows, int):
        raise TypeError("nrows must be an integer")

    if nrows < 0:
        raise ValueError("nrows must be non-negative")

    return nrows


def read_csv(
    path: str | os.PathLike[str],
    *,
    delimiter: str = ",",
    has_header: bool = True,
    usecols: list[str] | None = None,
    nrows: int | None = None,
    encoding: str = "utf-8",
    trim_headers: bool = True,
    thousands_separator: str | None = None,
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
    trim_headers : bool, default True
        Strip leading/trailing whitespace from column names.
    thousands_separator : str, optional
        Single non-alphanumeric character used as a thousands separator
        during numeric parsing.

        Values containing delimiter characters must still be quoted
        properly in the CSV input. For example, when using a comma
        delimiter, the value "1,234" must be quoted, while unquoted
        1,234 is interpreted as two separate fields.

    Returns
    -------
    ArFrame
        Data frame containing the CSV data.

    Raises
    ------
    ValueError
        If file format is unsupported or if thousands_separator is invalid.

    TypeError
        If thousands_separator is not a string or None.

    CsvReadError
        If CSV input contains NUL bytes and appears binary or corrupted.

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

    if _is_utf8_encoding(encoding):
        try:
            with open(path, "rb") as f:
                if b"\0" in f.read(1024):
                    raise CsvReadError(
                        "CSV input contains NUL bytes and appears to be binary or corrupted"
                    )
        except FileNotFoundError:
            pass  # Let C++ backend handle or raise standard error

    try:
        if os.path.getsize(path) == 0:
            raise CsvReadError(f"CSV file is empty: {path!r}")
    except FileNotFoundError:
        pass  # Let C++ backend handle or raise standard error

    _validate_thousands_separator(thousands_separator)
    delimiter = _validate_delimiter(delimiter)

    config = _CsvConfig()
    config.delimiter = delimiter
    config.has_header = has_header
    config.encoding = encoding
    config.trim_headers = trim_headers
    config.thousands_separator = thousands_separator

    if usecols is not None:
        config.usecols = _validate_usecols(usecols)

    if nrows is not None:
        config.nrows = _validate_nrows(nrows)

    reader = _CsvReader(config)
    try:
        with _utf8_csv_path(path, encoding, delimiter=delimiter) as native_path:
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
    trim_headers: bool = True,
    thousands_separator: str | None = None,
) -> dict[str, str]:
    """Return schema (column names + inferred types) without loading data.

    Parameters
    ----------
    path : str
        Path to the CSV file. Supports .csv, .txt, and .tsv extensions.
    delimiter : str, default ","
        Field delimiter character.
    encoding : str, default "utf-8"
        File encoding. For non-UTF-8 inputs, a sample of the file is
        transcoded to infer the schema.
    trim_headers : bool, default True
        Strip leading/trailing whitespace from column names.
    thousands_separator : str, optional
        Single non-alphanumeric character used as a thousands separator
        during numeric parsing.

        Values containing delimiter characters must still be quoted
        properly in the CSV input. For example, when using a comma
        delimiter, the value "1,234" must be quoted, while unquoted
        1,234 is interpreted as two separate fields.

    Returns
    -------
    dict[str, str]
        Dictionary mapping column names to inferred type strings.

    Raises
    ------
    ValueError
        If file format is unsupported or if thousands_separator is invalid.

    TypeError
        If thousands_separator is not a string or None.

    CsvReadError
        If CSV input contains NUL bytes and appears binary or corrupted.

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

    if _is_utf8_encoding(encoding):
        try:
            with open(path, "rb") as f:
                if b"\0" in f.read(1024):
                    raise CsvReadError(
                        "CSV input contains NUL bytes and appears to be binary or corrupted"
                    )
        except FileNotFoundError:
            pass  # Let C++ backend handle or raise standard error

    try:
        if os.path.getsize(path) == 0:
            raise CsvReadError(f"CSV file is empty: {path!r}")
    except FileNotFoundError:
        pass

    _validate_thousands_separator(thousands_separator)
    delimiter = _validate_delimiter(delimiter)

    config = _CsvConfig()
    config.delimiter = delimiter
    config.encoding = encoding
    config.trim_headers = trim_headers
    config.thousands_separator = thousands_separator

    reader = _CsvReader(config)
    try:
        # Schema inference only needs a sample, avoiding full-file transcode.
        # sample_rows is passed so _utf8_csv_path uses record-aware sampling
        # via csv.reader, which correctly handles quoted multiline fields that
        # straddle the boundary.
        with _utf8_csv_path(
            path,
            encoding,
            delimiter=delimiter,
            sample_rows=10000,
        ) as native_path:
            return reader.scan_schema(native_path)
    except RuntimeError as e:
        raise CsvReadError(str(e)) from e
