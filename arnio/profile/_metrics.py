"""Metric computations for profiling — all per-column and dataset-level metrics."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from arnio.adapt._protocol import DataFrameAdapter


def compute_null_rate(adapter: DataFrameAdapter, column: str) -> float:
    """Compute the null rate for a column (0.0 to 1.0)."""
    total = adapter.row_count()
    if total == 0:
        return 0.0
    return adapter.null_count(column) / total


def compute_unique_ratio(adapter: DataFrameAdapter, column: str) -> float:
    """Compute the unique ratio (unique / non-null count)."""
    non_null = adapter.row_count() - adapter.null_count(column)
    if non_null == 0:
        return 0.0
    return adapter.unique_count(column) / non_null


def compute_empty_string_count(adapter: DataFrameAdapter, column: str) -> int:
    """Count empty strings in a string/object column."""
    values = adapter.column_values(column)
    return sum(1 for v in values if isinstance(v, str) and v.strip() == "")


def compute_constant_column(adapter: DataFrameAdapter, column: str) -> bool:
    """Check if a column has only one unique value (or is all null)."""
    return adapter.unique_count(column) <= 1
