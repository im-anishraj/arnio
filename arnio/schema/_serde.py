"""Schema serialization — to/from YAML, JSON, and dict.

Enables schemas to be stored as config files and checked into version control.
"""

from __future__ import annotations

import json
from typing import Any

from arnio.exceptions import SchemaError
from arnio.schema._fields import Bool, Date, DateTime, Field, Float, Int, String
from arnio.schema._schema import Schema
from arnio.schema._semantic import URL, UUID, Email, IPAddress, PhoneNumber, Regex

# Maps type names to classes for deserialization
_FIELD_TYPE_REGISTRY: dict[str, type[Field]] = {
    "Int": Int,
    "Float": Float,
    "String": String,
    "Bool": Bool,
    "Date": Date,
    "DateTime": DateTime,
    "Email": Email,
    "URL": URL,
    "PhoneNumber": PhoneNumber,
    "IPAddress": IPAddress,
    "UUID": UUID,
    "Regex": Regex,
}

# Fields that are common to all field types (from base Field)
_BASE_FIELD_PARAMS = {"nullable", "unique", "allowed", "severity"}


def _field_to_dict(field_def: Field) -> dict[str, Any]:
    """Serialize a single Field to a dict."""
    type_name = type(field_def).__name__
    result: dict[str, Any] = {"type": type_name}

    # Include non-default parameters
    if not field_def.nullable:
        result["nullable"] = False
    if field_def.unique:
        result["unique"] = True
    if field_def.allowed is not None:
        result["allowed"] = sorted(field_def.allowed, key=str)
    if field_def.severity != "error":
        result["severity"] = field_def.severity

    # Type-specific params
    if isinstance(field_def, (Int, Float)):
        if field_def.min is not None:
            result["min"] = field_def.min
        if field_def.max is not None:
            result["max"] = field_def.max

    if isinstance(field_def, String):
        if field_def.min_length is not None:
            result["min_length"] = field_def.min_length
        if field_def.max_length is not None:
            result["max_length"] = field_def.max_length
        if field_def.pattern is not None:
            result["pattern"] = field_def.pattern

    if isinstance(field_def, (Date, DateTime)) and field_def.format != (
        "%Y-%m-%d" if isinstance(field_def, Date) else "%Y-%m-%d %H:%M:%S"
    ):
        result["format"] = field_def.format

    if isinstance(field_def, Regex):
        result["pattern"] = field_def.pattern

    return result


def _field_from_dict(data: dict[str, Any]) -> Field:
    """Deserialize a Field from a dict."""
    type_name = data.get("type")
    if type_name not in _FIELD_TYPE_REGISTRY:
        raise SchemaError(f"Unknown field type: {type_name!r}")

    field_cls = _FIELD_TYPE_REGISTRY[type_name]
    params = {k: v for k, v in data.items() if k != "type"}

    # Convert allowed list back to frozenset
    if "allowed" in params:
        params["allowed"] = frozenset(params["allowed"])

    return field_cls(**params)


def schema_to_dict(schema: Schema) -> dict[str, Any]:
    """Serialize a Schema to a dict.

    Returns:
        A dict that can be serialized to JSON or YAML.
    """
    result: dict[str, Any] = {
        "fields": {
            name: _field_to_dict(f)
            for name, f in schema.fields.items()
        },
    }
    if schema.strict:
        result["strict"] = True
    elif not schema.allow_extra:
        # Only emit allow_extra when explicitly set without strict
        result["allow_extra"] = False
    return result


def schema_from_dict(data: dict[str, Any]) -> Schema:
    """Deserialize a Schema from a dict.

    Args:
        data: A dict with "fields" key mapping column names to field dicts.

    Returns:
        A Schema instance.
    """
    if not isinstance(data, dict):
        raise SchemaError(f"Expected a dictionary, got {type(data).__name__}")

    if "fields" not in data:
        raise SchemaError("Schema dict must contain a 'fields' key")

    fields = {
        name: _field_from_dict(field_data)
        for name, field_data in data["fields"].items()
    }

    return Schema(
        fields,
        strict=data.get("strict", False),
        allow_extra=data.get("allow_extra", True),
    )


def schema_to_json(schema: Schema, *, indent: int = 2) -> str:
    """Serialize a Schema to a JSON string."""
    return json.dumps(schema_to_dict(schema), indent=indent)


def schema_from_json(json_str: str) -> Schema:
    """Deserialize a Schema from a JSON string."""
    try:
        data = json.loads(json_str)
    except json.JSONDecodeError as exc:
        raise SchemaError(f"Invalid JSON: {exc}") from exc
    return schema_from_dict(data)


def schema_to_yaml(schema: Schema) -> str:
    """Serialize a Schema to a YAML string.

    Requires PyYAML (``pip install pyyaml`` or ``pip install arnio[yaml]``).
    """
    try:
        import yaml
    except ImportError:
        raise ImportError(
            "PyYAML is required for YAML serialization. "
            "Install it with: pip install arnio[yaml]"
        ) from None

    return yaml.dump(schema_to_dict(schema), default_flow_style=False, sort_keys=False)


def schema_from_yaml(yaml_str: str) -> Schema:
    """Deserialize a Schema from a YAML string.

    Requires PyYAML (``pip install pyyaml`` or ``pip install arnio[yaml]``).
    """
    try:
        import yaml
    except ImportError:
        raise ImportError(
            "PyYAML is required for YAML deserialization. "
            "Install it with: pip install arnio[yaml]"
        ) from None

    try:
        data = yaml.safe_load(yaml_str)
    except yaml.YAMLError as exc:
        raise SchemaError(f"Invalid YAML: {exc}") from exc

    return schema_from_dict(data)
