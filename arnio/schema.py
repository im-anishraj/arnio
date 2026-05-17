"""
arnio.schema
Production data contracts and validation.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import pandas as pd

from .convert import to_pandas
from .frame import ArFrame

DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")


@dataclass(frozen=True)
class Field:
    """Validation rules for one column."""

    dtype: str | None = None
    nullable: bool = True
    min: int | float | None = None
    max: int | float | None = None
    pattern: str | None = None
    semantic: str | None = None
    allowed: set[Any] | None = None
    unique: bool = False
    min_length: int | None = None
    max_length: int | None = None


@dataclass(frozen=True)
class Schema:
    """Named column validation contract."""

    fields: dict[str, Field]
    strict: bool = False

    def validate(self, frame: ArFrame) -> ValidationResult:
        """Validate a frame against this schema."""
        return validate(frame, self)


@dataclass(frozen=True)
class ValidationIssue:
    """One validation failure."""

    column: str | None
    rule: str
    message: str
    row_index: int | None = None
    value: Any = None

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-friendly dictionary."""
        return {
            "column": self.column,
            "rule": self.rule,
            "message": self.message,
            "row_index": self.row_index,
            "value": _clean_scalar(self.value),
        }


@dataclass(frozen=True)
class ValidationResult:
    """Validation output with row-level issues."""

    row_count: int
    issue_count: int
    issues: list[ValidationIssue]
    bad_rows: list[int] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        """Whether validation passed with zero issues."""
        return self.issue_count == 0

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-friendly dictionary."""
        return {
            "passed": self.passed,
            "row_count": self.row_count,
            "issue_count": self.issue_count,
            "bad_rows": list(self.bad_rows),
            "issues": [issue.to_dict() for issue in self.issues],
        }

    def summary(self) -> dict[str, Any]:
        """Return a compact validation summary.

        Severity counts are not included because ``ValidationIssue`` does not
        currently carry severity information.
        """
        by_rule: dict[str, int] = {}
        by_column: dict[str, int] = {}
        by_column_and_rule: dict[str, dict[str, int]] = {}
        for issue in self.issues:
            by_rule[issue.rule] = by_rule.get(issue.rule, 0) + 1
            if issue.column is not None:
                by_column[issue.column] = by_column.get(issue.column, 0) + 1
                column_rules = by_column_and_rule.setdefault(issue.column, {})
                column_rules[issue.rule] = column_rules.get(issue.rule, 0) + 1
        return {
            "passed": self.passed,
            "issue_count": self.issue_count,
            "bad_row_count": len(self.bad_rows),
            "issues_by_rule": by_rule,
            "issues_by_column": by_column,
            "issues_by_column_and_rule": by_column_and_rule,
        }

    def to_pandas(self) -> pd.DataFrame:
        """Return issues as a pandas DataFrame."""
        return pd.DataFrame([issue.to_dict() for issue in self.issues])

    def to_markdown(self, *, max_issues: int | None = None) -> str:
        """Return a GitHub-friendly Markdown validation report.

        Parameters
        ----------
        max_issues : int, optional
            Maximum number of issues to include in the table. When omitted, all
            issues are shown.
        """
        if max_issues is not None and (
            not isinstance(max_issues, int) or isinstance(max_issues, bool)
        ):
            raise TypeError("max_issues must be an integer or None")
        if max_issues is not None and max_issues < 0:
            raise ValueError("max_issues must be non-negative")

        status = "passed" if self.passed else "failed"
        lines = [
            "## Validation Report",
            "",
            f"- Status: **{status}**",
            f"- Rows checked: {self.row_count}",
            f"- Issues found: {self.issue_count}",
            f"- Bad rows: {len(self.bad_rows)}",
        ]

        if self.passed:
            return "\n".join(lines)

        visible_issues = self.issues if max_issues is None else self.issues[:max_issues]
        if not visible_issues:
            lines.extend(["", "_Issue table omitted by `max_issues=0`._"])
            return "\n".join(lines)

        lines.extend(
            [
                "",
                "| Column | Rule | Row | Value | Message |",
                "| --- | --- | ---: | --- | --- |",
            ]
        )
        for issue in visible_issues:
            lines.append(
                "| "
                f"{_markdown_cell(issue.column)} | "
                f"{_markdown_cell(issue.rule)} | "
                f"{_markdown_cell(issue.row_index)} | "
                f"{_markdown_cell(_clean_scalar(issue.value))} | "
                f"{_markdown_cell(issue.message)} |"
            )

        hidden_count = self.issue_count - len(visible_issues)
        if hidden_count > 0:
            lines.extend(
                ["", f"_Showing {len(visible_issues)} of {self.issue_count} issues._"]
            )

        return "\n".join(lines)


def validate(frame: ArFrame, schema: Schema | dict[str, Field]) -> ValidationResult:
    """Validate an ArFrame against a schema.

    Parameters
    ----------
    frame : ArFrame
        Input frame.
    schema : Schema or dict[str, Field]
        Validation contract.

    Returns
    -------
    ValidationResult
        Validation result containing all issues and bad row indexes.

    Examples
    --------
    >>> schema = ar.Schema({"email": ar.Email(nullable=False)})
    >>> result = ar.validate(frame, schema)
    >>> result.passed
    """
    schema = schema if isinstance(schema, Schema) else Schema(schema)
    df = to_pandas(frame)
    dtypes = frame.dtypes
    issues: list[ValidationIssue] = []

    for name, field_def in schema.fields.items():
        if name not in df.columns:
            issues.append(
                ValidationIssue(
                    column=name,
                    rule="required_column",
                    message=f"Missing required column: {name}",
                )
            )
            continue
        issues.extend(_validate_column(df[name], dtypes.get(name), name, field_def))

    if schema.strict:
        expected = set(schema.fields)
        for name in df.columns:
            if name not in expected:
                issues.append(
                    ValidationIssue(
                        column=str(name),
                        rule="unexpected_column",
                        message=f"Unexpected column: {name}",
                    )
                )

    bad_rows = sorted(
        {issue.row_index for issue in issues if issue.row_index is not None}
    )
    return ValidationResult(
        row_count=len(df),
        issue_count=len(issues),
        issues=issues,
        bad_rows=bad_rows,
    )


def Int64(
    *,
    nullable: bool = True,
    min: int | None = None,
    max: int | None = None,
    unique: bool = False,
) -> Field:
    """Create an int64 schema field."""

    if min is not None and max is not None and min > max:
        raise ValueError("min must be less than or equal to max")

    return Field(
        dtype="int64",
        nullable=nullable,
        min=min,
        max=max,
        unique=unique,
    )


def Float64(
    *,
    nullable: bool = True,
    min: float | None = None,
    max: float | None = None,
    unique: bool = False,
) -> Field:
    """Create a float64 schema field."""

    if min is not None and max is not None and min > max:
        raise ValueError("min must be less than or equal to max")

    return Field(
        dtype="float64",
        nullable=nullable,
        min=min,
        max=max,
        unique=unique,
    )


def String(
    *,
    nullable: bool = True,
    pattern: str | None = None,
    allowed: set[Any] | list[Any] | tuple[Any, ...] | None = None,
    unique: bool = False,
    min_length: int | None = None,
    max_length: int | None = None,
) -> Field:
    """Create a string schema field."""

    if min_length is not None and max_length is not None and min_length > max_length:
        raise ValueError("min_length must be less than or equal to max_length")

    allowed_set = set(allowed) if allowed is not None else None

    return Field(
        dtype="string",
        nullable=nullable,
        pattern=pattern,
        allowed=allowed_set,
        unique=unique,
        min_length=min_length,
        max_length=max_length,
    )


def Bool(*, nullable: bool = True) -> Field:
    """Create a bool schema field."""
    return Field(dtype="bool", nullable=nullable)


def Email(*, nullable: bool = True, unique: bool = False) -> Field:
    """Create an email-address schema field."""
    return Field(
        dtype="string",
        nullable=nullable,
        semantic="email",
        unique=unique,
    )


def URL(*, nullable: bool = True, unique: bool = False) -> Field:
    """Create a URL schema field."""
    return Field(dtype="string", nullable=nullable, semantic="url", unique=unique)


def Date(*, nullable: bool = True, unique: bool = False) -> Field:
    """Create a date schema field."""
    return Field(
        dtype="string",
        nullable=nullable,
        semantic="date",
        unique=unique,
    )


def _validate_column(
    series: pd.Series,
    actual_dtype: str | None,
    name: str,
    field_def: Field,
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []

    if field_def.dtype is not None and actual_dtype != field_def.dtype:
        issues.append(
            ValidationIssue(
                column=name,
                rule="dtype",
                message=(
                    f"Column {name!r} has dtype {actual_dtype!r}; "
                    f"expected {field_def.dtype!r}"
                ),
            )
        )

    if not field_def.nullable:
        issues.extend(
            _row_issues(
                series[series.isna()],
                column=name,
                rule="nullable",
                message=f"Column {name!r} contains null values",
            )
        )

    non_null = series.dropna()

    if field_def.unique:
        duplicate_mask = non_null.duplicated(keep=False)
        issues.extend(
            _row_issues(
                non_null[duplicate_mask],
                column=name,
                rule="unique",
                message=f"Column {name!r} contains duplicate values",
            )
        )

    if field_def.allowed is not None:
        invalid = non_null[~non_null.isin(field_def.allowed)]
        issues.extend(
            _row_issues(
                invalid,
                column=name,
                rule="allowed",
                message=f"Column {name!r} contains values outside the allowed set",
            )
        )

    if field_def.min is not None or field_def.max is not None:
        numeric = pd.to_numeric(non_null, errors="coerce")
        invalid_numeric = non_null[numeric.isna()]
        issues.extend(
            _row_issues(
                invalid_numeric,
                column=name,
                rule="numeric",
                message=f"Column {name!r} contains non-numeric values",
            )
        )
        if field_def.min is not None:
            issues.extend(
                _row_issues(
                    non_null[numeric < field_def.min],
                    column=name,
                    rule="min",
                    message=f"Column {name!r} has values below {field_def.min}",
                )
            )
        if field_def.max is not None:
            issues.extend(
                _row_issues(
                    non_null[numeric > field_def.max],
                    column=name,
                    rule="max",
                    message=f"Column {name!r} has values above {field_def.max}",
                )
            )

    text = non_null.astype("string")

    if field_def.pattern is not None:
        invalid = non_null[~text.str.fullmatch(field_def.pattern, na=False)]
        issues.extend(
            _row_issues(
                invalid,
                column=name,
                rule="pattern",
                message=f"Column {name!r} has values that do not match the pattern",
            )
        )

    if field_def.semantic is not None:
        pattern = _SEMANTIC_PATTERNS.get(field_def.semantic)
        if pattern is None:
            issues.append(
                ValidationIssue(
                    column=name,
                    rule="semantic",
                    message=f"Unknown semantic type: {field_def.semantic}",
                )
            )
        else:
            if field_def.semantic == "date":
                invalid_values = []

                for index, value in non_null.items():
                    value_str = str(value)

                    if DATE_PATTERN.fullmatch(value_str) is None:
                        invalid_values.append((index, value))
                        continue

                    try:
                        datetime.strptime(value_str, "%Y-%m-%d")
                    except ValueError:
                        invalid_values.append((index, value))

                invalid = pd.Series({index: value for index, value in invalid_values})
            else:
                invalid = non_null[~text.str.fullmatch(pattern, na=False)]

            issues.extend(
                _row_issues(
                    invalid,
                    column=name,
                    rule=field_def.semantic,
                    message=f"Column {name!r} contains invalid {field_def.semantic} values",
                )
            )

    if field_def.min_length is not None:
        invalid = non_null[text.str.len() < field_def.min_length]
        issues.extend(
            _row_issues(
                invalid,
                column=name,
                rule="min_length",
                message=f"Column {name!r} has values shorter than {field_def.min_length}",
            )
        )

    if field_def.max_length is not None:
        invalid = non_null[text.str.len() > field_def.max_length]
        issues.extend(
            _row_issues(
                invalid,
                column=name,
                rule="max_length",
                message=f"Column {name!r} has values longer than {field_def.max_length}",
            )
        )

    return issues


def _row_issues(
    invalid: pd.Series,
    *,
    column: str,
    rule: str,
    message: str,
) -> list[ValidationIssue]:
    return [
        ValidationIssue(
            column=column,
            rule=rule,
            message=message,
            row_index=int(index),
            value=value,
        )
        for index, value in invalid.items()
    ]


def _clean_scalar(value: Any) -> Any:
    if pd.isna(value):
        return None
    if hasattr(value, "item"):
        return value.item()
    return value


def _markdown_cell(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).replace("\n", "<br>").replace("|", "\\|")
    return text


DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_SEMANTIC_PATTERNS = {
    "email": r"[^@\s]+@[^@\s]+\.[^@\s]+",
    "url": r"https?://[^\s]+",
    "phone": r"\+?[0-9][0-9 .()\-]{6,}[0-9]",
    "date": r"\d{4}-\d{2}-\d{2}",
}
