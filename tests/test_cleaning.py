"""Tests for data cleaning functions."""

import locale as _locale
import re

import numpy as np
import pandas as pd
import pytest

import arnio as ar
from arnio import from_pandas, to_pandas
from arnio.cleaning import _validate_column_sequence, _validate_string_mapping


class TestDropNulls:
    def test_drop_all_nulls(self, csv_with_nulls):
        frame = ar.read_csv(csv_with_nulls)
        result = ar.drop_nulls(frame)
        assert result.shape[0] < frame.shape[0]
        # Only Alice and Diana have no nulls
        assert result.shape[0] == 2

    def test_drop_nulls_subset(self, csv_with_nulls):
        frame = ar.read_csv(csv_with_nulls)
        result = ar.drop_nulls(frame, subset=["name"])
        # Only row 2 has null name
        assert result.shape[0] == 3

    def test_drop_nulls_empty_subset_raises(self):
        frame = ar.from_pandas(pd.DataFrame({"name": ["Alice", None, "Charlie"]}))

        with pytest.raises(ValueError, match="subset"):
            ar.drop_nulls(frame, subset=[])

    def test_drop_nulls_pipeline_empty_subset_raises(self):
        frame = ar.from_pandas(pd.DataFrame({"name": ["Alice", None, "Charlie"]}))

        with pytest.raises(ValueError, match="subset"):
            ar.pipeline(frame, [("drop_nulls", {"subset": []})])

    def test_drop_nulls_subset_none_still_works(self):
        frame = ar.from_pandas(pd.DataFrame({"name": ["Alice", None, "Charlie"]}))

        result = ar.drop_nulls(frame)

        assert result.shape[0] == 2


class TestKeepRowsWithNulls:
    def test_pandas_input_empty_subset_raises(self):
        df = pd.DataFrame({"name": ["Alice", None]})

        with pytest.raises(ValueError, match="subset"):
            ar.keep_rows_with_nulls(df, subset=[])

    def test_pandas_input_empty_tuple_subset_raises(self):
        df = pd.DataFrame({"name": ["Alice", None]})

        with pytest.raises(ValueError, match="subset"):
            ar.keep_rows_with_nulls(df, subset=())

    def test_empty_subset_raises(self):
        frame = ar.from_pandas(pd.DataFrame({"name": ["Alice", None]}))

        with pytest.raises(ValueError, match="subset"):
            ar.keep_rows_with_nulls(frame, subset=[])

    def test_empty_tuple_subset_raises(self):
        frame = ar.from_pandas(pd.DataFrame({"name": ["Alice", None]}))

        with pytest.raises(ValueError, match="subset"):
            ar.keep_rows_with_nulls(frame, subset=())

    def test_subset_none_still_works(self):
        frame = ar.from_pandas(pd.DataFrame({"name": ["Alice", None]}))

        result = ar.keep_rows_with_nulls(frame)

        assert result.shape[0] == 1

    def test_keeps_only_null_rows(self, csv_with_nulls):
        # full frame has 4 rows, 2 have nulls (row1: null name+score, row2: null age)
        frame = ar.read_csv(csv_with_nulls)
        result = ar.keep_rows_with_nulls(frame)
        assert result.shape[0] == 2

    def test_no_nulls_returns_empty(self, sample_csv):
        # sample_csv has no nulls — result should be empty
        frame = ar.read_csv(sample_csv)
        result = ar.keep_rows_with_nulls(frame)
        assert result.shape[0] == 0

    def test_all_nulls_returns_all_rows(self, tmp_path):
        # every row has a null — all rows should be kept
        path = tmp_path / "all_nulls.csv"
        path.write_text("name,age\nAlice,\n,25\nCharlie,\n")
        frame = ar.read_csv(path)
        result = ar.keep_rows_with_nulls(frame)
        assert result.shape[0] == frame.shape[0]

    def test_subset_targets_specific_column(self, csv_with_nulls):
        # only checking 'age' column — only Charlie has null age
        frame = ar.read_csv(csv_with_nulls)
        result = ar.keep_rows_with_nulls(frame, subset=["age"])
        assert result.shape[0] == 1

    def test_subset_unknown_column_raises(self, csv_with_nulls):
        # passing a column that doesn't exist should raise ValueError
        frame = ar.read_csv(csv_with_nulls)
        with pytest.raises(KeyError):
            ar.keep_rows_with_nulls(frame, subset=["nonexistent"])

    def test_index_is_reset(self, csv_with_nulls):
        # returned frame should have clean 0-based index
        frame = ar.read_csv(csv_with_nulls)
        result = ar.keep_rows_with_nulls(frame)
        df = ar.to_pandas(result)
        assert list(df.index) == list(range(len(df)))

    def test_pipeline_usage(self, csv_with_nulls):
        # function should work correctly when called via pipeline
        frame = ar.read_csv(csv_with_nulls)
        result = ar.pipeline(
            frame,
            [
                ("keep_rows_with_nulls",),
            ],
        )
        assert result.shape[0] == 2

    def test_pipeline_subset(self, csv_with_nulls):
        # pipeline with subset parameter
        frame = ar.read_csv(csv_with_nulls)
        result = ar.pipeline(
            frame,
            [
                ("keep_rows_with_nulls", {"subset": ["age"]}),
            ],
        )
        assert result.shape[0] == 1

    def test_invalid_subset_string(self, csv_with_nulls):
        """keep_rows_with_nulls raises TypeError when subset is a string."""
        frame = ar.read_csv(csv_with_nulls)
        with pytest.raises(TypeError, match="must be a list"):
            ar.keep_rows_with_nulls(frame, subset="age")

    def test_missing_column_raises(self, csv_with_nulls):
        """keep_rows_with_nulls raises KeyError when subset column is missing."""
        frame = ar.read_csv(csv_with_nulls)
        with pytest.raises(KeyError, match="nonexistent"):
            ar.keep_rows_with_nulls(frame, subset=["nonexistent"])


class TestFillNulls:
    def test_fill_with_string(self, csv_with_nulls):
        frame = ar.read_csv(csv_with_nulls)
        result = ar.fill_nulls(frame, "N/A", subset=["name"])
        assert result.shape == frame.shape

    def test_fill_with_number(self, csv_with_nulls):
        frame = ar.read_csv(csv_with_nulls)
        result = ar.fill_nulls(frame, 0)
        assert result.shape == frame.shape

    def test_incompatible_fill_rejected(self, tmp_path):
        path = tmp_path / "numbers.csv"
        path.write_text("x,y\n1,a\n,b\n3,c\n")
        frame = ar.read_csv(path)

        with pytest.raises(ValueError, match="Fill value is incompatible"):
            ar.fill_nulls(frame, "bad", subset=["x"])

    def test_fill_nulls_rejects_unsupported_types(self):
        frame = ar.from_pandas(pd.DataFrame({"a": [1, None], "b": ["x", None]}))

        for bad_value in [[1, 2], {"key": "val"}, object()]:
            with pytest.raises(
                TypeError, match="fill value must be a supported scalar"
            ):
                ar.fill_nulls(frame, bad_value)

    def test_fill_nulls_accepts_valid_scalars(self):
        # numeric column → fill with numeric
        frame_num = ar.from_pandas(pd.DataFrame({"a": [1.0, None]}))
        for good_value in [0, 0.0]:
            result = ar.fill_nulls(frame_num, good_value)
            df = ar.to_pandas(result)
            assert (
                df["a"].isnull().sum() == 0
            ), f"Nulls remain after filling with {good_value!r}"

        # string column → fill with string
        frame_str = ar.from_pandas(pd.DataFrame({"b": ["x", None]}))
        result = ar.fill_nulls(frame_str, "missing")
        df = ar.to_pandas(result)
        assert df["b"].isnull().sum() == 0, "Nulls remain after filling with 'missing'"

    def test_fill_nulls_rejects_bool_for_int64_column(self):
        frame = ar.from_pandas(
            pd.DataFrame({"a": pd.array([1, None, 3], dtype="Int64")})
        )
        with pytest.raises(TypeError, match="bool"):
            ar.fill_nulls(frame, True)

    def test_fill_nulls_rejects_bool_for_float64_column(self):
        frame = ar.from_pandas(pd.DataFrame({"a": [1.0, None, 3.0]}))
        with pytest.raises(TypeError, match="bool"):
            ar.fill_nulls(frame, False)

    def test_fill_nulls_rejects_bool_via_subset(self):
        frame = ar.from_pandas(
            pd.DataFrame(
                {"a": pd.array([1, None, 3], dtype="Int64"), "b": ["x", None, "z"]}
            )
        )
        with pytest.raises(TypeError, match="bool"):
            ar.fill_nulls(frame, True, subset=["a"])

    def test_fill_nulls_bool_accepted_for_bool_column(self):
        frame = ar.from_pandas(pd.DataFrame({"a": [True, None, False]}))
        result = ar.fill_nulls(frame, False)
        assert result is not None


class TestWinsorizeOutliers:
    def test_winsorize_outliers_clips_numeric_values(self):
        frame = ar.from_pandas(
            pd.DataFrame(
                {
                    "value": [1, 2, 3, 4, 100],
                }
            )
        )

        result = ar.winsorize_outliers(frame, lower=0.2, upper=0.8)
        df = ar.to_pandas(result)

        assert df["value"].tolist() == pytest.approx([1.8, 2.0, 3.0, 4.0, 23.2])

    def test_winsorize_outliers_subset(self):
        frame = ar.from_pandas(
            pd.DataFrame(
                {
                    "a": [1, 2, 3, 4, 100],
                    "b": [10, 20, 30, 40, 500],
                }
            )
        )

        result = ar.winsorize_outliers(
            frame,
            lower=0.2,
            upper=0.8,
            subset=["a"],
        )
        df = ar.to_pandas(result)

        assert df["a"].tolist() == pytest.approx([1.8, 2.0, 3.0, 4.0, 23.2])
        assert list(df["b"]) == [10, 20, 30, 40, 500]

    def test_winsorize_outliers_ignores_non_numeric_without_subset(self):
        frame = ar.from_pandas(
            pd.DataFrame(
                {
                    "value": [1, 2, 3, 4, 100],
                    "label": ["a", "b", "c", "d", "e"],
                }
            )
        )

        result = ar.winsorize_outliers(frame, lower=0.2, upper=0.8)
        df = ar.to_pandas(result)

        assert df["value"].tolist() == pytest.approx([1.8, 2.0, 3.0, 4.0, 23.2])
        assert list(df["label"]) == ["a", "b", "c", "d", "e"]

    def test_winsorize_outliers_rejects_non_numeric_subset(self):
        frame = ar.from_pandas(
            pd.DataFrame(
                {
                    "value": [1, 2, 3],
                    "label": ["a", "b", "c"],
                }
            )
        )

        with pytest.raises(ValueError, match="only supports numeric columns"):
            ar.winsorize_outliers(frame, subset=["label"])

    def test_winsorize_outliers_rejects_unknown_subset_column(self):
        frame = ar.from_pandas(pd.DataFrame({"value": [1, 2, 3]}))

        with pytest.raises(ValueError, match="Unknown columns in subset"):
            ar.winsorize_outliers(frame, subset=["missing"])

    @pytest.mark.parametrize(
        ("lower", "upper"),
        [
            (-0.1, 0.95),
            (0.05, 1.1),
            (0.8, 0.2),
            (0.5, 0.5),
        ],
    )
    def test_winsorize_outliers_rejects_invalid_bounds(self, lower, upper):
        frame = ar.from_pandas(pd.DataFrame({"value": [1, 2, 3]}))

        with pytest.raises(ValueError):
            ar.winsorize_outliers(frame, lower=lower, upper=upper)

    def test_winsorize_outliers_rejects_boolean_bounds(self):
        frame = ar.from_pandas(pd.DataFrame({"value": [1, 2, 3]}))

        with pytest.raises(TypeError, match="'lower' must be an int or float"):
            ar.winsorize_outliers(frame, lower=True)

        with pytest.raises(TypeError, match="'upper' must be an int or float"):
            ar.winsorize_outliers(frame, upper=False)

    @pytest.mark.parametrize("value", ["0.1", None, object()])
    def test_winsorize_outliers_rejects_non_numeric_bounds(self, value):
        frame = ar.from_pandas(pd.DataFrame({"value": [1, 2, 3]}))

        with pytest.raises(TypeError, match="'lower' must be an int or float"):
            ar.winsorize_outliers(frame, lower=value)

    @pytest.mark.parametrize(
        "value",
        [float("nan"), float("inf"), float("-inf")],
    )
    def test_winsorize_outliers_rejects_non_finite_bounds(self, value):
        frame = ar.from_pandas(pd.DataFrame({"value": [1, 2, 3]}))

        with pytest.raises(ValueError, match="finite"):
            ar.winsorize_outliers(frame, lower=value)

    def test_winsorize_outliers_identical_values_noop(self):
        frame = ar.from_pandas(pd.DataFrame({"value": [5, 5, 5]}))

        result = ar.winsorize_outliers(frame)
        df = ar.to_pandas(result)

        assert list(df["value"]) == [5, 5, 5]

    def test_winsorize_outliers_single_row_noop(self):
        frame = ar.from_pandas(pd.DataFrame({"value": [10]}))

        result = ar.winsorize_outliers(frame)
        df = ar.to_pandas(result)

        assert list(df["value"]) == [10]

    def test_winsorize_outliers_empty_dataframe(self):
        frame = ar.from_pandas(pd.DataFrame({"value": pd.Series(dtype="float64")}))
        result = ar.winsorize_outliers(frame)
        df = ar.to_pandas(result)
        assert df.shape == (0, 1)

    def test_winsorize_outliers_all_nulls(self):
        frame = ar.from_pandas(pd.DataFrame({"value": [None, None, None]}))
        result = ar.winsorize_outliers(frame)
        df = ar.to_pandas(result)
        assert df["value"].isna().all()

    def test_winsorize_outliers_two_rows(self):
        frame = ar.from_pandas(pd.DataFrame({"value": [10.0, 20.0]}))
        result = ar.winsorize_outliers(frame, lower=0.1, upper=0.9)
        df = ar.to_pandas(result)
        assert df["value"].tolist() == pytest.approx([11.0, 19.0])


class TestValidateColumnsExist:
    def test_returns_original_frame_when_columns_exist(self, sample_csv):
        frame = ar.read_csv(sample_csv)

        result = ar.validate_columns_exist(frame, ["name", "age"])

        assert result is frame

    def test_allows_empty_column_list(self, sample_csv):
        frame = ar.read_csv(sample_csv)

        result = ar.validate_columns_exist(frame, [])

        assert result is frame

    def test_raises_clear_error_for_missing_columns(self, sample_csv):
        frame = ar.read_csv(sample_csv)

        with pytest.raises(KeyError, match="Missing columns for test_op"):
            ar.validate_columns_exist(frame, ["missing"], operation="test_op")

    def test_rejects_string_columns_argument(self, sample_csv):
        frame = ar.read_csv(sample_csv)

        with pytest.raises(TypeError, match="not a string"):
            ar.validate_columns_exist(frame, "name")

    def test_rejects_non_string_column_items(self, sample_csv):
        frame = ar.read_csv(sample_csv)

        with pytest.raises(TypeError, match="only string column names"):
            ar.validate_columns_exist(frame, ["name", 1])

    def test_drop_nulls_rejects_string_subset(self, sample_csv):
        frame = ar.read_csv(sample_csv)

        with pytest.raises(TypeError, match="subset must be a sequence"):
            ar.drop_nulls(frame, subset="name")

    def test_drop_nulls_rejects_missing_subset_column(self, sample_csv):
        frame = ar.read_csv(sample_csv)

        with pytest.raises(KeyError, match="Missing columns for drop_nulls"):
            ar.drop_nulls(frame, subset=["missing"])

    def test_rename_rejects_missing_mapping_column(self, sample_csv):
        frame = ar.read_csv(sample_csv)

        with pytest.raises(KeyError, match="Missing columns for rename_columns"):
            ar.rename_columns(frame, {"missing": "new_name"})


class TestSharedColumnSequenceValidation:
    @pytest.mark.parametrize(
        ("func", "kwargs", "error_type", "message"),
        [
            (
                "keep_rows_with_nulls",
                {"subset": ["missing"]},
                KeyError,
                "Missing columns for keep_rows_with_nulls",
            ),
            (
                "fill_nulls",
                {"value": 0, "subset": ["missing"]},
                KeyError,
                "Missing columns for fill_nulls",
            ),
            (
                "drop_duplicates",
                {"subset": ["missing"]},
                KeyError,
                "Missing columns for drop_duplicates",
            ),
            (
                "strip_whitespace",
                {"subset": ["missing"]},
                KeyError,
                "Missing columns for strip_whitespace",
            ),
            (
                "normalize_case",
                {"subset": ["missing"]},
                KeyError,
                "Missing columns for normalize_case",
            ),
            (
                "normalize_unicode",
                {"subset": ["missing"]},
                KeyError,
                "Missing columns for normalize_unicode",
            ),
            (
                "standardize_missing_tokens",
                {"subset": ["missing"]},
                ValueError,
                "Unknown columns in subset",
            ),
            (
                "coalesce_columns",
                {"subset": ["missing"]},
                KeyError,
                "Missing columns for coalesce_columns",
            ),
        ],
    )
    def test_shared_subset_validation_rejects_missing_columns(
        self,
        sample_csv,
        func,
        kwargs,
        error_type,
        message,
    ):
        frame = ar.read_csv(sample_csv)

        with pytest.raises(error_type, match=message):
            getattr(ar, func)(frame, **kwargs)

    def test_coalesce_columns_selects_first_non_null_value(self):
        frame = ar.from_pandas(
            pd.DataFrame(
                {
                    "nickname": [None, "Bee", None],
                    "name": ["Alice", "Bob", "Cara"],
                }
            )
        )

        result = ar.coalesce_columns(
            frame,
            subset=["nickname", "name"],
            output_column="display_name",
        )
        df = ar.to_pandas(result)

        assert df["display_name"].tolist() == ["Alice", "Bee", "Cara"]

    def test_coalesce_columns_rejects_empty_subset(self):
        frame = ar.from_pandas(pd.DataFrame({"name": ["Alice"]}))

        with pytest.raises(ValueError, match="subset must contain at least one column"):
            ar.coalesce_columns(frame, subset=[])

    def test_coalesce_columns_allows_tuple(self):
        frame = ar.from_pandas(
            pd.DataFrame(
                {
                    "nickname": [None, "Bee", None],
                    "name": ["Alice", "Bob", "Cara"],
                }
            )
        )

        result = ar.coalesce_columns(
            frame,
            subset=("nickname", "name"),
            output_column="display_name",
        )
        df = ar.to_pandas(result)

        assert df["display_name"].tolist() == ["Alice", "Bee", "Cara"]

    @pytest.mark.parametrize(
        ("func", "kwargs", "message"),
        [
            ("drop_columns", {"columns": 123}, "must be a sequence of column names"),
            (
                "fill_nulls",
                {"value": 0, "subset": 123},
                "must be a sequence of column names",
            ),
            ("drop_duplicates", {"subset": 123}, "must be a sequence of column names"),
            (
                "strip_whitespace",
                {"subset": 123},
                "must be a sequence of column names",
            ),
            ("normalize_case", {"subset": 123}, "must be a sequence of column names"),
            (
                "normalize_unicode",
                {"subset": 123},
                "must be a sequence of column names",
            ),
            (
                "combine_columns",
                {"subset": 123, "separator": "-", "output_column": "combined"},
                "must be a sequence of column names",
            ),
            (
                "coalesce_columns",
                {"subset": 123, "output_column": "combined"},
                "must be a sequence of column names",
            ),
        ],
    )
    def test_shared_subset_validation_rejects_non_sequence_types(
        self,
        sample_csv,
        func,
        kwargs,
        message,
    ):
        frame = ar.read_csv(sample_csv)

        with pytest.raises(TypeError, match=message):
            getattr(ar, func)(frame, **kwargs)

    def test_drop_columns_allows_duplicate_entries(self):
        frame = ar.from_pandas(
            pd.DataFrame(
                {
                    "id": [1, 2],
                    "debug": ["x", "y"],
                    "name": ["Alice", "Bob"],
                }
            )
        )

        result = ar.drop_columns(frame, ["debug", "debug"])
        df = ar.to_pandas(result)

        assert list(df.columns) == ["id", "name"]

    def test_combine_columns_rejects_duplicate_subset_entries(self):
        frame = ar.from_pandas(pd.DataFrame({"word": ["go"], "suffix": ["!"]}))

        with pytest.raises(ValueError, match="duplicate column names"):
            ar.combine_columns(
                frame,
                subset=["word", "word", "suffix"],
                separator="-",
                output_column="combined",
            )

    def test_combine_columns_rejects_duplicate_subset_direct(self):
        frame = ar.from_pandas(pd.DataFrame({"a": ["x"], "b": ["y"]}))

        with pytest.raises(ValueError, match="duplicate column names"):
            ar.combine_columns(frame, subset=["a", "a"], output_column="combined")

    def test_combine_columns_pipeline_rejects_duplicate_subset(self):
        frame = ar.from_pandas(pd.DataFrame({"a": ["x"], "b": ["y"]}))

        with pytest.raises(ValueError, match="duplicate column names"):
            ar.pipeline(
                frame,
                [
                    (
                        "combine_columns",
                        {"subset": ["a", "a"], "output_column": "combined"},
                    )
                ],
            )

    def test_coalesce_columns_rejects_duplicate_subset_entries(self):
        frame = ar.from_pandas(
            pd.DataFrame({"nickname": [None, "Bee"], "name": ["Alice", "Bob"]})
        )

        with pytest.raises(ValueError, match="duplicate column names"):
            ar.coalesce_columns(
                frame,
                subset=["nickname", "nickname"],
                output_column="display_name",
            )

    def test_coalesce_columns_pipeline_rejects_duplicate_subset(self):
        frame = ar.from_pandas(
            pd.DataFrame({"nickname": [None, "Bee"], "name": ["Alice", "Bob"]})
        )

        with pytest.raises(ValueError, match="duplicate column names"):
            ar.pipeline(
                frame,
                [
                    (
                        "coalesce_columns",
                        {
                            "subset": ["nickname", "nickname"],
                            "output_column": "display_name",
                        },
                    )
                ],
            )


class TestDropDuplicates:
    def test_drop_dupes_first(self, csv_with_duplicates):
        frame = ar.read_csv(csv_with_duplicates)
        result = ar.drop_duplicates(frame)
        assert result.shape[0] == 3  # Alice, Bob, Charlie

    def test_drop_dupes_last(self, csv_with_duplicates):
        frame = ar.read_csv(csv_with_duplicates)
        result = ar.drop_duplicates(frame, keep="last")
        assert result.shape[0] == 3

    def test_drop_dupes_none(self, csv_with_duplicates):
        frame = ar.read_csv(csv_with_duplicates)
        result = ar.drop_duplicates(frame, keep="none")
        # Only Charlie is unique
        assert result.shape[0] == 1

    def test_drop_dupes_false_alias(self, csv_with_duplicates):
        frame = ar.read_csv(csv_with_duplicates)
        result = ar.drop_duplicates(frame, keep=False)
        # Only Charlie is unique
        assert result.shape[0] == 1

    @pytest.mark.parametrize(
        "keep",
        ["invalid", "FIRST", "all", "", True, None],
    )
    def test_drop_dupes_rejects_invalid_keep_values(self, csv_with_duplicates, keep):
        frame = ar.read_csv(csv_with_duplicates)
        with pytest.raises(ValueError, match="keep must be one of"):
            ar.drop_duplicates(frame, keep=keep)

    def test_drop_dupes_subset(self, csv_with_duplicates):
        frame = ar.read_csv(csv_with_duplicates)
        result = ar.drop_duplicates(frame, subset=["name"])
        assert result.shape[0] == 3

    def test_drop_duplicates_empty_subset_raises(self):
        frame = ar.from_pandas(pd.DataFrame({"id": [1, 2, 3], "name": ["a", "b", "c"]}))

        with pytest.raises(ValueError, match="subset"):
            ar.drop_duplicates(frame, subset=[])

    def test_drop_duplicates_pipeline_empty_subset_raises(self):
        frame = ar.from_pandas(pd.DataFrame({"id": [1, 2, 3], "name": ["a", "b", "c"]}))

        with pytest.raises(ValueError, match="subset"):
            ar.pipeline(frame, [("drop_duplicates", {"subset": []})])

    def test_drop_duplicates_valid_subset_still_works(self):
        frame = ar.from_pandas(
            pd.DataFrame({"id": [1, 2, 3], "name": ["Alice", "Alice", "Bob"]})
        )

        result = ar.drop_duplicates(frame, subset=["name"])
        df = ar.to_pandas(result)

        assert result.shape[0] < frame.shape[0]
        assert "name" in df.columns

    def test_drop_duplicates_subset_none_still_works(self):
        frame = ar.from_pandas(pd.DataFrame({"id": [1, 1, 2], "name": ["a", "a", "b"]}))

        result = ar.drop_duplicates(frame)

        assert result.shape[0] == 2

    def test_drop_dupes_regression_keep_true(self, csv_with_duplicates):
        frame = ar.read_csv(csv_with_duplicates)

        with pytest.raises(ValueError, match="keep must be one of"):
            ar.drop_duplicates(frame, keep=True)

    @pytest.mark.parametrize(
        ("keep", "expected_names"),
        [
            ("first", ["Alice", "Bob", "Charlie"]),
            ("last", ["Alice", "Charlie", "Bob"]),
            ("none", ["Charlie"]),
            (False, ["Charlie"]),
        ],
    )
    def test_drop_duplicates_keep_matrix_deterministic(
        self,
        csv_with_duplicates,
        keep,
        expected_names,
    ):
        frame = ar.read_csv(csv_with_duplicates)

        result = ar.drop_duplicates(frame, keep=keep)

        names = ar.to_pandas(result)["name"].tolist()

        assert names == expected_names

    def test_drop_duplicates_type_collision_int_vs_string(self):
        """int 1 and string '1' must NOT be treated as duplicates (fixes #33)."""
        frame = ar.from_pandas(pd.DataFrame({"id": [1, 2], "val": [1, "1"]}))
        result = ar.drop_duplicates(frame)
        assert result.shape[0] == 2

    def test_drop_duplicates_null_vs_empty_string(self):
        """None and '' must NOT be treated as duplicates (fixes #33)."""
        frame = ar.from_pandas(pd.DataFrame({"col1": [None, "", None]}))
        result = ar.drop_duplicates(frame)
        assert result.shape[0] == 2

    def test_drop_duplicates_separator_injection_unit_sep(self):
        """Rows whose values shift around the \x1f boundary must stay distinct (fixes #33).

        With the old row_key (no length prefixing):
          row 0: col1='a'      col2='b\x1fc'  -> key 'a\x1fb\x1fc\x1f'  (BUG: same as row 1)
          row 1: col1='a\x1fb' col2='c'       -> key 'a\x1fb\x1fc\x1f'  (BUG: same as row 0)
        The two rows are distinct but were incorrectly treated as duplicates.
        """
        frame = ar.from_pandas(
            pd.DataFrame({"col1": ["a", "a\x1fb"], "col2": ["b\x1fc", "c"]})
        )
        result = ar.drop_duplicates(frame)
        assert result.shape[0] == 2

    def test_drop_duplicates_separator_injection_colon(self):
        """Values containing ':' must not produce false duplicates (fixes #33)."""
        frame = ar.from_pandas(
            pd.DataFrame({"col1": ["a:b", "a"], "col2": ["c", "b:c"]})
        )
        result = ar.drop_duplicates(frame)
        assert result.shape[0] == 2

    def test_drop_duplicates_separator_injection_synthetic_prefix(self):
        """Values that look like serialized prefixes must not collide (fixes #33)."""
        frame = ar.from_pandas(
            pd.DataFrame({"col1": ["S1:a", ""], "col2": ["b", "S1:ab"]})
        )
        result = ar.drop_duplicates(frame)
        assert result.shape[0] == 2

    def test_drop_dupes_with_nan_and_nulls(self):
        import numpy as np
        import pandas as pd

        df = pd.DataFrame(
            {
                "id": [1, 1, 2, 2, 3, 3],
                "val1": [np.nan, np.nan, 10.5, 10.5, None, None],
                "val2": ["a", "a", "b", "b", None, None],
            }
        )
        frame = ar.from_pandas(df)

        # keep="first"
        res_first = ar.to_pandas(ar.drop_duplicates(frame, keep="first"))
        assert len(res_first) == 3

        # keep="none"
        res_none = ar.to_pandas(ar.drop_duplicates(frame, keep="none"))
        assert len(res_none) == 0

        # subset with NaN
        res_subset = ar.to_pandas(ar.drop_duplicates(frame, subset=["val1"]))
        assert len(res_subset) == 2

    def test_drop_duplicates_zero_col_subset_none_preserves_rows(self):
        frame = ar.from_pandas(pd.DataFrame(index=range(3)))
        result = ar.drop_duplicates(frame)
        assert result.shape == (3, 0)

    def test_drop_duplicates_zero_col_empty_subset_raises(self):
        frame = ar.from_pandas(pd.DataFrame(index=range(3)))
        with pytest.raises(ValueError, match="subset cannot be empty"):
            ar.drop_duplicates(frame, subset=[])

    def test_drop_duplicates_zero_col_missing_column_raises(self):
        frame = ar.from_pandas(pd.DataFrame(index=range(3)))
        with pytest.raises(KeyError):
            ar.drop_duplicates(frame, subset=["missing"])


class TestDropColumns:
    def test_drop_columns_removes_requested_columns_and_preserves_order(self):
        frame = ar.from_pandas(
            pd.DataFrame(
                {
                    "id": [1, 2],
                    "debug": ["x", "y"],
                    "name": ["Alice", "Bob"],
                    "flag": [True, False],
                }
            )
        )

        result = ar.drop_columns(frame, ["debug", "flag"])
        df = ar.to_pandas(result)

        assert list(df.columns) == ["id", "name"]
        assert list(df["name"]) == ["Alice", "Bob"]

    def test_drop_columns_accepts_tuple_input(self):
        frame = ar.from_pandas(
            pd.DataFrame(
                {
                    "a": [1],
                    "b": [2],
                    "c": [3],
                }
            )
        )

        result = ar.drop_columns(frame, ("a",))
        df = ar.to_pandas(result)

        assert list(df.columns) == ["b", "c"]

    def test_drop_columns_allows_empty_input_as_no_op(self, sample_csv):
        frame = ar.read_csv(sample_csv)

        result_helper = ar.drop_columns(frame, [])
        result_method = frame.drop_columns([])

        assert result_helper is not frame
        assert result_helper == frame
        assert result_helper == result_method

    def test_drop_columns_rejects_missing_columns(self, sample_csv):
        frame = ar.read_csv(sample_csv)

        with pytest.raises(ValueError, match="Columns not found in frame"):
            ar.drop_columns(frame, ["missing"])

    def test_drop_columns_rejects_string_input(self, sample_csv):
        frame = ar.read_csv(sample_csv)

        with pytest.raises(TypeError, match="not a string"):
            ar.drop_columns(frame, "age")

    def test_drop_columns_rejects_non_string_items(self, sample_csv):
        frame = ar.read_csv(sample_csv)

        with pytest.raises(TypeError, match="only string column names"):
            ar.drop_columns(frame, ["age", 1])

    def test_drop_columns_rejects_removing_all_columns_across_entry_points(self):
        frame = ar.from_pandas(pd.DataFrame({"id": [1, 2], "name": ["a", "b"]}))

        with pytest.raises(ValueError, match="drop_columns cannot remove all columns"):
            frame.drop_columns(["id", "name"])

        with pytest.raises(ValueError, match="drop_columns cannot remove all columns"):
            ar.drop_columns(frame, ["id", "name"])

        with pytest.raises(ValueError, match="drop_columns cannot remove all columns"):
            ar.pipeline(
                frame,
                [
                    ("drop_columns", {"columns": ["id", "name"]}),
                ],
            )


class TestDropEmptyColumnsPipeline:
    def test_drop_empty_columns_all_empty(self, csv_with_empty_columns):
        frame = ar.read_csv(csv_with_empty_columns)
        result = ar.drop_empty_columns(frame)
        assert "empty_num" not in result.columns
        assert "empty_text" not in result.columns
        assert "name" in result.columns
        assert "age" in result.columns

    def test_drop_empty_columns_no_empty(self, sample_csv):
        frame = ar.read_csv(sample_csv)
        result = ar.drop_empty_columns(frame)
        assert result.columns == frame.columns
        assert result.shape == frame.shape

    def test_drop_empty_columns_partially_empty(self, tmp_path):
        path = tmp_path / "mixed.csv"
        path.write_text("id,value,mixed\n1,10,\n2,20,data\n3,30,\n")
        frame = ar.read_csv(path)
        result = ar.drop_empty_columns(frame)
        assert "mixed" in result.columns

    def test_drop_empty_columns_pipeline(self, csv_with_empty_columns):
        frame = ar.read_csv(csv_with_empty_columns)
        result = ar.pipeline(
            frame,
            [("drop_empty_columns",)],
        )
        assert "empty_num" not in result.columns
        assert "empty_text" not in result.columns

    def test_drop_empty_columns_empty_frame(self):
        frame = ar.from_pandas(pd.DataFrame(columns=["a", "b", "c"]))
        result = ar.drop_empty_columns(frame)
        assert result.columns == ["a", "b", "c"]
        assert result.shape == frame.shape


class TestDropConstantColumns:
    def test_drop_constant_columns_removes_constant_columns(self):
        frame = ar.from_pandas(
            pd.DataFrame(
                {
                    "value": [1, 2, 3],
                    "constant_num": [7, 7, 7],
                    "constant_text": ["x", "x", "x"],
                }
            )
        )

        result = ar.drop_constant_columns(frame)
        df = ar.to_pandas(result)

        assert list(df.columns) == ["value"]
        assert list(df["value"]) == [1, 2, 3]

    def test_drop_constant_columns_keeps_non_constant_columns(self):
        frame = ar.from_pandas(
            pd.DataFrame(
                {
                    "a": [1, 2, 1],
                    "b": ["x", "y", "x"],
                }
            )
        )

        result = ar.drop_constant_columns(frame)

        assert result.columns == frame.columns
        assert result.shape == frame.shape

    def test_drop_constant_columns_drops_all_null_column(self):
        frame = ar.from_pandas(
            pd.DataFrame(
                {
                    "all_null": [None, None],
                    "value": [1, 2],
                }
            )
        )

        result = ar.drop_constant_columns(frame)

        assert result.columns == ["value"]

    def test_drop_constant_columns_keeps_value_plus_null_column(self):
        frame = ar.from_pandas(
            pd.DataFrame(
                {
                    "maybe_constant": [1, 1, None],
                    "constant": [2, 2, 2],
                }
            )
        )

        result = ar.drop_constant_columns(frame)
        df = ar.to_pandas(result)

        assert list(df.columns) == ["maybe_constant"]
        assert df.shape == (3, 1)

    def test_drop_constant_columns_empty_frame_keeps_columns(self):
        frame = ar.from_pandas(
            pd.DataFrame(
                {
                    "empty_num": pd.Series(dtype="float64"),
                    "empty_text": pd.Series(dtype="object"),
                }
            )
        )

        result = ar.drop_constant_columns(frame)

        assert result.columns == ["empty_num", "empty_text"]
        assert result.shape == frame.shape

    def test_drop_constant_columns_all_columns_dropped_preserves_row_count(self):
        frame = ar.from_pandas(pd.DataFrame({"a": [1], "b": ["x"], "c": [None]}))

        result = ar.drop_constant_columns(frame)

        assert result.columns == []
        assert result.shape[0] == 1
        assert result.shape[1] == 0
        assert ar.to_pandas(result).shape == (1, 0)

    def test_drop_constant_columns_all_columns_dropped_preserves_row_count_multiple_rows(
        self,
    ):
        frame = ar.from_pandas(pd.DataFrame({"a": [7, 7, 7], "b": ["x", "x", "x"]}))
        result = ar.drop_constant_columns(frame)
        assert result.columns == []
        assert result.shape == (3, 0)
        assert ar.to_pandas(result).shape == (3, 0)

    def test_zero_column_frame_shape_and_num_rows(self):
        df = pd.DataFrame(index=range(5))
        frame = ar.from_pandas(df)
        assert frame.shape == (5, 0)
        assert frame.shape[0] == 5
        assert frame.shape[1] == 0

    def test_zero_column_frame_pandas_roundtrip(self):
        for n in [0, 1, 5, 100]:
            df = pd.DataFrame(index=range(n))
            frame = ar.from_pandas(df)
            result = ar.to_pandas(frame)
            assert result.shape == (n, 0), f"failed for n={n}"

    def test_zero_column_frame_clone_preserves_row_count(self):
        df = pd.DataFrame(index=range(4))
        frame = ar.from_pandas(df)
        cloned = frame._frame.clone()
        assert cloned.num_rows() == 4
        assert cloned.num_cols() == 0

    def test_drop_constant_columns_pandas_input(self):
        df = pd.DataFrame(
            {
                "value": [1, 2, 3],
                "constant_num": [7, 7, 7],
                "constant_text": ["x", "x", "x"],
            }
        )

        result = ar.drop_constant_columns(df)
        assert isinstance(result, pd.DataFrame)
        assert list(result.columns) == ["value"]
        assert list(result["value"]) == [1, 2, 3]
        # Assert that the input DataFrame was not mutated
        assert list(df.columns) == ["value", "constant_num", "constant_text"]

    def test_drop_constant_columns_invalid_type_raises(self):
        with pytest.raises(
            TypeError, match="frame must be an ArFrame or a pandas DataFrame"
        ):
            ar.drop_constant_columns([1, 2, 3])

    def test_drop_constant_columns_zero_row_pandas_returns_new_object(self):
        df = pd.DataFrame({"a": pd.Series(dtype="int64")})

        result = ar.drop_constant_columns(df)

        assert result is not df
        assert result.shape == (0, 1)

    def test_drop_constant_columns_zero_row_arframe_returns_new_object(self):
        frame = ar.from_pandas(pd.DataFrame({"a": pd.Series(dtype="int64")}))

        result = ar.drop_constant_columns(frame)

        assert result is not frame
        assert result.shape == (0, 1)

    def test_drop_constant_columns_zero_row_attrs_not_shared(self):
        frame = ar.from_pandas(pd.DataFrame({"a": pd.Series(dtype="int64")}))

        frame._attrs = {"nested": {"x": 1}}

        result = ar.drop_constant_columns(frame)

        result._attrs["nested"]["x"] = 2

        assert frame._attrs["nested"]["x"] == 1


class TestDropEmptyColumns:
    def test_drop_empty_columns_removes_fully_empty_columns(self, tmp_path):
        csv_path = tmp_path / "drop_empty_columns.csv"
        csv_path.write_text(
            'all_null,all_blank,value\n,"",1\n,"   ",2\n,"",3\n',
            encoding="utf-8",
        )
        frame = ar.read_csv(csv_path)

        result = ar.drop_empty_columns(frame)
        df = ar.to_pandas(result)

        assert list(df.columns) == ["value"]
        assert list(df["value"]) == [1, 2, 3]

    def test_drop_empty_columns_keeps_partially_empty_columns(self, tmp_path):
        csv_path = tmp_path / "drop_empty_columns_partial.csv"
        csv_path.write_text(
            'maybe_empty,whitespace_then_value\n,"   "\n"",\nkept,x\n',
            encoding="utf-8",
        )
        frame = ar.read_csv(csv_path)

        result = ar.drop_empty_columns(frame)

        assert result.columns == frame.columns
        assert result.shape == frame.shape

    def test_drop_empty_columns_keeps_falsey_non_string_columns(self, tmp_path):
        csv_path = tmp_path / "drop_empty_columns_falsey.csv"
        csv_path.write_text(
            "zeros,string_zero\n0,0\n0,0\n0,0\n",
            encoding="utf-8",
        )
        frame = ar.read_csv(csv_path)

        result = ar.drop_empty_columns(frame)

        assert result.columns == ["zeros", "string_zero"]
        assert result.shape == frame.shape

    def test_drop_empty_columns_all_columns_dropped_preserves_row_count(self, tmp_path):
        csv_path = tmp_path / "drop_empty_columns_all.csv"
        csv_path.write_text('all_null,all_blank\n,""\n, \n', encoding="utf-8")
        frame = ar.read_csv(csv_path)

        result = ar.drop_empty_columns(frame)

        assert result.columns == []
        assert result.shape[1] == 0
        assert result.shape[0] in {0, 2}
        assert ar.to_pandas(result).shape[1] == 0

    def test_drop_empty_columns_preserves_schema_on_empty_frame(self):
        df = pd.DataFrame(columns=["a", "b", "c"])
        frame = ar.from_pandas(df)

        result = ar.drop_empty_columns(frame)

        assert result.columns == ["a", "b", "c"]
        assert result.shape[0] == 0
        assert result.shape[1] == 3

    def test_drop_empty_columns_zero_row_metadata_isolation(self):
        df = pd.DataFrame({"a": pd.Series(dtype="object")})
        frame = ar.from_pandas(df)
        frame._attrs = {"nested": {"x": 1}}

        result = ar.drop_empty_columns(frame)

        assert result is not frame
        assert result.columns == ["a"]
        assert result.shape == (0, 1)

        result._attrs["nested"]["x"] = 2
        assert frame._attrs["nested"]["x"] == 1


class TestClipNumeric:
    def test_clip_numeric_lower_only(self):
        frame = ar.from_pandas(pd.DataFrame({"value": [-5, 0, 10]}))

        result = ar.clip_numeric(frame, lower=1)
        df = ar.to_pandas(result)

        assert list(df["value"]) == [1, 1, 10]

    def test_clip_numeric_upper_only(self):
        frame = ar.from_pandas(pd.DataFrame({"value": [-5, 0, 10]}))

        result = ar.clip_numeric(frame, upper=3)
        df = ar.to_pandas(result)

        assert list(df["value"]) == [-5, 0, 3]

    def test_clip_numeric_both_bounds(self):
        frame = ar.from_pandas(pd.DataFrame({"value": [-5, 2, 10]}))

        result = ar.clip_numeric(frame, lower=0, upper=5)
        df = ar.to_pandas(result)

        assert list(df["value"]) == [0, 2, 5]

    def test_clip_numeric_all_numeric_subset_skips_non_numeric_columns(self):
        frame = ar.from_pandas(
            pd.DataFrame(
                {
                    "value": [-5, 5, 20],
                    "label": ["low", "ok", "high"],
                }
            )
        )

        result = ar.clip_numeric(frame, lower=0, upper=10)
        df = ar.to_pandas(result)

        assert list(df["value"]) == [0, 5, 10]
        assert list(df["label"]) == ["low", "ok", "high"]

    def test_clip_numeric_subset_only_requested_numeric_columns(self):
        frame = ar.from_pandas(
            pd.DataFrame(
                {
                    "a": [-5, 0, 10],
                    "b": [-10, 5, 20],
                    "label": ["x", "y", "z"],
                }
            )
        )

        result = ar.clip_numeric(frame, lower=0, upper=8, subset=["b"])
        df = ar.to_pandas(result)

        assert list(df["a"]) == [-5, 0, 10]
        assert list(df["b"]) == [0, 5, 8]
        assert list(df["label"]) == ["x", "y", "z"]

    def test_clip_numeric_string_subset_rejected_before_native_execution(self):
        frame = ar.from_pandas(pd.DataFrame({"a": [1, 2], "age": [1, 2]}))

        with pytest.raises(
            TypeError,
            match="subset must be a sequence of column names, not a string",
        ):
            ar.clip_numeric(frame, lower=0, subset="age")

    def test_clip_numeric_non_string_subset_item_rejected_before_native_execution(
        self,
    ):
        frame = ar.from_pandas(pd.DataFrame({"age": [1, 2, 3]}))

        with pytest.raises(
            TypeError,
            match="subset must contain only string column names",
        ):
            ar.clip_numeric(frame, lower=0, subset=[1])

    def test_clip_numeric_valid_tuple_subset_preserves_supported_behavior(self):
        frame = ar.from_pandas(
            pd.DataFrame(
                {
                    "a": [-5, 0, 10],
                    "b": [-10, 5, 20],
                    "label": ["x", "y", "z"],
                }
            )
        )

        result = ar.clip_numeric(frame, lower=0, upper=8, subset=("b",))
        df = ar.to_pandas(result)

        assert list(df["a"]) == [-5, 0, 10]
        assert list(df["b"]) == [0, 5, 8]
        assert list(df["label"]) == ["x", "y", "z"]

    def test_clip_numeric_keeps_missing_values(self):
        frame = ar.from_pandas(pd.DataFrame({"value": [None, -5.0, 10.0]}))

        result = ar.clip_numeric(frame, lower=0, upper=5)
        df = ar.to_pandas(result)

        assert pd.isna(df["value"].iloc[0])
        assert list(df["value"].iloc[1:]) == [0.0, 5.0]

    def test_clip_numeric_unknown_subset_column_raises(self):
        frame = ar.from_pandas(pd.DataFrame({"value": [1, 2, 3]}))

        with pytest.raises(ValueError, match="Unknown columns in subset"):
            ar.clip_numeric(frame, lower=0, subset=["missing"])

    def test_clip_numeric_non_numeric_subset_column_raises(self):
        frame = ar.from_pandas(
            pd.DataFrame({"value": [1, 2, 3], "label": ["x", "y", "z"]})
        )

        with pytest.raises(
            ValueError, match="clip_numeric only supports numeric columns"
        ):
            ar.clip_numeric(frame, lower=0, subset=["label"])

    def test_clip_numeric_no_bounds_raises(self):
        frame = ar.from_pandas(pd.DataFrame({"value": [1, 2, 3]}))

        with pytest.raises(
            ValueError, match="At least one of 'lower' or 'upper' must be provided"
        ):
            ar.clip_numeric(frame)

    def test_clip_numeric_inverted_bounds_raises(self):
        frame = ar.from_pandas(pd.DataFrame({"value": [1, 2, 3]}))

        with pytest.raises(ValueError, match="lower cannot be greater than upper"):
            ar.clip_numeric(frame, lower=5, upper=1)

    def test_clip_numeric_empty_subset_returns_frame_unchanged(self):
        # subset=[] must return the original frame without modification.
        # This was a previous review blocker; the guard lives in the Python wrapper
        # and must never reach the C++ layer.
        frame = ar.from_pandas(pd.DataFrame({"value": [-5, 0, 10]}))

        result = ar.clip_numeric(frame, lower=0, upper=5, subset=[])

        df_orig = ar.to_pandas(frame)
        df_result = ar.to_pandas(result)
        assert list(df_result["value"]) == list(df_orig["value"])

    def test_clip_numeric_non_integral_lower_on_int64_raises(self):
        # A float lower bound that is not integral (e.g. 1.5) must raise rather
        # than silently truncate to 1 via C++ static_cast<int64_t>.
        frame = ar.from_pandas(pd.DataFrame({"x": [0, 2, 5]}))

        with pytest.raises(ValueError, match="not an integer value"):
            ar.clip_numeric(frame, lower=1.5)

    def test_clip_numeric_non_integral_upper_on_int64_raises(self):
        # Same guard for the upper bound.
        frame = ar.from_pandas(pd.DataFrame({"x": [0, 2, 5]}))

        with pytest.raises(ValueError, match="not an integer value"):
            ar.clip_numeric(frame, upper=3.7)

    def test_clip_numeric_integral_float_bound_on_int64_accepted(self):
        # A float that is mathematically integral (e.g. 2.0) is fine.
        frame = ar.from_pandas(pd.DataFrame({"x": [-1, 2, 10]}))

        result = ar.clip_numeric(frame, lower=0.0, upper=5.0)
        df = ar.to_pandas(result)

        assert list(df["x"]) == [0, 2, 5]

    def test_clip_numeric_out_of_range_bound_on_int64_raises(self):
        frame = ar.from_pandas(pd.DataFrame({"x": [-1, 2, 10]}))

        with pytest.raises(ValueError, match="within int64 range"):
            ar.clip_numeric(frame, upper=1e20)

        with pytest.raises(ValueError, match="within int64 range"):
            ar.clip_numeric(frame, lower=-1e20)

    def test_clip_numeric_non_integral_bound_on_float64_accepted(self):
        # Non-integral bounds are valid for float64 columns.
        frame = ar.from_pandas(pd.DataFrame({"v": [-1.0, 2.5, 9.9]}))

        result = ar.clip_numeric(frame, lower=1.5, upper=8.3)
        df = ar.to_pandas(result)

        assert list(df["v"]) == [1.5, 2.5, 8.3]

    def test_clip_numeric_rejects_bool_and_non_numeric_bounds(self):
        frame = ar.from_pandas(pd.DataFrame({"values": [1.0, 5.0, 10.0, 20.0]}))

        # Boolean bounds must be rejected (bool is subclass of int in Python,
        # so explicit rejection is required)
        with pytest.raises(TypeError, match="'lower' must be an int or float"):
            ar.clip_numeric(frame, lower=True)

        with pytest.raises(TypeError, match="'upper' must be an int or float"):
            ar.clip_numeric(frame, upper=False)

        with pytest.raises(TypeError, match="'lower' must be an int or float"):
            ar.clip_numeric(frame, lower="a")

        with pytest.raises(TypeError, match="'upper' must be an int or float"):
            ar.clip_numeric(frame, upper="10")

        # Valid int and float bounds must still work fine
        ar.clip_numeric(frame, lower=0, upper=15)
        ar.clip_numeric(frame, lower=0.5, upper=9.5)

    def test_clip_numeric_pipeline_rejects_invalid_bounds(self):
        frame = ar.from_pandas(pd.DataFrame({"x": [1, 2, 3]}))

        with pytest.raises(TypeError, match="'lower' must be an int or float"):
            ar.pipeline(
                frame,
                [("clip_numeric", {"lower": True})],
            )


class TestStandardizeMissingTokens:
    def test_normal_case(self):
        df = pd.DataFrame({"value": [1, 2, "N/A"]})
        result = ar.standardize_missing_tokens(df)
        assert isinstance(result, pd.DataFrame)
        assert pd.isna(result["value"].iloc[2])

    def test_normal_case_arframe(self):
        frame = ar.from_pandas(pd.DataFrame({"value": [1, 2, "N/A"]}))
        result = ar.standardize_missing_tokens(frame)
        df = ar.to_pandas(result)
        assert isinstance(result, ar.ArFrame)
        assert pd.isna(df["value"].iloc[2])

    def test_default_case(self):
        df = pd.DataFrame({"value": [1, 2, "-"]})
        result = ar.standardize_missing_tokens(df)
        assert pd.isna(result["value"].iloc[2])

    def test_default_case_subset(self):
        df = pd.DataFrame(
            {
                "roll_no": ["001", "002", "003"],
                "name": ["Alice", "Bob", "Carter"],
                "marks": [100, 90, "-"],
            }
        )
        result = ar.standardize_missing_tokens(df, subset=["marks"])
        assert pd.isna(result["marks"].iloc[2])
        assert result["name"].iloc[2] == "Carter"

    def test_custom_case(self):
        df = pd.DataFrame({"value": [1, 2, "unknown"]})
        result = ar.standardize_missing_tokens(df, tokens=["unknown"])
        assert pd.isna(result["value"].iloc[2])

    def test_custom_case_subset(self):
        df = pd.DataFrame(
            {
                "roll_no": ["001", "002", "003"],
                "name": ["Alice", "Bob", "Carter"],
                "marks": [100, 90, "unknown"],
            }
        )
        result = ar.standardize_missing_tokens(df, tokens=["unknown"], subset=["marks"])
        assert pd.isna(result["marks"].iloc[2])
        assert result["name"].iloc[2] == "Carter"

    def test_non_string_columns(self):
        df = pd.DataFrame({"value": [1, 2, 3]})
        result = ar.standardize_missing_tokens(df)
        assert result["value"].iloc[0] == 1

    def test_unchanged_columns(self):
        df = pd.DataFrame({"value": [1, 2, "-"]})
        result = ar.standardize_missing_tokens(df, tokens=[])
        assert result["value"].iloc[2] == "-"

    def test_whitespace_only_values_remain_when_tokens_disabled(self):
        df = pd.DataFrame({"value": ["  ", "\t", "\n"]})

        result = ar.standardize_missing_tokens(df, tokens=[])

        assert result["value"].tolist() == ["  ", "\t", "\n"]

    def test_standardize_missing_tokens_unknown_subset_column_raises(self):
        frame = pd.DataFrame({"value": [1, 2, 3]})
        with pytest.raises(ValueError, match="Unknown columns in subset"):
            ar.standardize_missing_tokens(frame, subset=["missing"])

    def test_standardize_missing_tokens_pandas_subset_returns_dataframe(self):
        df = pd.DataFrame({"name": ["N/A", "Alice"], "city": ["-", "Paris"]})

        result = ar.standardize_missing_tokens(df, subset=["name"])

        assert isinstance(result, pd.DataFrame)
        assert pd.isna(result.loc[0, "name"])
        assert result.loc[1, "name"] == "Alice"
        assert result["city"].tolist() == ["-", "Paris"]

    def test_standardize_missing_tokens_normalizes_whitespace_wrapped_defaults(self):
        df = pd.DataFrame({"value": ["NULL ", " NaN", "  ", "", "Alice "]})

        result = ar.standardize_missing_tokens(df)

        assert pd.isna(result["value"].iloc[0])
        assert pd.isna(result["value"].iloc[1])
        assert pd.isna(result["value"].iloc[2])
        assert pd.isna(result["value"].iloc[3])
        assert result["value"].iloc[4] == "Alice "

    def test_standardize_missing_tokens_normalizes_whitespace_wrapped_custom_tokens(
        self,
    ):
        df = pd.DataFrame(
            {
                "status": [" unknown ", "pending", " custom-null "],
                "note": [" untouched ", "unknown", "kept"],
            }
        )

        result = ar.standardize_missing_tokens(
            df, tokens=["unknown", "custom-null"], subset=["status"]
        )

        assert pd.isna(result["status"].iloc[0])
        assert result["status"].iloc[1] == "pending"
        assert pd.isna(result["status"].iloc[2])
        assert result["note"].tolist() == [" untouched ", "unknown", "kept"]

    def test_standardize_missing_tokens_normalizes_custom_token_list_entries(self):
        df = pd.DataFrame({"value": ["unknown", " Unknown ", "kept"]})

        result = ar.standardize_missing_tokens(df, tokens=["  UNKNOWN  "])

        assert pd.isna(result["value"].iloc[0])
        assert pd.isna(result["value"].iloc[1])
        assert result["value"].iloc[2] == "kept"

    def test_standardize_missing_tokens_normalizes_custom_token_list_entries_in_subset(
        self,
    ):
        df = pd.DataFrame(
            {
                "status": [" unknown ", "kept"],
                "note": ["UNKNOWN", "still here"],
            }
        )

        result = ar.standardize_missing_tokens(
            df, tokens=["  UNKNOWN  "], subset=["status"]
        )

        assert pd.isna(result["status"].iloc[0])
        assert result["status"].iloc[1] == "kept"
        assert result["note"].tolist() == ["UNKNOWN", "still here"]

    def test_standardize_missing_tokens_normalizes_tab_and_newline_wrapped_tokens(
        self,
    ):
        df = pd.DataFrame({"value": ["\tNULL\t", "\n NaN\n", "\t kept \n"]})

        result = ar.standardize_missing_tokens(df)

        assert pd.isna(result["value"].iloc[0])
        assert pd.isna(result["value"].iloc[1])
        assert result["value"].iloc[2] == "\t kept \n"

    def test_standardize_missing_tokens_subset_does_not_normalize_excluded_whitespace(
        self,
    ):
        df = pd.DataFrame(
            {
                "status": ["  ", "NULL "],
                "note": ["  ", "NULL "],
            }
        )

        result = ar.standardize_missing_tokens(df, subset=["status"])

        assert pd.isna(result["status"].iloc[0])
        assert pd.isna(result["status"].iloc[1])
        assert result["note"].tolist() == ["  ", "NULL "]

    def test_standardize_missing_tokens_normalizes_carriage_return_wrapped_tokens(
        self,
    ):
        df = pd.DataFrame({"value": ["\r\nNULL\r", "\r\n nAn \r\n", "\r kept \r"]})

        result = ar.standardize_missing_tokens(df)

        assert pd.isna(result["value"].iloc[0])
        assert pd.isna(result["value"].iloc[1])
        assert result["value"].iloc[2] == "\r kept \r"

    def test_standardize_missing_tokens_normalizes_nonbreaking_space_wrapped_tokens(
        self,
    ):
        nbsp = "\u00a0"
        df = pd.DataFrame({"value": [f"{nbsp}NULL{nbsp}", f"{nbsp} kept {nbsp}"]})

        result = ar.standardize_missing_tokens(df)

        assert pd.isna(result["value"].iloc[0])
        assert result["value"].iloc[1] == f"{nbsp} kept {nbsp}"

    def test_standardize_missing_tokens_custom_tokens_do_not_fall_back_to_defaults(
        self,
    ):
        df = pd.DataFrame({"value": [" NULL ", " custom-null ", "kept"]})

        result = ar.standardize_missing_tokens(df, tokens=["custom-null"])

        assert result["value"].iloc[0] == " NULL "
        assert pd.isna(result["value"].iloc[1])
        assert result["value"].iloc[2] == "kept"

    def test_standardize_missing_tokens_whitespace_only_custom_tokens_match_blank_values(
        self,
    ):
        df = pd.DataFrame({"value": ["  ", "\t", "\n", "kept"]})

        result = ar.standardize_missing_tokens(df, tokens=["   "])

        assert pd.isna(result["value"].iloc[0])
        assert pd.isna(result["value"].iloc[1])
        assert pd.isna(result["value"].iloc[2])
        assert result["value"].iloc[3] == "kept"

    def test_standardize_missing_tokens_preserves_existing_nulls_while_normalizing_wrapped_tokens(
        self,
    ):
        df = pd.DataFrame({"value": [None, pd.NA, " NULL ", "kept"]})

        result = ar.standardize_missing_tokens(df)

        assert pd.isna(result["value"].iloc[0])
        assert pd.isna(result["value"].iloc[1])
        assert pd.isna(result["value"].iloc[2])
        assert result["value"].iloc[3] == "kept"

    def test_standardize_missing_tokens_normalizes_wrapped_punctuation_defaults(self):
        df = pd.DataFrame({"value": [" ? ", "\t-\t", "--", "kept"]})

        result = ar.standardize_missing_tokens(df)

        assert pd.isna(result["value"].iloc[0])
        assert pd.isna(result["value"].iloc[1])
        assert result["value"].iloc[2] == "--"
        assert result["value"].iloc[3] == "kept"

    def test_standardize_missing_tokens_scalar_int_raises(self):
        frame = pd.DataFrame({"x": ["NA", "N", "ok"]})
        with pytest.raises(TypeError, match="tokens must be a list of strings"):
            ar.standardize_missing_tokens(frame, tokens=1)

    def test_standardize_missing_tokens_dict_raises(self):
        frame = pd.DataFrame({"x": ["NA", "N", "ok"]})
        with pytest.raises(TypeError, match="tokens must be a list of strings"):
            ar.standardize_missing_tokens(frame, tokens={"NA": "bad"})

    def test_standardize_missing_tokens_bare_string_raises(self):
        frame = pd.DataFrame({"x": ["NA", "N", "ok"]})
        with pytest.raises(TypeError, match="tokens must be a list of strings"):
            ar.standardize_missing_tokens(frame, tokens="NA")

    def test_standardize_missing_tokens_list_with_non_string_item_raises(self):
        frame = pd.DataFrame({"x": ["NA", "N", "ok"]})
        with pytest.raises(TypeError, match="tokens must be a list of strings"):
            ar.standardize_missing_tokens(frame, tokens=["NA", 1])


class TestStripWhitespace:
    def test_strip(self, csv_with_whitespace):
        frame = ar.read_csv(csv_with_whitespace)
        result = ar.strip_whitespace(frame)
        df = ar.to_pandas(result)
        assert df["name"].iloc[0] == "Alice"
        assert df["city"].iloc[1] == "London"

    def test_strip_subset(self, csv_with_whitespace):
        frame = ar.read_csv(csv_with_whitespace)
        result = ar.strip_whitespace(frame, subset=["name"])
        df = ar.to_pandas(result)
        assert df["name"].iloc[0] == "Alice"

    def test_strip_tabs_and_newlines(self):
        frame = ar.from_pandas(
            pd.DataFrame(
                {
                    "name": ["\tAlice\n", "  Bob\t"],
                    "city": ["\nLondon ", "\tParis\t"],
                }
            )
        )

        result = ar.strip_whitespace(frame)

        df = ar.to_pandas(result)

        assert df["name"].tolist() == ["Alice", "Bob"]
        assert df["city"].tolist() == ["London", "Paris"]


class TestNormalizeCase:
    def test_lower(self, sample_csv):
        frame = ar.read_csv(sample_csv)
        result = ar.normalize_case(frame, subset=["name"], case_type="lower")
        df = ar.to_pandas(result)
        assert df["name"].iloc[0] == "alice"

    def test_upper(self, sample_csv):
        frame = ar.read_csv(sample_csv)
        result = ar.normalize_case(frame, subset=["name"], case_type="upper")
        df = ar.to_pandas(result)
        assert df["name"].iloc[0] == "ALICE"

    def test_title(self, sample_csv):
        frame = ar.read_csv(sample_csv)
        result = ar.normalize_case(frame, subset=["name"], case_type="title")
        df = ar.to_pandas(result)
        assert df["name"].iloc[0] == "Alice"

    def test_title_hyphen(self):
        import pandas as pd

        frame = ar.from_pandas(
            pd.DataFrame({"name": ["hello-world", "jean-luc picard"]})
        )
        result = ar.normalize_case(frame, subset=["name"], case_type="title")
        df = ar.to_pandas(result)
        assert df["name"].iloc[0] == "Hello-World"
        assert df["name"].iloc[1] == "Jean-Luc Picard"

    def test_title_underscore(self):
        import pandas as pd

        frame = ar.from_pandas(pd.DataFrame({"name": ["hello_world", "foo_bar_baz"]}))
        result = ar.normalize_case(frame, subset=["name"], case_type="title")
        df = ar.to_pandas(result)
        assert df["name"].iloc[0] == "Hello_World"
        assert df["name"].iloc[1] == "Foo_Bar_Baz"

    def test_title_period(self):
        import pandas as pd

        frame = ar.from_pandas(pd.DataFrame({"name": ["dr.strange", "mr.smith"]}))
        result = ar.normalize_case(frame, subset=["name"], case_type="title")
        df = ar.to_pandas(result)
        assert df["name"].iloc[0] == "Dr.Strange"
        assert df["name"].iloc[1] == "Mr.Smith"

    def test_title_slash(self):
        import pandas as pd

        frame = ar.from_pandas(pd.DataFrame({"name": ["hello/world", "foo/bar"]}))
        result = ar.normalize_case(frame, subset=["name"], case_type="title")
        df = ar.to_pandas(result)
        assert df["name"].iloc[0] == "Hello/World"
        assert df["name"].iloc[1] == "Foo/Bar"

    def test_unicode_bytes_are_preserved_for_lower_and_upper(self):
        import pandas as pd

        frame = ar.from_pandas(
            pd.DataFrame({"city": ["São Paulo", "München", "東京", "Dev 🚀"]})
        )

        lower = ar.to_pandas(
            ar.normalize_case(frame, subset=["city"], case_type="lower")
        )
        upper = ar.to_pandas(
            ar.normalize_case(frame, subset=["city"], case_type="upper")
        )

        assert lower["city"].tolist() == ["são paulo", "münchen", "東京", "dev 🚀"]
        assert upper["city"].tolist() == ["SãO PAULO", "MüNCHEN", "東京", "DEV 🚀"]

    def test_unicode_bytes_are_preserved_for_title(self):
        import pandas as pd

        frame = ar.from_pandas(
            pd.DataFrame({"city": ["são-paulo", "münchen central", "東京 station"]})
        )

        result = ar.normalize_case(frame, subset=["city"], case_type="title")
        df = ar.to_pandas(result)

        assert df["city"].tolist() == ["São-Paulo", "München Central", "東京 Station"]

    def test_title_preserves_non_ascii_word_prefixes(self):
        import pandas as pd

        frame = ar.from_pandas(pd.DataFrame({"word": ["éclair", "ñandú", "über-cool"]}))

        result = ar.normalize_case(frame, subset=["word"], case_type="title")
        df = ar.to_pandas(result)

        assert df["word"].tolist() == ["éclair", "ñandú", "über-Cool"]

    def test_invalid_case_type_int(self):
        import pandas as pd

        frame = ar.from_pandas(pd.DataFrame({"x": ["A"]}))
        with pytest.raises(TypeError, match="case_type must be a string"):
            ar.normalize_case(frame, case_type=123)

    def test_invalid_case_type_none(self):
        import pandas as pd

        frame = ar.from_pandas(pd.DataFrame({"x": ["A"]}))
        with pytest.raises(TypeError, match="case_type must be a string"):
            ar.normalize_case(frame, case_type=None)

    def test_invalid_case_type_string(self):
        import pandas as pd

        frame = ar.from_pandas(pd.DataFrame({"x": ["A"]}))
        with pytest.raises(ValueError, match="case_type must be one of"):
            ar.normalize_case(frame, case_type="invalid")


class TestNormalizeUnicode:
    def test_normalize_unicode(self):
        import unicodedata

        import pandas as pd

        import arnio as ar

        df = pd.DataFrame({"text": ["cafe\u0301"]})
        frame = ar.from_pandas(df)
        result = ar.normalize_unicode(frame, form="NFC")
        result_df = ar.to_pandas(result)
        assert result_df["text"].iloc[0] == unicodedata.normalize("NFC", "cafe\u0301")

    def test_normalize_unicode_non_string_form_raises(self):
        import pandas as pd
        import pytest

        import arnio as ar

        df = pd.DataFrame({"text": ["hello"]})
        frame = ar.from_pandas(df)
        with pytest.raises(TypeError, match="form must be a string"):
            ar.normalize_unicode(frame, form=["NFC"])

    def test_normalize_unicode_no_pandas_roundtrip(self):
        import pandas as pd

        import arnio as ar
        import arnio.convert as convert_mod

        df = pd.DataFrame({"text": ["café", "naïve"]})
        frame = ar.from_pandas(df)
        original = convert_mod.to_pandas

        def _should_not_be_called(*a, **kw):
            raise AssertionError("normalize_unicode called to_pandas!")

        convert_mod.to_pandas = _should_not_be_called
        try:
            result = ar.normalize_unicode(frame)
        finally:
            convert_mod.to_pandas = original

        result_df = original(result)
        assert result_df["text"].tolist() == ["café", "naïve"]

    def test_normalize_unicode_nfd_form(self):
        import unicodedata

        import pandas as pd

        import arnio as ar

        df = pd.DataFrame({"text": ["café"]})
        frame = ar.from_pandas(df)
        result = ar.normalize_unicode(frame, form="NFD")
        result_df = ar.to_pandas(result)
        assert (
            unicodedata.normalize("NFD", result_df["text"].iloc[0])
            == result_df["text"].iloc[0]
        )

    def test_normalize_unicode_nfkc_form(self):
        import pandas as pd

        import arnio as ar

        df = pd.DataFrame({"text": ["ﬁle"]})
        frame = ar.from_pandas(df)
        result = ar.normalize_unicode(frame, form="NFKC")
        result_df = ar.to_pandas(result)
        assert result_df["text"].iloc[0] == "file"

    def test_normalize_unicode_preserves_nulls(self):
        import pandas as pd

        import arnio as ar

        df = pd.DataFrame({"text": ["café", None, "naïve"]})
        frame = ar.from_pandas(df)
        result = ar.normalize_unicode(frame)
        result_df = ar.to_pandas(result)
        assert result_df["text"].iloc[0] == "café"
        assert pd.isna(result_df["text"].iloc[1])
        assert result_df["text"].iloc[2] == "naïve"

    def test_normalize_unicode_non_string_columns_unchanged(self):
        import pandas as pd

        import arnio as ar

        df = pd.DataFrame({"text": ["café"], "score": [42], "flag": [True]})
        frame = ar.from_pandas(df)
        result = ar.normalize_unicode(frame)
        result_df = ar.to_pandas(result)
        assert result_df["score"].iloc[0] == 42
        assert (
            result_df["flag"].iloc[0] is True
            or result_df["flag"].iloc[0] == True  # noqa: E712
        )

    def test_normalize_unicode_subset_only_targets_specified_columns(self):
        import pandas as pd

        import arnio as ar

        raw_a = "café"
        raw_b = "résumé"
        df = pd.DataFrame({"a": [raw_a], "b": [raw_b]})
        frame = ar.from_pandas(df)
        result = ar.normalize_unicode(frame, subset=["a"])
        result_df = ar.to_pandas(result)
        assert result_df["a"].iloc[0] == "café"
        assert result_df["b"].iloc[0] == raw_b

    def test_normalize_unicode_invalid_form_raises(self):
        import pandas as pd
        import pytest

        import arnio as ar

        df = pd.DataFrame({"text": ["hello"]})
        frame = ar.from_pandas(df)
        with pytest.raises(ValueError, match="Unsupported Unicode normalization form"):
            ar.normalize_unicode(frame, form="XYZ")

    def test_normalize_unicode_large_frame_no_pandas(self):
        import pandas as pd

        import arnio as ar

        n = 10_000
        df = pd.DataFrame({"text": ["café"] * n, "other": list(range(n))})
        frame = ar.from_pandas(df)
        result = ar.normalize_unicode(frame)
        result_df = ar.to_pandas(result)
        assert all(v == "café" for v in result_df["text"])

    def test_normalize_unicode_attrs_deepcopy(self):
        import pandas as pd

        import arnio as ar

        df = pd.DataFrame({"text": ["café"]})
        frame = ar.from_pandas(df)
        frame._attrs = {"meta": {"key": "value"}}
        result = ar.normalize_unicode(frame)
        result._attrs["meta"]["key"] = "mutated"
        assert frame._attrs["meta"]["key"] == "value"

    def test_normalize_unicode_zero_columns(self):
        import pandas as pd

        import arnio as ar

        # Non-empty zero-column frame
        frame_3_0 = ar.from_pandas(pd.DataFrame(index=range(3)))
        assert frame_3_0.shape == (3, 0)
        result_3_0 = ar.normalize_unicode(frame_3_0)
        assert result_3_0.shape == (3, 0)

        # Empty zero-column frame
        frame_0_0 = ar.from_pandas(pd.DataFrame())
        assert frame_0_0.shape == (0, 0)
        result_0_0 = ar.normalize_unicode(frame_0_0)
        assert result_0_0.shape == (0, 0)

        # Normal string-column behavior
        df_normal = pd.DataFrame({"text": ["cafe\u0301"], "other": [1]})
        frame_normal = ar.from_pandas(df_normal)
        result_normal = ar.normalize_unicode(frame_normal)
        assert result_normal.shape == (1, 2)
        assert ar.to_pandas(result_normal)["text"].iloc[0] == "café"

        # attrs preservation on the zero-column path
        frame_3_0_attrs = ar.from_pandas(pd.DataFrame(index=range(3)))
        frame_3_0_attrs._attrs = {"key": "value"}
        result_3_0_attrs = ar.normalize_unicode(frame_3_0_attrs)
        assert result_3_0_attrs.shape == (3, 0)
        assert result_3_0_attrs._attrs == {"key": "value"}

        # attrs deepcopy check on zero-column path
        result_3_0_attrs._attrs["key"] = "mutated"
        assert frame_3_0_attrs._attrs["key"] == "value"


class TestAttrsPreservation:
    """Native cleaning wrappers must carry over ArFrame._attrs via deep copy."""

    def _base_frame(self):
        import pandas as pd

        df = pd.DataFrame(
            {"name": [" Alice ", " Bob "], "age": [20, 30], "score": [1.5, 2.5]}
        )
        frame = ar.from_pandas(df)
        frame._attrs = {"source": "crm", "meta": {"version": 1}}
        return frame

    @pytest.mark.parametrize(
        "op_name, fn",
        [
            ("drop_nulls", lambda f: ar.drop_nulls(f)),
            ("fill_nulls", lambda f: ar.fill_nulls(f, 0)),
            ("drop_duplicates", lambda f: ar.drop_duplicates(f)),
            ("strip_whitespace", lambda f: ar.strip_whitespace(f)),
            (
                "normalize_case",
                lambda f: ar.normalize_case(f, subset=["name"], case_type="lower"),
            ),
            (
                "clip_numeric",
                lambda f: ar.clip_numeric(f, subset=["age"], lower=0, upper=99),
            ),
            ("rename_columns", lambda f: ar.rename_columns(f, {"score": "score2"})),
            ("trim_column_names", lambda f: ar.trim_column_names(f)),
            ("cast_types", lambda f: ar.cast_types(f, {"age": "float64"})),
            ("normalize_unicode", lambda f: ar.normalize_unicode(f, subset=["name"])),
        ],
    )
    def test_attrs_propagated(self, op_name, fn):
        frame = self._base_frame()
        result = fn(frame)
        assert result._attrs == {
            "source": "crm",
            "meta": {"version": 1},
        }, f"{op_name} dropped _attrs"

    @pytest.mark.parametrize(
        "op_name, fn",
        [
            ("drop_nulls", lambda f: ar.drop_nulls(f)),
            ("fill_nulls", lambda f: ar.fill_nulls(f, 0)),
            ("drop_duplicates", lambda f: ar.drop_duplicates(f)),
            ("strip_whitespace", lambda f: ar.strip_whitespace(f)),
            (
                "normalize_case",
                lambda f: ar.normalize_case(f, subset=["name"], case_type="lower"),
            ),
            (
                "clip_numeric",
                lambda f: ar.clip_numeric(f, subset=["age"], lower=0, upper=99),
            ),
            ("rename_columns", lambda f: ar.rename_columns(f, {"score": "score2"})),
            ("trim_column_names", lambda f: ar.trim_column_names(f)),
            ("cast_types", lambda f: ar.cast_types(f, {"age": "float64"})),
            ("normalize_unicode", lambda f: ar.normalize_unicode(f, subset=["name"])),
        ],
    )
    def test_attrs_deep_copy_isolated(self, op_name, fn):
        frame = self._base_frame()
        result = fn(frame)
        result._attrs["meta"]["version"] = 999
        assert (
            frame._attrs["meta"]["version"] == 1
        ), f"{op_name} shared _attrs by reference instead of deep copying"

    def test_drop_duplicates_zero_columns_preserves_attrs(self):
        """drop_duplicates zero-column early return must propagate attrs."""
        import pandas as pd

        from arnio._core import _Frame

        frame = ar.from_pandas(pd.DataFrame({"a": [1, 2, 3]}))
        # Build a genuine zero-column frame with rows intact
        frame._frame = _Frame.from_dict({}, {}, 3)
        frame._attrs = {"source": "crm", "meta": {"version": 1}}
        assert frame.shape == (3, 0)

        result = ar.drop_duplicates(frame)

        assert result._attrs == {
            "source": "crm",
            "meta": {"version": 1},
        }, "drop_duplicates zero-column path dropped _attrs"

    def test_drop_duplicates_zero_columns_attrs_deep_copy_isolated(self):
        """drop_duplicates zero-column result attrs must be a deep copy."""
        import pandas as pd

        from arnio._core import _Frame

        frame = ar.from_pandas(pd.DataFrame({"a": [1, 2, 3]}))
        frame._frame = _Frame.from_dict({}, {}, 3)
        frame._attrs = {"source": "crm", "meta": {"version": 1}}

        result = ar.drop_duplicates(frame)
        result._attrs["meta"]["version"] = 999

        assert (
            frame._attrs["meta"]["version"] == 1
        ), "drop_duplicates zero-column path shared _attrs by reference instead of deep copying"

    def test_empty_attrs_not_propagated(self):
        """When source frame has no attrs, result attrs should also be empty."""
        frame = ar.from_pandas(
            __import__("pandas").DataFrame({"name": ["Alice"], "age": [20]})
        )
        assert frame._attrs == {}
        result = ar.strip_whitespace(frame)
        assert result._attrs == {}


class TestParseBoolStrings:
    def test_parse_basic_bool_strings(self):
        import pandas as pd

        df = pd.DataFrame(
            {
                "active": ["YES", "no", "True", "0"],
            }
        )

        frame = ar.from_pandas(df)

        result = ar.pipeline(
            frame,
            [
                ("parse_bool_strings",),
            ],
        )

        cleaned = ar.to_pandas(result)

        assert cleaned["active"].tolist() == [True, False, True, False]

    def test_parse_bool_strings_preserves_unknown_values(self):
        import pandas as pd

        df = pd.DataFrame(
            {
                "active": ["YES", "maybe", "0"],
            }
        )

        frame = ar.from_pandas(df)

        result = ar.pipeline(
            frame,
            [
                ("parse_bool_strings",),
            ],
        )

        cleaned = ar.to_pandas(result)

        assert cleaned["active"].tolist() == [
            "True",
            "maybe",
            "False",
        ]

    def test_parse_bool_strings_mixed_object_column(self):
        import pandas as pd

        df = pd.DataFrame(
            {
                "active": ["YES", 123, "0"],
            },
            dtype=object,
        )

        frame = ar.from_pandas(df)

        result = ar.pipeline(
            frame,
            [
                ("parse_bool_strings",),
            ],
        )

        cleaned = ar.to_pandas(result)

        assert cleaned["active"].tolist() == [
            "True",
            "123",
            "False",
        ]

    def test_parse_bool_strings_direct_usage(self):
        import pandas as pd

        df = pd.DataFrame(
            {
                "active": [" YES ", "no", "maybe", None],
            }
        )

        frame = ar.from_pandas(df)

        result = ar.parse_bool_strings(frame)

        cleaned = ar.to_pandas(result)

        assert cleaned["active"].tolist()[:3] == [
            "True",
            "False",
            "maybe",
        ]

        assert pd.isna(cleaned["active"].iloc[3])

    def test_parse_bool_strings_subset(self):
        import pandas as pd

        df = pd.DataFrame(
            {
                "active": ["YES", "no"],
                "other": ["YES", "no"],
            },
            dtype=object,
        )

        frame = ar.from_pandas(df)

        result = ar.parse_bool_strings(
            frame,
            subset=["active"],
        )

        cleaned = ar.to_pandas(result)

        assert cleaned["active"].tolist() == [True, False]
        assert cleaned["other"].tolist() == ["YES", "no"]

    def test_parse_bool_strings_subset_skips_existing_bool_columns(self):
        import pandas as pd

        import arnio as ar

        df = pd.DataFrame(
            {
                "flag": [True, False, True],
            }
        )

        frame = ar.from_pandas(df)

        result = ar.parse_bool_strings(
            frame,
            subset=["flag"],
        )

        result_df = ar.to_pandas(result)

        assert result_df["flag"].tolist() == [True, False, True]
        assert str(result_df["flag"].dtype) == "boolean"

    def test_parse_bool_strings_custom_values(self):
        import pandas as pd

        df = pd.DataFrame(
            {
                "status": [
                    "enabled",
                    "disabled",
                    " ENABLED ",
                    " DISABLED ",
                    "maybe",
                ],
            },
            dtype=object,
        )

        frame = ar.from_pandas(df)

        result = ar.parse_bool_strings(
            frame,
            true_values={"enabled"},
            false_values={"disabled"},
        )

        cleaned = ar.to_pandas(result)

        assert cleaned["status"].tolist() == [
            "True",
            "False",
            "True",
            "False",
            "maybe",
        ]

    def test_parse_bool_strings_overlap_rejected(self):
        import pandas as pd

        df = pd.DataFrame(
            {
                "active": ["yes", "no"],
            },
            dtype=object,
        )

        frame = ar.from_pandas(df)

        with pytest.raises(ValueError):
            ar.parse_bool_strings(
                frame,
                true_values={"yes"},
                false_values={" YES "},
            )

    def test_parse_bool_strings_invalid_subset_type(self):
        import pandas as pd

        df = pd.DataFrame(
            {
                "active": ["YES", "no"],
            }
        )

        frame = ar.from_pandas(df)

        with pytest.raises(TypeError):
            ar.parse_bool_strings(frame, subset="active")

    def test_parse_bool_strings_empty_subset(self):
        import pandas as pd

        df = pd.DataFrame(
            {
                "active": ["YES", "no"],
            }
        )

        frame = ar.from_pandas(df)

        with pytest.raises(ValueError):
            ar.parse_bool_strings(frame, subset=[])

    def test_parse_bool_strings_accepts_tuple_subset(self):
        import pandas as pd

        df = pd.DataFrame(
            {
                "active": ["YES", "no"],
                "name": ["Alice", "Bob"],
            }
        )

        frame = ar.from_pandas(df)
        result = ar.parse_bool_strings(frame, subset=("active",))
        out = ar.to_pandas(result)

        assert out["active"].tolist() == [True, False]
        assert out["name"].tolist() == ["Alice", "Bob"]

    def test_parse_bool_strings_missing_subset_column(self):
        import pandas as pd

        df = pd.DataFrame(
            {
                "active": ["YES", "no"],
            }
        )

        frame = ar.from_pandas(df)

        with pytest.raises(ValueError):
            ar.parse_bool_strings(frame, subset=["missing"])

    def test_parse_bool_strings_non_string_true_values_raises(self):
        """Regression: non-string items in true_values must raise TypeError,
        not crash with AttributeError on .strip().lower()."""
        import pandas as pd

        df = pd.DataFrame({"active": ["yes", "no"]}, dtype=object)
        frame = ar.from_pandas(df)

        with pytest.raises(TypeError, match="true_values must contain only strings"):
            ar.parse_bool_strings(frame, true_values={1, "yes"})

    def test_parse_bool_strings_non_string_false_values_raises(self):
        """Regression: non-string items in false_values must raise TypeError,
        not crash with AttributeError on .strip().lower()."""
        import pandas as pd

        df = pd.DataFrame({"active": ["yes", "no"]}, dtype=object)
        frame = ar.from_pandas(df)

        with pytest.raises(TypeError, match="false_values must contain only strings"):
            ar.parse_bool_strings(frame, false_values={0, "no"})

    def test_parse_bool_strings_none_in_custom_values_raises(self):
        """Regression: None in true_values/false_values must raise TypeError."""
        import pandas as pd

        df = pd.DataFrame({"active": ["yes", "no"]}, dtype=object)
        frame = ar.from_pandas(df)

        with pytest.raises(TypeError, match="true_values must contain only strings"):
            ar.parse_bool_strings(frame, true_values={"yes", None})

    def test_parse_bool_strings_bool_in_custom_values_raises(self):
        """Regression: bool items in true_values must raise TypeError."""
        import pandas as pd

        df = pd.DataFrame({"active": ["yes", "no"]}, dtype=object)
        frame = ar.from_pandas(df)

        with pytest.raises(TypeError, match="true_values must contain only strings"):
            ar.parse_bool_strings(frame, true_values={True, "yes"})

    def test_parse_bool_strings_other_non_string_types_in_custom_values_raises(self):
        """Test that custom sets containing floats, ints, or None raise TypeError."""
        import pandas as pd

        df = pd.DataFrame({"active": ["yes", "no"]}, dtype=object)
        frame = ar.from_pandas(df)

        # Float
        with pytest.raises(
            TypeError, match="true_values must contain only strings, got float"
        ):
            ar.parse_bool_strings(frame, true_values={3.14, "yes"})

        with pytest.raises(
            TypeError, match="false_values must contain only strings, got float"
        ):
            ar.parse_bool_strings(frame, false_values={1.5, "no"})

        # Int
        with pytest.raises(
            TypeError, match="true_values must contain only strings, got int"
        ):
            ar.parse_bool_strings(frame, true_values={42, "yes"})

        # NoneType
        with pytest.raises(
            TypeError, match="true_values must contain only strings, got NoneType"
        ):
            ar.parse_bool_strings(frame, true_values={None, "yes"})

    def test_parse_bool_strings_non_iterable_custom_values_raises(self):
        """Test that passing a completely non-iterable type (like int, float, bool) to true_values/false_values raises TypeError."""
        import pandas as pd

        df = pd.DataFrame({"active": ["yes", "no"]}, dtype=object)
        frame = ar.from_pandas(df)

        with pytest.raises(
            TypeError, match="true_values must be a set, list, or tuple of strings"
        ):
            ar.parse_bool_strings(frame, true_values=123)

        with pytest.raises(
            TypeError,
            match="false_values must be a set, list, or tuple of strings",
        ):
            ar.parse_bool_strings(frame, false_values=45.6)

    def test_parse_bool_strings_rejects_mapping_containers(self):
        import pandas as pd

        df = pd.DataFrame({"active": ["yes", "no"]}, dtype=object)
        frame = ar.from_pandas(df)

        with pytest.raises(
            TypeError,
            match="true_values must be a set, list, or tuple of strings",
        ):
            ar.parse_bool_strings(frame, true_values={"yes": 1})

        with pytest.raises(
            TypeError,
            match="false_values must be a set, list, or tuple of strings",
        ):
            ar.parse_bool_strings(frame, false_values={"no": 1})

    def test_parse_bool_strings_overlap_whitespace_and_case_normalization(self):
        """Test that tokens that overlap after case folding and whitespace stripping are correctly rejected."""
        import pandas as pd

        df = pd.DataFrame({"active": ["yes", "no"]}, dtype=object)
        frame = ar.from_pandas(df)

        # Exact overlap
        with pytest.raises(ValueError, match="overlap after normalization: {'yes'}"):
            ar.parse_bool_strings(frame, true_values={"yes"}, false_values={"yes"})

        # Overlap after whitespace stripping and case folding
        with pytest.raises(ValueError, match="overlap after normalization: {'yes'}"):
            ar.parse_bool_strings(frame, true_values={" YES "}, false_values={"yes"})

        with pytest.raises(ValueError, match="overlap after normalization: {'yes'}"):
            ar.parse_bool_strings(frame, true_values={"yes"}, false_values={"Yes"})

    def test_parse_bool_strings_empty_custom_values_sets(self):
        """Test that empty custom true_values and false_values sets are accepted and behave as no-ops for matching."""
        import pandas as pd

        df = pd.DataFrame({"active": ["true", "false", "yes", "no"]}, dtype=object)
        frame = ar.from_pandas(df)

        # Empty true_values means no values are converted to True
        result1 = ar.parse_bool_strings(frame, true_values=set())
        cleaned1 = ar.to_pandas(result1)
        assert cleaned1["active"].tolist() == ["true", "False", "yes", "False"]

        # Empty false_values means no values are converted to False
        result2 = ar.parse_bool_strings(frame, false_values=set())
        cleaned2 = ar.to_pandas(result2)
        assert cleaned2["active"].tolist() == ["True", "false", "True", "no"]

    def test_parse_bool_strings_rejects_bare_strings(self):
        df = pd.DataFrame({"active": ["yes", "no"]}, dtype=object)
        frame = ar.from_pandas(df)

        with pytest.raises(
            TypeError,
            match="true_values must be a set/list/tuple of strings, not a bare string",
        ):
            ar.parse_bool_strings(frame, true_values="yes")

        with pytest.raises(
            TypeError,
            match="false_values must be a set/list/tuple of strings, not a bare string",
        ):
            ar.parse_bool_strings(frame, false_values="no")

        with pytest.raises(
            TypeError,
            match="true_values must be a set/list/tuple of strings, not a bare string",
        ):
            ar.parse_bool_strings(frame, true_values=b"yes")

        with pytest.raises(
            TypeError,
            match="false_values must be a set/list/tuple of strings, not a bare string",
        ):
            ar.parse_bool_strings(frame, false_values=b"no")

    def test_parse_bool_strings_implicit_empty_and_whitespace(self):
        """
        Test that implicit empty strings, whitespace-only strings, and unsupported
        tokens are preserved completely unchanged, as per current design contracts.
        """
        import pandas as pd

        import arnio as ar

        # Scenario 1: Testing Default Tokens (Standard behavior)
        raw_data_default = {
            "bool_col": ["True", "False", "", "   ", "unsupported_token"]
        }
        frame_default = ar.from_pandas(pd.DataFrame(raw_data_default))

        result_default = ar.parse_bool_strings(frame_default)
        df_default = ar.to_pandas(result_default)

        # Checking that empty/whitespace strings are strictly preserved unchanged
        assert df_default["bool_col"].iloc[2] == ""
        assert df_default["bool_col"].iloc[3] == "   "
        assert df_default["bool_col"].iloc[4] == "unsupported_token"

        # Scenario 2: Testing Custom Tokens (As requested by the maintainer)
        raw_data_custom = {"custom_col": ["yea", "nay", "", "   "]}
        frame_custom = ar.from_pandas(pd.DataFrame(raw_data_custom))

        result_custom = ar.parse_bool_strings(
            frame_custom, true_values=["yea"], false_values=["nay"]
        )
        df_custom = ar.to_pandas(result_custom)

        # Checking that for custom tokens, empty/whitespace strings are still completely untouched
        assert df_custom["custom_col"].iloc[2] == ""
        assert df_custom["custom_col"].iloc[3] == "   "

        # Verification that parsing action occurred perfectly for all values
        assert df_custom["custom_col"].to_list() == ["True", "False", "", "   "]


class TestRenameColumns:
    def test_rename(self, sample_csv):
        frame = ar.read_csv(sample_csv)
        result = ar.rename_columns(frame, {"name": "full_name", "age": "years"})
        assert "full_name" in result.columns
        assert "years" in result.columns
        assert "name" not in result.columns

    def test_rename_rejects_non_mapping(self, sample_csv):
        frame = ar.read_csv(sample_csv)

        with pytest.raises(
            TypeError, match="mapping must be a mapping of string keys to strings"
        ):
            ar.rename_columns(frame, [("name", "full_name")])

    def test_rename_rejects_non_string_target(self, sample_csv):
        frame = ar.read_csv(sample_csv)

        with pytest.raises(TypeError, match="values must be non-empty strings"):
            ar.rename_columns(frame, {"name": 123})

    def test_rename_rejects_duplicate_targets(self, sample_csv):
        frame = ar.read_csv(sample_csv)

        with pytest.raises(ValueError, match="target names would create duplicates"):
            ar.rename_columns(frame, {"name": "person", "age": "person"})

    def test_rename_rejects_collision_with_unmapped_column(self, sample_csv):
        frame = ar.read_csv(sample_csv)

        with pytest.raises(ValueError, match="collide with existing columns"):
            ar.rename_columns(frame, {"name": "age"})

    def test_rename_columns_rejects_empty_target(self, sample_csv):
        frame = ar.read_csv(sample_csv)

        with pytest.raises(TypeError, match="non-empty strings"):
            ar.rename_columns(frame, {"name": ""})

    def test_rename_columns_rejects_whitespace_target(self, sample_csv):
        frame = ar.read_csv(sample_csv)

        with pytest.raises(
            TypeError,
            match="values must be non-empty strings",
        ):
            ar.rename_columns(frame, {"name": "   "})

    # --- Regression tests for non-dict mapping validation (bug fix) ---

    def test_rename_rejects_none_with_clear_type_error(self, sample_csv):
        frame = ar.read_csv(sample_csv)
        with pytest.raises(TypeError, match="must be a mapping.*'NoneType'"):
            ar.rename_columns(frame, None)

    def test_rename_rejects_list_of_tuples_with_clear_type_error(self, sample_csv):
        frame = ar.read_csv(sample_csv)
        with pytest.raises(TypeError, match="must be a mapping.*'list'"):
            ar.rename_columns(frame, [("name", "full_name")])

    def test_rename_rejects_integer_with_clear_type_error(self, sample_csv):
        frame = ar.read_csv(sample_csv)
        with pytest.raises(TypeError, match="must be a mapping.*'int'"):
            ar.rename_columns(frame, 42)

    def test_rename_rejects_string_with_clear_type_error(self, sample_csv):
        frame = ar.read_csv(sample_csv)
        with pytest.raises(TypeError, match="must be a mapping.*'str'"):
            ar.rename_columns(frame, "name:full_name")

    def test_rename_valid_dict_still_works(self, sample_csv):
        frame = ar.read_csv(sample_csv)
        result = ar.rename_columns(frame, {"name": "full_name"})
        assert "full_name" in result.columns
        assert "name" not in result.columns

    def test_rename_rejects_non_string_key(self, sample_csv):
        frame = ar.read_csv(sample_csv)
        with pytest.raises(
            TypeError, match="keys must contain only string column names"
        ):
            ar.rename_columns(frame, {123: "new_name"})


class TestTrimColumnNames:
    def test_trim_column_names_basic(self):
        df = pd.DataFrame({" name ": [1], " age ": [2]})
        frame = from_pandas(df)
        result = ar.trim_column_names(frame)
        assert to_pandas(result).columns.tolist() == ["name", "age"]

    def test_trim_column_names_rejects_non_frame_input(self):
        with pytest.raises(TypeError, match="frame must be an ArFrame"):
            ar.trim_column_names([])

    def test_trim_column_names_already_clean(self):
        df = pd.DataFrame({"name": [1], "age": [2]})
        frame = from_pandas(df)
        result = ar.trim_column_names(frame)
        assert to_pandas(result).columns.tolist() == ["name", "age"]

    def test_trim_column_names_mixed(self):
        df = pd.DataFrame({" name": [1], "age ": [2], "score": [3]})
        frame = from_pandas(df)
        result = ar.trim_column_names(frame)
        assert to_pandas(result).columns.tolist() == ["name", "age", "score"]

    def test_trim_column_names_preserves_order(self):
        df = pd.DataFrame({" c ": [1], " b ": [2], " a ": [3]})
        frame = from_pandas(df)
        result = ar.trim_column_names(frame)
        assert to_pandas(result).columns.tolist() == ["c", "b", "a"]

    def test_trim_column_names_duplicate_raises(self):
        df = pd.DataFrame({" name": [1], "name ": [2]})
        frame = from_pandas(df)
        with pytest.raises(ValueError, match="duplicates"):
            ar.trim_column_names(frame)

    def test_trim_column_names_whitespace_only(self):
        df = pd.DataFrame({"   ": [1], " b ": [2]})
        frame = from_pandas(df)
        result = ar.trim_column_names(frame)
        assert to_pandas(result).columns.tolist() == ["", "b"]

    def test_trim_column_names_skips_pandas_round_trip(self, monkeypatch):
        import arnio.convert as convert

        def _boom(*_args, **_kwargs):
            raise AssertionError("trim_column_names should not call to_pandas")

        monkeypatch.setattr(convert, "to_pandas", _boom)
        frame = from_pandas(pd.DataFrame({" name ": [1]}))
        result = ar.trim_column_names(frame)
        assert result.columns == ["name"]


class TestMixedFrameValidation:
    @pytest.mark.parametrize(
        ("func", "kwargs"),
        [
            (
                "combine_columns",
                {"subset": ["a"], "separator": "-", "output_column": "combined"},
            ),
            ("drop_constant_columns", {}),
        ],
    )
    def test_mixed_helpers_reject_non_frame_input(self, func, kwargs):
        with pytest.raises(
            TypeError, match="frame must be an ArFrame or a pandas DataFrame"
        ):
            getattr(ar, func)([], **kwargs)


def test_from_pandas_multiindex_columns_are_stringified():
    df = pd.DataFrame(
        [[1, 2]],
        columns=pd.MultiIndex.from_tuples(
            [
                ("a", "x"),
                ("b", "y"),
            ]
        ),
    )

    frame = ar.from_pandas(df)

    result = ar.to_pandas(frame)

    assert list(result.columns) == ["('a', 'x')", "('b', 'y')"]
    assert not isinstance(result.columns, pd.MultiIndex)

    assert result.iloc[0].tolist() == [1, 2]


class TestCastTypes:
    def test_cast_int_to_string(self, sample_csv):
        frame = ar.read_csv(sample_csv)
        result = ar.cast_types(frame, {"age": "string"})
        assert result.dtypes["age"] == "string"

    def test_cast_int_to_float(self, sample_csv):
        frame = ar.read_csv(sample_csv)
        result = ar.cast_types(frame, {"age": "float64"})
        assert result.dtypes["age"] == "float64"

    def test_cast_unknown_type_rejected(self, sample_csv):
        frame = ar.read_csv(sample_csv)

        with pytest.raises(ar.TypeCastError, match="Unknown target dtype"):
            ar.cast_types(frame, {"age": "decimal"})

    def test_cast_invalid_value_raises_by_default(self):
        frame = ar.from_pandas(pd.DataFrame({"age": ["1", "bad"]}))

        with pytest.raises(ar.TypeCastError, match="Cannot cast column 'age'"):
            ar.cast_types(frame, {"age": "int64"})

    def test_cast_invalid_value_can_be_coerced(self):
        frame = ar.from_pandas(pd.DataFrame({"age": ["1", "bad"]}))

        result = ar.cast_types(frame, {"age": "int64"}, errors="coerce")
        df = ar.to_pandas(result)

        assert result.dtypes["age"] == "int64"
        assert df["age"].iloc[0] == 1
        assert pd.isna(df["age"].iloc[1])

    def test_cast_rejects_invalid_errors_policy(self, sample_csv):
        frame = ar.read_csv(sample_csv)

        with pytest.raises(ValueError, match="errors must be one of"):
            ar.cast_types(frame, {"age": "int64"}, errors="warn")

    @pytest.mark.parametrize(
        "mapping",
        [
            None,
            [("age", "int64")],
            (("age", "int64"),),
            "age=int64",
        ],
    )
    def test_cast_rejects_non_mapping_with_clear_error(self, sample_csv, mapping):
        frame = ar.read_csv(sample_csv)

        with pytest.raises(
            TypeError, match="mapping must be a mapping of string keys to strings"
        ):
            ar.cast_types(frame, mapping)

    def test_cast_bool_rejects_unknown_strings(self):
        frame = ar.from_pandas(pd.DataFrame({"active": ["true", "maybe"]}))

        with pytest.raises(ar.TypeCastError, match="Cannot cast column 'active'"):
            ar.cast_types(frame, {"active": "bool"})

    def test_cast_int_to_string_value_correctness(self, sample_csv):
        # Checks actual values, not just dtype
        frame = ar.read_csv(sample_csv)
        result = ar.cast_types(frame, {"age": "string"})
        df = ar.to_pandas(result)
        assert list(df["age"]) == ["30", "25", "35"]

    def test_cast_int_to_float_value_correctness(self, sample_csv):
        # Checks actual values, not just dtype
        frame = ar.read_csv(sample_csv)
        result = ar.cast_types(frame, {"age": "float64"})
        df = ar.to_pandas(result)
        assert list(df["age"]) == [30.0, 25.0, 35.0]

    def test_cast_float_to_int_raises_by_default(self):
        # float→int is lossy, so it raises TypeCastError by default
        frame = ar.from_pandas(pd.DataFrame({"score": [3.7, 2.1, 1.9]}))
        with pytest.raises(ar.TypeCastError, match="Cannot cast column 'score'"):
            ar.cast_types(frame, {"score": "int64"})

    def test_cast_float_to_int_coerces_to_null(self):
        # with errors="coerce", unparseable floats become null
        frame = ar.from_pandas(pd.DataFrame({"score": [3.7, 2.1]}))
        result = ar.cast_types(frame, {"score": "int64"}, errors="coerce")
        df = ar.to_pandas(result)
        assert result.dtypes["score"] == "int64"
        assert pd.isna(df["score"].iloc[0])

    def test_cast_null_preserved_through_int_to_float(self):
        # Nulls must survive type conversion
        frame = ar.from_pandas(
            pd.DataFrame({"x": pd.array([1, None, 3], dtype="Int64")})
        )
        result = ar.cast_types(frame, {"x": "float64"})
        df = ar.to_pandas(result)
        assert result.dtypes["x"] == "float64"
        assert df["x"].iloc[0] == 1.0
        assert pd.isna(df["x"].iloc[1])
        assert df["x"].iloc[2] == 3.0

    def test_cast_null_preserved_through_string_to_int_coerce(self):
        # Nulls in string column stay null after coerce cast
        frame = ar.from_pandas(pd.DataFrame({"age": ["10", None, "30"]}))
        result = ar.cast_types(frame, {"age": "int64"}, errors="coerce")
        df = ar.to_pandas(result)
        assert pd.isna(df["age"].iloc[1])
        assert df["age"].iloc[0] == 10
        assert df["age"].iloc[2] == 30

    def test_cast_bool_to_int_raises(self):
        # bool→int64 direct cast is not supported, raises TypeCastError
        frame = ar.from_pandas(pd.DataFrame({"flag": [True, False, True]}))
        with pytest.raises(ar.TypeCastError, match="Cannot cast column 'flag'"):
            ar.cast_types(frame, {"flag": "int64"})

    def test_cast_int_to_bool(self):
        # 1 → True, 0 → False
        frame = ar.from_pandas(pd.DataFrame({"flag": [1, 0, 1]}))
        result = ar.cast_types(frame, {"flag": "bool"})
        df = ar.to_pandas(result)
        assert result.dtypes["flag"] == "bool"
        assert list(df["flag"]) == [True, False, True]

    def test_cast_same_type_is_noop(self, sample_csv):
        # Casting to the same type should preserve values unchanged
        frame = ar.read_csv(sample_csv)
        result = ar.cast_types(frame, {"age": "int64"})
        df = ar.to_pandas(result)
        assert result.dtypes["age"] == "int64"
        assert list(df["age"]) == [30, 25, 35]

    def test_cast_nonexistent_column_raises(self, sample_csv):
        # Should raise KeyError clearly identifying the missing column
        frame = ar.read_csv(sample_csv)
        with pytest.raises(KeyError, match="nonexistent"):
            ar.cast_types(frame, {"nonexistent": "int64"})

    def test_cast_multiple_columns_at_once(self, sample_csv):
        # Multiple columns in one call should all be cast correctly
        frame = ar.read_csv(sample_csv)
        result = ar.cast_types(frame, {"age": "float64", "name": "string"})
        assert result.dtypes["age"] == "float64"
        assert result.dtypes["name"] == "string"

    def test_cast_string_to_float_unparseable_raises(self):
        # "abc" cannot be parsed as float64, should raise TypeCastError
        frame = ar.from_pandas(pd.DataFrame({"score": ["1.5", "abc"]}))
        with pytest.raises(ar.TypeCastError, match="Cannot cast column 'score'"):
            ar.cast_types(frame, {"score": "float64"})

    def test_cast_string_to_float_unparseable_coerces(self):
        # with errors="coerce", unparseable strings become null
        frame = ar.from_pandas(pd.DataFrame({"score": ["1.5", "abc"]}))
        result = ar.cast_types(frame, {"score": "float64"}, errors="coerce")
        df = ar.to_pandas(result)
        assert result.dtypes["score"] == "float64"
        assert df["score"].iloc[0] == 1.5
        assert pd.isna(df["score"].iloc[1])

    def test_cast_string_to_float_unparseable_ignores_column(self):
        frame = ar.from_pandas(pd.DataFrame({"score": ["1.5", "abc"]}))

        result = ar.cast_types(frame, {"score": "float64"}, errors="ignore")
        df = ar.to_pandas(result)

        assert result.dtypes["score"] == "string"
        assert list(df["score"]) == ["1.5", "abc"]

    def test_cast_string_to_int_unparseable_raises(self):
        # "hello" cannot be parsed as int64, raises TypeCastError by default
        frame = ar.from_pandas(pd.DataFrame({"age": ["10", "hello"]}))
        with pytest.raises(ar.TypeCastError, match="Cannot cast column 'age'"):
            ar.cast_types(frame, {"age": "int64"})

    def test_cast_string_to_int_unparseable_coerces(self):
        # with errors="coerce", unparseable strings become null
        frame = ar.from_pandas(pd.DataFrame({"age": ["10", "hello"]}))
        result = ar.cast_types(frame, {"age": "int64"}, errors="coerce")
        df = ar.to_pandas(result)
        assert result.dtypes["age"] == "int64"
        assert df["age"].iloc[0] == 10
        assert pd.isna(df["age"].iloc[1])

    def test_cast_ignore_casts_valid_columns_and_preserves_invalid_columns(self):
        frame = ar.from_pandas(
            pd.DataFrame(
                {
                    "age": ["10", "hello"],
                    "score": ["1.5", "2.25"],
                }
            )
        )

        result = ar.cast_types(
            frame,
            {"age": "int64", "score": "float64"},
            errors="ignore",
        )
        df = ar.to_pandas(result)

        assert result.dtypes["age"] == "string"
        assert result.dtypes["score"] == "float64"
        assert list(df["age"]) == ["10", "hello"]
        assert list(df["score"]) == [1.5, 2.25]

    def test_cast_ignore_still_rejects_unknown_target_dtype(self):
        frame = ar.from_pandas(pd.DataFrame({"age": ["10", "20"]}))

        with pytest.raises(ar.TypeCastError, match="Unknown target dtype"):
            ar.cast_types(frame, {"age": "datetime"}, errors="ignore")

    def test_cast_invalid_dtype_string_raises(self):
        # "datetime" is not a supported type, raises TypeCastError
        frame = ar.from_pandas(pd.DataFrame({"age": [1, 2, 3]}))
        with pytest.raises(ar.TypeCastError, match="Unknown target dtype"):
            ar.cast_types(frame, {"age": "datetime"})

    # ------------------------------------------------------------------
    # errors="report" mode
    # ------------------------------------------------------------------

    def test_cast_report_clean_data_returns_empty_failures(self):
        # No bad values → CastReport with empty failures list
        frame = ar.from_pandas(pd.DataFrame({"age": ["1", "2", "3"]}))
        report = ar.cast_types(frame, {"age": "int64"}, errors="report")
        assert isinstance(report, ar.CastReport)
        assert len(report.failures) == 0
        assert not report  # __bool__ is False when no failures

    def test_cast_report_returns_cast_report_type(self):
        frame = ar.from_pandas(pd.DataFrame({"age": ["1", "bad"]}))
        result = ar.cast_types(frame, {"age": "int64"}, errors="report")
        assert isinstance(result, ar.CastReport)
        assert isinstance(result.frame, ar.ArFrame)

    def test_cast_report_int_collects_failure(self):
        frame = ar.from_pandas(pd.DataFrame({"age": ["10", "bad", "30"]}))
        report = ar.cast_types(frame, {"age": "int64"}, errors="report")
        assert len(report.failures) == 1
        assert bool(report)  # __bool__ is True when there are failures

    def test_cast_report_failure_fields_are_correct(self):
        frame = ar.from_pandas(pd.DataFrame({"age": ["10", "bad"]}))
        report = ar.cast_types(frame, {"age": "int64"}, errors="report")
        f = report.failures[0]
        assert f.column == "age"
        assert f.row == 1  # 0-based index
        assert f.value == "bad"
        assert f.target_dtype == "int64"

    def test_cast_report_float_collects_failure(self):
        frame = ar.from_pandas(pd.DataFrame({"score": ["1.5", "abc"]}))
        report = ar.cast_types(frame, {"score": "float64"}, errors="report")
        assert len(report.failures) == 1
        f = report.failures[0]
        assert f.column == "score"
        assert f.row == 1
        assert f.value == "abc"
        assert f.target_dtype == "float64"

    def test_cast_report_bool_collects_failure(self):
        frame = ar.from_pandas(pd.DataFrame({"active": ["true", "maybe"]}))
        report = ar.cast_types(frame, {"active": "bool"}, errors="report")
        assert len(report.failures) == 1
        f = report.failures[0]
        assert f.column == "active"
        assert f.value == "maybe"
        assert f.target_dtype == "bool"

    def test_cast_report_null_not_included_in_failures(self):
        # Nulls are preserved as-is — they are not failures
        frame = ar.from_pandas(pd.DataFrame({"age": ["10", None, "30"]}))
        report = ar.cast_types(frame, {"age": "int64"}, errors="report")
        assert len(report.failures) == 0
        df = ar.to_pandas(report.frame)
        assert pd.isna(df["age"].iloc[1])

    def test_cast_report_mixed_valid_and_invalid(self):
        frame = ar.from_pandas(
            pd.DataFrame({"age": ["1", "bad", "3", "also_bad", "5"]})
        )
        report = ar.cast_types(frame, {"age": "int64"}, errors="report")
        assert len(report.failures) == 2
        assert report.failures[0].row == 1
        assert report.failures[1].row == 3

    def test_cast_report_failure_values_become_null_in_frame(self):
        frame = ar.from_pandas(pd.DataFrame({"age": ["10", "bad", "30"]}))
        report = ar.cast_types(frame, {"age": "int64"}, errors="report")
        df = ar.to_pandas(report.frame)
        assert df["age"].iloc[0] == 10
        assert pd.isna(df["age"].iloc[1])  # failure → null
        assert df["age"].iloc[2] == 30

    def test_cast_report_all_bad_values_no_raise(self):
        # report mode must never raise, even when every value fails
        frame = ar.from_pandas(pd.DataFrame({"age": ["a", "b", "c"]}))
        report = ar.cast_types(frame, {"age": "int64"}, errors="report")
        assert len(report.failures) == 3
        df = ar.to_pandas(report.frame)
        assert df["age"].isna().all()

    def test_cast_report_frame_dtype_matches_target(self):
        frame = ar.from_pandas(pd.DataFrame({"age": ["1", "bad"]}))
        report = ar.cast_types(frame, {"age": "int64"}, errors="report")
        assert report.frame.dtypes["age"] == "int64"

    def test_cast_report_multi_column_collects_across_columns(self):
        frame = ar.from_pandas(
            pd.DataFrame({"age": ["1", "bad"], "score": ["1.5", "abc"]})
        )
        report = ar.cast_types(
            frame, {"age": "int64", "score": "float64"}, errors="report"
        )
        columns = [f.column for f in report.failures]
        assert "age" in columns
        assert "score" in columns

    def test_cast_report_failures_ordered_by_row(self):
        frame = ar.from_pandas(pd.DataFrame({"age": ["bad", "1", "also_bad"]}))
        report = ar.cast_types(frame, {"age": "int64"}, errors="report")
        rows = [f.row for f in report.failures]
        assert rows == sorted(rows)

    def test_cast_report_multi_column_failures_ordered_by_row(self):
        frame = ar.from_pandas(
            pd.DataFrame(
                {
                    "age": ["1", "bad"],
                    "score": ["bad", "2.5"],
                }
            )
        )
        report = ar.cast_types(
            frame, {"age": "int64", "score": "float64"}, errors="report"
        )
        assert [f.row for f in report.failures] == [0, 1]


class TestCleanAPI:
    def test_clean_defaults(self, csv_with_whitespace):
        frame = ar.read_csv(csv_with_whitespace)
        result = ar.clean(frame)
        df = ar.to_pandas(result)

        # strip_whitespace is True by default
        assert df["name"].iloc[0] == "Alice"
        assert df["city"].iloc[1] == "London"

        # drop_nulls and drop_duplicates are False by default
        assert len(frame) == len(result)

    def test_clean_all(self, csv_with_nulls):

        frame = ar.read_csv(csv_with_nulls)

        result = ar.clean(
            frame,
            strip_whitespace=False,
            drop_nulls=True,
        )

        assert len(result) < len(frame)

    @pytest.mark.parametrize("invalid_val", ["yes", 1, None, []])
    def test_clean_invalid_strip_whitespace(self, csv_with_whitespace, invalid_val):
        frame = ar.read_csv(csv_with_whitespace)
        with pytest.raises(TypeError, match="strip_whitespace must be bool or dict"):
            ar.clean(frame, strip_whitespace=invalid_val)

    @pytest.mark.parametrize("invalid_val", ["yes", 1, None, []])
    def test_clean_invalid_drop_nulls(self, csv_with_whitespace, invalid_val):
        frame = ar.read_csv(csv_with_whitespace)
        with pytest.raises(TypeError, match="drop_nulls must be bool or dict"):
            ar.clean(frame, drop_nulls=invalid_val)

    @pytest.mark.parametrize("invalid_val", ["yes", 1, None, []])
    def test_clean_invalid_drop_duplicates(self, csv_with_whitespace, invalid_val):
        frame = ar.read_csv(csv_with_whitespace)
        with pytest.raises(TypeError, match="drop_duplicates must be bool or dict"):
            ar.clean(frame, drop_duplicates=invalid_val)

    def test_clean_drop_nulls_with_subset(self):
        frame = ar.from_dict(
            {
                "name": ["Alice", None, "Charlie"],
                "age": [25, 30, None],
            }
        )

        result = ar.clean(
            frame,
            drop_nulls={"subset": ["name"]},
        )

        data = result.to_dict()

        assert data["name"] == ["Alice", "Charlie"]
        assert data["age"] == [25, None]

    def test_clean_drop_duplicates_keep_last(self):
        frame = ar.from_dict(
            {
                "id": [1, 1, 2],
                "value": ["first", "last", "unique"],
            }
        )

        result = ar.clean(
            frame,
            drop_duplicates={
                "subset": ["id"],
                "keep": "last",
            },
        )

        data = result.to_dict()

        assert data["id"] == [1, 2]
        assert data["value"] == ["last", "unique"]

    def test_clean_strip_whitespace_subset(self):
        frame = ar.from_dict(
            {
                "name": ["  Alice  ", "  Bob  "],
                "city": ["  NYC  ", "  LA  "],
            }
        )

        result = ar.clean(
            frame,
            strip_whitespace={"subset": ["name"]},
        )

        data = result.to_dict()

        assert data["name"] == ["Alice", "Bob"]

        # city should remain untouched
        assert data["city"] == ["  NYC  ", "  LA  "]

    def test_clean_invalid_option_type(self):
        frame = ar.from_dict(
            {
                "name": ["Alice"],
            }
        )

        with pytest.raises(TypeError):
            ar.clean(
                frame,
                drop_nulls="invalid",
            )


class TestFilterRows:
    def test_filter_rows_missing_column_raises_clear_error(self):
        df = pd.DataFrame({"age": [20, 30]})

        with pytest.raises(ValueError, match="Unknown column: missing"):
            ar.filter_rows(df, "missing", ">", 10)

    def test_filter_rows_missing_column_raises_clear_error_for_arframe(self):
        frame = ar.from_pandas(pd.DataFrame({"age": [20, 30]}))

        with pytest.raises(ValueError, match="Unknown column: missing"):
            ar.filter_rows(frame, "missing", ">", 10)

    def test_filter_rows_valid_column_still_works(self):
        df = pd.DataFrame({"age": [20, 30]})

        result = ar.filter_rows(df, "age", ">", 20)

        assert len(result) == 1
        assert result.iloc[0]["age"] == 30

    def test_filter_rows_with_missing_values_does_not_crash(self):
        import numpy as np
        import pandas as pd

        df = pd.DataFrame({"age": [20, 30, np.nan, pd.NA, None]})

        result = ar.filter_rows(df, "age", ">", 25)

        assert len(result) == 1
        assert result.iloc[0]["age"] == 30

    def test_filter_rows_arframe_resets_row_positions(self):
        frame = ar.from_pandas(pd.DataFrame({"age": [10, 30, 40]}))

        result = ar.filter_rows(frame, "age", ">", 20)
        df = ar.to_pandas(result)

        assert list(df.index) == [0, 1]
        assert list(df["age"]) == [30, 40]

    def test_filter_rows_invalid_comparison_raises_column_aware_type_error(self):
        df = pd.DataFrame({"name": ["Alice", "Bob"]})

        with pytest.raises(
            TypeError, match="filter_rows: cannot compare column 'name'"
        ):
            ar.filter_rows(df, "name", ">", 1)

    def test_filter_rows_rejects_list_like_values(self):
        df = pd.DataFrame({"a": [1, 2, 3]})
        list_like_values = [
            [1, 2],
            (1, 2),
            {"a": 1},
            pd.Series([1, 2]),
            pd.Index([1, 2]),
            np.array([1, 2]),
        ]

        for value in list_like_values:
            with pytest.raises(TypeError, match="filter_rows value must be a scalar"):
                ar.filter_rows(df, "a", "==", value)

    def test_filter_rows_non_string_column_raises_type_error(self):
        frame = ar.from_pandas(pd.DataFrame({"x": [1, 2, 3]}))

        with pytest.raises(TypeError, match="column must be a non-empty string"):
            ar.filter_rows(frame, column=123, op="==", value=1)

    def test_filter_rows_empty_string_column_raises_type_error(self):
        frame = ar.from_pandas(pd.DataFrame({"x": [1, 2, 3]}))

        with pytest.raises(TypeError, match="column must be a non-empty string"):
            ar.filter_rows(frame, column="", op="==", value=1)

    def test_filter_rows_non_string_op_raises_type_error(self):
        frame = ar.from_pandas(pd.DataFrame({"x": [1, 2, 3]}))

        with pytest.raises(TypeError, match="op must be a string"):
            ar.filter_rows(frame, column="x", op=["=="], value=1)


class TestMappingValidation:
    def test_rename_columns_rejects_invalid_mapping_value_type(self, sample_csv):
        frame = ar.read_csv(sample_csv)

        with pytest.raises(TypeError, match="mapping values must be non-empty strings"):
            ar.rename_columns(frame, {"name": 123})

    def test_replace_values_rejects_missing_column(self, sample_csv):
        frame = ar.read_csv(sample_csv)

        with pytest.raises(KeyError, match="Column 'missing' not found"):
            ar.replace_values(frame, {"Alice": "Alicia"}, column="missing")

    def test_replace_values_rejects_non_mapping_input(self, sample_csv):
        frame = ar.read_csv(sample_csv)

        with pytest.raises(TypeError, match="mapping must be a dict-like mapping"):
            ar.replace_values(frame, [("Alice", "Alicia")])

    def test_replace_values_rejects_empty_mapping(self, sample_csv):
        frame = ar.read_csv(sample_csv)

        with pytest.raises(ValueError, match="mapping must not be empty"):
            ar.replace_values(frame, {})

    def test_rename_columns_rejects_non_mapping_input(self, sample_csv):
        frame = ar.read_csv(sample_csv)

        with pytest.raises(TypeError, match="mapping must be a mapping"):
            ar.rename_columns(frame, [("name", "full_name")])

    def test_cast_types_rejects_non_mapping_input(self, sample_csv):
        frame = ar.read_csv(sample_csv)

        with pytest.raises(TypeError, match="mapping must be a mapping"):
            ar.cast_types(frame, [("age", "string")])


class TestReplaceValues:
    def test_replace_values_null_key_replaces_existing_nulls_in_target_column(self):
        import numpy as np

        frame = ar.from_pandas(
            pd.DataFrame(
                {
                    "name": ["Alice", None, pd.NA],
                    "city": [None, "Paris", None],
                }
            )
        )

        result = ar.replace_values(frame, {np.nan: "Unknown"}, column="name")
        df = ar.to_pandas(result)

        assert list(df["name"]) == ["Alice", "Unknown", "Unknown"]
        assert pd.isna(df.loc[0, "city"])
        assert df.loc[1, "city"] == "Paris"
        assert pd.isna(df.loc[2, "city"])

    def test_replace_values_null_replacement_creates_real_nulls(self):
        frame = ar.from_pandas(
            pd.DataFrame({"status": ["active", "inactive", "active"]})
        )

        result = ar.replace_values(frame, {"inactive": None})
        df = ar.to_pandas(result)

        assert list(df["status"].iloc[[0, 2]]) == ["active", "active"]
        assert pd.isna(df.loc[1, "status"])

    def test_replace_values_supports_pd_na_key_and_value(self):
        frame = ar.from_pandas(
            pd.DataFrame({"score": [1, None, 3], "flag": ["ok", "missing", "ok"]})
        )

        result = ar.replace_values(frame, {pd.NA: 0, "missing": pd.NA})
        df = ar.to_pandas(result)

        assert list(df["score"]) == [1, 0, 3]
        assert df.loc[0, "flag"] == "ok"
        assert pd.isna(df.loc[1, "flag"])
        assert df.loc[2, "flag"] == "ok"

    def test_replace_values_tuple_mapping_key_does_not_crash(self):
        frame = ar.from_pandas(pd.DataFrame({"col": ["A", "B", "C"]}))

        with pytest.raises(TypeError, match="non-scalar mapping keys"):
            ar.replace_values(
                frame,
                {("A", "B"): "X"},
                column="col",
            )

    def test_replace_values_mixed_tuple_and_null_keys(self):
        frame = ar.from_pandas(pd.DataFrame({"col": ["A", np.nan, "C"]}))

        with pytest.raises(TypeError, match="non-scalar mapping keys"):
            ar.replace_values(
                frame,
                {
                    ("A", "B"): "X",
                    np.nan: "missing",
                },
                column="col",
            )

    def test_replace_values_error_message_includes_key_type(self):
        """TypeError message must name the offending key type."""
        frame = ar.from_pandas(pd.DataFrame({"col": ["A"]}))

        with pytest.raises(TypeError, match="tuple"):
            ar.replace_values(frame, {(1, 2): "X"})

    def test_replace_values_scalar_keys_still_work_after_validation(self):
        """Valid scalar mappings must be completely unaffected by the new check."""
        frame = ar.from_pandas(pd.DataFrame({"col": ["A", "B", "C"]}))

        result = ar.replace_values(frame, {"A": "Z"}, column="col")
        df = ar.to_pandas(result)

        assert list(df["col"]) == ["Z", "B", "C"]

    def test_replace_values_pandas_dataframe_input_returns_dataframe(self):
        df = pd.DataFrame({"status": ["active", "inactive"], "flag": ["ok", "ok"]})

        result = ar.replace_values(df, {"inactive": "paused"}, column="status")

        assert isinstance(result, pd.DataFrame)
        assert result["status"].tolist() == ["active", "paused"]
        assert result["flag"].tolist() == ["ok", "ok"]
        assert df["status"].tolist() == ["active", "inactive"]


class TestRoundNumericColumns:
    def test_round_subset_missing_column_raises_clear_error(self):
        import pandas as pd

        df = pd.DataFrame(
            {
                "price": [1.234, 5.678],
                "name": ["Alice", "Bob"],
            }
        )

        frame = ar.from_pandas(df)

        with pytest.raises(
            ValueError,
            match=r"round_numeric_columns: unknown column\(s\) in subset",
        ):
            ar.round_numeric_columns(
                frame,
                subset=["price", "missing_column"],
                decimals=1,
            )

    def test_round_subset_with_non_numeric(self):
        import pandas as pd

        df = pd.DataFrame({"name": ["john"], "score": [98.765]})
        frame = ar.from_pandas(df)
        result = ar.round_numeric_columns(
            frame,
            subset=["name", "score"],
            decimals=1,
        )
        result_df = ar.to_pandas(result)
        assert list(result_df["name"]) == ["john"]
        assert list(result_df["score"]) == [98.8]

    def test_round_all_numeric(self):
        import pandas as pd

        df = pd.DataFrame({"a": [1.123, 2.456], "b": [3.789, 4.0]})
        frame = ar.from_pandas(df)
        result = ar.round_numeric_columns(frame, decimals=1)
        result_df = ar.to_pandas(result)
        assert list(result_df["a"]) == [1.1, 2.5]
        assert list(result_df["b"]) == [3.8, 4.0]

    def test_round_subset(self):
        import pandas as pd

        df = pd.DataFrame({"a": [1.123, 2.456], "b": [3.789, 4.0]})
        frame = ar.from_pandas(df)
        result = ar.round_numeric_columns(frame, subset=["a"], decimals=1)
        result_df = ar.to_pandas(result)
        assert list(result_df["a"]) == [1.1, 2.5]
        assert list(result_df["b"]) == [3.789, 4.0]

    def test_round_mixed_types(self):
        import pandas as pd

        df = pd.DataFrame({"a": [1.123, 2.456], "c": ["str1", "str2"]})
        frame = ar.from_pandas(df)
        result = ar.round_numeric_columns(frame, decimals=1)
        result_df = ar.to_pandas(result)
        assert list(result_df["a"]) == [1.1, 2.5]
        assert list(result_df["c"]) == ["str1", "str2"]

    def test_round_numeric_columns_with_arframe_input(self):
        df = pd.DataFrame({"a": [1.123, 2.456], "b": [3.789, 4.0]})
        frame = ar.from_pandas(df)

        result = ar.round_numeric_columns(frame, decimals=1)

        assert isinstance(result, ar.ArFrame)
        result_df = ar.to_pandas(result)
        assert list(result_df["a"]) == [1.1, 2.5]
        assert list(result_df["b"]) == [3.8, 4.0]

    def test_round_numeric_columns_with_dataframe_input(self):
        df = pd.DataFrame({"a": [1.123, 2.456], "b": [3.789, 4.0]})

        result = ar.round_numeric_columns(df, decimals=1)

        assert isinstance(result, pd.DataFrame)
        assert list(result["a"]) == [1.1, 2.5]
        assert list(result["b"]) == [3.8, 4.0]

    def test_missing_column(self):
        import pandas as pd

        df = pd.DataFrame({"a": [1.123]})
        frame = ar.from_pandas(df)
        with pytest.raises(
            ValueError,
            match=r"round_numeric_columns: unknown column\(s\) in subset: \['missing_col'\]",
        ):
            ar.round_numeric_columns(frame, subset=["missing_col"])

    def test_with_nulls(self):
        import numpy as np
        import pandas as pd

        df = pd.DataFrame({"a": [1.123, np.nan, 2.456]})
        frame = ar.from_pandas(df)
        result = ar.round_numeric_columns(frame, decimals=1)
        result_df = ar.to_pandas(result)
        assert result_df["a"].isna().iloc[1]
        assert result_df["a"].iloc[0] == 1.1
        assert result_df["a"].iloc[2] == 2.5

    def test_invalid_subset_type(self):
        import pandas as pd
        import pytest

        df = pd.DataFrame({"a": [1.123]})
        frame = ar.from_pandas(df)
        with pytest.raises(
            TypeError, match="subset must be a sequence of column names"
        ):
            ar.round_numeric_columns(frame, subset="a")

    def test_invalid_decimals_type(self):
        import pandas as pd
        import pytest

        df = pd.DataFrame({"a": [1.123]})
        frame = ar.from_pandas(df)
        with pytest.raises(TypeError, match="decimals must be an integer"):
            ar.round_numeric_columns(frame, decimals="2")

    def test_decimals_rejects_bool(self):
        import pandas as pd
        import pytest

        df = pd.DataFrame({"a": [1.123]})
        frame = ar.from_pandas(df)
        with pytest.raises(TypeError, match="decimals must be an integer"):
            ar.round_numeric_columns(frame, decimals=True)

    def test_round_numeric_columns_pandas_input_returns_dataframe(self):
        df = pd.DataFrame({"a": [1.234, 5.678], "label": ["x", "y"]})

        result = ar.round_numeric_columns(df, decimals=1)

        assert isinstance(result, pd.DataFrame)
        assert result["a"].tolist() == [1.2, 5.7]
        assert result["label"].tolist() == ["x", "y"]
        assert df["a"].tolist() == [1.234, 5.678]

    def test_round_tuple_subset(self):
        import pandas as pd

        df = pd.DataFrame({"a": [1.123, 2.456], "b": [3.789, 4.0]})

        frame = ar.from_pandas(df)

        result = ar.round_numeric_columns(
            frame,
            subset=("a",),
            decimals=1,
        )

        result_df = ar.to_pandas(result)

        assert list(result_df["a"]) == [1.1, 2.5]
        assert list(result_df["b"]) == [3.789, 4.0]

    def test_round_tuple_subset_non_string_member(self):
        import pandas as pd

        df = pd.DataFrame({"a": [1.123]})

        frame = ar.from_pandas(df)

        with pytest.raises(
            TypeError,
            match="string column names",
        ):
            ar.round_numeric_columns(
                frame,
                subset=("a", 123),
                decimals=1,
            )


class TestCombineColumns:
    def test_combines_columns_with_separator(self):
        import pandas as pd

        df = pd.DataFrame({"first": ["Alice", "Bob"], "last": ["Smith", "Jones"]})
        frame = ar.from_pandas(df)

        result = ar.combine_columns(
            frame,
            subset=["first", "last"],
            separator=" ",
            output_column="full_name",
        )
        result_df = ar.to_pandas(result)

        assert list(result_df["full_name"]) == ["Alice Smith", "Bob Jones"]

    def test_combines_all_columns_by_default(self):
        import pandas as pd

        df = pd.DataFrame({"a": [1, 2], "b": ["x", "y"]})
        frame = ar.from_pandas(df)

        result = ar.combine_columns(
            frame,
            separator=",",
            output_column="combined",
        )
        result_df = ar.to_pandas(result)

        assert list(result_df["combined"]) == ["1,x", "2,y"]

    def test_preserves_null_rows(self):
        import pandas as pd

        df = pd.DataFrame({"a": [None, "hello"], "b": [None, "world"]})
        frame = ar.from_pandas(df)

        result = ar.combine_columns(
            frame,
            subset=["a", "b"],
            separator=" ",
            output_column="combined",
        )
        result_df = ar.to_pandas(result)

        assert pd.isna(result_df["combined"]).iloc[0]
        assert result_df["combined"].iloc[1] == "hello world"

    def test_combine_columns_mixed_null_and_non_null_columns(self):
        import pandas as pd

        df = pd.DataFrame(
            {
                "a": ["hello", None, "foo", None],
                "b": [None, "world", "bar", None],
            }
        )

        frame = ar.from_pandas(df)

        result = ar.combine_columns(
            frame,
            subset=["a", "b"],
            separator=" ",
            output_column="combined",
        )

        result_df = ar.to_pandas(result)

        assert result_df["combined"].iloc[0] == "hello "
        assert result_df["combined"].iloc[1] == " world"
        assert result_df["combined"].iloc[2] == "foo bar"
        assert pd.isna(result_df["combined"].iloc[3])

        # dtype contract
        assert str(result_df["combined"].dtype) == "string"

    def test_missing_subset_column_raises(self):
        import pandas as pd

        df = pd.DataFrame({"a": [1]})
        frame = ar.from_pandas(df)

        with pytest.raises(KeyError, match="Missing columns for combine_columns"):
            ar.combine_columns(
                frame,
                subset=["a", "missing"],
                separator="-",
                output_column="combined",
            )

    def test_output_column_already_exists_warns(self):
        import pandas as pd

        df = pd.DataFrame({"a": [1], "combined": ["old"]})
        frame = ar.from_pandas(df)

        with pytest.raises(ValueError, match="Output column 'combined' already exists"):
            ar.combine_columns(
                frame,
                subset=["a"],
                separator="-",
                output_column="combined",
            )

    def test_combine_columns_pandas_input_returns_dataframe(self):
        df = pd.DataFrame({"first": ["Alice", "Bob"], "last": ["Smith", "Jones"]})

        result = ar.combine_columns(
            df,
            subset=["first", "last"],
            separator=" ",
            output_column="full_name",
        )

        assert isinstance(result, pd.DataFrame)
        assert result["full_name"].tolist() == ["Alice Smith", "Bob Jones"]
        assert "full_name" not in df.columns


class TestCombineColumnsNativeRegression:
    def test_native_matches_pandas_reference(self):
        import numpy as np
        import pandas as pd

        rng = np.random.default_rng(42)
        n = 10_000
        # Use integers and strings to avoid float formatting differences between C++ and pandas
        df = pd.DataFrame(
            {
                "col_a": rng.integers(0, 100, size=n).astype(str).tolist(),
                "col_b": rng.integers(0, 100, size=n).astype(str).tolist(),
                "label": ["str"] * n,
            }
        )
        # Introduce some nulls
        for idx in rng.integers(0, n, size=200):
            df.at[idx, "col_a"] = None
        for idx in rng.integers(0, n, size=200):
            df.at[idx, "label"] = None

        # Add some empty strings
        for idx in rng.integers(0, n, size=200):
            df.at[idx, "col_b"] = ""

        frame = ar.from_pandas(df)
        native_df = ar.to_pandas(
            ar.combine_columns(frame, subset=["col_a", "label", "col_b"], separator="-")
        )

        # Reference: pandas
        ref = df.copy()
        subset_columns = ["col_a", "label", "col_b"]
        combined = ref[subset_columns].astype("string").fillna("").agg("-".join, axis=1)
        null_mask = ref[subset_columns].isna().all(axis=1)
        combined = combined.mask(null_mask, pd.NA)
        ref["combined"] = combined

        pd.testing.assert_series_equal(
            native_df["combined"], ref["combined"], check_dtype=False, check_names=False
        )
        assert len(native_df) == len(ref)

    def test_native_all_nulls_row_produces_null(self):
        import pandas as pd

        df = pd.DataFrame({"a": [None, "hello"], "b": [None, "world"]})
        frame = ar.from_pandas(df)
        result = ar.to_pandas(
            ar.combine_columns(frame, subset=["a", "b"], separator="-")
        )
        assert pd.isna(result["combined"]).iloc[0]
        assert result["combined"].iloc[1] == "hello-world"

    def test_native_empty_string_separator(self):
        import pandas as pd

        df = pd.DataFrame({"a": ["1", "2"], "b": ["3", "4"]})
        frame = ar.from_pandas(df)
        result = ar.to_pandas(
            ar.combine_columns(frame, subset=["a", "b"], separator="")
        )
        assert list(result["combined"]) == ["13", "24"]

    def test_native_numeric_formatting(self):
        import pandas as pd

        df = pd.DataFrame({"a": [123, 456], "b": [1.5, 0.0]})
        frame = ar.from_pandas(df)
        result = ar.to_pandas(
            ar.combine_columns(frame, subset=["a", "b"], separator="|")
        )
        # The native path now uses shortest-round-trip float formatting (like Python's str()),
        # which matches the pandas astype('string') contract.
        # 1.5 stays "1.5", 0.0 becomes "0.0", integers stay as integers.
        assert list(result["combined"]) == ["123|1.5", "456|0.0"]

    def test_native_bool_formatting(self):
        import pandas as pd

        df = pd.DataFrame({"a": [True, False], "b": [False, True]})
        frame = ar.from_pandas(df)
        result = ar.to_pandas(
            ar.combine_columns(frame, subset=["a", "b"], separator="|")
        )
        # The native path should format booleans as True / False to match
        # the pandas astype('string') contract.
        assert list(result["combined"]) == ["True|False", "False|True"]

    def test_unsupported_input_type_raises(self):
        with pytest.raises(
            TypeError, match="frame must be an ArFrame or a pandas DataFrame"
        ):
            ar.combine_columns({"a": [1, 2]}, subset=["a"])


class TestSafeDivideColumns:
    def test_normal_division(self, tmp_path):
        path = tmp_path / "data.csv"
        path.write_text("revenue,cost\n100,50\n200,100\n300,150\n")
        frame = ar.read_csv(path)
        result = ar.safe_divide_columns(
            frame, numerator="revenue", denominator="cost", output_column="ratio"
        )
        df = ar.to_pandas(result)
        assert df["ratio"].iloc[0] == 2.0
        assert df["ratio"].iloc[1] == 2.0
        assert df["ratio"].iloc[2] == 2.0

    def test_division_by_zero(self, tmp_path):
        path = tmp_path / "data.csv"
        path.write_text("revenue,cost\n100,0\n200,100\n300,0\n")
        frame = ar.read_csv(path)
        result = ar.safe_divide_columns(
            frame, numerator="revenue", denominator="cost", output_column="ratio"
        )
        df = ar.to_pandas(result)
        assert df["ratio"].iloc[0] == 0.0
        assert df["ratio"].iloc[2] == 0.0

    def test_null_inputs(self, tmp_path):
        path = tmp_path / "data.csv"
        path.write_text("revenue,cost\n100,\n200,100\n300,\n")
        frame = ar.read_csv(path)
        result = ar.safe_divide_columns(
            frame, numerator="revenue", denominator="cost", output_column="ratio"
        )
        df = ar.to_pandas(result)
        assert df["ratio"].iloc[0] == 0.0
        assert df["ratio"].iloc[2] == 0.0

    def test_missing_numerator_column(self, tmp_path):
        path = tmp_path / "data.csv"
        path.write_text("revenue,cost\n100,50\n")
        frame = ar.read_csv(path)
        with pytest.raises(ValueError, match="Numerator column"):
            ar.safe_divide_columns(
                frame,
                numerator="nonexistent",
                denominator="cost",
                output_column="ratio",
            )

    def test_missing_denominator_column(self, tmp_path):
        path = tmp_path / "data.csv"
        path.write_text("revenue,cost\n100,50\n")
        frame = ar.read_csv(path)
        with pytest.raises(ValueError, match="Denominator column"):
            ar.safe_divide_columns(
                frame,
                numerator="revenue",
                denominator="nonexistent",
                output_column="ratio",
            )

    def test_numerator_must_be_string(self, tmp_path):
        path = tmp_path / "data.csv"
        path.write_text("revenue,cost\n100,50\n")
        frame = ar.read_csv(path)

        with pytest.raises(TypeError, match="numerator must be a string column name"):
            ar.safe_divide_columns(
                frame,
                numerator=123,
                denominator="cost",
                output_column="ratio",
            )

    def test_denominator_must_be_string(self, tmp_path):
        path = tmp_path / "data.csv"
        path.write_text("revenue,cost\n100,50\n")
        frame = ar.read_csv(path)

        with pytest.raises(TypeError, match="denominator must be a string column name"):
            ar.safe_divide_columns(
                frame,
                numerator="revenue",
                denominator=None,
                output_column="ratio",
            )

    def test_valid_string_columns_still_work(self, tmp_path):
        path = tmp_path / "data.csv"
        path.write_text("revenue,cost\n100,50\n")
        frame = ar.read_csv(path)

        result = ar.safe_divide_columns(
            frame,
            numerator="revenue",
            denominator="cost",
            output_column="ratio",
        )

        df = ar.to_pandas(result)
        assert df["ratio"].iloc[0] == 2.0

    def test_output_column_already_exists(self, tmp_path):
        path = tmp_path / "data.csv"
        path.write_text("revenue,cost,ratio\n100,50,99\n200,100,99\n")
        frame = ar.read_csv(path)
        with pytest.raises(ValueError, match="Output column 'ratio' already exists"):
            ar.safe_divide_columns(
                frame, numerator="revenue", denominator="cost", output_column="ratio"
            )

    def test_string_zero_denominator_is_treated_as_zero(self):
        frame = ar.from_pandas(
            pd.DataFrame({"revenue": ["100", "200"], "cost": ["0", "50"]})
        )

        result = ar.safe_divide_columns(
            frame,
            numerator="revenue",
            denominator="cost",
            output_column="ratio",
        )
        df = ar.to_pandas(result)

        assert list(df["ratio"]) == [0.0, 4.0]

    def test_nonnumeric_numerator_raises(self):
        frame = ar.from_pandas(pd.DataFrame({"revenue": ["oops"], "cost": ["10"]}))

        with pytest.raises(ValueError, match="Numerator column 'revenue'"):
            ar.safe_divide_columns(
                frame,
                numerator="revenue",
                denominator="cost",
                output_column="ratio",
            )

    def test_nonnumeric_denominator_raises(self):
        frame = ar.from_pandas(pd.DataFrame({"revenue": ["100"], "cost": ["oops"]}))

        with pytest.raises(ValueError, match="Denominator column 'cost'"):
            ar.safe_divide_columns(
                frame,
                numerator="revenue",
                denominator="cost",
                output_column="ratio",
            )

    def test_zero_and_null_semantics_are_preserved(self):
        frame = ar.from_pandas(
            pd.DataFrame(
                {
                    "revenue": [10, 10, 0, 0, None, 10, None],
                    "cost": [2, 0, 10, 0, 10, None, None],
                }
            )
        )

        result = ar.safe_divide_columns(
            frame,
            numerator="revenue",
            denominator="cost",
            output_column="ratio",
            fill_value=-1.0,
        )
        df = ar.to_pandas(result)

        assert list(df["ratio"]) == [5.0, -1.0, 0.0, -1.0, -1.0, -1.0, -1.0]

    def test_float_and_negative_values_are_preserved(self):
        frame = ar.from_pandas(
            pd.DataFrame(
                {
                    "revenue": [7.5, -9.0, 9.0],
                    "cost": [2.5, 3.0, -3.0],
                }
            )
        )

        result = ar.safe_divide_columns(
            frame,
            numerator="revenue",
            denominator="cost",
            output_column="ratio",
        )
        df = ar.to_pandas(result)

        assert list(df["ratio"]) == [3.0, -3.0, -3.0]

    def test_pandas_dataframe_input_returns_pandas_dataframe(self):
        frame = pd.DataFrame({"revenue": [100, 200], "cost": [25, 0]})

        result = ar.safe_divide_columns(
            frame,
            numerator="revenue",
            denominator="cost",
            output_column="ratio",
        )

        assert isinstance(result, pd.DataFrame)
        assert list(result["ratio"]) == [4.0, 0.0]

    def test_native_numeric_arframe_path_avoids_pandas_roundtrip(self, monkeypatch):
        frame = ar.from_pandas(
            pd.DataFrame(
                {
                    "revenue": [100, 200],
                    "cost": [10, 20],
                }
            )
        )

        from arnio import convert

        original_to_pandas = convert.to_pandas

        def fail_to_pandas(_):
            raise AssertionError("native numeric path should avoid to_pandas")

        monkeypatch.setattr(convert, "to_pandas", fail_to_pandas)

        result = ar.safe_divide_columns(
            frame,
            numerator="revenue",
            denominator="cost",
            output_column="ratio",
        )

        df = original_to_pandas(result)

        assert list(df["ratio"]) == [10.0, 10.0]

    # --- Regression tests for string zero denominators (bug fix) ---

    def test_string_zero_denominator_uses_fill_value(self):
        # String "0" must be treated as zero — not silently passed through.
        frame = ar.from_pandas(
            pd.DataFrame({"num": [10.0, 20.0, 30.0], "den": ["0", "2", "0"]})
        )
        result = ar.safe_divide_columns(
            frame,
            numerator="num",
            denominator="den",
            output_column="ratio",
            fill_value=-1.0,
        )
        df = ar.to_pandas(result)
        assert list(df["ratio"]) == [-1.0, 10.0, -1.0]

    def test_string_zero_point_zero_denominator_uses_fill_value(self):
        # String "0.0" must also be treated as zero.
        frame = ar.from_pandas(pd.DataFrame({"num": [10.0, 20.0], "den": ["0.0", "4"]}))
        result = ar.safe_divide_columns(
            frame,
            numerator="num",
            denominator="den",
            output_column="ratio",
            fill_value=0.0,
        )
        df = ar.to_pandas(result)
        assert df["ratio"].iloc[0] == 0.0
        assert df["ratio"].iloc[1] == 5.0

    def test_numeric_zero_denominator_uses_fill_value(self):
        # Numeric 0 (int) must still be caught — regression guard.
        frame = ar.from_pandas(pd.DataFrame({"num": [10.0, 20.0], "den": [0, 4]}))
        result = ar.safe_divide_columns(
            frame,
            numerator="num",
            denominator="den",
            output_column="ratio",
            fill_value=-99.0,
        )
        df = ar.to_pandas(result)
        assert df["ratio"].iloc[0] == -99.0
        assert df["ratio"].iloc[1] == 5.0

    def test_nullable_denominator_uses_fill_value(self):
        # None / pd.NA denominator must use fill_value, not raise.
        frame = ar.from_pandas(
            pd.DataFrame({"num": [10.0, 20.0, 30.0], "den": [None, 4.0, None]})
        )
        result = ar.safe_divide_columns(
            frame,
            numerator="num",
            denominator="den",
            output_column="ratio",
            fill_value=0.0,
        )
        df = ar.to_pandas(result)
        assert df["ratio"].iloc[0] == 0.0
        assert df["ratio"].iloc[1] == 5.0
        assert df["ratio"].iloc[2] == 0.0

    def test_valid_nonzero_numeric_string_denominator_divides_correctly(self):
        # String "2" and "4" must produce valid division, not be masked.
        frame = ar.from_pandas(pd.DataFrame({"num": [10.0, 20.0], "den": ["2", "4"]}))
        result = ar.safe_divide_columns(
            frame,
            numerator="num",
            denominator="den",
            output_column="ratio",
            fill_value=-1.0,
        )
        df = ar.to_pandas(result)
        assert df["ratio"].iloc[0] == 5.0
        assert df["ratio"].iloc[1] == 5.0

    def test_invalid_non_null_denominator_string_raises(self):
        # A non-null, non-numeric string like "abc" must raise ValueError,
        # not be silently treated as null.
        frame = ar.from_pandas(pd.DataFrame({"num": [10.0, 20.0], "den": ["abc", "4"]}))
        with pytest.raises(
            ValueError, match="Denominator column 'den' contains non-numeric"
        ):
            ar.safe_divide_columns(
                frame, numerator="num", denominator="den", output_column="ratio"
            )

    def test_fill_value_bool_raises(self):
        frame = ar.from_pandas(pd.DataFrame({"a": [1.0, 2.0], "b": [1.0, 0.0]}))
        with pytest.raises(
            TypeError, match="fill_value must be a finite float, not bool"
        ):
            ar.safe_divide_columns(frame, "a", "b", "ratio", fill_value=True)

    def test_fill_value_nan_raises(self):
        frame = ar.from_pandas(pd.DataFrame({"a": [1.0, 2.0], "b": [1.0, 0.0]}))
        with pytest.raises(ValueError, match="fill_value must be finite"):
            ar.safe_divide_columns(frame, "a", "b", "ratio", fill_value=float("nan"))

    def test_fill_value_inf_raises(self):
        frame = ar.from_pandas(pd.DataFrame({"a": [1.0, 2.0], "b": [1.0, 0.0]}))
        with pytest.raises(ValueError, match="fill_value must be finite"):
            ar.safe_divide_columns(frame, "a", "b", "ratio", fill_value=float("inf"))

    def test_fill_value_negative_inf_raises(self):
        frame = ar.from_pandas(pd.DataFrame({"a": [1.0, 2.0], "b": [1.0, 0.0]}))
        with pytest.raises(ValueError, match="fill_value must be finite"):
            ar.safe_divide_columns(frame, "a", "b", "ratio", fill_value=float("-inf"))

    def test_fill_value_valid_float_passes(self):
        frame = ar.from_pandas(
            pd.DataFrame(
                {
                    "a": [1.0, 2.0],
                    "b": [1.0, 0.0],
                }
            )
        )

        result = ar.safe_divide_columns(
            frame,
            "a",
            "b",
            "ratio",
            fill_value=0.5,
        )

        df = ar.to_pandas(result)
        assert df["ratio"].tolist() == [1.0, 0.5]


class TestClipNumericNativeRegression:
    """Regression tests verifying the native C++ clip_numeric hot-path.

    These tests guard against regressions introduced when the implementation
    was moved from a pandas round-trip to the native C++ path.  They
    complement the existing TestClipNumeric suite by exercising edge cases
    that are specific to the columnar C++ representation.
    """

    # ------------------------------------------------------------------
    # INT64 column behaviour
    # ------------------------------------------------------------------

    def test_int64_lower_bound_applied(self):
        frame = ar.from_pandas(pd.DataFrame({"x": [-100, 0, 50]}))
        result = ar.clip_numeric(frame, lower=0)
        assert ar.to_pandas(result)["x"].tolist() == [0, 0, 50]

    def test_int64_upper_bound_applied(self):
        frame = ar.from_pandas(pd.DataFrame({"x": [0, 50, 200]}))
        result = ar.clip_numeric(frame, upper=100)
        assert ar.to_pandas(result)["x"].tolist() == [0, 50, 100]

    def test_int64_both_bounds(self):
        frame = ar.from_pandas(pd.DataFrame({"x": [-10, 5, 150]}))
        result = ar.clip_numeric(frame, lower=0, upper=100)
        assert ar.to_pandas(result)["x"].tolist() == [0, 5, 100]

    def test_int64_value_at_exact_bound_unchanged(self):
        frame = ar.from_pandas(pd.DataFrame({"x": [0, 100]}))
        result = ar.clip_numeric(frame, lower=0, upper=100)
        assert ar.to_pandas(result)["x"].tolist() == [0, 100]

    def test_int64_null_preserved(self):
        frame = ar.from_pandas(pd.DataFrame({"x": [None, -5, 200]}))
        df = ar.to_pandas(ar.clip_numeric(frame, lower=0, upper=100))
        assert pd.isna(df["x"].iloc[0])
        assert df["x"].iloc[1] == 0
        assert df["x"].iloc[2] == 100

    # ------------------------------------------------------------------
    # FLOAT64 column behaviour
    # ------------------------------------------------------------------

    def test_float64_lower_bound_applied(self):
        frame = ar.from_pandas(pd.DataFrame({"v": [-1.5, 0.0, 3.7]}))
        result = ar.clip_numeric(frame, lower=0.0)
        vals = ar.to_pandas(result)["v"].tolist()
        assert vals == [0.0, 0.0, 3.7]

    def test_float64_upper_bound_applied(self):
        frame = ar.from_pandas(pd.DataFrame({"v": [0.5, 5.0, 9.9]}))
        result = ar.clip_numeric(frame, upper=5.0)
        vals = ar.to_pandas(result)["v"].tolist()
        assert vals == [0.5, 5.0, 5.0]

    def test_float64_both_bounds(self):
        frame = ar.from_pandas(pd.DataFrame({"v": [-99.9, 2.5, 99.9]}))
        result = ar.clip_numeric(frame, lower=0.0, upper=10.0)
        vals = ar.to_pandas(result)["v"].tolist()
        assert vals == [0.0, 2.5, 10.0]

    def test_float64_null_preserved(self):
        frame = ar.from_pandas(pd.DataFrame({"v": [None, -1.0, 20.0]}))
        df = ar.to_pandas(ar.clip_numeric(frame, lower=0.0, upper=10.0))
        assert pd.isna(df["v"].iloc[0])
        assert df["v"].iloc[1] == 0.0
        assert df["v"].iloc[2] == 10.0

    # ------------------------------------------------------------------
    # Mixed-type frame: non-numeric columns must be cloned unchanged
    # ------------------------------------------------------------------

    def test_string_column_untouched(self):
        frame = ar.from_pandas(
            pd.DataFrame({"score": [-5, 50, 200], "label": ["low", "mid", "high"]})
        )
        result = ar.clip_numeric(frame, lower=0, upper=100)
        df = ar.to_pandas(result)
        assert df["score"].tolist() == [0, 50, 100]
        assert df["label"].tolist() == ["low", "mid", "high"]

    def test_bool_column_untouched(self):
        frame = ar.from_pandas(
            pd.DataFrame({"score": [-5, 50, 200], "flag": [True, False, True]})
        )
        result = ar.clip_numeric(frame, lower=0, upper=100)
        df = ar.to_pandas(result)
        assert df["score"].tolist() == [0, 50, 100]
        assert df["flag"].tolist() == [True, False, True]

    # ------------------------------------------------------------------
    # Subset selection
    # ------------------------------------------------------------------

    def test_subset_clips_only_named_column(self):
        frame = ar.from_pandas(pd.DataFrame({"a": [-10, 5, 200], "b": [-10, 5, 200]}))
        result = ar.clip_numeric(frame, lower=0, upper=100, subset=["a"])
        df = ar.to_pandas(result)
        assert df["a"].tolist() == [0, 5, 100]
        assert df["b"].tolist() == [-10, 5, 200]  # untouched

    # ------------------------------------------------------------------
    # Frame with no numeric columns — must return frame unchanged
    # ------------------------------------------------------------------

    def test_no_numeric_columns_returns_frame_unchanged(self):
        frame = ar.from_pandas(pd.DataFrame({"name": ["Alice", "Bob"]}))
        result = ar.clip_numeric(frame, lower=0, upper=100)
        assert ar.to_pandas(result)["name"].tolist() == ["Alice", "Bob"]

    # ------------------------------------------------------------------
    # Validation errors — must still be raised by the Python wrapper
    # ------------------------------------------------------------------

    def test_no_bounds_raises(self):
        frame = ar.from_pandas(pd.DataFrame({"x": [1, 2, 3]}))
        with pytest.raises(ValueError, match="At least one of 'lower' or 'upper'"):
            ar.clip_numeric(frame)

    def test_inverted_bounds_raises(self):
        frame = ar.from_pandas(pd.DataFrame({"x": [1, 2, 3]}))
        with pytest.raises(ValueError, match="lower cannot be greater than upper"):
            ar.clip_numeric(frame, lower=10, upper=5)

    def test_unknown_subset_column_raises(self):
        frame = ar.from_pandas(pd.DataFrame({"x": [1, 2, 3]}))
        with pytest.raises(ValueError, match="Unknown columns in subset"):
            ar.clip_numeric(frame, lower=0, subset=["nonexistent"])

    def test_non_numeric_subset_column_raises(self):
        frame = ar.from_pandas(pd.DataFrame({"x": [1, 2, 3], "label": ["a", "b", "c"]}))
        with pytest.raises(
            ValueError, match="clip_numeric only supports numeric columns"
        ):
            ar.clip_numeric(frame, lower=0, subset=["label"])

    # ------------------------------------------------------------------
    # Pipeline integration
    # ------------------------------------------------------------------

    def test_pipeline_clip_numeric(self):
        frame = ar.from_pandas(pd.DataFrame({"score": [-10, 50, 200]}))
        result = ar.pipeline(frame, [("clip_numeric", {"lower": 0, "upper": 100})])
        assert ar.to_pandas(result)["score"].tolist() == [0, 50, 100]

    def test_pipeline_winsorize_outliers(self):
        frame = ar.from_pandas(
            pd.DataFrame(
                {
                    "value": [1, 2, 3, 4, 100],
                    "label": ["a", "b", "c", "d", "e"],
                }
            )
        )

        result = ar.pipeline(
            frame,
            [
                ("winsorize_outliers", {"lower": 0.2, "upper": 0.8}),
            ],
        )
        df = ar.to_pandas(result)

        assert df["value"].tolist() == pytest.approx([1.8, 2.0, 3.0, 4.0, 23.2])
        assert list(df["label"]) == ["a", "b", "c", "d", "e"]

    # ------------------------------------------------------------------
    # Large-frame determinism: result must be identical to the old
    # pandas-based implementation for a representative dataset.
    # ------------------------------------------------------------------

    def test_native_matches_pandas_reference(self):
        """Native result must be numerically identical to pandas.clip()."""
        import numpy as np

        rng = np.random.default_rng(42)
        n = 10_000
        df = pd.DataFrame(
            {
                "int_col": rng.integers(-500, 500, size=n).tolist(),
                "float_col": rng.uniform(-500.0, 500.0, size=n).tolist(),
                "label": ["x"] * n,
            }
        )
        # Introduce some nulls
        for idx in rng.integers(0, n, size=200):
            df.at[idx, "int_col"] = None
        for idx in rng.integers(0, n, size=200):
            df.at[idx, "float_col"] = None

        frame = ar.from_pandas(df)
        native_df = ar.to_pandas(ar.clip_numeric(frame, lower=-100, upper=100))

        # Reference: pandas clip on a copy
        ref = df.copy()
        ref["int_col"] = ref["int_col"].clip(lower=-100, upper=100)
        ref["float_col"] = ref["float_col"].clip(lower=-100, upper=100)

        pd.testing.assert_series_equal(
            native_df["int_col"].reset_index(drop=True),
            ref["int_col"].reset_index(drop=True),
            check_names=False,
        )
        pd.testing.assert_series_equal(
            native_df["float_col"].reset_index(drop=True),
            ref["float_col"].reset_index(drop=True),
            check_names=False,
        )
        # String column must be untouched
        assert native_df["label"].tolist() == ["x"] * n


def test_drop_columns_matching_normal():
    df = pd.DataFrame({"temp_a": [1], "temp_b": [2], "keep_c": [3]})
    result = ar.drop_columns_matching(df, "^temp_")
    assert list(result.columns) == ["keep_c"]


def test_drop_columns_matching_handles_non_string_pandas_columns():
    df = pd.DataFrame([[1, 2, 3]], columns=[1, ("sensor", "temp"), "temp_a"])

    result = ar.drop_columns_matching(df, "^temp")

    assert list(result.columns) == [1, ("sensor", "temp")]


def test_drop_columns_matching_no_match():
    df = pd.DataFrame({"a": [1], "b": [2]})
    result = ar.drop_columns_matching(df, "^temp_")
    assert list(result.columns) == ["a", "b"]


def test_drop_columns_matching_invalid_regex():
    df = pd.DataFrame({"a": [1]})
    with pytest.raises(Exception):
        ar.drop_columns_matching(df, "[invalid")


def test_drop_columns_matching_non_string_pattern():
    df = pd.DataFrame({"a": [1]})
    with pytest.raises(TypeError):
        ar.drop_columns_matching(df, 123)


def test_drop_columns_matching_all_columns():
    df = pd.DataFrame({"a": [1, 2], "b": [3, 4]})
    with pytest.raises(ValueError, match="Pattern matches all columns"):
        ar.drop_columns_matching(df, ".*")


def test_drop_columns_matching_zero_column_pandas():
    df = pd.DataFrame(index=range(2))
    result = ar.drop_columns_matching(df, "^tmp")
    assert isinstance(result, pd.DataFrame)
    assert result.shape == (2, 0)


def test_drop_columns_matching_zero_column_arframe():
    frame = ar.from_pandas(pd.DataFrame(index=range(2)))
    result = ar.drop_columns_matching(frame, "^tmp")
    assert isinstance(result, ar.ArFrame)
    assert result.shape == (2, 0)


def test_fill_nulls_validation_lossy_and_non_finite():
    """
    Ensure that fill_nulls rejects non-finite values and lossy float-to-int conversions
    with strict user-facing error contracts, while allowing compatible type-safe or
    int-to-float conversions to work.
    """
    import pandas as pd
    import pytest

    import arnio as ar

    # --- 1. VALID FILL COVERAGE (Happy Paths & New Compatible Paths) ---
    # Valid Int-to-Int fill
    valid_int = ar.from_pandas(pd.DataFrame({"x": pd.Series([1, None], dtype="Int64")}))
    res_int = ar.fill_nulls(valid_int, 5, subset=["x"])
    assert ar.to_pandas(res_int)["x"].iloc[1] == 5

    # Valid Float-to-Float finite fill
    valid_float = ar.from_pandas(pd.DataFrame({"x": [1.0, None]}))
    res_float = ar.fill_nulls(valid_float, 3.5, subset=["x"])
    assert ar.to_pandas(res_float)["x"].iloc[1] == 3.5

    # Compatible Int-to-Float fill (Filling a float column with an integer value)
    res_compatible = ar.fill_nulls(valid_float, 5, subset=["x"])
    assert ar.to_pandas(res_compatible)["x"].iloc[1] == 5.0

    # --- 2. INVALID DIRECT USAGE TESTS (Strict Error Message Contracts) ---
    int_frame = ar.from_pandas(pd.DataFrame({"x": pd.Series([1, None], dtype="Int64")}))

    # Reject lossy float values for integer target columns
    with pytest.raises(
        ValueError,
        match="Lossy or non-finite numeric fill values are not permitted for integer columns.",
    ):
        ar.fill_nulls(int_frame, 1.9, subset=["x"])

    # Reject Infinity for integer target columns
    with pytest.raises(
        ValueError,
        match="Lossy or non-finite numeric fill values are not permitted for integer columns.",
    ):
        ar.fill_nulls(int_frame, float("inf"), subset=["x"])

    # New Coverage Reject NaN for integer target columns
    with pytest.raises(
        ValueError,
        match="Lossy or non-finite numeric fill values are not permitted for integer columns.",
    ):
        ar.fill_nulls(int_frame, float("nan"), subset=["x"])

    with pytest.raises(
        ValueError,
        match="Lossy or non-finite numeric fill values are not permitted for integer columns.",
    ):
        ar.fill_nulls(int_frame, 1e20, subset=["x"])

    float_frame = ar.from_pandas(pd.DataFrame({"x": [1.0, None]}))

    # Reject Infinity and NaN for float target columns
    with pytest.raises(
        ValueError,
        match="Non-finite numeric fill values are not permitted for float columns.",
    ):
        ar.fill_nulls(float_frame, float("inf"), subset=["x"])

    with pytest.raises(
        ValueError,
        match="Non-finite numeric fill values are not permitted for float columns.",
    ):
        ar.fill_nulls(float_frame, float("nan"), subset=["x"])

    # --- 3. PIPELINE USAGE TESTS ---
    with pytest.raises(
        ValueError,
        match="Lossy or non-finite numeric fill values are not permitted for integer columns.",
    ):
        ar.pipeline(int_frame, [("fill_nulls", {"value": 1.9, "subset": ["x"]})])

    with pytest.raises(
        ValueError,
        match="Non-finite numeric fill values are not permitted for float columns.",
    ):
        ar.pipeline(
            float_frame, [("fill_nulls", {"value": float("inf"), "subset": ["x"]})]
        )


def test_fill_nulls_empty_subset_raises():
    frame = ar.from_pandas(pd.DataFrame({"a": [1, None], "b": [None, 2]}))
    with pytest.raises(ValueError, match="subset cannot be empty"):
        ar.fill_nulls(frame, 0, subset=[])


def test_fill_nulls_none_subset_fills_all():
    frame = ar.from_pandas(pd.DataFrame({"a": [1, None], "b": [None, 2]}))
    result = ar.fill_nulls(frame, 0, subset=None)
    df = ar.to_pandas(result)
    assert df["a"].tolist() == [1.0, 0.0]
    assert df["b"].tolist() == [0.0, 2.0]


class TestSelectColumns:
    def test_select_columns_keeps_requested_columns_and_preserves_order(self):
        frame = ar.from_pandas(
            pd.DataFrame(
                {
                    "id": [1, 2],
                    "debug": ["x", "y"],
                    "name": ["Alice", "Bob"],
                    "flag": [True, False],
                }
            )
        )

        result = ar.select_columns(frame, ["name", "id"])
        df = ar.to_pandas(result)

        assert list(df.columns) == ["name", "id"]
        assert list(df["name"]) == ["Alice", "Bob"]

    def test_select_columns_rejects_missing_columns(self, sample_csv):
        frame = ar.read_csv(sample_csv)

        with pytest.raises(ValueError, match="Unknown columns"):
            ar.select_columns(frame, ["missing"])

    def test_select_columns_rejects_string_input(self, sample_csv):
        frame = ar.read_csv(sample_csv)

        with pytest.raises(
            TypeError, match="columns must be a sequence of column names, not a string"
        ):
            ar.select_columns(frame, "age")

    def test_select_columns_rejects_non_string_items(self, sample_csv):
        frame = ar.read_csv(sample_csv)

        with pytest.raises(TypeError, match="All column names must be strings"):
            ar.select_columns(frame, ["age", 1])

    def test_select_columns_rejects_empty(self):
        frame = ar.from_pandas(
            pd.DataFrame(
                {
                    "id": [1, 2],
                    "name": ["Alice", "Bob"],
                }
            )
        )

        with pytest.raises(ValueError, match="Column selection cannot be empty"):
            ar.select_columns(frame, [])

    def test_select_columns_rejects_duplicates(self):
        frame = ar.from_pandas(
            pd.DataFrame(
                {
                    "id": [1, 2],
                    "name": ["Alice", "Bob"],
                }
            )
        )

        with pytest.raises(ValueError):
            ar.select_columns(frame, ["id", "id"])

    def test_select_columns_null_nan_handling(self):
        df = pd.DataFrame(
            {
                "id": [1, None, 3],
                "name": ["Alice", "Bob", None],
                "score": [95.5, float("nan"), 80.0],
            }
        )
        frame = ar.from_pandas(df)
        selected = ar.select_columns(frame, ["id", "score"])
        res_df = ar.to_pandas(selected)
        assert pd.isna(res_df["id"].iloc[1])
        assert pd.isna(res_df["score"].iloc[1])
        assert res_df["id"].iloc[0] == 1
        assert res_df["score"].iloc[0] == 95.5

    def test_select_columns_single_column_frame(self):
        df = pd.DataFrame({"id": [1, 2]})
        frame = ar.from_pandas(df)
        selected = ar.select_columns(frame, ["id"])
        assert selected.columns == ["id"]
        assert selected.shape == (2, 1)

        multi_df = pd.DataFrame({"id": [1, 2], "name": ["A", "B"]})
        multi_frame = ar.from_pandas(multi_df)
        selected_single = ar.select_columns(multi_frame, ["name"])
        assert selected_single.columns == ["name"]
        assert selected_single.shape == (2, 1)

    def test_select_columns_reordering(self):
        df = pd.DataFrame(
            {
                "id": [1, 2],
                "name": ["Alice", "Bob"],
                "age": [25, 30],
            }
        )
        frame = ar.from_pandas(df)
        reordered = ar.select_columns(frame, ["age", "id", "name"])
        assert reordered.columns == ["age", "id", "name"]
        res_df = ar.to_pandas(reordered)
        assert list(res_df["age"]) == [25, 30]
        assert list(res_df["id"]) == [1, 2]
        assert list(res_df["name"]) == ["Alice", "Bob"]

    def test_select_columns_invalid_container_types(self):
        df = pd.DataFrame({"id": [1, 2], "name": ["A", "B"]})
        frame = ar.from_pandas(df)

        with pytest.raises(TypeError, match="must be a list or tuple"):
            ar.select_columns(frame, {"id": "name"})

        gen = (col for col in ["id"])
        with pytest.raises(TypeError, match="must be a list or tuple"):
            ar.select_columns(frame, gen)

        with pytest.raises(TypeError, match="must be a list or tuple"):
            ar.select_columns(frame, None)
        with pytest.raises(TypeError, match="must be a list or tuple"):
            ar.select_columns(frame, 123)

    def test_select_columns_dtype_preservation(self):
        df = pd.DataFrame(
            {
                "int_col": pd.Series([1, 2], dtype="Int64"),
                "float_col": pd.Series([1.5, 2.5], dtype="float64"),
                "bool_col": pd.Series([True, False], dtype="boolean"),
                "str_col": pd.Series(["A", "B"], dtype="string"),
            }
        )
        frame = ar.from_pandas(df)
        original_dtypes = frame.dtypes

        selected = ar.select_columns(frame, ["float_col", "str_col", "int_col"])
        new_dtypes = selected.dtypes

        assert new_dtypes["int_col"] == original_dtypes["int_col"]
        assert new_dtypes["float_col"] == original_dtypes["float_col"]
        assert new_dtypes["str_col"] == original_dtypes["str_col"]

        res_df = ar.to_pandas(selected)
        assert res_df["int_col"].dtype == pd.Int64Dtype()
        assert res_df["float_col"].dtype == "float64"
        assert res_df["str_col"].dtype == pd.StringDtype()


class TestFilterReplaceTypeAnnotations:
    """Issue #1257 — filter_rows and replace_values accept and return both ArFrame and pd.DataFrame."""

    def test_filter_rows_arframe_in_arframe_out(self, tmp_path):
        """ArFrame input returns ArFrame."""
        path = tmp_path / "data.csv"
        path.write_text("id,score\n1,10\n2,50\n3,90\n")
        frame = ar.read_csv(str(path))
        result = ar.filter_rows(frame, column="score", op=">", value=20)
        assert isinstance(result, ar.ArFrame)
        assert ar.to_pandas(result).shape[0] == 2

    def test_filter_rows_dataframe_in_dataframe_out(self):
        """pd.DataFrame input returns pd.DataFrame."""
        import pandas as pd

        df = pd.DataFrame({"id": [1, 2, 3], "score": [10, 50, 90]})
        result = ar.filter_rows(df, column="score", op=">", value=20)
        assert isinstance(result, pd.DataFrame)
        assert result.shape[0] == 2

    def test_replace_values_arframe_in_arframe_out(self, tmp_path):
        """ArFrame input returns ArFrame."""
        path = tmp_path / "data.csv"
        path.write_text("status\nactive\ninactive\nactive\n")
        frame = ar.read_csv(str(path))
        result = ar.replace_values(
            frame, {"active": "A", "inactive": "I"}, column="status"
        )
        assert isinstance(result, ar.ArFrame)
        df = ar.to_pandas(result)
        assert set(df["status"].tolist()) == {"A", "I"}

    def test_replace_values_dataframe_in_dataframe_out(self):
        """pd.DataFrame input returns pd.DataFrame."""
        import pandas as pd

        df = pd.DataFrame({"status": ["active", "inactive", "active"]})
        result = ar.replace_values(
            df, {"active": "A", "inactive": "I"}, column="status"
        )
        assert isinstance(result, pd.DataFrame)
        assert set(result["status"].tolist()) == {"A", "I"}

    def test_filter_rows_preserves_index_for_dataframe(self):
        """pd.DataFrame return preserves the original index."""
        import pandas as pd

        df = pd.DataFrame({"score": [10, 50, 90]}, index=[100, 200, 300])
        result = ar.filter_rows(df, column="score", op=">=", value=50)
        assert list(result.index) == [200, 300]

    def test_replace_values_whole_frame_dataframe(self):
        """replace_values with no column applies across all columns for pd.DataFrame."""
        import pandas as pd

        df = pd.DataFrame({"a": ["x", "y"], "b": ["x", "z"]})
        result = ar.replace_values(df, {"x": "X"})
        assert isinstance(result, pd.DataFrame)
        assert result["a"].tolist() == ["X", "y"]
        assert result["b"].tolist() == ["X", "z"]


class TestValidateColumnSequence:
    def test_string_raises_type_error(self):
        with pytest.raises(
            TypeError, match="must be a sequence of column names, not a string"
        ):
            _validate_column_sequence("col1", argument_name="columns")

    def test_bytes_raises_type_error(self):
        with pytest.raises(
            TypeError, match="must be a sequence of column names, not a string"
        ):
            _validate_column_sequence(b"col1", argument_name="columns")

    def test_non_sequence_raises_type_error(self):
        with pytest.raises(TypeError, match="must be a sequence of column names"):
            _validate_column_sequence({"col1", "col2"}, argument_name="columns")

    def test_non_string_elements_raise_type_error(self):
        with pytest.raises(TypeError, match="must contain only string column names"):
            _validate_column_sequence(["col1", 123, "col2"], argument_name="columns")

    def test_valid_list_returns_normalized(self):
        result = _validate_column_sequence(["col1", "col2"], argument_name="columns")
        assert result == ["col1", "col2"]

    def test_valid_tuple_returns_normalized(self):
        result = _validate_column_sequence(("col1", "col2"), argument_name="columns")
        assert result == ["col1", "col2"]

    def test_empty_list_returns_empty(self):
        result = _validate_column_sequence([], argument_name="columns")
        assert result == []


class TestValidateStringMapping:
    def test_non_mapping_raises_type_error(self):
        with pytest.raises(
            TypeError, match="must be a mapping of string keys to strings"
        ):
            _validate_string_mapping([("a", "b")], argument_name="mapping")

    def test_invalid_non_string_keys_raise_type_error(self):
        with pytest.raises(
            TypeError, match="keys must contain only string column names"
        ):
            _validate_string_mapping({1: "a", 2: "b"}, argument_name="mapping")

    def test_empty_value_raises_type_error(self):
        with pytest.raises(TypeError, match="values must be non-empty strings"):
            _validate_string_mapping({"a": "", "b": "value"}, argument_name="mapping")

    def test_whitespace_only_value_raises_type_error(self):
        with pytest.raises(TypeError, match="values must be non-empty strings"):
            _validate_string_mapping(
                {"a": "   ", "b": "value"}, argument_name="mapping"
            )

    def test_valid_string_mapping_returns_dict(self):
        result = _validate_string_mapping(
            {"a": "value1", "b": "value2"}, argument_name="mapping"
        )
        assert result == {"a": "value1", "b": "value2"}

    def test_empty_mapping_allow_empty_true(self):
        result = _validate_string_mapping({}, argument_name="mapping", allow_empty=True)
        assert result == {}

    def test_empty_mapping_allow_empty_false_raises(self):
        with pytest.raises(ValueError, match="must not be empty"):
            _validate_string_mapping({}, argument_name="mapping", allow_empty=False)


class TestCleanColumnNames:
    def test_clean_column_names_basic(self):
        df = pd.DataFrame({"My-Name!!": [1], "age##": [2]})
        frame = from_pandas(df)
        result = ar.clean_column_names(frame)
        assert to_pandas(result).columns.tolist() == ["my_name", "age"]

    def test_clean_column_names_noop_returns_fresh_frame(self):
        df = pd.DataFrame({"name": [1], "age": [2]})
        frame = from_pandas(df)

        result = ar.clean_column_names(frame)

        assert result is not frame
        assert to_pandas(result).equals(to_pandas(frame))

    def test_clean_column_names_noop_attrs_are_isolated(self):
        df = pd.DataFrame({"name": [1], "age": [2]})
        frame = from_pandas(df)
        frame._attrs = {"source": {"name": "original"}}

        result = ar.clean_column_names(frame)

        result._attrs["source"]["name"] = "mutated"

        assert frame._attrs["source"]["name"] == "original"

    def test_clean_column_names_consecutive_and_boundary_underscores(self):
        df = pd.DataFrame({"__col__name__": [1], "-another--col-": [2]})
        frame = from_pandas(df)
        result = ar.clean_column_names(frame)
        assert to_pandas(result).columns.tolist() == ["col_name", "another_col"]

    def test_clean_column_names_case_type_upper(self):
        df = pd.DataFrame({"My-Name!!": [1]})
        frame = from_pandas(df)
        result = ar.clean_column_names(frame, case_type="upper")
        assert to_pandas(result).columns.tolist() == ["MY_NAME"]

    def test_clean_column_names_case_type_none(self):
        df = pd.DataFrame({"My-Name!!": [1]})
        frame = from_pandas(df)
        result = ar.clean_column_names(frame, case_type="none")
        assert to_pandas(result).columns.tolist() == ["My_Name"]

    def test_clean_column_names_duplicate_raises(self):
        df = pd.DataFrame({"col__name": [1], "col---name": [2]})
        frame = from_pandas(df)
        with pytest.raises(ValueError, match="duplicates"):
            ar.clean_column_names(frame)

    def test_clean_column_names_case_type_invalid(self):
        df = pd.DataFrame({"name": [1]})
        frame = from_pandas(df)
        with pytest.raises(ValueError, match="case_type must be one of"):
            ar.clean_column_names(frame, case_type="invalid")

    def test_clean_column_names_case_type_type_error(self):
        df = pd.DataFrame({"name": [1]})
        frame = from_pandas(df)
        with pytest.raises(TypeError, match="must be a string"):
            ar.clean_column_names(frame, case_type=123)

    def test_clean_column_names_pipeline(self):
        df = pd.DataFrame({"My-Name!!": [1], "age##": [2]})
        frame = from_pandas(df)
        result = ar.pipeline(frame, [("clean_column_names", {"case_type": "upper"})])
        assert to_pandas(result).columns.tolist() == ["MY_NAME", "AGE"]

    def test_clean_column_names_case_type_title(self):
        df = pd.DataFrame({"My-NaMe!!": [1]})
        frame = from_pandas(df)
        result = ar.clean_column_names(frame, case_type="title")
        assert to_pandas(result).columns.tolist() == ["My_Name"]

    def test_clean_column_names_case_type_camel(self):
        df = pd.DataFrame({"My-Name!!": [1]})
        frame = from_pandas(df)
        result = ar.clean_column_names(frame, case_type="camel")
        assert to_pandas(result).columns.tolist() == ["myName"]

    def test_clean_column_names_case_type_title_acronyms(self):
        df = pd.DataFrame({"HTTP_status": [1]})
        frame = from_pandas(df)
        result = ar.clean_column_names(frame, case_type="title")
        assert to_pandas(result).columns.tolist() == ["Http_Status"]

    def test_clean_column_names_case_type_camel_acronyms(self):
        df = pd.DataFrame({"HTTP_status": [1]})
        frame = from_pandas(df)
        result = ar.clean_column_names(frame, case_type="camel")
        assert to_pandas(result).columns.tolist() == ["httpStatus"]

    def test_clean_column_names_case_type_title_leading_digits(self):
        df = pd.DataFrame({"123_status": [1]})
        frame = from_pandas(df)
        result = ar.clean_column_names(frame, case_type="title")
        assert to_pandas(result).columns.tolist() == ["123_Status"]

    def test_clean_column_names_case_type_camel_leading_digits(self):
        df = pd.DataFrame({"123_status": [1]})
        frame = from_pandas(df)
        result = ar.clean_column_names(frame, case_type="camel")
        assert to_pandas(result).columns.tolist() == ["123Status"]

    def test_clean_column_names_title_pipeline(self):
        df = pd.DataFrame({"My-Name!!": [1], "age##": [2]})
        frame = from_pandas(df)
        result = ar.pipeline(frame, [("clean_column_names", {"case_type": "title"})])
        assert to_pandas(result).columns.tolist() == ["My_Name", "Age"]

    def test_clean_column_names_camel_pipeline(self):
        df = pd.DataFrame({"My-Name!!": [1], "age##": [2]})
        frame = from_pandas(df)
        result = ar.pipeline(frame, [("clean_column_names", {"case_type": "camel"})])
        assert to_pandas(result).columns.tolist() == ["myName", "age"]

    def test_clean_column_names_title_duplicate_raises(self):
        df = pd.DataFrame({"My_Name": [1], "my_name": [2]})
        frame = from_pandas(df)
        with pytest.raises(ValueError, match="duplicates"):
            ar.clean_column_names(frame, case_type="title")

    def test_clean_column_names_camel_duplicate_raises(self):
        df = pd.DataFrame({"My_Name": [1], "my_name": [2]})
        frame = from_pandas(df)
        with pytest.raises(ValueError, match="duplicates"):
            ar.clean_column_names(frame, case_type="camel")


class TestSlugifyColumnNames:
    def test_spaces_become_underscores(self):
        frame = ar.from_pandas(pd.DataFrame({"First Name": ["Alice"]}))
        result = ar.slugify_column_names(frame)
        assert result.columns == ["first_name"]

    def test_mixed_case_lowercased(self):
        frame = ar.from_pandas(pd.DataFrame({"UserID": [1]}))
        result = ar.slugify_column_names(frame)
        assert result.columns == ["userid"]

    def test_special_chars_removed(self):
        frame = ar.from_pandas(pd.DataFrame({"Revenue ($)": [100.0]}))
        result = ar.slugify_column_names(frame)
        assert result.columns == ["revenue"]

    def test_empty_slug_raises(self):
        frame = ar.from_pandas(pd.DataFrame({"!!!": [1]}))
        with pytest.raises(ValueError):
            ar.slugify_column_names(frame)

    def test_duplicate_slugs_raise_by_default(self):
        frame = ar.from_pandas(pd.DataFrame({"First Name": [1], "first name": [2]}))
        with pytest.raises(ValueError):
            ar.slugify_column_names(frame)

    def test_pipeline_usage(self):
        frame = ar.from_pandas(pd.DataFrame({"First Name": ["Alice"], "Age": [25]}))
        result = ar.pipeline(frame, [("slugify_column_names", {})])
        assert result.columns == ["first_name", "age"]

    def test_on_duplicates_invalid_raises(self):
        frame = ar.from_pandas(pd.DataFrame({"a": [1]}))
        with pytest.raises(ValueError):
            ar.slugify_column_names(frame, on_duplicates="ignore")

def test_parse_numeric_strings():
    frame = ar.from_pandas(pd.DataFrame({
        "price": ["1234.50", "500", "10.25", "bad"],
        "rate": ["15%", "45.5%", "0.5%", "none"],
        "normal_text": ["apple", "banana", "cherry", "date"],
    }))

    cleaned = ar.parse_numeric_strings(frame, subset=["price", "rate"], errors="coerce")
    df = ar.to_pandas(cleaned)

    assert df["price"].iloc[0] == 1234.50
    assert df["price"].iloc[1] == 500.0
    assert df["price"].iloc[2] == 10.25
    assert pd.isna(df["price"].iloc[3])

    assert df["rate"].iloc[0] == 0.15
    assert df["rate"].iloc[1] == 0.455
    assert df["rate"].iloc[2] == 0.005
    assert pd.isna(df["rate"].iloc[3])

    assert df["normal_text"].iloc[0] == "apple"

    with pytest.raises(ValueError):
        ar.parse_numeric_strings(frame, subset=["price"], errors="raise")
    @pytest.mark.parametrize("frame", [None, [], {"a": [1]}])
    def test_non_frame_input_raises_typeerror(self, frame):
        with pytest.raises(
            TypeError, match="frame must be an ArFrame or pandas.DataFrame"
        ):
            ar.slugify_column_names(frame)


class TestRenameColumnsMatching:
    def test_basic_rename(self):
        frame = ar.from_pandas(
            pd.DataFrame({"temp_revenue": [1], "temp_cost": [2], "name": ["Alice"]})
        )
        result = ar.rename_columns_matching(frame, "^temp_", "")
        assert list(ar.to_pandas(result).columns) == ["revenue", "cost", "name"]

    def test_unchanged_columns_preserved(self):
        frame = ar.from_pandas(pd.DataFrame({"temp_a": [1], "b": [2]}))
        result = ar.rename_columns_matching(frame, "^temp_", "")
        assert "b" in ar.to_pandas(result).columns

    def test_no_match_returns_original_columns(self):
        frame = ar.from_pandas(pd.DataFrame({"a": [1], "b": [2]}))
        result = ar.rename_columns_matching(frame, "^temp_", "")
        assert list(ar.to_pandas(result).columns) == ["a", "b"]

    def test_rejects_non_string_pattern(self):
        frame = ar.from_pandas(pd.DataFrame({"a": [1]}))
        with pytest.raises(TypeError, match="pattern must be a string"):
            ar.rename_columns_matching(frame, 123, "")

    def test_rejects_non_string_replacement(self):
        frame = ar.from_pandas(pd.DataFrame({"a": [1]}))
        with pytest.raises(TypeError, match="replacement must be a string"):
            ar.rename_columns_matching(frame, "^a", 123)

    def test_rejects_invalid_regex(self):
        frame = ar.from_pandas(pd.DataFrame({"a": [1]}))
        with pytest.raises(re.error):
            ar.rename_columns_matching(frame, "[invalid", "")

    def test_rejects_duplicate_resulting_names(self):
        frame = ar.from_pandas(pd.DataFrame({"temp_a": [1], "a": [2]}))
        with pytest.raises(ValueError, match="duplicate column names"):
            ar.rename_columns_matching(frame, "^temp_", "")

    def test_pandas_input_returns_dataframe(self):
        df = pd.DataFrame({"temp_x": [1], "y": [2]})
        result = ar.rename_columns_matching(df, "^temp_", "")
        assert isinstance(result, pd.DataFrame)
        assert list(result.columns) == ["x", "y"]

    def test_pipeline_usage(self):
        frame = ar.from_pandas(pd.DataFrame({"temp_a": [1], "b": [2]}))
        result = ar.pipeline(
            frame,
            [("rename_columns_matching", {"pattern": "^temp_", "replacement": ""})],
        )
        assert "a" in ar.to_pandas(result).columns

    def test_rejects_empty_resulting_name(self):
        frame = ar.from_pandas(pd.DataFrame({"temp_": [1]}))
        with pytest.raises(ValueError):
            ar.rename_columns_matching(frame, "^temp_$", "")

    def test_rejects_whitespace_resulting_name(self):
        frame = ar.from_pandas(pd.DataFrame({"temp_": [1]}))
        with pytest.raises(ValueError):
            ar.rename_columns_matching(frame, "^temp_$", "   ")


class TestNormalizeMinmax:
    def test_basic_scale_to_unit_range(self):
        frame = ar.from_pandas(pd.DataFrame({"price": [0.0, 50.0, 100.0]}))
        result = ar.normalize_minmax(frame, subset=["price"])
        df = ar.to_pandas(result)
        assert df["price"].tolist() == pytest.approx([0.0, 0.5, 1.0])

    def test_returns_arframe(self):
        frame = ar.from_pandas(pd.DataFrame({"x": [1.0, 2.0, 3.0]}))
        result = ar.normalize_minmax(frame, subset=["x"])
        assert isinstance(result, ar.ArFrame)

    def test_custom_feature_range(self):
        frame = ar.from_pandas(pd.DataFrame({"x": [0.0, 100.0]}))
        result = ar.normalize_minmax(frame, subset=["x"], feature_range=(-1.0, 1.0))
        df = ar.to_pandas(result)
        assert df["x"].tolist() == pytest.approx([-1.0, 1.0])

    def test_nulls_preserved_and_excluded_from_computation(self):
        frame = ar.from_pandas(pd.DataFrame({"x": [0.0, None, 100.0]}))
        result = ar.normalize_minmax(frame, subset=["x"])
        df = ar.to_pandas(result)
        assert df["x"].iloc[0] == pytest.approx(0.0)
        assert df["x"].iloc[2] == pytest.approx(1.0)
        assert pd.isna(df["x"].iloc[1])

    def test_all_null_column_left_unchanged(self):
        frame = ar.from_pandas(pd.DataFrame({"x": [None, None, None]}))
        result = ar.normalize_minmax(frame, subset=["x"])
        df = ar.to_pandas(result)
        assert df["x"].isna().all()

    def test_constant_column_maps_to_lower_bound(self):
        frame = ar.from_pandas(pd.DataFrame({"x": [5.0, 5.0, 5.0]}))
        result = ar.normalize_minmax(frame, subset=["x"])
        df = ar.to_pandas(result)
        assert all(v == pytest.approx(0.0) for v in df["x"].dropna())

    def test_constant_column_preserves_nulls(self):
        frame = ar.from_pandas(pd.DataFrame({"x": [5.0, None, 5.0]}))
        result = ar.normalize_minmax(frame, subset=["x"])
        df = ar.to_pandas(result)
        assert df["x"].iloc[0] == pytest.approx(0.0)
        assert pd.isna(df["x"].iloc[1])
        assert df["x"].iloc[2] == pytest.approx(0.0)

    def test_non_numeric_subset_raises(self):
        frame = ar.from_pandas(pd.DataFrame({"name": ["a", "b"]}))
        with pytest.raises(ValueError, match="only supports numeric columns"):
            ar.normalize_minmax(frame, subset=["name"])

    def test_missing_subset_column_raises(self):
        frame = ar.from_pandas(pd.DataFrame({"x": [1.0, 2.0]}))
        with pytest.raises(ValueError, match="Unknown columns in subset"):
            ar.normalize_minmax(frame, subset=["nonexistent"])

    def test_feature_range_min_ge_max_raises(self):
        frame = ar.from_pandas(pd.DataFrame({"x": [1.0, 2.0]}))
        with pytest.raises(ValueError, match="strictly less than max"):
            ar.normalize_minmax(frame, feature_range=(1.0, 0.0))

    def test_feature_range_equal_bounds_raises(self):
        frame = ar.from_pandas(pd.DataFrame({"x": [1.0, 2.0]}))
        with pytest.raises(ValueError):
            ar.normalize_minmax(frame, feature_range=(1.0, 1.0))

    def test_feature_range_non_finite_raises(self):
        frame = ar.from_pandas(pd.DataFrame({"x": [1.0, 2.0]}))
        with pytest.raises(ValueError, match="finite"):
            ar.normalize_minmax(frame, feature_range=(float("-inf"), 1.0))

    def test_feature_range_wrong_type_raises(self):
        frame = ar.from_pandas(pd.DataFrame({"x": [1.0, 2.0]}))
        with pytest.raises(TypeError):
            ar.normalize_minmax(frame, feature_range="bad")

    def test_feature_range_bool_bounds_raises(self):
        frame = ar.from_pandas(pd.DataFrame({"x": [1.0, 2.0]}))
        with pytest.raises(TypeError):
            ar.normalize_minmax(frame, feature_range=(True, False))

    def test_no_subset_applies_to_all_numeric_columns(self):
        frame = ar.from_pandas(
            pd.DataFrame(
                {
                    "a": [0.0, 100.0],
                    "b": [0.0, 50.0],
                    "label": ["x", "y"],
                }
            )
        )
        result = ar.normalize_minmax(frame)
        df = ar.to_pandas(result)
        assert df["a"].tolist() == pytest.approx([0.0, 1.0])
        assert df["b"].tolist() == pytest.approx([0.0, 1.0])
        assert df["label"].tolist() == ["x", "y"]

    def test_int64_column_normalized(self):
        frame = ar.from_pandas(pd.DataFrame({"x": [0, 50, 100]}))
        result = ar.normalize_minmax(frame, subset=["x"])
        df = ar.to_pandas(result)
        assert df["x"].tolist() == pytest.approx([0.0, 0.5, 1.0])

    def test_no_numeric_columns_returns_frame_unchanged(self):
        frame = ar.from_pandas(pd.DataFrame({"label": ["a", "b"]}))
        result = ar.normalize_minmax(frame)
        df = ar.to_pandas(result)
        assert list(df.columns) == ["label"]
        assert df["label"].tolist() == ["a", "b"]

    def test_output_is_float64(self):
        frame = ar.from_pandas(pd.DataFrame({"x": [0, 1, 2]}))
        result = ar.normalize_minmax(frame)
        df = ar.to_pandas(result)
        assert df["x"].dtype in ("float64", "float")

    def test_pipeline_step_registered(self):
        frame = ar.from_pandas(pd.DataFrame({"price": [0.0, 100.0]}))
        result = ar.pipeline(frame, [("normalize_minmax", {"subset": ["price"]})])
        df = ar.to_pandas(result)
        assert df["price"].tolist() == pytest.approx([0.0, 1.0])

    def test_pipeline_with_custom_feature_range(self):
        frame = ar.from_pandas(pd.DataFrame({"x": [0.0, 50.0, 100.0]}))
        result = ar.pipeline(
            frame,
            [
                ("normalize_minmax", {"subset": ["x"], "feature_range": (-1.0, 1.0)}),
            ],
        )
        df = ar.to_pandas(result)
        assert df["x"].tolist() == pytest.approx([-1.0, 0.0, 1.0])

    def test_pipeline_chained_with_other_steps(self):
        frame = ar.from_pandas(
            pd.DataFrame(
                {
                    "price": [0.0, None, 100.0],
                    "label": ["  a  ", "b", "c"],
                }
            )
        )
        result = ar.pipeline(
            frame,
            [
                ("strip_whitespace",),
                ("normalize_minmax", {"subset": ["price"]}),
            ],
        )
        df = ar.to_pandas(result)
        assert df["price"].iloc[0] == pytest.approx(0.0)
        assert pd.isna(df["price"].iloc[1])
        assert df["price"].iloc[2] == pytest.approx(1.0)
        assert df["label"].iloc[0] == "a"


class TestNormalizeMinmaxExtra:
    def test_single_row_maps_to_lower_bound(self):
        frame = ar.from_pandas(pd.DataFrame({"x": [42.0]}))
        result = ar.normalize_minmax(frame, subset=["x"])
        df = ar.to_pandas(result)
        assert df["x"].iloc[0] == pytest.approx(0.0)

    def test_empty_frame_returns_empty(self):
        frame = ar.from_pandas(pd.DataFrame({"x": pd.Series(dtype="float64")}))
        result = ar.normalize_minmax(frame, subset=["x"])
        df = ar.to_pandas(result)
        assert df.empty

    def test_negative_values_scaled_correctly(self):
        frame = ar.from_pandas(pd.DataFrame({"x": [-100.0, 0.0, 100.0]}))
        result = ar.normalize_minmax(frame, subset=["x"])
        df = ar.to_pandas(result)
        assert df["x"].tolist() == pytest.approx([0.0, 0.5, 1.0])

    def test_non_subset_columns_untouched(self):
        frame = ar.from_pandas(
            pd.DataFrame(
                {
                    "price": [0.0, 100.0],
                    "qty": [10.0, 20.0],
                }
            )
        )
        result = ar.normalize_minmax(frame, subset=["price"])
        df = ar.to_pandas(result)
        assert df["price"].tolist() == pytest.approx([0.0, 1.0])
        assert df["qty"].tolist() == [10.0, 20.0]

    def test_feature_range_single_element_tuple_raises(self):
        frame = ar.from_pandas(pd.DataFrame({"x": [1.0, 2.0]}))
        with pytest.raises(ValueError):
            ar.normalize_minmax(frame, feature_range=(0.0,))

    def test_feature_range_three_elements_raises(self):
        frame = ar.from_pandas(pd.DataFrame({"x": [1.0, 2.0]}))
        with pytest.raises(ValueError):
            ar.normalize_minmax(frame, feature_range=(0.0, 0.5, 1.0))


class TestPublicHelpersValidateArFrame:
    @pytest.mark.parametrize("obj", [object(), None, 123, pd.DataFrame()])
    def test_cleaning_helpers_reject_invalid_frame(self, obj):
        with pytest.raises(TypeError, match=".*must be an ArFrame.*"):
            ar.drop_nulls(obj)
        with pytest.raises(TypeError, match=".*must be an ArFrame.*"):
            ar.strip_whitespace(obj)
        with pytest.raises(TypeError, match=".*must be an ArFrame.*"):
            ar.drop_columns(obj, ["x"])
        with pytest.raises(TypeError, match=".*must be an ArFrame.*"):
            ar.validate_columns_exist(obj, ["x"])


# ---------------------------------------------------------------------------
# Regression tests: locale-independent FLOAT64 parsing — issue #1989
#
# cast_types() and fill_nulls() previously used std::stod() which is
# locale-sensitive. On systems using locales like de_DE.UTF-8 or fr_FR.UTF-8,
# '.' is treated as a thousands separator rather than a decimal point, causing
# values that were ingested correctly from CSV to fail at cast time.
#
# The fix replaces both std::stod() call sites in cleaning.cpp with
# parse_float64_classic(), which uses std::istringstream imbued with
# std::locale::classic() — the same approach used by csv_reader.cpp.
#
# Each test that requires a non-English locale is skipped when the locale is
# unavailable on the runner (locale.setlocale raises locale.Error).
# ---------------------------------------------------------------------------


def _set_locale(name: str):
    """Attempt to activate *name* for LC_NUMERIC; return the previous value.

    Raises pytest.skip if the locale is unavailable on this machine.
    """
    try:
        prev = _locale.setlocale(_locale.LC_NUMERIC)
        _locale.setlocale(_locale.LC_NUMERIC, name)
        return prev
    except _locale.Error:
        pytest.skip(f"Locale {name!r} not available on this runner")


class TestCastTypesFloat64LocaleIndependent:
    """cast_types() FLOAT64 path must use locale-independent parsing (issue #1989)."""

    def test_cast_float64_succeeds_under_de_locale(self):
        """'1.5' must parse to 1.5 even when LC_NUMERIC=de_DE.UTF-8."""
        prev = _set_locale("de_DE.UTF-8")
        try:
            frame = ar.from_pandas(pd.DataFrame({"price": ["1.5", "2.5"]}))
            result = ar.cast_types(frame, {"price": "float64"})
            df = to_pandas(result)
            assert df["price"].tolist() == pytest.approx([1.5, 2.5])
        finally:
            _locale.setlocale(_locale.LC_NUMERIC, prev)

    def test_cast_float64_succeeds_under_fr_locale(self):
        """Same regression check with fr_FR.UTF-8."""
        prev = _set_locale("fr_FR.UTF-8")
        try:
            frame = ar.from_pandas(pd.DataFrame({"val": ["3.14", "2.71"]}))
            result = ar.cast_types(frame, {"val": "float64"})
            df = to_pandas(result)
            assert df["val"].tolist() == pytest.approx([3.14, 2.71])
        finally:
            _locale.setlocale(_locale.LC_NUMERIC, prev)

    def test_cast_float64_negative_value_under_de_locale(self):
        """Negative floats must also parse correctly under a non-English locale."""
        prev = _set_locale("de_DE.UTF-8")
        try:
            frame = ar.from_pandas(pd.DataFrame({"x": ["-1.25", "0.5"]}))
            result = ar.cast_types(frame, {"x": "float64"})
            df = to_pandas(result)
            assert df["x"].tolist() == pytest.approx([-1.25, 0.5])
        finally:
            _locale.setlocale(_locale.LC_NUMERIC, prev)

    def test_cast_float64_scientific_notation_under_de_locale(self):
        """Scientific notation must survive locale change."""
        prev = _set_locale("de_DE.UTF-8")
        try:
            frame = ar.from_pandas(pd.DataFrame({"v": ["1.5e2", "2.0e-1"]}))
            result = ar.cast_types(frame, {"v": "float64"})
            df = to_pandas(result)
            assert df["v"].tolist() == pytest.approx([150.0, 0.2])
        finally:
            _locale.setlocale(_locale.LC_NUMERIC, prev)

    def test_cast_float64_coerce_invalid_under_de_locale(self):
        """coerce_invalid=True must still null-out genuinely unparseable values."""
        prev = _set_locale("de_DE.UTF-8")
        try:
            frame = ar.from_pandas(pd.DataFrame({"x": ["1.5", "bad", "3.0"]}))
            result = ar.cast_types(frame, {"x": "float64"}, errors="coerce")
            df = to_pandas(result)
            assert df["x"].iloc[0] == pytest.approx(1.5)
            assert pd.isna(df["x"].iloc[1])
            assert df["x"].iloc[2] == pytest.approx(3.0)
        finally:
            _locale.setlocale(_locale.LC_NUMERIC, prev)

    def test_cast_float64_special_tokens_unchanged_under_de_locale(self):
        """'nan', 'inf', '-inf' must still map to special float values."""
        prev = _set_locale("de_DE.UTF-8")
        try:
            frame = ar.from_pandas(pd.DataFrame({"v": ["nan", "inf", "-inf"]}))
            result = ar.cast_types(frame, {"v": "float64"}, errors="coerce")
            df = to_pandas(result)
            # nan, inf, -inf are non-finite — with errors="coerce" they become null
            assert df["v"].isna().all()
        finally:
            _locale.setlocale(_locale.LC_NUMERIC, prev)

    def test_cast_float64_baseline_locale_independent(self):
        """Baseline: cast_types FLOAT64 works correctly under the default locale."""
        frame = ar.from_pandas(pd.DataFrame({"price": ["1.5", "99.99", "-3.14"]}))
        result = ar.cast_types(frame, {"price": "float64"})
        df = to_pandas(result)
        assert df["price"].tolist() == pytest.approx([1.5, 99.99, -3.14])

    def test_cast_float64_invalid_value_raises_under_de_locale(self):
        """A genuinely invalid value must still raise without coerce_invalid."""
        prev = _set_locale("de_DE.UTF-8")
        try:
            frame = ar.from_pandas(pd.DataFrame({"x": ["not_a_float"]}))
            with pytest.raises(Exception):
                ar.cast_types(frame, {"x": "float64"})
        finally:
            _locale.setlocale(_locale.LC_NUMERIC, prev)


class TestFillNullsFloat64LocaleIndependent:
    """fill_nulls() FLOAT64 fill-value path must also be locale-independent (issue #1989)."""

    def test_fill_nulls_float64_fill_value_under_de_locale(self):
        """A string fill value like '0.5' must be accepted under de_DE.UTF-8."""
        prev = _set_locale("de_DE.UTF-8")
        try:
            frame = ar.from_pandas(
                pd.DataFrame({"price": pd.array([1.5, None, 3.0], dtype="Float64")})
            )
            result = ar.fill_nulls(frame, "0.5", subset=["price"])
            df = to_pandas(result)
            assert df["price"].iloc[1] == pytest.approx(0.5)
        finally:
            _locale.setlocale(_locale.LC_NUMERIC, prev)

    def test_fill_nulls_float64_fill_value_under_fr_locale(self):
        """Same fill_nulls regression check with fr_FR.UTF-8."""
        prev = _set_locale("fr_FR.UTF-8")
        try:
            frame = ar.from_pandas(
                pd.DataFrame({"v": pd.array([None, 2.0], dtype="Float64")})
            )
            result = ar.fill_nulls(frame, "1.5", subset=["v"])
            df = to_pandas(result)
            assert df["v"].iloc[0] == pytest.approx(1.5)
        finally:
            _locale.setlocale(_locale.LC_NUMERIC, prev)

    def test_fill_nulls_float64_fill_value_baseline(self):
        """Baseline: fill_nulls FLOAT64 string fill value works under default locale."""
        frame = ar.from_pandas(
            pd.DataFrame({"x": pd.array([None, 2.5, None], dtype="Float64")})
        )
        result = ar.fill_nulls(frame, "1.0", subset=["x"])
        df = to_pandas(result)
        assert df["x"].iloc[0] == pytest.approx(1.0)
        assert df["x"].iloc[2] == pytest.approx(1.0)

    def test_fill_nulls_float64_non_finite_fill_rejected_under_de_locale(self):
        """Non-finite fill values must still be rejected regardless of locale."""
        prev = _set_locale("de_DE.UTF-8")
        try:
            frame = ar.from_pandas(
                pd.DataFrame({"x": pd.array([None, 1.0], dtype="Float64")})
            )
            with pytest.raises(Exception):
                ar.fill_nulls(frame, "inf", subset=["x"])
        finally:
            _locale.setlocale(_locale.LC_NUMERIC, prev)


class TestHashColumns:
    """Tests for ar.hash_columns (pure-Python / hashlib implementation)."""

    def _frame(self):
        return ar.from_pandas(
            pd.DataFrame(
                {
                    "email": ["user@example.com", None, ""],
                    "user_id": ["abc123", "xyz999", "def456"],
                    "age": [30, 25, 40],
                }
            )
        )

    def test_sha256_produces_64_char_hex(self):
        frame = self._frame()
        result = ar.hash_columns(frame, subset=["email"])
        df = ar.to_pandas(result)
        digest = df["email"].iloc[0]
        assert len(digest) == 64
        assert all(c in "0123456789abcdef" for c in digest)

    def test_sha256_known_answer(self):
        import hashlib

        frame = self._frame()
        result = ar.hash_columns(frame, subset=["email"])
        df = ar.to_pandas(result)
        assert df["email"].iloc[0] == hashlib.sha256(b"user@example.com").hexdigest()

    def test_sha256_empty_string_is_hashed_not_null(self):
        import hashlib

        frame = self._frame()
        result = ar.hash_columns(frame, subset=["email"])
        df = ar.to_pandas(result)
        assert df["email"].iloc[2] == hashlib.sha256(b"").hexdigest()

    def test_null_cells_preserved(self):
        frame = self._frame()
        result = ar.hash_columns(frame, subset=["email"])
        df = ar.to_pandas(result)
        assert pd.isna(df["email"].iloc[1])

    def test_non_subset_columns_unchanged(self):
        frame = self._frame()
        result = ar.hash_columns(frame, subset=["email"])
        df = ar.to_pandas(result)
        assert df["user_id"].iloc[0] == "abc123"
        assert df["age"].iloc[0] == 30

    def test_md5_produces_32_char_hex(self):
        import hashlib

        frame = self._frame()
        result = ar.hash_columns(frame, subset=["user_id"], algorithm="md5")
        df = ar.to_pandas(result)
        digest = df["user_id"].iloc[0]
        assert len(digest) == 32
        assert all(c in "0123456789abcdef" for c in digest)
        assert digest == hashlib.md5(b"abc123").hexdigest()

    def test_multiple_subset_columns(self):
        import hashlib

        frame = self._frame()
        result = ar.hash_columns(frame, subset=["email", "user_id"])
        df = ar.to_pandas(result)
        assert df["email"].iloc[0] == hashlib.sha256(b"user@example.com").hexdigest()
        assert df["user_id"].iloc[0] == hashlib.sha256(b"abc123").hexdigest()

    def test_missing_column_raises_value_error(self):
        frame = self._frame()
        with pytest.raises(ValueError, match="not found"):
            ar.hash_columns(frame, subset=["nonexistent"])

    def test_non_string_column_raises_type_error(self):
        frame = self._frame()
        with pytest.raises(TypeError, match="string"):
            ar.hash_columns(frame, subset=["age"])

    def test_empty_subset_raises_value_error(self):
        frame = self._frame()
        with pytest.raises(ValueError, match="non-empty"):
            ar.hash_columns(frame, subset=[])

    def test_unsupported_algorithm_raises_value_error(self):
        frame = self._frame()
        with pytest.raises(ValueError, match="algorithm"):
            ar.hash_columns(frame, subset=["email"], algorithm="sha512")

    def test_pipeline_step(self):
        import hashlib

        frame = self._frame()
        result = ar.pipeline(
            frame,
            [("hash_columns", {"subset": ["email", "user_id"], "algorithm": "sha256"})],
        )
        df = ar.to_pandas(result)
        assert df["email"].iloc[0] == hashlib.sha256(b"user@example.com").hexdigest()

    def test_pipeline_step_default_algorithm(self):
        import hashlib

        frame = self._frame()
        result = ar.pipeline(frame, [("hash_columns", {"subset": ["user_id"]})])
        df = ar.to_pandas(result)
        assert df["user_id"].iloc[0] == hashlib.sha256(b"abc123").hexdigest()

    def test_input_frame_is_not_mutated(self):

        frame = self._frame()
        df_before = ar.to_pandas(frame).copy()
        ar.hash_columns(frame, subset=["email", "user_id"])
        df_after = ar.to_pandas(frame)
        # Original frame must be byte-for-byte identical after the call
        assert df_after["email"].iloc[0] == df_before["email"].iloc[0]
        assert df_after["user_id"].iloc[0] == df_before["user_id"].iloc[0]
        assert pd.isna(df_after["email"].iloc[1]) == pd.isna(df_before["email"].iloc[1])
