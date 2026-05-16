import pandas as pd
import pytest

# Skip this entire test suite if scikit-learn isn't installed
pytest.importorskip("sklearn")

from sklearn.pipeline import Pipeline
from arnio.integrations.sklearn import ArnioCleaner

def test_arniocleaner_dataframe_validation():
    cleaner = ArnioCleaner()
    
    with pytest.raises(TypeError):
        cleaner.fit([1, 2, 3])
        
    with pytest.raises(TypeError):
        cleaner.transform([1, 2, 3])

def test_arniocleaner_in_pipeline():
    df = pd.DataFrame({"A": [" data ", "here "], "B": [1, 2]})
    cleaner = ArnioCleaner(steps=[])
    pipe = Pipeline([("arnio_prep", cleaner)])
    
    result = pipe.fit_transform(df)
    
    assert isinstance(result, pd.DataFrame)
    assert result.index.equals(df.index)