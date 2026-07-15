"""Base field types for schema definitions.

Field is the base class. Each concrete type (Int, Float, String, Bool,
Date, DateTime) subclasses Field and provides specialized validation
via ``validate_value()``.

Users can create custom field types by subclassing Field.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from arnio.exceptions import SchemaError


@dataclass(frozen=True)
class Field:
    """Base field type — defines validation rules for one column.

    All concrete field types (Int, Float, String, etc.) subclass this.
    Users can subclass Field to create custom validators.

    Args:
        nullable: Whether null values are allowed. Defaults to True.
        unique: Whether all values must be unique. Defaults to False.
        allowed: Set of allowed values. If set, every non-null value must
                 be a member of this set.
        severity: Issue severity — "error" or "warning". Defaults to "error".
    """

    nullable: bool = True
    unique: bool = False
    allowed: frozenset[Any] | None = None
    severity: str = "error"

    def __post_init__(self) -> None:
        if not isinstance(self.nullable, bool):
            raise SchemaError(f"nullable must be bool, got {type(self.nullable).__name__}")
        if not isinstance(self.unique, bool):
            raise SchemaError(f"unique must be bool, got {type(self.unique).__name__}")
        if self.severity not in ("error", "warning"):
            raise SchemaError(f"severity must be 'error' or 'warning', got {self.severity!r}")
        if self.allowed is not None and not isinstance(self.allowed, (set, frozenset, list, tuple)):
            raise SchemaError(
                f"allowed must be a set, list, or tuple, got {type(self.allowed).__name__}"
            )
        # Normalize allowed to frozenset
        if self.allowed is not None and not isinstance(self.allowed, frozenset):
            object.__setattr__(self, "allowed", frozenset(self.allowed))

    @property
    def expected_dtype(self) -> str | None:
        """Return the expected dtype string, or None if any dtype is acceptable."""
        return None

    def validate_value(self, value: Any) -> str | None:
        """Validate a single non-null value. Return an error message or None.

        Subclasses override this to add type-specific validation logic.
        The base implementation only checks ``allowed``.
        """
        if self.allowed is not None and value not in self.allowed:
            return f"Value {value!r} is not in the allowed set"
        return None


def _validate_numeric_bound(value: int | float | None, name: str) -> None:
    """Raise if a numeric bound is not finite."""
    if value is not None:
        if isinstance(value, bool):
            raise SchemaError(f"{name} must be a number, got bool")
        if not isinstance(value, (int, float)):
            raise SchemaError(f"{name} must be a number, got {type(value).__name__}")
        if not math.isfinite(value):
            raise SchemaError(f"{name} must be finite, got {value!r}")


@dataclass(frozen=True)
class Int(Field):
    """Integer field with optional min/max constraints.

    Args:
        min: Minimum allowed value (inclusive).
        max: Maximum allowed value (inclusive).
        nullable: Whether null values are allowed.
        unique: Whether all values must be unique.
        allowed: Set of allowed values.
        severity: Issue severity level.

    Examples:
        >>> ar.Int(min=0, max=150)
        >>> ar.Int(nullable=False, allowed={1, 2, 3})
    """

    min: int | float | None = None
    max: int | float | None = None

    def __post_init__(self) -> None:
        super().__post_init__()
        _validate_numeric_bound(self.min, "min")
        _validate_numeric_bound(self.max, "max")
        if self.min is not None and self.max is not None and self.min > self.max:
            raise SchemaError(f"min ({self.min}) must be <= max ({self.max})")

    @property
    def expected_dtype(self) -> str:
        return "int64"

    def validate_value(self, value: Any) -> str | None:
        base = super().validate_value(value)
        if base is not None:
            return base
        # bool is a subclass of int in Python; accept it as a valid integer
        if isinstance(value, bool):
            num = int(value)
        elif isinstance(value, (int, float)):
            num = value  # type: ignore[assignment]
        else:
            try:
                num = int(value)
            except (ValueError, TypeError):
                return f"Cannot interpret {value!r} as integer"
        if self.min is not None and num < self.min:
            return f"Value {num} is below minimum {self.min}"
        if self.max is not None and num > self.max:
            return f"Value {num} exceeds maximum {self.max}"
        return None


@dataclass(frozen=True)
class Float(Field):
    """Float field with optional min/max constraints.

    Args:
        min: Minimum allowed value (inclusive).
        max: Maximum allowed value (inclusive).
        nullable: Whether null values are allowed.
        unique: Whether all values must be unique.
        allowed: Set of allowed values.
        severity: Issue severity level.
    """

    min: int | float | None = None
    max: int | float | None = None

    def __post_init__(self) -> None:
        super().__post_init__()
        _validate_numeric_bound(self.min, "min")
        _validate_numeric_bound(self.max, "max")
        if self.min is not None and self.max is not None and self.min > self.max:
            raise SchemaError(f"min ({self.min}) must be <= max ({self.max})")

    @property
    def expected_dtype(self) -> str:
        return "float64"

    def validate_value(self, value: Any) -> str | None:
        base = super().validate_value(value)
        if base is not None:
            return base
        try:
            num = float(value)
        except (ValueError, TypeError):
            return f"Cannot interpret {value!r} as float"
        if not math.isfinite(num):
            return f"Value {value!r} is not finite"
        if self.min is not None and num < self.min:
            return f"Value {num} is below minimum {self.min}"
        if self.max is not None and num > self.max:
            return f"Value {num} exceeds maximum {self.max}"
        return None


@dataclass(frozen=True)
class String(Field):
    """String field with optional length and pattern constraints.

    Args:
        min_length: Minimum string length.
        max_length: Maximum string length.
        pattern: Regex pattern the value must match (full match).
        nullable: Whether null values are allowed.
        unique: Whether all values must be unique.
        allowed: Set of allowed values.
        severity: Issue severity level.
    """

    min_length: int | None = None
    max_length: int | None = None
    pattern: str | None = None
    _compiled_pattern: Any = field(init=False, repr=False, default=None)

    def __post_init__(self) -> None:
        super().__post_init__()
        if self.min_length is not None:
            if isinstance(self.min_length, bool) or not isinstance(self.min_length, int):
                raise SchemaError(f"min_length must be int, got {type(self.min_length).__name__}")
            if self.min_length < 0:
                raise SchemaError(f"min_length must be >= 0, got {self.min_length}")
        if self.max_length is not None:
            if isinstance(self.max_length, bool) or not isinstance(self.max_length, int):
                raise SchemaError(f"max_length must be int, got {type(self.max_length).__name__}")
            if self.max_length < 0:
                raise SchemaError(f"max_length must be >= 0, got {self.max_length}")
        if (
            self.min_length is not None
            and self.max_length is not None
            and self.min_length > self.max_length
        ):
            raise SchemaError(
                f"min_length ({self.min_length}) must be <= max_length ({self.max_length})"
            )
        if self.pattern is not None:
            if not isinstance(self.pattern, str):
                raise SchemaError(f"pattern must be str, got {type(self.pattern).__name__}")
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
        if self.min_length is not None and len(s) < self.min_length:
            return f"String length {len(s)} is below minimum {self.min_length}"
        if self.max_length is not None and len(s) > self.max_length:
            return f"String length {len(s)} exceeds maximum {self.max_length}"
        if self.pattern is not None and not self._compiled_pattern.fullmatch(s):
            return f"Value {s!r} does not match pattern {self.pattern!r}"
        return None


@dataclass(frozen=True)
class Bool(Field):
    """Boolean field.

    Args:
        nullable: Whether null values are allowed.
        severity: Issue severity level.
    """

    @property
    def expected_dtype(self) -> str:
        return "bool"

    def validate_value(self, value: Any) -> str | None:
        base = super().validate_value(value)
        if base is not None:
            return base
        if not isinstance(value, (bool, int)):
            return f"Cannot interpret {value!r} as boolean"
        return None


@dataclass(frozen=True)
class Date(Field):
    """Date string field with format validation.

    Args:
        format: Expected date format (strftime-compatible).
                Defaults to ``"%Y-%m-%d"``.
        nullable: Whether null values are allowed.
        unique: Whether all values must be unique.
        severity: Issue severity level.
    """

    format: str = "%Y-%m-%d"

    def __post_init__(self) -> None:
        super().__post_init__()
        if not isinstance(self.format, str):
            raise SchemaError(f"format must be str, got {type(self.format).__name__}")

    @property
    def expected_dtype(self) -> str | None:
        return None  # Date strings can be object/string dtype

    def validate_value(self, value: Any) -> str | None:
        base = super().validate_value(value)
        if base is not None:
            return base
        s = str(value)
        try:
            datetime.strptime(s, self.format)
        except ValueError:
            return f"Value {s!r} does not match date format {self.format!r}"
        return None


@dataclass(frozen=True)
class DateTime(Field):
    """DateTime string field with format validation.

    Args:
        format: Expected datetime format (strftime-compatible).
                Defaults to ``"%Y-%m-%d %H:%M:%S"``.
        nullable: Whether null values are allowed.
        unique: Whether all values must be unique.
        severity: Issue severity level.
    """

    format: str = "%Y-%m-%d %H:%M:%S"

    def __post_init__(self) -> None:
        super().__post_init__()
        if not isinstance(self.format, str):
            raise SchemaError(f"format must be str, got {type(self.format).__name__}")

    @property
    def expected_dtype(self) -> str | None:
        return None

    def validate_value(self, value: Any) -> str | None:
        base = super().validate_value(value)
        if base is not None:
            return base
        s = str(value)
        try:
            datetime.strptime(s, self.format)
        except ValueError:
            return f"Value {s!r} does not match datetime format {self.format!r}"
        return None
