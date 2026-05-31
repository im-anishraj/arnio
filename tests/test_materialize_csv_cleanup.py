"""
Regression tests for the temp-file cleanup path in _materialize_csv_input.

Fixes #2194: when tmp.close() raises during exception cleanup, os.unlink
must still run so the temp file is not leaked on disk.
"""

import io
import os
from unittest.mock import patch

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
        real_unlink = os.unlink  # capture before patching to avoid recursion
        unlinked = []

        def tracking_unlink(path):
            unlinked.append(path)
            try:
                real_unlink(path)
            except OSError:
                pass

        source = _FailOnReadStream()

        with (
            patch(
                "arnio.io.tempfile.NamedTemporaryFile.close",
                side_effect=OSError("simulated flush error on close"),
            ),
            patch("arnio.io.os.unlink", side_effect=tracking_unlink),
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
            patch(
                "arnio.io.tempfile.NamedTemporaryFile.close",
                side_effect=OSError("close error"),
            ),
            patch("arnio.io.os.unlink", side_effect=OSError("unlink error")),
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
