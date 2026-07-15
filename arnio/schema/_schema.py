"""Schema class — define what trustworthy data looks like.

Supports both dict-based and class-based definition:

    # Dict-based
    schema = ar.Schema({"email": ar.Email(), "age": ar.Int(min=0)})

    # Class-based
    class Customers(ar.Schema):
        email = ar.Email()
        age = ar.Int(min=0)

Both produce the same internal representation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from arnio.exceptions import SchemaError
from arnio.schema._fields import Field

if TYPE_CHECKING:
    from collections.abc import Iterator


class _SchemaMeta(type):
    """Metaclass that collects Field annotations from class body.

    When a user writes:

        class MySchema(Schema):
            name = String()
            age = Int(min=0)

    This metaclass collects the Field instances into the ``_fields`` dict
    so that Schema instances can be used interchangeably whether created
    via dict or class syntax.
    """

    def __new__(
        mcs,
        name: str,
        bases: tuple[type, ...],
        namespace: dict[str, Any],
        **kwargs: Any,
    ) -> _SchemaMeta:
        fields: dict[str, Field] = {}

        # Inherit fields from parent schema classes
        for base in bases:
            if hasattr(base, "_fields") and isinstance(base._fields, dict):
                fields.update(base._fields)

        # Collect Field instances from class body
        for attr_name, attr_value in namespace.items():
            if isinstance(attr_value, Field):
                fields[attr_name] = attr_value

        namespace["_fields"] = fields
        cls = super().__new__(mcs, name, bases, namespace, **kwargs)
        return cls


class Schema(metaclass=_SchemaMeta):
    """Named column validation contract.

    Can be created in two ways:

    **Dict-based** (dynamic, config-driven)::

        schema = ar.Schema({
            "email": ar.Email(nullable=False),
            "age": ar.Int(min=0, max=150),
        })

    **Class-based** (IDE-friendly, inheritable)::

        class Customers(ar.Schema):
            email = ar.Email(nullable=False)
            age = ar.Int(min=0, max=150)

    Args:
        fields: Mapping of column names to Field instances.
                Only needed for dict-based construction.
        strict: If True, columns not in the schema raise an error.
        allow_extra: If True (default), ignore columns not in schema.
    """

    _fields: dict[str, Field]

    def __init__(
        self,
        fields: dict[str, Field] | None = None,
        *,
        strict: bool = False,
        allow_extra: bool = True,
    ) -> None:
        if fields is not None:
            # Dict-based construction
            if not fields:
                raise SchemaError("Schema must define at least one field.")
            self._validate_fields_dict(fields)
            self._fields = dict(fields)
        elif not self._fields:
            raise SchemaError(
                "Schema requires either a fields dict or class-level Field definitions."
            )

        self.strict = strict
        self.allow_extra = allow_extra

        if strict and allow_extra:
            # strict=True implies allow_extra=False
            self.allow_extra = False

    @staticmethod
    def _validate_fields_dict(fields: dict[str, Field]) -> None:
        """Validate that a fields dict is well-formed."""
        if not isinstance(fields, dict):
            raise SchemaError(
                f"Schema fields must be a dict, got {type(fields).__name__}"
            )
        for name, field_def in fields.items():
            if not isinstance(name, str):
                raise SchemaError(
                    f"Field names must be strings, got {type(name).__name__}: {name!r}"
                )
            if not isinstance(field_def, Field):
                raise SchemaError(
                    f"Field {name!r} must be a Field instance (e.g., ar.Int()), "
                    f"got {type(field_def).__name__}"
                )

    @property
    def fields(self) -> dict[str, Field]:
        """Return the schema's field definitions."""
        return dict(self._fields)

    @property
    def column_names(self) -> list[str]:
        """Return all column names defined in the schema."""
        return list(self._fields.keys())

    @property
    def required_columns(self) -> list[str]:
        """Return columns that are non-nullable (must exist and have values)."""
        return [
            name for name, f in self._fields.items()
            if not f.nullable
        ]

    def __contains__(self, column: str) -> bool:
        return column in self._fields

    def __getitem__(self, column: str) -> Field:
        return self._fields[column]

    def __len__(self) -> int:
        return len(self._fields)

    def __iter__(self) -> Iterator[str]:
        return iter(self._fields)

    def __repr__(self) -> str:
        field_strs = ", ".join(
            f"{name!r}: {field_def.__class__.__name__}(...)"
            for name, field_def in self._fields.items()
        )
        return f"Schema({{{field_strs}}})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Schema):
            return NotImplemented
        return self._fields == other._fields
