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

    def pipeline(
        self,
        steps: Sequence[Any],
        *,
        return_metadata: bool = False,
        dry_run: bool = False,
        verbose: bool = False,
    ) -> pd.DataFrame | tuple[pd.DataFrame, dict[str, Any]]:
        """Run an Arnio pipeline and return a pandas DataFrame.

        Parameters
        ----------
        steps : Sequence[tuple]
            List of pipeline steps to apply.
        return_metadata : bool, default False
            When True, also return a metadata dictionary with per-step timing
            and row count information.
        dry_run : bool, default False
            Validate pipeline structure without applying transformations.
        verbose : bool, default False
            Enable diagnostic logging for each pipeline step.

        Returns
        -------
        pd.DataFrame or tuple[pd.DataFrame, dict]
            If return_metadata is False (default), returns a pandas DataFrame.
            If return_metadata is True, returns (DataFrame, metadata_dict).
        """
        frame = self.to_arframe()
        result = run_pipeline(
            frame,
            steps,
            return_metadata=return_metadata,
            dry_run=dry_run,
            verbose=verbose,
        )

        if return_metadata:
            ar_frame, metadata = result
            return to_pandas(ar_frame), metadata
        return to_pandas(result)

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

    def profile(
        self,
        *,
        sample_size: int = 5,
        approx_top_values: bool = False,
        approx_top_values_min_unique: int = 1000,
        approx_top_values_min_ratio: float = 0.2,
        approx_top_values_sample_size: int = 2000,
    ) -> DataQualityReport:
        """Profile DataFrame quality with Arnio."""
        return profile(
            self.to_arframe(),
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
    ) -> pd.DataFrame | DataQualityReport | tuple[pd.DataFrame, DataQualityReport]:
        """Run Arnio's automatic cleaning and return pandas output."""
        result = auto_clean(
            self.to_arframe(),
            mode=mode,
            return_report=return_report,
            dry_run=dry_run,
            allow_lossy_casts=allow_lossy_casts,
        )

        if dry_run and not return_report:
            return result

        if return_report:
            frame, report = result
            return to_pandas(frame), report

        return to_pandas(result)

    def validate(self, schema: Schema | dict[str, Any]) -> ValidationResult:
        """Validate the DataFrame against an Arnio schema."""
        return validate(self.to_arframe(), schema)
