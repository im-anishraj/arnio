"""Tests for the pipeline function."""

import pytest

import arnio as ar


class TestPipeline:
    def test_single_step(self, csv_with_nulls):
        frame = ar.read_csv(csv_with_nulls)
        result = ar.pipeline(
            frame,
            [
                ("drop_nulls",),
            ],
        )
        assert result.shape[0] < frame.shape[0]

    def test_multi_step(self, csv_with_whitespace):
        frame = ar.read_csv(csv_with_whitespace)
        result = ar.pipeline(
            frame,
            [
                ("strip_whitespace",),
                ("normalize_case", {"case_type": "lower"}),
            ],
        )
        df = ar.to_pandas(result)
        assert df["name"].iloc[0] == "alice"

    def test_full_pipeline(self, csv_with_nulls):
        frame = ar.read_csv(csv_with_nulls)
        result = ar.pipeline(
            frame,
            [
                ("drop_nulls",),
                ("strip_whitespace",),
                ("drop_duplicates",),
            ],
        )
        assert isinstance(result, ar.ArFrame)
        assert result.shape[0] <= frame.shape[0]

    def test_pipeline_with_kwargs(self, csv_with_duplicates):
        frame = ar.read_csv(csv_with_duplicates)
        result = ar.pipeline(
            frame,
            [
                ("drop_duplicates", {"keep": "last"}),
            ],
        )
        assert result.shape[0] == 3

    def test_pipeline_drop_constant_columns(self):
        import pandas as pd

        frame = ar.from_pandas(
            pd.DataFrame(
                {
                    "constant": [1, 1, 1],
                    "value": [1, 2, 1],
                }
            )
        )

        result = ar.pipeline(
            frame,
            [
                ("drop_constant_columns",),
            ],
        )
        df = ar.to_pandas(result)

        assert list(df.columns) == ["value"]
        assert list(df["value"]) == [1, 2, 1]

    def test_pipeline_clip_numeric(self):
        import pandas as pd

        frame = ar.from_pandas(
            pd.DataFrame(
                {
                    "value": [-5, 2, 10],
                    "label": ["a", "b", "c"],
                }
            )
        )

        result = ar.pipeline(
            frame,
            [
                ("clip_numeric", {"lower": 0, "upper": 5}),
            ],
        )
        df = ar.to_pandas(result)

        assert list(df["value"]) == [0, 2, 5]
        assert list(df["label"]) == ["a", "b", "c"]

    def test_pipeline_mapping_shorthand(self, sample_csv):
        frame = ar.read_csv(sample_csv)
        result = ar.pipeline(
            frame,
            [
                ("cast_types", {"age": "float64"}),
                ("rename_columns", {"age": "years"}),
            ],
        )

        assert result.dtypes["years"] == "float64"
        assert "age" not in result.columns

    def test_pipeline_mapping_keyword_form(self, sample_csv):
        frame = ar.read_csv(sample_csv)
        result = ar.pipeline(
            frame,
            [
                ("cast_types", {"mapping": {"age": "float64"}}),
                ("rename_columns", {"mapping": {"age": "years"}}),
            ],
        )

        assert result.dtypes["years"] == "float64"
        assert "age" not in result.columns

    def test_pipeline_validate_columns_exist(self, sample_csv):
        frame = ar.read_csv(sample_csv)
        result = ar.pipeline(
            frame,
            [
                ("validate_columns_exist", {"columns": ["name", "age"]}),
                ("strip_whitespace", {"subset": ["name"]}),
            ],
        )

        assert result.shape == frame.shape

    def test_pipeline_validate_columns_exist_allows_empty_columns(self, sample_csv):
        frame = ar.read_csv(sample_csv)
        result = ar.pipeline(frame, [("validate_columns_exist", {"columns": []})])

        assert result is frame

    def test_pipeline_validate_columns_exist_rejects_missing_columns(self, sample_csv):
        import pytest

        frame = ar.read_csv(sample_csv)

        with pytest.raises(KeyError, match="Missing columns"):
            ar.pipeline(
                frame,
                [("validate_columns_exist", {"columns": ["missing"]})],
            )

    def test_pipeline_subset_step_rejects_missing_columns(self, sample_csv):
        import pytest

        frame = ar.read_csv(sample_csv)

        with pytest.raises(KeyError, match="Missing columns for strip_whitespace"):
            ar.pipeline(
                frame,
                [("strip_whitespace", {"subset": ["missing"]})],
            )

    def test_empty_pipeline(self, sample_csv):
        frame = ar.read_csv(sample_csv)
        result = ar.pipeline(frame, [])
        assert result.shape == frame.shape

    def test_invalid_step_name(self, sample_csv):
        frame = ar.read_csv(sample_csv)
        try:
            ar.pipeline(frame, [("nonexistent_op",)])
            assert False, "Should have raised UnknownStepError"
        except ar.UnknownStepError as e:
            assert "Unknown pipeline step" in str(e)

    def test_invalid_step_format(self, sample_csv):
        frame = ar.read_csv(sample_csv)
        try:
            ar.pipeline(frame, [("a", "b", "c")])
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "Invalid step format" in str(e)

    def test_invalid_step_kwargs(self, sample_csv):
        frame = ar.read_csv(sample_csv)
        try:
            ar.pipeline(frame, [("drop_nulls", "subset=name")])
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "Expected a dict" in str(e)


class TestUnregisterStep:
    def test_unregister_custom_step(self):
        def dummy(df, **kwargs):
            return df

        ar.register_step("temp_step", dummy)
        assert "temp_step" in ar.list_steps()
        ar.unregister_step("temp_step")
        assert "temp_step" not in ar.list_steps()

    def test_unregister_nonexistent_raises(self):
        with pytest.raises(ar.UnknownStepError):
            ar.unregister_step("does_not_exist")

    def test_unregister_builtin_raises(self):
        with pytest.raises(ValueError, match="Cannot unregister built-in"):
            ar.unregister_step("drop_nulls")

    def test_unregister_is_idempotent_after_register(self):
        def dummy(df, **kwargs):
            return df

        ar.register_step("temp_idempotent", dummy)
        ar.unregister_step("temp_idempotent")
        with pytest.raises(ar.UnknownStepError):
            ar.unregister_step("temp_idempotent")


def test_filter_rows_greater_than():
    import pandas as pd

    import arnio as ar

    df = pd.DataFrame({"age": [20, 30, 40]})

    frame = ar.from_pandas(df)

    result = ar.pipeline(
        frame, [("filter_rows", {"column": "age", "op": ">", "value": 25})]
    )

    result_df = ar.to_pandas(result)

    assert len(result_df) == 2
    assert list(result_df["age"]) == [30, 40]


def test_filter_rows_equal_string():
    import pandas as pd

    import arnio as ar

    df = pd.DataFrame({"name": ["Alice", "Bob", "Alice"]})

    frame = ar.from_pandas(df)

    result = ar.pipeline(
        frame, [("filter_rows", {"column": "name", "op": "==", "value": "Alice"})]
    )

    result_df = ar.to_pandas(result)

    assert list(result_df["name"]) == ["Alice", "Alice"]


def test_filter_rows_bool():
    import pandas as pd

    import arnio as ar

    df = pd.DataFrame({"active": [True, False, True]})

    frame = ar.from_pandas(df)

    result = ar.pipeline(
        frame, [("filter_rows", {"column": "active", "op": "==", "value": True})]
    )

    result_df = ar.to_pandas(result)

    assert list(result_df["active"]) == [True, True]


def test_filter_rows_invalid_operator():
    import pandas as pd
    import pytest

    import arnio as ar

    df = pd.DataFrame({"age": [20, 30]})

    frame = ar.from_pandas(df)

    with pytest.raises(ValueError):
        ar.pipeline(
            frame, [("filter_rows", {"column": "age", "op": "invalid", "value": 25})]
        )


def test_filter_rows_direct_api():
    import pandas as pd

    import arnio as ar

    df = pd.DataFrame({"age": [20, 30, 40]})

    frame = ar.from_pandas(df)

    result = ar.filter_rows(frame, column="age", op=">", value=25)

    result_df = ar.to_pandas(result)

    assert list(result_df["age"]) == [30, 40]


def test_round_numeric_columns_pipeline():
    import pandas as pd

    import arnio as ar

    df = pd.DataFrame({"price": [10.555, 20.123]})
    frame = ar.from_pandas(df)

    result = ar.pipeline(
        frame, [("round_numeric_columns", {"subset": ["price"], "decimals": 2})]
    )

    result_df = ar.to_pandas(result)
    assert list(result_df["price"]) == [10.56, 20.12]


def test_safe_divide_columns_pipeline():
    import pandas as pd

    import arnio as ar

    df = pd.DataFrame({"revenue": [100.0, 200.0, 0.0], "cost": [50.0, 0.0, 30.0]})

    frame = ar.from_pandas(df)

    result = ar.pipeline(
        frame,
        [
            (
                "safe_divide_columns",
                {
                    "numerator": "revenue",
                    "denominator": "cost",
                    "output_column": "ratio",
                },
            )
        ],
    )

    result_df = ar.to_pandas(result)
    assert result_df["ratio"].iloc[0] == 2.0
    assert result_df["ratio"].iloc[1] == 0.0  # division by zero → fill_value
    assert result_df["ratio"].iloc[2] == 0.0  # zero numerator
