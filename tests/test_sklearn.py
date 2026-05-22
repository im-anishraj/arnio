import warnings

import numpy as np
import pandas as pd
import pytest

pytest.importorskip("sklearn")

from sklearn.pipeline import Pipeline  # noqa: E402

from arnio.integrations.sklearn import ArnioCleaner  # noqa: E402


# ===========================================================================
# Original tests (kept, updated to match new contract)
# ===========================================================================

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
    assert list(result.columns) == ["A", "B"]


<<<<<<< HEAD
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


=======
>>>>>>> 8e5471d (feat(sklearn): enforce schema-stability contract in ArnioCleaner (#946))
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


# ===========================================================================
# Issue #946 – ArnioCleaner schema-stability contract
# ===========================================================================
# Policy (chosen by maintainer):
#   • Row-count changes  → ALWAYS rejected at fit() in BOTH modes
#   • Column schema changes → rejected by default (strict mode),
#                             allowed only with allow_schema_changes=True
#   • get_feature_names_out() → reflects final columns in opt-in mode


# ---------------------------------------------------------------------------
# STRICT MODE (default): row-count-changing steps rejected at fit()
# ---------------------------------------------------------------------------

def test_strict_drop_nulls_rejected_at_fit():
    """drop_nulls must raise at fit() because it may change row count."""
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
<<<<<<< HEAD
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


def test_arniocleaner_rejects_non_boolean_options():
    """Ensure non-boolean values are rejected at fit/transform, not construction."""
    df = pd.DataFrame({"A": [1, 2, 3]})
    invalid_values = ["false", "True", 1, 0, None, [], {}]
    for value in invalid_values:
        with pytest.raises(TypeError, match="copy must be a bool"):
            ArnioCleaner(copy=value).fit(df)
        with pytest.raises(TypeError, match="allow_row_count_change must be a bool"):
            ArnioCleaner(allow_row_count_change=value).fit(df)


def test_arniocleaner_construction_with_invalid_params_does_not_raise():
    # Construction must succeed even with invalid types (sklearn convention)
    cleaner = ArnioCleaner(copy="yes")
    assert cleaner.copy == "yes"
    cleaner2 = ArnioCleaner(allow_row_count_change=1)
    assert cleaner2.allow_row_count_change == 1


def test_arniocleaner_clone_with_invalid_params_does_not_raise():
    # sklearn clone() must work without triggering validation
    from sklearn.base import clone

    cleaner = ArnioCleaner(copy="yes")
    cloned = clone(cleaner)
    assert cloned.copy == "yes"
=======
    with pytest.raises(ValueError, match="row-count-changing"):
        cleaner.fit(df)


def test_strict_keep_rows_with_nulls_rejected_at_fit():
    df = pd.DataFrame({"a": [1, None, 3]})
    cleaner = ArnioCleaner(steps=[("keep_rows_with_nulls",)])
    with pytest.raises(ValueError, match="row-count-changing"):
        cleaner.fit(df)


# ---------------------------------------------------------------------------
# STRICT MODE: column-schema-changing steps rejected at fit()
# ---------------------------------------------------------------------------

def test_strict_rename_columns_rejected():
    df = pd.DataFrame({"A": [1, 2], "B": [3, 4]})
    cleaner = ArnioCleaner(steps=[("rename_columns", {"A": "alpha"})],)
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
    """combine_columns adds a column – rejected in strict mode."""
    df = pd.DataFrame({"first": ["John", "Jane"], "last": ["Doe", "Smith"]})
    cleaner = ArnioCleaner(
        steps=[
            (
                "combine_columns",
                {"subset": ["first", "last"], "output_column": "full_name", "separator": " "},
            )
        ]
    )
    with pytest.raises(ValueError, match="allow_schema_changes"):
        cleaner.fit(df)


def test_strict_trim_column_names_rejected():
    df = pd.DataFrame({" A ": [1, 2], "B ": [3, 4]})
    cleaner = ArnioCleaner(steps=[("trim_column_names",)])
    with pytest.raises(ValueError, match="allow_schema_changes"):
        cleaner.fit(df)


# ---------------------------------------------------------------------------
# STRICT MODE: schema-preserving steps pass cleanly
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# OPT-IN MODE (allow_schema_changes=True): row-count STILL rejected
# ---------------------------------------------------------------------------

def test_optIn_row_count_still_rejected_drop_nulls():
    """Row-count-changing steps are always rejected, even in opt-in mode."""
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


# ---------------------------------------------------------------------------
# OPT-IN MODE: column-schema-changing steps allowed
# ---------------------------------------------------------------------------

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
    """drop_constant_columns drops the all-same column A."""
    df = pd.DataFrame({"A": [1, 1, 1], "B": [2, 3, 4]})
    cleaner = ArnioCleaner(
        steps=[("drop_constant_columns",)],
        allow_schema_changes=True,
    )
    result = cleaner.fit_transform(df)
    assert list(result.columns) == ["B"]


def test_optIn_combine_columns_allowed():
    """combine_columns appends a new column – allowed in opt-in mode."""
    df = pd.DataFrame({"first": ["John", "Jane"], "last": ["Doe", "Smith"]})
    cleaner = ArnioCleaner(
        steps=[
            (
                "combine_columns",
                {"subset": ["first", "last"], "output_column": "full_name", "separator": " "},
            )
        ],
        allow_schema_changes=True,
    )
    result = cleaner.fit_transform(df)
    assert "full_name" in result.columns
    assert result["full_name"].tolist() == ["John Doe", "Jane Smith"]


# ---------------------------------------------------------------------------
# OPT-IN MODE: get_feature_names_out() reflects final transformed columns
# ---------------------------------------------------------------------------

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
                {"subset": ["first", "last"], "output_column": "full_name", "separator": " "},
            )
        ],
        allow_schema_changes=True,
    )
    cleaner.fit(df)
    out = list(cleaner.get_feature_names_out())
    assert "full_name" in out
    assert "first" in out and "last" in out
>>>>>>> 8e5471d (feat(sklearn): enforce schema-stability contract in ArnioCleaner (#946))
