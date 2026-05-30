"""Scikit-learn integration for Arnio's data preparation engine."""

import warnings

import numpy as np
import pandas as pd

try:
    from sklearn.base import BaseEstimator, TransformerMixin
    from sklearn.utils.validation import check_is_fitted
except ImportError:
    raise ImportError(
        "The 'scikit-learn' package is required to use ArnioCleaner. "
        "Install it with: pip install arnio[sklearn]"
    )

from arnio.convert import from_pandas, to_pandas
from arnio.pipeline import pipeline as run_pipeline

_ROW_COUNT_CHANGING_STEPS = frozenset(
    {"drop_nulls", "drop_duplicates", "keep_rows_with_nulls", "filter_rows"}
)

_SCHEMA_CHANGING_STEPS = frozenset(
    {
        "rename_columns",
        "drop_columns",
        "drop_columns_matching",
        "drop_constant_columns",
        "combine_columns",
        "coalesce_columns",
        "trim_column_names",
    }
)


class ArnioCleaner(BaseEstimator, TransformerMixin):
    def __init__(
        self,
        steps=None,
        copy=True,
        allow_row_count_change=False,
        allow_schema_changes=False,
    ):
        self.steps = steps if steps is not None else []
        self.copy = copy
        self.allow_row_count_change = allow_row_count_change
        self.allow_schema_changes = allow_schema_changes

    def _validate_params(self):
        if not isinstance(self.copy, bool):
            raise TypeError("copy must be a bool")
        if not isinstance(self.allow_row_count_change, bool):
            raise TypeError("allow_row_count_change must be a bool")
        if not isinstance(self.allow_schema_changes, bool):
            raise TypeError("allow_schema_changes must be a bool")

    def set_params(self, **params):
        snapshot = self.get_params(deep=False)

        try:
            super().set_params(**params)
            self._validate_params()
        except Exception:
            for key, value in snapshot.items():
                setattr(self, key, value)
            raise

        return self

    def _validate_steps_contract(self):
        for step in self.steps:
            name = step[0] if isinstance(step, tuple) else step
            if name in _ROW_COUNT_CHANGING_STEPS and not self.allow_row_count_change:
                raise ValueError(
                    f"Step '{name}' changed the row count, which is not allowed. "
                    "Use allow_row_count_change=True to enable."
                )
            if not self.allow_schema_changes and name in _SCHEMA_CHANGING_STEPS:
                raise ValueError(
                    f"Schema-changing step '{name}' not allowed. Use allow_schema_changes=True."
                )

    def fit(self, X, y=None):
        self._validate_params()

        if not isinstance(X, pd.DataFrame):
            raise TypeError(f"ArnioCleaner requires a pandas DataFrame, got {type(X)}")

        self._validate_steps_contract()

        self.feature_names_in_ = np.array(X.columns, dtype=object)
        self.n_features_in_ = X.shape[1]

        if self.allow_schema_changes and self.steps:
            X_probe = X.copy()
            ar_probe = from_pandas(X_probe)
            out_probe = to_pandas(run_pipeline(ar_probe, self.steps))
            self.feature_names_out_ = np.array(out_probe.columns, dtype=object)
        else:
            self.feature_names_out_ = self.feature_names_in_.copy()

        self.feature_dtypes_in_ = {col: str(X[col].dtype) for col in X.columns}
        return self

    def transform(self, X, y=None):
        self._validate_params()
        check_is_fitted(self, "n_features_in_")
        if not isinstance(X, pd.DataFrame):
            raise TypeError(f"ArnioCleaner requires a pandas DataFrame, got {type(X)}")

        if list(X.columns) != list(self.feature_names_in_):
            raise ValueError(
                "columns must match those seen during fit. "
                f"Expected {list(self.feature_names_in_)}, got {list(X.columns)}."
            )

        for col in X.columns:
            fitted = self.feature_dtypes_in_.get(col)
            current = str(X[col].dtype)
            if fitted and current != fitted:
                warnings.warn(
                    f"ArnioCleaner: column '{col}' dtype changed from '{fitted}' to '{current}'.",
                    UserWarning,
                    stacklevel=2,
                )

        X_in = X.copy() if self.copy else X
        cleaned = run_pipeline(from_pandas(X_in), self.steps)
        X_out = to_pandas(cleaned)

        if len(X_out) != len(X):
            if not self.allow_row_count_change:
                raise ValueError(
                    f"A pipeline step changed the row count from {len(X)} to {len(X_out)}. "
                    "Use allow_row_count_change=True to allow this."
                )
            X_out = X_out.reset_index(drop=True)
        else:
            X_out.index = X.index

        self.feature_names_out_ = np.array(X_out.columns, dtype=object)
        return X_out

    def get_feature_names_out(self, input_features=None):
        check_is_fitted(self, "feature_names_out_")
        if input_features is None:
            return self.feature_names_out_

        if len(input_features) != self.n_features_in_:
            raise ValueError(f"input_features should have length {self.n_features_in_}")
        if list(input_features) != list(self.feature_names_in_):
            raise ValueError("input_features must match columns seen during fit.")

        return self.feature_names_out_
