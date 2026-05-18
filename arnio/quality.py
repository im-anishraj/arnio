"""
arnio.quality
Data quality profiling and safe automatic cleaning helpers.
"""

from __future__ import annotations

import html
import json
from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from .cleaning import cast_types, drop_duplicates, strip_whitespace
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
    min: Any = None
    max: Any = None
    mean: float | None = None
    q25: float | None = None
    q50: float | None = None
    q75: float | None = None
    q95: float | None = None
    sample_values: list[Any] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    top_values: list[tuple[Any, int, float]] | None = None

    def to_dict(self, *, redact_sample_values: bool = False) -> dict[str, Any]:
        """Return a JSON-friendly dictionary."""
        sample_values = (
            ["[REDACTED]" for _ in self.sample_values]
            if redact_sample_values
            else [_clean_scalar(value) for value in self.sample_values]
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
            "min": _clean_scalar(self.min),
            "max": _clean_scalar(self.max),
            "mean": self.mean,
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
            "top_values": (
                [
                    {"value": _clean_scalar(v), "count": c, "ratio": r}
                    for v, c, r in self.top_values
                ]
                if self.top_values is not None
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

    def to_dict(self, *, redact_sample_values: bool = False) -> dict[str, Any]:
        """Return a JSON-friendly dictionary representation."""
        return {
            "row_count": self.row_count,
            "column_count": self.column_count,
            "memory_usage": self.memory_usage,
            "duplicate_rows": self.duplicate_rows,
            "duplicate_ratio": self.duplicate_ratio,
            "quality_score": self.quality_score,
            "score_components": self.score_components,
            "columns": {
                name: column.to_dict(redact_sample_values=redact_sample_values)
                for name, column in self.columns.items()
            },
            "suggestions": [
                {
                    "step": s[0],
                    "kwargs": dict(s[1]),
                    "confidence_score": getattr(s, "confidence_score", None),
                    "confidence_reason": getattr(s, "confidence_reason", None),
                }
                for s in self.suggestions
            ],
        }

    def to_json(self, **kwargs: Any) -> str:
        """Return a JSON string representation of the report."""
        return json.dumps(self.to_dict(), **kwargs)

    def to_markdown(self) -> str:
        """Return a GitHub-friendly Markdown report."""

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
                    f"| {column.name} "
                    f"| {column.dtype} "
                    f"| {column.semantic_type} "
                    f"| {column.null_count} "
                    f"| {column.unique_count} "
                    f"| {column.unique_ratio:.2%} "
                    f"| {warnings} |"
                )

            lines.append("")

        # Suggestions
        if self.suggestions:
            lines.append("## Suggested Cleaning Steps")
            lines.append("")

            for step in self.suggestions:
                conf_score = getattr(step, "confidence_score", None)
                conf_reason = getattr(step, "confidence_reason", None)
                if conf_score is not None and conf_reason is not None:
                    lines.append(
                        f"- `{step[0]}`: `{step[1]}` "
                        f"(Confidence: {conf_score:.2f} - {conf_reason})"
                    )
                else:
                    lines.append(f"- `{step[0]}`: `{step[1]}`")

            lines.append("")

        return "\n".join(lines)

    def to_html(self, file_path: str | None = None) -> str:
        """Return a self-contained, dependency-free HTML data quality report."""

        def e(text: Any) -> str:
            return html.escape(str(text))

        styles = """
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 20px; background-color: #f8f9fa; }
        .container { max-width: 1200px; margin: 0 auto; background: #fff; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        h1, h2 { color: #2c3e50; border-bottom: 1px solid #eee; padding-bottom: 10px; }
        .metrics-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-bottom: 30px; }
        .metric-card { background: #f8f9fa; padding: 15px; border-radius: 6px; border: 1px solid #e9ecef; text-align: center; }
        .metric-value { font-size: 24px; font-weight: bold; color: #007bff; }
        .metric-label { font-size: 14px; color: #6c757d; text-transform: uppercase; letter-spacing: 0.5px; }
        table { width: 100%; border-collapse: collapse; margin-bottom: 30px; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #dee2e6; }
        th { background-color: #f8f9fa; font-weight: 600; color: #495057; }
        tr:hover { background-color: #f1f3f5; }
        .warnings { color: #dc3545; font-size: 14px; }
        .suggestion { background: #e8f4f8; border-left: 4px solid #17a2b8; padding: 10px 15px; margin-bottom: 10px; }
        .suggestion code { font-family: monospace; background: #fff; padding: 2px 5px; border-radius: 3px; border: 1px solid #ced4da; }
        """

        lines: list[str] = []
        lines.append("<!DOCTYPE html>")
        lines.append('<html lang="en">')
        lines.append("<head>")
        lines.append('    <meta charset="UTF-8">')
        lines.append(
            '    <meta name="viewport" content="width=device-width, initial-scale=1.0">'
        )
        lines.append("    <title>Data Quality Report</title>")
        lines.append(f"    <style>{styles}</style>")
        lines.append("</head>")
        lines.append("<body>")
        lines.append('    <div class="container">')
        lines.append("        <h1>Data Quality Report</h1>")

        lines.append('        <div class="metrics-grid">')
        metrics = [
            ("Rows", self.row_count),
            ("Columns", self.column_count),
            ("Memory Usage", self.memory_usage),
            ("Duplicate Rows", self.duplicate_rows),
            ("Duplicate Ratio", f"{self.duplicate_ratio:.2%}"),
            ("Quality Score", f"{self.quality_score:.2f}"),
        ]
        for label, value in metrics:
            lines.append('            <div class="metric-card">')
            lines.append(f'                <div class="metric-value">{e(value)}</div>')
            lines.append(f'                <div class="metric-label">{e(label)}</div>')
            lines.append("            </div>")
        lines.append("        </div>")

        if self.columns:
            lines.append("        <h2>Columns Overview</h2>")
            lines.append("        <table>")
            lines.append("            <thead>")
            lines.append("                <tr>")
            lines.append("                    <th>Name</th>")
            lines.append("                    <th>Type</th>")
            lines.append("                    <th>Nulls</th>")
            lines.append("                    <th>Unique</th>")
            lines.append("                    <th>Warnings</th>")
            lines.append("                </tr>")
            lines.append("            </thead>")
            lines.append("            <tbody>")

            for name in sorted(self.columns):
                col = self.columns[name]
                warnings_str = ", ".join(col.warnings) if col.warnings else "-"
                lines.append("                <tr>")
                lines.append(f"                    <td>{e(col.name)}</td>")
                lines.append(f"                    <td>{e(col.dtype)}</td>")
                lines.append(f"                    <td>{e(col.null_count)}</td>")
                lines.append(f"                    <td>{e(col.unique_count)}</td>")
                lines.append(
                    f'                    <td class="warnings">{e(warnings_str)}</td>'
                )
                lines.append("                </tr>")

            lines.append("            </tbody>")
            lines.append("        </table>")

        if self.suggestions:
            lines.append("        <h2>Cleaning Suggestions</h2>")
            for step in self.suggestions:
                conf_score = getattr(step, "confidence_score", None)
                conf_text = (
                    f" (Confidence: {conf_score:.2f})" if conf_score is not None else ""
                )
                lines.append('        <div class="suggestion">')
                lines.append(
                    f"            <code>{e(step[0])}</code>: <code>{e(step[1])}</code>{e(conf_text)}"
                )
                lines.append("        </div>")

        lines.append("    </div>")
        lines.append("</body>")
        lines.append("</html>")

        html_out = "\n".join(lines)
        if file_path:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(html_out)

        return html_out

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
                    "min": _clean_scalar(column.min),
                    "max": _clean_scalar(column.max),
                    "mean": column.mean,
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
                }
                for column in self.columns.values()
            ]
        )


def profile(frame: ArFrame, *, sample_size: int = 5) -> DataQualityReport:
    """Profile data quality for an ArFrame.

    Parameters
    ----------
    frame : ArFrame
        Input frame to inspect.
    sample_size : int, default 5
        Number of non-null sample values to keep per column.

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
    if not isinstance(sample_size, int) or isinstance(sample_size, bool):
        raise TypeError("sample_size must be an integer")
    if sample_size < 0:
        raise ValueError("sample_size must be non-negative")

    df = to_pandas(frame)
    row_count, column_count = frame.shape
    duplicate_rows = int(df.duplicated().sum()) if row_count else 0
    duplicate_ratio = _ratio(duplicate_rows, row_count)

    columns = {
        name: _profile_column(
            name=name,
            series=df[name],
            dtype=frame.dtypes.get(name, str(df[name].dtype)),
            row_count=row_count,
            sample_size=sample_size,
        )
        for name in df.columns
    }

    report = DataQualityReport(
        row_count=row_count,
        column_count=column_count,
        memory_usage=frame.memory_usage(),
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


def _calculate_quality_score(
    row_count: int,
    duplicate_ratio: float,
    columns: dict[str, ColumnProfile],
) -> tuple[float, dict[str, float]]:
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


def auto_clean(
    frame: ArFrame,
    *,
    mode: str = "safe",
    return_report: bool = False,
    dry_run: bool = False,
    allow_lossy_casts: bool = False,
) -> ArFrame | DataQualityReport | tuple[ArFrame, DataQualityReport]:
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

    Returns
    -------
    ArFrame, DataQualityReport, or tuple[ArFrame, DataQualityReport]
        Cleaned frame, the dry-run report, or a frame/report tuple.

    Examples
    --------
    >>> clean = ar.auto_clean(frame)
    >>> report = ar.auto_clean(frame, mode="strict", dry_run=True)
    >>> clean = ar.auto_clean(frame, mode="strict", allow_lossy_casts=True)
    """
    if mode not in {"safe", "strict"}:
        raise ValueError("mode must be 'safe' or 'strict'")

    if not isinstance(dry_run, bool):
        raise TypeError("dry_run must be a bool")
    if not isinstance(allow_lossy_casts, bool):
        raise TypeError("allow_lossy_casts must be a bool")

    report = profile(frame)
    if dry_run:
        if return_report:
            return frame, report
        return report

    result = frame

    for step, kwargs in report.suggestions:
        if mode == "safe" and step != "strip_whitespace":
            continue
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
) -> ColumnProfile:
    null_count = int(series.isna().sum())
    non_null = series.dropna()
    unique_count = int(non_null.nunique(dropna=True))
    unique_ratio = _ratio(unique_count, len(non_null))
    sample_values = non_null.head(sample_size).tolist()

    empty_string_count = 0
    whitespace_count = 0
    top_values = None
    q25 = q50 = q75 = q95 = None
    if dtype == "string" or pd.api.types.is_string_dtype(series.dtype):
        as_text = non_null.astype("string")
        stripped = as_text.str.strip()
        empty_string_count = int((stripped == "").sum())
        whitespace_count = int((as_text != stripped).sum())
        top_values = _top_values(non_null)

    min_value = max_value = mean = None
    if len(non_null) and _is_numeric_dtype(dtype):
        numeric = pd.to_numeric(series, errors="coerce")
        numeric_non_null = numeric.dropna()
        if len(numeric_non_null):
            min_value = numeric_non_null.min()
            max_value = numeric_non_null.max()
            mean = float(numeric_non_null.mean())
            quantiles = numeric_non_null.quantile([0.25, 0.50, 0.75, 0.95])
            q25 = round(float(quantiles.loc[0.25]), 4)
            q50 = round(float(quantiles.loc[0.50]), 4)
            q75 = round(float(quantiles.loc[0.75]), 4)
            q95 = round(float(quantiles.loc[0.95]), 4)
    elif len(non_null) and (
        dtype == "string" or pd.api.types.is_string_dtype(series.dtype)
    ):
        lengths = non_null.astype("string").str.len()
        min_value = int(lengths.min())
        max_value = int(lengths.max())
        mean = float(lengths.mean())

    semantic_type = _detect_semantic_type(name, series, dtype)
    suggested_dtype = _suggest_column_dtype(series, dtype)
    warnings = _column_warnings(
        null_count=null_count,
        row_count=row_count,
        unique_count=unique_count,
        whitespace_count=whitespace_count,
        empty_string_count=empty_string_count,
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
        min=min_value,
        max=max_value,
        mean=mean,
        q25=q25,
        q50=q50,
        q75=q75,
        q95=q95,
        sample_values=sample_values,
        warnings=warnings,
        top_values=top_values,
    )


def _detect_semantic_type(name: str, series: pd.Series, dtype: str) -> str:
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
        return "int64" if (numeric % 1 == 0).all() else "float64"
    return None


def _column_warnings(
    *,
    null_count: int,
    row_count: int,
    unique_count: int,
    whitespace_count: int,
    empty_string_count: int,
) -> list[str]:
    warnings: list[str] = []
    if null_count:
        warnings.append("contains_nulls")
    if row_count and null_count == row_count:
        warnings.append("all_null")
    if row_count and unique_count == 1:
        warnings.append("constant")
    if whitespace_count:
        warnings.append("leading_or_trailing_whitespace")
    if empty_string_count:
        warnings.append("empty_strings")
    return warnings


def _match_ratio(values: pd.Series, pattern: str) -> float:
    return _ratio(int(values.str.fullmatch(pattern, na=False).sum()), len(values))


def _looks_like_datetime(values: pd.Series) -> bool:
    date_like = values.str.fullmatch(
        r"(\d{4}-\d{1,2}-\d{1,2})|(\d{1,2}/\d{1,2}/\d{2,4})",
        na=False,
    )
    if _ratio(int(date_like.sum()), len(values)) < 0.8:
        return False
    parsed = pd.to_datetime(values, errors="coerce")
    return _ratio(int(parsed.notna().sum()), len(values)) >= 0.8


def _is_numeric_dtype(dtype: str) -> bool:
    return dtype in {"int64", "float64"}


def _ratio(part: int, total: int) -> float:
    if total == 0:
        return 0.0
    return round(part / total, 6)


def _clean_scalar(value: Any) -> Any:
    if pd.isna(value):
        return None
    if hasattr(value, "item"):
        return value.item()
    return value


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


_EMAIL_PATTERN = r"[^@\s]+@[^@\s]+\.[^@\s]+"
_URL_PATTERN = r"https?://[^\s]+"
_PHONE_PATTERN = r"\+?[0-9][0-9 .()\-]{6,}[0-9]"
