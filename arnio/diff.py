"""
arnio.diff
DataFrame-level drift detection.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd


@dataclass(frozen=True)
class ColumnDiff:
    """Drift details for a single column."""

    name: str
    change: str  # "added", "removed", "dtype_changed", "null_ratio_changed"
    expected_dtype: str | None = None
    observed_dtype: str | None = None
    expected_null_ratio: float | None = None
    observed_null_ratio: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "change": self.change,
            "expected_dtype": self.expected_dtype,
            "observed_dtype": self.observed_dtype,
            "expected_null_ratio": self.expected_null_ratio,
            "observed_null_ratio": self.observed_null_ratio,
        }


@dataclass(frozen=True)
class DataFrameDiffReport:
    """Result of comparing two DataFrames for drift."""

    expected_row_count: int
    observed_row_count: int
    column_diffs: list[ColumnDiff] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not isinstance(self.expected_row_count, int) or isinstance(
            self.expected_row_count, bool
        ):
            raise TypeError("expected_row_count must be an int")
        if self.expected_row_count < 0:
            raise ValueError("expected_row_count must be >= 0")
        if not isinstance(self.observed_row_count, int) or isinstance(
            self.observed_row_count, bool
        ):
            raise TypeError("observed_row_count must be an int")
        if self.observed_row_count < 0:
            raise ValueError("observed_row_count must be >= 0")
        if not isinstance(self.column_diffs, list):
            raise TypeError("column_diffs must be a list")
        for item in self.column_diffs:
            if not isinstance(item, ColumnDiff):
                raise TypeError("column_diffs must contain ColumnDiff instances")

    @property
    def row_count_delta(self) -> int:
        """Difference in row count (observed - expected)."""
        return self.observed_row_count - self.expected_row_count

    @property
    def has_breaking_changes(self) -> bool:
        """True if any column was removed or had a dtype change."""
        breaking = {"removed", "dtype_changed"}
        return any(cd.change in breaking for cd in self.column_diffs)

    @property
    def is_clean(self) -> bool:
        """True if there are no column diffs and no row count delta."""
        return not self.column_diffs and self.row_count_delta == 0

    def summary(self) -> str:
        """Return a compact human-readable summary of the drift report."""
        by_change: dict[str, int] = {}
        for cd in self.column_diffs:
            by_change[cd.change] = by_change.get(cd.change, 0) + 1

        parts = [
            f"status: {'clean' if self.is_clean else 'drifted'}",
            f"breaking_changes: {'yes' if self.has_breaking_changes else 'no'}",
            f"rows: {self.expected_row_count} -> {self.observed_row_count} (delta: {self.row_count_delta:+d})",
            f"column_diffs: {len(self.column_diffs)}",
        ]
        if by_change:
            breakdown = ", ".join(f"{k}={v}" for k, v in sorted(by_change.items()))
            parts.append(f"changes: {breakdown}")
        return "\n".join(parts)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-friendly dictionary."""
        return {
            "is_clean": self.is_clean,
            "has_breaking_changes": self.has_breaking_changes,
            "expected_row_count": self.expected_row_count,
            "observed_row_count": self.observed_row_count,
            "row_count_delta": self.row_count_delta,
            "column_diffs": [cd.to_dict() for cd in self.column_diffs],
        }

    def to_markdown(self) -> str:
        """Return a GitHub-friendly Markdown drift report."""
        status = "clean" if self.is_clean else "drifted"
        lines = [
            "## DataFrame Diff Report",
            "",
            f"- Status: **{status}**",
            f"- Row count: {self.expected_row_count} → {self.observed_row_count} (delta: {self.row_count_delta:+d})",
            f"- Breaking changes: **{'yes' if self.has_breaking_changes else 'no'}**",
            f"- Column diffs: {len(self.column_diffs)}",
        ]
        if not self.column_diffs:
            return "\n".join(lines)

        lines.extend(
            [
                "",
                "| Column | Change | Expected dtype | Observed dtype | Expected null% | Observed null% |",
                "|---|---|---|---|---|---|",
            ]
        )
        for cd in self.column_diffs:

            def _fmt(v: Any) -> str:
                if v is None:
                    return ""
                if isinstance(v, float):
                    return f"{v:.1%}"
                return str(v)

            lines.append(
                f"| {cd.name} | {cd.change} | {_fmt(cd.expected_dtype)} | "
                f"{_fmt(cd.observed_dtype)} | {_fmt(cd.expected_null_ratio)} | "
                f"{_fmt(cd.observed_null_ratio)} |"
            )
        return "\n".join(lines)


def _null_ratio(series: pd.Series) -> float:
    """Return the fraction of null/empty values in a series."""
    if len(series) == 0:
        return 0.0
    null_mask = series.isna()
    if series.dtype == object or hasattr(series, "str"):
        try:
            null_mask = null_mask | (series.fillna("").astype(str).str.strip() == "")
        except Exception:
            pass
    return float(null_mask.sum()) / len(series)


def _infer_dtype(series: pd.Series) -> str:
    """Map a pandas dtype to an arnio dtype string."""
    dtype_str = str(series.dtype)
    mapping = {
        "int64": "int64",
        "int32": "int64",
        "float64": "float64",
        "float32": "float64",
        "bool": "bool",
        "object": "string",
        "string": "string",
        "str": "string",
    }
    if dtype_str.startswith("datetime"):
        return "datetime"
    return mapping.get(dtype_str, dtype_str)


def diff_dataframes(
    expected: pd.DataFrame,
    observed: pd.DataFrame,
    *,
    null_ratio_threshold: float = 0.0,
) -> DataFrameDiffReport:
    """Compare two DataFrames and return a drift report.

    Parameters
    ----------
    expected : pd.DataFrame
        Baseline DataFrame.
    observed : pd.DataFrame
        New DataFrame to compare against the baseline.
    null_ratio_threshold : float, default 0.0
        Minimum absolute change in null ratio to flag as drift.
        Set to e.g. 0.05 to ignore small fluctuations.

    Returns
    -------
    DataFrameDiffReport

    Raises
    ------
    TypeError
        If either argument is not a pandas DataFrame.
    ValueError
        If null_ratio_threshold is not in [0.0, 1.0].
    """
    if not isinstance(expected, pd.DataFrame):
        raise TypeError(
            f"expected must be a pandas DataFrame, got {type(expected).__name__}"
        )
    if not isinstance(observed, pd.DataFrame):
        raise TypeError(
            f"observed must be a pandas DataFrame, got {type(observed).__name__}"
        )
    if not isinstance(null_ratio_threshold, (int, float)) or isinstance(
        null_ratio_threshold, bool
    ):
        raise TypeError("null_ratio_threshold must be a float")
    if not (0.0 <= null_ratio_threshold <= 1.0):
        raise ValueError("null_ratio_threshold must be between 0.0 and 1.0")

    expected_cols = set(expected.columns)
    observed_cols = set(observed.columns)
    diffs: list[ColumnDiff] = []

    # Removed columns
    for col in sorted(expected_cols - observed_cols):
        diffs.append(
            ColumnDiff(
                name=col,
                change="removed",
                expected_dtype=_infer_dtype(expected[col]),
            )
        )

    # Added columns
    for col in sorted(observed_cols - expected_cols):
        diffs.append(
            ColumnDiff(
                name=col,
                change="added",
                observed_dtype=_infer_dtype(observed[col]),
            )
        )

    # Common columns check dtype and null ratio
    for col in sorted(expected_cols & observed_cols):
        exp_dtype = _infer_dtype(expected[col])
        obs_dtype = _infer_dtype(observed[col])

        if exp_dtype != obs_dtype:
            diffs.append(
                ColumnDiff(
                    name=col,
                    change="dtype_changed",
                    expected_dtype=exp_dtype,
                    observed_dtype=obs_dtype,
                )
            )
            continue  # dtype change is already breaking; skip null ratio for this col

        exp_null = _null_ratio(expected[col])
        obs_null = _null_ratio(observed[col])

        if abs(obs_null - exp_null) > null_ratio_threshold:
            diffs.append(
                ColumnDiff(
                    name=col,
                    change="null_ratio_changed",
                    expected_dtype=exp_dtype,
                    observed_dtype=obs_dtype,
                    expected_null_ratio=exp_null,
                    observed_null_ratio=obs_null,
                )
            )

    return DataFrameDiffReport(
        expected_row_count=len(expected),
        observed_row_count=len(observed),
        column_diffs=diffs,
    )
