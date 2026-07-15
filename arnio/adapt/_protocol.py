"""Adapter protocol — abstract interface for DataFrame operations.

The adapter protocol defines every operation that the core engines
(validate, profile, clean) need to perform on data. Each concrete
adapter implements these using native engine calls.

The engines NEVER touch raw DataFrames. They only call adapter methods.
This is the isolation boundary.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable


@dataclass(frozen=True)
class NumericStats:
    """Summary statistics for a numeric column."""

    mean: float
    std: float
    min: float
    max: float
    median: float
    q1: float
    q3: float


@dataclass(frozen=True)
class StringLengthStats:
    """Length statistics for a string column."""

    min_length: int
    max_length: int
    mean_length: float


@runtime_checkable
class DataFrameAdapter(Protocol):
    """Protocol defining all operations the core engines need.

    Read-only operations are used by validate and profile.
    Mutating operations are used by clean. Mutating operations
    mutate the data in place and return the same adapter.
    The caller is responsible for calling `working_copy()` once
    before a chain of mutations to avoid modifying the original data.
    """

    def working_copy(self) -> DataFrameAdapter:
        """Return a new adapter wrapping a deep copy of the data."""
        ...

    # -- Identity & metadata ------------------------------------------------

    def column_names(self) -> list[str]:
        """Return all column names in order."""
        ...

    def row_count(self) -> int:
        """Return total number of rows."""
        ...

    def column_dtype(self, column: str) -> str:
        """Return the dtype of a column as a normalized string.

        Returns one of: "int64", "float64", "string", "bool", "datetime",
        "object", or the raw dtype string if unknown.
        """
        ...

    # -- Null analysis ------------------------------------------------------

    def null_count(self, column: str) -> int:
        """Count null/NaN values in a column."""
        ...

    # -- Uniqueness ---------------------------------------------------------

    def unique_count(self, column: str) -> int:
        """Count distinct non-null values in a column."""
        ...

    def duplicate_count(self) -> int:
        """Count fully duplicate rows in the entire dataset."""
        ...

    # -- Value inspection ---------------------------------------------------

    def value_counts(self, column: str, *, top_n: int = 10) -> dict[Any, int]:
        """Return top N values with their counts, ordered by frequency."""
        ...

    def values_in_set(self, column: str, allowed: set[Any]) -> int:
        """Count non-null values that are members of the allowed set."""
        ...

    def regex_match_count(self, column: str, pattern: str) -> int:
        """Count non-null string values matching a regex pattern."""
        ...

    def column_values(self, column: str) -> list[Any]:
        """Return all values in a column as a Python list.

        Used for per-value validation (semantic fields, custom validators).
        For large datasets, consider using ``sample()`` first.
        """
        ...

    def check_per_value(
        self, column: str, field_def: Any, max_issues: int | None = None
    ) -> list[Any]:
        """Run vectorized per-value validation. Returns a list of Issues."""
        ...

    # -- Numeric statistics -------------------------------------------------

    def numeric_stats(self, column: str) -> NumericStats:
        """Compute summary statistics for a numeric column."""
        ...

    # -- String statistics --------------------------------------------------

    def string_lengths(self, column: str) -> StringLengthStats:
        """Compute min/max/mean string lengths for a string column."""
        ...

    # -- Sampling -----------------------------------------------------------

    def sample(self, n: int) -> DataFrameAdapter:
        """Return a new adapter wrapping at most *n* random rows."""
        ...

    # -- Mutating operations (return new adapter) ---------------------------

    def strip_whitespace(self, columns: list[str] | None = None) -> DataFrameAdapter:
        """Strip leading/trailing whitespace from string columns."""
        ...

    def normalize_case(
        self, columns: list[str] | None = None, *, case: str = "lower"
    ) -> DataFrameAdapter:
        """Convert string columns to lower/upper/title case."""
        ...

    def drop_duplicates(self) -> DataFrameAdapter:
        """Remove duplicate rows."""
        ...

    def drop_nulls(
        self,
        columns: list[str] | None = None,
        *,
        how: str = "any",
    ) -> DataFrameAdapter:
        """Remove rows with null values."""
        ...

    def fill_nulls(
        self, column: str, value: Any
    ) -> DataFrameAdapter:
        """Fill null values in a column with a constant."""
        ...

    def rename_columns(self, mapping: dict[str, str]) -> DataFrameAdapter:
        """Rename columns according to a mapping."""
        ...

    def drop_columns(self, columns: list[str]) -> DataFrameAdapter:
        """Drop specified columns."""
        ...

    def cast_column(self, column: str, dtype: str) -> DataFrameAdapter:
        """Cast a column to a different dtype."""
        ...

    def replace_values(
        self, column: str, mapping: dict[Any, Any]
    ) -> DataFrameAdapter:
        """Replace values in a column according to a mapping."""
        ...

    def slugify_column_names(self) -> DataFrameAdapter:
        """Normalize column names to snake_case, stripping special characters."""
        ...

    def standardize_missing(
        self,
        tokens: set[str] | None = None,
        columns: list[str] | None = None,
    ) -> DataFrameAdapter:
        """Replace common missing-value tokens with actual null."""
        ...

    # -- Unwrap -------------------------------------------------------------

    def unwrap(self) -> Any:
        """Return the underlying native data object.

        For the pandas adapter this returns a ``pd.DataFrame``.
        For the dict adapter this returns a ``list[dict]``.
        """
        ...
