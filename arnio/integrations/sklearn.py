import pandas as pd
import pytest
from arnio.integrations.sklearn import ArnioCleaner


def test_basic_cleaning():
    df = pd.DataFrame({"A": [" dirty ", "data "], "B": [1, 2]})
    cleaner = ArnioCleaner(steps=[("strip_whitespace",)])
    result = cleaner.fit_transform(df)
    assert list(result.columns) == ["A", "B"]


def test_strict_mode_rejects_schema_change():
    df = pd.DataFrame({"A": [1, 2]})
    cleaner = ArnioCleaner(steps=[("rename_columns", {"A": "newA"})])
    with pytest.raises(ValueError):
        cleaner.fit(df)


def test_allow_schema_changes_mode():
    df = pd.DataFrame({"A": [1, 2], "B": [3, 4]})
    cleaner = ArnioCleaner(steps=[("rename_columns", {"A": "newA"})], allow_schema_changes=True)
    result = cleaner.fit_transform(df)
    assert list(result.columns) == ["newA", "B"]


def test_row_count_change_always_rejected():
    df = pd.DataFrame({"A": [1, None, 3]})
    cleaner = ArnioCleaner(steps=[("drop_nulls",)])
    with pytest.raises(ValueError):
        cleaner.fit(df)


def test_get_feature_names_out():
    df = pd.DataFrame({"A": [1, 2], "B": [3, 4]})
    cleaner = ArnioCleaner(steps=[("rename_columns", {"A": "X"})], allow_schema_changes=True)
    cleaner.fit(df)
    assert list(cleaner.get_feature_names_out()) == ["X", "B"]