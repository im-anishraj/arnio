"""
arnio.quality
Data quality profiling and safe automatic cleaning helpers.
"""

from __future__ import annotations

import html
import json
import math
import os
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

from .cleaning import (
    _validate_column_sequence,
    cast_types,
    drop_duplicates,
    strip_whitespace,
    validate_columns_exist,
)
from .convert import to_pandas
from .frame import ArFrame


class CleaningSuggestion(tuple):
    """A data quality cleaning suggestion that is backwards-compatible with tuples.

    Exposes `step` and `kwargs` like a regular 2-tuple, but also carries
    `confidence_score` and `confidence_reason` attributes.
    """

    def __new__(
        cls,
        step: str,
        kwargs: dict[str, Any],
        confidence_score: float,
        confidence_reason: str,
    ) -> CleaningSuggestion:
        instance = super().__new__(cls, (step, kwargs))
        instance._confidence_score = float(confidence_score)
        instance._confidence_reason = str(confidence_reason)
        return instance

    @property
    def step(self) -> str:
        return self[0]

    @property
    def kwargs(self) -> dict[str, Any]:
        return self[1]

    @property
    def confidence_score(self) -> float:
        return self._confidence_score

    @property
    def confidence_reason(self) -> str:
        return self._confidence_reason

    def __getnewargs__(self) -> tuple[str, dict[str, Any], float, str]:
        return (self.step, self.kwargs, self.confidence_score, self.confidence_reason)

    def __repr__(self) -> str:
        return (
            f"CleaningSuggestion(step={self.step!r}, kwargs={self.kwargs!r}, "
            f"confidence_score={self.confidence_score:.2f}, "
            f"confidence_reason={self.confidence_reason!r})"
        )


@dataclass(frozen=True)
class ColumnProfile:
    """Quality profile for one column.

    For numeric columns ``min``, ``max``, and ``mean`` report **value**
    statistics.  For string columns the same fields report **string-length**
    statistics (minimum length, maximum length, and mean length of non-null
    values).

    ``empty_string_count`` is the number of non-null values that become empty
    after stripping leading/trailing whitespace — whitespace-only strings are
    therefore counted as empty.

    ``top_values_is_approximate`` indicates whether ``top_values`` were
    estimated from a deterministic sample. When ``True``,
    ``top_values_sample_count`` and ``top_values_sample_ratio`` describe the
    sample used for the counts/ratios.
    """

    name: str
    dtype: str
    semantic_type: str
    row_count: int
    null_count: int
    null_ratio: float
    unique_count: int
    unique_ratio: float
    empty_string_count: int = 0
    whitespace_count: int = 0
    suggested_dtype: str | None = None
    email_validity_ratio: float | None = None
    url_validity_ratio: float | None = None
    min: Any = None
    max: Any = None
    mean: float | None = None
    std: float | None = None
    q25: float | None = None
    q50: float | None = None
    q75: float | None = None
    q95: float | None = None
    sample_values: list[Any] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    top_values: list[tuple[Any, int, float]] | None = None
    top_values_is_approximate: bool = False
    top_values_sample_count: int | None = None
    top_values_sample_ratio: float | None = None
    histogram: list[tuple[float, float, int, float]] | None = None

    def to_dict(self, *, redact_sample_values: bool = False) -> dict[str, Any]:
        """Return a JSON-friendly dictionary."""
        redact_sample_values = _validate_bool_option(
            redact_sample_values, "redact_sample_values"
        )
        sample_values = (
            ["[REDACTED]" for _ in self.sample_values]
            if redact_sample_values
            else [_clean_scalar(value) for value in self.sample_values]
        )
        top_values = (
            [
                {"value": "[REDACTED]", "count": c, "ratio": r}
                for _value, c, r in self.top_values
            ]
            if redact_sample_values and self.top_values is not None
            else (
                [
                    {"value": _clean_scalar(v), "count": c, "ratio": r}
                    for v, c, r in self.top_values
                ]
                if self.top_values is not None
                else None
            )
        )
        return {
            "name": self.name,
            "dtype": self.dtype,
            "semantic_type": self.semantic_type,
            "row_count": self.row_count,
            "null_count": self.null_count,
            "null_ratio": self.null_ratio,
            "unique_count": self.unique_count,
            "unique_ratio": self.unique_ratio,
            "empty_string_count": self.empty_string_count,
            "whitespace_count": self.whitespace_count,
            "suggested_dtype": self.suggested_dtype,
            "email_validity_ratio": self.email_validity_ratio,
            "url_validity_ratio": self.url_validity_ratio,
            "min": _clean_scalar(self.min),
            "max": _clean_scalar(self.max),
            "mean": self.mean,
            "std": self.std,
            **(
                {
                    "q25": _clean_scalar(self.q25),
                    "q50": _clean_scalar(self.q50),
                    "q75": _clean_scalar(self.q75),
                    "q95": _clean_scalar(self.q95),
                }
                if _is_numeric_dtype(self.dtype)
                else {}
            ),
            "sample_values": sample_values,
            "warnings": list(self.warnings),
            "top_values": top_values,
            "top_values_is_approximate": self.top_values_is_approximate,
            "top_values_sample_count": self.top_values_sample_count,
            "top_values_sample_ratio": self.top_values_sample_ratio,
            "histogram": (
                [
                    {
                        "bucket_start": _clean_scalar(start),
                        "bucket_end": _clean_scalar(end),
                        "count": count,
                        "ratio": ratio,
                    }
                    for start, end, count, ratio in self.histogram
                ]
                if self.histogram is not None
                else None
            ),
        }


@dataclass(frozen=True)
class DataQualityReport:
    """Whole-frame data quality report."""

    row_count: int
    column_count: int
    memory_usage: int
    duplicate_rows: int
    duplicate_ratio: float
    columns: dict[str, ColumnProfile]
    quality_score: float = 100.0
    score_components: dict[str, float] = field(default_factory=dict)
    suggestions: list[tuple[str, dict[str, Any]]] = field(default_factory=list)

    def to_dict(
        self,
        *,
        redact_sample_values: bool = False,
        exclude_columns: list[str] | set[str] | tuple[str, ...] | None = None,
    ) -> dict[str, Any]:
        """Return a JSON-friendly dictionary representation."""
        redact_sample_values = _validate_bool_option(
            redact_sample_values, "redact_sample_values"
        )

        if exclude_columns is None:
            exclude_columns = set()

        elif not isinstance(exclude_columns, (list, tuple, set)):
            raise TypeError("exclude_columns must be a list, tuple, set, or None")

        else:
            if not all(isinstance(column, str) for column in exclude_columns):
                raise TypeError("exclude_columns must contain only string column names")

            exclude_columns = set(exclude_columns)

        def _redact_reason(reason: str | None) -> str | None:
            if not reason or not exclude_columns:
                return reason
            for col in exclude_columns:
                reason = reason.replace(f"'{col}'", "'[REDACTED]'")
            return reason

        return {
            "row_count": self.row_count,
            "column_count": self.column_count,
            "memory_usage": self.memory_usage,
            "duplicate_rows": self.duplicate_rows,
            "duplicate_ratio": self.duplicate_ratio,
            "quality_score": self.quality_score,
            "score_components": self.score_components,
            "columns": {
                name: self.columns[name].to_dict(
                    redact_sample_values=redact_sample_values
                )
                for name in sorted(self.columns)
                if name not in exclude_columns
            },
            "suggestions": [
                {
                    "step": s[0],
                    "kwargs": (
                        {
                            k: v
                            for k, v in dict(s[1]).items()
                            if k not in exclude_columns
                        }
                        if s[0] == "cast_types"
                        else {
                            key: (
                                [item for item in value if item not in exclude_columns]
                                if key in {"subset", "columns"}
                                and isinstance(value, list)
                                else (
                                    {
                                        col_name: col_type
                                        for col_name, col_type in value.items()
                                        if col_name not in exclude_columns
                                    }
                                    if key == "cast_types" and isinstance(value, dict)
                                    else value
                                )
                            )
                        )
                        for key, value in sorted(dict(s[1]).items())
                    },
                            for key, value in dict(s[1]).items()
                        }
                    ),
                    "confidence_score": getattr(s, "confidence_score", None),
                    "confidence_reason": _redact_reason(
                        getattr(s, "confidence_reason", None)
                    ),
                }
                for s in sorted(
                    self.suggestions,
                    key=lambda item: (
                        item[0],
                        json.dumps(item[1], sort_keys=True, default=str),
                    ),
                )
            ],
        }

    def __repr__(self) -> str:
        """Deterministic concise representation for terminals and notebooks."""

        column_names = sorted(self.columns)

        preview = ", ".join(column_names[:5])

        if len(column_names) > 5:
            preview += ", ..."

        return (
            "DataQualityReport("
            f"rows={self.row_count}, "
            f"columns={self.column_count}, "
            f"duplicates={self.duplicate_rows}, "
            f"quality_score={self.quality_score:.2f}, "
            f"column_names=[{preview}]"
            ")"
        )

    __str__ = __repr__

    def to_json(
        self,
        *,
        indent: int | None = None,
        redact_sample_values: bool = False,
        exclude_columns: list[str] | set[str] | tuple[str, ...] | None = None,
        output: Any | None = None,
    ) -> str | None:
        """Return the report as a JSON string.

        Example:
        report.to_json(indent=2)
        """

        json_out = json.dumps(
            self.to_dict(
                redact_sample_values=redact_sample_values,
                exclude_columns=exclude_columns,
            ),
            indent=indent,
        )

        if output is None:
            return json_out

        if not hasattr(output, "write"):
            raise TypeError("output must be a writable text stream")

        output.write(json_out)
        return None

    @staticmethod
    def _validate_max_suggestions(max_suggestions: int | None) -> int | None:
        if max_suggestions is None:
            return None
        if not isinstance(max_suggestions, int) or isinstance(max_suggestions, bool):
            raise TypeError("max_suggestions must be an integer or None")
        if max_suggestions <= 0:
            raise ValueError("max_suggestions must be positive")
        return max_suggestions

    def to_markdown(
        self,
        output: Any | None = None,
        max_suggestions: int | None = None,
    ) -> str | None:
        """Return a GitHub-friendly Markdown report."""
        max_suggestions = self._validate_max_suggestions(max_suggestions)

        lines: list[str] = []

        lines.append("# Data Quality Report")
        lines.append("")

        # Overview
        lines.append("## Overview")
        lines.append("")
        lines.append(f"- Rows: {self.row_count}")
        lines.append(f"- Columns: {self.column_count}")
        lines.append(f"- Memory Usage: {self.memory_usage}")
        lines.append(f"- Duplicate Rows: {self.duplicate_rows}")
        lines.append(f"- Duplicate Ratio: {self.duplicate_ratio:.2%}")
        lines.append("")

        # Columns
        if self.columns:
            lines.append("## Columns")
            lines.append("")

            lines.append(
                "| Name | Dtype | Semantic Type | Nulls | Unique Count | Unique Ratio | Warnings |"
            )

            lines.append("|---|---|---|---|---|---|---|")

            for name in sorted(self.columns):
                column = self.columns[name]

                warnings = ", ".join(column.warnings) if column.warnings else "-"

                lines.append(
                    f"| {_markdown_cell(column.name)} "
                    f"| {_markdown_cell(column.dtype)} "
                    f"| {_markdown_cell(column.semantic_type)} "
                    f"| {_markdown_cell(column.null_count)} "
                    f"| {_markdown_cell(column.unique_count)} "
                    f"| {_markdown_cell(f'{column.unique_ratio:.2%}')} "
                    f"| {_markdown_cell(warnings)} |"
                )

            lines.append("")

        # Suggestions
        if self.suggestions:
            import json

            lines.append("## Suggested Cleaning Steps")
            lines.append("")

            rendered_suggestions = self.suggestions
            if max_suggestions is not None:
                rendered_suggestions = self.suggestions[:max_suggestions]

            for step in rendered_suggestions:
                kwargs_str = json.dumps(step[1], sort_keys=True, default=str)
                conf_score = getattr(step, "confidence_score", None)
                conf_reason = getattr(step, "confidence_reason", None)
                if conf_score is not None and conf_reason is not None:
                    lines.append(
                        f"- `{step[0]}`: `{kwargs_str}` "
                        f"(Confidence: {conf_score:.2f} - {conf_reason})"
                    )
                else:
                    lines.append(f"- `{step[0]}`: `{kwargs_str}`")

            if max_suggestions is not None and len(self.suggestions) > len(
                rendered_suggestions
            ):
                lines.append(
                    f"Showing {len(rendered_suggestions)} of {len(self.suggestions)} suggestions."
                )

            lines.append("")

        markdown = "\n".join(lines)

        if output is None:
            return markdown

        if not hasattr(output, "write"):
            raise TypeError("output must be a writable text stream")

        output.write(markdown)
        return None

    def to_html(
        self,
        file_path: str | None = None,
        output: Any | None = None,
        max_suggestions: int | None = None,
    ) -> str | None:
        """Return a self-contained, dependency-free HTML data quality report.

        In notebook environments, ``DataQualityReport`` will render a compact dashboard
        automatically via ``_repr_html_``.
        """
        if file_path is not None:
            if isinstance(file_path, bool) or not isinstance(
                file_path, (str, bytes, os.PathLike)
            ):
                raise TypeError(
                    f"file_path must be a string, bytes, or os.PathLike object, got {type(file_path).__name__}"
                )

        max_suggestions = self._validate_max_suggestions(max_suggestions)
        html_out = self._to_html_dashboard(
            full_document=True,
            max_suggestions=max_suggestions,
        )
        if file_path:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(html_out)

        if output is None:
            return html_out

        if not hasattr(output, "write"):
            raise TypeError("output must be a writable text stream")

        output.write(html_out)
        return None

    def _repr_html_(self) -> str:  # pragma: no cover - exercised via tests directly
        """Notebook-friendly HTML representation."""
        return self._to_html_dashboard(full_document=False)

    def _to_html_dashboard(
        self,
        *,
        full_document: bool,
        max_suggestions: int | None = None,
    ) -> str:
        def e(text: Any) -> str:
            return html.escape(str(text), quote=True)

        def fmt_bytes(n: int) -> str:
            units = ["B", "KB", "MB", "GB", "TB"]
            value = float(n)
            unit_idx = 0
            while value >= 1024 and unit_idx < len(units) - 1:
                value /= 1024
                unit_idx += 1
            if unit_idx == 0:
                return f"{int(value)} {units[unit_idx]}"
            return f"{value:.2f} {units[unit_idx]}"

        def score_class(score: float) -> str:
            if score >= 90:
                return "good"
            if score >= 70:
                return "warn"
            return "bad"

        total_warnings = sum(len(c.warnings) for c in self.columns.values())
        cols_with_warnings = sum(1 for c in self.columns.values() if c.warnings)
        cols_with_nulls = sum(1 for c in self.columns.values() if c.null_count > 0)

        styles = """
        /* Scoped styles for notebook output */
        .arnio-dqr { font-family: -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif; line-height: 1.45; color: #111827; }
        .arnio-dqr .container { max-width: 1200px; margin: 0 auto; background: #ffffff; padding: 20px; border-radius: 10px; border: 1px solid #e5e7eb; }
        .arnio-dqr .header { display: flex; gap: 14px; align-items: center; justify-content: space-between; flex-wrap: wrap; margin-bottom: 14px; }
        .arnio-dqr h1 { margin: 0; font-size: 20px; letter-spacing: -0.01em; }
        .arnio-dqr .subtitle { color: #6b7280; font-size: 12px; margin-top: 2px; }
        .arnio-dqr .pill { display:inline-flex; align-items:center; gap:8px; padding: 6px 10px; border-radius: 999px; border: 1px solid #e5e7eb; background: #f9fafb; font-size: 12px; }
        .arnio-dqr .score { font-weight: 700; }
        .arnio-dqr .score.good { color: #047857; }
        .arnio-dqr .score.warn { color: #b45309; }
        .arnio-dqr .score.bad { color: #b91c1c; }
        .arnio-dqr .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 10px; margin: 14px 0 18px 0; }
        .arnio-dqr .card { border: 1px solid #e5e7eb; border-radius: 10px; padding: 10px 12px; background: #ffffff; }
        .arnio-dqr .card .label { color: #6b7280; font-size: 11px; text-transform: uppercase; letter-spacing: 0.06em; }
        .arnio-dqr .card .value { font-size: 18px; font-weight: 700; margin-top: 4px; }
        .arnio-dqr .section { margin-top: 14px; }
        .arnio-dqr h2 { margin: 0 0 8px 0; font-size: 14px; color: #111827; letter-spacing: -0.01em; }
        .arnio-dqr table { width: 100%; border-collapse: collapse; font-size: 12px; }
        .arnio-dqr th, .arnio-dqr td { padding: 8px 8px; border-bottom: 1px solid #e5e7eb; vertical-align: top; }
        .arnio-dqr th { text-align: left; color: #374151; background: #f9fafb; position: sticky; top: 0; }
        .arnio-dqr .muted { color: #6b7280; }
        .arnio-dqr .warn { color: #b91c1c; font-weight: 600; }
        .arnio-dqr .chip { display:inline-block; padding: 2px 6px; border: 1px solid #e5e7eb; border-radius: 999px; background:#ffffff; margin: 0 4px 4px 0; font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace; font-size: 11px; }
        .arnio-dqr .bar { width: 100%; height: 6px; border-radius: 999px; background: #e5e7eb; overflow: hidden; margin-top: 4px; }
        .arnio-dqr .bar > span { display: block; height: 100%; background: #3b82f6; }
        .arnio-dqr details { border: 1px solid #e5e7eb; border-radius: 10px; padding: 8px 10px; background: #ffffff; }
        .arnio-dqr details + details { margin-top: 8px; }
        .arnio-dqr summary { cursor: pointer; font-weight: 600; }
        .arnio-dqr code { font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace; font-size: 11px; }
        """

        lines: list[str] = []
        if full_document:
            lines.append("<!DOCTYPE html>")
            lines.append('<html lang="en">')
            lines.append("<head>")
            lines.append('  <meta charset="UTF-8">')
            lines.append(
                '  <meta name="viewport" content="width=device-width, initial-scale=1.0">'
            )
            lines.append("  <title>Data Quality Report</title>")
            lines.append(f"  <style>{styles}</style>")
            lines.append("</head>")
            lines.append('<body style="margin:0;padding:16px;background:#f3f4f6;">')
            lines.append('<div class="arnio-dqr">')
        else:
            lines.append(f"<style>{styles}</style>")
            lines.append('<div class="arnio-dqr">')

        lines.append('<div class="container">')
        lines.append('<div class="header">')
        lines.append("<div>")
        lines.append("<h1>Data Quality Report</h1>")
        lines.append(
            f'<div class="subtitle">Rows: {e(self.row_count)} · Columns: {e(self.column_count)} · Memory: {e(fmt_bytes(self.memory_usage))}</div>'
        )
        lines.append("</div>")
        lines.append(
            f"<div class=\"pill\"><span class=\"muted\">Quality score</span> <span class=\"score {score_class(self.quality_score)}\">{e(f'{self.quality_score:.2f}')}</span></div>"
        )
        lines.append("</div>")

        lines.append('<div class="grid">')
        cards: list[tuple[str, str]] = [
            ("Duplicate rows", f"{self.duplicate_rows} ({self.duplicate_ratio:.2%})"),
            ("Columns w/ nulls", str(cols_with_nulls)),
            ("Columns w/ warnings", str(cols_with_warnings)),
            ("Total warnings", str(total_warnings)),
        ]
        if self.score_components:
            penalty_total = sum(self.score_components.values())
            cards.append(("Score delta", f"{penalty_total:+.2f}"))
        for label, value in cards:
            lines.append('<div class="card">')
            lines.append(f'<div class="label">{e(label)}</div>')
            lines.append(f'<div class="value">{e(value)}</div>')
            lines.append("</div>")
        lines.append("</div>")

        if self.score_components:
            lines.append('<div class="section">')
            lines.append("<h2>Score Components</h2>")
            lines.append("<table>")
            lines.append("<thead><tr><th>Component</th><th>Delta</th></tr></thead>")
            lines.append("<tbody>")
            for key, value in sorted(self.score_components.items()):
                cls = "warn" if value < 0 else "muted"
                lines.append("<tr>")
                lines.append(f"<td><code>{e(key)}</code></td>")
                lines.append(f"<td class=\"{cls}\">{e(f'{value:+.2f}')}</td>")
                lines.append("</tr>")
            lines.append("</tbody>")
            lines.append("</table>")
            lines.append("</div>")

        if self.columns:
            lines.append('<div class="section">')
            lines.append("<h2>Columns</h2>")
            lines.append("<table>")
            lines.append(
                "<thead><tr>"
                "<th>Name</th><th>Dtype</th><th>Semantic</th><th>Nulls</th><th>Unique</th>"
                "<th>Top Values / Dist</th><th>Warnings</th><th>Suggestion</th>"
                "</tr></thead>"
            )
            lines.append("<tbody>")
            for name in sorted(self.columns):
                col = self.columns[name]
                null_pct = (col.null_ratio * 100.0) if col.row_count else 0.0
                unique_pct = (col.unique_ratio * 100.0) if col.row_count else 0.0
                warnings_str = ", ".join(col.warnings) if col.warnings else "-"
                suggested = col.suggested_dtype if col.suggested_dtype else "-"

                if col.top_values:
                    top_bits: list[str] = []
                    for v, _c, r in col.top_values[:3]:
                        top_bits.append(
                            f"<span class=\"chip\">{e(v)} · {e(f'{r:.0%}')}</span>"
                        )
                    top_html = "".join(top_bits)
                elif col.histogram:
                    max_ratio = max((r for _, _, _, r in col.histogram), default=1.0)
                    if max_ratio == 0:
                        max_ratio = 1.0
                    bars = []
                    last_idx = len(col.histogram) - 1
                    for idx, (start, end, count, r) in enumerate(col.histogram):
                        height_pct = (r / max_ratio) * 100
                        bucket_label = (
                            f"[{start:.4g}, {end:.4g}]"
                            if idx == last_idx
                            else f"[{start:.4g}, {end:.4g})"
                        )
                        bars.append(
                            f'<div style="flex:1;height:{height_pct}%;background:#3b82f6;min-height:1px;border-radius:1px;" '
                            f'title="{bucket_label}: {count} ({r:.1%})"></div>'
                        )
                    top_html = (
                        f'<div style="display:inline-flex;align-items:flex-end;gap:1.5px;'
                        f'height:20px;width:100px;background:#f3f4f6;border-radius:3px;padding:2px;" '
                        f'title="Numeric Distribution Histogram">'
                        f'{"".join(bars)}'
                        f"</div>"
                    )
                else:
                    top_html = '<span class="muted">-</span>'

                lines.append("<tr>")
                lines.append(f"<td><code>{e(col.name)}</code></td>")
                lines.append(f"<td>{e(col.dtype)}</td>")
                lines.append(f"<td>{e(col.semantic_type)}</td>")
                lines.append(
                    "<td>"
                    f"{e(col.null_count)} <span class=\"muted\">({e(f'{null_pct:.1f}%')})</span>"
                    f'<div class="bar"><span style="width:{max(0.0, min(100.0, null_pct)):.2f}%"></span></div>'
                    "</td>"
                )
                lines.append(
                    "<td>"
                    f"{e(col.unique_count)} <span class=\"muted\">({e(f'{unique_pct:.1f}%')})</span>"
                    f'<div class="bar"><span style="width:{max(0.0, min(100.0, unique_pct)):.2f}%"></span></div>'
                    "</td>"
                )
                lines.append(f"<td>{top_html}</td>")
                lines.append(
                    f"<td class=\"{'warn' if col.warnings else 'muted'}\">{e(warnings_str)}</td>"
                )
                lines.append(f"<td>{e(suggested)}</td>")
                lines.append("</tr>")
            lines.append("</tbody></table>")
            lines.append("</div>")

        if self.suggestions:
            rendered_suggestions = self.suggestions
            if max_suggestions is not None:
                rendered_suggestions = self.suggestions[:max_suggestions]

            lines.append('<div class="section">')
            lines.append("<h2>Cleaning Suggestions</h2>")
            for step in rendered_suggestions:
                conf_score = getattr(step, "confidence_score", None)
                conf_reason = getattr(step, "confidence_reason", None)
                conf_bits: list[str] = []
                if conf_score is not None:
                    conf_bits.append(f"Confidence: {conf_score:.2f}")
                if conf_reason:
                    conf_bits.append(str(conf_reason))
                conf_text = f" — {e(' · '.join(conf_bits))}" if conf_bits else ""
                lines.append("<details>")
                lines.append(
                    f'<summary><code>{e(step[0])}</code> <span class="muted">{e(step[1])}</span></summary>'
                )
                lines.append(
                    f'<div class="subtitle">{conf_text}</div>' if conf_text else ""
                )
                lines.append("</details>")
            if max_suggestions is not None and len(self.suggestions) > len(
                rendered_suggestions
            ):
                lines.append(
                    f'<div class="muted">Showing {len(rendered_suggestions)} of {len(self.suggestions)} suggestions.</div>'
                )
            lines.append("</div>")

        lines.append("</div>")  # container
        lines.append("</div>")  # arnio-dqr
        if full_document:
            lines.append("</body></html>")

        return "\n".join(lines)

    def summary(self) -> dict[str, Any]:
        """Return the highest-signal report fields."""
        return {
            "quality_score": self.quality_score,
            "score_components": self.score_components,
            "rows": self.row_count,
            "columns": self.column_count,
            "memory_usage": self.memory_usage,
            "duplicate_rows": self.duplicate_rows,
            "columns_with_nulls": [
                name for name, profile in self.columns.items() if profile.null_count > 0
            ],
            "columns_with_whitespace": [
                name
                for name, profile in self.columns.items()
                if profile.whitespace_count > 0
            ],
            "suggestions": self.suggestions,
        }

    def to_pandas(self) -> pd.DataFrame:
        """Return one row per column as a pandas DataFrame."""
        return pd.DataFrame(
            [
                {
                    "name": column.name,
                    "dtype": column.dtype,
                    "semantic_type": column.semantic_type,
                    "null_count": column.null_count,
                    "null_ratio": column.null_ratio,
                    "unique_count": column.unique_count,
                    "unique_ratio": column.unique_ratio,
                    "empty_string_count": column.empty_string_count,
                    "whitespace_count": column.whitespace_count,
                    "suggested_dtype": column.suggested_dtype,
                    "email_validity_ratio": column.email_validity_ratio,
                    "url_validity_ratio": column.url_validity_ratio,
                    "min": _clean_scalar(column.min),
                    "max": _clean_scalar(column.max),
                    "mean": column.mean,
                    "std": column.std,
                    **(
                        {
                            "q25": _clean_scalar(column.q25),
                            "q50": _clean_scalar(column.q50),
                            "q75": _clean_scalar(column.q75),
                            "q95": _clean_scalar(column.q95),
                        }
                        if _is_numeric_dtype(column.dtype)
                        else {}
                    ),
                    "warnings": column.warnings,
                    "top_values": column.top_values,
                    "top_values_is_approximate": column.top_values_is_approximate,
                    "top_values_sample_count": column.top_values_sample_count,
                    "top_values_sample_ratio": column.top_values_sample_ratio,
                    "histogram": column.histogram,
                }
                for column in self.columns.values()
            ]
        )


@dataclass(frozen=True)
class ProfileComparison:
    """Structured drift comparison between two quality profiles."""

    left_profile: DataQualityReport
    right_profile: DataQualityReport
    drift_report: dict[str, dict[str, Any]]
    status_counts: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-friendly dictionary representation."""
        return {
            "left_profile": self.left_profile.to_dict(),
            "right_profile": self.right_profile.to_dict(),
            "status_counts": dict(self.status_counts),
            "drift_report": {
                name: _clean_drift_entry(entry)
                for name, entry in self.drift_report.items()
            },
        }

    def to_json(
        self,
        *,
        indent: int | None = None,
        output: Any | None = None,
    ) -> str | None:
        """Return the comparison as a JSON string.

        Example:
        comparison.to_json(indent=2)
        """
        json_out = json.dumps(self.to_dict(), indent=indent)

        if output is None:
            return json_out

        if not hasattr(output, "write"):
            raise TypeError("output must be a writable text stream")

        output.write(json_out)
        return None

    def to_markdown(self, output: Any | None = None) -> str | None:
        """Return a GitHub-friendly Markdown drift report."""
        lines: list[str] = ["# Profile Comparison Report", ""]

        status_summary = ", ".join(
            f"{count} {status}" for status, count in sorted(self.status_counts.items())
        )
        lines.append(f"**Status summary:** {status_summary}")
        lines.append("")

        if self.drift_report:
            lines.append("## Column Drift")
            lines.append("")
            lines.append("| Column | Status | Changes | Reasons |")
            lines.append("|---|---|---|---|")
            for name, entry in sorted(self.drift_report.items()):
                status = entry.get("status", "-")
                changes = ", ".join(entry.get("changes", {}).keys()) or "-"
                reasons = "; ".join(entry.get("reasons", [])) or "-"
                lines.append(
                    f"| {_markdown_cell(name)} "
                    f"| {_markdown_cell(status)} "
                    f"| {_markdown_cell(changes)} "
                    f"| {_markdown_cell(reasons)} |"
                )
            lines.append("")

        markdown = "\n".join(lines)

        if output is None:
            return markdown

        if not hasattr(output, "write"):
            raise TypeError("output must be a writable text stream")

        output.write(markdown)
        return None


@dataclass(frozen=True)
class QualityGateIssue:
    """One failed data-quality gate."""

    metric: str
    message: str
    column: str | None = None
    baseline: Any = None
    current: Any = None
    threshold: Any = None
    delta: float | None = None

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-friendly dictionary representation."""
        return {
            "metric": self.metric,
            "column": self.column,
            "baseline": _clean_scalar(self.baseline),
            "current": _clean_scalar(self.current),
            "threshold": _clean_scalar(self.threshold),
            "delta": _clean_scalar(self.delta),
            "message": self.message,
        }


@dataclass(frozen=True)
class QualityGateResult:
    """Pass/fail result from threshold-based profile quality gates."""

    baseline_profile: DataQualityReport
    current_profile: DataQualityReport
    issues: list[QualityGateIssue]
    thresholds: dict[str, Any]

    @property
    def passed(self) -> bool:
        """Whether all configured quality gates passed."""
        return len(self.issues) == 0

    def summary(self) -> dict[str, Any]:
        """Return a compact summary suitable for logs and CI output."""
        return {
            "passed": self.passed,
            "issue_count": len(self.issues),
            "row_count": {
                "baseline": self.baseline_profile.row_count,
                "current": self.current_profile.row_count,
            },
            "column_count": {
                "baseline": self.baseline_profile.column_count,
                "current": self.current_profile.column_count,
            },
        }

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-friendly dictionary representation."""
        return {
            "passed": self.passed,
            "summary": self.summary(),
            "thresholds": {
                name: _clean_scalar(value) for name, value in self.thresholds.items()
            },
            "issues": [issue.to_dict() for issue in self.issues],
        }

    def to_markdown(self) -> str:
        """Return a GitHub-friendly quality-gate report."""
        lines = ["# Data Quality Gates", ""]
        lines.append(f"- Status: {'passed' if self.passed else 'failed'}")
        lines.append(f"- Issues: {len(self.issues)}")
        lines.append(f"- Baseline rows: {self.baseline_profile.row_count}")
        lines.append(f"- Current rows: {self.current_profile.row_count}")
        lines.append("")

        if not self.issues:
            lines.append("All configured quality gates passed.")
            return "\n".join(lines)

        lines.append(
            "| Metric | Column | Baseline | Current | Delta | Threshold | Message |"
        )
        lines.append("|---|---|---|---|---|---|---|")

        for issue in self.issues:
            lines.append(
                "| "
                f"{_markdown_cell(issue.metric)} | "
                f"{_markdown_cell(issue.column)} | "
                f"{_markdown_cell(issue.baseline)} | "
                f"{_markdown_cell(issue.current)} | "
                f"{_markdown_cell(issue.delta)} | "
                f"{_markdown_cell(issue.threshold)} | "
                f"{_markdown_cell(issue.message)} |"
            )

        return "\n".join(lines)

    def raise_for_failures(self) -> None:
        """Raise ``ValueError`` if any configured quality gate failed."""
        if self.passed:
            return
        raise ValueError(
            f"{len(self.issues)} data quality gate(s) failed. "
            "Inspect result.issues or result.to_markdown() for details."
        )

    def to_json(
        self,
        *,
        indent: int | None = None,
        output: Any | None = None,
    ) -> str | None:
        """Return the quality gate result as a JSON string.

        Example:
        result.to_json(indent=2)
        """
        json_out = json.dumps(self.to_dict(), indent=indent)

        if output is None:
            return json_out

        if not hasattr(output, "write"):
            raise TypeError("output must be a writable text stream")

        output.write(json_out)
        return None


def profile(
    frame: ArFrame,
    *,
    exclude_columns: Sequence[str] | None = None,
    sample_size: int = 5,
    approx_top_values: bool = False,
    approx_top_values_min_unique: int = 1000,
    approx_top_values_min_ratio: float = 0.2,
    approx_top_values_sample_size: int = 2000,
) -> DataQualityReport:
    """Profile data quality for an ArFrame.

    Parameters
    ----------
    frame : ArFrame
        Input frame to inspect.
    exclude_columns : Sequence[str], optional
        Column names to exclude from profiling.
    sample_size : int, default 5
        Number of non-null sample values to keep per column.
    approx_top_values : bool, default False
        When True, approximate top values for high-cardinality string columns.
    approx_top_values_min_unique : int, default 1000
        Minimum unique count required to enable approximate top values.
    approx_top_values_min_ratio : float, default 0.2
        Minimum unique ratio (unique / non-null) required to enable approximation.
    approx_top_values_sample_size : int, default 2000
        Number of non-null values sampled to estimate top values.

    Returns
    -------
    DataQualityReport
        Report containing nulls, uniqueness, basic stats, semantic hints, and
        safe cleaning suggestions.

    Examples
    --------
    >>> frame = ar.read_csv("raw.csv")
    >>> report = ar.profile(frame, sample_size=3)
    >>> report.summary()
    """
    if not isinstance(frame, ArFrame):
        raise TypeError(
            f"profile() expects an ArFrame, got {type(frame).__name__}. Use arnio.from_pandas() first."
        )

    if not isinstance(sample_size, int) or isinstance(sample_size, bool):
        raise TypeError("sample_size must be an integer")
    if sample_size < 0:
        raise ValueError("sample_size must be non-negative")
    if not isinstance(approx_top_values, bool):
        raise TypeError("approx_top_values must be a bool")
    if not isinstance(approx_top_values_min_unique, int) or isinstance(
        approx_top_values_min_unique, bool
    ):
        raise TypeError("approx_top_values_min_unique must be an integer")
    if approx_top_values_min_unique < 0:
        raise ValueError("approx_top_values_min_unique must be non-negative")
    if not isinstance(approx_top_values_min_ratio, (int, float)) or isinstance(
        approx_top_values_min_ratio, bool
    ):
        raise TypeError("approx_top_values_min_ratio must be a float")
    if approx_top_values_min_ratio < 0 or approx_top_values_min_ratio > 1:
        raise ValueError("approx_top_values_min_ratio must be between 0 and 1")
    if not isinstance(approx_top_values_sample_size, int) or isinstance(
        approx_top_values_sample_size, bool
    ):
        raise TypeError("approx_top_values_sample_size must be an integer")

    if approx_top_values_sample_size <= 0:
        raise ValueError("approx_top_values_sample_size must be positive")

    normalized_exclude_columns: list[str] = []

    if exclude_columns is not None:
        normalized_exclude_columns = _validate_column_sequence(
            exclude_columns,
            argument_name="exclude_columns",
        )
        validate_columns_exist(
            frame,
            normalized_exclude_columns,
            operation="profile",
        )

    has_exclusions = len(normalized_exclude_columns) > 0

    df = to_pandas(frame)

    if has_exclusions:
        df = df.drop(columns=normalized_exclude_columns)

    row_count = len(df)
    column_count = len(df.columns)
    duplicate_rows = int(df.duplicated().sum()) if row_count else 0
    duplicate_ratio = _ratio(duplicate_rows, row_count)

    columns = {
        name: _profile_column(
            name=name,
            series=df[name],
            dtype=frame.dtypes.get(name, str(df[name].dtype)),
            row_count=row_count,
            sample_size=sample_size,
            approx_top_values=approx_top_values,
            approx_top_values_min_unique=approx_top_values_min_unique,
            approx_top_values_min_ratio=approx_top_values_min_ratio,
            approx_top_values_sample_size=approx_top_values_sample_size,
        )
        for name in df.columns
    }

    report = DataQualityReport(
        row_count=row_count,
        column_count=column_count,
        memory_usage=(
            int(df.memory_usage(deep=True).sum())
            if has_exclusions
            else frame.memory_usage()
        ),
        duplicate_rows=duplicate_rows,
        duplicate_ratio=duplicate_ratio,
        columns=columns,
        suggestions=[],
    )

    quality_score, score_components = _calculate_quality_score(
        row_count, duplicate_ratio, columns
    )

    return DataQualityReport(
        row_count=report.row_count,
        column_count=report.column_count,
        memory_usage=report.memory_usage,
        duplicate_rows=report.duplicate_rows,
        duplicate_ratio=report.duplicate_ratio,
        quality_score=quality_score,
        score_components=score_components,
        columns=report.columns,
        suggestions=suggest_cleaning(report),
    )


def compare_profiles(
    profile_a: DataQualityReport,
    profile_b: DataQualityReport,
) -> ProfileComparison:
    """Compare two data-quality profiles for drift.

    The comparison is column-wise and focuses on changes in null ratios, dtype,
    uniqueness, and numeric distribution metrics. Numeric columns compare
    ``mean``, ``std``, ``min``, and ``max`` when available.

    Parameters
    ----------
    profile_a, profile_b : DataQualityReport
        Profiles produced by :func:`profile`.

    Returns
    -------
    ProfileComparison
        Structured comparison containing a ``drift_report`` entry for each
        shared column.

    Raises
    ------
    ValueError
        If the two profiles do not cover the same set of columns.

    Examples
    --------
    >>> baseline = ar.profile(ar.read_csv("baseline.csv"))
    >>> current = ar.profile(ar.read_csv("current.csv"))
    >>> comparison = ar.compare_profiles(baseline, current)
    >>> comparison.drift_report["score"]["status"]
    'warning'
    """
    if not isinstance(profile_a, DataQualityReport) or not isinstance(
        profile_b, DataQualityReport
    ):
        raise TypeError("compare_profiles expects two DataQualityReport instances")

    columns_a = set(profile_a.columns)
    columns_b = set(profile_b.columns)
    if columns_a != columns_b:
        missing_from_a = sorted(columns_b - columns_a)
        missing_from_b = sorted(columns_a - columns_b)
        raise ValueError(
            "Profiles have incompatible schemas: "
            f"missing from profile_a={missing_from_a}, "
            f"missing from profile_b={missing_from_b}. "
            "This is likely caused by calling profile() with different exclude_columns "
            "on each dataset. Profile both datasets with the same included/excluded "
            "columns before comparing."
        )

    drift_report: dict[str, dict[str, Any]] = {}
    status_counts = {"ok": 0, "warning": 0, "changed": 0}

    for name in sorted(columns_a):
        entry = _compare_column_profiles(
            profile_a.columns[name], profile_b.columns[name]
        )
        drift_report[name] = entry
        status_counts[entry["status"]] += 1

    return ProfileComparison(
        left_profile=profile_a,
        right_profile=profile_b,
        drift_report=drift_report,
        status_counts=status_counts,
    )


def check_quality_gates(
    baseline_profile: DataQualityReport,
    current_profile: DataQualityReport,
    *,
    max_row_count_delta_ratio: float | None = 0.1,
    max_duplicate_ratio_delta: float | None = 0.05,
    max_null_ratio_delta: float | None = 0.05,
    max_numeric_mean_delta_ratio: float | None = 0.1,
    max_numeric_std_delta_ratio: float | None = 0.2,
    allow_new_columns: bool = False,
    allow_missing_columns: bool = False,
    fail_on_dtype_change: bool = True,
) -> QualityGateResult:
    """Check two quality profiles against pass/fail drift thresholds.

    Parameters
    ----------
    baseline_profile, current_profile : DataQualityReport
        Profiles produced by :func:`profile`.
    max_row_count_delta_ratio : float or None, default 0.1
        Maximum relative row-count drift. ``None`` disables this gate.
    max_duplicate_ratio_delta : float or None, default 0.05
        Maximum absolute duplicate-ratio drift. ``None`` disables this gate.
    max_null_ratio_delta : float or None, default 0.05
        Maximum absolute per-column null-ratio drift. ``None`` disables this gate.
    max_numeric_mean_delta_ratio : float or None, default 0.1
        Maximum relative per-column numeric mean drift. ``None`` disables this gate.
    max_numeric_std_delta_ratio : float or None, default 0.2
        Maximum relative per-column numeric standard-deviation drift.
        ``None`` disables this gate.
    allow_new_columns, allow_missing_columns : bool, default False
        Whether added or removed columns are allowed.
    fail_on_dtype_change : bool, default True
        Whether shared columns with changed dtypes fail the gate.

    Returns
    -------
    QualityGateResult
        Structured pass/fail output with issue details and Markdown rendering.

    Examples
    --------
    >>> baseline = ar.profile(ar.read_csv("baseline.csv"))
    >>> current = ar.profile(ar.read_csv("current.csv"))
    >>> result = ar.check_quality_gates(baseline, current)
    >>> result.passed
    True
    """
    if not isinstance(baseline_profile, DataQualityReport) or not isinstance(
        current_profile, DataQualityReport
    ):
        raise TypeError("check_quality_gates expects two DataQualityReport instances")

    thresholds = {
        "max_row_count_delta_ratio": _validate_gate_threshold(
            max_row_count_delta_ratio, "max_row_count_delta_ratio"
        ),
        "max_duplicate_ratio_delta": _validate_gate_threshold(
            max_duplicate_ratio_delta, "max_duplicate_ratio_delta"
        ),
        "max_null_ratio_delta": _validate_gate_threshold(
            max_null_ratio_delta, "max_null_ratio_delta"
        ),
        "max_numeric_mean_delta_ratio": _validate_gate_threshold(
            max_numeric_mean_delta_ratio, "max_numeric_mean_delta_ratio"
        ),
        "max_numeric_std_delta_ratio": _validate_gate_threshold(
            max_numeric_std_delta_ratio, "max_numeric_std_delta_ratio"
        ),
        "allow_new_columns": _validate_gate_bool(
            allow_new_columns, "allow_new_columns"
        ),
        "allow_missing_columns": _validate_gate_bool(
            allow_missing_columns, "allow_missing_columns"
        ),
        "fail_on_dtype_change": _validate_gate_bool(
            fail_on_dtype_change, "fail_on_dtype_change"
        ),
    }

    issues: list[QualityGateIssue] = []

    _add_ratio_issue(
        issues,
        metric="row_count",
        baseline=baseline_profile.row_count,
        current=current_profile.row_count,
        threshold=thresholds["max_row_count_delta_ratio"],
        message="row count drift exceeded threshold",
    )
    _add_absolute_issue(
        issues,
        metric="duplicate_ratio",
        baseline=baseline_profile.duplicate_ratio,
        current=current_profile.duplicate_ratio,
        threshold=thresholds["max_duplicate_ratio_delta"],
        message="duplicate ratio drift exceeded threshold",
    )

    baseline_columns = set(baseline_profile.columns)
    current_columns = set(current_profile.columns)

    if not thresholds["allow_missing_columns"]:
        for column in sorted(baseline_columns - current_columns):
            issues.append(
                QualityGateIssue(
                    metric="missing_column",
                    column=column,
                    baseline=column,
                    current=None,
                    threshold="allow_missing_columns=True",
                    message=f"column {column!r} is missing from current profile",
                )
            )

    if not thresholds["allow_new_columns"]:
        for column in sorted(current_columns - baseline_columns):
            issues.append(
                QualityGateIssue(
                    metric="new_column",
                    column=column,
                    baseline=None,
                    current=column,
                    threshold="allow_new_columns=True",
                    message=f"column {column!r} was added in current profile",
                )
            )

    for column in sorted(baseline_columns & current_columns):
        baseline_column = baseline_profile.columns[column]
        current_column = current_profile.columns[column]

        if (
            thresholds["fail_on_dtype_change"]
            and baseline_column.dtype != current_column.dtype
        ):
            issues.append(
                QualityGateIssue(
                    metric="dtype",
                    column=column,
                    baseline=baseline_column.dtype,
                    current=current_column.dtype,
                    threshold="same dtype",
                    message=f"column {column!r} dtype changed",
                )
            )

        _add_absolute_issue(
            issues,
            metric="null_ratio",
            column=column,
            baseline=baseline_column.null_ratio,
            current=current_column.null_ratio,
            threshold=thresholds["max_null_ratio_delta"],
            message=f"column {column!r} null ratio drift exceeded threshold",
        )

        if _is_numeric_dtype(baseline_column.dtype) and _is_numeric_dtype(
            current_column.dtype
        ):
            _add_ratio_issue(
                issues,
                metric="numeric_mean",
                column=column,
                baseline=baseline_column.mean,
                current=current_column.mean,
                threshold=thresholds["max_numeric_mean_delta_ratio"],
                message=f"column {column!r} numeric mean drift exceeded threshold",
            )
            _add_ratio_issue(
                issues,
                metric="numeric_std",
                column=column,
                baseline=baseline_column.std,
                current=current_column.std,
                threshold=thresholds["max_numeric_std_delta_ratio"],
                message=(
                    f"column {column!r} numeric standard deviation drift "
                    "exceeded threshold"
                ),
            )

    return QualityGateResult(
        baseline_profile=baseline_profile,
        current_profile=current_profile,
        issues=issues,
        thresholds=thresholds,
    )


def _calculate_quality_score(
    row_count: int,
    duplicate_ratio: float,
    columns: dict[str, ColumnProfile],
) -> tuple[float, dict[str, float]]:
    """Compute an overall quality score and per-penalty breakdown from profile data."""
    if row_count == 0 or not columns:
        return 100.0, {}

    duplicate_penalty = round(min(duplicate_ratio * 100.0, 20.0), 2)

    null_ratios = [c.null_ratio for c in columns.values()]
    avg_null_ratio = sum(null_ratios) / len(null_ratios) if null_ratios else 0.0
    null_penalty = round(min(avg_null_ratio * 100.0, 40.0), 2)

    type_mismatches = sum(1 for c in columns.values() if c.suggested_dtype is not None)
    mismatch_ratio = type_mismatches / len(columns) if columns else 0.0
    type_mismatch_penalty = round(min(mismatch_ratio * 100.0, 40.0), 2)

    score_components: dict[str, float] = {}
    if duplicate_penalty > 0:
        score_components["duplicate_penalty"] = -duplicate_penalty
    if null_penalty > 0:
        score_components["null_penalty"] = -null_penalty
    if type_mismatch_penalty > 0:
        score_components["type_mismatch_penalty"] = -type_mismatch_penalty

    quality_score = round(
        100.0 - duplicate_penalty - null_penalty - type_mismatch_penalty, 2
    )

    return quality_score, score_components


def _merge_status(current: str, new_status: str) -> str:
    """Return the higher-severity status between current and new_status."""
    order = {"ok": 0, "warning": 1, "changed": 2}
    return new_status if order[new_status] > order[current] else current


def _numeric_delta(value_a: Any, value_b: Any) -> float | None:
    """Return the absolute numeric difference between two values, or None if non-numeric."""
    if isinstance(value_a, (int, float)) and isinstance(value_b, (int, float)):
        return abs(float(value_a) - float(value_b))
    return None


def _clean_drift_entry(entry: dict[str, Any]) -> dict[str, Any]:
    """Normalize a raw drift entry dict into a clean serializable structure."""
    return {
        "status": entry["status"],
        "changes": {
            metric: {key: _clean_scalar(value) for key, value in change.items()}
            for metric, change in entry["changes"].items()
        },
        "reasons": list(entry["reasons"]),
    }


def _validate_gate_threshold(value: float | None, name: str) -> float | None:
    """Validate that a quality gate threshold is a finite non-negative number or None."""
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be a non-negative number or None")
    value = float(value)
    if not math.isfinite(value) or value < 0:
        raise ValueError(f"{name} must be a finite non-negative number")
    return value


def _validate_gate_bool(value: bool, name: str) -> bool:
    return _validate_bool_option(value, name)


def _validate_bool_option(value: bool, name: str) -> bool:
    if not isinstance(value, bool):
        raise TypeError(f"{name} must be a bool")
    return value


def _relative_delta(baseline: Any, current: Any) -> float | None:
    """Return the relative change between baseline and current, or None if not computable."""
    if baseline is None or current is None:
        return None
    if not isinstance(baseline, (int, float)) or not isinstance(current, (int, float)):
        return None
    baseline_value = float(baseline)
    current_value = float(current)
    if not math.isfinite(baseline_value) or not math.isfinite(current_value):
        return None
    return abs(current_value - baseline_value) / max(abs(baseline_value), 1.0)


def _absolute_delta(baseline: Any, current: Any) -> float | None:
    """Return the absolute numeric change between baseline and current, or None if not computable."""
    if baseline is None or current is None:
        return None
    if not isinstance(baseline, (int, float)) or not isinstance(current, (int, float)):
        return None
    baseline_value = float(baseline)
    current_value = float(current)
    if not math.isfinite(baseline_value) or not math.isfinite(current_value):
        return None
    return abs(current_value - baseline_value)


def _add_ratio_issue(
    issues: list[QualityGateIssue],
    *,
    metric: str,
    baseline: Any,
    current: Any,
    threshold: float | None,
    message: str,
    column: str | None = None,
) -> None:
    """Append a QualityGateIssue if the relative delta between baseline and current exceeds threshold."""
    if threshold is None:
        return
    delta = _relative_delta(baseline, current)
    if delta is not None and delta > threshold:
        issues.append(
            QualityGateIssue(
                metric=metric,
                column=column,
                baseline=baseline,
                current=current,
                threshold=threshold,
                delta=round(delta, 6),
                message=message,
            )
        )


def _add_absolute_issue(
    issues: list[QualityGateIssue],
    *,
    metric: str,
    baseline: Any,
    current: Any,
    threshold: float | None,
    message: str,
    column: str | None = None,
) -> None:
    """Append a QualityGateIssue if the absolute delta between baseline and current exceeds threshold."""
    if threshold is None:
        return
    delta = _absolute_delta(baseline, current)
    if delta is not None and delta > threshold:
        issues.append(
            QualityGateIssue(
                metric=metric,
                column=column,
                baseline=baseline,
                current=current,
                threshold=threshold,
                delta=round(delta, 6),
                message=message,
            )
        )


def _markdown_cell(value: Any) -> str:
    """Escape a value for safe rendering inside a Markdown table cell."""
    if value is None:
        return "-"
    text = str(_clean_scalar(value))
    return (
        text.replace("\\", "\\\\")
        .replace("|", "\\|")
        .replace("\r\n", "<br>")
        .replace("\r", "<br>")
        .replace("\n", "<br>")
    )


def _compare_column_profiles(
    column_a: ColumnProfile,
    column_b: ColumnProfile,
) -> dict[str, Any]:
    """Compare two ColumnProfile objects and return a drift entry with status, changes, and reasons."""
    changes: dict[str, dict[str, Any]] = {}
    reasons: list[str] = []
    status = "ok"

    def add_change(
        metric: str,
        value_a: Any,
        value_b: Any,
        *,
        warning_threshold: float | None = None,
        changed_threshold: float | None = None,
        reason: str | None = None,
    ) -> None:
        nonlocal status
        if value_a == value_b:
            return

        delta = _numeric_delta(value_a, value_b)
        changes[metric] = {
            "baseline": _clean_scalar(value_a),
            "comparison": _clean_scalar(value_b),
            "delta": _clean_scalar(delta),
        }

        metric_status = "ok"
        if (
            changed_threshold is not None
            and delta is not None
            and delta > changed_threshold
        ):
            metric_status = "changed"
        elif (
            warning_threshold is not None
            and delta is not None
            and delta > warning_threshold
        ):
            metric_status = "warning"
        elif warning_threshold is None and changed_threshold is None:
            metric_status = "changed"

        status = _merge_status(status, metric_status)
        if reason is not None:
            reasons.append(reason)

    add_change(
        "dtype",
        column_a.dtype,
        column_b.dtype,
        reason=f"dtype changed from {column_a.dtype} to {column_b.dtype}",
    )
    add_change(
        "null_ratio",
        column_a.null_ratio,
        column_b.null_ratio,
        warning_threshold=0.1,
        changed_threshold=0.25,
        reason="null ratio changed",
    )
    add_change(
        "unique_count",
        column_a.unique_count,
        column_b.unique_count,
        warning_threshold=max(1.0, column_a.row_count * 0.1, column_b.row_count * 0.1),
        changed_threshold=max(
            2.0, column_a.row_count * 0.25, column_b.row_count * 0.25
        ),
        reason="unique count changed",
    )
    add_change(
        "unique_ratio",
        column_a.unique_ratio,
        column_b.unique_ratio,
        warning_threshold=0.1,
        changed_threshold=0.25,
        reason="unique ratio changed",
    )

    if _is_numeric_dtype(column_a.dtype) and _is_numeric_dtype(column_b.dtype):
        for metric in ("mean", "std", "min", "max"):
            value_a = getattr(column_a, metric)
            value_b = getattr(column_b, metric)
            if value_a is None or value_b is None:
                continue
            scale = max(abs(float(value_a)), abs(float(value_b)), 1.0)
            add_change(
                metric,
                value_a,
                value_b,
                warning_threshold=scale * 0.1,
                changed_threshold=scale * 0.25,
                reason=f"numeric {metric} changed",
            )

    if not changes:
        reasons.append("no drift detected")

    return {
        "status": status,
        "changes": changes,
        "reasons": reasons,
    }


def suggest_cleaning(
    frame_or_report: ArFrame | DataQualityReport,
) -> list[CleaningSuggestion]:
    """Suggest safe built-in cleaning steps.

    Parameters
    ----------
    frame_or_report : ArFrame or DataQualityReport
        Frame to profile or an existing report.

    Returns
    -------
    list[CleaningSuggestion]
        Pipeline-compatible cleaning suggestions.

    Examples
    --------
    >>> suggestions = ar.suggest_cleaning(frame)
    >>> clean = ar.pipeline(frame, suggestions)
    """
    report = (
        frame_or_report
        if isinstance(frame_or_report, DataQualityReport)
        else profile(frame_or_report)
    )

    suggestions: list[CleaningSuggestion] = []
    whitespace_columns = [
        name for name, column in report.columns.items() if column.whitespace_count > 0
    ]
    if whitespace_columns:
        suggestions.append(
            CleaningSuggestion(
                "strip_whitespace",
                {"subset": whitespace_columns},
                0.95,
                "Trimming leading/trailing whitespace is a safe and highly recommended operation for columns with formatting anomalies.",
            )
        )

    cast_mapping = _suggest_casts(report)
    if cast_mapping:
        col_scores = []
        col_reasons = []
        for col_name, target_dtype in cast_mapping.items():
            col_profile = report.columns[col_name]
            non_null_ratio = 1.0 - col_profile.null_ratio

            score = 0.95
            reason = (
                f"Column '{col_name}' conforms perfectly to {target_dtype} structure."
            )

            if non_null_ratio < 0.2:
                score -= 0.3
                reason = f"Column '{col_name}' has very low non-null support ({non_null_ratio:.1%}) for {target_dtype} type inference."
            elif non_null_ratio < 0.5:
                score -= 0.15
                reason = f"Column '{col_name}' has moderate non-null support ({non_null_ratio:.1%}) for {target_dtype} type inference."

            col_scores.append(score)
            col_reasons.append(reason)

        avg_score = round(sum(col_scores) / len(col_scores), 2)
        reason = "; ".join(col_reasons)
        suggestions.append(
            CleaningSuggestion(
                "cast_types",
                cast_mapping,
                avg_score,
                reason,
            )
        )

    if report.duplicate_rows > 0:
        if report.duplicate_ratio > 0.5:
            score = 0.75
            reason = f"High duplicate ratio ({report.duplicate_ratio:.1%}) suggests potential schema or merge anomalies; review before dropping."
        else:
            score = 0.95
            reason = f"Low duplicate ratio ({report.duplicate_ratio:.1%}) suggests standard redundant records."

        suggestions.append(
            CleaningSuggestion(
                "drop_duplicates",
                {"keep": "first"},
                score,
                reason,
            )
        )

    return suggestions


@dataclass(frozen=True)
class CleanStepRecord:
    """Audit record for a single step applied by auto_clean."""

    step: str
    """Name of the cleaning step (e.g. ``strip_whitespace``)."""
    kwargs: dict[str, Any]
    """Keyword arguments passed to the step."""
    rows_before: int
    """Row count before this step was applied."""
    rows_after: int
    """Row count after this step was applied."""
    rows_removed: int
    """Number of rows removed by this step (0 for non-row-dropping steps)."""
    reason: str
    """Human-readable explanation of why this step was selected."""


@dataclass(frozen=True)
class CleanExplanation:
    """Structured audit trail returned by ``auto_clean`` when ``explain=True``.

    This object captures a before-and-after summary of every cleaning step
    that was applied, making it easy to audit, log, or display what
    ``auto_clean`` changed and why.
    """

    mode: str
    """The cleaning mode that was used (``'safe'`` or ``'strict'``)."""
    rows_before: int
    """Total row count before any cleaning."""
    rows_after: int
    """Total row count after all cleaning steps."""
    rows_removed: int
    """Total rows removed across all steps."""
    steps: list[CleanStepRecord]
    """Ordered list of steps that were actually applied."""

    def __str__(self) -> str:
        lines: list[str] = [
            f"CleanExplanation(mode={self.mode!r})",
            f"  rows : {self.rows_before} -> {self.rows_after} ({self.rows_removed} removed)",
            f"  steps applied ({len(self.steps)}):",
        ]
        for rec in self.steps:
            lines.append(
                f"    [{rec.step}] rows {rec.rows_before}->{rec.rows_after} "
                f"(-{rec.rows_removed}) | reason: {rec.reason}"
            )
        if not self.steps:
            lines.append("    (none)")
        return "\n".join(lines)


def auto_clean(
    frame: ArFrame,
    *,
    mode: str = "safe",
    return_report: bool = False,
    dry_run: bool = False,
    allow_lossy_casts: bool = False,
    explain: bool = False,
) -> (
    ArFrame
    | DataQualityReport
    | tuple[ArFrame, DataQualityReport]
    | tuple[ArFrame, CleanExplanation]
    | tuple[ArFrame, DataQualityReport, CleanExplanation]
):
    """Apply built-in automatic cleaning.

    Parameters
    ----------
    frame : ArFrame
        Input frame.
    mode : {"safe", "strict"}, default "safe"
        ``safe`` applies only low-risk cleanup such as whitespace trimming.
        ``strict`` also applies deterministic casts and exact duplicate removal.
    return_report : bool, default False
        Whether to return the pre-cleaning quality report.
    dry_run : bool, default False
        Return the proposed pre-cleaning report without mutating the frame.
    allow_lossy_casts : bool, default False
        Required before strict mode applies suggested type casts.
    explain : bool, default False
        When ``True``, return a :class:`CleanExplanation` object that records
        which steps ran, before/after row counts for each step, and why each
        step was selected. The cleaned frame is always the first element in the
        returned tuple.

    Returns
    -------
    ArFrame
        Cleaned frame (when *return_report*, *dry_run*, and *explain* are all ``False``).
    DataQualityReport
        When *dry_run* is ``True`` and *return_report* is ``False``.
    tuple[ArFrame, DataQualityReport]
        When only *return_report* is ``True``.
    tuple[ArFrame, CleanExplanation]
        When only *explain* is ``True``.
    tuple[ArFrame, DataQualityReport, CleanExplanation]
        When both *return_report* and *explain* are ``True``.

    Examples
    --------
    >>> clean = ar.auto_clean(frame)
    >>> report = ar.auto_clean(frame, mode="strict", dry_run=True)
    >>> clean = ar.auto_clean(frame, mode="strict", allow_lossy_casts=True)
    >>> clean, report = ar.auto_clean(frame, mode="strict", return_report=True)
    >>> clean, explanation = ar.auto_clean(frame, explain=True)
    >>> print(explanation)
    """
    if not isinstance(frame, ArFrame):
        raise TypeError(
            f"auto_clean() expects an ArFrame, got {type(frame).__name__}. Use arnio.from_pandas() first."
        )

    if mode not in {"safe", "strict"}:
        raise ValueError("mode must be 'safe' or 'strict'")

    if not isinstance(return_report, bool):
        raise TypeError("return_report must be a bool")
    if not isinstance(dry_run, bool):
        raise TypeError("dry_run must be a bool")
    if not isinstance(allow_lossy_casts, bool):
        raise TypeError("allow_lossy_casts must be a bool")
    if not isinstance(explain, bool):
        raise TypeError("explain must be a bool")

    if dry_run and explain:
        raise ValueError("explain=True cannot be used with dry_run=True")
    if dry_run and return_report:
        raise ValueError("return_report=True cannot be used with dry_run=True")

    report = profile(frame)
    if dry_run:
        return report

    result = frame
    step_records: list[CleanStepRecord] = []
    rows_before_all = result.shape[0]

    for suggestion in report.suggestions:
        if isinstance(suggestion, CleaningSuggestion):
            step = suggestion.step
            kwargs = suggestion.kwargs
            reason = suggestion.confidence_reason
        else:
            step, kwargs = suggestion
            reason = step

        if mode == "safe" and step != "strip_whitespace":
            continue

        rows_before_step = result.shape[0]

        if step == "strip_whitespace":
            result = strip_whitespace(result, **kwargs)
        elif step == "cast_types":
            if not allow_lossy_casts:
                raise ValueError(
                    "auto_clean(mode='strict') would apply type casts. "
                    f"Proposed mapping: {kwargs}. Run with dry_run=True to inspect "
                    "the report, or pass allow_lossy_casts=True to apply them."
                )
            result = cast_types(result, kwargs)
        elif step == "drop_duplicates":
            result = drop_duplicates(result, **kwargs)
        else:
            continue

        rows_after_step = result.shape[0]
        step_records.append(
            CleanStepRecord(
                step=step,
                kwargs=kwargs,
                rows_before=rows_before_step,
                rows_after=rows_after_step,
                rows_removed=rows_before_step - rows_after_step,
                reason=reason,
            )
        )

    rows_after_all = result.shape[0]

    if explain:
        explanation = CleanExplanation(
            mode=mode,
            rows_before=rows_before_all,
            rows_after=rows_after_all,
            rows_removed=rows_before_all - rows_after_all,
            steps=step_records,
        )
        if return_report:
            return result, report, explanation
        return result, explanation

    if return_report:
        return result, report
    return result


def _profile_column(
    *,
    name: str,
    series: pd.Series,
    dtype: str,
    row_count: int,
    sample_size: int,
    approx_top_values: bool,
    approx_top_values_min_unique: int,
    approx_top_values_min_ratio: float,
    approx_top_values_sample_size: int,
) -> ColumnProfile:
    """Compute a full ColumnProfile for a single column series."""
    null_count = int(series.isna().sum())
    non_null = series.dropna()
    unique_count = int(non_null.nunique(dropna=True))
    unique_ratio = _ratio(unique_count, len(non_null))
    dominant_ratio = 0.0

    if len(non_null):
        value_counts = non_null.value_counts(dropna=True)
        dominant_ratio = _ratio(int(value_counts.iloc[0]), len(non_null))
    sample_values = non_null.head(sample_size).tolist()

    empty_string_count = 0
    whitespace_count = 0
    top_values = None
    top_values_is_approximate = False
    top_values_sample_count = None
    top_values_sample_ratio = None
    q25 = q50 = q75 = q95 = None
    std = None
    if dtype == "string" or pd.api.types.is_string_dtype(series.dtype):
        as_text = non_null.astype("string")
        stripped = as_text.str.strip()
        empty_string_count = int((stripped == "").sum())
        whitespace_count = int((as_text != stripped).sum())
        if (
            approx_top_values
            and unique_count >= approx_top_values_min_unique
            and unique_ratio >= approx_top_values_min_ratio
        ):
            top_values, sample_count, sample_ratio = _approx_top_values(
                non_null,
                sample_size=approx_top_values_sample_size,
            )
            top_values_is_approximate = True
            top_values_sample_count = sample_count
            top_values_sample_ratio = sample_ratio
        else:
            top_values = _top_values(non_null)

    min_value = max_value = mean = histogram = None
    if len(non_null) and _is_numeric_dtype(dtype):
        numeric = pd.to_numeric(series, errors="coerce")
        numeric_non_null = numeric.dropna()
        if len(numeric_non_null):
            min_value = numeric_non_null.min()
            max_value = numeric_non_null.max()
            mean = float(numeric_non_null.mean())
            std = float(numeric_non_null.std(ddof=0))
            quantiles = numeric_non_null.quantile([0.25, 0.50, 0.75, 0.95])
            q25 = round(float(quantiles.loc[0.25]), 4)
            q50 = round(float(quantiles.loc[0.50]), 4)
            q75 = round(float(quantiles.loc[0.75]), 4)
            q95 = round(float(quantiles.loc[0.95]), 4)

            # Calculate histogram
            finite_values = numeric_non_null[np.isfinite(numeric_non_null)]
            if len(finite_values):
                counts, bin_edges = np.histogram(finite_values.to_numpy(), bins=10)
                total = int(counts.sum())
                histogram = [
                    (
                        float(bin_edges[i]),
                        float(bin_edges[i + 1]),
                        int(counts[i]),
                        _ratio(int(counts[i]), total),
                    )
                    for i in range(len(counts))
                ]
            else:
                histogram = None
    elif len(non_null) and (
        dtype == "string" or pd.api.types.is_string_dtype(series.dtype)
    ):
        lengths = non_null.astype("string").str.len()
        min_value = int(lengths.min())
        max_value = int(lengths.max())
        mean = float(lengths.mean())

    semantic_type = _detect_semantic_type(name, series, dtype)
    suggested_dtype = _suggest_column_dtype(series, dtype)

    email_validity_ratio = None
    url_validity_ratio = None
    if len(non_null) > 0:
        if semantic_type == "email":
            email_validity_ratio = _match_ratio(
                non_null.astype("string").str.strip(), _EMAIL_PATTERN
            )
        elif semantic_type == "url":
            url_validity_ratio = _match_ratio(
                non_null.astype("string").str.strip(), _URL_PATTERN
            )

    warnings = _column_warnings(
        null_count=null_count,
        row_count=row_count,
        unique_count=unique_count,
        unique_ratio=unique_ratio,
        semantic_type=semantic_type,
        whitespace_count=whitespace_count,
        empty_string_count=empty_string_count,
        dominant_ratio=dominant_ratio,
    )

    return ColumnProfile(
        name=name,
        dtype=dtype,
        semantic_type=semantic_type,
        row_count=row_count,
        null_count=null_count,
        null_ratio=_ratio(null_count, row_count),
        unique_count=unique_count,
        unique_ratio=unique_ratio,
        empty_string_count=empty_string_count,
        whitespace_count=whitespace_count,
        suggested_dtype=suggested_dtype,
        email_validity_ratio=email_validity_ratio,
        url_validity_ratio=url_validity_ratio,
        min=min_value,
        max=max_value,
        mean=mean,
        std=std,
        q25=q25,
        q50=q50,
        q75=q75,
        q95=q95,
        sample_values=sample_values,
        warnings=warnings,
        top_values=top_values,
        top_values_is_approximate=top_values_is_approximate,
        top_values_sample_count=top_values_sample_count,
        top_values_sample_ratio=top_values_sample_ratio,
        histogram=histogram,
    )


def _detect_semantic_type(name: str, series: pd.Series, dtype: str) -> str:
    """Infer the semantic type of a column from its name, dtype, and value patterns."""
    lower_name = name.lower()
    values = series.dropna().astype("string").str.strip()
    if len(values) == 0:
        return "empty"

    if lower_name in {
        "id",
        "uuid",
        "zip",
        "zipcode",
        "zip_code",
    } or lower_name.endswith("_id"):
        return "identifier"
    if _is_numeric_dtype(dtype):
        return "numeric"
    if dtype == "bool":
        return "boolean"
    if _match_ratio(values, _EMAIL_PATTERN) >= 0.8:
        return "email"
    if _match_ratio(values, _URL_PATTERN) >= 0.8:
        return "url"
    if _match_ratio(values, _PHONE_PATTERN) >= 0.8:
        return "phone"
    if _looks_like_datetime(values):
        return "datetime"
    if len(values) > 0 and values.nunique(dropna=True) <= max(20, len(values) * 0.2):
        return "categorical"
    return "text"


def _suggest_casts(report: DataQualityReport) -> dict[str, str]:
    """Return a mapping of column names to suggested dtype casts based on the profile report."""
    mapping: dict[str, str] = {}
    for name, column in report.columns.items():
        if column.suggested_dtype is not None:
            # Skip numeric casts for identifier-like columns to prevent data loss (e.g., leading zeros)
            if column.semantic_type == "identifier" and column.suggested_dtype in {
                "int64",
                "float64",
            }:
                continue
            mapping[name] = column.suggested_dtype
    return mapping


def _suggest_column_dtype(series: pd.Series, dtype: str) -> str | None:
    """Return a suggested target dtype if a string column appears safely castable, else None."""
    if dtype != "string":
        return None
    values = series.dropna().astype("string").str.strip()
    if len(values) == 0:
        return None

    lower = values.str.lower()
    if lower.isin(["true", "false", "1", "0"]).all():
        return "bool"

    numeric = pd.to_numeric(values, errors="coerce")
    if numeric.notna().all():
        if values.str.fullmatch(r"[+-]?\d+").all():
            return "int64"
        return "float64"
    return None


def _column_warnings(
    *,
    null_count: int,
    row_count: int,
    unique_count: int,
    unique_ratio: float,
    semantic_type: str,
    whitespace_count: int,
    empty_string_count: int,
    dominant_ratio: float,
) -> list[str]:
    """Build a list of warning flag strings for a column based on its profile statistics."""
    warnings: list[str] = []
    if null_count:
        warnings.append("contains_nulls")
    if row_count and null_count == row_count:
        warnings.append("all_null")
    if row_count and unique_count == 1:
        warnings.append("constant")
    if row_count and unique_count > 1 and dominant_ratio >= _NEAR_CONSTANT_THRESHOLD:
        warnings.append("near_constant")
    non_null_count = row_count - null_count
    if (
        non_null_count > 0
        and unique_count >= _HIGH_CARDINALITY_MIN_UNIQUE
        and unique_ratio >= _HIGH_CARDINALITY_RATIO_THRESHOLD
        and semantic_type in {"identifier", "text"}
    ):
        warnings.append("high_cardinality")
    if whitespace_count:
        warnings.append("leading_or_trailing_whitespace")
    if empty_string_count:
        warnings.append("empty_strings")
    return warnings


def _match_ratio(values: pd.Series, pattern: str) -> float:
    """Return the fraction of values in a series that fully match a regex pattern."""
    return _ratio(int(values.str.fullmatch(pattern, na=False).sum()), len(values))


def _looks_like_datetime(values: pd.Series) -> bool:
    """Return True if the majority of values look like parseable date strings."""
    date_like = values.str.fullmatch(
        r"(\d{4}-\d{1,2}-\d{1,2})|(\d{1,2}/\d{1,2}/\d{2,4})",
        na=False,
    )
    if _ratio(int(date_like.sum()), len(values)) < 0.8:
        return False
    parsed = pd.to_datetime(values, errors="coerce")
    return _ratio(int(parsed.notna().sum()), len(values)) >= 0.8


def _is_numeric_dtype(dtype: str) -> bool:
    """Return True if dtype is int64 or float64."""
    return dtype in {"int64", "float64"}


def _ratio(part: int, total: int) -> float:
    """Return part/total rounded to 6 decimal places, or 0.0 if total is zero."""
    if total == 0:
        return 0.0
    return round(part / total, 6)


def _clean_scalar(value: Any) -> Any:
    """Convert NaN and numpy scalar values to JSON-safe Python types."""
    if pd.isna(value):
        return None
    if hasattr(value, "item"):
        return value.item()
    return value


_APPROX_TOP_VALUES_SEED = 0
_NEAR_CONSTANT_THRESHOLD = 0.95
_HIGH_CARDINALITY_RATIO_THRESHOLD = 0.9
_HIGH_CARDINALITY_MIN_UNIQUE = 100


def _top_values(
    series: pd.Series,
    n: int = 5,
) -> list[tuple[Any, int, float]]:
    """Return top-N value frequencies for a non-null series.

    Nulls are excluded. Percentages are based on the non-null total.
    """
    if len(series) == 0:
        return []
    counts = series.value_counts(dropna=True)
    total = int(counts.sum())
    return [
        (val, int(cnt), _ratio(int(cnt), total)) for val, cnt in counts.head(n).items()
    ]


def _approx_top_values(
    series: pd.Series,
    *,
    n: int = 5,
    sample_size: int = 2000,
) -> tuple[list[tuple[Any, int, float]], int, float]:
    """Return approximate top-N value frequencies for a non-null series.

    Sampling uses a fixed seed for deterministic output.
    """
    if len(series) == 0:
        return [], 0, 0.0
    sample_n = min(len(series), sample_size)
    sampled = series.sample(n=sample_n, random_state=_APPROX_TOP_VALUES_SEED)
    counts = sampled.value_counts(dropna=True)
    total = int(counts.sum())
    return (
        [
            (val, int(cnt), _ratio(int(cnt), total))
            for val, cnt in counts.head(n).items()
        ],
        sample_n,
        _ratio(sample_n, len(series)),
    )


_EMAIL_PATTERN = r"[^@\s]+@[^@\s]+\.[^@\s]+"
_URL_PATTERN = r"https?://[^\s]+"
_PHONE_PATTERN = r"\+?[0-9][0-9 .()\-]{6,}[0-9]"
