import pandas as pd
import pytest
from arnio.integrations.sklearn import ArnioCleaner

<<<<<<< HEAD
def test_basic_cleaning():
    df = pd.DataFrame({"A": [" dirty ", "data "], "B": [1, 2]})
    cleaner = ArnioCleaner(steps=[("strip_whitespace",)])
    result = cleaner.fit_transform(df)
=======
pytest.importorskip("sklearn")

from sklearn.pipeline import Pipeline  # noqa: E402

from arnio.integrations.sklearn import ArnioCleaner  # noqa: E402


def test_arniocleaner_non_dataframe_input():
    cleaner = ArnioCleaner()
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
    cleaner = ArnioCleaner(steps=[("strip_whitespace",)], copy=True)
    cleaner.fit_transform(df)
    assert df.iloc[0, 0] == "  dirty  "


def test_arniocleaner_in_pipeline():
    df = pd.DataFrame({"A": [" data ", "here "], "B": [1, 2]})
    cleaner = ArnioCleaner(steps=[])
    pipe = Pipeline([("arnio_prep", cleaner)])
    result = pipe.fit_transform(df)
    assert isinstance(result, pd.DataFrame)
    assert result.index.equals(df.index)
>>>>>>> 46a44f5 (feat(sklearn): enforce schema-stability contract in ArnioCleaner (#946))
    assert list(result.columns) == ["A", "B"]

def test_strict_mode_rejects_schema_change():
    df = pd.DataFrame({"A": [1, 2]})
    cleaner = ArnioCleaner(steps=[("rename_columns", {"A": "newA"})])
    with pytest.raises(ValueError):
        cleaner.fit(df)

<<<<<<< HEAD
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
=======
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


def test_strict_drop_nulls_rejected_at_fit():
    df = pd.DataFrame({"name": ["Alice", None], "age": [30, 40]})
    cleaner = ArnioCleaner(steps=[("drop_nulls",)])
    with pytest.raises(ValueError, match="row-count-changing"):
        cleaner.fit(df)


def test_strict_drop_duplicates_rejected_at_fit():
    df = pd.DataFrame({"x": [1, 1, 2]})
    cleaner = ArnioCleaner(steps=[("drop_duplicates",)])
    with pytest.raises(ValueError, match="row-count-changing"):
        cleaner.fit(df)


def test_strict_filter_rows_rejected_at_fit():
    df = pd.DataFrame({"score": [10, 50, 90]})
    cleaner = ArnioCleaner(
        steps=[("filter_rows", {"column": "score", "op": ">", "value": 20})]
    )
    with pytest.raises(ValueError, match="row-count-changing"):
        cleaner.fit(df)


def test_strict_keep_rows_with_nulls_rejected_at_fit():
    df = pd.DataFrame({"a": [1, None, 3]})
    cleaner = ArnioCleaner(steps=[("keep_rows_with_nulls",)])
    with pytest.raises(ValueError, match="row-count-changing"):
        cleaner.fit(df)


def test_strict_rename_columns_rejected():
    df = pd.DataFrame({"A": [1, 2], "B": [3, 4]})
    cleaner = ArnioCleaner(steps=[("rename_columns", {"A": "alpha"})])
    with pytest.raises(ValueError, match="allow_schema_changes"):
        cleaner.fit(df)


def test_strict_drop_columns_rejected():
    df = pd.DataFrame({"A": [1, 2], "B": [3, 4]})
    cleaner = ArnioCleaner(steps=[("drop_columns", {"columns": ["B"]})])
    with pytest.raises(ValueError, match="allow_schema_changes"):
        cleaner.fit(df)


def test_strict_drop_constant_columns_rejected():
    df = pd.DataFrame({"A": [1, 1], "B": [2, 3]})
    cleaner = ArnioCleaner(steps=[("drop_constant_columns",)])
    with pytest.raises(ValueError, match="allow_schema_changes"):
        cleaner.fit(df)


def test_strict_combine_columns_rejected():
    df = pd.DataFrame({"first": ["John", "Jane"], "last": ["Doe", "Smith"]})
    cleaner = ArnioCleaner(
        steps=[
            (
                "combine_columns",
                {
                    "subset": ["first", "last"],
                    "output_column": "full_name",
                    "separator": " ",
                },
            )
        ]
    )
    with pytest.raises(ValueError, match="allow_schema_changes"):
        cleaner.fit(df)


def test_strict_strip_whitespace_allowed():
    df = pd.DataFrame({"A": [" dirty ", "data "], "B": [1, 2]})
    cleaner = ArnioCleaner(steps=[("strip_whitespace",)])
    result = cleaner.fit_transform(df)
    assert result["A"].tolist() == ["dirty", "data"]
    assert list(result.columns) == ["A", "B"]


def test_strict_fill_nulls_allowed():
    df = pd.DataFrame({"A": [1.0, None, 3.0]})
    cleaner = ArnioCleaner(steps=[("fill_nulls", {"value": 0})])
    result = cleaner.fit_transform(df)
    assert result["A"].tolist() == [1.0, 0.0, 3.0]


def test_strict_normalize_case_allowed():
    df = pd.DataFrame({"name": ["ALICE", "Bob"]})
    cleaner = ArnioCleaner(steps=[("normalize_case",)])
    result = cleaner.fit_transform(df)
    assert result["name"].tolist() == ["alice", "bob"]


def test_strict_get_feature_names_out_returns_input_columns():
    df = pd.DataFrame({"A": [1, 2], "B": [3, 4]})
    cleaner = ArnioCleaner(steps=[("strip_whitespace",)])
    cleaner.fit(df)
    assert list(cleaner.get_feature_names_out()) == ["A", "B"]


def test_optIn_row_count_still_rejected_drop_nulls():
    df = pd.DataFrame({"name": ["Alice", None], "age": [30, 40]})
    cleaner = ArnioCleaner(steps=[("drop_nulls",)], allow_schema_changes=True)
    with pytest.raises(ValueError, match="row-count-changing"):
        cleaner.fit(df)


def test_optIn_row_count_still_rejected_filter_rows():
    df = pd.DataFrame({"score": [10, 50, 90]})
    cleaner = ArnioCleaner(
        steps=[("filter_rows", {"column": "score", "op": ">", "value": 20})],
        allow_schema_changes=True,
    )
    with pytest.raises(ValueError, match="row-count-changing"):
        cleaner.fit(df)


def test_optIn_rename_columns_allowed():
    df = pd.DataFrame({"A": [1, 2], "B": [3, 4]})
    cleaner = ArnioCleaner(
        steps=[("rename_columns", {"A": "alpha"})],
        allow_schema_changes=True,
    )
    result = cleaner.fit_transform(df)
    assert list(result.columns) == ["alpha", "B"]


def test_optIn_drop_columns_allowed():
    df = pd.DataFrame({"A": [1, 2], "B": [3, 4], "C": [5, 6]})
    cleaner = ArnioCleaner(
        steps=[("drop_columns", {"columns": ["C"]})],
        allow_schema_changes=True,
    )
    result = cleaner.fit_transform(df)
    assert list(result.columns) == ["A", "B"]


def test_optIn_drop_constant_columns_allowed():
    df = pd.DataFrame({"A": [1, 1, 1], "B": [2, 3, 4]})
    cleaner = ArnioCleaner(
        steps=[("drop_constant_columns",)],
        allow_schema_changes=True,
    )
    result = cleaner.fit_transform(df)
    assert list(result.columns) == ["B"]


def test_optIn_combine_columns_allowed():
    df = pd.DataFrame({"first": ["John", "Jane"], "last": ["Doe", "Smith"]})
    cleaner = ArnioCleaner(
        steps=[
            (
                "combine_columns",
                {
                    "subset": ["first", "last"],
                    "output_column": "full_name",
                    "separator": " ",
                },
            )
        ],
        allow_schema_changes=True,
    )
    result = cleaner.fit_transform(df)
    assert "full_name" in result.columns
    assert result["full_name"].tolist() == ["John Doe", "Jane Smith"]


def test_optIn_get_feature_names_out_after_rename():
    df = pd.DataFrame({"A": [1, 2], "B": [3, 4]})
    cleaner = ArnioCleaner(
        steps=[("rename_columns", {"A": "alpha"})],
        allow_schema_changes=True,
    )
    cleaner.fit(df)
    assert list(cleaner.get_feature_names_out()) == ["alpha", "B"]


def test_optIn_get_feature_names_out_after_drop():
    df = pd.DataFrame({"A": [1, 2], "B": [3, 4], "C": [5, 6]})
    cleaner = ArnioCleaner(
        steps=[("drop_columns", {"columns": ["C"]})],
        allow_schema_changes=True,
    )
    cleaner.fit(df)
    assert list(cleaner.get_feature_names_out()) == ["A", "B"]


def test_optIn_get_feature_names_out_after_drop_constant():
    df = pd.DataFrame({"A": [1, 1, 1], "B": [2, 3, 4]})
    cleaner = ArnioCleaner(
        steps=[("drop_constant_columns",)],
        allow_schema_changes=True,
    )
    cleaner.fit(df)
    assert list(cleaner.get_feature_names_out()) == ["B"]


def test_optIn_get_feature_names_out_after_combine():
    df = pd.DataFrame({"first": ["John", "Jane"], "last": ["Doe", "Smith"]})
    cleaner = ArnioCleaner(
        steps=[
            (
                "combine_columns",
                {
                    "subset": ["first", "last"],
                    "output_column": "full_name",
                    "separator": " ",
                },
            )
        ],
        allow_schema_changes=True,
    )
    cleaner.fit(df)
    out = list(cleaner.get_feature_names_out())
    assert "full_name" in out
    assert "first" in out and "last" in out


def test_get_feature_names_out_mismatched_input_features():
    df = pd.DataFrame({"A": [1, 2], "B": [3, 4]})
    cleaner = ArnioCleaner(steps=[("strip_whitespace",)])
    cleaner.fit(df)
    with pytest.raises(ValueError):
        cleaner.get_feature_names_out(input_features=["A", "B", "C"])
>>>>>>> 46a44f5 (feat(sklearn): enforce schema-stability contract in ArnioCleaner (#946))
