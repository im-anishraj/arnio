"""
Tests for Schema YAML serialization: to_yaml(), from_yaml(),
save_schema(), and load_schema().
"""
from __future__ import annotations

import pathlib
import pytest
import yaml

from arnio.schema import (
    Bool,
    Date,
    DateTime,
    Email,
    Field,
    Float64,
    Int64,
    Regex,
    Schema,
    String,
    URL,
    load_schema,
    save_schema,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_schema() -> Schema:
    return Schema(
        fields={
            "user_id": Int64(nullable=False, unique=True),
            "email": Email(nullable=False),
            "score": Float64(nullable=True, min=0.0, max=100.0),
            "status": String(allowed={"active", "inactive"}),
            "is_active": Bool(nullable=False),
        },
        strict=True,
        unique=["user_id"],
    )


# ---------------------------------------------------------------------------
# to_yaml: basic round-trip
# ---------------------------------------------------------------------------

class TestToYaml:
    def test_returns_string(self):
        schema = _make_schema()
        result = schema.to_yaml()
        assert isinstance(result, str)

    def test_valid_yaml(self):
        schema = _make_schema()
        parsed = yaml.safe_load(schema.to_yaml())
        assert isinstance(parsed, dict)
        assert "fields" in parsed

    def test_fields_sorted_alphabetically(self):
        schema = _make_schema()
        parsed = yaml.safe_load(schema.to_yaml())
        keys = list(parsed["fields"].keys())
        assert keys == sorted(keys)

    def test_strict_preserved(self):
        schema = _make_schema()
        parsed = yaml.safe_load(schema.to_yaml())
        assert parsed["strict"] is True

    def test_unique_preserved(self):
        schema = _make_schema()
        parsed = yaml.safe_load(schema.to_yaml())
        assert parsed["unique"] == ["user_id"]

    def test_unique_none(self):
        schema = Schema({"x": Int64()})
        parsed = yaml.safe_load(schema.to_yaml())
        assert parsed["unique"] is None

    def test_nullable_false_preserved(self):
        schema = Schema({"x": Int64(nullable=False)})
        parsed = yaml.safe_load(schema.to_yaml())
        assert parsed["fields"]["x"]["nullable"] is False

    def test_allowed_set_sorted(self):
        schema = Schema({"status": String(allowed={"z", "a", "m"})})
        parsed = yaml.safe_load(schema.to_yaml())
        assert parsed["fields"]["status"]["allowed"] == ["a", "m", "z"]

    def test_deterministic_across_calls(self):
        schema = _make_schema()
        assert schema.to_yaml() == schema.to_yaml()

    def test_raises_if_rules_present(self):
        schema = Schema(
            fields={"x": Int64()},
            rules=[lambda df: []],
        )
        with pytest.raises(ValueError, match="not YAML serializable"):
            schema.to_yaml()

    def test_writes_to_file(self, tmp_path):
        schema = _make_schema()
        target = tmp_path / "contract.schema.yaml"
        returned = schema.to_yaml(path=str(target))
        assert target.exists()
        assert target.read_text(encoding="utf-8") == returned

    def test_file_content_is_valid_yaml(self, tmp_path):
        schema = _make_schema()
        target = tmp_path / "contract.schema.yaml"
        schema.to_yaml(path=str(target))
        parsed = yaml.safe_load(target.read_text(encoding="utf-8"))
        assert "fields" in parsed

    def test_overwrite_existing_file(self, tmp_path):
        schema1 = Schema({"a": Int64()})
        schema2 = Schema({"b": Float64()})
        target = tmp_path / "schema.yaml"
        schema1.to_yaml(path=str(target))
        schema2.to_yaml(path=str(target))
        parsed = yaml.safe_load(target.read_text(encoding="utf-8"))
        assert "b" in parsed["fields"]
        assert "a" not in parsed["fields"]


# ---------------------------------------------------------------------------
# from_yaml: deserialization
# ---------------------------------------------------------------------------

class TestFromYaml:
    def test_round_trip_fields(self):
        original = _make_schema()
        restored = Schema.from_yaml(original.to_yaml())
        assert set(restored.fields.keys()) == set(original.fields.keys())

    def test_round_trip_strict(self):
        original = _make_schema()
        restored = Schema.from_yaml(original.to_yaml())
        assert restored.strict == original.strict

    def test_round_trip_unique(self):
        original = _make_schema()
        restored = Schema.from_yaml(original.to_yaml())
        assert list(restored.unique) == list(original.unique)

    def test_round_trip_nullable(self):
        original = Schema({"x": Int64(nullable=False)})
        restored = Schema.from_yaml(original.to_yaml())
        assert restored.fields["x"].nullable is False

    def test_round_trip_dtype(self):
        original = Schema({"x": Float64()})
        restored = Schema.from_yaml(original.to_yaml())
        assert restored.fields["x"].dtype == "float64"

    def test_round_trip_allowed_set(self):
        original = Schema({"s": String(allowed={"a", "b", "c"})})
        restored = Schema.from_yaml(original.to_yaml())
        assert restored.fields["s"].allowed == {"a", "b", "c"}

    def test_round_trip_pattern(self):
        original = Schema({"code": Regex(r"^[A-Z]{3}$")})
        restored = Schema.from_yaml(original.to_yaml())
        assert restored.fields["code"].pattern == r"^[A-Z]{3}$"

    def test_round_trip_min_max(self):
        original = Schema({"score": Float64(min=0.0, max=1.0)})
        restored = Schema.from_yaml(original.to_yaml())
        assert restored.fields["score"].min == 0.0
        assert restored.fields["score"].max == 1.0

    def test_round_trip_severity(self):
        original = Schema({"x": Int64(severity="warning")})
        restored = Schema.from_yaml(original.to_yaml())
        assert restored.fields["x"].severity == "warning"

    def test_round_trip_email_semantic(self):
        original = Schema({"e": Email(nullable=False)})
        restored = Schema.from_yaml(original.to_yaml())
        assert restored.fields["e"].semantic == "email"

    def test_round_trip_bool_dtype(self):
        original = Schema({"flag": Bool(nullable=False)})
        restored = Schema.from_yaml(original.to_yaml())
        assert restored.fields["flag"].dtype == "bool"

    def test_round_trip_unique_none(self):
        original = Schema({"x": Int64()})
        restored = Schema.from_yaml(original.to_yaml())
        assert restored.unique is None

    def test_round_trip_strict_false(self):
        original = Schema({"x": Int64()}, strict=False)
        restored = Schema.from_yaml(original.to_yaml())
        assert restored.strict is False

    def test_raises_on_invalid_yaml(self):
        with pytest.raises(ValueError, match="Invalid schema YAML"):
            Schema.from_yaml(": : : bad yaml {{{{")

    def test_raises_on_wrong_top_level_type(self):
        with pytest.raises(TypeError):
            Schema.from_yaml("- just a list\n")

    def test_raises_on_missing_fields_key(self):
        bad_yaml = yaml.dump({"strict": False, "unique": None})
        with pytest.raises(TypeError, match="'fields' must be an object"):
            Schema.from_yaml(bad_yaml)

    def test_raises_on_wrong_strict_type(self):
        bad_yaml = yaml.dump({"fields": {}, "strict": "yes", "unique": None})
        with pytest.raises(TypeError, match="'strict' must be a boolean"):
            Schema.from_yaml(bad_yaml)


# ---------------------------------------------------------------------------
# save_schema / load_schema convenience helpers
# ---------------------------------------------------------------------------

class TestSaveLoadSchema:
    def test_save_creates_file(self, tmp_path):
        schema = _make_schema()
        path = tmp_path / "schema.yaml"
        save_schema(schema, str(path))
        assert path.exists()

    def test_load_round_trip(self, tmp_path):
        original = _make_schema()
        path = tmp_path / "schema.yaml"
        save_schema(original, str(path))
        restored = load_schema(str(path))
        assert set(restored.fields.keys()) == set(original.fields.keys())
        assert restored.strict == original.strict

    def test_load_missing_file_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            load_schema(str(tmp_path / "nonexistent.yaml"))

    def test_save_does_not_return_value(self, tmp_path):
        schema = _make_schema()
        result = save_schema(schema, str(tmp_path / "s.yaml"))
        assert result is None

    def test_load_returns_schema(self, tmp_path):
        schema = _make_schema()
        path = tmp_path / "schema.yaml"
        save_schema(schema, str(path))
        restored = load_schema(str(path))
        assert isinstance(restored, Schema)

    def test_save_load_unicode_allowed_values(self, tmp_path):
        schema = Schema({"city": String(allowed={"München", "Zürich", "Köln"})})
        path = tmp_path / "schema.yaml"
        save_schema(schema, str(path))
        restored = load_schema(str(path))
        assert restored.fields["city"].allowed == {"München", "Zürich", "Köln"}

    def test_deterministic_file_content(self, tmp_path):
        schema = _make_schema()
        p1 = tmp_path / "a.yaml"
        p2 = tmp_path / "b.yaml"
        save_schema(schema, str(p1))
        save_schema(schema, str(p2))
        assert p1.read_text(encoding="utf-8") == p2.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# DateTime round-trip (has special _datetime_min/_datetime_max handling)
# ---------------------------------------------------------------------------

class TestDateTimeYamlRoundTrip:
    def test_datetime_bounds_preserved(self):
        original = Schema(
            {"ts": DateTime(min="2020-01-01", max="2030-12-31", nullable=False)}
        )
        restored = Schema.from_yaml(original.to_yaml())
        assert restored.fields["ts"].dtype == "datetime"
        assert restored.fields["ts"]._datetime_min is not None
        assert restored.fields["ts"]._datetime_max is not None

    def test_datetime_no_bounds(self):
        original = Schema({"ts": DateTime()})
        restored = Schema.from_yaml(original.to_yaml())
        assert restored.fields["ts"]._datetime_min is None
        assert restored.fields["ts"]._datetime_max is None