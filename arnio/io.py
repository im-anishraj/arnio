"""
arnio.io
CSV reading and writing functions.
"""

from __future__ import annotations

import codecs
import io
import json
import os
import shutil
import tempfile
import urllib.error
import urllib.parse
import urllib.request
import warnings
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from typing import cast

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
    if not isinstance(encoding, str):
        raise TypeError(f"encoding must be a string, got {type(encoding).__name__!r}")
    return encoding.lower().replace("_", "-") in {"utf-8", "utf8"}


def _raise_csv_path_os_error(path: str, error: OSError) -> None:
    """Raise a path-aware CsvReadError for filesystem access failures."""
    reason = error.strerror or str(error)
    raise CsvReadError(f"Could not access CSV file {path!r}: {reason}") from error


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
            f"Could not decode {path!r} using encoding {encoding!r}"
        ) from e
    except OSError as e:
        _raise_csv_path_os_error(path, e)
    finally:
        if tmp_name is not None:
            try:
                os.unlink(tmp_name)
            except OSError:
                pass


def _validate_thousands_separator(
    thousands_separator: str | None,
    decimal_separator: str = ".",
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
    if thousands_separator in {"+", "-"}:
        raise ValueError("Invalid thousands_separator: '+' and '-' are not allowed")
    if thousands_separator == decimal_separator:
        raise ValueError("thousands_separator must differ from decimal_separator")


def _validate_decimal_separator(decimal_separator: str) -> str:
    if not isinstance(decimal_separator, str):
        raise TypeError("decimal_separator must be a string")
    if len(decimal_separator) != 1:
        raise ValueError("decimal_separator must be a single character")
    if decimal_separator.isalnum() or decimal_separator in {'"', "\n", "\r"}:
        raise ValueError(
            "decimal_separator must be a single non-alphanumeric character"
        )
    if decimal_separator in {"+", "-"}:
        raise ValueError("Invalid decimal_separator: '+' and '-' are not allowed")
    return decimal_separator


def _validate_delimiter(delimiter: str) -> str:
    """Validate CSV delimiter."""
    if not isinstance(delimiter, str):
        raise TypeError("delimiter must be a string")

    if len(delimiter) != 1:
        raise ValueError(
            "delimiter must be a single character; delimiter must be exactly one character"
        )

    if delimiter in {"\n", "\r"}:
        raise ValueError("delimiter must not be a newline character")

    if delimiter == '"':
        raise ValueError("delimiter must not be the CSV quote character")

    cp = ord(delimiter)
    if (cp <= 0x1F and cp != 0x09) or cp == 0x7F:  # 0x09 = tab, allowed
        raise ValueError("delimiter must not be a control character")

    return delimiter


def _validate_usecols(usecols: Sequence[str]) -> list[str]:
    """Validate usecols parameter."""
    if isinstance(usecols, str):
        raise TypeError("usecols must be a sequence of column names, not a string")

    if not isinstance(usecols, Sequence):
        raise TypeError("usecols must be a sequence of strings")

    if len(usecols) == 0:
        raise ValueError("usecols must not be empty")

    for col in usecols:
        if not isinstance(col, str):
            raise TypeError("usecols must contain only strings")

    if len(set(usecols)) != len(usecols):
        raise ValueError("usecols must not contain duplicate column names")

    return list(usecols)


def _validate_dtype_mapping(dtype: dict[str, str]) -> dict[str, str]:
    if not isinstance(dtype, dict):
        raise TypeError(
            "dtype must be a dictionary mapping column names to dtype strings"
        )

    allowed = {"string", "int64", "float64", "bool"}

    validated: dict[str, str] = {}

    for column, dtype_name in dtype.items():
        if not isinstance(column, str):
            raise TypeError("dtype column names must be strings")

        if not isinstance(dtype_name, str):
            raise TypeError("dtype values must be strings")

        if dtype_name not in allowed:
            raise ValueError(
                f"Unsupported dtype {dtype_name!r}. Expected one of: {sorted(allowed)}"
            )

        validated[column] = dtype_name

    return validated


def _validate_nrows(nrows: int) -> int:
    """Validate nrows parameter."""
    if isinstance(nrows, bool) or not isinstance(nrows, int):
        raise TypeError("nrows must be an integer")

    if nrows < 0:
        raise ValueError("nrows must be non-negative")

    return nrows


_PREVIEW_BAD_ROWS = 10
_FILE_LIKE_COPY_CHUNK_SIZE = 8192

# ---------------------------------------------------------------------------
# Remote URL support
# ---------------------------------------------------------------------------

# Schemes fetched via stdlib urllib — zero new dependencies.
_SUPPORTED_URL_SCHEMES = frozenset({"https", "http"})

# Cloud provider schemes that are reserved for follow-up optional extras.
# Fail fast with an actionable install hint rather than a cryptic C++ error.
_CLOUD_SCHEME_HINTS: dict[str, str] = {
    "s3": 'pip install "arnio[s3]"',
    "gs": 'pip install "arnio[gcs]"',
    "gcs": 'pip install "arnio[gcs]"',
    "az": 'pip install "arnio[azure]"',
    "abfs": 'pip install "arnio[azure]"',
    "abfss": 'pip install "arnio[azure]"',
}

_URL_FETCH_TIMEOUT = 30  # seconds
_URL_FETCH_CHUNK_SIZE = 65536  # 64 KiB per streaming read


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
            response = urllib.request.urlopen(req, timeout=_URL_FETCH_TIMEOUT)
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


def _warn_bad_rows(bad_rows: list) -> None:
    """Emit a UserWarning summarizing rows dropped by on_bad_lines='warn'."""
    lines = [
        f"  CSV row {br.row} has {br.actual} fields; expected {br.expected}"
        for br in bad_rows[:_PREVIEW_BAD_ROWS]
    ]
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


def _validate_bool_option(value: bool, name: str) -> bool:
    """Validate that a boolean option is strictly True or False."""
    if not isinstance(value, bool):
        raise TypeError(
            f"{name} must be True or False, got {type(value).__name__}: {value!r}"
        )
    return value


def _validate_parser_mode(mode: str) -> str:
    """Validate CSV parser mode."""
    if not isinstance(mode, str):
        raise TypeError("mode must be a string")
    if mode not in {"strict", "permissive"}:
        raise ValueError("mode must be either 'strict' or 'permissive'")
    return mode


def _validate_on_bad_lines(on_bad_lines: str) -> str:
    if not isinstance(on_bad_lines, str):
        raise TypeError("on_bad_lines must be a string")
    if on_bad_lines not in {"error", "warn", "skip"}:
        raise ValueError("on_bad_lines must be either 'error', 'warn', 'skip'")
    return on_bad_lines


def _materialize_csv_input(
    source: str | os.PathLike[str] | io.TextIOBase,
    caller: str = "read_csv",
) -> tuple[str, bool, bool]:
    """Convert supported CSV inputs into a filesystem path.

    Supported input types
    ---------------------
    - Local filesystem paths (``str`` or ``os.PathLike``) — returned as-is.
    - ``https://`` / ``http://`` URLs — fetched via stdlib ``urllib`` and
      written to a UTF-8 temporary file.
    - Cloud provider URLs (``s3://``, ``gs://``, ``az://``, …) — raise
      ``ValueError`` with an actionable ``pip install`` hint.
    - Text file-like objects (``io.StringIO`` or any object with a
      ``read()`` method returning ``str``) — copied to a UTF-8 temp file.

    Returns
    -------
    (path, should_cleanup, is_materialized_text)
        ``should_cleanup`` is ``True`` when a temp file was created and the
        caller must delete it.  ``is_materialized_text`` signals that the
        file was already decoded to UTF-8, so ``_utf8_csv_path`` should
        skip re-transcoding.
    """
    if isinstance(source, (str, os.PathLike)):
        raw = os.fspath(source)
        is_temp = False

        # Only inspect scheme for plain strings — PathLike objects are
        # always local filesystem paths.
        if isinstance(source, str):
            parsed = urllib.parse.urlparse(raw)
            scheme = parsed.scheme.lower()

            # Cloud provider schemes — reserved, fail fast with install hint.
            if scheme in _CLOUD_SCHEME_HINTS:
                raise ValueError(
                    f"Cloud scheme {scheme!r} is not yet supported by arnio. "
                    f"Install the optional extra when available: "
                    f"{_CLOUD_SCHEME_HINTS[scheme]}"
                )

            # HTTP/HTTPS — fetch via stdlib urllib, no new dependencies.
            if scheme in _SUPPORTED_URL_SCHEMES:
                raw = _fetch_url_to_tempfile(raw)
                is_temp = True

        is_gz = False
        if isinstance(source, str) and source.lower().endswith(".gz"):
            is_gz = True
        elif not isinstance(source, str) and raw.lower().endswith(".gz"):
            is_gz = True

        if is_gz:
            import gzip

            tmp = tempfile.NamedTemporaryFile(
                mode="wb",
                suffix=".csv",
                delete=False,
            )
            try:
                with gzip.open(raw, "rb") as gz_file:
                    shutil.copyfileobj(gz_file, tmp, length=_FILE_LIKE_COPY_CHUNK_SIZE)
                tmp.close()
                if is_temp:
                    try:
                        os.unlink(raw)
                    except OSError:
                        pass
                return tmp.name, True, False
            except Exception:
                try:
                    tmp.close()
                except OSError:
                    pass
                try:
                    os.unlink(tmp.name)
                except OSError:
                    pass
                if is_temp:
                    try:
                        os.unlink(raw)
                    except OSError:
                        pass
                raise

        # If it was an HTTP fetch but not a .gz, it's materialized text
        if is_temp:
            return raw, True, True

        return raw, False, False

    if isinstance(source, io.StringIO) or (
        hasattr(source, "read") and callable(source.read)
    ):
        text_tmp = tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            suffix=".csv",
            delete=False,
        )

        try:
            while True:
                chunk = source.read(_FILE_LIKE_COPY_CHUNK_SIZE)
                if chunk == "":
                    break
                if not isinstance(chunk, str):
                    raise TypeError(
                        "read_csv file-like objects must return text, not bytes"
                    )
                text_tmp.write(chunk)
            text_tmp.close()
            return text_tmp.name, True, True
        except Exception:
            try:
                text_tmp.close()
            except OSError:
                pass
            try:
                os.unlink(text_tmp.name)
            except OSError:
                pass
            raise

    # read_csv_chunked expects a shorter message (no URL mention) per its test.
    if caller == "read_csv_chunked":
        raise TypeError(f"{caller} expected a filesystem path or text file-like object")
    raise TypeError(
        f"{caller} expected a filesystem path, a URL, or a text file-like object"
    )


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
    except OSError as e:
        _raise_csv_path_os_error(path, e)


def _validate_csv_path(
    path: str, encoding: str, *, reject_utf8_nul_bytes: bool = True
) -> None:
    """Shared validation for CSV-style file inputs."""

    is_utf8 = _is_utf8_encoding(encoding)
    if reject_utf8_nul_bytes and is_utf8:
        _reject_utf8_nul_bytes(path)

    try:
        if os.path.getsize(path) == 0:
            raise CsvReadError(f"CSV file is empty: {path!r}")
    except FileNotFoundError:
        pass
    except OSError as e:
        _raise_csv_path_os_error(path, e)


_VALID_ENCODING_ERRORS = {"strict", "replace", "ignore"}


def _validate_encoding_errors(value: str) -> str:
    if not isinstance(value, str):
        raise TypeError("encoding_errors must be a string")

    if value not in _VALID_ENCODING_ERRORS:
        raise ValueError(
            "encoding_errors must be one of 'strict', 'replace', or 'ignore'"
        )

    return value


def read_csv(
    path: str | os.PathLike[str] | io.TextIOBase,
    *,
    delimiter: str | None = None,
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
        Strip leading/trailing whitespace from column names.  Regardless
        of this setting, headers that differ only by leading or trailing
        whitespace are always rejected with a :exc:`CsvReadError` because
        they would produce ambiguous column access.
    decimal_separator : str, default "."
        Single non-alphanumeric character used as the decimal separator
        during numeric parsing. Use "," to opt in to European-style decimals
        such as ``"12,45"``. Values containing the CSV delimiter must still
        be quoted.
    thousands_separator : str, optional
        Single non-alphanumeric character used as a thousands separator
        during numeric parsing.



        Values containing delimiter characters must still be quoted
        properly in the CSV input. For example, when using a comma
        delimiter, the value "1,234" must be quoted, while unquoted
        1,234 is interpreted as two separate fields.

    dtype : dict[str, str], optional
        Explicit column dtype mapping. Specified columns skip automatic
        type inference and use the requested dtype directly.

        Supported dtypes:
        - "string"
        - "int64"
        - "float64"
        - "bool"

    mode : {"strict", "permissive"}, default "strict"
        Controls malformed row handling.

        - strict: raises CsvReadError on inconsistent row widths.
        - permissive: fills missing trailing fields with nulls.
        - both modes reject extra fields because they would otherwise be
          silently dropped.

    on_bad_lines : {"error", "warn", "skip"}, default "error"
        Action to take on rows classified as bad by ``mode``.

        - error: raise CsvReadError on the first bad row.
        - warn: drop the row and emit a UserWarning.
        - skip: drop the row silently.

        In permissive mode, narrow rows are still padded silently and do
        not reach this dispatch; only wide rows do. Dropped rows count
        toward ``nrows``.

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

    try:
        # Explicitly validate the decompressed temp file (or local path) rather than the compressed bytes
        _validate_csv_path(native_path, encoding)

        path_lower = native_path.lower()

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

        reader = _CsvReader(config)
    except Exception:
        if should_cleanup and os.path.exists(native_path):
            os.unlink(native_path)
        raise

    try:
        effective_encoding = "utf-8" if is_materialized_text else encoding
        with _utf8_csv_path(
            native_path,
            effective_encoding,
            encoding_errors=encoding_errors,
            delimiter=delimiter,
        ) as native_csv_path:
            cpp_frame, bad_rows = reader.read(native_csv_path, on_bad_lines)

        # on_bad_lines == "error" will raise RuntimeError then converted to CsvReadError as before
        if on_bad_lines == "warn" and bad_rows:
            _warn_bad_rows(bad_rows)

        return ArFrame(cpp_frame)

    except ValueError:
        raise
    except CsvReadError:
        raise
    except RuntimeError as e:
        raise CsvReadError(str(e)) from None

    finally:
        if should_cleanup and os.path.exists(native_path):
            os.unlink(native_path)


def read_csv_chunked(
    path: str | os.PathLike[str] | io.TextIOBase,
    *,
    chunksize: int = 10_000,
    dtype: dict[str, str] | None = None,
    delimiter: str | None = None,
    has_header: bool = True,
    usecols: list[str] | None = None,
    nrows: int | None = None,
    skip_rows: int = 0,
    skiprows: int | None = None,
    encoding: str = "utf-8",
    trim_headers: bool = True,
    decimal_separator: str = ".",
    thousands_separator: str | None = None,
    null_values: list[str] | None = None,
    mode: str = "strict",
    on_bad_lines: str = "error",
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
    skip_rows : int, default 0
        Number of data rows to skip after the header row.
    skiprows : int, optional
        Alias for ``skip_rows`` for API consistency with ``read_csv``.
        Note: in chunked mode both ``skip_rows`` and ``skiprows`` skip
        data rows *after* the header, not lines before it.
        If both are supplied they must agree; conflicting values raise
        ``ValueError``.
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

            if not (
                orig_path_lower.endswith(".csv")
                or orig_path_lower.endswith(".txt")
                or orig_path_lower.endswith(".tsv")
                or orig_path_lower.endswith(".gz")
            ):
                raise ValueError(
                    f"Unsupported file format: {path}. "
                    "Only .csv, .txt, .tsv, and compressed .csv.gz are supported."
                )

        # Explicitly validate the decompressed temp file (or local path) rather than the compressed bytes
        _validate_csv_path(native_path, encoding, reject_utf8_nul_bytes=False)

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
            yielded_nonempty_chunk = False
            while True:
                chunk = reader.next_chunk(chunksize, on_bad_lines)
                if chunk is None:
                    break
                cpp_frame, bad_rows = chunk

                if on_bad_lines == "warn" and bad_rows:
                    _warn_bad_rows(bad_rows)
                frame = ArFrame(cpp_frame)

                if frame.shape[0] == 0 and bad_rows:
                    if yielded_nonempty_chunk:
                        continue

                yielded_nonempty_chunk = yielded_nonempty_chunk or frame.shape[0] > 0

                yield frame
    except ValueError:
        raise
    except CsvReadError:
        raise
    except RuntimeError as e:
        raise CsvReadError(str(e)) from None
    finally:
        reader.close()
        if should_cleanup and os.path.exists(native_path):
            os.unlink(native_path)


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

    delimiter = _validate_delimiter(delimiter)
    if not isinstance(line_terminator, str):
        raise TypeError("line_terminator must be a string")
    if line_terminator not in {"\n", "\r\n", "\r"}:
        raise ValueError(
            f"line_terminator must be one of '\\n', '\\r\\n', or '\\r', got {line_terminator!r}"
        )

    config = _CsvWriteConfig()
    config.delimiter = delimiter
    config.write_header = _validate_bool_option(write_header, "write_header")
    config.line_terminator = line_terminator

    writer = _CsvWriter(config)
    try:
        writer.write(frame._frame, path)
    except RuntimeError as e:
        raise RuntimeError(str(e)) from e


def scan_csv(
    path: str | os.PathLike[str] | io.TextIOBase,
    *,
    delimiter: str | None = None,
    encoding: str = "utf-8",
    trim_headers: bool = True,
    decimal_separator: str = ".",
    thousands_separator: str | None = None,
    sample_size: int | None = None,
    null_values: list[str] | None = None,
    has_header: bool = True,
    encoding_errors: str = "strict",
    mode: str = "strict",
    on_bad_lines: str = "error",
) -> dict[str, str]:
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
    Returns
    -------
    dict[str, str]
        Dictionary mapping column names to inferred type strings.

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
    >>> schema = ar.scan_csv("data.csv")
    >>> print(schema)
    {'name': 'string', 'age': 'int64'}
    >>> schema = ar.scan_csv("data.tsv")              # tab auto-detected
    >>> schema = ar.scan_csv("data.tsv", delimiter=",")  # explicit comma honoured
    >>> schema = ar.scan_csv("data.dat")              # non-standard extension accepted
    """

    native_path, should_cleanup, _ = _materialize_csv_input(path, caller="scan_csv")

    try:
        _validate_csv_path(native_path, encoding, reject_utf8_nul_bytes=False)

        path_lower = native_path.lower()

        # Resolve the sentinel: auto-detect tab for .tsv only when the caller
        # truly omitted delimiter (None).  An explicit delimiter="," is always
        # honoured, even for .tsv paths.
        if delimiter is None:
            delimiter = "\t" if path_lower.endswith(".tsv") else ","

        decimal_separator = _validate_decimal_separator(decimal_separator)
        _validate_thousands_separator(thousands_separator, decimal_separator)
        delimiter = _validate_delimiter(delimiter)
        encoding_errors = _validate_encoding_errors(encoding_errors)
        mode = _validate_parser_mode(mode)
        on_bad_lines = _validate_on_bad_lines(on_bad_lines)
        config = _CsvConfig()
        config.delimiter = delimiter
        config.encoding = encoding
        config.trim_headers = _validate_bool_option(trim_headers, "trim_headers")
        config.decimal_separator = decimal_separator
        config.thousands_separator = thousands_separator
        config.has_header = _validate_bool_option(has_header, "has_header")
        config.encoding_errors = encoding_errors
        config.mode = mode

        if null_values is not None:
            config.null_values = _validate_null_values(null_values)

        if sample_size is not None:
            if not isinstance(sample_size, int) or isinstance(sample_size, bool):
                raise TypeError("sample_size must be an integer.")
            if sample_size <= 0:
                raise ValueError(
                    "sample_size must be a positive integer greater than 0."
                )
            config.sample_size = sample_size

        reader = _CsvReader(config)
        # Schema inference only needs a sample, avoiding full-file transcode.
        # For scan_csv, if sample_rows is specified, we use that for sniffing the schema.
        # sample_rows is passed so _utf8_csv_path uses record-aware sampling
        # without rewriting decoded CSV text before native parsing.
        with _utf8_csv_path(
            native_path,
            encoding,
            encoding_errors=encoding_errors,
            delimiter=delimiter,
            sample_rows=100 if sample_size is None else sample_size,
        ) as native_csv_path:
            schema, bad_row_msgs = reader.scan_schema(native_csv_path, on_bad_lines)
            if on_bad_lines == "warn" and bad_row_msgs:
                warnings.warn(
                    f"{len(bad_row_msgs)} malformed CSV row(s) skipped during schema inference:\n"
                    + "\n".join(f"  {m}" for m in bad_row_msgs),
                    UserWarning,
                    stacklevel=2,
                )
            return cast(dict[str, str], schema)
    except RuntimeError as e:
        raise CsvReadError(str(e)) from None
    finally:
        if should_cleanup and os.path.exists(native_path):
            try:
                os.unlink(native_path)
            except OSError:
                pass


def _reject_non_finite(constant: str) -> None:
    """Reject non-finite JSON constants (NaN, Infinity, -Infinity)."""
    raise ValueError(f"Non-finite JSON constant not allowed: {constant!r}")


def _reject_duplicate_json_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    seen = set()
    result = {}
    for key, value in pairs:
        if key in seen:
            raise ValueError(f"duplicate key {key!r}")
        seen.add(key)
        result[key] = value
    return result


def _validate_jsonl_encoding(encoding: str) -> None:
    if not isinstance(encoding, str):
        raise TypeError(f"encoding must be a string, got {type(encoding).__name__!r}")
    try:
        codecs.lookup(encoding)
    except LookupError:
        raise ValueError(f"Unknown encoding: {encoding!r}")


def _validate_jsonl_nrows(nrows: int | None) -> int | None:
    if nrows is not None:
        if isinstance(nrows, bool) or not isinstance(nrows, int):
            raise TypeError("nrows must be an integer")
        if nrows < 0:
            raise ValueError("nrows must be non-negative")
    return nrows


def _validate_jsonl_path(path: str) -> None:
    path_lower = path.lower()
    if not (path_lower.endswith(".jsonl") or path_lower.endswith(".ndjson")):
        raise ValueError(
            f"Unsupported file format: {path}. "
            "read_jsonl only supports .jsonl and .ndjson files."
        )


def _parse_jsonl_record(line: str, lineno: int, path: str) -> dict:
    from .convert import _is_nested

    try:
        obj = json.loads(
            line,
            object_pairs_hook=_reject_duplicate_json_keys,
            parse_constant=_reject_non_finite,
        )
    except json.JSONDecodeError as exc:
        raise JsonlReadError(
            f"Invalid JSON on line {lineno} of {path!r}: {exc}"
        ) from exc
    except ValueError as exc:
        message = str(exc)
        prefix = (
            "Duplicate key" if message.startswith("duplicate key") else "Invalid value"
        )
        raise JsonlReadError(f"{prefix} on line {lineno} of {path!r}: {exc}") from exc

    if not isinstance(obj, dict):
        raise JsonlReadError(
            f"Expected a JSON object on line {lineno} of {path!r}, "
            f"got {type(obj).__name__}"
        )

    for key, value in obj.items():
        if _is_nested(value):
            raise JsonlReadError(
                f"Column {key!r} contains unsupported nested value "
                f"of type {type(value).__name__!r} on line {lineno} of {path!r}. "
                "Convert nested objects to strings or flatten them first."
            )

    return obj


def _iter_jsonl_records(
    path: str,
    *,
    encoding: str,
    encoding_errors: str,
    nrows: int | None,
) -> Iterator[dict]:
    records_read = 0
    try:
        with open(path, encoding=encoding, errors=encoding_errors) as fh:
            for lineno, raw_line in enumerate(fh, start=1):
                line = raw_line.rstrip("\r\n")
                if not line.strip():
                    continue
                if nrows is not None and records_read >= nrows:
                    break
                yield _parse_jsonl_record(line, lineno, path)
                records_read += 1
    except OSError as exc:
        raise JsonlReadError(str(exc)) from exc
    except UnicodeDecodeError as exc:
        raise JsonlReadError(
            f"Could not decode {path!r} using encoding {encoding!r}: {exc}"
        ) from exc


def _records_to_arframe(records: list[dict]) -> ArFrame:
    import pandas as pd

    from .convert import from_pandas

    return from_pandas(pd.DataFrame(records))


def read_jsonl(
    path: str | os.PathLike[str],
    *,
    encoding: str = "utf-8",
    encoding_errors: str = "strict",
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
        JSON or unsupported nested values. The error message includes the
        1-based line number.

    Examples
    --------
    >>> frame = ar.read_jsonl("events.jsonl")
    >>> frame = ar.read_jsonl("data.ndjson", nrows=1000)
    """
    _validate_jsonl_encoding(encoding)

    if not isinstance(path, (str, os.PathLike)):
        raise TypeError(
            f"read_jsonl expected a filesystem path, got {type(path).__name__!r}"
        )
    path = os.fspath(path)
    encoding_errors = _validate_encoding_errors(encoding_errors)
    nrows = _validate_jsonl_nrows(nrows)

    if nrows == 0:
        # Short-circuit: caller explicitly requested zero rows.
        # Do not open or inspect the file at all; even malformed content or an
        # unsupported extension must not raise when nrows=0.
        return _records_to_arframe([])

    _validate_jsonl_path(path)
    records = list(
        _iter_jsonl_records(
            path,
            encoding=encoding,
            encoding_errors=encoding_errors,
            nrows=nrows,
        )
    )
    if not records:
        raise JsonlReadError(f"JSON Lines file is empty (no data rows): {path!r}")

    return _records_to_arframe(records)


def read_jsonl_chunked(
    path: str | os.PathLike[str],
    *,
    chunksize: int = 10000,
    encoding: str = "utf-8",
    encoding_errors: str = "strict",
    nrows: int | None = None,
) -> Iterator[ArFrame]:
    """Yield JSON Lines records as ``ArFrame`` chunks.

    This is the streaming counterpart to :func:`read_jsonl`.  It preserves the
    same parsing and validation rules while materializing at most one chunk of
    decoded records at a time.

    Parameters
    ----------
    path : str or path-like
        Path to the ``.jsonl`` or ``.ndjson`` file.
    chunksize : int, default ``10000``
        Maximum number of data rows per yielded chunk.
    encoding : str, default ``"utf-8"``
        File encoding.
    encoding_errors : str, default ``"strict"``
        Error policy used while decoding file bytes.
    nrows : int, optional
        Maximum number of data rows to read. If ``None``, all rows are read.

    Yields
    ------
    ArFrame
        Parsed records in chunks of at most ``chunksize`` rows.

    Raises
    ------
    ValueError
        If the file extension is not ``.jsonl`` or ``.ndjson``, if
        ``chunksize`` is not positive, or if ``nrows`` is not non-negative.
    JsonlReadError
        If the file is empty (no data rows), or if a line contains invalid
        JSON or unsupported nested values. The error message includes the
        1-based line number.
    """
    _validate_jsonl_encoding(encoding)

    path = os.fspath(path)
    encoding_errors = _validate_encoding_errors(encoding_errors)
    nrows = _validate_jsonl_nrows(nrows)

    if isinstance(chunksize, bool) or not isinstance(chunksize, int):
        raise TypeError("chunksize must be an integer")
    if chunksize <= 0:
        raise ValueError("chunksize must be a positive integer")

    if nrows == 0:
        return

    _validate_jsonl_path(path)

    chunk: list[dict] = []
    yielded_any = False
    for record in _iter_jsonl_records(
        path,
        encoding=encoding,
        encoding_errors=encoding_errors,
        nrows=nrows,
    ):
        chunk.append(record)
        if len(chunk) == chunksize:
            yielded_any = True
            yield _records_to_arframe(chunk)
            chunk = []

    if chunk:
        yielded_any = True
        yield _records_to_arframe(chunk)

    if not yielded_any:
        raise JsonlReadError(f"JSON Lines file is empty (no data rows): {path!r}")


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
        Number of characters to sample from the start of the file for sniffing.
        Note: For multi-byte encodings like UTF-8 with multi-byte characters
        (emoji, CJK), the actual bytes read may exceed this value since
        characters are counted, not bytes.

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
    if not isinstance(path, (str, os.PathLike)):
        raise TypeError(
            f"sniff_delimiter expected a filesystem path, got {type(path).__name__!r}"
        )
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

    if _is_utf8_encoding(encoding):
        try:
            _reject_utf8_nul_bytes(path)
        except FileNotFoundError:
            pass

    # 3. Read Sample
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
    best_candidates: list[str] = []
    best_consistency = -1.0
    best_mode = -1

    from collections import Counter

    for delimiter in candidates:
        line_counts = counts[delimiter]
        non_zero_counts = [c for c in line_counts if c > 0]
        if not non_zero_counts:
            continue

        counter = Counter(non_zero_counts)
        mode, mode_freq = counter.most_common(1)[0]

        # Primary score: fraction of ALL lines that show the modal count
        consistency = mode_freq / len(line_counts)

        if consistency > best_consistency + 1e-9:
            # Strictly better consistency → new sole leader
            best_consistency = consistency
            best_mode = mode
            best_candidates = [delimiter]
        elif abs(consistency - best_consistency) < 1e-9:
            # Consistency tied → apply secondary tie-breaker (mode)
            if mode > best_mode:
                # Higher per-line count wins the tie
                best_mode = mode
                best_candidates = [delimiter]
            elif mode == best_mode:
                # Both scores identical → ambiguous; keep both
                best_candidates.append(delimiter)
            # mode < best_mode: current leader keeps its position

    if not best_candidates or best_consistency <= 0.0:
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
    preserve_attrs: bool = True,
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
    preserve_attrs : bool, default ``True``
        When ``True``, ``DataFrame.attrs`` are written into Parquet
        metadata; all attr values must be JSON-serializable or a
        ``TypeError`` is raised with a clear message.  Set to ``False``
        to silently drop attrs on export.

    Raises
    ------
    ImportError
        If ``pyarrow`` is not installed.
    TypeError
        If ``preserve_attrs`` is ``True`` and ``DataFrame.attrs``
        contains non-JSON-serializable values.
    ValueError
        If the file extension is not ``.parquet`` or ``.pq``, if
        ``compression`` is not a recognised codec, or if
        ``row_group_size`` is not a positive integer.

    Examples
    --------
    >>> ar.write_parquet(frame, "output.parquet")
    >>> ar.write_parquet(frame, "output.pq", compression="zstd")
    >>> ar.write_parquet(frame, "output.parquet", row_group_size=50_000)
    >>> ar.write_parquet(frame, "output.parquet", preserve_attrs=False)
    """
    if not isinstance(frame, ArFrame):
        raise TypeError("frame must be an ArFrame")

    from .convert import to_pandas

    if not isinstance(path, (str, bytes, os.PathLike)):
        raise TypeError(
            f"path must be a string, bytes, or os.PathLike object, got {type(path).__name__!r}"
        )

    path = os.fsdecode(os.fspath(path))
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

    rows, cols = frame.shape
    if cols == 0 and rows > 0:
        raise ValueError(
            f"Cannot write a zero-column ArFrame with {rows} rows to Parquet: the current export path cannot preserve row count without columns."
        )

    df = to_pandas(frame)

    if df.attrs:
        if preserve_attrs:
            try:
                json.dumps(df.attrs)
            except (TypeError, ValueError) as exc:
                raise TypeError(
                    "write_parquet() requires that DataFrame.attrs contain only "
                    "JSON-serializable values (str, int, float, bool, list, dict, None). "
                    f"Serialization failed: {exc}. "
                    "To export without metadata, pass preserve_attrs=False."
                ) from exc
        else:
            df.attrs = {}

    kwargs: dict = {
        "engine": "pyarrow",
        "compression": None if compression == "none" else compression,
        "index": False,
    }
    if row_group_size is not None:
        kwargs["row_group_size"] = row_group_size

    df.to_parquet(path, **kwargs)
