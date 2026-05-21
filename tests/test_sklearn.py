import numpy as np
import pandas as pd
import pytest

pytest.importorskip("sklearn")

from sklearn.pipeline import Pipeline  # noqa: E402

from arnio.integrations.sklearn import ArnioCleaner  # noqa: E402


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


def test_arniocleaner_rejects_row_dropping_by_default():
    df = pd.DataFrame({"name": ["Alice", None], "age": [30, 40]})

    cleaner = ArnioCleaner(steps=[("drop_nulls",)])

    with pytest.raises(ValueError, match="changed the row count"):
        cleaner.fit_transform(df)


def test_arniocleaner_allows_row_dropping_when_enabled():
    df = pd.DataFrame({"name": ["Alice", None], "age": [30, 40]}, index=[10, 20])

    cleaner = ArnioCleaner(
        steps=[("drop_nulls",)],
        allow_row_count_change=True,
    )
    result = cleaner.fit_transform(df)

    assert len(result) == 1
    assert list(result.index) == [0]
    assert result.iloc[0]["name"] == "Alice"


def test_arniocleaner_rejects_transform_column_order_mismatch():
    train = pd.DataFrame({"A": [" x "], "B": [1]})
    test = pd.DataFrame({"B": [1], "A": [" x "]})

    cleaner = ArnioCleaner(steps=[("strip_whitespace",)])
    cleaner.fit(train)

    with pytest.raises(ValueError, match="columns must match"):
        cleaner.transform(test)


def test_arniocleaner_rejects_transform_with_renamed_column():
    train = pd.DataFrame({"A": [" x "], "B": [1]})
    test = pd.DataFrame({"A": [" x "], "C": [1]})
    cleaner = ArnioCleaner(steps=[("strip_whitespace",)])
    cleaner.fit(train)
    with pytest.raises(ValueError, match="columns must match"):
        cleaner.transform(test)


def test_arniocleaner_rejects_transform_with_extra_columns():
    train = pd.DataFrame({"A": [" x "], "B": [1]})
    test = pd.DataFrame({"A": [" x "], "B": [1], "C": [2]})
    cleaner = ArnioCleaner(steps=[("strip_whitespace",)])
    cleaner.fit(train)
    with pytest.raises(ValueError, match="columns must match"):
        cleaner.transform(test)


def test_arniocleaner_rejects_transform_with_missing_columns():
    train = pd.DataFrame({"A": [" x "], "B": [1]})
    test = pd.DataFrame({"A": [" x "]})
    cleaner = ArnioCleaner(steps=[("strip_whitespace",)])
    cleaner.fit(train)
    with pytest.raises(ValueError, match="columns must match"):
        cleaner.transform(test)


# --- Issue: ArnioCleaner row-dropping pipeline behavior ---
# Tests added to cover drop_nulls and filter_rows changing row count
# as required by the acceptance criteria

def test_drop_nulls_changes_row_count_when_allowed():
    df = pd.DataFrame({"name": ["Alice", "Bob", None], "age": [30, 25, 40]})
    cleaner = ArnioCleaner(
        steps=[("drop_nulls",)],
        allow_row_count_change=True,
    )
    result = cleaner.fit_transform(df)
    assert len(result) == 2
    assert list(result["name"]) == ["Alice", "Bob"]


def test_filter_rows_changes_row_count_when_allowed():
    # filter_rows takes column, op, value as separate kwargs
    df = pd.DataFrame({"score": [10, 50, 90], "label": ["low", "mid", "high"]})
    cleaner = ArnioCleaner(
        steps=[("filter_rows", {"column": "score", "op": ">", "value": 20})],
        allow_row_count_change=True,
    )
    result = cleaner.fit_transform(df)
    assert len(result) == 2
    assert list(result["label"]) == ["mid", "high"]


def test_drop_nulls_rejects_row_count_change_by_default():
    # drop_nulls without allow_row_count_change=True must raise ValueError
    df = pd.DataFrame({"name": ["Alice", None], "age": [30, 40]})
    cleaner = ArnioCleaner(steps=[("drop_nulls",)])
    with pytest.raises(ValueError, match="changed the row count"):
        cleaner.fit_transform(df)


def test_filter_rows_rejects_row_count_change_by_default():
    # filter_rows without allow_row_count_change=True must raise ValueError
    df = pd.DataFrame({"score": [10, 50, 90]})
    cleaner = ArnioCleaner(
        steps=[("filter_rows", {"column": "score", "op": ">", "value": 20})]
    )
    with pytest.raises(ValueError, match="changed the row count"):
        cleaner.fit_transform(df)