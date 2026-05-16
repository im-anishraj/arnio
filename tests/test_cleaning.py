"""Tests for data cleaning functions."""

import pandas as pd
import pytest

import arnio as ar


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

    def test_drop_dupes_subset(self, csv_with_duplicates):
        frame = ar.read_csv(csv_with_duplicates)
        result = ar.drop_duplicates(frame, subset=["name"])
        assert result.shape[0] == 3


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


class TestRenameColumns:
    def test_rename(self, sample_csv):
        frame = ar.read_csv(sample_csv)
        result = ar.rename_columns(frame, {"name": "full_name", "age": "years"})
        assert "full_name" in result.columns
        assert "years" in result.columns
        assert "name" not in result.columns


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
        with pytest.raises(IndexError, match="Column not found"):
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
class TestSlugifyColumnNames:
    # ------------------------------------------------------------------
    # Normal conversions
    # ------------------------------------------------------------------
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

    def test_hyphens_become_underscores(self):
        frame = ar.from_pandas(pd.DataFrame({"order-id": [42]}))
        result = ar.slugify_column_names(frame)
        assert result.columns == ["order_id"]

    def test_leading_trailing_whitespace_stripped(self):
        frame = ar.from_pandas(pd.DataFrame({"  age  ": [30]}))
        result = ar.slugify_column_names(frame)
        assert result.columns == ["age"]

    def test_repeated_separators_collapsed(self):
        frame = ar.from_pandas(pd.DataFrame({"first__last": ["x"]}))
        result = ar.slugify_column_names(frame)
        assert result.columns == ["first_last"]

    def test_multiple_columns_all_slugified(self):
        frame = ar.from_pandas(
            pd.DataFrame({"First Name": ["A"], "Revenue ($)": [1.0], "ID": [1]})
        )
        result = ar.slugify_column_names(frame)
        assert result.columns == ["first_name", "revenue", "id"]

    # ------------------------------------------------------------------
    # Column order preserved
    # ------------------------------------------------------------------
    def test_column_order_preserved(self):
        frame = ar.from_pandas(
            pd.DataFrame({"Z Col": [1], "A Col": [2], "M Col": [3]})
        )
        result = ar.slugify_column_names(frame)
        assert result.columns == ["z_col", "a_col", "m_col"]

    # ------------------------------------------------------------------
    # Already-clean names are a no-op
    # ------------------------------------------------------------------
    def test_already_clean_name_unchanged(self):
        frame = ar.from_pandas(pd.DataFrame({"user_id": [1], "revenue": [9.9]}))
        result = ar.slugify_column_names(frame)
        assert result.columns == ["user_id", "revenue"]

    def test_already_clean_data_unchanged(self):
        df = pd.DataFrame({"score": [1, 2, 3]})
        frame = ar.from_pandas(df)
        result = ar.slugify_column_names(frame)
        result_df = ar.to_pandas(result)
        assert list(result_df["score"]) == [1, 2, 3]

    # ------------------------------------------------------------------
    # Duplicate-name behaviour
    # ------------------------------------------------------------------
    def test_duplicate_slug_raises_by_default(self):
        # "Name" and "name" both slug to "name"
        frame = ar.from_pandas(pd.DataFrame({"Name": ["A"], "name": ["B"]}))
        with pytest.raises(ValueError, match="duplicate column names"):
            ar.slugify_column_names(frame)

    def test_duplicate_slug_ignore_keeps_first(self):
        frame = ar.from_pandas(pd.DataFrame({"Name": ["A"], "name": ["B"]}))
        result = ar.slugify_column_names(frame, duplicates="ignore")
        result_df = ar.to_pandas(result)
        assert result_df.columns.tolist() == ["name"]
        # First column ("Name" → "A") is kept
        assert result_df["name"].iloc[0] == "A"

    def test_duplicate_slug_error_message_names_both_columns(self):
        frame = ar.from_pandas(pd.DataFrame({"Revenue ($)": [1.0], "Revenue": [2.0]}))
        with pytest.raises(ValueError, match="revenue"):
            ar.slugify_column_names(frame)

    def test_invalid_duplicates_value_raises(self):
        frame = ar.from_pandas(pd.DataFrame({"col": [1]}))
        with pytest.raises(ValueError, match="duplicates must be"):
            ar.slugify_column_names(frame, duplicates="drop")

    # ------------------------------------------------------------------
    # Pipeline integration
    # ------------------------------------------------------------------
    def test_registered_as_pipeline_step(self):
        frame = ar.from_pandas(
            pd.DataFrame({"First Name": ["Alice"], "Revenue ($)": [100.0]})
        )
        result = ar.pipeline(frame, [("slugify_column_names",)])
        assert result.columns == ["first_name", "revenue"]

    def test_pipeline_step_with_duplicates_kwarg(self):
        frame = ar.from_pandas(pd.DataFrame({"Name": ["A"], "name": ["B"]}))
        result = ar.pipeline(
            frame, [("slugify_column_names", {"duplicates": "ignore"})]
        )
        assert result.columns == ["name"]

    # ------------------------------------------------------------------
    # Edge cases
    # ------------------------------------------------------------------
    def test_empty_frame_no_columns(self):
        frame = ar.from_pandas(pd.DataFrame())
        result = ar.slugify_column_names(frame)
        assert result.columns == []

    def test_single_column(self):
        frame = ar.from_pandas(pd.DataFrame({"  Revenue ($)  ": [1.0]}))
        result = ar.slugify_column_names(frame)
        assert result.columns == ["revenue"]