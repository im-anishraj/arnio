import numpy as np
import pandas as pd
import pytest

pytest.importorskip("sklearn")

from sklearn.pipeline import Pipeline
from arnio.integrations.sklearn import ArnioCleaner

def test_arniocleaner_non_dataframe_input():
    cleaner = ArnioCleaner()
    # Test lists and numpy arrays fail safely
    with pytest.raises(TypeError, match="requires a pandas DataFrame"):
        cleaner.fit([[1, 2], [3, 4]])

    cleaner.fit(pd.DataFrame({"A": [1]}))
    with pytest.raises(TypeError, match="requires a pandas DataFrame"):
        cleaner.transform(np.array([[1], [2]]))

def test_arniocleaner_configured_steps():
    df = pd.DataFrame({"A": ["  dirty  ", "data "], "B": [1, 2]})

    cleaner = ArnioCleaner(steps=[("strip_whitespace",)])
    result = cleaner.fit_transform(df)

    assert result["A"].tolist() == ["dirty", "data"]

def test_arniocleaner_copy_behavior():
    df = pd.DataFrame({"A": ["  dirty  ", "data "]})

    # Test copy=True (default) ensures the original dataframe isn't mutated
    cleaner = ArnioCleaner(steps=[("strip_whitespace",)], copy=True)
    cleaner.fit_transform(df)

    # Original should still have spaces
    assert df.iloc[0, 0] == "  dirty  "

def test_arniocleaner_in_pipeline():
    df = pd.DataFrame({"A": [" data ", "here "], "B": [1, 2]})
    cleaner = ArnioCleaner(steps=[])
    pipe = Pipeline([("arnio_prep", cleaner)])

    result = pipe.fit_transform(df)

    assert isinstance(result, pd.DataFrame)
    assert result.index.equals(df.index)
    assert list(result.columns) == ["A", "B"]
    