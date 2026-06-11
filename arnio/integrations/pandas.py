"""Pandas DataFrame accessor for Arnio workflows."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import pandas as pd

from arnio.cleaning import (
    clip_numeric as clip_numeric_values,
)
from arnio.cleaning import (
    drop_nulls as drop_null_rows,
)
from arnio.cleaning import (
    fill_nulls as fill_null_values,
)
from arnio.cleaning import (
    strip_whitespace as strip_whitespace_values,
)
from arnio.convert import from_pandas, to_pandas
from arnio.frame import ArFrame
from arnio.pipeline import pipeline as run_pipeline
from arnio.quality import (
    CleanExplanation,
    DataQualityReport,
    auto_clean,
    profile,
    suggest_cleaning,
)
from arnio.schema import Schema, ValidationResult, validate


@pd.api.extensions.register_dataframe_accessor("arnio")
class ArnioPandasAccessor:
    """Run Arnio preparation helpers from an existing pandas DataFrame."""

    def __init__(self, pandas_obj: pd.DataFrame) -> None:
        self._df = pandas_obj

    def to_arframe(self) -> ArFrame:
        """Convert the DataFrame into an Arnio frame."""
        return from_pandas(self._df)

    def pipeline(self, steps: Sequence[Any]) -> pd.DataFrame:
        """Run an Arnio pipeline and return a pandas DataFrame."""
        frame = self.to_arframe()
        return to_pandas(run_pipeline(frame, steps))

    def clean(
        self,
        steps: Sequence[Any] | None = None,
        *,
        strip_whitespace: bool = True,
        drop_nulls: bool = False,
        drop_duplicates: bool = False,
    ) -> pd.DataFrame:
        """Clean a DataFrame with Arnio and return pandas output.

        When ``steps`` is provided, it is passed directly to ``ar.pipeline``.
        Otherwise this uses Arnio's convenience ``clean`` behavior.
        """
        if steps is not None:
            return self.pipeline(steps)

        from arnio.cleaning import clean

        frame = clean(
            self.to_arframe(),
            strip_whitespace=strip_whitespace,
            drop_nulls=drop_nulls,
            drop_duplicates=drop_duplicates,
        )
        return to_pandas(frame)

    def strip_whitespace(self, *, subset: list[str] | None = None) -> pd.DataFrame:
        """Trim leading/trailing whitespace and return pandas output."""
        frame = strip_whitespace_values(self.to_arframe(), subset=subset)
        return to_pandas(frame)

    def drop_nulls(self, *, subset: list[str] | None = None) -> pd.DataFrame:
        """Drop rows with nulls in the selected columns."""
        frame = drop_null_rows(self.to_arframe(), subset=subset)
        return to_pandas(frame)

    def fill_nulls(
        self, value: Any, *, subset: list[str] | None = None
    ) -> pd.DataFrame:
        """Fill nulls in the selected columns and return pandas output."""
        frame = fill_null_values(self.to_arframe(), value, subset=subset)
        return to_pandas(frame)

    def clip_numeric(
        self,
        *,
        lower: int | float | None = None,
        upper: int | float | None = None,
        subset: list[str] | None = None,
    ) -> pd.DataFrame:
        """Clip numeric values in the selected columns and return pandas output."""
        frame = clip_numeric_values(
            self.to_arframe(),
            lower=lower,
            upper=upper,
            subset=subset,
        )
        return to_pandas(frame)

    def profile(
        self,
        *,
        exclude_columns: Sequence[str] | None = None,
        sample_size: int = 5,
        approx_top_values: bool = False,
        approx_top_values_min_unique: int = 1000,
        approx_top_values_min_ratio: float = 0.2,
        approx_top_values_sample_size: int = 2000,
    ) -> DataQualityReport:
        """Profile DataFrame quality with Arnio."""
        return profile(
            self.to_arframe(),
            exclude_columns=exclude_columns,
            sample_size=sample_size,
            approx_top_values=approx_top_values,
            approx_top_values_min_unique=approx_top_values_min_unique,
            approx_top_values_min_ratio=approx_top_values_min_ratio,
            approx_top_values_sample_size=approx_top_values_sample_size,
        )

    def suggest_cleaning(self) -> list[tuple[str, dict[str, Any]]]:
        """Return Arnio pipeline-compatible cleaning suggestions."""
        return suggest_cleaning(self.to_arframe())

    def auto_clean(
        self,
        *,
        mode: str = "safe",
        return_report: bool = False,
        dry_run: bool = False,
        allow_lossy_casts: bool = False,
        confirmed_casts: dict[str, str] | None = None,
        explain: bool = False,
    ) -> (
        pd.DataFrame
        | DataQualityReport
        | tuple[pd.DataFrame, DataQualityReport]
        | tuple[pd.DataFrame, CleanExplanation]
        | tuple[pd.DataFrame, DataQualityReport, CleanExplanation]
    ):
        """Run Arnio's automatic cleaning and return pandas output.

        Parameters
        ----------
        explain : bool, default False
            When ``True``, also return a :class:`~arnio.quality.CleanExplanation`
            audit trail describing which steps ran and why.
        confirmed_casts : dict[str, str] or None, default None
            Exact strict-mode ``cast_types`` mapping to confirm after previewing
            proposed casts with ``dry_run=True`` or ``suggest_cleaning()``.
        """
        result = auto_clean(
            self.to_arframe(),
            mode=mode,
            return_report=return_report,
            dry_run=dry_run,
            allow_lossy_casts=allow_lossy_casts,
            confirmed_casts=confirmed_casts,
            explain=explain,
        )

        if dry_run:
            return result

        if return_report and explain:
            frame, report, explanation = result
            return to_pandas(frame), report, explanation

        if return_report:
            frame, report = result
            return to_pandas(frame), report

        if explain:
            frame, explanation = result
            return to_pandas(frame), explanation

        return to_pandas(result)

    def validate(
        self,
        schema: Schema | dict[str, Any],
        *,
        max_errors: int | None = None,
    ) -> ValidationResult:
        """Validate the DataFrame against an Arnio schema.

        Parameters
        ----------
        schema : Schema or dict[str, Field]
            Schema to validate against.
        max_errors : int or None, default None
            Maximum number of validation issues to collect. Mirrors the
            ``max_errors`` parameter of ``ar.validate()``. When None all
            issues are collected.
        """
        return validate(self.to_arframe(), schema, max_errors=max_errors)
