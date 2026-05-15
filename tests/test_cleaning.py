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


class TestDropEmptyColumns:
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
        result = ar.pipeline(frame,[("drop_empty_columns",)],)
        assert "empty_num" not in result.columns
        assert "empty_text" not in result.columns


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
