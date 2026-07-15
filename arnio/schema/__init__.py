"""arnio.schema — Schema definition and field types.

Public API:
    Schema      — Define what trustworthy data looks like.
    Field       — Base field type for custom validators.
    Int         — Integer field with optional min/max constraints.
    Float       — Float field with optional min/max constraints.
    String      — String field with optional length/pattern constraints.
    Bool        — Boolean field.
    Date        — Date string field with format validation.
    DateTime    — DateTime string field with format validation.
    Email       — Email address semantic field.
    URL         — URL semantic field.
    PhoneNumber — Phone number semantic field.
    IPAddress   — IP address semantic field.
    UUID        — UUID semantic field.
    Regex       — Custom regex pattern field.
"""

from arnio.schema._fields import Bool, Date, DateTime, Field, Float, Int, String
from arnio.schema._schema import Schema
from arnio.schema._semantic import URL, UUID, Email, IPAddress, PhoneNumber, Regex

__all__ = [
    "URL",
    "UUID",
    "Bool",
    "Date",
    "DateTime",
    "Email",
    "Field",
    "Float",
    "IPAddress",
    "Int",
    "PhoneNumber",
    "Regex",
    "Schema",
    "String",
]
