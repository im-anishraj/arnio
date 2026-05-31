"""
Regression tests for the temp-file cleanup path in _materialize_csv_input.

Fixes #2194: when tmp.close() raises during exception cleanup, os.unlink
must still run so the temp file is not leaked on disk.
"""

import io
import os
import tempfile
from unittest.mock import patch

import pytest

from arnio.io import _materialize_csv_input

# Capture the real os.unlink once at module level so no test can accidentally
# capture a patched version via a delayed assignment.
_REAL_UNLINK = os.unlink


class _FailOnReadStream:
    """A file-like that raises on read() to trigger the except path."""

    def read(self, size=-1):
        raise OSError("simulated read failure")


class _FailAfterFirstChunkStream:
    """A file-like that returns one chunk then raises, so write() is called."""

    def __init__(self):
        self._calls = 0

    def read(self, size=-1):
        self._calls += 1
        if self._calls == 1:
            return "col1,col2\n"
        raise OSError("simulated mid-read failure")


class _FakeTmp:
    """
    Lightweight fake NamedTemporaryFile whose close() raises OSError.
    Used to verify that os.unlink() is still called even when close() fails.
    """

    def __init__(self, suffix=".csv", **kwargs):
        self._real = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        self.name = self._real.name

    def write(self, data):
        self._real.write(data)

    def close(self):
        self._real.close()
        raise OSError("simulated flush error on close")


def _make_tracking_unlink():
    """Return (tracking_unlink, unlinked_list) pair using the real unlink."""
    unlinked = []

    def tracking_unlink(path):
        unlinked.append(path)
        try:
            _REAL_UNLINK(path)
        except OSError:
            pass

    return tracking_unlink, unlinked


class TestMaterializeCsvCleanup:
    def test_unlink_called_on_read_failure(self):
        """os.unlink must be called when read() raises, so no temp file is leaked."""
        tracking_unlink, unlinked = _make_tracking_unlink()
        source = _FailOnReadStream()

        with patch("arnio.io.os.unlink", side_effect=tracking_unlink):
            with pytest.raises(OSError, match="simulated read failure"):
                _materialize_csv_input(source)

        assert unlinked, "os.unlink was never called — temp file was leaked"

    def test_unlink_called_on_mid_read_failure(self):
        """os.unlink must be called even when failure occurs after partial write."""
        tracking_unlink, unlinked = _make_tracking_unlink()
        source = _FailAfterFirstChunkStream()

        with patch("arnio.io.os.unlink", side_effect=tracking_unlink):
            with pytest.raises(OSError, match="simulated mid-read failure"):
                _materialize_csv_input(source)

        assert unlinked, "os.unlink was never called — temp file was leaked"

    def test_unlink_runs_when_close_raises_on_cleanup(self):
        """
        Core regression for #2194: if tmp.close() raises during exception
        cleanup, os.unlink() must still be called so the file is not leaked.
        """
        tracking_unlink, unlinked = _make_tracking_unlink()
        source = _FailOnReadStream()

        with (
            patch("arnio.io.tempfile.NamedTemporaryFile", side_effect=_FakeTmp),
            patch("arnio.io.os.unlink", side_effect=tracking_unlink),
        ):
            with pytest.raises(OSError, match="simulated read failure"):
                _materialize_csv_input(source)

        assert unlinked, "os.unlink was never called — temp file was leaked"

    def test_original_exception_is_reraised(self):
        """The cleanup path must re-raise the original exception, not swallow it."""
        source = _FailOnReadStream()
        with pytest.raises(OSError, match="simulated read failure"):
            _materialize_csv_input(source)

    def test_original_exception_reraised_even_when_unlink_fails(self):
        """If unlink() also raises during cleanup, the original exception propagates."""
        source = _FailOnReadStream()
        with patch("arnio.io.os.unlink", side_effect=OSError("unlink error")):
            with pytest.raises(OSError, match="simulated read failure"):
                _materialize_csv_input(source)

    def test_normal_path_still_works(self):
        """Regression: the happy path must still return a valid temp file path."""
        source = io.StringIO("col1,col2\n1,2\n3,4\n")
        path, created, should_delete = _materialize_csv_input(source)
        try:
            assert isinstance(path, str)
            assert os.path.exists(path)
            assert created is True
            assert should_delete is True
        finally:
            try:
                _REAL_UNLINK(path)
            except OSError:
                pass

    def test_no_temp_file_for_path_input(self, tmp_path):
        """A plain file path must pass through without creating a temp file."""
        p = tmp_path / "data.csv"
        p.write_text("a,b\n1,2\n")
        path, created, _ = _materialize_csv_input(str(p))
        assert path == str(p)
        assert created is False
