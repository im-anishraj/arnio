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


class ArnioCleaner(BaseEstimator, TransformerMixin):
    """
    A scikit-learn compatible transformer that wraps the Arnio C++ pipeline.

    Example:
        >>> import pandas as pd
        >>> from sklearn.pipeline import Pipeline
        >>> from arnio.integrations.sklearn import ArnioCleaner
        >>>
        >>> df = pd.DataFrame({"A": [" dirty ", "data "], "B": [1, 2]})
        >>> pipe = Pipeline([("arnio_prep", ArnioCleaner(steps=[]))])
        >>> X_clean = pipe.fit_transform(df)
    """

    def __init__(self, steps=None, copy=True, allow_row_count_change=False):
        self.steps = steps if steps is not None else []
        self.copy = copy
        self.allow_row_count_change = allow_row_count_change

    def _validate_params(self):
        if not isinstance(self.copy, bool):
            raise TypeError("copy must be a bool")
        if not isinstance(self.allow_row_count_change, bool):
            raise TypeError("allow_row_count_change must be a bool")

    def fit(self, X, y=None):
        self._validate_params()
        if not isinstance(X, pd.DataFrame):
            raise TypeError(f"ArnioCleaner requires a pandas DataFrame, got {type(X)}")

        # Scikit-learn expectation: store feature names as a numpy array and
        # track feature count.
        self.feature_names_in_ = np.array(X.columns, dtype=object)
        self.n_features_in_ = X.shape[1]

        # Store column dtypes so transform() can warn when they change
        # between fit and transform (e.g. after a CSV round-trip).
        self.feature_dtypes_in_ = {col: str(X[col].dtype) for col in X.columns}
        self.feature_names_out_ = self.feature_names_in_.copy()

        return self

    def transform(self, X, y=None):
        # Scikit-learn expectation: ensure the estimator was fitted
        self._validate_params()
        check_is_fitted(self, "n_features_in_")

        if not isinstance(X, pd.DataFrame):
            raise TypeError(f"ArnioCleaner requires a pandas DataFrame, got {type(X)}")

        if list(X.columns) != list(self.feature_names_in_):
            raise ValueError(
                "ArnioCleaner transform input columns must match the columns seen "
                "during fit, including order."
            )

        # Warn when a column's dtype differs from what was seen in fit().
        # This is a warning-only signal — it does not block the transform —
        # because some pipelines intentionally apply dtype changes upstream.
        for col in X.columns:
            fitted_dtype = self.feature_dtypes_in_.get(col)
            current_dtype = str(X[col].dtype)
            if fitted_dtype is not None and current_dtype != fitted_dtype:
                warnings.warn(
                    f"ArnioCleaner: column '{col}' dtype changed from "
                    f"'{fitted_dtype}' (fit) to '{current_dtype}' (transform). "
                    f"This may cause unexpected behaviour in the Arnio pipeline.",
                    UserWarning,
                    stacklevel=2,
                )

        X_in = X.copy() if self.copy else X

        ar_frame = from_pandas(X_in)
        cleaned_ar_frame = run_pipeline(ar_frame, self.steps)
        X_out = to_pandas(cleaned_ar_frame)
        self.feature_names_out_ = np.array(X_out.columns, dtype=object)

        if len(X_out.index) != len(X.index):
            if not self.allow_row_count_change:
                raise ValueError(
                    "ArnioCleaner pipeline changed the row count during transform. "
                    "Pass allow_row_count_change=True to allow row-dropping steps."
                )
            X_out = X_out.reset_index(drop=True)
        elif not X_out.index.equals(X.index):
            X_out.index = X.index

        return X_out

    def get_feature_names_out(self, input_features=None):
        """Enable compatibility with ColumnTransformer workflows."""
        check_is_fitted(self, "n_features_in_")

        if input_features is None:
            return self.feature_names_out_

        if len(input_features) != self.n_features_in_:
            raise ValueError(
                f"input_features should have length equal to number of features "
                f"({self.n_features_in_}), got {len(input_features)}"
            )

        if list(input_features) != list(self.feature_names_in_):
            raise ValueError(
                "input_features must match the columns seen during fit, including order."
            )

        return self.feature_names_out_
