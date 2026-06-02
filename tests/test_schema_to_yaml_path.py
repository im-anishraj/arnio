"""Tests for schema_to_yaml(..., path=...) output-path validation.

Covers:
- valid file path (str) writes and returns YAML
- valid pathlib.Path writes and returns YAML
- valid os.PathLike writes and returns YAML
- parent directory creation for nested paths
- empty string path raises ValueError
- whitespace-only string path raises ValueError
- existing directory path raises ValueError
- non-string / non-PathLike types raise TypeError

Fixes #1674
"""

import os
import pathlib

import pytest

import arnio as ar

_SCHEMA = {"id": "int64", "name": "string"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _CustomPathLike(os.PathLike):
    """Minimal os.PathLike implementation that is NOT a pathlib.Path."""

    def __init__(self, path: str) -> None:
        self._path = path

    def __fspath__(self) -> str:
        return self._path


# ---------------------------------------------------------------------------
# Valid path behavior
# ---------------------------------------------------------------------------


class TestSchemaToYamlValidPaths:
    def test_str_path_writes_file(self, tmp_path):
        out = str(tmp_path / "schema.yaml")
        result = ar.schema_to_yaml(_SCHEMA, path=out)
        assert pathlib.Path(out).exists()
        assert pathlib.Path(out).read_text(encoding="utf-8") == result

    def test_pathlib_path_writes_file(self, tmp_path):
        out = tmp_path / "schema.yaml"
        result = ar.schema_to_yaml(_SCHEMA, path=out)
        assert out.exists()
        assert out.read_text(encoding="utf-8") == result

    def test_os_pathlike_writes_file(self, tmp_path):
        out = _CustomPathLike(str(tmp_path / "schema.yaml"))
        result = ar.schema_to_yaml(_SCHEMA, path=out)
        assert pathlib.Path(os.fspath(out)).exists()
        assert pathlib.Path(os.fspath(out)).read_text(encoding="utf-8") == result

    def test_yaml_string_always_returned(self, tmp_path):
        out = tmp_path / "schema.yaml"
        result = ar.schema_to_yaml(_SCHEMA, path=out)
        assert isinstance(result, str)
        assert result.endswith("\n")

    def test_parent_dirs_created(self, tmp_path):
        out = tmp_path / "a" / "b" / "c" / "schema.yaml"
        ar.schema_to_yaml(_SCHEMA, path=out)
        assert out.exists()

    def test_no_path_returns_yaml_string(self):
        result = ar.schema_to_yaml(_SCHEMA)
        assert isinstance(result, str)
        assert "id" in result

    def test_existing_file_overwritten(self, tmp_path):
        out = tmp_path / "schema.yaml"
        out.write_text("old content", encoding="utf-8")
        ar.schema_to_yaml(_SCHEMA, path=out)
        assert out.read_text(encoding="utf-8") != "old content"


# ---------------------------------------------------------------------------
# Invalid path — TypeError
# ---------------------------------------------------------------------------


class TestSchemaToYamlPathTypeErrors:
    @pytest.mark.parametrize(
        "bad_path",
        [
            123,
            True,
            False,
            3.14,
            ["schema.yaml"],
            {"path": "schema.yaml"},
            object(),
        ],
    )
    def test_non_string_non_pathlike_raises_type_error(self, bad_path):
        with pytest.raises(TypeError, match="path must be a string or os.PathLike"):
            ar.schema_to_yaml(_SCHEMA, path=bad_path)


# ---------------------------------------------------------------------------
# Invalid path — ValueError (empty)
# ---------------------------------------------------------------------------


class TestSchemaToYamlEmptyPath:
    def test_empty_string_raises(self):
        with pytest.raises(ValueError, match="path must not be empty"):
            ar.schema_to_yaml(_SCHEMA, path="")

    def test_whitespace_only_string_raises(self):
        with pytest.raises(ValueError, match="path must not be empty"):
            ar.schema_to_yaml(_SCHEMA, path="   ")

    def test_tab_only_string_raises(self):
        with pytest.raises(ValueError, match="path must not be empty"):
            ar.schema_to_yaml(_SCHEMA, path="\t")


# ---------------------------------------------------------------------------
# Invalid path — ValueError (directory)
# ---------------------------------------------------------------------------


class TestSchemaToYamlDirectoryPath:
    def test_dot_raises(self, tmp_path):
        with pytest.raises(
            ValueError, match="path must point to a file, not a directory"
        ):
            ar.schema_to_yaml(_SCHEMA, path=".")

    def test_existing_dir_raises(self, tmp_path):
        with pytest.raises(
            ValueError, match="path must point to a file, not a directory"
        ):
            ar.schema_to_yaml(_SCHEMA, path=str(tmp_path))

    def test_existing_dir_as_pathlib_raises(self, tmp_path):
        with pytest.raises(
            ValueError, match="path must point to a file, not a directory"
        ):
            ar.schema_to_yaml(_SCHEMA, path=tmp_path)
