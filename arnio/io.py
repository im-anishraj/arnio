"""
arnio.io
CSV reading and writing functions.
"""

from __future__ import annotations

import codecs
import io
import json
import os
import re as _re
import shutil
import tempfile
import urllib.error
import urllib.parse
import urllib.request
import warnings
from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Callable, cast

from ._core import (
    _CsvChunkReader,
    _CsvConfig,
    _CsvReader,
    _CsvWriteConfig,
    _CsvWriter,
)
from .exceptions import CsvReadError, JsonlReadError, RemoteReadError
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
    encoding_errors: str = "strict",
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
        with open(path, encoding=encoding, errors=encoding_errors, newline="") as src:
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
            f"Could not decode {path!r} using encoding {encoding!r}: "
            f"invalid byte(s) at position {e.start} "
            f"(byte value: 0x{e.object[e.start]:02x}). "
            f"Try a different encoding or use encoding_errors='replace'."
        ) from e
    except OSError as e:
        _raise_csv_path_os_error(path, e)
    finally:
        if tmp_name is not None:
            try:
                os.unlink(tmp_name)
            except OSError:
                pass


@contextmanager
def _utf8_csv_path_sampled(
    path: str,
    encoding: str,
    delimiter: str = ",",
    sample_rows: int | None = None,
    has_header: bool = True,
    encoding_errors: str = "strict",
) -> Iterator[tuple[str, int]]:
    """Return a UTF-8 sampled CSV path and the actual sampled row count.

    The native reader only consumes UTF-8 bytes. When sampling is requested,
    this helper writes a temporary UTF-8 file containing at most
    ``sample_rows`` complete logical records and tracks the number of records
    written.
    """
    if sample_rows is None:
        raise ValueError("sample_rows must not be None")

    tmp_name: str | None = None
    row_count = 0
    effective_limit = sample_rows + 1 if has_header else sample_rows
    try:
        with open(path, encoding=encoding, errors=encoding_errors, newline="") as src:
            with tempfile.NamedTemporaryFile(
                "w", encoding="utf-8", newline="", suffix=".csv", delete=False
            ) as tmp:
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
                                if row_count >= effective_limit:
                                    sample_complete = True
                                    break
                            else:
                                last_char_was_terminator = False

                        index += 1

                    if sample_complete and not pending_cr:
                        break

                if sample_rows > 0 and not last_char_was_terminator and tmp.tell() > 0:
                    row_count += 1
                tmp_name = tmp.name
        yield tmp_name, row_count
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


_PREVIEW_BAD_ROWS = 10


def _fetch_url_to_tempfile(url: str) -> str:
    """Fetch an HTTP/HTTPS URL and write its content to a UTF-8 temp file.

    Parameters
    ----------
    url : str
        A well-formed ``http://`` or ``https://`` URL whose response body
        is assumed to be UTF-8 encoded CSV text.

    Returns
    -------
    str
        Absolute path to the temporary file.  The caller is responsible for
        deleting it (``should_cleanup=True`` is returned by
        ``_materialize_csv_input``).

    Raises
    ------
    RemoteReadError
        On any network-level failure (DNS, timeout, connection refused) or
        a non-2xx HTTP response.
    """
    tmp = tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        suffix=".csv",
        delete=False,
    )
    tmp_name = tmp.name
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "arnio/read_csv"},
        )
        try:
            response = urllib.request.urlopen(req, timeout=_URL_FETCH_TIMEOUT)  # nosec B310
        except urllib.error.HTTPError as exc:
            raise RemoteReadError(
                f"HTTP {exc.code} fetching CSV URL {url!r}: {exc.reason}",
                url=url,
                status_code=exc.code,
            ) from exc
        except urllib.error.URLError as exc:
            raise RemoteReadError(
                f"Could not fetch CSV URL {url!r}: {exc.reason}",
                url=url,
            ) from exc

        # Stream response body into temp file using an incremental UTF-8
        # decoder so that multi-byte characters split across read() chunk
        # boundaries are handled correctly and do not raise a false
        # RemoteReadError.
        with response:
            decoder = codecs.getincrementaldecoder("utf-8")("strict")
            raw_bytes = response.read(_URL_FETCH_CHUNK_SIZE)
            while raw_bytes:
                try:
                    tmp.write(decoder.decode(raw_bytes, final=False))
                except UnicodeDecodeError as exc:
                    raise RemoteReadError(
                        f"Remote CSV at {url!r} is not valid UTF-8: {exc}",
                        url=url,
                    ) from exc
                raw_bytes = response.read(_URL_FETCH_CHUNK_SIZE)
            # Flush any bytes buffered inside the decoder for the final
            # (possibly incomplete) multi-byte sequence.
            try:
                tmp.write(decoder.decode(b"", final=True))
            except UnicodeDecodeError as exc:
                raise RemoteReadError(
                    f"Remote CSV at {url!r} is not valid UTF-8: {exc}",
                    url=url,
                ) from exc

        tmp.close()
        return tmp_name

    except RemoteReadError:
        try:
            tmp.close()
        except OSError:
            pass
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise
    except Exception as exc:
        try:
            tmp.close()
        except OSError:
            pass
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise RemoteReadError(
            f"Unexpected error fetching CSV URL {url!r}: {exc}",
            url=url,
        ) from exc


def _warn_bad_rows(bad_rows: Sequence[object]) -> None:
    """Emit a UserWarning summarizing rows dropped by on_bad_lines='warn'."""
    if not bad_rows:
        return

    def format_bad_row(br: object) -> str:
        if isinstance(br, str):
            return f"  {br}"
        row_bad = cast(_BadRow, br)
        return f"  CSV row {row_bad.row} has {row_bad.actual} fields; expected {row_bad.expected}"

    lines = [format_bad_row(br) for br in bad_rows[:_PREVIEW_BAD_ROWS]]
    extra = len(bad_rows) - _PREVIEW_BAD_ROWS
    if extra > 0:
        lines.append(f"  (+{extra} more)")
    warnings.warn(
        f"{len(bad_rows)} malformed CSV row(s):\n" + "\n".join(lines),
        UserWarning,
        stacklevel=3,
    )


def _validate_skip_rows(skip_rows: int) -> int:
    """Validate skip_rows parameter."""
    if isinstance(skip_rows, bool) or not isinstance(skip_rows, int):
        raise TypeError("skip_rows must be an integer")

    if skip_rows < 0:
        raise ValueError("skip_rows must be non-negative")

    return skip_rows


def _validate_skiprows(skiprows: int | None) -> int | None:
    """Validate skiprows parameter."""
    if skiprows is None:
        return None
    if isinstance(skiprows, bool) or not isinstance(skiprows, int):
        raise TypeError("skiprows must be an integer or None")
    if skiprows < 0:
        raise ValueError("skiprows must be non-negative")
    return skiprows


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



def _validate_on_bad_lines(on_bad_lines: str) -> str:
    """Validate on_bad_lines parameter."""
    if not isinstance(on_bad_lines, str):
        raise TypeError("on_bad_lines must be a string")

    valid_values = {"error", "warn", "skip"}

    if on_bad_lines not in valid_values:
        raise ValueError("on_bad_lines must be one of: " "'error', 'warn', or 'skip'")

    return on_bad_lines
]

@dataclass(frozen=True)
class CSVProgress:
    rows_read: int
    bytes_read: int
    total_bytes: int | None
    done: bool


def read_csv(
    path: str | os.PathLike[str] | io.TextIOBase,
    *,
    delimiter: str = ",",
    on_bad_lines: str = "warn",
    has_header: bool = True,
    usecols: list[str] | None = None,
    nrows: int | None = None,
    skiprows: int | None = None,
    encoding: str = "utf-8",
    trim_headers: bool = True,
    decimal_separator: str = ".",
    thousands_separator: str | None = None,
    null_values: list[str] | None = None,
    dtype: dict[str, str] | None = None,
    mode: str = "strict",
    encoding_errors: str = "strict",
    on_bad_lines: str = "error",
    progress_hook: Callable[[CSVProgress], None] | None = None,
    progress_interval_rows: int = 10000,
) -> ArFrame:
    """Read a CSV file into an ArFrame via C++ backend.

    Parameters
    ----------
    path : str or file-like object
        Filesystem path or text file-like object containing CSV data.
        Any file extension is accepted, including compressed ``.csv.gz`` files.
        For ``.tsv`` files, the delimiter
        is automatically set to ``'\t'`` when ``delimiter`` is omitted.
    delimiter : str or None, default None
        Field delimiter character.  When ``None`` (the default) the
        delimiter is inferred from the file extension: ``'\t'`` for
        ``.tsv`` files and ``','`` for everything else.  Passing an
        explicit value always takes precedence — for example,
        ``delimiter=','`` reads a comma-delimited ``.tsv`` file without
        any auto-detection.
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

    verbose : bool, default False
        If True, prints progress information during CSV reading,
        including the file path and number of rows loaded.

    progress_hook : Callable[[CSVProgress], None], optional
        Callback function to report parsing progress. Receives a CSVProgress payload containing rows_read, bytes_read, total_bytes, and done.
    progress_interval_rows : int, default 10000
        Number of rows to process before firing the progress hook.

    Returns
    -------
    ArFrame
        Data frame containing the CSV data.

    Raises
    ------
    ValueError
        If thousands_separator is invalid.

    TypeError
        If delimiter is not a string or None, or thousands_separator is
        not a string or None.

    CsvReadError
        If CSV input contains NUL bytes and appears binary or corrupted.

    Examples
    --------
    >>> import arnio as ar

    Read a basic CSV file:

    >>> df = ar.read_csv("data.csv")              # comma delimiter

    Read a CSV with specific columns and row limit:

    >>> df = ar.read_csv("large_data.csv", usecols=["id", "name"], nrows=1000)

    Other important behaviors:

    >>> df = ar.read_csv("data.tsv")              # tab auto-detected
    >>> df = ar.read_csv("data.tsv", delimiter=",")  # explicit comma honoured
    >>> df = ar.read_csv("data.dat")              # non-standard extension accepted
    """
    native_path, should_cleanup, is_materialized_text = _materialize_csv_input(path)

    if _is_utf8_encoding(encoding):
        _reject_utf8_nul_bytes(path)
    try:
        # Explicitly validate the decompressed temp file (or local path) rather than the compressed bytes
        _validate_csv_path(native_path, encoding)

    _validate_thousands_separator(thousands_separator)
    delimiter = _validate_delimiter(delimiter)
    mode = _validate_parser_mode(mode)
    on_bad_lines = _validate_on_bad_lines(on_bad_lines)
    config = _CsvConfig()
    config.delimiter = delimiter
    config.on_bad_lines = on_bad_lines
    config.has_header = has_header
    config.encoding = encoding
    config.trim_headers = trim_headers
    config.thousands_separator = thousands_separator
    config.mode = mode

        # Resolve the sentinel: auto-detect tab for .tsv only when the caller
        # truly omitted delimiter (None).  An explicit delimiter="," is always
        # honoured, even for .tsv paths.
        if delimiter is None:
            delimiter = "\t" if path_lower.endswith(".tsv") else ","

        decimal_separator = _validate_decimal_separator(decimal_separator)
        _validate_thousands_separator(thousands_separator, decimal_separator)
        delimiter = _validate_delimiter(delimiter)
        mode = _validate_parser_mode(mode)
        encoding_errors = _validate_encoding_errors(encoding_errors)
        on_bad_lines = _validate_on_bad_lines(on_bad_lines)
        config = _CsvConfig()
        config.delimiter = delimiter
        config.has_header = _validate_bool_option(has_header, "has_header")
        config.encoding = encoding
        config.trim_headers = _validate_bool_option(trim_headers, "trim_headers")
        config.decimal_separator = decimal_separator
        config.thousands_separator = thousands_separator
        config.mode = mode
        config.encoding_errors = encoding_errors
        if null_values is not None:
            config.null_values = _validate_null_values(null_values)
        if dtype is not None:
            config.dtype = _validate_dtype_mapping(dtype)
        if usecols is not None:
            config.usecols = _validate_usecols(usecols)
        if nrows is not None:
            config.nrows = _validate_nrows(nrows)
        if skiprows is not None:
            config.skip_rows = _validate_skip_rows(skiprows)

        if progress_hook is not None:
            if isinstance(progress_interval_rows, bool) or not isinstance(
                progress_interval_rows, int
            ):
                raise TypeError("progress_interval_rows must be an integer")
            if progress_interval_rows <= 0:
                raise ValueError("progress_interval_rows must be a positive integer")

            def wrapper(
                rows: int, bytes_read: int, total_bytes: int | None, is_done: bool
            ) -> None:
                box = CSVProgress(
                    rows_read=rows,
                    bytes_read=bytes_read,
                    total_bytes=total_bytes,
                    done=is_done,
                )
                progress_hook(box)

            config.progress_hook = wrapper  # type: ignore[attr-defined]
            config.progress_interval_rows = progress_interval_rows  # type: ignore[attr-defined]

        reader = _CsvReader(config)
    except Exception:
        if should_cleanup and os.path.exists(native_path):
            os.unlink(native_path)
        raise

    try:
        native_path: str
        with _utf8_csv_path(
            native_path,
            effective_encoding,
            encoding_errors=encoding_errors,
            delimiter=delimiter,
        ) as native_csv_path:
            try:
                cpp_frame, bad_rows = reader.read(native_csv_path, on_bad_lines)
            except CsvReadError:
                raise
            except (ValueError, TypeError):
                raise
            except RuntimeError as e:
                raise _enrich_csv_runtime_error(
                    e, native_path, encoding, delimiter
                ) from None

        if verbose:
            print(f"[arnio] Reading: {path}")
            frame = ArFrame(cpp_frame)
            print(f"[arnio] Done! {len(frame)} rows loaded.")
            return frame
        return ArFrame(cpp_frame)

        frame = ArFrame(cpp_frame)

        # Case 2: Delimiter mismatch — check only when usecols was not restricted
        # (usecols can legitimately produce 1 column) and has_header is True
        # so we can peek at the data line.
        if usecols is None and has_header:
            _warn_delimiter_mismatch(native_path, delimiter, frame.shape[1])

        return frame

    except (ValueError, TypeError):
        raise
    except CsvReadError:
        raise
    except Exception as e:
        raise CsvReadError(str(e)) from None

    finally:
        if should_cleanup and os.path.exists(native_path):
            os.unlink(native_path)


def read_csv_chunked(
    path: str | os.PathLike[str] | io.TextIOBase,
    *,
    chunksize: int = 10_000,
    delimiter: str | None = None,
    has_header: bool = True,
    usecols: list[str] | None = None,
    nrows: int | None = None,
    skiprows: int | None = None,
    skip_rows: int | None = None,
    encoding: str = "utf-8",
    trim_headers: bool = True,
    decimal_separator: str = ".",
    thousands_separator: str | None = None,
    null_values: list[str] | None = None,
    dtype: dict[str, str] | None = None,
    mode: str = "strict",
    encoding_errors: str = "strict",
    on_bad_lines: str = "error",
    progress_hook: Callable[[CSVProgress], None] | None = None,
    progress_interval_rows: int = 10000,
) -> Iterator[ArFrame]:
    """Read a CSV file in chunks, yielding ArFrame objects.

    Column types are inferred from the first chunk and applied consistently
    to all subsequent chunks. Memory use is bounded by the chunk size.

    Parameters
    ----------
    path : str or file-like object
        Path to the CSV file. Supports .csv, .txt, .tsv, and compressed .csv.gz extensions.
        Text file-like objects are copied to a temporary file in bounded
        chunks before native parsing.  For ``.tsv`` paths the delimiter is
        automatically set to ``'\\t'`` when ``delimiter`` is omitted.
    chunksize : int, default 10_000
        Maximum number of data rows per yielded chunk.
    delimiter : str or None, default None
        Field delimiter character.  When ``None`` (the default) the
        delimiter is inferred from the file extension: ``'\\t'`` for
        ``.tsv`` files and ``','`` for everything else.  Passing an
        explicit value always takes precedence — for example,
        ``delimiter=','`` reads a comma-delimited ``.tsv`` file without
        any auto-detection.
    has_header : bool, default True
        Whether the file has a header row.
    usecols : list[str], optional
        Columns to read. If None, reads all columns.
    nrows : int, optional
        Maximum total number of data rows to read across all chunks.
    skiprows : int, optional
        Number of data rows to skip after the header row.
        Alias ``skip_rows`` is still accepted but deprecated and
        will be removed in a future release.
    dtype : dict[str, str], optional
        Explicit column dtype mapping. Specified columns skip automatic
        type inference and use the requested dtype directly.
        Supported dtypes: ``"string"``, ``"int64"``, ``"float64"``, ``"bool"``.
    encoding_errors : {"strict", "replace", "ignore"}, default "strict"
        Controls how invalid UTF-8 bytes are handled during CSV parsing.
    encoding : str, default "utf-8"
        File encoding.
    trim_headers : bool, default True
        Strip leading/trailing whitespace from column names.  Regardless
        of this setting, headers that differ only by leading or trailing
        whitespace are always rejected with a :exc:`CsvReadError` because
        they would produce ambiguous column access.
    decimal_separator : str, default "."
        Single non-alphanumeric character used as the decimal separator
        during numeric parsing.
    thousands_separator : str, optional
        Single non-alphanumeric character used as a thousands separator
        during numeric parsing.
    null_values : list[str], optional
        Strings treated as null values.

    mode : {"strict", "permissive"}, default "strict"
        Controls malformed row handling.
        Both modes reject extra fields; permissive mode only allows missing
        trailing fields, which are filled with nulls.
    on_bad_lines : {"error", "warn", "skip"}, default "error"
        Action to take on rows classified as bad by ``mode``.

        - error: raise CsvReadError on the first bad row.
        - warn: drop the row and emit a UserWarning.
        - skip: drop the row silently.

        In permissive mode, narrow rows are still padded silently and do
        not reach this dispatch; only wide rows do. Dropped rows count
        toward ``nrows``.

    progress_hook : Callable[[CSVProgress], None], optional
        Callback function to report parsing progress. Receives a CSVProgress payload containing rows_read, bytes_read, total_bytes, and done.
    progress_interval_rows : int, default 10000
        Number of rows to process before firing the progress hook.

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

    Read a TSV file — tab delimiter is inferred automatically:

    >>> for chunk in ar.read_csv_chunked("data.tsv", chunksize=10_000):
    ...     process(chunk)

    Override auto-detection (e.g. a comma-delimited file with a .tsv extension):

    >>> for chunk in ar.read_csv_chunked("data.tsv", delimiter=",", chunksize=10_000):
    ...     process(chunk)
    """
    is_path_input = isinstance(path, (str, os.PathLike))
    native_path, should_cleanup, is_materialized_text = _materialize_csv_input(
        path, caller="read_csv_chunked"
    )
    try:
        path_lower = native_path.lower()
        if is_path_input:
            # We check the original path extension if it was passed as a path
            if isinstance(path, str):
                orig_path_lower = path.lower()
            elif isinstance(path, os.PathLike):
                orig_path_lower = os.fspath(path).lower()
            else:
                orig_path_lower = ""

    # Handle skip_rows → skiprows deprecation shim
    if skip_rows is not None:
        import warnings

        warnings.warn(
            "skip_rows is deprecated and will be removed in a future release. "
            "Use skiprows instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        if skiprows is not None:
            raise TypeError(
                "Cannot pass both skip_rows and skiprows. Use skiprows only."
            )
        skiprows = skip_rows

    # Delimiter auto-inference (matches read_csv behaviour)
    if delimiter is None:
        delimiter = "\t" if path.lower().endswith(".tsv") else ","

    decimal_separator = _validate_decimal_separator(decimal_separator)
    _validate_thousands_separator(thousands_separator, decimal_separator)
    delimiter = _validate_delimiter(delimiter)
    mode = _validate_parser_mode(mode)
    chunksize = _validate_chunksize(chunksize)
    encoding_errors = _validate_encoding_errors(encoding_errors)
    on_bad_lines = _validate_on_bad_lines(on_bad_lines)

    resolved_skiprows = _validate_skiprows(skiprows)

    config = _CsvConfig()
    config.delimiter = delimiter
    config.has_header = has_header
    config.on_bad_lines = on_bad_lines
    config.encoding = encoding
    config.trim_headers = trim_headers
    config.thousands_separator = thousands_separator
    config.mode = mode
    config.encoding_errors = encoding_errors
    if resolved_skiprows is not None:
        config.skip_rows = resolved_skiprows
    if dtype is not None:
        config.dtype = _validate_dtype_mapping(dtype)

        # Resolve the sentinel: auto-detect tab for .tsv only when the caller
        # truly omitted delimiter (None).  An explicit delimiter="," is always
        # honoured, even for .tsv paths.  File-like objects are materialised
        # to a temporary .csv path, so auto-detection safely falls back to ","
        # for those inputs — consistent with read_csv behaviour.
        if delimiter is None:
            delimiter = "\t" if path_lower.endswith(".tsv") else ","

        decimal_separator = _validate_decimal_separator(decimal_separator)
        _validate_thousands_separator(thousands_separator, decimal_separator)
        delimiter = _validate_delimiter(delimiter)
        mode = _validate_parser_mode(mode)
        chunksize = _validate_chunksize(chunksize)

        # Resolve skiprows / skip_rows alias.
        # Both skip data rows after the header in chunked mode.
        # skip_rows is kept for backward compatibility; skiprows matches
        # the read_csv parameter name. Both may be passed as long as they
        # agree; conflicting values raise ValueError.
        if skiprows is not None:
            if isinstance(skiprows, bool) or not isinstance(skiprows, int):
                raise TypeError("skiprows must be an integer")
            if skiprows < 0:
                raise ValueError("skiprows must be non-negative")
            if skip_rows != 0 and skip_rows != skiprows:
                raise ValueError(
                    f"Conflicting values: skiprows={skiprows!r} and "
                    f"skip_rows={skip_rows!r}. Pass only one of them."
                )
            skip_rows = skiprows

        skip_rows = _validate_skip_rows(skip_rows)
        on_bad_lines = _validate_on_bad_lines(on_bad_lines)

        config = _CsvConfig()
        config.delimiter = delimiter
        config.has_header = _validate_bool_option(has_header, "has_header")
        config.encoding = encoding
        config.trim_headers = _validate_bool_option(trim_headers, "trim_headers")
        config.decimal_separator = decimal_separator
        config.thousands_separator = thousands_separator
        config.mode = mode
        config.skip_rows = skip_rows

        if null_values is not None:
            config.null_values = _validate_null_values(null_values)

        if dtype is not None:
            config.dtype = _validate_dtype_mapping(dtype)

        if usecols is not None:
            config.usecols = _validate_usecols(usecols)
        if nrows is not None:
            config.nrows = _validate_nrows(nrows)

        if progress_hook is not None:
            if isinstance(progress_interval_rows, bool) or not isinstance(
                progress_interval_rows, int
            ):
                raise TypeError("progress_interval_rows must be an integer")
            if progress_interval_rows <= 0:
                raise ValueError("progress_interval_rows must be a positive integer")

            last_rows = 0
            last_bytes = 0
            last_total: int | None = 0

            def wrapper(
                rows: int, bytes_read: int, total_bytes: int | None, is_done: bool
            ) -> None:
                nonlocal last_rows, last_bytes, last_total
                last_rows = rows
                last_bytes = bytes_read
                last_total = total_bytes

                box = CSVProgress(
                    rows_read=rows,
                    bytes_read=bytes_read,
                    total_bytes=total_bytes,
                    done=is_done,
                )
                progress_hook(box)

            config.progress_hook = wrapper  # type: ignore[attr-defined]
            config.progress_interval_rows = progress_interval_rows  # type: ignore[attr-defined]

        reader = _CsvChunkReader(config)
    except Exception:
        if should_cleanup and os.path.exists(native_path):
            os.unlink(native_path)
        raise

    try:
        effective_encoding = "utf-8" if is_materialized_text else encoding
        with _utf8_csv_path(
            native_path, effective_encoding, delimiter=delimiter
        ) as native_csv_path:
            reader.open(native_csv_path)

            # Smart counter for small files
            total_yielded_rows = 0

                ar_frame = ArFrame(cpp_frame)
                if dtype is not None:
                    from .cleaning import cast_types as _apply_dtype

                    ar_frame = _apply_dtype(ar_frame, dtype)
                yield ar_frame
    except ValueError:
        raise
    except CsvReadError:
        raise
    except Exception as e:
        raise CsvReadError(str(e)) from None
    finally:
        if should_cleanup and os.path.exists(native_path):
            try:
                os.unlink(native_path)
            except OSError:
                pass


def write_csv(
    frame: ArFrame,
    path: str | os.PathLike[str],
    *,
    delimiter: str = ",",
    write_header: bool = True,
    line_terminator: str = "\n",
    escape_formulas: bool = False,
    encoding: str = "utf-8",
    encoding_errors: str = "strict",
) -> None:
    """Write an ArFrame to a CSV file via C++ backend.

    Parameters
    ----------
    frame : ArFrame
        The data frame to write.
    path : str
        Destination file path. Supports .csv, .txt, and .tsv extensions.
    delimiter : str or default ","
        Field delimiter character.
    write_header : bool, default True
        Whether to write the column header row.
    line_terminator : str, default "\\n"
        Line terminator to use between rows.
    escape_formulas : bool, default False
        If True, prefix string cell values that begin with spreadsheet formula
        trigger characters (``=``, ``+``, ``-``, ``@``, tab, or carriage return)
        with a single quote before CSV quoting. Numeric columns are not changed.
    encoding : str, default "utf-8"
        Output file encoding. UTF-8 (default) uses the native writer path
        directly with no transcoding overhead. Any other encoding supported
        by Python's ``codecs`` module is accepted; the native writer emits
        UTF-8 to a temporary file which is then transcoded in bounded chunks.
    encoding_errors : str, default "strict"
        How encoding errors are handled: ``"strict"`` raises ``ValueError``
        for unencodable characters, ``"replace"`` substitutes a replacement
        character, ``"ignore"`` drops unencodable characters.

    Raises
    ------
    TypeError
        If ``encoding`` or ``encoding_errors`` is not a string.
    ValueError
        If ``encoding`` is an unknown codec, ``encoding_errors`` is not one of
        ``"strict"``, ``"replace"``, or ``"ignore"``, or if a character cannot
        be encoded in the requested encoding with ``encoding_errors="strict"``.
    RuntimeError
        If the file cannot be opened or written.

    Examples
    --------
    >>> ar.write_csv(frame, "output.csv")
    >>> ar.write_csv(frame, "output.tsv", delimiter="\\t")
    >>> ar.write_csv(frame, "output_latin1.csv", encoding="latin-1")
    """
    if not isinstance(frame, ArFrame):
        raise TypeError("frame must be an ArFrame")

    if not isinstance(path, (str, bytes, os.PathLike)):
        raise TypeError(
            f"path must be a string, bytes, or os.PathLike object, got {type(path).__name__!r}"
        )
    path = os.fsdecode(os.fspath(path))
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

    # Validate encoding and encoding_errors before any file I/O.
    _validate_jsonl_encoding(encoding)
    _validate_encoding_errors(encoding_errors)

    config = _CsvWriteConfig()
    config.delimiter = delimiter
    config.has_header = has_header
    config.encoding = encoding
    config.trim_headers = trim_headers

    if usecols is not None:
        config.usecols = usecols
    if nrows is not None:
        config.nrows = nrows

    if _is_utf8_encoding(encoding):
        # Fast path: native writer emits UTF-8 directly — no transcoding overhead.
        try:
            writer.write(frame._frame, path)
        except RuntimeError as e:
            raise RuntimeError(str(e)) from e
        return

    # Non-UTF-8 path: write UTF-8 to a temp file, then transcode in bounded
    # chunks so the entire file is never held in memory at once.
    import tempfile

    _CHUNK_SIZE = 1 << 20  # 1 MiB per chunk

    tmp_fd, tmp_path = tempfile.mkstemp(suffix=".csv")
    output_tmp_path: str | None = None
    try:
        with _comment_filtered_csv_path(path, encoding, comment) as native_path:
            cpp_frame = reader.read(native_path)
    except ValueError:
        raise
    except CsvReadError:
        raise
    except RuntimeError as e:
        raise CsvReadError(str(e)) from e
    return ArFrame(cpp_frame)


# Characters that spreadsheet applications (Excel, Sheets, LibreOffice Calc)
# interpret as formula triggers when they appear at the start of a cell.
_SPREADSHEET_FORMULA_PREFIXES: frozenset[str] = frozenset(
    {"=", "+", "-", "@", "\t", "\r"}
)


def _sanitize_for_spreadsheet(frame: ArFrame) -> ArFrame:
    """Return a copy of *frame* with dangerous string cells prefixed.

    Any string cell whose first character is one of ``= + - @ \\t \\r``
    is prefixed with a single-quote (``'``).  Spreadsheet applications
    treat the leading single-quote as a "display as literal text" marker
    without displaying it, which neutralises CSV-injection attacks.

    Non-string columns and null values are left untouched.
    """
    import pandas as pd

    from .convert import from_pandas, to_pandas

    def _prefix_if_dangerous(val: object) -> object:
        if isinstance(val, str) and val and val[0] in _SPREADSHEET_FORMULA_PREFIXES:
            return "'" + val
        return val

    df = to_pandas(frame)

    for col in df.columns:
        if pd.api.types.is_string_dtype(df[col]):
            df[col] = df[col].apply(_prefix_if_dangerous)

    return from_pandas(df)


def write_csv(
    frame: ArFrame,
    path: str | os.PathLike[str],
    *,
    delimiter: str = ",",
    write_header: bool = True,
    line_terminator: str = "\n",
    safe_for_spreadsheet: bool = False,
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
    safe_for_spreadsheet : bool, default False
        When ``True``, prefix every string cell that starts with a
        spreadsheet formula trigger (``= + - @ \\t \\r``) with a
        single-quote (``'``).  This prevents CSV-injection attacks when
        the file is opened in Excel, Google Sheets, or LibreOffice Calc.

        The default is ``False`` so that raw data is preserved for
        programmatic consumers.  Set to ``True`` when the CSV is
        destined for human users opening it in a spreadsheet.

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
    >>> ar.write_csv(frame, "export.csv", safe_for_spreadsheet=True)
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

    if not isinstance(safe_for_spreadsheet, bool):
        raise TypeError(
            f"safe_for_spreadsheet must be True or False, "
            f"got {type(safe_for_spreadsheet).__name__}"
        )

    if safe_for_spreadsheet:
        frame = _sanitize_for_spreadsheet(frame)

    config = _CsvWriteConfig()
    config.delimiter = delimiter
    config.write_header = write_header
    config.line_terminator = line_terminator

    writer = _CsvWriter(config)
    dir_path = os.path.dirname(os.path.abspath(path))
    tmp_fd, tmp_path = tempfile.mkstemp(
        dir=dir_path,
        suffix=".csv",
        prefix=f".{os.path.basename(path)}.",
    )
    os.close(tmp_fd)
    try:
        writer.write(frame._frame, tmp_path)
        os.replace(tmp_path, path)
    except BaseException:
        try:
            os.unlink(tmp_path)
        except FileNotFoundError:
            pass
        raise


def scan_csv(
    path: str | os.PathLike[str] | io.TextIOBase,
    *,
    delimiter: str | None = None,
    encoding: str = "utf-8",
    skiprows: int | None = None,
    trim_headers: bool = True,
    decimal_separator: str = ".",
    thousands_separator: str | None = None,
    sample_size: int | None = None,
    null_values: list[str] | None = None,
    has_header: bool = True,
    encoding_errors: str = "strict",
    on_bad_lines: str = "error",
    return_metadata: bool = False,
) -> dict[str, str] | dict[str, object]:
    """Return schema (column names + inferred types) without loading data.

    Parameters
    ----------
    path : str or file-like object
        Filesystem path or text file-like object containing CSV data.
        Any file extension is accepted, including compressed ``.csv.gz`` files.
        For ``.tsv`` files, the delimiter
        is automatically set to ``'\t'`` when ``delimiter`` is omitted.
    delimiter : str or None, default None
        Field delimiter character.  When ``None`` (the default) the
        delimiter is inferred from the file extension: ``'\t'`` for
        ``.tsv`` files and ``','`` for everything else.  Passing an
        explicit value always takes precedence.
    encoding : str, default "utf-8"
        File encoding. For non-UTF-8 inputs, a sample of the file is
        transcoded to infer the schema.
    skiprows : int or None, default None
        Number of lines to skip at the beginning of the file before reading the
        header or data. Useful for bypassing unstructured metadata.
    trim_headers : bool, default True
        Strip leading/trailing whitespace from column names.

        Values containing delimiter characters must still be quoted
        properly in the CSV input. For example, when using a comma
        delimiter, the value "1,234" must be quoted, while unquoted
        1,234 is interpreted as two separate fields.
    sample_size : int, optional
        Number of rows to read for type inference. If None, defaults to 100 rows.
    has_header : bool, default True
        Whether the CSV file contains a header row.
        When False, synthetic column names are generated
        in the form ``col_0``, ``col_1``, etc., matching
        the behavior of ``read_csv(..., has_header=False)``.

    encoding_errors : str, default "strict"
        How encoding errors are handled. One of ``"strict"``, ``"replace"``,
        or ``"ignore"``.

    mode : {"strict", "permissive"}, default "strict"
        Controls malformed row handling during schema inference. In
        ``"permissive"`` mode, narrow rows are padded with nulls before type
        inference so scanning matches ``read_csv(..., mode="permissive")``.

    on_bad_lines : str, default "error"
        What to do when a malformed row is encountered during schema inference.
        ``"error"`` raises :exc:`CsvReadError` immediately (default).
        ``"warn"`` skips the bad row and emits a :class:`UserWarning`.
        ``"skip"`` silently skips the bad row without any warning.
    return_metadata : bool, default False
        Whether to return lightweight scan metadata along with
        inferred schema information.
    Returns
    -------
    dict[str, str] | dict[str, object]
        By default, returns a dictionary mapping column names
        to inferred type strings.

        When ``return_metadata=True``, returns a dictionary
        containing both inferred schema and lightweight scan metadata.

    Raises
    ------
    ValueError
        If thousands_separator or skiprows is invalid.

    TypeError
        If delimiter is not a string or None, or thousands_separator is
        not a string or None, or skiprows is not an integer.

    CsvReadError
        If CSV input contains NUL bytes and appears binary or corrupted.

    Examples
    --------
    >>> schema = ar.scan_csv("data.csv")
    >>> print(schema)
    {'name': 'string', 'age': 'int64'}
    >>> schema = ar.scan_csv("data.tsv")              # tab auto-detected
    >>> schema = ar.scan_csv("data.tsv", delimiter=",")  # explicit comma honoured
    >>> schema = ar.scan_csv("data.dat")              # non-standard extension accepted
    """

    path = os.fspath(path)

    _validate_csv_path(path, encoding)

    path_lower = path.lower()

    # Resolve the sentinel: auto-detect tab for .tsv only when the caller
    # truly omitted delimiter (None).  An explicit delimiter="," is always
    # honoured, even for .tsv paths.
    if delimiter is None:
        delimiter = "\t" if path_lower.endswith(".tsv") else ","

    decimal_separator = _validate_decimal_separator(decimal_separator)
    _validate_thousands_separator(thousands_separator, decimal_separator)
    delimiter = _validate_delimiter(delimiter)
    encoding_errors = _validate_encoding_errors(encoding_errors)
    on_bad_lines = _validate_on_bad_lines(on_bad_lines)
    config = _CsvConfig()
    config.delimiter = delimiter
    config.encoding = encoding
    config.trim_headers = _validate_bool_option(trim_headers, "trim_headers")
    config.decimal_separator = decimal_separator
    config.thousands_separator = thousands_separator
    config.has_header = has_header
    config.encoding_errors = encoding_errors

    if skiprows is not None:
        config.skip_rows = _validate_skip_rows(skiprows)
    if null_values is not None:
        config.null_values = _validate_null_values(null_values)

    if sample_size is not None:
        if not isinstance(sample_size, int) or isinstance(sample_size, bool):
            raise TypeError("sample_size must be an integer.")
        if sample_size <= 0:
            raise ValueError("sample_size must be a positive integer greater than 0.")
        config.sample_size = sample_size

    reader = _CsvReader(config)

    # Calculate the total rows needed from the file to satisfy the sample
    # request, ensuring skipped rows don't reduce the effective sample size.
    effective_sample_rows = 100 if sample_size is None else sample_size
    if skiprows is not None:
        effective_sample_rows += skiprows

    try:
        # Schema inference only needs a sample, avoiding full-file transcode.
        # sample_rows is passed so _utf8_csv_path uses record-aware sampling
        # without rewriting decoded CSV text before native parsing.
        with _utf8_csv_path_sampled(
            path,
            encoding,
            encoding_errors=encoding_errors,
            delimiter=delimiter,
            sample_rows=effective_sample_rows,
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
                if nrows is not None and len(records) >= nrows:
                    break
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

    except FileNotFoundError:
        pass

    config = _CsvConfig()
    config.delimiter = delimiter
    config.encoding = encoding
    config.trim_headers = trim_headers
    reader = _CsvReader(config)
    try:
        with open(path, encoding=encoding, errors="strict") as f:
            sample = f.read(sample_size)
    except LookupError as e:
        raise ValueError(f"Unknown encoding: {encoding}") from e
    except UnicodeDecodeError as e:
        raise CsvReadError(
            f"Could not decode {path!r} using encoding {encoding!r}"
        ) from e

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


_VALID_COMPRESSIONS = {"snappy", "gzip", "brotli", "zstd", "none"}


def write_parquet(
    frame: ArFrame,
    path: str | os.PathLike[str],
    *,
    compression: str = "snappy",
    row_group_size: int | None = None,
) -> None:
    """Write an ArFrame to a Parquet file via pyarrow.

    Requires the ``pyarrow`` package.  Install it with::

        pip install arnio[parquet]

    The implementation converts the frame to a pandas DataFrame via
    :func:`to_pandas` and delegates encoding to
    ``pandas.DataFrame.to_parquet(engine="pyarrow")``.

    Parameters
    ----------
    frame : ArFrame
        The data frame to write.
    path : str or path-like
        Destination file path.  Must end with ``.parquet`` or ``.pq``.
    compression : str, default ``"snappy"``
        Parquet compression codec.  Accepted values: ``"snappy"``,
        ``"gzip"``, ``"brotli"``, ``"zstd"``, ``"none"``.
    row_group_size : int, optional
        Number of rows per Parquet row group.  If ``None``, pyarrow
        chooses the default (typically 128 MB per group).  Must be a
        positive integer when provided.

    Raises
    ------
    ImportError
        If ``pyarrow`` is not installed.
    ValueError
        If the file extension is not ``.parquet`` or ``.pq``, if
        ``compression`` is not a recognised codec, or if
        ``row_group_size`` is not a positive integer.

    Examples
    --------
    >>> ar.write_parquet(frame, "output.parquet")
    >>> ar.write_parquet(frame, "output.pq", compression="zstd")
    >>> ar.write_parquet(frame, "output.parquet", row_group_size=50_000)
    """
    from .convert import to_pandas

    path = os.fspath(path)
    path_lower = path.lower()
    if not (path_lower.endswith(".parquet") or path_lower.endswith(".pq")):
        raise ValueError(
            f"Unsupported file format: {path}. "
            "write_parquet only supports .parquet and .pq files."
        )
    if not isinstance(compression, str):
        raise TypeError("compression must be a string")
    if compression not in _VALID_COMPRESSIONS:
        raise ValueError(
            f"Unknown compression codec: {compression!r}. "
            f"Valid options are: {sorted(_VALID_COMPRESSIONS)}"
        )

    if row_group_size is not None:
        if isinstance(row_group_size, bool) or not isinstance(row_group_size, int):
            raise TypeError("row_group_size must be an integer")
        if row_group_size <= 0:
            raise ValueError("row_group_size must be a positive integer")

    try:
        import pyarrow  # noqa: F401 — presence check only
    except ImportError as exc:
        raise ImportError(
            "pyarrow is required for Parquet export. "
            "Install it with: pip install arnio[parquet]"
        ) from exc

    df = to_pandas(frame)

    kwargs: dict = {
        "engine": "pyarrow",
        "compression": None if compression == "none" else compression,
        "index": False,
    }
    if row_group_size is not None:
        kwargs["row_group_size"] = row_group_size

    df.to_parquet(path, **kwargs)
