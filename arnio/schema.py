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
from .exceptions import ArnioError
from .frame import ArFrame

ISSUE_COLUMNS = [
    "column",
    "rule",
    "message",
    "row_index",
    "value",
]

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
    format: str | None = None
    _datetime_min: pd.Timestamp | None = None
    _datetime_max: pd.Timestamp | None = None


@dataclass(frozen=True)
class Schema:
    """Named column validation contract."""

    fields: dict[str, Field]
    strict: bool = False
    unique: list[str] | tuple[str, ...] | None = None

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
        if not self.issues:
            return pd.DataFrame(columns=ISSUE_COLUMNS)

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

    def raise_for_errors(self) -> None:
        """Raise an ArnioError when validation failed.

        Returns None when validation passed.
        The raised exception message summarizes all validation issues.
        """
        if self.passed:
            return None

        parts: list[str] = []
        parts.append(
            f"Schema validation failed: {self.issue_count} issue(s) across {len(self.bad_rows)} bad row(s)"
        )
        for issue in self.issues:
            col = issue.column if issue.column is not None else ""
            row = "" if issue.row_index is None else f"row {issue.row_index}"
            parts.append(f"- {col} | {issue.rule} | {row} | {issue.message}")

        raise ArnioError("\n".join(parts))


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

    if schema.unique is not None:
        if isinstance(schema.unique, (list, tuple)) and len(schema.unique) == 0:
            issues.append(
                ValidationIssue(
                    column=None,
                    rule="composite_unique",
                    message="Composite unique columns cannot be empty",
                )
            )
        elif isinstance(schema.unique, (list, tuple)):
            missing_cols = [c for c in schema.unique if c not in df.columns]
            if missing_cols:
                for col in missing_cols:
                    issues.append(
                        ValidationIssue(
                            column=col,
                            rule="missing_column",
                            message=f"Column {col!r} not found",
                        )
                    )
            else:
                duplicate_mask = df.duplicated(subset=list(schema.unique), keep=False)
                if duplicate_mask.any():
                    for index in df[duplicate_mask].index:
                        issues.append(
                            ValidationIssue(
                                column=None,
                                rule="composite_unique",
                                message=(
                                    "Duplicate rows found for columns"
                                    f" {list(schema.unique)}"
                                ),
                                row_index=int(index),
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


def Email(
    *,
    nullable: bool = True,
    unique: bool = False,
    validation: str = "light",
) -> Field:
    """Create an email-address schema field."""
    if validation not in {"light", "strict"}:
        raise ValueError("Email validation must be 'light' or 'strict'")
    return Field(
        dtype="string",
        nullable=nullable,
        semantic="email" if validation == "light" else "email:strict",
        unique=unique,
    )


def URL(*, nullable: bool = True, unique: bool = False) -> Field:
    """Create a URL schema field."""
    return Field(dtype="string", nullable=nullable, semantic="url", unique=unique)


def CountryCode(*, nullable: bool = True, unique: bool = False) -> Field:
    """Create an uppercase ISO alpha-2 country-code schema field."""
    return Field(
        dtype="string",
        nullable=nullable,
        semantic="country_code",
        unique=unique,
    )


def Date(*, nullable: bool = True, unique: bool = False) -> Field:
    """Create a date schema field."""
    return Field(
        dtype="string",
        nullable=nullable,
        semantic="date",
        unique=unique,
    )


def Regex(
    pattern: str,
    *,
    nullable: bool = True,
    unique: bool = False,
) -> Field:
    """Create a regex-validated string schema field.

    The pattern is compiled at call time so invalid expressions raise
    ``re.error`` immediately rather than at validation time.

    Parameters
    ----------
    pattern : str
        Regular expression that every non-null value must fully match.
    nullable : bool, default True
        Whether null values are allowed.
    unique : bool, default False
        Whether all non-null values must be unique.

    Examples
    --------
    >>> schema = ar.Schema({
    ...     "user_id": ar.Regex(r"^USR-\\d{4}$", nullable=False),
    ...     "zip_code": ar.Regex(r"^\\d{5}(-\\d{4})?$", nullable=True),
    ... })
    """
    import re

    re.compile(pattern)  # fail fast on invalid pattern
    return Field(
        dtype="string",
        nullable=nullable,
        pattern=pattern,
        unique=unique,
    )


def DateTime(
    *,
    nullable: bool = True,
    min: Any = None,
    max: Any = None,
    unique: bool = False,
    format: str | None = None,
) -> Field:
    """Create a datetime schema field for validating string timestamps."""
    if format is not None and not isinstance(format, str):
        raise TypeError("DateTime format must be a string or None")

    min_val = _parse_datetime_bound(min, "min")
    max_val = _parse_datetime_bound(max, "max")
    if min_val is not None and max_val is not None and min_val > max_val:
        raise ValueError("DateTime min must be less than or equal to max")

    return Field(
        dtype="datetime",
        nullable=nullable,
        unique=unique,
        format=format,
        _datetime_min=min_val,
        _datetime_max=max_val,
    )


def _validate_column(
    series: pd.Series,
    actual_dtype: str | None,
    name: str,
    field_def: Field,
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []

    if field_def.dtype is not None and actual_dtype != field_def.dtype:
        if not (field_def.dtype == "datetime" and actual_dtype == "string"):
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

    if field_def.dtype == "datetime":
        issues.extend(_validate_datetime(non_null, name, field_def))

    elif field_def.min is not None or field_def.max is not None:
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
                # For most semantics we can use a regex fullmatch. For
                # country codes we additionally check that the code is an
                # assigned ISO 3166-1 alpha-2 value.
                invalid = non_null[~text.str.fullmatch(pattern, na=False)]

                if field_def.semantic == "country_code":
                    # Rows that matched the basic pattern but are not in the
                    # ISO list should also be reported.
                    matched_mask = text.str.fullmatch(pattern, na=False)
                    matched = non_null[matched_mask]
                    invalid_unassigned = matched[~matched.isin(_ISO_ALPHA2)]
                    if not invalid_unassigned.empty:
                        invalid = pd.concat([invalid, invalid_unassigned])

            if not invalid.empty:
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


def _validate_datetime(
    non_null: pd.Series,
    name: str,
    field_def: Field,
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    parsed = pd.to_datetime(non_null, format=field_def.format, errors="coerce")

    invalid_format = non_null[parsed.isna()]
    issues.extend(
        _row_issues(
            invalid_format,
            column=name,
            rule="format",
            message=f"Column {name!r} does not match the required datetime format",
        )
    )

    valid_mask = parsed.notna()
    valid_non_null = non_null[valid_mask]
    valid_parsed = parsed[valid_mask]

    if field_def._datetime_min is not None:
        issues.extend(
            _row_issues(
                valid_non_null[valid_parsed < field_def._datetime_min],
                column=name,
                rule="min",
                message=f"Column {name!r} has values below {field_def._datetime_min}",
            )
        )
    if field_def._datetime_max is not None:
        issues.extend(
            _row_issues(
                valid_non_null[valid_parsed > field_def._datetime_max],
                column=name,
                rule="max",
                message=f"Column {name!r} has values above {field_def._datetime_max}",
            )
        )

    return issues


def _parse_datetime_bound(value: Any, name: str) -> pd.Timestamp | None:
    if value is None:
        return None
    try:
        parsed = pd.to_datetime(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"DateTime {name} must be a parseable datetime scalar"
        ) from exc

    if not isinstance(parsed, pd.Timestamp) or pd.isna(parsed):
        raise ValueError(f"DateTime {name} must be a parseable datetime scalar")
    return parsed


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
            row_index=int(index) + 1,
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


_SEMANTIC_PATTERNS = {
    "email": r"[^@\s]+@[^@\s]+\.[^@\s]+",
    "email:strict": (
        r"[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+"
        r"@"
        r"[a-zA-Z0-9-]+"
        r"(?:\.[a-zA-Z0-9-]+)+"
    ),
    "url": r"https?://[^\s]+",
    "phone": r"\+?[0-9][0-9 .()\-]{6,}[0-9]",
    "country_code": r"[A-Z]{2}",
    "date": r"\d{4}-\d{2}-\d{2}",
}

# ISO 3166-1 alpha-2 country codes. If `pycountry` is available we'll
# build this set from it at import time; otherwise fall back to this static
# list to allow deterministic validation in environments without the
# external dependency.
try:
    import pycountry  # type: ignore

    _ISO_ALPHA2 = {c.alpha_2 for c in pycountry.countries}
except Exception:
    _ISO_ALPHA2 = {
        "AF","AX","AL","DZ","AS","AD","AO","AI","AQ","AG",
        "AR","AM","AW","AU","AT","AZ","BS","BH","BD","BB",
        "BY","BE","BZ","BJ","BM","BT","BO","BQ","BA","BW",
        "BV","BR","IO","BN","BG","BF","BI","CV","KH","CM",
        "CA","KY","CF","TD","CL","CN","CX","CC","CO","KM",
        "CG","CD","CK","CR","CI","HR","CU","CW","CY","CZ",
        "DK","DJ","DM","DO","EC","EG","SV","GQ","ER","EE",
        "ET","FK","FO","FJ","FI","FR","GF","PF","TF","GA",
        "GM","GE","DE","GH","GI","GR","GL","GD","GP","GU",
        "GT","GG","GN","GW","GY","HT","HM","VA","HN","HK",
        "HU","IS","IN","ID","IR","IQ","IE","IM","IL","IT",
        "JM","JP","JE","JO","KZ","KE","KI","KP","KR","KW",
        "KG","LA","LV","LB","LS","LR","LY","LI","LT","LU",
        "MO","MK","MG","MW","MY","MV","ML","MT","MH","MQ",
        "MR","MU","YT","MX","FM","MD","MC","MN","ME","MS",
        "MA","MZ","MM","NA","NR","NP","NL","NC","NZ","NI",
        "NE","NG","NU","NF","MP","NO","OM","PK","PW","PS",
        "PA","PG","PY","PE","PH","PN","PL","PT","PR","QA",
        "RE","RO","RU","RW","BL","SH","KN","LC","MF","PM",
        "VC","WS","SM","ST","SA","SN","RS","SC","SL","SG",
        "SX","SK","SI","SB","SO","ZA","GS","SS","ES","LK",
        "SD","SR","SJ","SE","CH","SY","TW","TJ","TZ","TH",
        "TL","TG","TK","TO","TT","TN","TR","TM","TC","TV",
        "UG","UA","AE","GB","US","UM","UY","UZ","VU","VE",
        "VN","VG","VI","WF","EH","YE","ZM","ZW",
    }
