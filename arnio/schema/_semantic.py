"""Semantic field types — high-value domain-specific validators.

Each semantic type subclasses Field and provides specialized
``validate_value()`` logic for common data patterns.
"""

from __future__ import annotations

import re
import uuid as _uuid_module
from dataclasses import dataclass
from ipaddress import IPv4Address, IPv6Address
from typing import Any

from arnio.exceptions import SchemaError
from arnio.schema._fields import Field

# Pre-compiled patterns for performance
_EMAIL_PATTERN = re.compile(
    r"^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-zA-Z0-9]"
    r"(?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?"
    r"(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$"
)

_URL_PATTERN = re.compile(
    r"^https?://"
    r"(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+"
    r"[a-zA-Z]{2,}"
    r"(?::\d{1,5})?"
    r"(?:/[^\s]*)?$"
)

_PHONE_PATTERN = re.compile(
    r"^\+?[0-9\s\-().]{7,20}$"
)


@dataclass(frozen=True)
class Email(Field):
    """Email address field.

    Validates that the value matches a standard email format.
    Does not verify deliverability — only format correctness.

    Args:
        nullable: Whether null values are allowed.
        unique: Whether all values must be unique.
        severity: Issue severity level.
    """

    @property
    def expected_dtype(self) -> str:
        return "string"

    @property
    def pattern(self) -> re.Pattern:
        return _EMAIL_PATTERN

    def validate_value(self, value: Any) -> str | None:
        base = super().validate_value(value)
        if base is not None:
            return base
        s = str(value)
        if not _EMAIL_PATTERN.fullmatch(s):
            return f"Value {s!r} is not a valid email address"
        return None


@dataclass(frozen=True)
class URL(Field):
    """URL field.

    Validates that the value is a well-formed HTTP/HTTPS URL.

    Args:
        nullable: Whether null values are allowed.
        unique: Whether all values must be unique.
        severity: Issue severity level.
    """

    @property
    def expected_dtype(self) -> str:
        return "string"

    @property
    def pattern(self) -> re.Pattern:
        return _URL_PATTERN

    def validate_value(self, value: Any) -> str | None:
        base = super().validate_value(value)
        if base is not None:
            return base
        s = str(value)
        if not _URL_PATTERN.fullmatch(s):
            return f"Value {s!r} is not a valid URL"
        return None


@dataclass(frozen=True)
class PhoneNumber(Field):
    """Phone number field.

    Validates that the value matches a general phone number pattern.
    Accepts international format (+1-234-567-8900) and common variations.
    Does not validate against specific country rules.

    Args:
        nullable: Whether null values are allowed.
        unique: Whether all values must be unique.
        severity: Issue severity level.
    """

    @property
    def expected_dtype(self) -> str:
        return "string"

    @property
    def pattern(self) -> re.Pattern:
        return _PHONE_PATTERN

    def validate_value(self, value: Any) -> str | None:
        base = super().validate_value(value)
        if base is not None:
            return base
        s = str(value)
        if not _PHONE_PATTERN.fullmatch(s):
            return f"Value {s!r} is not a valid phone number"
        return None


@dataclass(frozen=True)
class IPAddress(Field):
    """IP address field (IPv4 or IPv6).

    Args:
        nullable: Whether null values are allowed.
        unique: Whether all values must be unique.
        severity: Issue severity level.
    """

    @property
    def expected_dtype(self) -> str:
        return "string"

    def validate_value(self, value: Any) -> str | None:
        base = super().validate_value(value)
        if base is not None:
            return base
        s = str(value)
        try:
            IPv4Address(s)
            return None
        except ValueError:
            pass
        try:
            IPv6Address(s)
            return None
        except ValueError:
            return f"Value {s!r} is not a valid IP address"


@dataclass(frozen=True)
class UUID(Field):
    """UUID field.

    Validates that the value is a valid UUID string (any version).

    Args:
        nullable: Whether null values are allowed.
        unique: Whether all values must be unique.
        severity: Issue severity level.
    """

    @property
    def expected_dtype(self) -> str:
        return "string"

    def validate_value(self, value: Any) -> str | None:
        base = super().validate_value(value)
        if base is not None:
            return base
        s = str(value)
        try:
            _uuid_module.UUID(s)
        except ValueError:
            return f"Value {s!r} is not a valid UUID"
        return None


@dataclass(frozen=True)
class Regex(Field):
    """Custom regex pattern field.

    Validates that string values fully match the given regex pattern.

    Args:
        pattern: Regex pattern to match against (full match).
        nullable: Whether null values are allowed.
        unique: Whether all values must be unique.
        severity: Issue severity level.

    Examples:
        >>> ar.Regex(pattern=r"^[A-Z]{2}\\d{4}$")  # e.g., "AB1234"
    """

    pattern: str = ""

    def __post_init__(self) -> None:
        super().__post_init__()
        if not self.pattern:
            raise SchemaError("Regex field requires a non-empty pattern")
        try:
            compiled = re.compile(self.pattern)
            object.__setattr__(self, "_compiled_pattern", compiled)
        except re.error as exc:
            raise SchemaError(f"Invalid regex pattern: {exc}") from exc

    @property
    def expected_dtype(self) -> str:
        return "string"

    def validate_value(self, value: Any) -> str | None:
        base = super().validate_value(value)
        if base is not None:
            return base
        s = str(value)
        if not getattr(self, "_compiled_pattern").fullmatch(s):
            return f"Value {s!r} does not match pattern {self.pattern!r}"
        return None
