"""Validation engine — core logic for ``ar.validate(data, schema)``."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from arnio.adapt._detect import resolve_adapter
from arnio.schema._schema import Schema
from arnio.validate._result import Issue, ValidationResult
from arnio.validate._rules import (
    check_allowed_values,
    check_column_exists,
    check_dtype_compatibility,
    check_null_constraint,
    check_per_value_validation,
    check_uniqueness,
)

if TYPE_CHECKING:
    from arnio.schema._fields import Field


def validate(
    data: Any,
    schema: Schema | dict[str, Field],
    *,
    max_errors: int | None = None,
) -> ValidationResult:
    """Validate data against a schema. Return structured results.

    **Never raises on bad data.** Returns a ``ValidationResult`` with
    all issues found. Users decide what to do with the results.

    Args:
        data: Any supported data type (pandas DataFrame, list of dicts, etc.)
        schema: A Schema instance or a dict mapping column names to Field instances.
        max_errors: Maximum number of issues to collect. None = unlimited.

    Returns:
        A ValidationResult containing all validation issues.

    Raises:
        AdapterError: If the data type is not supported.
        SchemaError: If the schema definition is invalid.
    """
    # Normalize schema input
    if isinstance(schema, dict):
        schema = Schema(schema)

    adapter = resolve_adapter(data)
    issues: list[Issue] = []

    def _add(issue: Issue | None) -> None:
        if issue is not None:
            issues.append(issue)

    def _add_many(new_issues: list[Issue]) -> None:
        issues.extend(new_issues)

    def _at_limit() -> bool:
        return max_errors is not None and len(issues) >= max_errors

    # Check for extra columns in strict mode
    if schema.strict or not schema.allow_extra:
        data_columns = set(adapter.column_names())
        schema_columns = set(schema.column_names)
        extra = data_columns - schema_columns
        for col in sorted(extra):
            if _at_limit():
                break
            _add(Issue(
                column=col,
                rule="no_extra_columns",
                message=f"Column {col!r} is not defined in the schema (strict mode)",
                severity="error",
            ))

    # Validate each schema field
    for col_name, field_def in schema.fields.items():
        if _at_limit():
            break

        # 1. Column existence
        exists_issue = check_column_exists(adapter, col_name, field_def)
        if exists_issue is not None:
            _add(exists_issue)
            continue  # Can't check further if column doesn't exist

        # 2. Dtype compatibility
        _add(check_dtype_compatibility(adapter, col_name, field_def))
        if _at_limit():
            break

        # 3. Null constraint
        _add(check_null_constraint(adapter, col_name, field_def))
        if _at_limit():
            break

        # 4. Uniqueness
        _add(check_uniqueness(adapter, col_name, field_def))
        if _at_limit():
            break

        # 5. Allowed values (set-level check — fast)
        _add_many(check_allowed_values(adapter, col_name, field_def))
        if _at_limit():
            break

        # 6. Per-value validation (semantic, min/max, pattern)
        remaining = (max_errors - len(issues)) if max_errors is not None else None
        _add_many(check_per_value_validation(
            adapter, col_name, field_def, max_issues=remaining,
        ))

    # Trim to max_errors
    if max_errors is not None:
        issues = issues[:max_errors]

    return ValidationResult(issues=issues)
