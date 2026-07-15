"""Tests for the schema system."""

import pytest

import arnio as ar
from arnio.exceptions import SchemaError


class TestFieldTypes:
    """Test base field types."""

    def test_int_basic(self):
        f = ar.Int()
        assert f.nullable is True
        assert f.expected_dtype == "int64"

    def test_int_with_constraints(self):
        f = ar.Int(min=0, max=150, nullable=False)
        assert f.min == 0
        assert f.max == 150
        assert f.nullable is False

    def test_int_min_greater_than_max_raises(self):
        with pytest.raises(SchemaError, match=r"min.*<=.*max"):
            ar.Int(min=10, max=5)

    def test_int_validate_value(self):
        f = ar.Int(min=0, max=100)
        assert f.validate_value(50) is None
        assert f.validate_value(-1) is not None
        assert f.validate_value(101) is not None

    def test_float_basic(self):
        f = ar.Float(min=0.0, max=1.0)
        assert f.expected_dtype == "float64"
        assert f.validate_value(0.5) is None
        assert f.validate_value(1.5) is not None

    def test_string_basic(self):
        f = ar.String(min_length=1, max_length=100)
        assert f.expected_dtype == "string"
        assert f.validate_value("hello") is None

    def test_string_length_validation(self):
        f = ar.String(min_length=3, max_length=10)
        assert f.validate_value("ab") is not None
        assert f.validate_value("abc") is None
        assert f.validate_value("a" * 11) is not None

    def test_string_pattern(self):
        f = ar.String(pattern=r"^\d{3}-\d{4}$")
        assert f.validate_value("123-4567") is None
        assert f.validate_value("abc") is not None

    def test_string_invalid_pattern_raises(self):
        with pytest.raises(SchemaError, match="regex"):
            ar.String(pattern="[invalid")

    def test_bool_basic(self):
        f = ar.Bool()
        assert f.expected_dtype == "bool"
        assert f.validate_value(True) is None
        assert f.validate_value(False) is None

    def test_date_basic(self):
        f = ar.Date()
        assert f.validate_value("2024-01-15") is None
        assert f.validate_value("not-a-date") is not None

    def test_date_custom_format(self):
        f = ar.Date(format="%d/%m/%Y")
        assert f.validate_value("15/01/2024") is None
        assert f.validate_value("2024-01-15") is not None

    def test_datetime_basic(self):
        f = ar.DateTime()
        assert f.validate_value("2024-01-15 10:30:00") is None
        assert f.validate_value("not-a-datetime") is not None

    def test_allowed_values(self):
        f = ar.String(allowed={"US", "UK", "IN"})
        assert f.validate_value("US") is None
        assert f.validate_value("DE") is not None


class TestSemanticFields:
    """Test semantic field types."""

    def test_email_valid(self):
        f = ar.Email()
        assert f.validate_value("user@example.com") is None
        assert f.validate_value("user+tag@domain.co.uk") is None

    def test_email_invalid(self):
        f = ar.Email()
        assert f.validate_value("not-an-email") is not None
        assert f.validate_value("@example.com") is not None

    def test_url_valid(self):
        f = ar.URL()
        assert f.validate_value("https://example.com") is None
        assert f.validate_value("http://sub.domain.org/path") is None

    def test_url_invalid(self):
        f = ar.URL()
        assert f.validate_value("not-a-url") is not None
        assert f.validate_value("ftp://files.com") is not None

    def test_phone_valid(self):
        f = ar.PhoneNumber()
        assert f.validate_value("+1-234-567-8900") is None
        assert f.validate_value("(555) 123-4567") is None

    def test_phone_invalid(self):
        f = ar.PhoneNumber()
        assert f.validate_value("123") is not None

    def test_ip_address_v4(self):
        f = ar.IPAddress()
        assert f.validate_value("192.168.1.1") is None
        assert f.validate_value("999.999.999.999") is not None

    def test_ip_address_v6(self):
        f = ar.IPAddress()
        assert f.validate_value("::1") is None

    def test_uuid_valid(self):
        f = ar.UUID()
        assert f.validate_value("550e8400-e29b-41d4-a716-446655440000") is None

    def test_uuid_invalid(self):
        f = ar.UUID()
        assert f.validate_value("not-a-uuid") is not None

    def test_regex_field(self):
        f = ar.Regex(pattern=r"^[A-Z]{2}\d{4}$")
        assert f.validate_value("AB1234") is None
        assert f.validate_value("ab1234") is not None

    def test_regex_empty_pattern_raises(self):
        with pytest.raises(SchemaError, match="non-empty"):
            ar.Regex(pattern="")


class TestSchema:
    """Test Schema class — both dict-based and class-based."""

    def test_dict_based_schema(self):
        schema = ar.Schema({
            "name": ar.String(),
            "age": ar.Int(min=0),
        })
        assert "name" in schema
        assert "age" in schema
        assert len(schema) == 2

    def test_class_based_schema(self):
        class Users(ar.Schema):
            name = ar.String()
            age = ar.Int(min=0)

        schema = Users()
        assert "name" in schema
        assert "age" in schema
        assert len(schema) == 2

    def test_dict_and_class_schemas_equivalent(self):
        dict_schema = ar.Schema({
            "name": ar.String(),
            "age": ar.Int(min=0),
        })

        class ClassSchema(ar.Schema):
            name = ar.String()
            age = ar.Int(min=0)

        class_schema = ClassSchema()
        assert dict_schema.column_names == class_schema.column_names

    def test_schema_strict_mode(self):
        schema = ar.Schema({"a": ar.Int()}, strict=True)
        assert schema.strict is True
        assert schema.allow_extra is False

    def test_schema_required_columns(self):
        schema = ar.Schema({
            "required": ar.String(nullable=False),
            "optional": ar.String(nullable=True),
        })
        assert schema.required_columns == ["required"]

    def test_invalid_fields_raises(self):
        with pytest.raises(SchemaError, match="Field instance"):
            ar.Schema({"name": "not a field"})

    def test_non_string_field_name_raises(self):
        with pytest.raises(SchemaError, match="strings"):
            ar.Schema({123: ar.String()})

    def test_schema_inheritance(self):
        class Base(ar.Schema):
            name = ar.String()

        class Extended(Base):
            age = ar.Int()

        schema = Extended()
        assert "name" in schema
        assert "age" in schema

    def test_schema_repr(self):
        schema = ar.Schema({"name": ar.String()})
        assert "Schema" in repr(schema)
        assert "name" in repr(schema)


class TestSchemaInference:
    """Test schema inference from data."""

    def test_infer_from_pandas(self, sample_df):
        schema = ar.infer_schema(sample_df)
        assert "name" in schema
        assert "age" in schema

    def test_infer_from_dicts(self, sample_dicts):
        schema = ar.infer_schema(sample_dicts)
        assert "name" in schema
        assert "age" in schema


class TestSchemaDiff:
    """Test schema diff."""

    def test_identical_schemas(self):
        a = ar.Schema({"name": ar.String()})
        b = ar.Schema({"name": ar.String()})
        diff = ar.diff_schemas(a, b)
        assert diff.is_identical

    def test_added_column(self):
        a = ar.Schema({"name": ar.String()})
        b = ar.Schema({"name": ar.String(), "age": ar.Int()})
        diff = ar.diff_schemas(a, b)
        assert not diff.is_identical
        assert any(c.change_type == "added" for c in diff.changes)

    def test_removed_column(self):
        a = ar.Schema({"name": ar.String(), "age": ar.Int()})
        b = ar.Schema({"name": ar.String()})
        diff = ar.diff_schemas(a, b)
        assert any(c.change_type == "removed" for c in diff.changes)


class TestSchemaSerde:
    """Test schema serialization."""

    def test_to_dict_roundtrip(self):
        schema = ar.Schema({
            "name": ar.String(min_length=1),
            "age": ar.Int(min=0, max=150),
        })
        d = ar.schema_to_dict(schema)
        restored = ar.schema_from_dict(d)
        assert restored.column_names == schema.column_names

    def test_to_json_roundtrip(self):
        schema = ar.Schema({"email": ar.Email(nullable=False)})
        json_str = ar.schema_to_json(schema)
        restored = ar.schema_from_json(json_str)
        assert "email" in restored
