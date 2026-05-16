"""Scikit-learn integration for Arnio's data preparation engine."""

import pandas as pd

# Fail gracefully if scikit-learn isn't installed in the current environment
try:
    from sklearn.base import BaseEstimator, TransformerMixin
except ImportError:
    raise ImportError(
        "The 'scikit-learn' package is required to use ArnioCleaner. "
        "Install it with: pip install scikit-learn"
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
        self.feature_names_in_ = None
        
    def fit(self, X, y=None):
        if not isinstance(X, pd.DataFrame):
            raise TypeError(f"ArnioCleaner requires a pandas DataFrame, got {type(X)}")
            
        # Store input features for get_feature_names_out compliance
        self.feature_names_in_ = X.columns.tolist()
        return self
        
    def transform(self, X, y=None):
        if not isinstance(X, pd.DataFrame):
            raise TypeError(f"ArnioCleaner requires a pandas DataFrame, got {type(X)}")
            
        # Prevent mutating the user's original data
        X_in = X.copy() if self.copy else X
        
        # Execute the Arnio C++ pipeline
        ar_frame = from_pandas(X_in)
        cleaned_ar_frame = run_pipeline(ar_frame, self.steps)
        X_out = to_pandas(cleaned_ar_frame)
            
        # Ensure the pandas index survives the C++ conversion roundtrip
        if not X_out.index.equals(X.index):
            X_out.index = X.index
            
        return X_out

    def get_feature_names_out(self, input_features=None):
        return self.feature_names_in_