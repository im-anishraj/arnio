import warnings

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


def test_arniocleaner_feature_names_out_tracks_dropped_columns():
    df = pd.DataFrame({"A": ["x", "y"], "B": [1, 2]})

    cleaner = ArnioCleaner(steps=[("drop_columns", {"columns": ["B"]})])
    cleaner.fit(df)
    result = cleaner.transform(df)

    assert list(result.columns) == ["A"]
    assert cleaner.get_feature_names_out().tolist() == ["A"]


def test_arniocleaner_feature_names_out_tracks_renamed_columns():
    df = pd.DataFrame({"A": ["x", "y"], "B": [1, 2]})

    cleaner = ArnioCleaner(steps=[("rename_columns", {"mapping": {"A": "name"}})])
    cleaner.fit(df)
    result = cleaner.transform(df)

    assert list(result.columns) == ["name", "B"]
    assert cleaner.get_feature_names_out(["A", "B"]).tolist() == ["name", "B"]


def test_arniocleaner_feature_names_out_rejects_wrong_input_features():
    df = pd.DataFrame({"A": ["x", "y"], "B": [1, 2]})

    cleaner = ArnioCleaner().fit(df)

    with pytest.raises(ValueError, match="input_features must match"):
        cleaner.get_feature_names_out(["B", "A"])


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

<<<<<<<<< Temporary merge branch 1

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


# --- Issue #1278: dtype drift warning in transform() ---


def test_arniocleaner_warns_on_dtype_change_in_transform():
    """transform() emits UserWarning when a column dtype changed since fit()."""
    train_df = pd.DataFrame({"age": [25, 30, 35], "score": [1.0, 2.0, 3.0]})
    # Simulate dtype drift: age is now object/string after a CSV round-trip
    test_df = pd.DataFrame({"age": ["25", "30", "35"], "score": [1.0, 2.0, 3.0]})

    cleaner = ArnioCleaner(steps=[])
    cleaner.fit(train_df)

    with pytest.warns(UserWarning, match="dtype changed"):
        cleaner.transform(test_df)


def test_arniocleaner_no_warning_when_dtypes_unchanged():
    """transform() emits no warning when dtypes match what was seen in fit()."""
    df = pd.DataFrame({"age": [25, 30, 35], "score": [1.0, 2.0, 3.0]})

    cleaner = ArnioCleaner(steps=[])
    cleaner.fit(df)

    # Should complete without any warning
    with warnings.catch_warnings():
        warnings.simplefilter("error", UserWarning)
        cleaner.transform(df)


def test_arniocleaner_dtype_warning_names_the_changed_column():
    """The UserWarning message names the specific column that changed dtype."""
    train_df = pd.DataFrame({"id": [1, 2], "value": [10, 20]})
    test_df = pd.DataFrame({"id": ["1", "2"], "value": [10, 20]})

    cleaner = ArnioCleaner(steps=[])
    cleaner.fit(train_df)

    with pytest.warns(UserWarning, match="'id'"):
        cleaner.transform(test_df)


def test_arniocleaner_dtype_warning_does_not_block_transform():
    """transform() still returns a result even when a dtype warning is emitted."""
    train_df = pd.DataFrame({"score": [1, 2, 3]})
    test_df = pd.DataFrame({"score": ["1", "2", "3"]})

    cleaner = ArnioCleaner(steps=[])
    cleaner.fit(train_df)

    with pytest.warns(UserWarning):
        result = cleaner.transform(test_df)

    assert isinstance(result, pd.DataFrame)
    assert result.shape == test_df.shape


def test_arniocleaner_fit_stores_feature_dtypes():
    """fit() stores feature_dtypes_in_ for every column."""
    df = pd.DataFrame({"a": [1, 2], "b": [1.0, 2.0], "c": ["x", "y"]})
    cleaner = ArnioCleaner(steps=[])
    cleaner.fit(df)

    assert hasattr(cleaner, "feature_dtypes_in_")
    assert cleaner.feature_dtypes_in_["a"] == str(df["a"].dtype)
    assert cleaner.feature_dtypes_in_["b"] == str(df["b"].dtype)
    assert cleaner.feature_dtypes_in_["c"] == str(df["c"].dtype)


def test_arniocleaner_warns_for_multiple_dtype_changes():
    """A warning is emitted for each column that changed dtype."""
    train_df = pd.DataFrame({"a": [1, 2], "b": [3, 4]})
    test_df = pd.DataFrame({"a": ["1", "2"], "b": ["3", "4"]})

    cleaner = ArnioCleaner(steps=[])
    cleaner.fit(train_df)

    with pytest.warns(UserWarning) as record:
        cleaner.transform(test_df)

    # One warning per changed column
    assert len(record) == 2
    messages = {str(w.message) for w in record}
    assert any("'a'" in m for m in messages)
    assert any("'b'" in m for m in messages)
=========
def test_arniocleaner_rejects_non_boolean_options():
    """Ensure constructor explicitly blocks truthy/falsy non-boolean values."""
    invalid_values = ["false", "True", 1, 0, None, [], {}]    
    for value in invalid_values:
        with pytest.raises(TypeError, match="copy must be a bool"):
            ArnioCleaner(copy=value)
        with pytest.raises(TypeError, match="allow_row_count_change must be a bool"):
            ArnioCleaner(allow_row_count_change=value)
>>>>>>>>> Temporary merge branch 2
