"""Tests for data cleaning functions."""

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
