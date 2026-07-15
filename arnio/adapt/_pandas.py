"""pandas DataFrame adapter — implements DataFrameAdapter for pd.DataFrame."""

from __future__ import annotations

import re
import unicodedata
from typing import Any

import pandas as pd

from arnio.adapt._protocol import NumericStats, StringLengthStats


def _is_string_dtype(series: pd.Series) -> bool:
    """Check if a pandas Series has string-like dtype (works with pandas 2.x and 3.x)."""
    dtype = series.dtype
    dtype_str = str(dtype).lower()
    return (
        dtype.name == "object"
        or dtype.kind in ("U", "S")
        or "string" in dtype_str
        or dtype_str == "str"
    )

# Default tokens treated as missing values by standardize_missing.
_DEFAULT_MISSING_TOKENS: frozenset[str] = frozenset({
    "", "n/a", "N/A", "na", "NA", "nan", "NaN", "NAN",
    "null", "NULL", "none", "None", "NONE",
    "-", "--", ".", "?", "missing", "MISSING",
    "undefined", "UNDEFINED", "#N/A", "#NA", "#REF!",
    "not available", "Not Available",
})


class PandasAdapter:
    """DataFrameAdapter implementation for pandas DataFrames.

    All mutating operations return a NEW PandasAdapter wrapping a copy.
    The original DataFrame is never modified.
    """

    __slots__ = ("_df",)

    def __init__(self, df: pd.DataFrame) -> None:
        self._df = df

    # -- Identity & metadata ------------------------------------------------

    def column_names(self) -> list[str]:
        return list(self._df.columns)

    def row_count(self) -> int:
        return len(self._df)

    def column_dtype(self, column: str) -> str:
        dtype = self._df[column].dtype
        kind = dtype.kind

        mapping: dict[str, str] = {
            "i": "int64",
            "u": "int64",
            "f": "float64",
            "b": "bool",
            "M": "datetime",
            "U": "string",
            "S": "string",
        }

        if kind in mapping:
            return mapping[kind]

        # pandas StringDtype, nullable integer, etc.
        dtype_str = str(dtype).lower()
        if "int" in dtype_str:
            return "int64"
        if "float" in dtype_str:
            return "float64"
        if "bool" in dtype_str:
            return "bool"
        if "string" in dtype_str or dtype_str == "str":
            return "string"
        if "datetime" in dtype_str:
            return "datetime"
        if dtype_str == "object":
            return "object"

        return str(dtype)

    # -- Null analysis ------------------------------------------------------

    def null_count(self, column: str) -> int:
        return int(self._df[column].isna().sum())

    # -- Uniqueness ---------------------------------------------------------

    def unique_count(self, column: str) -> int:
        return int(self._df[column].nunique(dropna=True))

    def duplicate_count(self) -> int:
        return int(self._df.duplicated().sum())

    # -- Value inspection ---------------------------------------------------

    def value_counts(self, column: str, *, top_n: int = 10) -> dict[Any, int]:
        counts = self._df[column].value_counts(dropna=True).head(top_n)
        return dict(zip(counts.index.tolist(), counts.values.tolist(), strict=False))

    def values_in_set(self, column: str, allowed: set[Any]) -> int:
        series = self._df[column].dropna()
        return int(series.isin(allowed).sum())

    def regex_match_count(self, column: str, pattern: str) -> int:
        series = self._df[column].dropna().astype(str)
        return int(series.str.fullmatch(pattern).sum())

    def column_values(self, column: str) -> list[Any]:
        return self._df[column].tolist()  # type: ignore[no-any-return]

    def check_per_value(
        self, column: str, field_def: Any, max_issues: int | None = None
    ) -> list[Any]:
        import arnio.schema as schema
        from arnio.validate._result import Issue
        
        issues: list[Any] = []
        series = self._df[column]
        mask = series.notna()
        if not mask.any():
            return issues
            
        valid_series = series[mask]
        
        def _add_issues(fail_mask: pd.Series, msg_template: str, rule: str) -> None:
            if not fail_mask.any():
                return
            fail_indices = fail_mask[fail_mask].index
            if max_issues is not None:
                remaining = max_issues - len(issues)
                if remaining <= 0:
                    return
                fail_indices = fail_indices[:remaining]
            
            # Extract just the bad values at once
            bad_vals = series.loc[fail_indices]
            for idx, val in bad_vals.items():
                issues.append(Issue(
                    column=column,
                    rule=rule,
                    message=msg_template.format(value=val),
                    severity=field_def.severity,
                    row_index=int(str(idx)),
                    value=val
                ))

        # We must support min/max for Numeric
        if getattr(field_def, "min", None) is not None or getattr(field_def, "max", None) is not None:
            if isinstance(field_def, (schema.Int, schema.Float)):
                numeric_series = pd.to_numeric(valid_series, errors="coerce")
                
                # Identify values that could not be coerced
                invalid_mask = numeric_series.isna() & valid_series.notna() & (valid_series != "")
                _add_issues(invalid_mask, "Cannot interpret {value!r} as number", "value_validation")
                
                # Compare valid numeric values
                if getattr(field_def, "min", None) is not None:
                    fails = numeric_series < field_def.min
                    _add_issues(fails, f"Value {{value}} is less than minimum {field_def.min}", "value_validation")
                if getattr(field_def, "max", None) is not None:
                    fails = numeric_series > field_def.max
                    _add_issues(fails, f"Value {{value}} is greater than maximum {field_def.max}", "value_validation")
            else:
                if getattr(field_def, "min", None) is not None:
                    fails = valid_series < field_def.min
                    _add_issues(fails, f"Value {{value}} is less than minimum {field_def.min}", "value_validation")
                if getattr(field_def, "max", None) is not None:
                    fails = valid_series > field_def.max
                    _add_issues(fails, f"Value {{value}} is greater than maximum {field_def.max}", "value_validation")

        # Support length for String
        if getattr(field_def, "min_length", None) is not None:
            fails = valid_series.str.len() < field_def.min_length
            _add_issues(fails, f"String length is less than minimum {field_def.min_length}", "value_validation")
        if getattr(field_def, "max_length", None) is not None:
            fails = valid_series.str.len() > field_def.max_length
            _add_issues(fails, f"String length is greater than maximum {field_def.max_length}", "value_validation")
            
        # Support Regex and semantic patterns
        pattern = getattr(field_def, "pattern", None)
        if pattern is not None:
            try:
                fails = ~valid_series.astype(str).str.fullmatch(pattern)
                msg = f"String does not match pattern {pattern!r}" if isinstance(field_def, schema.String) else "Value does not match required format"
                _add_issues(fails, msg, "value_validation")
            except AttributeError:
                pass

        # Fallback for complex validation without pattern
        if hasattr(field_def, "validate_value") and not pattern and not isinstance(field_def, (schema.Int, schema.Float, schema.String, schema.Regex)):
            # We don't want to fallback if we just checked pattern, because the fallback might do the same
            # Wait, Email and URL might use validate_value instead of exposing pattern.
            # Let's just run validate_value if it exists and we didn't just check a pattern.
            # Actually, `validate_value` is defined on all Fields. But if we already verified min/max/pattern,
            # we should skip it for Int/Float/String/Regex to avoid double-checking.
            for idx, val in valid_series.items():
                if max_issues is not None and len(issues) >= max_issues:
                    break
                err = field_def.validate_value(val)
                if err:
                    issues.append(Issue(column=column, rule="value_validation", message=err, severity=field_def.severity, row_index=int(str(idx)), value=val))
                        
        return issues

    # -- Numeric statistics -------------------------------------------------

    def numeric_stats(self, column: str) -> NumericStats:
        series = self._df[column].dropna()
        desc = series.describe()
        def _to_float(val: Any, default: float = 0.0) -> float:
            if pd.isna(val):
                return default
            return float(val)

        return NumericStats(
            min=_to_float(desc.get("min")),
            max=_to_float(desc.get("max")),
            mean=_to_float(desc.get("mean")),
            std=_to_float(desc.get("std")),
            q1=_to_float(desc.get("25%")),
            median=_to_float(desc.get("50%")),
            q3=_to_float(desc.get("75%")),
        )

    # -- String statistics --------------------------------------------------

    def string_lengths(self, column: str) -> StringLengthStats:
        lengths = self._df[column].dropna().astype(str).str.len()
        if lengths.empty:
            return StringLengthStats(min_length=0, max_length=0, mean_length=0.0)
        return StringLengthStats(
            min_length=int(lengths.min()),
            max_length=int(lengths.max()),
            mean_length=float(lengths.mean()),
        )

    # -- Sampling -----------------------------------------------------------

    def sample(self, n: int) -> PandasAdapter:
        actual_n = min(n, len(self._df))
        if actual_n == 0:
            return PandasAdapter(self._df.head(0))
        return PandasAdapter(self._df.sample(n=actual_n, random_state=42))

    def working_copy(self) -> "PandasAdapter":
        return PandasAdapter(self._df.copy())

    # -- Mutating operations (mutate in-place and return self) --------------

    def strip_whitespace(self, columns: list[str] | None = None) -> PandasAdapter:
        cols = columns or [c for c in self._df.columns if _is_string_dtype(self._df[c])]
        for col in cols:
            if col in self._df.columns and _is_string_dtype(self._df[col]):
                self._df[col] = self._df[col].str.strip()
        return self

    def normalize_case(
        self, columns: list[str] | None = None, *, case: str = "lower"
    ) -> PandasAdapter:
        cols = columns or [c for c in self._df.columns if _is_string_dtype(self._df[c])]

        if case not in {"lower", "upper", "title"}:
            raise ValueError(f"case must be 'lower', 'upper', or 'title', got {case!r}")

        for col in cols:
            if col in self._df.columns and _is_string_dtype(self._df[col]):
                if case == "lower":
                    self._df[col] = self._df[col].str.lower()
                elif case == "upper":
                    self._df[col] = self._df[col].str.upper()
                elif case == "title":
                    self._df[col] = self._df[col].str.title()
        return self

    def drop_duplicates(self) -> PandasAdapter:
        self._df = self._df.drop_duplicates().reset_index(drop=True)
        return self

    def drop_nulls(
        self,
        columns: list[str] | None = None,
        *,
        how: str = "any",
    ) -> PandasAdapter:
        self._df = self._df.dropna(subset=columns, how=how).reset_index(drop=True)  # type: ignore
        return self

    def fill_nulls(self, column: str, value: Any) -> PandasAdapter:
        self._df[column] = self._df[column].fillna(value)
        return self

    def rename_columns(self, mapping: dict[str, str]) -> PandasAdapter:
        self._df = self._df.rename(columns=mapping)
        return self

    def drop_columns(self, columns: list[str]) -> PandasAdapter:
        existing = [c for c in columns if c in self._df.columns]
        self._df = self._df.drop(columns=existing)
        return self

    def cast_column(self, column: str, dtype: str) -> PandasAdapter:
        dtype_map: dict[str, str] = {
            "int64": "int64",
            "float64": "float64",
            "string": "object",
            "bool": "bool",
        }
        pd_dtype = dtype_map.get(dtype, dtype)
        self._df[column] = self._df[column].astype(pd_dtype)  # type: ignore
        return self

    def replace_values(self, column: str, mapping: dict[Any, Any]) -> PandasAdapter:
        self._df[column] = self._df[column].replace(mapping)
        return self

    def slugify_column_names(self) -> PandasAdapter:
        def _slugify(name: str) -> str:
            # Normalize unicode to ASCII-compatible form
            name = unicodedata.normalize("NFKD", name)
            name = name.encode("ascii", "ignore").decode("ascii")
            # Replace non-alphanumeric with underscores
            name = re.sub(r"[^a-zA-Z0-9]+", "_", name)
            # Strip leading/trailing underscores and collapse doubles
            name = re.sub(r"_+", "_", name).strip("_")
            return name.lower()

        mapping = {col: _slugify(col) for col in self._df.columns}
        return self.rename_columns(mapping)

    def standardize_missing(
        self,
        tokens: set[str] | None = None,
        columns: list[str] | None = None,
    ) -> PandasAdapter:
        token_set = tokens if tokens is not None else _DEFAULT_MISSING_TOKENS
        cols = columns or [c for c in self._df.columns if _is_string_dtype(self._df[c])]
        for col in cols:
            if col in self._df.columns and _is_string_dtype(self._df[col]):
                mask = self._df[col].isin(token_set)
                self._df.loc[mask, col] = None
        return self

    # -- Unwrap -------------------------------------------------------------

    def unwrap(self) -> pd.DataFrame:
        return self._df

    # -- Repr ---------------------------------------------------------------

    def __repr__(self) -> str:
        return f"PandasAdapter({self.row_count()} rows, {len(self.column_names())} columns)"
