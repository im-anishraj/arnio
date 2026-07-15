"""Built-in cleaning step definitions.

Each step is a function that takes an adapter and optional params,
and returns a new adapter with the cleaning applied.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from arnio.adapt._protocol import DataFrameAdapter


def step_strip_whitespace(
    adapter: DataFrameAdapter, *, columns: list[str] | None = None
) -> DataFrameAdapter:
    """Strip leading/trailing whitespace from string columns."""
    return adapter.strip_whitespace(columns)


def step_normalize_case(
    adapter: DataFrameAdapter,
    *,
    columns: list[str] | None = None,
    case: str = "lower",
) -> DataFrameAdapter:
    """Normalize string case to lower/upper/title."""
    return adapter.normalize_case(columns, case=case)


def step_drop_duplicates(adapter: DataFrameAdapter) -> DataFrameAdapter:
    """Remove duplicate rows."""
    return adapter.drop_duplicates()


def step_drop_nulls(
    adapter: DataFrameAdapter,
    *,
    columns: list[str] | None = None,
    how: str = "any",
) -> DataFrameAdapter:
    """Remove rows with null values."""
    return adapter.drop_nulls(columns, how=how)


def step_fill_nulls(
    adapter: DataFrameAdapter, *, column: str, value: Any
) -> DataFrameAdapter:
    """Fill null values in a column."""
    return adapter.fill_nulls(column, value)


def step_slugify_column_names(adapter: DataFrameAdapter) -> DataFrameAdapter:
    """Normalize column names to snake_case."""
    return adapter.slugify_column_names()


def step_standardize_missing(
    adapter: DataFrameAdapter,
    *,
    tokens: set[str] | None = None,
    columns: list[str] | None = None,
) -> DataFrameAdapter:
    """Replace common missing-value tokens with actual null."""
    return adapter.standardize_missing(tokens, columns)


def step_rename_columns(
    adapter: DataFrameAdapter, *, mapping: dict[str, str]
) -> DataFrameAdapter:
    """Rename columns according to a mapping."""
    return adapter.rename_columns(mapping)


def step_drop_columns(
    adapter: DataFrameAdapter, *, columns: list[str]
) -> DataFrameAdapter:
    """Drop specified columns."""
    return adapter.drop_columns(columns)


def step_replace_values(
    adapter: DataFrameAdapter, *, column: str, mapping: dict[Any, Any]
) -> DataFrameAdapter:
    """Replace values in a column."""
    return adapter.replace_values(column, mapping)


def step_cast_column(
    adapter: DataFrameAdapter, *, column: str, dtype: str
) -> DataFrameAdapter:
    """Cast a column to a different type."""
    return adapter.cast_column(column, dtype)
