"""dict/list-of-dicts adapter — implements DataFrameAdapter for plain Python dicts.

Internally converts to pandas for computation, then converts back to
list[dict] on unwrap. This is the simplest adapter — it exists so users
can use arnio without requiring pandas as part of their mental model.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pandas as pd

from arnio.adapt._pandas import PandasAdapter

if TYPE_CHECKING:
    from arnio.adapt._protocol import NumericStats, StringLengthStats


def _to_dataframe(data: dict[str, list[Any]] | list[dict[str, Any]]) -> pd.DataFrame:
    """Convert dict-like input to a pandas DataFrame."""
    if isinstance(data, list):
        return pd.DataFrame(data)  # type: ignore[no-any-return]
    return pd.DataFrame(data)  # type: ignore[no-any-return]


class DictAdapter:
    """DataFrameAdapter implementation for dict / list-of-dicts.

    Wraps a PandasAdapter internally. Mutating operations return
    a new DictAdapter that wraps the modified data.
    """

    __slots__ = ("_inner",)

    def __init__(self, data: dict[str, list[Any]] | list[dict[str, Any]]) -> None:
        df = _to_dataframe(data)
        self._inner = PandasAdapter(df)

    @classmethod
    def _from_pandas_adapter(cls, adapter: PandasAdapter) -> DictAdapter:
        """Create a DictAdapter wrapping an existing PandasAdapter."""
        obj = object.__new__(cls)
        obj._inner = adapter
        return obj

    # -- Delegate read-only operations to inner adapter ---------------------

    def column_names(self) -> list[str]:
        return self._inner.column_names()

    def row_count(self) -> int:
        return self._inner.row_count()

    def column_dtype(self, column: str) -> str:
        return self._inner.column_dtype(column)

    def null_count(self, column: str) -> int:
        return self._inner.null_count(column)

    def unique_count(self, column: str) -> int:
        return self._inner.unique_count(column)

    def duplicate_count(self) -> int:
        return self._inner.duplicate_count()

    def value_counts(self, column: str, *, top_n: int = 10) -> dict[Any, int]:
        return self._inner.value_counts(column, top_n=top_n)

    def values_in_set(self, column: str, allowed: set[Any]) -> int:
        return self._inner.values_in_set(column, allowed)

    def regex_match_count(self, column: str, pattern: str) -> int:
        return self._inner.regex_match_count(column, pattern)

    def column_values(self, column: str) -> list[Any]:
        return self._inner.column_values(column)

    def numeric_stats(self, column: str) -> NumericStats:
        return self._inner.numeric_stats(column)

    def check_per_value(
        self, column: str, field_def: Any, max_issues: int | None = None
    ) -> list[Any]:
        return self._inner.check_per_value(column, field_def, max_issues=max_issues)

    def string_lengths(self, column: str) -> StringLengthStats:
        return self._inner.string_lengths(column)

    def sample(self, n: int) -> DictAdapter:
        return self._wrap(self._inner.sample(n))

    # -- Mutating operations ------------------------------------------------

    def _wrap(self, inner: PandasAdapter) -> DictAdapter:
        return DictAdapter._from_pandas_adapter(inner)

    def working_copy(self) -> DictAdapter:
        return self._wrap(self._inner.working_copy())

    def strip_whitespace(self, columns: list[str] | None = None) -> DictAdapter:
        return self._wrap(self._inner.strip_whitespace(columns))

    def normalize_case(
        self, columns: list[str] | None = None, *, case: str = "lower"
    ) -> DictAdapter:
        return self._wrap(self._inner.normalize_case(columns, case=case))

    def drop_duplicates(self) -> DictAdapter:
        return self._wrap(self._inner.drop_duplicates())

    def drop_nulls(
        self,
        columns: list[str] | None = None,
        *,
        how: str = "any",
    ) -> DictAdapter:
        return self._wrap(self._inner.drop_nulls(columns, how=how))

    def fill_nulls(self, column: str, value: Any) -> DictAdapter:
        return self._wrap(self._inner.fill_nulls(column, value))

    def rename_columns(self, mapping: dict[str, str]) -> DictAdapter:
        return self._wrap(self._inner.rename_columns(mapping))

    def drop_columns(self, columns: list[str]) -> DictAdapter:
        return self._wrap(self._inner.drop_columns(columns))

    def cast_column(self, column: str, dtype: str) -> DictAdapter:
        return self._wrap(self._inner.cast_column(column, dtype))

    def replace_values(self, column: str, mapping: dict[Any, Any]) -> DictAdapter:
        return self._wrap(self._inner.replace_values(column, mapping))

    def slugify_column_names(self) -> DictAdapter:
        return self._wrap(self._inner.slugify_column_names())

    def standardize_missing(
        self,
        tokens: set[str] | None = None,
        columns: list[str] | None = None,
    ) -> DictAdapter:
        return self._wrap(self._inner.standardize_missing(tokens, columns))

    # -- Unwrap returns list[dict] ------------------------------------------

    def unwrap(self) -> list[dict[str, Any]]:
        return self._inner.unwrap().to_dict(orient="records")  # type: ignore[return-value]

    def __repr__(self) -> str:
        return f"DictAdapter({self.row_count()} rows, {len(self.column_names())} columns)"
