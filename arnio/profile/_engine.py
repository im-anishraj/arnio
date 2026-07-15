"""Profiling engine — core logic for ``ar.profile(data)``."""

from __future__ import annotations

import contextlib
from typing import Any

from arnio.adapt._detect import resolve_adapter
from arnio.profile._metrics import (
    compute_constant_column,
    compute_empty_string_count,
    compute_null_rate,
    compute_unique_ratio,
)
from arnio.profile._report import ColumnProfile, ProfileReport
from arnio.profile._suggest import _suggest_from_profiles


def profile(data: Any) -> ProfileReport:
    """Profile data quality and return a comprehensive report.

    Computes per-column metrics (null rate, unique ratio, value counts,
    numeric stats, string lengths) and dataset-level metrics (quality score,
    duplicate count). Attaches cleaning suggestions.

    Args:
        data: Any supported data type (pandas DataFrame, list of dicts, etc.)

    Returns:
        A ProfileReport with quality score, column profiles, and suggestions.
    """
    adapter = resolve_adapter(data)
    columns: dict[str, ColumnProfile] = {}

    for col in adapter.column_names():
        dtype = adapter.column_dtype(col)
        null_count = adapter.null_count(col)
        null_rate = compute_null_rate(adapter, col)
        unique_count = adapter.unique_count(col)
        unique_ratio = compute_unique_ratio(adapter, col)
        top_values = adapter.value_counts(col, top_n=10)
        is_constant = compute_constant_column(adapter, col)

        warnings: list[str] = []

        # Compute type-specific stats
        numeric_stats = None
        string_lengths = None
        empty_string_count = 0

        if dtype in ("int64", "float64"):
            with contextlib.suppress(Exception):
                numeric_stats = adapter.numeric_stats(col)

        if dtype in ("string", "object"):
            with contextlib.suppress(Exception):
                string_lengths = adapter.string_lengths(col)
            empty_string_count = compute_empty_string_count(adapter, col)

        # Detect quality warnings
        if null_rate == 1.0:
            warnings.append("all_null")
        elif null_rate > 0.5:
            warnings.append("high_null_rate")

        if is_constant and adapter.row_count() > 0:
            warnings.append("constant")

        row_count = adapter.row_count()
        if row_count > 0 and unique_ratio > 0.95 and unique_count > 50:
            warnings.append("high_cardinality")

        if empty_string_count > 0:
            warnings.append("has_empty_strings")

        columns[col] = ColumnProfile(
            name=col,
            dtype=dtype,
            null_count=null_count,
            null_rate=null_rate,
            unique_count=unique_count,
            unique_ratio=unique_ratio,
            top_values=top_values,
            numeric_stats=numeric_stats,
            string_lengths=string_lengths,
            empty_string_count=empty_string_count,
            is_constant=is_constant,
            warnings=tuple(warnings),
        )

    # Compute dataset-level metrics
    row_count = adapter.row_count()
    column_count = len(adapter.column_names())
    duplicate_count = adapter.duplicate_count()

    # Compute quality score
    quality_score = _compute_quality_score(columns, row_count, duplicate_count)

    # Generate suggestions
    suggestions = _suggest_from_profiles(columns, duplicate_count)

    return ProfileReport(
        quality_score=quality_score,
        row_count=row_count,
        column_count=column_count,
        duplicate_count=duplicate_count,
        columns=columns,
        suggestions=suggestions,
    )


def _compute_quality_score(
    columns: dict[str, ColumnProfile],
    row_count: int,
    duplicate_count: int,
) -> float:
    """Compute an overall quality score from 0 to 100.

    Scoring factors:
    - Completeness (null rates across columns) — 40 points
    - Uniqueness (duplicate rows) — 20 points
    - Consistency (constant columns, high cardinality) — 20 points
    - Validity (empty strings, warnings) — 20 points
    """
    if not columns or row_count == 0:
        return 100.0

    # Completeness: average (1 - null_rate) across columns
    avg_completeness = sum(1 - cp.null_rate for cp in columns.values()) / len(columns)
    completeness_score = avg_completeness * 40

    # Uniqueness: penalize duplicate rows
    dup_rate = duplicate_count / row_count if row_count > 0 else 0
    uniqueness_score = (1 - dup_rate) * 20

    # Consistency: penalize constant and all-null columns
    problem_cols = sum(
        1 for cp in columns.values()
        if cp.is_constant or cp.null_rate == 1.0
    )
    consistency_score = max(0, (1 - problem_cols / len(columns)) * 20)

    # Validity: penalize columns with warnings
    warning_cols = sum(1 for cp in columns.values() if cp.warnings)
    validity_score = max(0, (1 - warning_cols / len(columns)) * 20)

    return round(
        completeness_score + uniqueness_score + consistency_score + validity_score,
        1,
    )
