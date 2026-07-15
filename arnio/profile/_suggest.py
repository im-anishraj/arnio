"""Suggest cleaning steps based on profiling results.

``suggest()`` analyzes profiling data to recommend cleaning operations.
This is Arnio's most unique feature — intelligent, profile-driven suggestions.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from arnio.profile._report import ColumnProfile


def _suggest_from_profiles(
    columns: dict[str, ColumnProfile],
    duplicate_count: int,
) -> list[dict[str, Any]]:
    """Generate cleaning suggestions from column profiles.

    Each suggestion includes: step, params, reason, confidence, impact.
    """
    suggestions: list[dict[str, Any]] = []

    # Check for duplicate rows
    if duplicate_count > 0:
        suggestions.append({
            "step": "drop_duplicates",
            "params": {},
            "reason": f"{duplicate_count} duplicate row(s) detected",
            "confidence": 0.9,
            "impact": f"{duplicate_count} rows would be removed",
        })

    # Per-column suggestions
    strip_cols: list[str] = []
    high_null_cols: list[str] = []
    empty_str_cols: list[str] = []

    for name, cp in columns.items():
        # Detect whitespace issues in string columns
        if cp.dtype in ("string", "object") and cp.empty_string_count > 0:
            strip_cols.append(name)
            empty_str_cols.append(name)

        # Detect high null rate
        if cp.null_rate > 0.5 and cp.null_rate < 1.0:
            high_null_cols.append(name)

        # Detect all-null columns
        if cp.null_rate == 1.0:
            suggestions.append({
                "step": "drop_columns",
                "params": {"columns": [name]},
                "reason": f"Column {name!r} is entirely null",
                "confidence": 0.95,
                "impact": "1 column would be removed",
            })

        # Detect constant columns
        if cp.is_constant and cp.null_rate < 1.0:
            suggestions.append({
                "step": "drop_columns",
                "params": {"columns": [name]},
                "reason": f"Column {name!r} has only one unique value (constant)",
                "confidence": 0.7,
                "impact": "1 column would be removed",
            })

    # Batch whitespace suggestion
    if strip_cols:
        suggestions.append({
            "step": "strip_whitespace",
            "params": {"columns": strip_cols},
            "reason": f"Empty/whitespace strings detected in {len(strip_cols)} column(s)",
            "confidence": 0.85,
            "impact": f"Affects {len(strip_cols)} column(s)",
        })

    # High null rate suggestion
    for col in high_null_cols:
        cp = columns[col]
        suggestions.append({
            "step": "fill_nulls",
            "params": {"column": col},
            "reason": f"Column {col!r} has {cp.null_rate:.0%} null values",
            "confidence": 0.5,
            "impact": f"{cp.null_count} values would be filled",
        })

    # Sort by confidence (highest first)
    suggestions.sort(key=lambda s: s.get("confidence", 0), reverse=True)

    return suggestions


def suggest(data: Any) -> list[dict[str, Any]]:
    """Auto-suggest cleaning steps based on data profiling.

    Profiles the data internally and analyzes the results to recommend
    cleaning operations. Each suggestion includes:

    - **step**: The cleaning step name (compatible with ``ar.clean()``)
    - **params**: Parameters for the step
    - **reason**: Why this step is suggested
    - **confidence**: How confident Arnio is (0.0 to 1.0)
    - **impact**: Estimated impact description

    Args:
        data: Any supported data type.

    Returns:
        A list of suggestion dicts, sorted by confidence (highest first).
    """
    from arnio.profile._engine import profile

    report = profile(data)
    return report.suggestions
