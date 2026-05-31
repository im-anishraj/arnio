import importlib
import importlib.util
import pathlib
import sys

import pytest


def test_missing_cpp_extension_error_message(monkeypatch):
    """Ensure that a missing _arnio_cpp extension raises an ImportError with a helpful message."""
    try:
        import arnio  # noqa: F401
    except ImportError as e:
        error_msg = str(e)
    else:
        monkeypatch.setitem(sys.modules, "arnio._arnio_cpp", None)
        monkeypatch.delitem(sys.modules, "arnio._core", raising=False)
        with pytest.raises(ImportError) as exc_info:
            importlib.import_module("arnio._core")
        error_msg = str(exc_info.value)

    assert "arnio C++ extension (_arnio_cpp) not found" in error_msg
    assert "pip install -e ." in error_msg
    assert "Desktop development with C++" in error_msg
    assert "gcc or clang" in error_msg


# ---------------------------------------------------------------------------
# Regression tests for issue #1892:
# __version__ must reflect the source checkout, not a stale installed dist.
# ---------------------------------------------------------------------------


def test_version_is_string():
    """arnio.__version__ must always be a non-empty string."""
    import arnio

    assert isinstance(arnio.__version__, str)
    assert len(arnio.__version__) > 0


def test_version_not_unknown_on_installed_package():
    """In a normal test environment (package installed) version must not be 'unknown'."""
    import arnio

    assert (
        arnio.__version__ != "unknown"
    ), "__version__ fell through to 'unknown' even though arnio is installed"


def _load_version_module(tmp_path: pathlib.Path) -> object:
    """Copy arnio/_version.py into tmp_path/arnio/ and load it as a standalone module.

    _version.py uses Path(__file__).resolve().parent.parent to locate pyproject.toml,
    so the file must sit one level below tmp_path (tmp_path/arnio/_version.py) so
    that _here.parent == tmp_path, matching where the test places pyproject.toml.
    """
    real_version = pathlib.Path(__file__).parent.parent / "arnio" / "_version.py"
    src = real_version.read_text(encoding="utf-8")
    pkg_dir = tmp_path / "arnio"
    pkg_dir.mkdir()
    version_file = pkg_dir / "_version.py"
    version_file.write_text(src, encoding="utf-8")

    spec = importlib.util.spec_from_file_location(
        "_arnio_version_isolated", version_file
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_version_reads_pyproject_in_source_checkout(tmp_path):
    """When pyproject.toml sits next to the package dir, its version is used."""
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "arnio"\nversion = "9.9.9"\n', encoding="utf-8"
    )

    mod = _load_version_module(tmp_path)

    assert (
        mod.__version__ == "9.9.9"
    ), f"Expected '9.9.9' from pyproject.toml, got {mod.__version__!r}"


def test_version_fallback_unknown_when_no_pyproject_and_no_metadata(
    tmp_path, monkeypatch
):
    """When neither pyproject.toml nor metadata is available, fall back to 'unknown'."""
    import importlib.metadata

    monkeypatch.setattr(
        importlib.metadata,
        "version",
        lambda name: (_ for _ in ()).throw(
            importlib.metadata.PackageNotFoundError(name)
        ),
    )

    mod = _load_version_module(tmp_path)

    assert mod.__version__ == "unknown", f"Expected 'unknown', got {mod.__version__!r}"
