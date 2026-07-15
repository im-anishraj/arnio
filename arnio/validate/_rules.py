"""Built-in validation rules.

Each rule is a focused function that checks one aspect of a column.
The engine orchestrates these rules for each schema field.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Any

import pandas as pd

from arnio.validate._result import Issue

if TYPE_CHECKING:
    from arnio.adapt._protocol import DataFrameAdapter
    from arnio.schema._fields import Field


def check_column_exists(
    adapter: DataFrameAdapter, column: str, field_def: Field
) -> Issue | None:
    """Check that a column exists in the data."""
    if column not in adapter.column_names():
        return Issue(
            column=column,
            rule="column_exists",
            message=f"Column {column!r} is missing from the data",
            severity=field_def.severity,
        )
    return None


def check_null_constraint(
    adapter: DataFrameAdapter, column: str, field_def: Field
) -> Issue | None:
    """Check that non-nullable columns have no null values."""
    if field_def.nullable:
        return None
    null_count = adapter.null_count(column)
    if null_count > 0:
        return Issue(
            column=column,
            rule="not_nullable",
            message=f"Column {column!r} has {null_count} null value(s) but is not nullable",
            severity=field_def.severity,
        )
    return None


def check_uniqueness(
    adapter: DataFrameAdapter, column: str, field_def: Field
) -> Issue | None:
    """Check that unique-constrained columns have all distinct values."""
    if not field_def.unique:
        return None
    unique = adapter.unique_count(column)
    total = adapter.row_count() - adapter.null_count(column)
    if total > 0 and unique < total:
        dup_count = total - unique
        return Issue(
            column=column,
            rule="unique",
            message=f"Column {column!r} has {dup_count} duplicate value(s)",
            severity=field_def.severity,
        )
    return None


def check_dtype_compatibility(
    adapter: DataFrameAdapter, column: str, field_def: Field
) -> Issue | None:
    """Check that the column dtype is compatible with the field type."""
    expected = field_def.expected_dtype
    if expected is None:
        return None

    actual = adapter.column_dtype(column)

    # Flexible compatibility rules
    compatible: dict[str, set[str]] = {
        "int64": {"int64", "float64"},  # int columns are often float64 due to NaN
        "float64": {"float64", "int64"},
        "string": {"string", "object"},
        "bool": {"bool", "int64", "object"},
        "datetime": {"datetime", "object"},
    }

    allowed_dtypes = compatible.get(expected, {expected})
    if actual not in allowed_dtypes:
        return Issue(
            column=column,
            rule="dtype",
            message=f"Column {column!r} has dtype {actual!r}, expected compatible with {expected!r}",
            severity="warning",  # dtype mismatches are warnings, not errors
        )
    return None


def check_allowed_values(
    adapter: DataFrameAdapter, column: str, field_def: Field
) -> list[Issue]:
    """Check that all values are in the allowed set."""
    if field_def.allowed is None:
        return []

    total_non_null = adapter.row_count() - adapter.null_count(column)
    if total_non_null == 0:
        return []

    in_set = adapter.values_in_set(column, set(field_def.allowed))
    violations = total_non_null - in_set

    if violations > 0:
        return [Issue(
            column=column,
            rule="allowed_values",
            message=f"Column {column!r} has {violations} value(s) not in the allowed set",
            severity=field_def.severity,
        )]
    return []


def check_per_value_validation(
    adapter: DataFrameAdapter,
    column: str,
    field_def: Field,
    *,
    max_issues: int | None = 100,
) -> list[Issue]:
    """Run per-value validation using the adapter's vectorized checks.

    This handles semantic validation (email format, URL format, etc.),
    min/max for numeric fields, and pattern matching for string fields.
    """
    return adapter.check_per_value(column, field_def, max_issues=max_issues)


def _is_null(value: Any) -> bool:
    """Check if a value is null-like."""
    if value is None:
        return True
    try:
        if math.isnan(value):
            return True
    except (TypeError, ValueError):
        pass
    # pandas NA / NaT
    try:
        if pd.isna(value):
            return True
    except (TypeError, ValueError):
        pass
    return False
