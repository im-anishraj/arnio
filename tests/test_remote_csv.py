"""Tests for remote HTTP/HTTPS CSV input support in read_csv, scan_csv,
and read_csv_chunked.

All tests use a local http.server.HTTPServer in a background thread so CI
runs are deterministic and require no real network access.

Run with:
    pytest tests/test_remote_csv.py -v
"""

from __future__ import annotations

import http.server
import io
import os
import socket
import tempfile
import threading
import time
from unittest.mock import MagicMock, patch

import pytest

from arnio.exceptions import RemoteReadError
from arnio.io import (
    _CLOUD_SCHEME_HINTS,
    _fetch_url_to_tempfile,
    _materialize_csv_input,
)

# ---------------------------------------------------------------------------
# Skip guard — tests that call read_csv / scan_csv need the C++ extension
# ---------------------------------------------------------------------------

try:
    import arnio as ar

    _HAS_ARNIO = getattr(ar, "_arnio_cpp", None) is not None
except ImportError:
    _HAS_ARNIO = False

needs_arnio = pytest.mark.skipif(
    not _HAS_ARNIO,
    reason="arnio C++ extension not available",
)

# ---------------------------------------------------------------------------
# Local HTTP server fixture
# ---------------------------------------------------------------------------

_CSV_CONTENT = "name,age,score\nAlice,30,9.5\nBob,25,7.0\n"
_CSV_BYTES = _CSV_CONTENT.encode()


class _SingleFileHandler(http.server.BaseHTTPRequestHandler):
    """Serves one fixed CSV body for any GET; returns 404 for /missing."""

    csv_bytes: bytes = _CSV_BYTES

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/missing.csv":
            self.send_response(404)
            self.end_headers()
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/csv; charset=utf-8")
        self.send_header("Content-Length", str(len(self.csv_bytes)))
        self.end_headers()
        self.wfile.write(self.csv_bytes)

    def log_message(self, *args: object) -> None:  # silence server output
        pass


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def http_server():
    """Yield a running local HTTP server base URL for the test module."""
    port = _free_port()
    server = http.server.HTTPServer(("127.0.0.1", port), _SingleFileHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    # Give the server a moment to bind before tests run
    time.sleep(0.05)
    yield f"http://127.0.0.1:{port}"
    server.shutdown()


# ---------------------------------------------------------------------------
# _materialize_csv_input — URL routing unit tests (no C++ needed)
# ---------------------------------------------------------------------------


class TestMaterializeCsvInputUrlRouting:
    """Unit tests for the URL-detection layer in _materialize_csv_input."""

    def test_http_url_returns_temp_path_and_cleanup_flags(self, http_server):
        url = f"{http_server}/data.csv"
        path, should_cleanup, is_materialized = _materialize_csv_input(url)
        try:
            assert isinstance(path, str)
            assert os.path.exists(path)
            assert should_cleanup is True
            assert is_materialized is True
        finally:
            if should_cleanup and os.path.exists(path):
                os.unlink(path)

    def test_temp_file_contains_correct_csv_content(self, http_server):
        url = f"{http_server}/data.csv"
        path, should_cleanup, _ = _materialize_csv_input(url)
        try:
            content = open(path, encoding="utf-8").read()
            assert "name,age,score" in content
            assert "Alice" in content
        finally:
            if should_cleanup and os.path.exists(path):
                os.unlink(path)

    def test_local_path_string_passthrough_unchanged(self, tmp_path):
        p = tmp_path / "data.csv"
        p.write_text("a,b\n1,2\n")
        path, should_cleanup, _ = _materialize_csv_input(str(p))
        assert path == str(p)
        assert should_cleanup is False

    def test_pathlike_is_not_parsed_as_url(self, tmp_path):
        """os.PathLike objects bypass URL parsing — no false positives."""
        p = tmp_path / "data.csv"
        p.write_text("a,b\n1,2\n")
        path, should_cleanup, _ = _materialize_csv_input(p)
        assert should_cleanup is False

    def test_file_like_object_passthrough_unchanged(self):
        source = io.StringIO("col1,col2\n1,2\n")
        path, should_cleanup, _ = _materialize_csv_input(source)
        try:
            assert os.path.exists(path)
            assert should_cleanup is True
        finally:
            if should_cleanup and os.path.exists(path):
                os.unlink(path)

    def test_unsupported_type_raises_type_error(self):
        with pytest.raises(TypeError, match="filesystem path"):
            _materialize_csv_input(12345)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Cloud scheme rejection
# ---------------------------------------------------------------------------


class TestCloudSchemeRejection:
    """Unsupported cloud schemes must fail fast with actionable install hints."""

    @pytest.mark.parametrize("scheme", list(_CLOUD_SCHEME_HINTS.keys()))
    def test_cloud_scheme_raises_value_error(self, scheme):
        with pytest.raises(ValueError, match=scheme):
            _materialize_csv_input(f"{scheme}://bucket/data.csv")

    @pytest.mark.parametrize("scheme", list(_CLOUD_SCHEME_HINTS.keys()))
    def test_cloud_scheme_error_contains_pip_hint(self, scheme):
        with pytest.raises(ValueError, match="pip install"):
            _materialize_csv_input(f"{scheme}://bucket/data.csv")

    def test_s3_hint_references_s3_extra(self):
        with pytest.raises(ValueError, match=r"arnio\[s3\]"):
            _materialize_csv_input("s3://my-bucket/data.csv")

    def test_gs_hint_references_gcs_extra(self):
        with pytest.raises(ValueError, match=r"arnio\[gcs\]"):
            _materialize_csv_input("gs://my-bucket/data.csv")

    def test_az_hint_references_azure_extra(self):
        with pytest.raises(ValueError, match=r"arnio\[azure\]"):
            _materialize_csv_input("az://container/data.csv")

    def test_abfs_hint_references_azure_extra(self):
        with pytest.raises(ValueError, match=r"arnio\[azure\]"):
            _materialize_csv_input(
                "abfs://container@account.dfs.core.windows.net/data.csv"
            )


# ---------------------------------------------------------------------------
# _fetch_url_to_tempfile unit tests
# ---------------------------------------------------------------------------


class TestFetchUrlToTempfile:
    def test_returns_path_to_existing_file(self, http_server):
        url = f"{http_server}/data.csv"
        path = _fetch_url_to_tempfile(url)
        try:
            assert os.path.exists(path)
        finally:
            os.unlink(path)

    def test_file_contains_full_csv_body(self, http_server):
        url = f"{http_server}/data.csv"
        path = _fetch_url_to_tempfile(url)
        try:
            content = open(path, encoding="utf-8").read()
            assert content == _CSV_CONTENT
        finally:
            os.unlink(path)

    def test_404_raises_remote_read_error(self, http_server):
        url = f"{http_server}/missing.csv"
        with pytest.raises(RemoteReadError) as exc_info:
            _fetch_url_to_tempfile(url)
        assert exc_info.value.url == url
        assert exc_info.value.status_code == 404

    def test_404_error_message_includes_url(self, http_server):
        url = f"{http_server}/missing.csv"
        with pytest.raises(RemoteReadError, match="404"):
            _fetch_url_to_tempfile(url)

    def test_unreachable_host_raises_remote_read_error(self):
        url = "http://127.0.0.1:1"  # port 1 — always refused
        with pytest.raises(RemoteReadError) as exc_info:
            _fetch_url_to_tempfile(url)
        assert exc_info.value.url == url
        assert exc_info.value.status_code is None

    def test_no_temp_file_leaked_on_404(self, http_server, tmp_path):
        """Temp file must be deleted when the request fails."""
        created_paths: list[str] = []
        real_ntf = tempfile.NamedTemporaryFile

        def tracking_ntf(**kwargs):
            f = real_ntf(**kwargs)
            created_paths.append(f.name)
            return f

        url = f"{http_server}/missing.csv"
        with patch("arnio.io.tempfile.NamedTemporaryFile", side_effect=tracking_ntf):
            with pytest.raises(RemoteReadError):
                _fetch_url_to_tempfile(url)

        for p in created_paths:
            assert not os.path.exists(p), f"Temp file was leaked: {p}"

    def test_no_temp_file_leaked_on_connection_error(self):
        created_paths: list[str] = []
        real_ntf = tempfile.NamedTemporaryFile

        def tracking_ntf(**kwargs):
            f = real_ntf(**kwargs)
            created_paths.append(f.name)
            return f

        url = "http://127.0.0.1:1/data.csv"
        with patch("arnio.io.tempfile.NamedTemporaryFile", side_effect=tracking_ntf):
            with pytest.raises(RemoteReadError):
                _fetch_url_to_tempfile(url)

        for p in created_paths:
            assert not os.path.exists(p), f"Temp file was leaked: {p}"


class TestFetchUrlToTempfileIncrementalDecoding:
    """Regression tests for multi-byte UTF-8 characters split across read() chunks."""

    def test_multibyte_char_split_across_chunks_does_not_raise(self):
        """A valid multi-byte UTF-8 char split across two read() calls must not
        raise RemoteReadError.  The euro sign € is 3 bytes (\xe2\x82\xac);
        we split it so the first two bytes land in chunk 1 and the third in
        chunk 2, which would break a naive per-chunk decode."""
        euro_csv = "name,price\nCoffee,\u20ac2.50\n".encode()

        # Find the start of the 3-byte euro sign and split across it
        euro_pos = euro_csv.index(b"\xe2")
        chunk1 = euro_csv[: euro_pos + 2]  # \xe2 \x82  (first two bytes of €)
        chunk2 = euro_csv[euro_pos + 2 :]  # \xac ...    (last byte of € + rest)

        mock_response = MagicMock()
        mock_response.read.side_effect = [chunk1, chunk2, b""]
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("arnio.io.urllib.request.urlopen", return_value=mock_response):
            with patch("arnio.io.urllib.request.Request", return_value=MagicMock()):
                path = _fetch_url_to_tempfile("http://example.com/data.csv")
        try:
            content = open(path, encoding="utf-8").read()
            assert "\u20ac" in content, "Euro sign must survive the split-chunk decode"
            assert "Coffee" in content
        finally:
            os.unlink(path)

    def test_four_byte_char_split_across_chunks_does_not_raise(self):
        """Same split test with a 4-byte character (𝄞, U+1D11E, musical symbol G clef)
        to cover the full range of valid UTF-8 sequences."""
        gclef_csv = "col\n\U0001d11e\n".encode()

        # 4-byte sequence: split after byte 2
        gclef_pos = gclef_csv.index(b"\xf0")
        chunk1 = gclef_csv[: gclef_pos + 2]
        chunk2 = gclef_csv[gclef_pos + 2 :]

        mock_response = MagicMock()
        mock_response.read.side_effect = [chunk1, chunk2, b""]
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("arnio.io.urllib.request.urlopen", return_value=mock_response):
            with patch("arnio.io.urllib.request.Request", return_value=MagicMock()):
                path = _fetch_url_to_tempfile("http://example.com/data.csv")
        try:
            content = open(path, encoding="utf-8").read()
            assert "\U0001d11e" in content
        finally:
            os.unlink(path)

    def test_genuinely_invalid_utf8_still_raises_remote_read_error(self):
        """Invalid UTF-8 bytes must still raise RemoteReadError, not pass through."""
        bad_bytes = b"col\n\xff\xfe\n"  # \xff is never valid UTF-8

        mock_response = MagicMock()
        mock_response.read.side_effect = [bad_bytes, b""]
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("arnio.io.urllib.request.urlopen", return_value=mock_response):
            with patch("arnio.io.urllib.request.Request", return_value=MagicMock()):
                with pytest.raises(RemoteReadError, match="not valid UTF-8"):
                    _fetch_url_to_tempfile("http://example.com/data.csv")


# ---------------------------------------------------------------------------
# RemoteReadError attributes
# ---------------------------------------------------------------------------


class TestRemoteReadError:
    def test_url_attribute_is_stored(self, http_server):
        url = f"{http_server}/missing.csv"
        with pytest.raises(RemoteReadError) as exc_info:
            _fetch_url_to_tempfile(url)
        assert exc_info.value.url == url

    def test_status_code_stored_on_http_error(self, http_server):
        url = f"{http_server}/missing.csv"
        with pytest.raises(RemoteReadError) as exc_info:
            _fetch_url_to_tempfile(url)
        assert exc_info.value.status_code == 404

    def test_status_code_none_on_network_error(self):
        url = "http://127.0.0.1:1/data.csv"
        with pytest.raises(RemoteReadError) as exc_info:
            _fetch_url_to_tempfile(url)
        assert exc_info.value.status_code is None

    def test_is_subclass_of_arnio_error(self):
        from arnio.exceptions import ArnioError

        err = RemoteReadError("test", url="http://x.example/a.csv", status_code=500)
        assert isinstance(err, ArnioError)

    def test_importable_from_arnio_top_level(self):
        from arnio import RemoteReadError as RRE  # noqa: F401

        assert RRE is RemoteReadError


# ---------------------------------------------------------------------------
# read_csv + scan_csv integration (requires C++ extension)
# ---------------------------------------------------------------------------


@needs_arnio
class TestReadCsvHttpUrl:
    def test_read_csv_returns_arframe(self, http_server):
        url = f"{http_server}/data.csv"
        frame = ar.read_csv(url)
        assert isinstance(frame, ar.ArFrame)

    def test_read_csv_correct_shape(self, http_server):
        url = f"{http_server}/data.csv"
        frame = ar.read_csv(url)
        assert frame.shape == (2, 3)

    def test_read_csv_correct_columns(self, http_server):
        url = f"{http_server}/data.csv"
        frame = ar.read_csv(url)
        assert list(frame.columns) == ["name", "age", "score"]

    def test_read_csv_correct_values(self, http_server):

        url = f"{http_server}/data.csv"
        frame = ar.read_csv(url)
        df = ar.to_pandas(frame)
        assert df["name"].tolist() == ["Alice", "Bob"]
        assert df["age"].tolist() == [30, 25]

    def test_read_csv_url_404_raises_remote_read_error(self, http_server):
        url = f"{http_server}/missing.csv"
        with pytest.raises(RemoteReadError):
            ar.read_csv(url)

    def test_read_csv_url_unreachable_raises_remote_read_error(self):
        with pytest.raises(RemoteReadError):
            ar.read_csv("http://127.0.0.1:1/data.csv")

    def test_read_csv_local_path_still_works(self, tmp_path):
        """Regression: existing local path behavior must be unchanged."""
        p = tmp_path / "data.csv"
        p.write_text("x,y\n1,2\n3,4\n")
        frame = ar.read_csv(str(p))
        assert frame.shape == (2, 2)

    def test_read_csv_file_like_still_works(self):
        """Regression: existing file-like object path must be unchanged."""
        source = io.StringIO("a,b\n10,20\n30,40\n")
        frame = ar.read_csv(source)
        assert frame.shape == (2, 2)


@needs_arnio
class TestScanCsvHttpUrl:
    def test_scan_csv_returns_schema_dict(self, http_server):
        url = f"{http_server}/data.csv"
        schema = ar.scan_csv(url)
        assert isinstance(schema, dict)

    def test_scan_csv_infers_correct_column_names(self, http_server):
        url = f"{http_server}/data.csv"
        schema = ar.scan_csv(url)
        assert set(schema.keys()) == {"name", "age", "score"}

    def test_scan_csv_infers_correct_dtypes(self, http_server):
        url = f"{http_server}/data.csv"
        schema = ar.scan_csv(url)
        assert schema["name"] == "string"
        assert schema["age"] == "int64"
        assert schema["score"] == "float64"

    def test_scan_csv_url_404_raises_remote_read_error(self, http_server):
        url = f"{http_server}/missing.csv"
        with pytest.raises(RemoteReadError):
            ar.scan_csv(url)


@needs_arnio
class TestReadCsvChunkedHttpUrl:
    def test_read_csv_chunked_yields_frames(self, http_server):
        url = f"{http_server}/data.csv"
        chunks = list(ar.read_csv_chunked(url, chunksize=1))
        assert len(chunks) >= 1
        for chunk in chunks:
            assert isinstance(chunk, ar.ArFrame)

    def test_read_csv_chunked_total_rows(self, http_server):
        url = f"{http_server}/data.csv"
        chunks = list(ar.read_csv_chunked(url, chunksize=1))
        total = sum(c.shape[0] for c in chunks)
        assert total == 2

    def test_read_csv_chunked_url_404_raises_remote_read_error(self, http_server):
        url = f"{http_server}/missing.csv"
        with pytest.raises(RemoteReadError):
            list(ar.read_csv_chunked(url))


# ---------------------------------------------------------------------------
# Cloud scheme rejection via public API (requires C++ extension for read_csv
# but the ValueError is raised in Python before C++ is reached)
# ---------------------------------------------------------------------------

# All five planned cloud schemes must be covered.
_ALL_CLOUD_SCHEMES = ["s3", "gs", "az", "abfs", "abfss"]


class TestCloudSchemeRejectionPublicApi:
    """Public API functions must reject cloud schemes with actionable errors.

    These tests call ar.read_csv / ar.scan_csv / ar.read_csv_chunked directly
    (not the internal _materialize_csv_input helper) so a regression in the
    Python-before-C++ guard is caught regardless of where the hook lives.
    The ValueError is raised before the C++ extension is invoked, so no
    compiled extension is required for these tests to run.
    """

    @pytest.mark.parametrize("scheme", _ALL_CLOUD_SCHEMES)
    def test_read_csv_raises_value_error_for_cloud_scheme(self, scheme):
        with pytest.raises(ValueError, match="pip install"):
            ar.read_csv(f"{scheme}://bucket/file.csv")

    @pytest.mark.parametrize("scheme", _ALL_CLOUD_SCHEMES)
    def test_read_csv_error_contains_scheme_name(self, scheme):
        with pytest.raises(ValueError, match=scheme):
            ar.read_csv(f"{scheme}://bucket/file.csv")

    @pytest.mark.parametrize("scheme", _ALL_CLOUD_SCHEMES)
    def test_scan_csv_raises_value_error_for_cloud_scheme(self, scheme):
        with pytest.raises(ValueError, match="pip install"):
            ar.scan_csv(f"{scheme}://bucket/file.csv")

    @pytest.mark.parametrize("scheme", _ALL_CLOUD_SCHEMES)
    def test_scan_csv_error_contains_scheme_name(self, scheme):
        with pytest.raises(ValueError, match=scheme):
            ar.scan_csv(f"{scheme}://bucket/file.csv")

    @pytest.mark.parametrize("scheme", _ALL_CLOUD_SCHEMES)
    def test_read_csv_chunked_raises_value_error_for_cloud_scheme(self, scheme):
        # Must iterate the generator to trigger the guard.
        with pytest.raises(ValueError, match="pip install"):
            next(iter(ar.read_csv_chunked(f"{scheme}://bucket/file.csv")))

    @pytest.mark.parametrize("scheme", _ALL_CLOUD_SCHEMES)
    def test_read_csv_chunked_error_contains_scheme_name(self, scheme):
        with pytest.raises(ValueError, match=scheme):
            next(iter(ar.read_csv_chunked(f"{scheme}://bucket/file.csv")))


class TestRemoteCsvLimits:
    """Tests for early stream termination and size limits on remote files."""

    def test_size_limit_raises_error(self):
        """Verify that a response exceeding max_response_size raises RemoteReadError."""
        mock_response = MagicMock()
        mock_response.read.side_effect = [b"1,2\n", b"3,4\n", b""]
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("arnio.io.urllib.request.urlopen", return_value=mock_response):
            with patch("arnio.io.urllib.request.Request", return_value=MagicMock()):
                # Set limit to 2 bytes, but chunk is 4 bytes
                with pytest.raises(RemoteReadError, match="size exceeded limit"):
                    _fetch_url_to_tempfile("http://example.com/data.csv", max_response_size=2)

    def test_row_limit_stops_reading_early(self):
        """Verify that streaming stops early once limit_rows is satisfied."""
        # We simulate a response with 5 chunks, but limit_rows=2 should stop after chunk 2
        mock_response = MagicMock()
        mock_response.read.side_effect = [b"a,b\n", b"1,2\n", b"3,4\n", b"5,6\n", b""]
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("arnio.io.urllib.request.urlopen", return_value=mock_response):
            with patch("arnio.io.urllib.request.Request", return_value=MagicMock()):
                # limit_rows = 2 (header + 1 data row)
                path = _fetch_url_to_tempfile("http://example.com/data.csv", limit_rows=2)
                try:
                    content = open(path, encoding="utf-8").read()
                    assert "a,b" in content
                    assert "1,2" in content
                    # Should NOT have downloaded later chunks
                    assert "3,4" not in content
                    # read() should have been called only twice
                    assert mock_response.read.call_count <= 3
                finally:
                    os.unlink(path)
