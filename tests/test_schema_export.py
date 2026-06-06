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

    def test_numeric_looking_strings_quoted(self):
        raw = {
            "status": {
                "type": "STRING",
                "allowed": ["001", "123", "1.5", "-45"],
            }
        }
        out = schema_to_yaml(raw)

        assert '"001"' in out
        assert '"123"' in out
        assert '"1.5"' in out
        assert '"-45"' in out

    def test_genuine_numbers_remain_unquoted(self):
        raw = {
            "metrics": {
                "count": 100,
                "score": 4.5,
            }
        }
        out = schema_to_yaml(raw)

        assert "count: 100" in out
        assert "score: 4.5" in out
        assert '"100"' not in out
        assert '"4.5"' not in out

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
    schema = ar.Schema({"price": ar.Field(dtype="float64", nullable=False)})
    result = schema_to_dict(schema)
    assert result["fields"]["price"]["dtype"] == "float64"
    assert result["fields"]["price"]["nullable"] is False


def test_real_schema_field_allowed_set_normalized():
    schema = ar.Schema({"status": ar.Field(dtype="string", allowed={"a", "b", "c"})})
    result = schema_to_dict(schema)
    assert result["fields"]["status"]["allowed"] == ["a", "b", "c"]


def test_real_schema_field_required_if_tuple_normalized():
    schema = ar.Schema(
        {"col": ar.Field(dtype="string", required_if=("other_col", "yes"))}
    )
    result = schema_to_dict(schema)
    assert isinstance(result["fields"]["col"]["required_if"], list)
    assert result["fields"]["col"]["required_if"] == ["other_col", "yes"]


def test_real_schema_field_datetime_bounds():
    schema = ar.Schema(
        {"ts": ar.Field(dtype="datetime", min="2020-01-01", max="2025-12-31")}
    )
    result = schema_to_dict(schema)
    assert "datetime_min" in result["fields"]["ts"]
    assert "datetime_max" in result["fields"]["ts"]
    assert result["fields"]["ts"]["min"] == "2020-01-01"
    assert result["fields"]["ts"]["max"] == "2025-12-31"


def test_real_schema_with_rules_raises():
    schema = ar.Schema({"col": ar.Field(dtype="string")}, rules=[lambda df: []])
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


# ── Regression tests for issue #1467 ────────────────────────────────────────


def test_raw_dict_fields_named_strict_and_unique_not_dropped():
    """Flat scan_csv-style dict: strict/unique are real field names, not metadata."""
    raw = {"strict": "int64", "unique": "string", "name": "string"}
    result = schema_to_dict(raw)

    assert "strict" in result["fields"]
    assert "unique" in result["fields"]
    assert "name" in result["fields"]

    # No top-level metadata keys should appear
    assert set(result.keys()) == {"fields"}


def test_schema_object_fields_named_strict_and_unique_not_dropped():
    """Schema object: fields named strict/unique survive alongside schema metadata."""
    schema = ar.Schema(
        {
            "strict": ar.Field(dtype="int64"),
            "unique": ar.Field(dtype="string"),
            "name": ar.Field(dtype="string"),
        },
        strict=True,
        unique=["name"],
    )

    result = schema_to_dict(schema)

    assert "strict" in result["fields"]
    assert "unique" in result["fields"]
    assert "name" in result["fields"]

    # Schema-level metadata must still be top-level
    assert result["strict"] is True
    assert result["unique"] == ["name"]


# ── Regression tests for issue #1730 ────────────────────────────────────────


class TestDateLikeStringQuoting:
    """Date-like string values must be quoted to prevent YAML timestamp resolution."""

    def test_bare_date_in_allowed_is_quoted(self):
        raw = {"field": {"type": "string", "allowed": ["2026-05-28"]}}
        out = schema_to_yaml(raw)
        assert '"2026-05-28"' in out

    def test_iso_datetime_in_default_is_quoted(self):
        raw = {"field": {"type": "string", "default": "2026-05-28T10:30:00"}}
        out = schema_to_yaml(raw)
        assert '"2026-05-28T10:30:00"' in out

    def test_space_separated_datetime_is_quoted(self):
        raw = {"field": {"type": "string", "default": "2026-05-28 10:30:00"}}
        out = schema_to_yaml(raw)
        assert '"2026-05-28 10:30:00"' in out

    def test_yaml_roundtrip_preserves_date_string(self):
        """Date values survive a YAML round-trip as strings, not date objects."""
        import yaml  # soft dep – skip if not installed

        raw = {"field": {"type": "string", "allowed": ["2026-05-28"]}}
        yaml_text = schema_to_yaml(raw)
        loaded = yaml.safe_load(yaml_text)
        value = loaded["fields"]["field"]["allowed"][0]
        assert isinstance(value, str)
        assert value == "2026-05-28"

    def test_non_date_strings_unaffected(self):
        """Partial date-like strings must NOT be quoted."""
        raw = {
            "field": {
                "type": "string",
                "allowed": ["05-28", "hello"],
            }
        }
        out = schema_to_yaml(raw)
        assert "- 05-28" in out  # MM-DD fragment, not a full date
        assert "- hello" in out  # regular string

    def test_date_with_time_zone_suffix_is_quoted(self):
        raw = {"field": {"type": "string", "default": "2026-05-28T10:30:00+05:30"}}
        out = schema_to_yaml(raw)
        assert '"2026-05-28T10:30:00+05:30"' in out


# ── Regression tests for issue #1797 ────────────────────────────────────────


class TestStructuredMetadataValidation:
    """schema_to_dict() must validate and normalize structured raw-dict metadata.

    Covers the path where the input is {"fields": {...}, "strict": ..., ...}.
    Previously, metadata was merged without any validation, which allowed
    non-serializable values and non-string keys to leak into the result and
    cause delayed failures in schema_to_yaml() or downstream serializers.
    """

    def test_non_string_metadata_key_raises(self):
        """Integer metadata keys must be rejected immediately."""
        with pytest.raises(TypeError, match="metadata keys must be strings"):
            schema_to_dict({"fields": {"a": "int64"}, 123: "bad"})

    def test_unsupported_metadata_value_raises(self):
        """Non-serializable metadata values (e.g. object()) must be rejected."""
        with pytest.raises(TypeError):
            schema_to_dict({"fields": {"a": "int64"}, "strict": object()})

    def test_tuple_metadata_value_normalized_to_list(self):
        """Tuple metadata values (e.g. unique=('id',)) must be converted to list."""
        result = schema_to_dict({"fields": {"a": "int64"}, "unique": ("id", "name")})
        assert result["unique"] == ["id", "name"]
        assert isinstance(result["unique"], list)

    def test_valid_strict_metadata_preserved(self):
        """strict=True metadata must survive schema_to_dict() unchanged."""
        result = schema_to_dict({"fields": {"a": "int64"}, "strict": True})
        assert result["strict"] is True

    def test_valid_unique_list_metadata_preserved(self):
        """unique=['id'] metadata must survive schema_to_dict() unchanged."""
        result = schema_to_dict({"fields": {"a": "int64"}, "unique": ["id"]})
        assert result["unique"] == ["id"]

    def test_schema_to_yaml_end_to_end_valid_metadata(self):
        """schema_to_yaml() must not raise for valid structured metadata."""
        raw = {"fields": {"a": "int64"}, "strict": True, "unique": ["a"]}
        out = schema_to_yaml(raw)
        assert "strict: true" in out
        assert "- a" in out

    def test_schema_to_yaml_raises_for_non_string_key(self):
        """schema_to_yaml() must surface the TypeError from non-string metadata keys."""
        with pytest.raises(TypeError, match="metadata keys must be strings"):
            schema_to_yaml({"fields": {"a": "int64"}, 123: "bad"})

    def test_schema_to_yaml_raises_for_unsupported_metadata_value(self):
        """schema_to_yaml() must surface the TypeError from object() metadata values."""
        with pytest.raises(TypeError):
            schema_to_yaml({"fields": {"a": "int64"}, "strict": object()})


# ── Tests for schema_from_yaml (inverse of schema_to_yaml) ──────────────────


class TestSchemaFromYaml:
    """schema_from_yaml() must be the deterministic inverse of schema_to_yaml().

    Covers:
    - round-trip: schema_to_yaml(schema) -> file -> schema_from_yaml(path)
    - PathLike always treated as file path
    - str without newlines treated as file path
    - str with newlines parsed as raw YAML text
    - FileNotFoundError for missing path (PathLike and str)
    - ValueError for syntactically invalid YAML
    - ValueError for unknown schema-level keys
    - ValueError for unknown field-level keys
    - UserWarning for rules_omitted: true marker
    - minimal schema (fields only, no strict/unique)
    - schema with strict=True and unique constraint
    - TypeError for wrong source type
    - empty YAML raises ValueError
    """

    # ── round-trip ────────────────────────────────────────────────────────────

    def test_round_trip_via_file(self, tmp_path):
        """schema_to_yaml(schema, path=…) then schema_from_yaml(path) is lossless."""
        import arnio as ar

        schema = ar.Schema(
            fields={
                "age": ar.Int64(nullable=False, min=0, max=150),
                "email": ar.Email(),
                "country": ar.Field(dtype="string", nullable=True),
            },
            strict=True,
            unique=["email"],
        )
        yaml_path = tmp_path / "schema.yaml"
        ar.schema_to_yaml(schema, path=str(yaml_path))

        loaded = ar.schema_from_yaml(yaml_path)  # PathLike

        assert set(loaded.fields.keys()) == set(schema.fields.keys())
        assert loaded.strict == schema.strict
        assert set(loaded.unique) == set(schema.unique)

        for col in schema.fields:
            original = schema.fields[col]
            restored = loaded.fields[col]
            assert restored.dtype == original.dtype
            assert restored.nullable == original.nullable

    def test_round_trip_via_str_path(self, tmp_path):
        """Passing a str file path (no newlines) must work identically to PathLike."""
        import arnio as ar

        schema = ar.Schema(
            fields={"score": ar.Float64(nullable=True, min=0.0, max=1.0)},
        )
        yaml_path = tmp_path / "s.yaml"
        ar.schema_to_yaml(schema, path=str(yaml_path))

        loaded = ar.schema_from_yaml(str(yaml_path))  # str, no newlines → file

        assert "score" in loaded.fields
        assert loaded.fields["score"].dtype == "float64"

    def test_round_trip_raw_yaml_text(self):
        """A str with newlines is parsed directly as YAML text, not as a path."""
        from arnio.schema_export import schema_from_yaml

        yaml_text = (
            "fields:\n"
            "  age:\n"
            "    dtype: int64\n"
            "    nullable: false\n"
            "    min: 0\n"
            "    max: 120\n"
            "strict: false\n"
        )
        schema = schema_from_yaml(yaml_text)

        assert "age" in schema.fields
        assert schema.fields["age"].dtype == "int64"
        assert schema.fields["age"].nullable is False

    # ── minimal schema ────────────────────────────────────────────────────────

    def test_minimal_schema_fields_only(self, tmp_path):
        """A YAML file with only 'fields' (no strict/unique) must load cleanly."""
        import arnio as ar

        yaml_text = "fields:\n  name:\n    dtype: string\n    nullable: true\n"
        yaml_path = tmp_path / "minimal.yaml"
        yaml_path.write_text(yaml_text, encoding="utf-8")

        schema = ar.schema_from_yaml(yaml_path)

        assert "name" in schema.fields
        assert schema.fields["name"].dtype == "string"
        assert schema.strict is False  # default

    # ── PathLike handling ─────────────────────────────────────────────────────

    def test_pathlike_missing_file_raises_file_not_found(self, tmp_path):
        """PathLike that points to a non-existent file must raise FileNotFoundError."""
        import arnio as ar

        missing = tmp_path / "does_not_exist.yaml"
        with pytest.raises(FileNotFoundError, match="does_not_exist.yaml"):
            ar.schema_from_yaml(missing)

    # ── str-path handling ─────────────────────────────────────────────────────

    def test_str_path_missing_file_raises_file_not_found(self, tmp_path):
        """str without newlines pointing to a missing file must raise FileNotFoundError."""
        import arnio as ar

        missing = str(tmp_path / "ghost.yaml")
        with pytest.raises(FileNotFoundError, match="ghost.yaml"):
            ar.schema_from_yaml(missing)

    def test_str_path_does_not_silently_parse_as_yaml(self, tmp_path):
        """A path-looking str that does not exist must NOT be parsed as YAML text."""
        import arnio as ar

        # "no_newlines_at_all" has no newlines → must be treated as path
        with pytest.raises(FileNotFoundError):
            ar.schema_from_yaml("no_newlines_at_all")

    # ── error handling ────────────────────────────────────────────────────────

    def test_invalid_yaml_syntax_raises_value_error(self):
        """Syntactically broken YAML must raise ValueError, not a yaml.YAMLError."""
        import arnio as ar

        bad_yaml = "fields:\n  col:\n    dtype: [unclosed\n"
        with pytest.raises(ValueError, match="Invalid schema YAML"):
            ar.schema_from_yaml(bad_yaml)

    def test_unknown_schema_key_raises_value_error(self, tmp_path):
        """An unknown top-level key must raise ValueError with a clear message."""
        import arnio as ar

        bad = tmp_path / "bad.yaml"
        bad.write_text(
            "fields:\n  x:\n    dtype: string\nunknown_key: true\n",
            encoding="utf-8",
        )
        with pytest.raises(ValueError, match="unknown"):
            ar.schema_from_yaml(bad)

    def test_unknown_field_key_raises_value_error(self, tmp_path):
        """An unknown key inside a field definition must raise ValueError."""
        import arnio as ar

        bad = tmp_path / "bad_field.yaml"
        bad.write_text(
            "fields:\n  x:\n    dtype: string\n    foobar: true\n",
            encoding="utf-8",
        )
        with pytest.raises(ValueError, match="unknown"):
            ar.schema_from_yaml(bad)

    def test_empty_yaml_raises_value_error(self, tmp_path):
        """An empty YAML file must raise ValueError, not AttributeError or TypeError."""
        import arnio as ar

        empty = tmp_path / "empty.yaml"
        empty.write_text("", encoding="utf-8")
        with pytest.raises(ValueError, match="empty"):
            ar.schema_from_yaml(empty)

    def test_wrong_type_raises_type_error(self):
        """Passing a non-str, non-PathLike raises TypeError."""
        import arnio as ar

        with pytest.raises(TypeError, match="str or os.PathLike"):
            ar.schema_from_yaml(42)  # type: ignore[arg-type]

    # ── rules_omitted warning ─────────────────────────────────────────────────

    def test_rules_omitted_emits_user_warning(self):
        """A YAML payload with rules_omitted: true must emit a UserWarning."""
        import arnio as ar

        yaml_text = "fields:\n" "  x:\n" "    dtype: string\n" "rules_omitted: true\n"
        with pytest.warns(UserWarning, match="rules_omitted"):
            schema = ar.schema_from_yaml(yaml_text)

        assert "x" in schema.fields  # schema still loads successfully

    # ── schema with strict and unique ─────────────────────────────────────────

    def test_strict_and_unique_preserved(self, tmp_path):
        """strict=True and unique constraints must survive the round-trip."""
        import arnio as ar

        yaml_text = (
            "fields:\n"
            "  id:\n"
            "    dtype: int64\n"
            "    nullable: false\n"
            "  name:\n"
            "    dtype: string\n"
            "strict: true\n"
            "unique:\n"
            "- id\n"
        )
        yaml_path = tmp_path / "strict.yaml"
        yaml_path.write_text(yaml_text, encoding="utf-8")

        schema = ar.schema_from_yaml(yaml_path)

        assert schema.strict is True
        assert "id" in schema.unique

    # ── public API surface ────────────────────────────────────────────────────

    def test_accessible_via_ar_namespace(self):
        """schema_from_yaml must be importable from the top-level arnio namespace."""
        import arnio as ar

        assert hasattr(ar, "schema_from_yaml")
        assert callable(ar.schema_from_yaml)

    def test_in_all(self):
        """schema_from_yaml must be listed in arnio.__all__."""
        import arnio as ar

        assert "schema_from_yaml" in ar.__all__
