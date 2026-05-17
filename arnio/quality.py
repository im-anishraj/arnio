"""
arnio.quality
Data quality profiling and safe automatic cleaning helpers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd
import json

from .cleaning import cast_types, drop_duplicates, strip_whitespace
from .convert import to_pandas
from .frame import ArFrame


@dataclass(frozen=True)
class ColumnProfile:
    """Quality profile for one column."""

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
    sample_values: list[Any] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    top_values: list[tuple[Any, int, float]] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-friendly dictionary."""
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
            "sample_values": [_clean_scalar(value) for value in self.sample_values],
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
    suggestions: list[tuple[str, dict[str, Any]]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-friendly dictionary representation."""
        return {
            "row_count": self.row_count,
            "column_count": self.column_count,
            "memory_usage": self.memory_usage,
            "duplicate_rows": self.duplicate_rows,
            "duplicate_ratio": self.duplicate_ratio,
            "columns": {
                name: column.to_dict() for name, column in self.columns.items()
            },
            "suggestions": [
                {"step": step, "kwargs": dict(kwargs)}
                for step, kwargs in self.suggestions
            ],
        }
         
    def to_json(self, **kwargs: Any) -> str:
        """Return a JSON string representation of the report."""
        return json.dumps(self.to_dict(), **kwargs)
    
    def summary(self) -> dict[str, Any]:
        """Return the highest-signal report fields."""
        return {
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

    return DataQualityReport(
        row_count=report.row_count,
        column_count=report.column_count,
        memory_usage=report.memory_usage,
        duplicate_rows=report.duplicate_rows,
        duplicate_ratio=report.duplicate_ratio,
        columns=report.columns,
        suggestions=suggest_cleaning(report),
    )


def suggest_cleaning(
    frame_or_report: ArFrame | DataQualityReport,
) -> list[tuple[str, dict[str, Any]]]:
    """Suggest safe built-in cleaning steps.

    Parameters
    ----------
    frame_or_report : ArFrame or DataQualityReport
        Frame to profile or an existing report.

    Returns
    -------
    list[tuple[str, dict[str, Any]]]
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

    suggestions: list[tuple[str, dict[str, Any]]] = []
    whitespace_columns = [
        name for name, column in report.columns.items() if column.whitespace_count > 0
    ]
    if whitespace_columns:
        suggestions.append(("strip_whitespace", {"subset": whitespace_columns}))

    cast_mapping = _suggest_casts(report)
    if cast_mapping:
        suggestions.append(("cast_types", cast_mapping))

    if report.duplicate_rows > 0:
        suggestions.append(("drop_duplicates", {"keep": "first"}))

    return suggestions


def auto_clean(
    frame: ArFrame,
    *,
    mode: str = "safe",
    return_report: bool = False,
) -> ArFrame | tuple[ArFrame, DataQualityReport]:
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

    Returns
    -------
    ArFrame or tuple[ArFrame, DataQualityReport]
        Cleaned frame, optionally with the source quality report.

    Examples
    --------
    >>> clean = ar.auto_clean(frame)
    >>> clean, report = ar.auto_clean(frame, mode="strict", return_report=True)
    """
    if mode not in {"safe", "strict"}:
        raise ValueError("mode must be 'safe' or 'strict'")

    report = profile(frame)
    result = frame

    for step, kwargs in report.suggestions:
        if mode == "safe" and step != "strip_whitespace":
            continue
        if step == "strip_whitespace":
            result = strip_whitespace(result, **kwargs)
        elif step == "cast_types":
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
    if dtype == "string" or pd.api.types.is_string_dtype(series.dtype):
        as_text = non_null.astype("string")
        stripped = as_text.str.strip()
        empty_string_count = int((stripped == "").sum())
        whitespace_count = int((as_text != stripped).sum())
        top_values = _top_values(non_null)

    numeric = pd.to_numeric(series, errors="coerce")
    numeric_non_null = numeric.dropna()
    min_value = max_value = mean = None
    if len(numeric_non_null) and _is_numeric_dtype(dtype):
        min_value = numeric_non_null.min()
        max_value = numeric_non_null.max()
        mean = float(numeric_non_null.mean())

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
