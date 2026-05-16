"""Tests for the pipeline function."""

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


def test_pipeline_normalize_unicode():
    import pandas as pd

    import arnio as ar

    df = pd.DataFrame({"text": ["café"]})

    frame = ar.from_pandas(df)

    result = ar.pipeline(
        frame,
        [
            ("normalize_unicode",),
        ],
    )

    result_df = ar.to_pandas(result)

    assert result_df["text"].iloc[0] == "café"


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
            ),
        ],
    )

    result_df = ar.to_pandas(result)

    assert result_df["ratio"].iloc[0] == 2.0
    assert result_df["ratio"].iloc[1] == 0.0  # division by zero → fill_value
    assert result_df["ratio"].iloc[2] == 0.0  # zero numerator
