"""
arnio.io
CSV reading and writing functions.
"""

from __future__ import annotations

import csv
import os
import shutil
import tempfile
from collections.abc import Iterator, Sequence
from contextlib import contextmanager

from ._core import _CsvConfig, _CsvReader, _CsvWriteConfig, _CsvWriter
from .exceptions import CsvReadError
from .frame import ArFrame

DEFAULT_DELIMITER_CANDIDATES = (",", ";", "\t", "|")


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
    if thousands_separator in {".", "+", "-"}:
        raise ValueError(
            "Invalid thousands_separator: '.', '+' and '-' are not allowed"
        )


def _validate_delimiter(delimiter: str) -> str:
    """Validate CSV delimiter."""
    if not isinstance(delimiter, str):
        raise TypeError("delimiter must be a string")

    if len(delimiter) != 1:
        raise ValueError("delimiter must be exactly one character")

    return delimiter


def _validate_delimiter_candidates(candidates: Sequence[str]) -> tuple[str, ...]:
    if isinstance(candidates, str):
        raise TypeError("candidates must be a sequence of delimiter strings")
    if not isinstance(candidates, Sequence):
        raise TypeError("candidates must be a sequence of delimiter strings")
    if not candidates:
        raise ValueError("candidates must contain at least one delimiter")

    validated = tuple(_validate_delimiter(candidate) for candidate in candidates)
    if len(set(validated)) != len(validated):
        raise ValueError("candidates must not contain duplicate delimiters")
    return validated


def _delimiter_score(sample: str, delimiter: str) -> tuple[int, int, int]:
    try:
        rows = [
            row
            for row in csv.reader(sample.splitlines(), delimiter=delimiter)
            if row and any(field.strip() for field in row)
        ]
    except csv.Error:
        return (0, 0, 0)

    widths = [len(row) for row in rows]
    delimited_widths = [width for width in widths if width > 1]
    if not delimited_widths:
        return (0, 0, 0)

    width_counts = {
        width: delimited_widths.count(width) for width in set(delimited_widths)
    }
    most_common_width = max(width_counts, key=width_counts.get)
    consistent_rows = width_counts[most_common_width]
    delimiter_occurrences = sum(line.count(delimiter) for line in sample.splitlines())
    return (consistent_rows, most_common_width, delimiter_occurrences)


def sniff_csv_delimiter(
    path: str | os.PathLike[str],
    *,
    candidates: Sequence[str] = DEFAULT_DELIMITER_CANDIDATES,
    encoding: str = "utf-8",
    sample_size: int = 65536,
) -> str:
    """Detect the delimiter used by a CSV-like text file.

    Parameters
    ----------
    path : str
        Path to the CSV-like file.
    candidates : sequence of str, default (",", ";", "\\t", "|")
        Single-character delimiters to evaluate.
    encoding : str, default "utf-8"
        Text encoding used to read the sample.
    sample_size : int, default 65536
        Maximum number of characters to sample from the file.

    Returns
    -------
    str
        Detected delimiter character.

    Raises
    ------
    ValueError
        If candidates are invalid, no delimiter is detected, or the best
        delimiter is ambiguous.

    TypeError
        If candidates or sample_size have invalid types.

    CsvReadError
        If the file is empty, binary/corrupted, missing, or cannot be decoded.

    Examples
    --------
    >>> delimiter = ar.sniff_csv_delimiter("data.csv")
    >>> frame = ar.read_csv("data.csv", delimiter=delimiter)
    """
    if isinstance(sample_size, bool) or not isinstance(sample_size, int):
        raise TypeError("sample_size must be an integer")
    if sample_size <= 0:
        raise ValueError("sample_size must be a positive integer greater than 0")

    path = os.fspath(path)
    validated_candidates = _validate_delimiter_candidates(candidates)

    try:
        with open(path, "rb") as f:
            raw = f.read(sample_size)
    except OSError as e:
        raise CsvReadError(str(e)) from e

    if not raw:
        raise CsvReadError(f"CSV file is empty: {path!r}")
    if b"\0" in raw:
        raise CsvReadError(
            "CSV input contains NUL bytes and appears to be binary or corrupted"
        )

    try:
        sample = raw.decode(encoding)
    except LookupError as e:
        raise ValueError(f"Unknown encoding: {encoding}") from e
    except UnicodeDecodeError as e:
        raise CsvReadError(
            f"Could not decode {path!r} using encoding {encoding!r}"
        ) from e

    scores = {
        delimiter: _delimiter_score(sample, delimiter)
        for delimiter in validated_candidates
    }
    usable_scores = {
        delimiter: score for delimiter, score in scores.items() if score[0] > 0
    }
    if not usable_scores:
        raise ValueError(
            f"Could not detect a delimiter from candidates {validated_candidates!r}"
        )

    best_score = max(usable_scores.values())
    best_delimiters = [
        delimiter for delimiter, score in usable_scores.items() if score == best_score
    ]
    if len(best_delimiters) > 1:
        formatted = ", ".join(repr(delimiter) for delimiter in best_delimiters)
        raise ValueError(f"Ambiguous delimiter candidates: {formatted}")

    return best_delimiters[0]


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


def write_csv(
    frame: ArFrame,
    path: str | os.PathLike[str],
    *,
    delimiter: str = ",",
    write_header: bool = True,
    line_terminator: str = "\n",
) -> None:
    """Write an ArFrame to a CSV file via C++ backend.

    Parameters
    ----------
    frame : ArFrame
        The data frame to write.
    path : str
        Destination file path. Supports .csv, .txt, and .tsv extensions.
    delimiter : str, default ","
        Field delimiter character.
    write_header : bool, default True
        Whether to write the column header row.
    line_terminator : str, default "\\n"
        Line terminator to use between rows.

    Raises
    ------
    ValueError
        If file format is unsupported.
    RuntimeError
        If the file cannot be opened or written.

    Examples
    --------
    >>> ar.write_csv(frame, "output.csv")
    >>> ar.write_csv(frame, "output.tsv", delimiter="\\t")
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

    if len(delimiter) != 1:
        raise ValueError(f"delimiter must be a single character, got {delimiter!r}")

    config = _CsvWriteConfig()
    config.delimiter = delimiter
    config.write_header = write_header
    config.line_terminator = line_terminator

    writer = _CsvWriter(config)
    try:
        writer.write(frame._frame, path)
    except RuntimeError as e:
        raise RuntimeError(str(e)) from e


def scan_csv(
    path: str | os.PathLike[str],
    *,
    delimiter: str = ",",
    encoding: str = "utf-8",
    trim_headers: bool = True,
    thousands_separator: str | None = None,
    sample_size: int | None = None,
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
    sample_size : int, optional
        Number of rows to read for type inference. If None, defaults to 100 rows.

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

    if sample_size is not None:
        if not isinstance(sample_size, int) or isinstance(sample_size, bool):
            raise TypeError("sample_size must be an integer.")
        if sample_size <= 0:
            raise ValueError("sample_size must be a positive integer greater than 0.")
        config.sample_size = sample_size

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
            sample_rows=100 if sample_size is None else sample_size,
        ) as native_path:
            return reader.scan_schema(native_path)
    except RuntimeError as e:
        raise CsvReadError(str(e)) from e
