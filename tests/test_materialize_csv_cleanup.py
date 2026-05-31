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


class _FailOnReadStream:
    """A file-like that raises on read() to trigger the except path."""
    def read(self, size=-1):
        raise OSError("simulated read failure")


class TestMaterializeCsvCleanup:

    def test_unlink_runs_even_when_close_raises(self, tmp_path):
        unlinked = []
        real_ntf = tempfile.NamedTemporaryFile

        def patched_ntf(**kwargs):
            handle = real_ntf(**kwargs)
            original_close = handle.close
            call_count = [0]

            def flaky_close():
                call_count[0] += 1
                if call_count[0] == 1:
                    raise OSError("simulated flush error on close")
                original_close()

            handle.close = flaky_close
            return handle

        def tracking_unlink(path):
            unlinked.append(path)
            os.unlink(path)

        source = _FailOnReadStream()

        with patch("arnio.io.tempfile.NamedTemporaryFile", side_effect=patched_ntf), \
             patch("arnio.io.os.unlink", side_effect=tracking_unlink):
            with pytest.raises(OSError, match="simulated read failure"):
                _materialize_csv_input(source)

        assert unlinked, "os.unlink was never called — temp file was leaked"

    def test_original_exception_is_reraised(self):
        source = _FailOnReadStream()
        with pytest.raises(OSError, match="simulated read failure"):
            _materialize_csv_input(source)

    def test_unlink_failure_does_not_mask_original_exception(self, tmp_path):
        real_ntf = tempfile.NamedTemporaryFile

        def patched_ntf(**kwargs):
            handle = real_ntf(**kwargs)
            handle.close = lambda: (_ for _ in ()).throw(OSError("close error"))
            return handle

        source = _FailOnReadStream()

        with patch("arnio.io.tempfile.NamedTemporaryFile", side_effect=patched_ntf), \
             patch("arnio.io.os.unlink", side_effect=OSError("unlink error")):
            with pytest.raises(OSError, match="simulated read failure"):
                _materialize_csv_input(source)

    def test_normal_path_still_works(self):
        source = io.StringIO("col1,col2\n1,2\n3,4\n")
        path, created, should_delete = _materialize_csv_input(source)
        try:
            assert isinstance(path, str)
            assert os.path.exists(path)
            assert created is True
            assert should_delete is True
        finally:
            os.unlink(path)

    def test_no_temp_file_for_path_input(self, tmp_path):
        p = tmp_path / "data.csv"
        p.write_text("a,b\n1,2\n")
        path, created, _ = _materialize_csv_input(str(p))
        assert path == str(p)
        assert created is False
