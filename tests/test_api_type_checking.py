import pandas as pd
import pytest

import arnio as ar


def test_to_pandas_raises_type_error_for_non_arframe():
    # Attempting to call to_pandas with a normal pandas DataFrame or other object
    df = pd.DataFrame({"a": [1, 2, 3]})
    with pytest.raises(TypeError):
        ar.to_pandas(df)

    with pytest.raises(TypeError):
        ar.to_pandas([1, 2, 3])


def test_profile_raises_type_error_for_non_arframe():
    df = pd.DataFrame({"a": [1, 2, 3]})
    with pytest.raises(TypeError):
        ar.profile(df)

    with pytest.raises(TypeError):
        ar.profile("not an arframe")


def test_auto_clean_raises_type_error_for_non_arframe():
    df = pd.DataFrame({"a": [1, 2, 3]})
    with pytest.raises(TypeError):
        ar.auto_clean(df)

    with pytest.raises(TypeError):
        ar.auto_clean(123)
