"""Pandas DataFrame accessor for Arnio workflows."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import pandas as pd

from arnio.convert import from_pandas, to_pandas
from arnio.frame import ArFrame
from arnio.pipeline import pipeline as run_pipeline
from arnio.quality import DataQualityReport, auto_clean, profile, suggest_cleaning
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

    def profile(self, *, sample_size: int = 5) -> DataQualityReport:
        """Profile DataFrame quality with Arnio."""
        return profile(self.to_arframe(), sample_size=sample_size)

    def suggest_cleaning(self) -> list[tuple[str, dict[str, Any]]]:
        """Return Arnio pipeline-compatible cleaning suggestions."""
        return suggest_cleaning(self.to_arframe())

    def auto_clean(
        self,
        *,
        mode: str = "safe",
        return_report: bool = False,
    ) -> pd.DataFrame | tuple[pd.DataFrame, DataQualityReport]:
        """Run Arnio's automatic cleaning and return pandas output."""
        result = auto_clean(
            self.to_arframe(),
            mode=mode,
            return_report=return_report,
        )

        if return_report:
            frame, report = result
            return to_pandas(frame), report

        return to_pandas(result)

    def validate(self, schema: Schema | dict[str, Any]) -> ValidationResult:
        """Validate the DataFrame against an Arnio schema."""
        return validate(self.to_arframe(), schema)
