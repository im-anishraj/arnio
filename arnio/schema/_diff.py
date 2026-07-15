"""Schema diff — compare two schemas to detect drift.

``diff_schemas(a, b)`` returns a structured diff showing what changed.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from arnio.schema._fields import Field
    from arnio.schema._schema import Schema


@dataclass(frozen=True)
class FieldDiff:
    """Diff for a single field between two schemas.

    Attributes:
        column: Column name.
        change_type: One of "added", "removed", "modified".
        old_field: The field in schema A (None if added).
        new_field: The field in schema B (None if removed).
        details: Human-readable list of what changed.
    """

    column: str
    change_type: str
    old_field: Field | None = None
    new_field: Field | None = None
    details: tuple[str, ...] = ()


@dataclass(frozen=True)
class SchemaDiff:
    """Result of comparing two schemas.

    Attributes:
        changes: List of per-field diffs.
        is_identical: True if schemas are equivalent.
    """

    changes: tuple[FieldDiff, ...] = ()

    @property
    def is_identical(self) -> bool:
        return len(self.changes) == 0

    def __bool__(self) -> bool:
        return not self.is_identical

    def __repr__(self) -> str:
        if self.is_identical:
            return "SchemaDiff(identical)"
        summaries = [
            f"  {c.change_type}: {c.column}" for c in self.changes
        ]
        return "SchemaDiff(\n" + "\n".join(summaries) + "\n)"


def _compare_fields(column: str, old: Field, new: Field) -> FieldDiff | None:
    """Compare two field definitions, return a diff if they differ."""
    if old == new:
        return None

    details: list[str] = []

    if type(old) is not type(new):
        details.append(
            f"type changed from {type(old).__name__} to {type(new).__name__}"
        )
    else:
        # Same type — compare all dataclass fields
        import dataclasses

        for dc_field in dataclasses.fields(old):
            old_val = getattr(old, dc_field.name)
            new_val = getattr(new, dc_field.name)
            if old_val != new_val:
                details.append(
                    f"{dc_field.name} changed from {old_val!r} to {new_val!r}"
                )

    # If types differ, also check common base attributes
    if type(old) is not type(new):
        if old.nullable != new.nullable:
            details.append(
                f"nullable changed from {old.nullable} to {new.nullable}"
            )
        if old.unique != new.unique:
            details.append(
                f"unique changed from {old.unique} to {new.unique}"
            )
        if old.allowed != new.allowed:
            details.append("allowed values changed")

    return FieldDiff(
        column=column,
        change_type="modified",
        old_field=old,
        new_field=new,
        details=tuple(details) if details else ("field definition changed",),
    )


def diff_schemas(a: Schema, b: Schema) -> SchemaDiff:
    """Compare two schemas and return a structured diff.

    Args:
        a: The "before" schema.
        b: The "after" schema.

    Returns:
        A SchemaDiff with all changes between the two schemas.
    """
    changes: list[FieldDiff] = []

    all_columns = dict.fromkeys([*a.column_names, *b.column_names])

    for col in all_columns:
        in_a = col in a
        in_b = col in b

        if in_a and not in_b:
            changes.append(FieldDiff(
                column=col, change_type="removed", old_field=a[col],
            ))
        elif not in_a and in_b:
            changes.append(FieldDiff(
                column=col, change_type="added", new_field=b[col],
            ))
        else:
            diff = _compare_fields(col, a[col], b[col])
            if diff is not None:
                changes.append(diff)

    return SchemaDiff(changes=tuple(changes))
