"""Profile report types — ColumnProfile and ProfileReport."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from arnio.adapt._protocol import NumericStats, StringLengthStats


@dataclass(frozen=True)
class ColumnProfile:
    """Quality profile for a single column.

    Attributes:
        name: Column name.
        dtype: Detected dtype string.
        null_count: Number of null values.
        null_rate: Fraction of null values (0.0 to 1.0).
        unique_count: Number of distinct non-null values.
        unique_ratio: Ratio of unique to non-null values.
        top_values: Most frequent values with counts.
        numeric_stats: Summary statistics (only for numeric columns).
        string_lengths: Length statistics (only for string columns).
        empty_string_count: Count of empty/whitespace-only strings.
        is_constant: True if column has <= 1 unique value.
        warnings: List of quality warnings for this column.
    """

    name: str
    dtype: str
    null_count: int = 0
    null_rate: float = 0.0
    unique_count: int = 0
    unique_ratio: float = 0.0
    top_values: dict[Any, int] = field(default_factory=dict)
    numeric_stats: NumericStats | None = None
    string_lengths: StringLengthStats | None = None
    empty_string_count: int = 0
    is_constant: bool = False
    warnings: tuple[str, ...] = ()


@dataclass
class ProfileReport:
    """Comprehensive data quality report.

    Attributes:
        quality_score: Overall quality score (0-100).
        row_count: Total number of rows.
        column_count: Total number of columns.
        duplicate_count: Number of duplicate rows.
        columns: Per-column profiles keyed by column name.
        suggestions: Suggested cleaning steps.
    """

    quality_score: float = 100.0
    row_count: int = 0
    column_count: int = 0
    duplicate_count: int = 0
    columns: dict[str, ColumnProfile] = field(default_factory=dict)
    suggestions: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a dict."""
        return {
            "quality_score": round(self.quality_score, 1),
            "row_count": self.row_count,
            "column_count": self.column_count,
            "duplicate_count": self.duplicate_count,
            "columns": {
                name: _column_to_dict(cp)
                for name, cp in self.columns.items()
            },
            "suggestions": self.suggestions,
        }

    def to_json(self, *, indent: int = 2) -> str:
        """Serialize to a JSON string."""
        return json.dumps(self.to_dict(), indent=indent, default=str)

    def to_markdown(self) -> str:
        """Render as a Markdown report."""
        lines = [
            "# Data Quality Report",
            "",
            f"**Quality Score:** {self.quality_score:.1f}/100",
            f"**Rows:** {self.row_count:,} | **Columns:** {self.column_count} | **Duplicates:** {self.duplicate_count:,}",
            "",
            "## Column Profiles",
            "",
            "| Column | Type | Nulls | Null% | Unique | Warnings |",
            "|--------|------|-------|-------|--------|----------|",
        ]
        for name, cp in self.columns.items():
            warn_str = ", ".join(cp.warnings) if cp.warnings else "—"
            lines.append(
                f"| {name} | {cp.dtype} | {cp.null_count:,} | "
                f"{cp.null_rate:.1%} | {cp.unique_count:,} | {warn_str} |"
            )

        if self.suggestions:
            lines.extend(["", "## Suggestions", ""])
            for s in self.suggestions:
                lines.append(f"- **{s.get('step', '?')}**: {s.get('reason', '')}")

        return "\n".join(lines) + "\n"

    def to_html(self) -> str:
        """Render as an HTML dashboard."""
        rows = "\n".join(
            f"<tr><td>{name}</td><td>{cp.dtype}</td>"
            f"<td>{cp.null_count:,}</td><td>{cp.null_rate:.1%}</td>"
            f"<td>{cp.unique_count:,}</td>"
            f"<td>{', '.join(cp.warnings) or '—'}</td></tr>"
            for name, cp in self.columns.items()
        )

        score_color = (
            "#22c55e" if self.quality_score >= 80
            else "#f59e0b" if self.quality_score >= 50
            else "#ef4444"
        )

        return (
            f'<div class="arnio-profile">'
            f'<h2>Data Quality Report</h2>'
            f'<div class="score" style="color:{score_color};font-size:2em;font-weight:bold;">'
            f'{self.quality_score:.1f}/100</div>'
            f'<p>{self.row_count:,} rows · {self.column_count} columns · '
            f'{self.duplicate_count:,} duplicates</p>'
            f'<table><thead><tr>'
            f'<th>Column</th><th>Type</th><th>Nulls</th><th>Null%</th>'
            f'<th>Unique</th><th>Warnings</th>'
            f'</tr></thead><tbody>{rows}</tbody></table></div>'
        )

    def _repr_html_(self) -> str:
        """Jupyter notebook rendering."""
        return self.to_html()

    def __repr__(self) -> str:
        return (
            f"ProfileReport(score={self.quality_score:.1f}, "
            f"rows={self.row_count:,}, columns={self.column_count})"
        )


def _column_to_dict(cp: ColumnProfile) -> dict[str, Any]:
    """Serialize a ColumnProfile to a dict."""
    result: dict[str, Any] = {
        "name": cp.name,
        "dtype": cp.dtype,
        "null_count": cp.null_count,
        "null_rate": round(cp.null_rate, 4),
        "unique_count": cp.unique_count,
        "unique_ratio": round(cp.unique_ratio, 4),
        "top_values": {str(k): v for k, v in cp.top_values.items()},
        "is_constant": cp.is_constant,
        "warnings": list(cp.warnings),
    }
    if cp.numeric_stats is not None:
        result["numeric_stats"] = {
            "mean": cp.numeric_stats.mean,
            "std": cp.numeric_stats.std,
            "min": cp.numeric_stats.min,
            "max": cp.numeric_stats.max,
            "median": cp.numeric_stats.median,
            "q1": cp.numeric_stats.q1,
            "q3": cp.numeric_stats.q3,
        }
    if cp.string_lengths is not None:
        result["string_lengths"] = {
            "min_length": cp.string_lengths.min_length,
            "max_length": cp.string_lengths.max_length,
            "mean_length": round(cp.string_lengths.mean_length, 1),
        }
    if cp.empty_string_count > 0:
        result["empty_string_count"] = cp.empty_string_count
    return result
