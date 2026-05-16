"""Scikit-learn integration for Arnio's data preparation engine."""

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

    def __init__(self, steps=None, copy=True):
        self.steps = steps if steps is not None else []
        self.copy = copy

    def fit(self, X, y=None):
        if not isinstance(X, pd.DataFrame):
            raise TypeError(f"ArnioCleaner requires a pandas DataFrame, got {type(X)}")

        # Scikit-learn expectation: store feature names as a numpy array and track feature count
        self.feature_names_in_ = np.array(X.columns, dtype=object)
        self.n_features_in_ = X.shape[1]
        return self

    def transform(self, X, y=None):
        # Scikit-learn expectation: ensure the estimator was fitted
        check_is_fitted(self, "n_features_in_")

        if not isinstance(X, pd.DataFrame):
            raise TypeError(f"ArnioCleaner requires a pandas DataFrame, got {type(X)}")

        X_in = X.copy() if self.copy else X

        ar_frame = from_pandas(X_in)
        cleaned_ar_frame = run_pipeline(ar_frame, self.steps)
        X_out = to_pandas(cleaned_ar_frame)

        if not X_out.index.equals(X.index):
            X_out.index = X.index

        return X_out

    def get_feature_names_out(self, input_features=None):
        """Enable compatibility with ColumnTransformer workflows."""
        check_is_fitted(self, "n_features_in_")

        if input_features is None:
            return self.feature_names_in_

        if len(input_features) != self.n_features_in_:
            raise ValueError(
                f"input_features should have length equal to number of features "
                f"({self.n_features_in_}), got {len(input_features)}"
            )

        return np.asarray(input_features, dtype=object)
    