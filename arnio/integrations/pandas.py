"""Pandas DataFrame accessor for Arnio workflows."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import numpy as np
import pandas as pd

from arnio.convert import from_pandas, to_pandas
from arnio.diff import DataFrameDiffReport, diff_dataframes
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

    def to_numpy(
        self,
        columns: list[str] | None = None,
        *,
        null_value: float = float("nan"),
        allow_non_numeric: bool = False,
    ) -> np.ndarray:
        """Extract numeric columns as a 2-D NumPy ``float64`` array.

        This is ideal for preparing clean arrays from messy DataFrames
        for use in scikit-learn models or other numerical workflows.

        Converts the DataFrame to an ArFrame internally, then delegates
        to :func:`arnio.to_numpy`.  See that function for full parameter
        documentation.
        """
        return validate(self.to_arframe(), schema, max_errors=max_errors)

    def diff(
        self,
        other: pd.DataFrame,
        *,
        null_ratio_threshold: float = 0.0,
    ) -> DataFrameDiffReport:
        """Compare this DataFrame against another for drift.

        Parameters
        ----------
        other : pd.DataFrame
            DataFrame to compare against.
        null_ratio_threshold : float, default 0.0
            Minimum absolute change in null ratio to flag as drift.
        """
        return diff_dataframes(
            self._df, other, null_ratio_threshold=null_ratio_threshold
        )
