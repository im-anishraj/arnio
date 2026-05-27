"""tests/test_schema_export.py unit tests for arnio.schema_export.

Covers:
- basic dict schema (scan_csv style)
- schema object with .fields attribute
- empty schema
- optional / nullable fields
- nested metadata dicts
- file write (path= argument)
- determinism across multiple calls
- unsupported type raises TypeError
- all scalar edge-cases (bool, None, float specials, strings needing quotes)
"""

from __future__ import annotations

import pathlib

import pytest

import arnio as ar
from arnio.schema_export import schema_to_dict, schema_to_yaml


class _FakeField:
    """Minimal stand-in for a future arnio Field object."""

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


class _FakeSchema:
    """Minimal stand-in for a future arnio Schema object."""

    def __init__(self, fields: dict):
        self.fields = fields


class TestSchemaToDict:
    def test_flat_string_dict(self):
        raw = {"id": "INT64", "name": "STRING", "score": "FLOAT64"}
        result = schema_to_dict(raw)
        assert result == {
            "fields": {
                "id": {"type": "INT64"},
                "name": {"type": "STRING"},
                "score": {"type": "FLOAT64"},
            }
        }

    def test_nested_dict_preserved(self):
        raw = {
            "age": {"type": "INT64", "nullable": True, "min": 0},
        }
        result = schema_to_dict(raw)
        assert result["fields"]["age"] == {"min": 0, "nullable": True, "type": "INT64"}

    def test_empty_schema(self):
        assert schema_to_dict({}) == {"fields": {}}

    def test_field_keys_sorted(self):
        raw = {"z_col": "BOOL", "a_col": "STRING", "m_col": "INT64"}
        keys = list(schema_to_dict(raw)["fields"].keys())
        assert keys == sorted(keys)

    def test_schema_object_with_fields_attr(self):
        schema = _FakeSchema({"price": _FakeField(type="FLOAT64", nullable=False)})
        result = schema_to_dict(schema)
        assert result["fields"]["price"]["type"] == "FLOAT64"
        assert result["fields"]["price"]["nullable"] is False

    def test_schema_object_dict_fields(self):
        schema = _FakeSchema({"val": {"type": "INT64", "default": None}})
        result = schema_to_dict(schema)
        assert result["fields"]["val"]["default"] is None

    def test_unsupported_type_raises(self):
        with pytest.raises(TypeError, match="Expected a dict"):
            schema_to_dict(42)


class TestSchemaToYamlOutput:
    def test_basic_output(self):
        raw = {"id": "INT64", "name": "STRING"}
        out = schema_to_yaml(raw)
        assert "fields:" in out
        assert "id:" in out
        assert "type: INT64" in out
        assert "type: STRING" in out

    def test_ends_with_newline(self):
        assert schema_to_yaml({"x": "BOOL"}).endswith("\n")

    def test_empty_schema_yaml(self):
        out = schema_to_yaml({})
        assert "fields: {}" in out

    def test_deterministic_repeated_calls(self):
        raw = {"z": "INT64", "a": "FLOAT64", "m": "BOOL"}
        assert schema_to_yaml(raw) == schema_to_yaml(raw)

    def test_nullable_field_present(self):
        raw = {"col": {"type": "STRING", "nullable": True}}
        out = schema_to_yaml(raw)
        assert "nullable: true" in out

    def test_none_value(self):
        raw = {"col": {"type": "STRING", "default": None}}
        out = schema_to_yaml(raw)
        assert "default: null" in out

    def test_numeric_constraints(self):
        raw = {"age": {"type": "INT64", "min": 0, "max": 150}}
        out = schema_to_yaml(raw)
        assert "min: 0" in out
        assert "max: 150" in out

    def test_bool_false(self):
        raw = {"flag": {"type": "BOOL", "nullable": False}}
        out = schema_to_yaml(raw)
        assert "nullable: false" in out

    def test_string_needing_quotes(self):
        # value contains a colon → must be quoted
        raw = {"label": {"type": "STRING", "description": "key: value"}}
        out = schema_to_yaml(raw)
        assert '"key: value"' in out

    def test_empty_string_quoted(self):
        raw = {"col": {"type": "STRING", "default": ""}}
        out = schema_to_yaml(raw)
        assert '""' in out

    def test_list_of_allowed_values(self):
        raw = {"status": {"type": "STRING", "allowed": ["active", "inactive"]}}
        out = schema_to_yaml(raw)
        assert "- active" in out
        assert "- inactive" in out

    def test_unsupported_value_type_raises(self):
        # Inject an unsupported type deep in the dict.
        raw = {"col": {"type": object()}}  # object() isnt a supported scalar
        with pytest.raises(TypeError):
            schema_to_yaml(raw)

    def test_float_specials(self):

        raw = {"col": {"type": "FLOAT64", "min": float("inf"), "nan_ex": float("nan")}}
        out = schema_to_yaml(raw)
        assert ".inf" in out
        assert ".nan" in out

    def test_schema_object(self):
        schema = _FakeSchema({"ts": _FakeField(type="TIMESTAMP", nullable=True)})
        out = schema_to_yaml(schema)
        assert "ts:" in out
        assert "TIMESTAMP" in out

    def test_emit_scalar_prevents_yaml_injection(self):
        # test \n
        raw1 = {"key": {"type": "STRING", "description": "safe\nmalicious_key: true"}}
        out1 = schema_to_yaml(raw1)
        assert '"safe\\nmalicious_key: true"' in out1

        # test \r
        raw2 = {"key": {"type": "STRING", "description": "safe\rmalicious_key: true"}}
        out2 = schema_to_yaml(raw2)
        assert '"safe\\rmalicious_key: true"' in out2


class TestSchemaToYamlFileWrite:
    def test_writes_file(self, tmp_path):
        raw = {"id": "INT64"}
        dest = tmp_path / "schema.yaml"
        returned = schema_to_yaml(raw, path=dest)
        assert dest.exists()
        written = dest.read_text(encoding="utf-8")
        assert written == returned

    def test_file_ends_with_newline(self, tmp_path):
        dest = tmp_path / "s.yaml"
        schema_to_yaml({"x": "BOOL"}, path=dest)
        assert dest.read_text(encoding="utf-8").endswith("\n")

    def test_creates_parent_dirs(self, tmp_path):
        dest = tmp_path / "deep" / "nested" / "schema.yaml"
        schema_to_yaml({"col": "STRING"}, path=dest)
        assert dest.exists()

    def test_overwrites_existing_file(self, tmp_path):
        dest = tmp_path / "schema.yaml"
        dest.write_text("old content", encoding="utf-8")
        schema_to_yaml({"col": "INT64"}, path=dest)
        assert "old content" not in dest.read_text(encoding="utf-8")

    def test_string_path_accepted(self, tmp_path):
        dest = str(tmp_path / "schema.yaml")
        schema_to_yaml({"col": "STRING"}, path=dest)
        assert pathlib.Path(dest).exists()

    def test_no_file_when_path_none(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        schema_to_yaml({"col": "INT64"})  # no path= no file
        assert list(tmp_path.iterdir()) == []


def test_public_api_accessible_via_arnio_namespace():
    assert hasattr(ar, "schema_to_dict")
    assert hasattr(ar, "schema_to_yaml")
    assert ar.schema_to_dict is schema_to_dict
    assert ar.schema_to_yaml is schema_to_yaml


def test_schema_with_rules_raises():
    schema = _FakeSchema({"col": {"type": "STRING"}})
    schema.rules = [lambda df: []]
    with pytest.raises(ValueError, match="rules"):
        schema_to_dict(schema)


def test_strict_and_unique_preserved():
    schema = _FakeSchema({"col": {"type": "INT64"}})
    schema.strict = True
    schema.unique = ["col"]
    result = schema_to_dict(schema)
    assert result["strict"] is True
    assert result["unique"] == ["col"]


def test_set_valued_allowed_normalized():
    raw = {"status": {"type": "STRING", "allowed": {"b", "a", "c"}}}
    result = schema_to_dict(raw)
    assert result["fields"]["status"]["allowed"] == ["a", "b", "c"]


def test_real_schema_field_dtype():
    schema = ar.Schema({"price": ar.Field(dtype="FLOAT64", nullable=False)})
    result = schema_to_dict(schema)
    assert result["fields"]["price"]["dtype"] == "FLOAT64"
    assert result["fields"]["price"]["nullable"] is False


def test_real_schema_field_allowed_set_normalized():
    schema = ar.Schema({"status": ar.Field(dtype="STRING", allowed={"a", "b", "c"})})
    result = schema_to_dict(schema)
    assert result["fields"]["status"]["allowed"] == ["a", "b", "c"]


def test_real_schema_field_required_if_tuple_normalized():
    schema = ar.Schema(
        {"col": ar.Field(dtype="STRING", required_if=("other_col", "yes"))}
    )
    result = schema_to_dict(schema)
    assert isinstance(result["fields"]["col"]["required_if"], list)
    assert result["fields"]["col"]["required_if"] == ["other_col", "yes"]


def test_real_schema_field_datetime_bounds():
    schema = ar.Schema(
        {"ts": ar.Field(dtype="DATETIME", min="2020-01-01", max="2025-12-31")}
    )
    result = schema_to_dict(schema)
    assert "datetime_min" in result["fields"]["ts"]
    assert "datetime_max" in result["fields"]["ts"]
    assert result["fields"]["ts"]["min"] == "2020-01-01"
    assert result["fields"]["ts"]["max"] == "2025-12-31"


def test_real_schema_with_rules_raises():
    schema = ar.Schema({"col": ar.Field(dtype="STRING")}, rules=[lambda df: []])
    with pytest.raises(ValueError, match="rules"):
        schema_to_dict(schema)


# test unsupported raw field value
def test_raw_field_object_raises():
    with pytest.raises(TypeError):
        schema_to_dict({"x": object()})


# test for nested set normalization
def test_nested_set_normalized():
    result = schema_to_dict({"x": {"meta": {"tags": {"b", "a"}}}})

    assert result == {"fields": {"x": {"meta": {"tags": ["a", "b"]}}}}


# test for nested unsupported object inside dict
def test_nested_unsupported_object_raises():
    with pytest.raises(TypeError):
        schema_to_dict({"x": {"meta": {"bad": object()}}})


# test for nested unsupported object inside list
def test_list_with_unsupported_object_raises():
    with pytest.raises(TypeError):
        schema_to_dict({"x": {"values": [1, object()]}})
