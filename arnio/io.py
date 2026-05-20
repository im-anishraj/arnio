"""
arnio.io
CSV reading and writing functions.
"""

from __future__ import annotations

import io
import os
import shutil
import tempfile
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from typing import cast

from ._core import _CsvChunkReader, _CsvConfig, _CsvReader, _CsvWriteConfig, _CsvWriter
from .exceptions import CsvReadError, JsonlReadError
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
                    # Preserve the original decoded CSV text while sampling
                    # complete logical records so scan_schema does not see a
                    # rewritten file with normalized quoting or line endings.
                    row_count = 0
                    in_quotes = False
                    pending_quote = False
                    pending_cr = False
                    last_char_was_terminator = False
                    sample_complete = False

                    while chunk := src.read(8192):
                        chunk_len = len(chunk)
                        index = 0
                        while index < chunk_len:
                            char = chunk[index]

                            if sample_complete:
                                if pending_cr and char == "\n":
                                    tmp.write(char)
                                pending_cr = False
                                break

                            tmp.write(char)

                            if pending_cr:
                                pending_cr = False
                                if char == "\n":
                                    last_char_was_terminator = True
                                    index += 1
                                    continue

                            if char == '"':
                                if pending_quote:
                                    pending_quote = False
                                elif in_quotes:
                                    pending_quote = True
                                else:
                                    in_quotes = True
                                last_char_was_terminator = False
                            else:
                                if pending_quote:
                                    in_quotes = False
                                    pending_quote = False

                                if not in_quotes and char in {"\n", "\r"}:
                                    row_count += 1
                                    last_char_was_terminator = True
                                    if char == "\r":
                                        if (
                                            index + 1 < chunk_len
                                            and chunk[index + 1] == "\n"
                                        ):
                                            tmp.write("\n")
                                            index += 1
                                        else:
                                            pending_cr = True
                                    if row_count >= sample_rows:
                                        sample_complete = True
                                        break
                                else:
                                    last_char_was_terminator = False

                            index += 1

                        if sample_complete and not pending_cr:
                            break

                    if (
                        sample_rows > 0
                        and not last_char_was_terminator
                        and tmp.tell() > 0
                    ):
                        # Count a final record that reaches EOF without a line
                        # terminator so sampling semantics match the previous
                        # logical-record-based behavior.
                        row_count += 1
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


def _validate_skip_rows(skip_rows: int) -> int:
    """Validate skip_rows parameter."""
    if isinstance(skip_rows, bool) or not isinstance(skip_rows, int):
        raise TypeError("skip_rows must be an integer")

    if skip_rows < 0:
        raise ValueError("skip_rows must be non-negative")

    return skip_rows


def _validate_chunksize(chunksize: int) -> int:
    """Validate chunksize parameter."""
    if isinstance(chunksize, bool) or not isinstance(chunksize, int):
        raise TypeError("chunksize must be an integer")

    if chunksize <= 0:
        raise ValueError("chunksize must be a positive integer")

    return chunksize


def _validate_null_values(null_values: list[str]) -> list[str]:
    """Validate null_values parameter."""
    if isinstance(null_values, str):
        raise TypeError("null_values must be a list of strings, not a bare string")

    if not isinstance(null_values, list):
        raise TypeError("null_values must be a list of strings")

    for val in null_values:
        if not isinstance(val, str):
            raise TypeError("null_values must contain only strings")

    return list(null_values)


def _validate_parser_mode(mode: str) -> str:
    """Validate CSV parser mode."""
    if not isinstance(mode, str):
        raise TypeError("mode must be a string")
    if mode not in {"strict", "permissive"}:
        raise ValueError("mode must be either 'strict' or 'permissive'")
    return mode


def _materialize_csv_input(
    source: str | os.PathLike[str] | io.TextIOBase,
) -> tuple[str, bool]:
    """Convert supported CSV inputs into a filesystem path."""
    if isinstance(source, (str, os.PathLike)):
        return os.fspath(source), False
    if isinstance(source, io.StringIO) or (
        hasattr(source, "read") and callable(source.read)
    ):
        content = source.read()

        if not isinstance(content, str):
            raise TypeError("read_csv file-like objects must return text, not bytes")

        tmp = tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            suffix=".csv",
            delete=False,
        )

        try:
            tmp.write(content)
            tmp.close()
            return tmp.name, True
        except Exception:
            os.unlink(tmp.name)
            raise

    raise TypeError("read_csv expected a filesystem path or text file-like object")


def _reject_utf8_nul_bytes(path: str) -> None:
    """Reject UTF-8 CSV inputs that contain NUL bytes anywhere in the file."""
    try:
        with open(path, "rb") as f:
            while chunk := f.read(8192):
                if b"\0" in chunk:
                    raise CsvReadError(
                        "CSV input contains NUL bytes and appears to be binary or corrupted"
                    )
    except FileNotFoundError:
        pass  # Let C++ backend handle or raise standard error


def read_csv(
    path: str | os.PathLike[str],
    *,
    delimiter: str = ",",
    has_header: bool = True,
    usecols: list[str] | None = None,
    nrows: int | None = None,
    skiprows: int | None = None,
    encoding: str = "utf-8",
    trim_headers: bool = True,
    thousands_separator: str | None = None,
    null_values: list[str] | None = None,
    mode: str = "strict",
) -> ArFrame:
    """Read a CSV file into an ArFrame via C++ backend.

    Parameters
    ----------
    path : str or file-like object
        Filesystem path or text file-like object containing CSV data.
        Supports .csv, .txt, and .tsv extensions for path inputs.
    delimiter : str, default ","
        Field delimiter character.
    has_header : bool, default True
        Whether the file has a header row.
    usecols : list[str], optional
        Columns to read. If None, reads all columns.
    nrows : int, optional
        Number of rows to read. If None, reads all rows.
    skiprows : int, optional
        Number of lines to skip before reading the header. Useful for
        CSV files with metadata preambles before the actual data.
        If None, no lines are skipped.
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

    mode : {"strict", "permissive"}, default "strict"
        Controls malformed row handling.

        - strict: raises CsvReadError on inconsistent row widths.
        - permissive: fills missing trailing fields with nulls.

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
    path, should_cleanup = _materialize_csv_input(path)
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
        _reject_utf8_nul_bytes(path)
    try:
        if os.path.getsize(path) == 0:
            raise CsvReadError(f"CSV file is empty: {path!r}")
    except FileNotFoundError:
        pass  # Let C++ backend handle or raise standard error

    _validate_thousands_separator(thousands_separator)
    delimiter = _validate_delimiter(delimiter)
    mode = _validate_parser_mode(mode)
    config = _CsvConfig()
    config.delimiter = delimiter
    config.has_header = has_header
    config.encoding = encoding
    config.trim_headers = trim_headers
    config.thousands_separator = thousands_separator
    config.mode = mode

    if null_values is not None:
        config.null_values = _validate_null_values(null_values)

    if usecols is not None:
        config.usecols = _validate_usecols(usecols)

    if nrows is not None:
        config.nrows = _validate_nrows(nrows)

    if skiprows is not None:
        config.skip_rows = _validate_skip_rows(skiprows)

    reader = _CsvReader(config)

    try:
        with _utf8_csv_path(path, encoding, delimiter=delimiter) as native_path:
            cpp_frame = reader.read(native_path)

        return ArFrame(cpp_frame)

    except ValueError:
        raise
    except CsvReadError:
        raise
    except RuntimeError as e:
        raise CsvReadError(str(e)) from e

    finally:
        if should_cleanup and os.path.exists(path):
            os.unlink(path)


def read_csv_chunked(
    path: str | os.PathLike[str],
    *,
    chunksize: int = 10_000,
    delimiter: str = ",",
    has_header: bool = True,
    usecols: list[str] | None = None,
    nrows: int | None = None,
    skip_rows: int = 0,
    encoding: str = "utf-8",
    trim_headers: bool = True,
    thousands_separator: str | None = None,
    null_values: list[str] | None = None,
    mode: str = "strict",
) -> Iterator[ArFrame]:
    """Read a CSV file in chunks, yielding ArFrame objects.

    Column types are inferred from the first chunk and applied consistently
    to all subsequent chunks. Memory use is bounded by the chunk size.

    Parameters
    ----------
    path : str
        Path to the CSV file. Supports .csv, .txt, and .tsv extensions.
    chunksize : int, default 10_000
        Maximum number of data rows per yielded chunk.
    delimiter : str, default ","
        Field delimiter character.
    has_header : bool, default True
        Whether the file has a header row.
    usecols : list[str], optional
        Columns to read. If None, reads all columns.
    nrows : int, optional
        Maximum total number of data rows to read across all chunks.
    skip_rows : int, default 0
        Number of data rows to skip after the header row.
    encoding : str, default "utf-8"
        File encoding.
    trim_headers : bool, default True
        Strip leading/trailing whitespace from column names.
    thousands_separator : str, optional
        Single non-alphanumeric character used as a thousands separator
        during numeric parsing.
    null_values : list[str], optional
        Strings treated as null values.
    mode : {"strict", "permissive"}, default "strict"
        Controls malformed row handling.

    Yields
    ------
    ArFrame
        Successive chunks of the CSV data.

    Examples
    --------
    >>> for chunk in ar.read_csv_chunked("huge.csv", chunksize=100_000):
    ...     clean = ar.pipeline(chunk, [("drop_nulls",)])
    ...     df = ar.to_pandas(clean)
    ...     process(df)
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
        if os.path.getsize(path) == 0:
            raise CsvReadError(f"CSV file is empty: {path!r}")
    except FileNotFoundError:
        pass

    _validate_thousands_separator(thousands_separator)
    delimiter = _validate_delimiter(delimiter)
    mode = _validate_parser_mode(mode)
    chunksize = _validate_chunksize(chunksize)
    skip_rows = _validate_skip_rows(skip_rows)

    config = _CsvConfig()
    config.delimiter = delimiter
    config.has_header = has_header
    config.encoding = encoding
    config.trim_headers = trim_headers
    config.thousands_separator = thousands_separator
    config.mode = mode
    config.skip_rows = skip_rows

    if null_values is not None:
        config.null_values = _validate_null_values(null_values)

    if usecols is not None:
        config.usecols = _validate_usecols(usecols)

    if nrows is not None:
        config.nrows = _validate_nrows(nrows)

    reader = _CsvChunkReader(config)
    try:
        with _utf8_csv_path(path, encoding, delimiter=delimiter) as native_path:
            reader.open(native_path)
            while True:
                cpp_frame = reader.next_chunk(chunksize)
                if cpp_frame is None:
                    break
                yield ArFrame(cpp_frame)
    except ValueError:
        raise
    except CsvReadError:
        raise
    except RuntimeError as e:
        raise CsvReadError(str(e)) from e
    finally:
        reader.close()


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

    if not isinstance(delimiter, str):
        raise TypeError("delimiter must be a string")
    if len(delimiter) != 1:
        raise ValueError(f"delimiter must be a single character, got {delimiter!r}")
    if delimiter in {"\n", "\r"}:
        raise ValueError("delimiter must not be a newline character")
    if delimiter == '"':
        raise ValueError("delimiter must not be the CSV quote character")
    if not isinstance(line_terminator, str):
        raise TypeError("line_terminator must be a string")
    if line_terminator == "":
        raise ValueError("line_terminator must not be empty")

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
    null_values: list[str] | None = None,
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
        _reject_utf8_nul_bytes(path)
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

    if null_values is not None:
        config.null_values = _validate_null_values(null_values)

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
        # without rewriting decoded CSV text before native parsing.
        with _utf8_csv_path(
            path,
            encoding,
            delimiter=delimiter,
            sample_rows=100 if sample_size is None else sample_size,
        ) as native_path:
            return cast(dict[str, str], reader.scan_schema(native_path))
    except RuntimeError as e:
        raise CsvReadError(str(e)) from e


def read_jsonl(
    path: str | os.PathLike[str],
    *,
    encoding: str = "utf-8",
    nrows: int | None = None,
) -> ArFrame:
    """Read a JSON Lines file into an ArFrame.

    Each non-blank line must be a complete JSON object (``{...}``).  Column
    names are taken from the union of all keys found in the file.  Missing
    keys in a row become null values.  Type inference follows the same rules
    as :func:`from_pandas`: the first non-null value in a column determines
    its dtype; mixed-type columns are coerced to string.

    Parameters
    ----------
    path : str or path-like
        Path to the ``.jsonl`` or ``.ndjson`` file.
    encoding : str, default ``"utf-8"``
        File encoding.
    nrows : int, optional
        Maximum number of data rows to read.  If ``None``, all rows are read.

    Returns
    -------
    ArFrame
        Data frame containing the parsed records.

    Raises
    ------
    ValueError
        If the file extension is not ``.jsonl`` or ``.ndjson``, or if
        ``nrows`` is not a non-negative integer.
    JsonlReadError
        If the file is empty (no data rows), or if a line contains invalid
        JSON.  The error message includes the 1-based line number.

    Examples
    --------
    >>> frame = ar.read_jsonl("events.jsonl")
    >>> frame = ar.read_jsonl("data.ndjson", nrows=1000)
    """
    import json

    from .convert import from_pandas

    path = os.fspath(path)
    path_lower = path.lower()
    if not (path_lower.endswith(".jsonl") or path_lower.endswith(".ndjson")):
        raise ValueError(
            f"Unsupported file format: {path}. "
            "read_jsonl only supports .jsonl and .ndjson files."
        )

    if nrows is not None:
        if isinstance(nrows, bool) or not isinstance(nrows, int):
            raise TypeError("nrows must be an integer")
        if nrows < 0:
            raise ValueError("nrows must be non-negative")
        if nrows == 0:
            # Short-circuit: caller explicitly requested zero rows.
            # Do not open or inspect the file at all — even malformed content
            # must not raise when nrows=0.
            import pandas as pd

            from .convert import from_pandas

            return from_pandas(pd.DataFrame())

    records: list[dict] = []
    try:
        with open(path, encoding=encoding) as fh:
            for lineno, raw_line in enumerate(fh, start=1):
                line = raw_line.rstrip("\r\n")
                if not line.strip():
                    continue  # skip blank / whitespace-only lines
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise JsonlReadError(
                        f"Invalid JSON on line {lineno} of {path!r}: {exc}"
                    ) from exc
                if not isinstance(obj, dict):
                    raise JsonlReadError(
                        f"Expected a JSON object on line {lineno} of {path!r}, "
                        f"got {type(obj).__name__}"
                    )
                if nrows is not None and len(records) >= nrows:
                    break
                records.append(obj)
    except OSError as exc:
        raise JsonlReadError(str(exc)) from exc
    except UnicodeDecodeError as exc:
        raise JsonlReadError(
            f"Could not decode {path!r} using encoding {encoding!r}: {exc}"
        ) from exc

    if not records:
        raise JsonlReadError(f"JSON Lines file is empty (no data rows): {path!r}")

    import pandas as pd

    df = pd.DataFrame(records)
    return from_pandas(df)


def sniff_delimiter(
    path: str | os.PathLike[str],
    *,
    encoding: str = "utf-8",
    sample_size: int = 2048,
) -> str:
    """Sniff and return the field delimiter character from a CSV file.

    Parameters
    ----------
    path : str or os.PathLike[str]
        Path to the CSV file.
    encoding : str, default "utf-8"
        File encoding.
    sample_size : int, default 2048
        Number of bytes to sample from the start of the file for sniffing.

    Returns
    -------
    str
        The detected delimiter (one of ",", ";", "\\t", "|").

    Raises
    ------
    CsvReadError
        If the file is empty or contains binary data.
    ValueError
        If the sample size is invalid or the delimiter is ambiguous.
    """
    path = os.fspath(path)

    # 1. Parameter Validation
    if not isinstance(encoding, str):
        raise TypeError("encoding must be a string")
    if isinstance(sample_size, bool) or not isinstance(sample_size, int):
        raise TypeError("sample_size must be an integer")
    if sample_size <= 0:
        raise ValueError("sample_size must be a positive integer greater than 0")

    # 2. Check File Exists and Check for Binary Content
    try:
        if os.path.getsize(path) == 0:
            raise CsvReadError(f"CSV file is empty: {path!r}")
    except FileNotFoundError as e:
        raise FileNotFoundError(f"File not found: {path!r}") from e

    try:
        with open(path, "rb") as f:
            if b"\0" in f.read(1024):
                raise CsvReadError(
                    "CSV input contains NUL bytes and appears to be binary or corrupted"
                )
    except FileNotFoundError:
        pass

    # 3. Read Sample
    try:
        with open(path, encoding=encoding, errors="replace") as f:
            sample = f.read(sample_size)
    except LookupError as e:
        raise ValueError(f"Unknown encoding: {encoding}") from e

    if not sample:
        raise CsvReadError(f"CSV file is empty: {path!r}")

    # 4. Analyze Sample with Quote-Aware Character Scanner
    candidates = [",", ";", "\t", "|"]
    counts = {c: [0] for c in candidates}

    in_quotes = False
    quote_char = None

    i = 0
    n = len(sample)
    while i < n:
        char = sample[i]
        if in_quotes:
            if char == quote_char:
                # Check for escaped quote (e.g. standard CSV double-quote "")
                if i + 1 < n and sample[i + 1] == quote_char:
                    i += 1  # Skip the escaped quote
                else:
                    in_quotes = False
                    quote_char = None
        else:
            if char in ('"', "'"):
                in_quotes = True
                quote_char = char
            elif char in ("\n", "\r"):
                # Line boundary outside quotes
                if char == "\r" and i + 1 < n and sample[i + 1] == "\n":
                    i += 1
                for c in candidates:
                    counts[c].append(0)
            elif char in counts:
                counts[char][-1] += 1
        i += 1

    # Remove the last line if it is empty (e.g., trailing newline)
    for c in candidates:
        if len(counts[c]) > 1 and counts[c][-1] == 0:
            counts[c].pop()

    # 5. Score Candidates and Detect Ties/Ambiguity
    best_candidates = []
    best_score = -1.0

    from collections import Counter

    for delimiter in candidates:
        line_counts = counts[delimiter]
        non_zero_counts = [c for c in line_counts if c > 0]
        if not non_zero_counts:
            continue

        counter = Counter(non_zero_counts)
        mode, mode_freq = counter.most_common(1)[0]

        consistency = mode_freq / len(line_counts)
        score = consistency * 10.0 + (mode * 0.1)

        if score > best_score:
            best_score = score
            best_candidates = [delimiter]
        elif abs(score - best_score) < 1e-9:
            best_candidates.append(delimiter)

    if not best_candidates or best_score <= 0.0:
        raise ValueError(
            f"Could not determine CSV delimiter from sample: no candidate delimiters found in {path!r}"
        )

    if len(best_candidates) > 1:
        raise ValueError(
            f"Could not determine CSV delimiter from sample: multiple candidate delimiters {best_candidates} have the same score"
        )

    return best_candidates[0]
