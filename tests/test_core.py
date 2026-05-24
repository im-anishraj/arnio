import pytest
import sys
import importlib

def test_missing_cpp_extension_error_message(monkeypatch):
    """Ensure that a missing _arnio_cpp extension raises an ImportError with a helpful message."""
    try:
        import arnio
    except ImportError as e:
        # If arnio is already failing to import due to missing extension (like in local tests)
        error_msg = str(e)
    else:
        # If it is installed, we force it to fail
        monkeypatch.setitem(sys.modules, "arnio._arnio_cpp", None)
        monkeypatch.delitem(sys.modules, "arnio._core", raising=False)
        with pytest.raises(ImportError) as exc_info:
            importlib.import_module("arnio._core")
        error_msg = str(exc_info.value)

    assert "arnio C++ extension (_arnio_cpp) not found" in error_msg
    assert "pip install -e ." in error_msg
    assert "Desktop development with C++" in error_msg
    assert "gcc or clang" in error_msg
