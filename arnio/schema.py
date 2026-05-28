"""
arnio.schema
Production data contracts and validation.
"""

from __future__ import annotations

import json
import re
import warnings
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable
from zoneinfo import available_timezones

import numpy as np
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
    "severity",
]

DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")
URL_SCHEME_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*$")

_VALID_SEVERITIES = {"error", "warning"}


def _validate_severity(severity: str) -> None:
    """Raise ValueError if severity is not 'error' or 'warning'."""
    if severity not in _VALID_SEVERITIES:
        raise ValueError("severity must be 'error' or 'warning'")


_DTYPE_MAP = {
    "int": "int64",
    "int64": "int64",
    "int32": "int64",
    "float": "float64",
    "float64": "float64",
    "float32": "float64",
    "bool": "bool",
    "object": "string",
    "string": "string",
    "str": "string",
    "null": "null",
}


ISO_3166_1_ALPHA_2 = {
    "AD",
    "AE",
    "AF",
    "AG",
    "AI",
    "AL",
    "AM",
    "AO",
    "AQ",
    "AR",
    "AS",
    "AT",
    "AU",
    "AW",
    "AX",
    "AZ",
    "BA",
    "BB",
    "BD",
    "BE",
    "BF",
    "BG",
    "BH",
    "BI",
    "BJ",
    "BL",
    "BM",
    "BN",
    "BO",
    "BQ",
    "BR",
    "BS",
    "BT",
    "BV",
    "BW",
    "BY",
    "BZ",
    "CA",
    "CC",
    "CD",
    "CF",
    "CG",
    "CH",
    "CI",
    "CK",
    "CL",
    "CM",
    "CN",
    "CO",
    "CR",
    "CU",
    "CV",
    "CW",
    "CX",
    "CY",
    "CZ",
    "DE",
    "DJ",
    "DK",
    "DM",
    "DO",
    "DZ",
    "EC",
    "EE",
    "EG",
    "EH",
    "ER",
    "ES",
    "ET",
    "FI",
    "FJ",
    "FK",
    "FM",
    "FO",
    "FR",
    "GA",
    "GB",
    "GD",
    "GE",
    "GF",
    "GG",
    "GH",
    "GI",
    "GL",
    "GM",
    "GN",
    "GP",
    "GQ",
    "GR",
    "GS",
    "GT",
    "GU",
    "GW",
    "GY",
    "HK",
    "HM",
    "HN",
    "HR",
    "HT",
    "HU",
    "ID",
    "IE",
    "IL",
    "IM",
    "IN",
    "IO",
    "IQ",
    "IR",
    "IS",
    "IT",
    "JE",
    "JM",
    "JO",
    "JP",
    "KE",
    "KG",
    "KH",
    "KI",
    "KM",
    "KN",
    "KP",
    "KR",
    "KW",
    "KY",
    "KZ",
    "LA",
    "LB",
    "LC",
    "LI",
    "LK",
    "LR",
    "LS",
    "LT",
    "LU",
    "LV",
    "LY",
    "MA",
    "MC",
    "MD",
    "ME",
    "MF",
    "MG",
    "MH",
    "MK",
    "ML",
    "MM",
    "MN",
    "MO",
    "MP",
    "MQ",
    "MR",
    "MS",
    "MT",
    "MU",
    "MV",
    "MW",
    "MX",
    "MY",
    "MZ",
    "NA",
    "NC",
    "NE",
    "NF",
    "NG",
    "NI",
    "NL",
    "NO",
    "NP",
    "NR",
    "NU",
    "NZ",
    "OM",
    "PA",
    "PE",
    "PF",
    "PG",
    "PH",
    "PK",
    "PL",
    "PM",
    "PN",
    "PR",
    "PS",
    "PT",
    "PW",
    "PY",
    "QA",
    "RE",
    "RO",
    "RS",
    "RU",
    "RW",
    "SA",
    "SB",
    "SC",
    "SD",
    "SE",
    "SG",
    "SH",
    "SI",
    "SJ",
    "SK",
    "SL",
    "SM",
    "SN",
    "SO",
    "SR",
    "SS",
    "ST",
    "SV",
    "SX",
    "SY",
    "SZ",
    "TC",
    "TD",
    "TF",
    "TG",
    "TH",
    "TJ",
    "TK",
    "TL",
    "TM",
    "TN",
    "TO",
    "TR",
    "TT",
    "TV",
    "TW",
    "TZ",
    "UA",
    "UG",
    "UM",
    "US",
    "UY",
    "UZ",
    "VA",
    "VC",
    "VE",
    "VG",
    "VI",
    "VN",
    "VU",
    "WF",
    "WS",
    "YE",
    "YT",
    "ZA",
    "ZM",
    "ZW",
}

ISO_639_1_CODES = {
    "aa",
    "ab",
    "ae",
    "af",
    "ak",
    "am",
    "an",
    "ar",
    "as",
    "av",
    "ay",
    "az",
    "ba",
    "be",
    "bg",
    "bh",
    "bi",
    "bm",
    "bn",
    "bo",
    "br",
    "bs",
    "ca",
    "ce",
    "ch",
    "co",
    "cr",
    "cs",
    "cu",
    "cv",
    "cy",
    "da",
    "de",
    "dv",
    "dz",
    "ee",
    "el",
    "en",
    "eo",
    "es",
    "et",
    "eu",
    "fa",
    "ff",
    "fi",
    "fj",
    "fo",
    "fr",
    "fy",
    "ga",
    "gd",
    "gl",
    "gn",
    "gu",
    "gv",
    "ha",
    "he",
    "hi",
    "ho",
    "hr",
    "ht",
    "hu",
    "hy",
    "hz",
    "ia",
    "id",
    "ie",
    "ig",
    "ii",
    "ik",
    "io",
    "is",
    "it",
    "iu",
    "ja",
    "jv",
    "ka",
    "kg",
    "ki",
    "kj",
    "kk",
    "kl",
    "km",
    "kn",
    "ko",
    "kr",
    "ks",
    "ku",
    "kv",
    "kw",
    "ky",
    "la",
    "lb",
    "lg",
    "li",
    "ln",
    "lo",
    "lt",
    "lu",
    "lv",
    "mg",
    "mh",
    "mi",
    "mk",
    "ml",
    "mn",
    "mr",
    "ms",
    "mt",
    "my",
    "na",
    "nb",
    "nd",
    "ne",
    "ng",
    "nl",
    "nn",
    "no",
    "nr",
    "nv",
    "ny",
    "oc",
    "oj",
    "om",
    "or",
    "os",
    "pa",
    "pi",
    "pl",
    "ps",
    "pt",
    "qu",
    "rm",
    "rn",
    "ro",
    "ru",
    "rw",
    "sa",
    "sc",
    "sd",
    "se",
    "sg",
    "si",
    "sk",
    "sl",
    "sm",
    "sn",
    "so",
    "sq",
    "sr",
    "ss",
    "st",
    "su",
    "sv",
    "sw",
    "ta",
    "te",
    "tg",
    "th",
    "ti",
    "tk",
    "tl",
    "tn",
    "to",
    "tr",
    "ts",
    "tt",
    "tw",
    "ty",
    "ug",
    "uk",
    "ur",
    "uz",
    "ve",
    "vi",
    "vo",
    "wa",
    "wo",
    "xh",
    "yi",
    "yo",
    "za",
    "zh",
    "zu",
}

ISO_4217_CURRENCY_CODES = {
    "AED",
    "AFN",
    "ALL",
    "AMD",
    "ANG",
    "AOA",
    "ARS",
    "AUD",
    "AWG",
    "AZN",
    "BAM",
    "BBD",
    "BDT",
    "BGN",
    "BHD",
    "BIF",
    "BMD",
    "BND",
    "BOB",
    "BOV",
    "BRL",
    "BSD",
    "BTN",
    "BWP",
    "BYN",
    "BZD",
    "CAD",
    "CDF",
    "CHE",
    "CHF",
    "CHW",
    "CLF",
    "CLP",
    "CNY",
    "COP",
    "COU",
    "CRC",
    "CUP",
    "CVE",
    "CZK",
    "DJF",
    "DKK",
    "DOP",
    "DZD",
    "EGP",
    "ERN",
    "ETB",
    "EUR",
    "FJD",
    "FKP",
    "GBP",
    "GEL",
    "GHS",
    "GIP",
    "GMD",
    "GNF",
    "GTQ",
    "GYD",
    "HKD",
    "HNL",
    "HRK",
    "HTG",
    "HUF",
    "IDR",
    "ILS",
    "INR",
    "IQD",
    "IRR",
    "ISK",
    "JMD",
    "JOD",
    "JPY",
    "KES",
    "KGS",
    "KHR",
    "KMF",
    "KPW",
    "KRW",
    "KWD",
    "KYD",
    "KZT",
    "LAK",
    "LBP",
    "LKR",
    "LRD",
    "LSL",
    "LYD",
    "MAD",
    "MDL",
    "MGA",
    "MKD",
    "MMK",
    "MNT",
    "MOP",
    "MRU",
    "MUR",
    "MVR",
    "MWK",
    "MXN",
    "MXV",
    "MYR",
    "MZN",
    "NAD",
    "NGN",
    "NIO",
    "NOK",
    "NPR",
    "NZD",
    "OMR",
    "PAB",
    "PEN",
    "PGK",
    "PHP",
    "PKR",
    "PLN",
    "PYG",
    "QAR",
    "RON",
    "RSD",
    "RUB",
    "RWF",
    "SAR",
    "SBD",
    "SCR",
    "SDG",
    "SEK",
    "SGD",
    "SHP",
    "SLE",
    "SLL",
    "SOS",
    "SRD",
    "SSP",
    "STN",
    "SVC",
    "SYP",
    "SZL",
    "THB",
    "TJS",
    "TMT",
    "TND",
    "TOP",
    "TRY",
    "TTD",
    "TWD",
    "TZS",
    "UAH",
    "UGX",
    "USD",
    "USN",
    "UYI",
    "UYU",
    "UYW",
    "UZS",
    "VES",
    "VND",
    "VUV",
    "WST",
    "XAF",
    "XAG",
    "XBA",
    "XBB",
    "XBC",
    "XBD",
    "XCD",
    "XDR",
    "XOF",
    "XPD",
    "XPF",
    "XPT",
    "XSU",
    "XTS",
    "XUA",
    "XXX",
    "YER",
    "ZAR",
    "ZMW",
    "ZWL",
}

IANA_TIMEZONES = available_timezones()


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
    required_if: tuple[str, Any] | None = None
    severity: str = "error"

    def __post_init__(self) -> None:
        if not isinstance(self.nullable, bool):
            raise TypeError("nullable must be a bool")
        if not isinstance(self.unique, bool):
            raise TypeError("unique must be a bool")

        if self.required_if is not None:
            if not isinstance(self.required_if, tuple):
                raise TypeError("required_if must be a tuple or None")
            if len(self.required_if) != 2:
                raise TypeError(
                    "required_if must be a (column_name, expected_value) tuple"
                )
            if not isinstance(self.required_if[0], str):
                raise TypeError("required_if column name must be a string")
        if self.dtype in {"int64", "float64"}:
            if self.min is not None:
                if isinstance(self.min, bool) or not isinstance(self.min, (int, float)):
                    raise TypeError("min must be numeric or None")
            if self.max is not None:
                if isinstance(self.max, bool) or not isinstance(self.max, (int, float)):
                    raise TypeError("max must be numeric or None")

        _validate_severity(self.severity)


@dataclass(frozen=True)
class Schema:
    """Named column validation contract."""

    fields: dict[str, Field]
    strict: bool = False
    unique: list[str] | tuple[str, ...] | None = None
    rules: list[Callable[[pd.DataFrame], list[ValidationIssue]]] | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.fields, dict):
            raise TypeError(
                f"Schema 'fields' must be a mapping (like a dict), got {type(self.fields).__name__}"
            )

        for key in self.fields:
            if not isinstance(key, str):
                raise TypeError(
                    f"Schema field names must be strings, got {type(key).__name__!r}: {key!r}"
                )

        for name, field_def in self.fields.items():
            if not isinstance(field_def, Field):
                raise TypeError(
                    f"Schema value for column {name!r} must be a Field instance such as ar.Int64(), got {type(field_def).__name__}"
                )

        if self.unique is not None:
            if isinstance(self.unique, str):
                raise TypeError(
                    "Schema 'unique' must be a list or tuple of strings (e.g., ['column_name']), "
                    f"not a bare string: {self.unique!r}."
                )
            if not isinstance(self.unique, (list, tuple)):
                raise TypeError(
                    "Schema 'unique' must be a list or tuple of strings (e.g., ['column_name']), "
                    f"got {type(self.unique).__name__}."
                )
            for item in self.unique:
                if not isinstance(item, str):
                    raise TypeError(
                        f"Schema 'unique' members must be strings, got {type(item).__name__} for element {item!r}."
                    )
        if not isinstance(self.strict, bool):
            raise TypeError("Schema 'strict' must be a boolean")

        if self.rules is not None:
            if not isinstance(self.rules, (list, tuple)):
                raise TypeError("Schema 'rules' must be a list of callables")
            for rule in self.rules:
                if not callable(rule):
                    raise TypeError("Schema 'rules' must be a list of callables")

    def validate(
        self,
        frame: ArFrame,
        max_errors: int | None = None,
    ) -> ValidationResult:
        """
        Validate an ArFrame against this schema.

        Args:
            frame:
                frame to validate.
            max_errors:
                Maximum number of validation issues to return.
                Validation stops once this limit is reached.
        """
        return validate(frame, self, max_errors=max_errors)

    def to_json(self) -> str:
        """Serialize the schema to a stable JSON string.

        Cross-field ``rules`` cannot be serialized. When rules are present
        they are silently omitted and a ``UserWarning`` is emitted. The
        returned payload includes ``"rules_omitted": true`` so downstream
        consumers can detect the gap. Call ``from_json()`` to restore the
        field-only schema; rules must be re-attached manually afterward.
        """
        rules_omitted = bool(self.rules)
        if rules_omitted:
            warnings.warn(
                "Schema.to_json(): cross-field rules cannot be serialized "
                "and have been omitted. The JSON payload includes "
                '"rules_omitted": true. Restore rules manually after '
                "from_json().",
                UserWarning,
                stacklevel=2,
            )

        payload = {
            "fields": {
                name: _field_to_json_dict(field_def)
                for name, field_def in sorted(self.fields.items())
            },
            "strict": self.strict,
            "unique": list(self.unique) if self.unique is not None else None,
        }
        if rules_omitted:
            payload["rules_omitted"] = True
        return json.dumps(payload, sort_keys=True)

    @classmethod
    def from_json(cls, value: str) -> Schema:
        """Deserialize a schema from a JSON string produced by ``to_json()``."""
        try:
            payload = json.loads(value)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid schema JSON: {exc.msg}") from exc

        if not isinstance(payload, dict):
            raise TypeError(
                "Schema JSON must decode to an object with 'fields', 'strict', and optional 'unique'."
            )

        fields_payload = payload.get("fields")
        if not isinstance(fields_payload, dict):
            raise TypeError(
                "Schema JSON 'fields' must be an object mapping names to field definitions."
            )

        fields = {
            name: _field_from_json_dict(name, field_payload)
            for name, field_payload in fields_payload.items()
        }

        strict = payload.get("strict", False)
        if not isinstance(strict, bool):
            raise TypeError("Schema JSON 'strict' must be a boolean.")

        unique = payload.get("unique")
        if unique is not None and not isinstance(unique, list):
            raise TypeError("Schema JSON 'unique' must be a list of strings or null.")

        # rules_omitted marker is accepted and silently ignored — rules
        # cannot be round-tripped through JSON and must be re-attached
        # manually by the caller if needed.
        return cls(fields=fields, strict=strict, unique=unique)

    @classmethod
    def bootstrap_from_report(cls, report: Any) -> Schema:
        """Create a Schema from a DataQualityReport.

        Args:
            report: A DataQualityReport produced by arnio.profile().

        Returns:
            Schema: A new Schema inferred from the report's column profiles.

        Raises:
            TypeError: If the input is not a DataQualityReport.
            ValueError: If the report has no columns, or any column profile
                is missing a dtype.

        Example:
            >>> report = ar.profile(frame)
            >>> schema = ar.Schema.bootstrap_from_report(report)
            >>> result = schema.validate(frame)
        """
        from .quality import DataQualityReport

        if not isinstance(report, DataQualityReport):
            raise TypeError(f"Expected DataQualityReport, got {type(report).__name__}")
        if not report.columns:
            raise ValueError(
                "Cannot bootstrap schema from an empty report (no columns)."
            )

        fields = {}
        for col_name, profile in report.columns.items():
            dtype_val = getattr(profile, "dtype", None)
            null_count = getattr(profile, "null_count", 0)

            if not dtype_val:
                raise ValueError(
                    f"Column profile for {col_name!r} is missing 'dtype' key."
                )

            arnio_dtype = _DTYPE_MAP.get(str(dtype_val).lower(), "string")
            fields[col_name] = Field(dtype=arnio_dtype, nullable=null_count > 0)

        return cls(fields=fields)


@dataclass(frozen=True)
class ValidationIssue:
    """One validation failure."""

    column: str | None
    rule: str
    message: str
    row_index: int | None = None
    value: Any = None
    severity: str = "error"

    def __post_init__(self) -> None:
        _validate_severity(self.severity)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-friendly dictionary."""
        return {
            "column": self.column,
            "rule": self.rule,
            "message": self.message,
            "row_index": self.row_index,
            "value": _clean_scalar(self.value),
            "severity": self.severity,
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
        """Whether validation passed with zero error-level issues."""
        return not any(issue.severity == "error" for issue in self.issues)

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
        """Return a compact validation summary."""
        by_rule: dict[str, int] = {}
        by_column: dict[str, int] = {}
        by_column_and_rule: dict[str, dict[str, int]] = {}
        severity_counts: dict[str, int] = {}
        for issue in self.issues:
            by_rule[issue.rule] = by_rule.get(issue.rule, 0) + 1
            severity_counts[issue.severity] = severity_counts.get(issue.severity, 0) + 1
            if issue.column is not None:
                by_column[issue.column] = by_column.get(issue.column, 0) + 1
                column_rules = by_column_and_rule.setdefault(issue.column, {})
                column_rules[issue.rule] = column_rules.get(issue.rule, 0) + 1
        return {
            "passed": self.passed,
            "issue_count": self.issue_count,
            "bad_row_count": len(self.bad_rows),
            "issues_by_rule": by_rule,
            "severity_counts": severity_counts,
            "issues_by_column": by_column,
            "issues_by_column_and_rule": by_column_and_rule,
        }

    def to_pandas(self) -> pd.DataFrame:
        """Return issues as a pandas DataFrame."""
        if not self.issues:
            return pd.DataFrame(columns=ISSUE_COLUMNS)

        return pd.DataFrame([issue.to_dict() for issue in self.issues])

    def to_markdown(
        self,
        *,
        max_issues: int | None = None,
        redact_values: bool = False,
    ) -> str:
        """Return a GitHub-friendly Markdown validation report.

        Parameters
        ----------
        max_issues : int, optional
            Maximum number of issues to include in the table. When omitted, all
            issues are shown.
        redact_values : bool, default False
            When True, the *Value* column in the issue table is replaced with
            ``[REDACTED]`` so that invalid/sensitive data is not exposed in
            reports. Set to ``False`` (the default) to keep original behavior.
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

        if self.passed and self.issue_count == 0:
            return "\n".join(lines)

        visible_issues = self.issues if max_issues is None else self.issues[:max_issues]
        if not visible_issues:
            lines.extend(["", "_Issue table omitted by `max_issues=0`._"])
            return "\n".join(lines)

        lines.extend(
            [
                "",
                "| Column | Rule | Severity | Row | Value | Message |",
                "|---|---|---|---|---|---|",
            ]
        )
        for issue in visible_issues:
            value_cell = (
                "[REDACTED]"
                if redact_values
                else _markdown_cell(_clean_scalar(issue.value))
            )
            lines.append(
                "| "
                f"{_markdown_cell(issue.column)} | "
                f"{_markdown_cell(issue.rule)} | "
                f"{_markdown_cell(issue.severity)} | "
                f"{_markdown_cell(issue.row_index)} | "
                f"{value_cell} | "
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


@dataclass(frozen=True)
class SchemaDiffEntry:
    """One schema contract difference."""

    column: str | None
    change: str
    attribute: str | None = None
    expected: Any = None
    observed: Any = None

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-friendly dictionary."""
        return {
            "column": self.column,
            "change": self.change,
            "attribute": self.attribute,
            "expected": _clean_scalar(self.expected),
            "observed": _clean_scalar(self.observed),
        }


@dataclass(frozen=True)
class SchemaDiff:
    """Result of comparing two schema contracts."""

    differences: list[SchemaDiffEntry]

    @property
    def changed(self) -> bool:
        """Whether the two schemas differ."""
        return bool(self.differences)

    @property
    def difference_count(self) -> int:
        """Number of differences found."""
        return len(self.differences)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-friendly dictionary."""
        return {
            "changed": self.changed,
            "difference_count": self.difference_count,
            "differences": [diff.to_dict() for diff in self.differences],
        }

    def summary(self) -> dict[str, Any]:
        """Return compact counts by change kind."""
        by_change: dict[str, int] = {}
        by_column: dict[str, int] = {}
        for diff in self.differences:
            by_change[diff.change] = by_change.get(diff.change, 0) + 1
            if diff.column is not None:
                by_column[diff.column] = by_column.get(diff.column, 0) + 1
        return {
            "changed": self.changed,
            "difference_count": self.difference_count,
            "differences_by_change": by_change,
            "differences_by_column": by_column,
        }

    def to_markdown(self) -> str:
        """Return a GitHub-friendly Markdown schema diff report."""
        lines = [
            "## Schema Diff",
            "",
            f"- Status: **{'changed' if self.changed else 'unchanged'}**",
            f"- Differences found: {self.difference_count}",
        ]
        if not self.changed:
            return "\n".join(lines)

        lines.extend(
            [
                "",
                "| Column | Change | Attribute | Expected | Observed |",
                "| --- | --- | --- | --- | --- |",
            ]
        )
        for diff in self.differences:
            lines.append(
                "| "
                f"{_markdown_cell(diff.column)} | "
                f"{_markdown_cell(diff.change)} | "
                f"{_markdown_cell(diff.attribute)} | "
                f"{_markdown_cell(_clean_scalar(diff.expected))} | "
                f"{_markdown_cell(_clean_scalar(diff.observed))} |"
            )
        return "\n".join(lines)


def diff_schema(
    expected: Schema | dict[str, Field],
    observed: Schema | dict[str, Field],
) -> SchemaDiff:
    """Compare two schema contracts.

    Parameters
    ----------
    expected : Schema or dict[str, Field]
        Baseline or required contract.
    observed : Schema or dict[str, Field]
        Newly inferred, generated, or release candidate contract.

    Returns
    -------
    SchemaDiff
        Structured differences covering missing columns, extra columns,
        changed field attributes, and schema-level options.
    """
    expected_schema = expected if isinstance(expected, Schema) else Schema(expected)
    observed_schema = observed if isinstance(observed, Schema) else Schema(observed)
    differences: list[SchemaDiffEntry] = []

    expected_columns = set(expected_schema.fields)
    observed_columns = set(observed_schema.fields)

    for column in sorted(expected_columns - observed_columns):
        differences.append(
            SchemaDiffEntry(
                column=column,
                change="missing_column",
                expected=_field_to_dict(expected_schema.fields[column]),
            )
        )

    for column in sorted(observed_columns - expected_columns):
        differences.append(
            SchemaDiffEntry(
                column=column,
                change="extra_column",
                observed=_field_to_dict(observed_schema.fields[column]),
            )
        )

    for column in sorted(expected_columns & observed_columns):
        expected_field = _field_to_dict(expected_schema.fields[column])
        observed_field = _field_to_dict(observed_schema.fields[column])
        for attribute in sorted(set(expected_field) | set(observed_field)):
            expected_value = expected_field.get(attribute)
            observed_value = observed_field.get(attribute)
            if expected_value != observed_value:
                differences.append(
                    SchemaDiffEntry(
                        column=column,
                        change="changed_field",
                        attribute=attribute,
                        expected=expected_value,
                        observed=observed_value,
                    )
                )

    if expected_schema.strict != observed_schema.strict:
        differences.append(
            SchemaDiffEntry(
                column=None,
                change="changed_schema",
                attribute="strict",
                expected=expected_schema.strict,
                observed=observed_schema.strict,
            )
        )

    if _normalize_unique(expected_schema.unique) != _normalize_unique(
        observed_schema.unique
    ):
        differences.append(
            SchemaDiffEntry(
                column=None,
                change="changed_schema",
                attribute="unique",
                expected=_normalize_unique(expected_schema.unique),
                observed=_normalize_unique(observed_schema.unique),
            )
        )

    return SchemaDiff(differences)


def validate(
    frame: ArFrame,
    schema: Schema | dict[str, Field],
    max_errors: int | None = None,
) -> ValidationResult:
    """Validate an ArFrame against a schema.

    Parameters
    ----------
    frame : ArFrame
        Input frame. Must be a single in-memory ArFrame. Chunked validation
        is not currently supported by this function.
    schema : Schema or dict[str, Field]
        Validation schema.

    max_errors : int | None
        Maximum number of validation issues to return.
        Validation stops once this limit is reached.

    Returns
    -------
    ValidationResult
        Validation result containing all issues and bad row indexes.

    Raises
    ------
    TypeError
        If schema.unique is provided but is not a list or tuple of strings.

    Examples
    --------
    >>> schema = ar.Schema({"email": ar.Email(nullable=False)})
    >>> result = ar.validate(frame, schema)
    >>> result.passed
    """
    if not isinstance(frame, ArFrame):
        raise TypeError(
            "validate() expects a single ArFrame. Chunked validation is not "
            "currently supported; validate each chunk explicitly or materialize "
            "the data before validation."
        )

    schema = schema if isinstance(schema, Schema) else Schema(schema)
    if max_errors is not None:
        if isinstance(max_errors, bool) or not isinstance(max_errors, int):
            raise TypeError("max_errors must be an int or None")

    if max_errors is not None and max_errors < 0:
        raise ValueError("max_errors must be >= 0")

    df = to_pandas(frame)
    dtypes = frame.dtypes
    issues: list[ValidationIssue] = []

    if max_errors == 0:
        return ValidationResult(
            row_count=len(df),
            issue_count=0,
            issues=[],
            bad_rows=sorted(
                {issue.row_index for issue in issues if issue.row_index is not None}
            ),
        )

    def reached_limit() -> bool:
        return max_errors is not None and len(issues) >= max_errors

    for name, field_def in schema.fields.items():
        if name not in df.columns:
            issues.append(
                ValidationIssue(
                    column=name,
                    rule="required_column",
                    message=f"Missing required column: {name}",
                    severity=field_def.severity,
                )
            )

            if reached_limit():
                issues = issues[:max_errors]

                return ValidationResult(
                    row_count=len(df),
                    issue_count=len(issues),
                    issues=issues,
                    bad_rows=sorted(
                        {
                            issue.row_index
                            for issue in issues
                            if issue.row_index is not None
                        }
                    ),
                )

            continue
        column_issues = _validate_column(
            df,
            df[name],
            dtypes.get(name),
            name,
            field_def,
        )

        remaining = None if max_errors is None else max_errors - len(issues)
        if remaining is not None:
            column_issues = column_issues[:remaining]

        issues.extend(column_issues)

        if reached_limit():
            issues = issues[:max_errors]

            return ValidationResult(
                row_count=len(df),
                issue_count=len(issues),
                issues=issues,
                bad_rows=sorted(
                    {issue.row_index for issue in issues if issue.row_index is not None}
                ),
            )

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

                if reached_limit():
                    issues = issues[:max_errors]

                    return ValidationResult(
                        row_count=len(df),
                        issue_count=len(issues),
                        issues=issues,
                        bad_rows=sorted(
                            {
                                issue.row_index
                                for issue in issues
                                if issue.row_index is not None
                            }
                        ),
                    )

    if schema.unique is not None:
        if not isinstance(schema.unique, (list, tuple)):
            raise TypeError(
                "Schema 'unique' must be a list or tuple of strings (e.g., ['column_name']), "
                f"got {type(schema.unique).__name__}."
            )

        for item in schema.unique:
            if not isinstance(item, str):
                raise TypeError(
                    f"Schema 'unique' members must be strings, got {type(item).__name__} for element {item!r}."
                )

        if len(schema.unique) == 0:
            issues.append(
                ValidationIssue(
                    column=None,
                    rule="composite_unique",
                    message="Composite unique columns cannot be empty",
                )
            )
            if reached_limit():
                issues = issues[:max_errors]

                return ValidationResult(
                    row_count=len(df),
                    issue_count=len(issues),
                    issues=issues,
                    bad_rows=sorted(
                        {
                            issue.row_index
                            for issue in issues
                            if issue.row_index is not None
                        }
                    ),
                )

        else:
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

                    if reached_limit():
                        issues = issues[:max_errors]

                        return ValidationResult(
                            row_count=len(df),
                            issue_count=len(issues),
                            issues=issues,
                            bad_rows=sorted(
                                {
                                    issue.row_index
                                    for issue in issues
                                    if issue.row_index is not None
                                }
                            ),
                        )
            else:
                duplicate_mask = df.duplicated(
                    subset=list(schema.unique),
                    keep=False,
                )

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
                                row_index=int(index) + 1,
                            )
                        )

                        if reached_limit():
                            issues = issues[:max_errors]

                            return ValidationResult(
                                row_count=len(df),
                                issue_count=len(issues),
                                issues=issues,
                                bad_rows=sorted(
                                    {
                                        issue.row_index
                                        for issue in issues
                                        if issue.row_index is not None
                                    }
                                ),
                            )

    if schema.rules:
        for rule_fn in schema.rules:
            rule_name = getattr(rule_fn, "__name__", type(rule_fn).__name__)
            try:
                result = rule_fn(df)
                if not isinstance(result, list):
                    raise TypeError(
                        f"Rule {rule_name!r} must return a list of "
                        f"ValidationIssue, got {type(result).__name__!r}"
                    )
                for item in result:
                    if not isinstance(item, ValidationIssue):
                        raise TypeError(
                            f"Rule {rule_name!r} returned a non-ValidationIssue "
                            f"item: {type(item).__name__!r}"
                        )
                issues.extend(result)
                if reached_limit():
                    issues = issues[:max_errors]

                    return ValidationResult(
                        row_count=len(df),
                        issue_count=len(issues),
                        issues=issues,
                        bad_rows=sorted(
                            {
                                issue.row_index
                                for issue in issues
                                if issue.row_index is not None
                            }
                        ),
                    )

            except KeyError as e:
                issues.append(
                    ValidationIssue(
                        column=str(e).strip("'"),
                        rule="missing_column",
                        message=f"Cross-field rule referenced a missing column: {e}",
                    )
                )
                if reached_limit():
                    issues = issues[:max_errors]

                    return ValidationResult(
                        row_count=len(df),
                        issue_count=len(issues),
                        issues=issues,
                        bad_rows=sorted(
                            {
                                issue.row_index
                                for issue in issues
                                if issue.row_index is not None
                            }
                        ),
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
    severity: str = "error",
    required_if: tuple[str, Any] | None = None,
) -> Field:
    """Create an int64 schema field.

    Args:
        nullable: Whether null values are allowed.
        min: Minimum allowed value.
        max: Maximum allowed value.
        unique: Whether non-null values must be unique.
        severity: Severity level for validation issues.
        required_if: Conditional requirement as a column/value pair.

    Returns:
        Field: Configured int64 schema field.
    """

    if min is not None:
        if isinstance(min, bool) or not isinstance(min, (int, float)):
            raise TypeError("min must be numeric or None")
    if max is not None:
        if isinstance(max, bool) or not isinstance(max, (int, float)):
            raise TypeError("max must be numeric or None")
    if min is not None and max is not None and min > max:
        raise ValueError("min must be less than or equal to max")

    return Field(
        dtype="int64",
        nullable=nullable,
        min=min,
        max=max,
        unique=unique,
        required_if=required_if,
        severity=severity,
    )


def Float64(
    *,
    nullable: bool = True,
    min: float | None = None,
    max: float | None = None,
    unique: bool = False,
    severity: str = "error",
    required_if: tuple[str, Any] | None = None,
) -> Field:
    """Create a float64 schema field.

    Args:
        nullable: Whether null values are allowed.
        min: Minimum allowed value.
        max: Maximum allowed value.
        unique: Whether non-null values must be unique.
        severity: Severity level for validation issues.
        required_if: Conditional requirement as a column/value pair.

    Returns:
        Field: Configured float64 schema field.
    """

    if min is not None:
        if isinstance(min, bool) or not isinstance(min, (int, float)):
            raise TypeError("min must be numeric or None")
    if max is not None:
        if isinstance(max, bool) or not isinstance(max, (int, float)):
            raise TypeError("max must be numeric or None")
    if min is not None and max is not None and min > max:
        raise ValueError("min must be less than or equal to max")

    return Field(
        dtype="float64",
        nullable=nullable,
        min=min,
        max=max,
        unique=unique,
        required_if=required_if,
        severity=severity,
    )


def String(
    *,
    nullable: bool = True,
    pattern: str | None = None,
    allowed: set[Any] | list[Any] | tuple[Any, ...] | None = None,
    unique: bool = False,
    severity: str = "error",
    min_length: int | None = None,
    max_length: int | None = None,
    required_if: tuple[str, Any] | None = None,
) -> Field:
    """Create a string schema field.

    Args:
        nullable: Whether null values are allowed.
        pattern: Regular expression pattern that non-null values must match.
        allowed: Allowed values for the field.
        unique: Whether non-null values must be unique.
        severity: Severity level for validation issues.
        min_length: Minimum allowed string length.
        max_length: Maximum allowed string length.
        required_if: Conditional requirement as a column/value pair.

    Returns:
        Field: Configured string schema field.
    """

    if min_length is not None and max_length is not None and min_length > max_length:
        raise ValueError("min_length must be less than or equal to max_length")

    if isinstance(allowed, (str, bytes)):
        raise TypeError(
            "allowed must be a sequence of allowed values, not a bare string"
        )

    allowed_set = set(allowed) if allowed is not None else None

    return Field(
        dtype="string",
        nullable=nullable,
        pattern=pattern,
        allowed=allowed_set,
        unique=unique,
        min_length=min_length,
        max_length=max_length,
        required_if=required_if,
        severity=severity,
    )


def Bool(
    *,
    nullable: bool = True,
    severity: str = "error",
    required_if: tuple[str, Any] | None = None,
) -> Field:
    """Create a bool schema field.

    Args:
        nullable: Whether null values are allowed.
        severity: Severity level for validation issues.
        required_if: Conditional requirement as a column/value pair.

    Returns:
        Field: Configured bool schema field.
    """
    return Field(
        dtype="bool",
        nullable=nullable,
        required_if=required_if,
        severity=severity,
    )


def Email(
    *,
    nullable: bool = True,
    unique: bool = False,
    severity: str = "error",
    validation: str = "light",
    required_if: tuple[str, Any] | None = None,
) -> Field:
    """Create an email-address schema field.

    Args:
        nullable: Whether null values are allowed.
        unique: Whether non-null values must be unique.
        severity: Severity level for validation issues.
        validation: Email validation mode, either "light" or "strict".
        required_if: Conditional requirement as a column/value pair.

    Returns:
        Field: Configured email-address schema field.
    """
    if validation not in {"light", "strict"}:
        raise ValueError("Email validation must be 'light' or 'strict'")
    return Field(
        dtype="string",
        nullable=nullable,
        semantic="email" if validation == "light" else "email:strict",
        unique=unique,
        required_if=required_if,
        severity=severity,
    )


def URL(
    *,
    nullable: bool = True,
    unique: bool = False,
    severity: str = "error",
    required_if: tuple[str, Any] | None = None,
    allowed_schemes: list[str] | None = None,
) -> Field:
    """Create a URL schema field.
    Args:
        nullable: Whether null values are allowed.
        unique: Whether non-null values must be unique.
        severity: Severity level for validation issues.
        required_if: Conditional requirement as a column/value pair.
        allowed_schemes: List of allowed URL schemes e.g. ["https"].
            If None, both http and https are accepted.
    Returns:
        Field: Configured URL schema field.
    """
    if allowed_schemes is not None:
        if isinstance(allowed_schemes, (str, bytes)):
            raise TypeError(
                "allowed_schemes must be a sequence of scheme names, not a bare string"
            )

        if not isinstance(allowed_schemes, (list, tuple, set)):
            raise TypeError("allowed_schemes must be a sequence of scheme names")

        normalized_schemes = set()

        for scheme in allowed_schemes:
            if not isinstance(scheme, str):
                raise ValueError("allowed_schemes must contain non-empty strings")

            scheme = scheme.strip()

            if scheme == "":
                raise ValueError("allowed_schemes must contain non-empty strings")

            if URL_SCHEME_PATTERN.fullmatch(scheme) is None:
                raise ValueError(
                    "allowed_schemes must contain URL scheme names such as 'http' or 'https'"
                )

            normalized_schemes.add(scheme)

        if len(normalized_schemes) == 0:
            raise ValueError("allowed_schemes must be a non-empty sequence")

        schemes = "|".join(re.escape(scheme) for scheme in sorted(normalized_schemes))

        semantic = f"url:{schemes}"

    else:
        semantic = "url"
    return Field(
        dtype="string",
        nullable=nullable,
        semantic=semantic,
        unique=unique,
        required_if=required_if,
        severity=severity,
    )


def PhoneNumber(
    *,
    nullable: bool = True,
    unique: bool = False,
    severity: str = "error",
    required_if: tuple[str, Any] | None = None,
) -> Field:
    """Create a phone-number schema field.

    Args:
        nullable: Whether null values are allowed.
        unique: Whether non-null values must be unique.
        severity: Severity level for validation issues.
        required_if: Conditional requirement as a column/value pair.

    Returns:
        Field: Configured phone-number schema field.
    """
    return Field(
        dtype="string",
        nullable=nullable,
        semantic="phone",
        unique=unique,
        required_if=required_if,
        severity=severity,
    )


def CountryCode(
    *,
    nullable: bool = True,
    unique: bool = False,
    severity: str = "error",
    required_if: tuple[str, Any] | None = None,
) -> Field:
    """Create an uppercase ISO alpha-2 country-code schema field.

    Args:
        nullable: Whether null values are allowed.
        unique: Whether non-null values must be unique.
        severity: Severity level for validation issues.
        required_if: Conditional requirement as a column/value pair.

    Returns:
        Field: Configured uppercase ISO alpha-2 country-code schema field.
    """
    return Field(
        dtype="string",
        nullable=nullable,
        semantic="country_code",
        unique=unique,
        required_if=required_if,
        severity=severity,
    )


def LanguageCode(
    *,
    nullable: bool = True,
    unique: bool = False,
    severity: str = "error",
    required_if: tuple[str, Any] | None = None,
) -> Field:
    """Create a lowercase ISO 639-1 language-code schema field.

    Args:
        nullable: Whether null values are allowed.
        unique: Whether non-null values must be unique.
        severity: Severity level for validation issues.
        required_if: Conditional requirement as a column/value pair.

    Returns:
        Field: Configured lowercase ISO 639-1 language-code schema field.
    """
    return Field(
        dtype="string",
        nullable=nullable,
        semantic="language_code",
        unique=unique,
        required_if=required_if,
        severity=severity,
    )


def TimeZone(
    *,
    nullable: bool = True,
    unique: bool = False,
    severity: str = "error",
    required_if: tuple[str, Any] | None = None,
) -> Field:
    """Create an IANA timezone schema field.

    Args:
        nullable: Whether null values are allowed.
        unique: Whether non-null values must be unique.
        severity: Severity level for validation issues.
        required_if: Conditional requirement as a column/value pair.

    Returns:
        Field: Configured IANA timezone schema field.
    """
    return Field(
        dtype="string",
        nullable=nullable,
        semantic="timezone",
        unique=unique,
        required_if=required_if,
        severity=severity,
    )


def CurrencyCode(
    *,
    nullable: bool = True,
    unique: bool = False,
    severity: str = "error",
    required_if: tuple[str, Any] | None = None,
    allowed: set[Any] | list[Any] | tuple[Any, ...] | None = None,
) -> Field:
    """Create a currency-code schema field.

    Args:
        nullable: Whether null values are allowed.
        unique: Whether non-null values must be unique.
        severity: Severity level for validation issues.
        required_if: Conditional requirement as a column/value pair.
        allowed: Allowed currency codes, overriding the default active ISO 4217 set.

    Returns:
        Field: Configured 3-letter uppercase currency-code schema field.
    """
    allowed_set = set(allowed) if allowed is not None else None
    return Field(
        dtype="string",
        nullable=nullable,
        semantic="currency_code",
        unique=unique,
        severity=severity,
        required_if=required_if,
        allowed=allowed_set,
    )


def Date(
    *,
    nullable: bool = True,
    unique: bool = False,
    severity: str = "error",
    required_if: tuple[str, Any] | None = None,
) -> Field:
    """Create a date schema field.

    Args:
        nullable: Whether null values are allowed.
        unique: Whether non-null values must be unique.
        severity: Severity level for validation issues.
        required_if: Conditional requirement as a column/value pair.

    Returns:
        Field: Configured date schema field.
    """
    return Field(
        dtype="string",
        nullable=nullable,
        semantic="date",
        unique=unique,
        required_if=required_if,
        severity=severity,
    )


def Regex(
    pattern: str,
    *,
    nullable: bool = True,
    unique: bool = False,
    severity: str = "error",
    required_if: tuple[str, Any] | None = None,
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
        required_if=required_if,
        severity=severity,
    )


def DateTime(
    *,
    nullable: bool = True,
    min: Any = None,
    max: Any = None,
    unique: bool = False,
    severity: str = "error",
    format: str | None = None,
    required_if: tuple[str, Any] | None = None,
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
        required_if=required_if,
        severity=severity,
    )


def _is_safely_convertible_to_dtype(
    series: pd.Series,
    expected_dtype: str,
    column_name: str,
) -> bool:
    """Return True if series values can be safely cast to expected_dtype without data loss."""
    try:
        non_null = series.dropna()

        if len(non_null) == 0:
            return False

        values = non_null.astype(str)

        lower_name = column_name.lower()

        is_identifier_like = (
            lower_name == "id"
            or lower_name.endswith("_id")
            or lower_name
            in {
                "uuid",
                "zip",
                "zipcode",
                "zip_code",
            }
        )

        if is_identifier_like:
            if values.str.match(r"^0\d+$").any():
                return False

        if expected_dtype == "int64":
            if not values.str.match(r"^-?\d+$").all():
                return False

            parsed = pd.to_numeric(values, errors="raise")

            int64_info = np.iinfo(np.int64)
            if (parsed < int64_info.min).any() or (parsed > int64_info.max).any():
                return False

            return True

        if expected_dtype == "float64":
            pd.to_numeric(values, errors="raise")
            return True

    except Exception:
        return False

    return False


def _validate_column(
    df: pd.DataFrame,
    series: pd.Series,
    actual_dtype: str | None,
    name: str,
    field_def: Field,
) -> list[ValidationIssue]:
    """Validate a single column against its Field definition and return all issues found."""
    issues: list[ValidationIssue] = []

    if field_def.dtype is not None and actual_dtype != field_def.dtype:
        if not (field_def.dtype == "datetime" and actual_dtype == "string"):

            message = (
                f"Column {name!r} has dtype {actual_dtype!r}; "
                f"expected {field_def.dtype!r}"
            )
            if (
                actual_dtype == "string"
                and field_def.dtype in {"int64", "float64"}
                and _is_safely_convertible_to_dtype(
                    df[name],
                    field_def.dtype,
                    name,
                )
            ):
                message += (
                    f". Values appear safely convertible " f"to '{field_def.dtype}'"
                )

            issues.append(
                ValidationIssue(
                    column=name,
                    rule="dtype",
                    message=message,
                    severity=field_def.severity,
                )
            )

    is_null_mask = series.isna()
    if actual_dtype in ("object", "string"):
        is_null_mask = is_null_mask | (series.fillna("").astype(str).str.strip() == "")

    if not field_def.nullable:
        issues.extend(
            _row_issues(
                series[is_null_mask],
                column=name,
                rule="nullable",
                message=f"Column {name!r} contains null or empty values",
                severity=field_def.severity,
            )
        )

    non_null = series[~is_null_mask]

    if field_def.required_if is not None:
        condition_column, expected_value = field_def.required_if

        if condition_column not in df.columns:
            issues.append(
                ValidationIssue(
                    column=condition_column,
                    rule="missing_column",
                    message=f"Column {condition_column!r} not found",
                )
            )
        else:
            trigger_mask = df[condition_column] == expected_value
            invalid = series[trigger_mask & is_null_mask]

            issues.extend(
                _row_issues(
                    invalid,
                    column=name,
                    rule="required_if",
                    message=(
                        f"Column {name!r} is required when "
                        f"{condition_column!r} == {expected_value!r}"
                    ),
                    severity=field_def.severity,
                )
            )

    if field_def.unique:
        duplicate_mask = non_null.duplicated(keep=False)
        issues.extend(
            _row_issues(
                non_null[duplicate_mask],
                column=name,
                rule="unique",
                message=f"Column {name!r} contains duplicate values",
                severity=field_def.severity,
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
                severity=field_def.severity,
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
                severity=field_def.severity,
            )
        )
        if field_def.min is not None:
            issues.extend(
                _row_issues(
                    non_null[numeric < field_def.min],
                    column=name,
                    rule="min",
                    message=f"Column {name!r} has values below {field_def.min}",
                    severity=field_def.severity,
                )
            )
        if field_def.max is not None:
            issues.extend(
                _row_issues(
                    non_null[numeric > field_def.max],
                    column=name,
                    rule="max",
                    message=f"Column {name!r} has values above {field_def.max}",
                    severity=field_def.severity,
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
                severity=field_def.severity,
            )
        )

    if field_def.semantic is not None:
        if field_def.semantic.startswith("custom:"):
            validator_name = field_def.semantic[len("custom:") :]
            fn = _CUSTOM_VALIDATORS.get(validator_name)
            if fn is None:
                issues.append(
                    ValidationIssue(
                        column=name,
                        rule="custom",
                        message=f"Custom validator {validator_name!r} is not registered",
                    )
                )
            else:
                invalid = non_null[
                    ~non_null.map(
                        lambda v: _normalize_validator_result(fn(v), validator_name)
                    )
                ]
                issues.extend(
                    _row_issues(
                        invalid,
                        column=name,
                        rule="custom",
                        message=(
                            f"Column {name!r} contains values that failed "
                            f"the {validator_name!r} validator"
                        ),
                        severity=field_def.severity,
                    )
                )
        else:
            pattern = _SEMANTIC_PATTERNS.get(field_def.semantic)
            if pattern is None and field_def.semantic.startswith("url:"):
                schemes = field_def.semantic[len("url:") :]
                pattern = rf"({schemes})://[^\s]+"
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
                    invalid = pd.Series(
                        {index: value for index, value in invalid_values}
                    )
                elif field_def.semantic == "country_code":
                    invalid = non_null[~non_null.isin(ISO_3166_1_ALPHA_2)]

                elif field_def.semantic == "language_code":
                    invalid = non_null[~non_null.isin(ISO_639_1_CODES)]
                elif field_def.semantic == "timezone":
                    invalid = non_null[~non_null.isin(IANA_TIMEZONES)]
                elif field_def.semantic == "currency_code":
                    if field_def.allowed is not None:
                        invalid = pd.Series(dtype=object)
                    else:
                        invalid = non_null[~non_null.isin(ISO_4217_CURRENCY_CODES)]

                else:
                    invalid = non_null[~text.str.fullmatch(pattern, na=False)]

                issues.extend(
                    _row_issues(
                        invalid,
                        column=name,
                        rule=field_def.semantic,
                        message=f"Column {name!r} contains invalid {field_def.semantic} values",
                        severity=field_def.severity,
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
                severity=field_def.severity,
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
                severity=field_def.severity,
            )
        )

    return issues


def _validate_datetime(
    non_null: pd.Series,
    name: str,
    field_def: Field,
) -> list[ValidationIssue]:
    """Validate non-null datetime values against the format and min/max bounds in field_def."""
    issues: list[ValidationIssue] = []
    parsed = pd.to_datetime(non_null, format=field_def.format, errors="coerce")

    invalid_format = non_null[parsed.isna()]
    issues.extend(
        _row_issues(
            invalid_format,
            column=name,
            rule="format",
            message=f"Column {name!r} does not match the required datetime format",
            severity=field_def.severity,
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
                severity=field_def.severity,
            )
        )
    if field_def._datetime_max is not None:
        issues.extend(
            _row_issues(
                valid_non_null[valid_parsed > field_def._datetime_max],
                column=name,
                rule="max",
                message=f"Column {name!r} has values above {field_def._datetime_max}",
                severity=field_def.severity,
            )
        )

    return issues


def _parse_datetime_bound(value: Any, name: str) -> pd.Timestamp | None:
    """Parse a datetime bound value into a pd.Timestamp, raising ValueError on failure."""
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
    severity: str = "error",
) -> list[ValidationIssue]:
    """Convert a series of invalid rows into a list of ValidationIssue objects."""
    return [
        ValidationIssue(
            column=column,
            rule=rule,
            message=message,
            row_index=int(index) + 1,
            value=value,
            severity=severity,
        )
        for index, value in invalid.items()
    ]


def _field_to_dict(field_def: Field) -> dict[str, Any]:
    """Serialize a Field definition to a plain dict suitable for in-memory use."""
    return {
        "dtype": field_def.dtype,
        "nullable": field_def.nullable,
        "min": field_def.min,
        "max": field_def.max,
        "pattern": field_def.pattern,
        "semantic": field_def.semantic,
        "allowed": _normalize_sequence(field_def.allowed),
        "unique": field_def.unique,
        "min_length": field_def.min_length,
        "max_length": field_def.max_length,
        "format": field_def.format,
        "datetime_min": _clean_scalar(field_def._datetime_min),
        "datetime_max": _clean_scalar(field_def._datetime_max),
        "required_if": _normalize_sequence(field_def.required_if),
    }


def _field_to_json_dict(field_def: Field) -> dict[str, Any]:
    """Serialize a Field definition to a JSON-safe dict, converting timestamps to ISO strings."""
    data = _field_to_dict(field_def)
    data["severity"] = field_def.severity
    data["datetime_min"] = (
        field_def._datetime_min.isoformat()
        if field_def._datetime_min is not None
        else None
    )
    data["datetime_max"] = (
        field_def._datetime_max.isoformat()
        if field_def._datetime_max is not None
        else None
    )
    return data


def _field_from_json_dict(name: str, payload: Any) -> Field:
    """Deserialize a JSON dict payload into a Field definition for the given column name."""
    if not isinstance(payload, dict):
        raise TypeError(
            f"Schema JSON field for column {name!r} must be an object, got {type(payload).__name__}."
        )

    allowed = payload.get("allowed")
    if allowed is not None:
        if not isinstance(allowed, list):
            raise TypeError(
                f"Schema JSON field {name!r} 'allowed' must be a list or null."
            )
        allowed = set(allowed)

    required_if = payload.get("required_if")
    if required_if is not None:
        if not isinstance(required_if, list) or len(required_if) != 2:
            raise TypeError(
                f"Schema JSON field {name!r} 'required_if' must be a 2-item list or null."
            )
        required_if = tuple(required_if)

    return Field(
        dtype=payload.get("dtype"),
        nullable=payload.get("nullable", True),
        min=payload.get("min"),
        max=payload.get("max"),
        pattern=payload.get("pattern"),
        semantic=payload.get("semantic"),
        allowed=allowed,
        unique=payload.get("unique", False),
        min_length=payload.get("min_length"),
        max_length=payload.get("max_length"),
        format=payload.get("format"),
        _datetime_min=_parse_datetime_bound(
            payload.get("datetime_min"), "datetime_min"
        ),
        _datetime_max=_parse_datetime_bound(
            payload.get("datetime_max"), "datetime_max"
        ),
        required_if=required_if,
        severity=payload.get("severity", "error"),
    )


def _normalize_unique(
    value: list[str] | tuple[str, ...] | None,
) -> tuple[str, ...] | None:
    """Normalize a unique-constraint value into a sorted tuple, or None if not set."""
    if value is None:
        return None
    return tuple(sorted(value))


def _normalize_sequence(value: Any) -> Any:
    """Convert sets and tuples to lists for JSON-serializable output."""
    if isinstance(value, set):
        return sorted(value)
    if isinstance(value, tuple):
        return list(value)
    return value


def _clean_scalar(value: Any) -> Any:
    """Recursively convert numpy scalars and NaN values to JSON-safe Python types."""
    if isinstance(value, dict):
        return {key: _clean_scalar(val) for key, val in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_clean_scalar(item) for item in value]
    if pd.isna(value):
        return None
    if hasattr(value, "item"):
        return value.item()
    return value


def _markdown_cell(value: Any) -> str:
    """Escape a value for safe rendering inside a Markdown table cell."""
    if value is None:
        return ""
    text = str(value).replace("\n", "<br>").replace("|", "\\|")
    return text


_SEMANTIC_PATTERNS = {
    "email": r"[^@\s]+@[^@\s]+\.[^@\s]+",
    "language_code": r"[a-z]{2}",
    "timezone": r"[A-Za-z_]+(?:/[A-Za-z_\-]+)+",
    "email:strict": (
        r"[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+"
        r"@"
        r"[a-zA-Z0-9-]+"
        r"(?:\.[a-zA-Z0-9-]+)+"
    ),
    "url": r"https?://[^\s]+",
    "phone": r"\+?[0-9][0-9 .()\-]{6,}[0-9]",
    "country_code": r"[A-Z]{2}",
    "currency_code": r"[A-Z]{3}",
    "date": r"\d{4}-\d{2}-\d{2}",
}

# Registry for custom validators registered via register_validator()
_CUSTOM_VALIDATORS: dict[str, callable] = {}


def register_validator(name: str, fn: callable) -> None:
    """Register a custom validator function for use with Custom().

    Parameters
    ----------
    name : str
        Unique name to identify this validator.
    fn : callable
        A function that accepts a scalar value and returns True if valid,
        False otherwise.

    Examples
    --------
    >>> def is_positive(value):
    ...     return value > 0
    >>> ar.register_validator("positive", is_positive)
    """
    if not callable(fn):
        raise TypeError("fn must be callable")
    if not isinstance(name, str) or not name:
        raise ValueError("name must be a non-empty string")
    _CUSTOM_VALIDATORS[name] = fn


def _normalize_validator_result(result: object, validator_name: str) -> bool:
    """Normalize a custom validator return value to a strict bool.

    Contract:
    - ``True``  → passes validation
    - ``False`` → fails validation
    - ``None``  → fails validation
    - ``pd.NA`` → fails validation
    - anything else → raises TypeError naming the validator

    This avoids calling bool() on pd.NA (which raises
    "TypeError: boolean value of NA is ambiguous") and enforces a clear
    return-value contract for custom validators.
    """
    if result is True:
        return True
    if result is False or result is None:
        return False
    # Check for pd.NA without importing pandas at module level
    try:
        import pandas as _pd

        if result is _pd.NA:
            return False
    except ImportError:
        pass
    raise TypeError(
        f"Custom validator {validator_name!r} returned "
        f"{type(result).__name__!r} ({result!r}); "
        "validators must return True (pass) or False (fail)."
    )


def Custom(
    name: str,
    *,
    nullable: bool = True,
    unique: bool = False,
    severity: str = "error",
) -> Field:
    """Create a field validated by a registered custom validator.

    Parameters
    ----------
    name : str
        Name of the validator registered via register_validator().
    nullable : bool, default True
        Whether null values are allowed.
    unique : bool, default False
        Whether all non-null values must be unique.

    Examples
    --------
    >>> ar.register_validator("positive", lambda v: v > 0)
    >>> schema = ar.Schema({"score": ar.Custom("positive", nullable=False)})
    """
    if name not in _CUSTOM_VALIDATORS:
        raise ValueError(
            f"No validator registered under {name!r}. "
            "Call ar.register_validator() first."
        )
    return Field(
        dtype=None,
        nullable=nullable,
        unique=unique,
        semantic=f"custom:{name}",
        severity=severity,
    )
