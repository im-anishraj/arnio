"""Tests for data cleaning functions."""

import pandas as pd
import pytest

import arnio as ar
from arnio import from_pandas, to_pandas


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


class TestKeepRowsWithNulls:
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
        with pytest.raises(ValueError, match="unknown column"):
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

    def test_drop_columns_allows_empty_input_as_no_op(self, sample_csv):
        frame = ar.read_csv(sample_csv)

        result = ar.drop_columns(frame, [])

        assert result is frame

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

    def test_drop_columns_rejects_removing_all_columns(self):
        frame = ar.from_pandas(pd.DataFrame({"id": [1, 2], "name": ["a", "b"]}))

        with pytest.raises(ValueError, match="drop_columns cannot remove all columns"):
            ar.drop_columns(frame, ["id", "name"])


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

    def test_drop_constant_columns_all_columns_dropped_reports_zero_rows(self):
        frame = ar.from_pandas(pd.DataFrame({"a": [1], "b": ["x"], "c": [None]}))

        result = ar.drop_constant_columns(frame)

        assert result.columns == []
        assert result.shape[0] == 0
        assert result.shape[1] == 0


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

    def test_clip_numeric_non_integral_bound_on_float64_accepted(self):
        # Non-integral bounds are valid for float64 columns.
        frame = ar.from_pandas(pd.DataFrame({"v": [-1.0, 2.5, 9.9]}))

        result = ar.clip_numeric(frame, lower=1.5, upper=8.3)
        df = ar.to_pandas(result)

        assert list(df["v"]) == [1.5, 2.5, 8.3]


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

    def test_standardize_missing_tokens_unknown_subset_column_raises(self):
        frame = ar.from_pandas(pd.DataFrame({"value": [1, 2, 3]}))
        with pytest.raises(ValueError, match="Unknown columns in subset"):
            ar.standardize_missing_tokens(frame, subset=["missing"])


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


class TestNormalizeUnicode:
    def test_normalize_unicode(self):
        import pandas as pd

        import arnio as ar

        df = pd.DataFrame({"text": ["cafe\u0301"]})

        frame = ar.from_pandas(df)

        result = ar.normalize_unicode(frame)

        result_df = ar.to_pandas(result)

        assert result_df["text"].iloc[0] == "café"


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


class TestRenameColumns:
    def test_rename(self, sample_csv):
        frame = ar.read_csv(sample_csv)
        result = ar.rename_columns(frame, {"name": "full_name", "age": "years"})
        assert "full_name" in result.columns
        assert "years" in result.columns
        assert "name" not in result.columns

    def test_rename_rejects_non_mapping(self, sample_csv):
        frame = ar.read_csv(sample_csv)

        with pytest.raises(TypeError, match="mapping must be a mapping"):
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


class TestTrimColumnNames:
    def test_trim_column_names_basic(self):
        df = pd.DataFrame({" name ": [1], " age ": [2]})
        frame = from_pandas(df)
        result = ar.trim_column_names(frame)
        assert to_pandas(result).columns.tolist() == ["name", "age"]

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

        with pytest.raises(ValueError, match="errors must be either"):
            ar.cast_types(frame, {"age": "int64"}, errors="ignore")

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

        with pytest.raises(TypeError, match="mapping must be a mapping"):
            ar.cast_types(frame, mapping)

    def test_cast_bool_rejects_unknown_strings(self):
        frame = ar.from_pandas(pd.DataFrame({"active": ["true", "maybe"]}))

        with pytest.raises(ar.TypeCastError, match="Cannot cast column 'active'"):
            ar.cast_types(frame, {"active": "bool"})


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
        # reuse csv_with_nulls as it has a null row (Bob missing name)
        frame = ar.read_csv(csv_with_nulls)
        # Drop nulls
        result = ar.clean(frame, strip_whitespace=False, drop_nulls=True)
        assert len(result) < len(frame)


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


class TestRoundNumericColumns:
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
        with pytest.raises(TypeError, match="subset must be a list"):
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

    def test_round_subset_with_non_numeric(self):
        import pandas as pd

        df = pd.DataFrame({"name": ["john"], "score": [98.765]})
        frame = ar.from_pandas(df)
        result = ar.round_numeric_columns(frame, subset=["name", "score"], decimals=1)
        result_df = ar.to_pandas(result)

        assert list(result_df["name"]) == ["john"]
        assert list(result_df["score"]) == [98.8]


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

    def test_output_column_already_exists(self, tmp_path):
        import warnings

        path = tmp_path / "data.csv"
        path.write_text("revenue,cost,ratio\n100,50,99\n200,100,99\n")
        frame = ar.read_csv(path)
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = ar.safe_divide_columns(
                frame, numerator="revenue", denominator="cost", output_column="ratio"
            )
            assert len(w) == 1
            assert "already exists" in str(w[0].message)
        df = ar.to_pandas(result)
        assert df["ratio"].iloc[0] == 2.0

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
