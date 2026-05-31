"""
Regression tests for the temp-file cleanup path in _materialize_csv_input.

Fixes #2194: when tmp.close() raises during exception cleanup, os.unlink
must still run so the temp file is not leaked on disk.
"""

import io
import os
import tempfile
from unittest.mock import patch, call

import pytest

from arnio.io import _materialize_csv_input


class _FailOnReadStream:
    """A file-like that raises on read() to trigger the except path."""
    def read(self, size=-1):
        raise OSError("simulated read failure")


class TestMaterializeCsvCleanup:

    def test_unlink_runs_even_when_close_raises(self):
        """
        If tmp.close() raises in the cleanup path, os.unlink must still be
        called so the temp file is not leaked.
        """
        unlinked = []

        # Track which temp file gets created so we can assert unlink was called on it
        created_tmp_name = []
        real_ntf = tempfile.NamedTemporaryFile

        def patched_ntf(**kwargs):
            handle = real_ntf(**kwargs)
            created_tmp_name.append(handle.name)
            return handle

        close_call_count = [0]
        real_close = None

        def patched_close(self_handle):
            close_call_count[0] += 1
            if close_call_count[0] == 1:
                # First call is the cleanup call — raise to simulate flush error
                raise OSError("simulated flush error on close")
            # Subsequent calls (if any) succeed
            real_close(self_handle)

        def tracking_unlink(path):
            unlinked.append(path)
            # Actually delete so we don't leave files behind
            try:
                os.unlink(path)
            except OSError:
                pass

        source = _FailOnReadStream()

        with (
            patch("arnio.io.tempfile.NamedTemporaryFile", side_effect=patched_ntf),
            patch("arnio.io.os.unlink", side_effect=tracking_unlink),
            patch(
                "arnio.io.tempfile.NamedTemporaryFile.close",
                side_effect=OSError("simulated flush error on close"),
                autospec=False,
            ),
        ):
            with pytest.raises(OSError, match="simulated read failure"):
                _materialize_csv_input(source)

        assert unlinked, "os.unlink was never called — temp file was leaked"

    def test_original_exception_is_reraised(self):
        """The cleanup path must re-raise the original exception."""
        source = _FailOnReadStream()
        with pytest.raises(OSError, match="simulated read failure"):
            _materialize_csv_input(source)

    def test_unlink_failure_does_not_mask_original_exception(self):
        """If unlink() also raises during cleanup, the original exception propagates."""
        source = _FailOnReadStream()
        with (
            patch("arnio.io.os.unlink", side_effect=OSError("unlink error")),
            patch(
                "arnio.io.tempfile.NamedTemporaryFile.close",
                side_effect=OSError("close error"),
                autospec=False,
            ),
        ):
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
                os.unlink(path)
            except OSError:
                pass

    def test_no_temp_file_for_path_input(self, tmp_path):
        """A plain file path must pass through without creating a temp file."""
        p = tmp_path / "data.csv"
        p.write_text("a,b\n1,2\n")
        path, created, _ = _materialize_csv_input(str(p))
        assert path == str(p)
        assert created is False
