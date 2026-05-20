"""Standalone tests for _validate_bool_option in arnio/io.py."""

import sys
import types
import pytest
import importlib.util
import pathlib

# Create fake arnio package and submodules to satisfy relative imports
arnio_pkg = types.ModuleType("arnio")
arnio_pkg.__path__ = []
sys.modules["arnio"] = arnio_pkg

core = types.ModuleType("arnio._core")
core._CsvConfig = object
core._CsvReader = object
core._CsvWriter = object
core._CsvWriteConfig = object
core._CsvChunkReader = object
sys.modules["arnio._core"] = core

exceptions = types.ModuleType("arnio.exceptions")
exceptions.CsvReadError = Exception
exceptions.JsonlReadError = Exception
sys.modules["arnio.exceptions"] = exceptions

frame_mod = types.ModuleType("arnio.frame")
frame_mod.ArFrame = object
sys.modules["arnio.frame"] = frame_mod

spec = importlib.util.spec_from_file_location(
    "arnio.io",
    pathlib.Path(__file__).parent.parent / "arnio" / "io.py",
    submodule_search_locations=[],
)
mod = importlib.util.module_from_spec(spec)
mod.__package__ = "arnio"
spec.loader.exec_module(mod)

_validate_bool_option = mod._validate_bool_option


class TestValidateBoolOption:

    def test_true_accepted(self):
        assert _validate_bool_option(True, "has_header") is True

    def test_false_accepted(self):
        assert _validate_bool_option(False, "has_header") is False

    def test_none_rejected(self):
        with pytest.raises(TypeError, match="has_header"):
            _validate_bool_option(None, "has_header")

    def test_int_zero_rejected(self):
        with pytest.raises(TypeError, match="write_header"):
            _validate_bool_option(0, "write_header")

    def test_int_one_rejected(self):
        with pytest.raises(TypeError, match="trim_headers"):
            _validate_bool_option(1, "trim_headers")

    def test_string_rejected(self):
        with pytest.raises(TypeError, match="has_header"):
            _validate_bool_option("true", "has_header")

    def test_error_message_names_parameter(self):
        with pytest.raises(TypeError, match="write_header"):
            _validate_bool_option(None, "write_header")
