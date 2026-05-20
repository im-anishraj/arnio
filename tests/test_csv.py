"""Tests for CSV reading functionality."""

import builtins
import io
import os
import re
from pathlib import Path

import pandas as pd
import pytest

import arnio as ar
from arnio.exceptions import CsvReadError
from arnio.io import _utf8_csv_path

MESSY_CSV = str(Path(__file__).parent / "fixtures" / "messy_sales_data.csv")


class ChunkTrackingTextStream:
    def __init__(self, chunks):
        self._chunks = iter(chunks)
        self.read_sizes = []

    def read(self, size=-1):
        self.read_sizes.append(size)
        return next(self._chunks, "")


class TestReadCsv:
    def test_read_csv_dtype_override_string(self, tmp_path):
        path = tmp_path / "zip_codes.csv"
        path.write_text("zip,quantity\n07001,5\n08002,10\n")

        frame = ar.read_csv(
            path,
            dtype={"zip": "string"},
        )

        pdf = ar.to_pandas(frame)

        assert frame.dtypes["zip"] == "string"
        assert pdf["zip"].tolist() == ["07001", "08002"]

    def test_read_csv_dtype_mixed_inference(self, tmp_path):
        path = tmp_path / "mixed_types.csv"
        path.write_text("zip,price\n07001,12.5\n08002,20.0\n")

        frame = ar.read_csv(
            path,
            dtype={"zip": "string"},
        )

        assert frame.dtypes["zip"] == "string"
        assert frame.dtypes["price"] == "float64"

    def test_read_csv_dtype_rejects_non_string_mapping_entries(self, tmp_path):
        path = tmp_path / "bad_dtype_mapping.csv"
        path.write_text("age\n25\n")

        with pytest.raises(TypeError, match="dtype column names must be strings"):
            ar.read_csv(path, dtype={1: "int64"})

        with pytest.raises(TypeError, match="dtype values must be strings"):
            ar.read_csv(path, dtype={"age": int})

    def test_read_csv_dtype_with_generated_column_names(self, tmp_path):
        path = tmp_path / "no_header.csv"
        path.write_text("07001,5\n08002,10\n")

        frame = ar.read_csv(
            path,
            has_header=False,
            dtype={"col_0": "string", "col_1": "int64"},
        )

        pdf = ar.to_pandas(frame)

        assert frame.dtypes["col_0"] == "string"
        assert frame.dtypes["col_1"] == "int64"
        assert pdf["col_0"].tolist() == ["07001", "08002"]
        assert pdf["col_1"].tolist() == [5, 10]

    def test_read_csv_dtype_with_usecols(self, tmp_path):
        path = tmp_path / "usecols_dtype.csv"
        path.write_text("zip,quantity,price\n07001,5,12.5\n08002,10,20.0\n")

        frame = ar.read_csv(
            path,
            usecols=["zip", "price"],
            dtype={"zip": "string"},
        )

        pdf = ar.to_pandas(frame)

        assert list(pdf.columns) == ["zip", "price"]
        assert frame.dtypes["zip"] == "string"
        assert frame.dtypes["price"] == "float64"
        assert pdf["zip"].tolist() == ["07001", "08002"]

    def test_read_csv_fully_explicit_dtype_with_usecols(self, tmp_path):
        path = tmp_path / "usecols_full_dtype.csv"
        path.write_text("zip,quantity,price\n07001,5,12.5\n08002,10,20.0\n")

        frame = ar.read_csv(
            path,
            usecols=["zip", "price"],
            dtype={"zip": "string", "price": "float64"},
        )

        pdf = ar.to_pandas(frame)

        assert list(pdf.columns) == ["zip", "price"]
        assert frame.dtypes == {"zip": "string", "price": "float64"}
        assert pdf["zip"].tolist() == ["07001", "08002"]
        assert pdf["price"].tolist() == [12.5, 20.0]

    def test_read_csv_fully_explicit_dtype_preserves_bad_line_errors(self, tmp_path):
        path = tmp_path / "full_dtype_bad_line_error.csv"
        path.write_text("id,name\n1,Alice\n2,Bob,extra\n")

        with pytest.raises(ar.CsvReadError, match="CSV row 3 has 3 fields; expected 2"):
            ar.read_csv(
                path,
                dtype={"id": "int64", "name": "string"},
            )

    def test_read_csv_fully_explicit_dtype_preserves_bad_line_warnings(self, tmp_path):
        path = tmp_path / "full_dtype_bad_line_warn.csv"
        path.write_text("id,name\n1,Alice\n2,Bob,extra\n3,Cara\n")

        with pytest.warns(UserWarning, match="CSV row 3 has 3 fields; expected 2"):
            frame = ar.read_csv(
                path,
                dtype={"id": "int64", "name": "string"},
                on_bad_lines="warn",
            )

        pdf = ar.to_pandas(frame)

        assert frame.dtypes == {"id": "int64", "name": "string"}
        assert pdf["id"].tolist() == [1, 3]
        assert pdf["name"].tolist() == ["Alice", "Cara"]

    def test_read_csv_dtype_parse_failure_raises(self, tmp_path):
        path = tmp_path / "parse_failure.csv"
        path.write_text("quantity\nabc\n")

        with pytest.raises(
            ar.CsvReadError,
            match="Invalid token 'abc' for forced int64 column",
        ):
            ar.read_csv(
                path,
                dtype={"quantity": "int64"},
            )

    def test_read_csv_dtype_non_selected_usecols_column(self, tmp_path):
        path = tmp_path / "dtype_usecols_error.csv"
        path.write_text("zip,price\n07001,12.5\n")

        with pytest.raises(
            ar.CsvReadError,
            match="dtype specified for non-selected column",
        ):
            ar.read_csv(
                path,
                usecols=["zip"],
                dtype={"price": "float64"},
            )

    def test_read_csv_dtype_override_string_to_int64(self, tmp_path):
        path = tmp_path / "quantities.csv"
        path.write_text("quantity,label\n5,small\n10,large\n")

        frame = ar.read_csv(
            path,
            dtype={"quantity": "int64"},
        )

        pdf = ar.to_pandas(frame)

        assert frame.dtypes["quantity"] == "int64"
        assert pdf["quantity"].tolist() == [5, 10]

    def test_read_csv_invalid_dtype_name(self, tmp_path):
        path = tmp_path / "invalid_dtype.csv"
        path.write_text("age\n25\n")

        with pytest.raises(ValueError, match="Unsupported dtype"):
            ar.read_csv(
                path,
                dtype={"age": "datetime"},
            )

    def test_read_csv_dtype_unknown_column(self, tmp_path):
        path = tmp_path / "unknown_column.csv"
        path.write_text("age,name\n25,Alice\n")

        with pytest.raises(ar.CsvReadError, match="Column not found in dtype mapping"):
            ar.read_csv(
                path,
                dtype={"salary": "float64"},
            )

    def test_basic_read(self, sample_csv):
        frame = ar.read_csv(sample_csv)
        assert isinstance(frame, ar.ArFrame)
        assert frame.shape == (3, 4)
        assert frame.columns == ["name", "age", "email", "active"]

    def test_usecols(self, sample_csv):
        frame = ar.read_csv(sample_csv, usecols=["name", "age"])
        assert frame.shape == (3, 2)
        assert frame.columns == ["name", "age"]

    def test_nrows(self, sample_csv):
        frame = ar.read_csv(sample_csv, nrows=2)
        assert frame.shape == (2, 4)

    def test_invalid_delimiter(self, tmp_path):
        csv_path = tmp_path / "test.csv"
        csv_path.write_text("a,b\n1,2\n")

        with pytest.raises(ValueError, match="delimiter must be exactly one character"):
            ar.read_csv(csv_path, delimiter="::")

        with pytest.raises(ValueError, match="delimiter must be exactly one character"):
            ar.read_csv(csv_path, delimiter="")

        with pytest.raises(TypeError, match="delimiter must be a string"):
            ar.read_csv(csv_path, delimiter=1)

    def test_invalid_usecols(self, tmp_path):
        csv_path = tmp_path / "test.csv"
        csv_path.write_text("id,name\n1,Alice\n")

        with pytest.raises(
            TypeError,
            match="usecols must be a sequence of column names, not a string",
        ):
            ar.read_csv(csv_path, usecols="name")

        with pytest.raises(
            TypeError,
            match="usecols must contain only strings",
        ):
            ar.read_csv(csv_path, usecols=[123])

        with pytest.raises(
            ValueError,
            match="usecols must not contain duplicate column names",
        ):
            ar.read_csv(csv_path, usecols=["id", "id"])

        with pytest.raises(
            ValueError,
            match="usecols must not be empty",
        ):
            ar.read_csv(csv_path, usecols=[])

    def test_invalid_empty_usecols_chunked(self, tmp_path):
        csv_path = tmp_path / "chunked.csv"
        csv_path.write_text("id,name\n1,Alice\n2,Bob\n")

        with pytest.raises(
            ValueError,
            match="usecols must not be empty",
        ):
            list(ar.read_csv_chunked(csv_path, chunksize=1, usecols=[]))

    def test_invalid_nrows(self, tmp_path):
        csv_path = tmp_path / "test.csv"
        csv_path.write_text("a,b\n1,2\n")

        with pytest.raises(TypeError, match="nrows must be an integer"):
            ar.read_csv(csv_path, nrows=True)

        with pytest.raises(TypeError, match="nrows must be an integer"):
            ar.read_csv(csv_path, nrows=1.5)

        with pytest.raises(ValueError, match="nrows must be non-negative"):
            ar.read_csv(csv_path, nrows=-1)

    def test_no_header(self, csv_no_header):
        frame = ar.read_csv(csv_no_header, has_header=False)
        assert frame.shape == (2, 3)
        assert "col_0" in frame.columns

    def test_type_inference(self, sample_csv):
        frame = ar.read_csv(sample_csv)
        dtypes = frame.dtypes
        assert dtypes["age"] == "int64"
        assert dtypes["name"] == "string"
        assert dtypes["active"] == "bool"

    # ----------------------------
    # Thousands separator tests
    # ----------------------------

    def test_thousands_separator_comma(self, tmp_path):
        csv_path = tmp_path / "comma_thousands.csv"
        csv_path.write_text('value\n"1,234"\n')
        frame = ar.read_csv(csv_path, thousands_separator=",")
        df = ar.to_pandas(frame)
        assert df["value"].iloc[0] == 1234

    def test_thousands_separator_space(self, tmp_path):
        csv_path = tmp_path / "space_thousands.csv"
        csv_path.write_text("value\n1 234\n")
        frame = ar.read_csv(csv_path, thousands_separator=" ")
        df = ar.to_pandas(frame)
        assert df["value"].iloc[0] == 1234

    def test_valid_float_thousands_separator(self, tmp_path):
        csv_path = tmp_path / "float.csv"
        csv_path.write_text('value\n"1,234.56"\n')
        frame = ar.read_csv(csv_path, thousands_separator=",")
        df = ar.to_pandas(frame)
        assert df["value"].iloc[0] == 1234.56

    def test_default_behavior_without_thousands_separator(self, tmp_path):
        csv_path = tmp_path / "default_behavior.csv"
        csv_path.write_text('value\n"1,234"\n')
        frame = ar.read_csv(csv_path)
        df = ar.to_pandas(frame)
        assert df["value"].iloc[0] == "1,234"

    def test_decimal_separator_comma_with_semicolon_delimiter(self, tmp_path):
        csv_path = tmp_path / "comma_decimal_semicolon.csv"
        csv_path.write_text("value;label\n12,45;gross\n0,5;half\n")
        frame = ar.read_csv(csv_path, delimiter=";", decimal_separator=",")
        df = ar.to_pandas(frame)
        assert frame.dtypes["value"] == "float64"
        assert df["value"].tolist() == pytest.approx([12.45, 0.5])

    def test_decimal_separator_comma_with_quoted_comma_delimiter(self, tmp_path):
        csv_path = tmp_path / "quoted_comma_decimal.csv"
        csv_path.write_text('value\n"12,45"\n"-0,5"\n')
        frame = ar.read_csv(csv_path, decimal_separator=",")
        df = ar.to_pandas(frame)
        assert df["value"].tolist() == pytest.approx([12.45, -0.5])

    def test_decimal_separator_default_preserves_comma_values(self, tmp_path):
        csv_path = tmp_path / "default_comma_decimal.csv"
        csv_path.write_text('value\n"12,45"\n')
        frame = ar.read_csv(csv_path)
        df = ar.to_pandas(frame)
        assert frame.dtypes["value"] == "string"
        assert df["value"].iloc[0] == "12,45"

    def test_decimal_separator_with_dot_thousands_separator(self, tmp_path):
        csv_path = tmp_path / "european_number.csv"
        csv_path.write_text('value\n"1.234,56"\n')
        frame = ar.read_csv(
            csv_path,
            decimal_separator=",",
            thousands_separator=".",
        )
        df = ar.to_pandas(frame)
        assert df["value"].iloc[0] == pytest.approx(1234.56)

    def test_mixed_decimal_formats_become_null(self, tmp_path):
        csv_path = tmp_path / "mixed_decimal_formats.csv"
        csv_path.write_text('value\n"12,45"\n"12.45"\n')
        frame = ar.read_csv(csv_path, decimal_separator=",")
        df = ar.to_pandas(frame)
        assert frame.dtypes["value"] == "float64"
        assert df["value"].iloc[0] == pytest.approx(12.45)
        assert pd.isna(df["value"].iloc[1])

    def test_scan_csv_decimal_separator_matches_read_csv(self, tmp_path):
        csv_path = tmp_path / "scan_comma_decimal.csv"
        csv_path.write_text('value\n"12,45"\n')
        assert ar.scan_csv(csv_path, decimal_separator=",")["value"] == "float64"
        assert ar.read_csv(csv_path, decimal_separator=",").dtypes["value"] == "float64"

    def test_read_csv_chunked_decimal_separator(self, tmp_path):
        csv_path = tmp_path / "chunked_comma_decimal.csv"
        csv_path.write_text("value;label\n12,45;a\n67,89;b\n")
        chunks = list(
            ar.read_csv_chunked(
                csv_path,
                chunksize=1,
                delimiter=";",
                decimal_separator=",",
            )
        )
        assert [
            ar.to_pandas(chunk)["value"].iloc[0] for chunk in chunks
        ] == pytest.approx([12.45, 67.89])

    @pytest.mark.parametrize("separator", ["", "a", "3", "ab", "\n", '"', "+", "-"])
    def test_invalid_decimal_separator(self, tmp_path, separator):
        csv_path = tmp_path / "decimal_separator.csv"
        csv_path.write_text("value\n1234\n")
        with pytest.raises(ValueError):
            ar.read_csv(csv_path, decimal_separator=separator)
        with pytest.raises(ValueError):
            ar.scan_csv(csv_path, decimal_separator=separator)

    @pytest.mark.parametrize("separator", [1, 1.5, True, [], {}])
    def test_invalid_non_string_decimal_separator(self, tmp_path, separator):
        csv_path = tmp_path / "decimal_separator_type.csv"
        csv_path.write_text("value\n1234\n")
        with pytest.raises(TypeError):
            ar.read_csv(csv_path, decimal_separator=separator)
        with pytest.raises(TypeError):
            ar.scan_csv(csv_path, decimal_separator=separator)

    def test_thousands_separator_must_differ_from_decimal_separator(self, tmp_path):
        csv_path = tmp_path / "same_separators.csv"
        csv_path.write_text("value\n1234\n")
        with pytest.raises(ValueError, match="must differ"):
            ar.read_csv(csv_path, decimal_separator=",", thousands_separator=",")
        with pytest.raises(ValueError, match="must differ"):
            ar.scan_csv(csv_path, decimal_separator=",", thousands_separator=",")

    @pytest.mark.parametrize(
        "separator", ["", "a", "3", "ab", "\n", '"', ".", "+", "-"]
    )
    def test_invalid_thousands_separator(self, tmp_path, separator):
        csv_path = tmp_path / "default_behavior.csv"
        csv_path.write_text("value\n1234\n")
        with pytest.raises(ValueError):
            ar.read_csv(csv_path, thousands_separator=separator)
        with pytest.raises(ValueError):
            ar.scan_csv(csv_path, thousands_separator=separator)

    @pytest.mark.parametrize("separator", [1, 1.5, True, [], {}])
    def test_invalid_non_string_thousands_separator(self, tmp_path, separator):
        csv_path = tmp_path / "test.csv"
        csv_path.write_text("value\n1234\n")
        with pytest.raises(TypeError):
            ar.read_csv(csv_path, thousands_separator=separator)
        with pytest.raises(TypeError):
            ar.scan_csv(csv_path, thousands_separator=separator)

    def test_thousands_separator_not_applied_to_strings(self, tmp_path):
        csv_path = tmp_path / "string.csv"
        csv_path.write_text('message\n"hello,world"\n')
        frame = ar.read_csv(csv_path, thousands_separator=",")
        df = ar.to_pandas(frame)
        assert df["message"].iloc[0] == "hello,world"

    @pytest.mark.parametrize(
        "value",
        ["12,34", "1,,234", "1234,", ",123"],
    )
    def test_invalid_thousands_grouping_remains_string(self, tmp_path, value):
        csv_path = tmp_path / "invalid.csv"
        csv_path.write_text(f'value\n"{value}"\n')
        frame = ar.read_csv(csv_path, thousands_separator=",")
        assert frame.dtypes["value"] == "string"

    def test_unquoted_comma_value_with_comma_delimiter(self, tmp_path):
        csv_path = tmp_path / "delimiter_interaction.csv"
        csv_path.write_text("value\n1,234\n")
        with pytest.raises(ar.CsvReadError, match="CSV row 2 has 2 fields; expected 1"):
            ar.read_csv(csv_path)

    def test_read_csv_rejects_missing_fields(self, tmp_path):
        csv_path = tmp_path / "missing_fields.csv"
        csv_path.write_text("a,b\n1,2\n3\n")

        with pytest.raises(ar.CsvReadError, match="CSV row 3 has 1 fields; expected 2"):
            ar.read_csv(csv_path)

    def test_read_csv_rejects_extra_fields_without_header(self, tmp_path):
        csv_path = tmp_path / "extra_fields_no_header.csv"
        csv_path.write_text("1,2\n3,4,5\n")

        with pytest.raises(ar.CsvReadError, match="CSV row 2 has 3 fields; expected 2"):
            ar.read_csv(csv_path, has_header=False)

    def test_large_integer_overflow_remains_string(self, tmp_path):
        csv_path = tmp_path / "large_integer.csv"
        csv_path.write_text("value\n9223372036854775808\n")

        frame = ar.read_csv(csv_path)
        df = ar.to_pandas(frame)

        assert frame.dtypes["value"] == "string"
        assert df["value"].iloc[0] == "9223372036854775808"

    def test_mixed_integer_overflow_promotes_column_to_string(self, tmp_path):
        csv_path = tmp_path / "mixed_large_integer.csv"
        csv_path.write_text("value\n1\n9223372036854775808\n")

        frame = ar.read_csv(csv_path)
        df = ar.to_pandas(frame)

        assert frame.dtypes["value"] == "string"
        assert list(df["value"]) == ["1", "9223372036854775808"]

    def test_thousands_separator_negative_numbers(self, tmp_path):
        csv_path = tmp_path / "negative_numbers.csv"
        csv_path.write_text('value\n"-1,234"\n')
        frame = ar.read_csv(csv_path, thousands_separator=",")
        df = ar.to_pandas(frame)
        assert df["value"].iloc[0] == -1234

    def test_thousands_separator_large_numbers(self, tmp_path):
        csv_path = tmp_path / "large.csv"
        csv_path.write_text('value\n"1,234,567,890"\n')
        frame = ar.read_csv(csv_path, thousands_separator=",")
        df = ar.to_pandas(frame)
        assert df["value"].iloc[0] == 1234567890

    def test_mixed_int_and_float_consistency(self, tmp_path):
        csv_path = tmp_path / "mixed.csv"
        csv_path.write_text('value\n"1,234"\n"2,345.67"\n"3,000"\n')
        frame = ar.read_csv(csv_path, thousands_separator=",")
        df = ar.to_pandas(frame)
        assert df["value"].iloc[0] == 1234
        assert df["value"].iloc[1] == 2345.67
        assert df["value"].iloc[2] == 3000

    def test_thousands_separator_with_whitespace(self, tmp_path):
        csv_path = tmp_path / "ws.csv"
        csv_path.write_text('value\n" 1,234 "\n')
        frame = ar.read_csv(csv_path, thousands_separator=",")
        df = ar.to_pandas(frame)
        assert df["value"].iloc[0] == 1234

    def test_thousands_separator_empty_values(self, tmp_path):
        csv_path = tmp_path / "empty.csv"
        csv_path.write_text('value\n""\n"1,234"\n')
        frame = ar.read_csv(csv_path, thousands_separator=",")
        df = ar.to_pandas(frame)
        assert pd.isna(df["value"].iloc[0])
        assert df["value"].iloc[1] == 1234

    def test_invalid_grouped_integer_values_become_null(self, tmp_path):
        csv_content = 'value\n"1,234"\n"+1,234"\n"-1,234"\n"12,34"\n"1,,234"\n"123,45"\n"-12,34"\n'
        csv_file = tmp_path / "invalid_grouping.csv"
        csv_file.write_text(csv_content)
        frame = ar.read_csv(csv_file, thousands_separator=",")
        df = ar.to_pandas(frame)
        assert df["value"].iloc[0] == 1234
        assert df["value"].iloc[1] == 1234
        assert df["value"].iloc[2] == -1234
        invalid_indices = [3, 4, 5, 6]
        for idx in invalid_indices:
            assert pd.isna(df["value"].iloc[idx])

    def test_invalid_grouped_float_values_become_null(self, tmp_path):
        csv_content = 'value\n"1,234.56"\n"12,34.56"\n"1,,234.56"\n"123,45.67"'
        csv_file = tmp_path / "invalid_float_grouping.csv"
        csv_file.write_text(csv_content)
        frame = ar.read_csv(csv_file, thousands_separator=",")
        df = ar.to_pandas(frame)
        assert df["value"].iloc[0] == 1234.56
        invalid_indices = [1, 2, 3]
        for idx in invalid_indices:
            assert pd.isna(df["value"].iloc[idx])

    def test_alphanumeric_grouped_values_remain_string(self, tmp_path):
        csv_content = 'value\n"1a,234"\n"123,abc"\n'
        csv_file = tmp_path / "alnum.csv"
        csv_file.write_text(csv_content)
        frame = ar.read_csv(csv_file, thousands_separator=",")
        df = ar.to_pandas(frame)
        assert frame.dtypes["value"] == "string"
        assert df["value"].iloc[0] == "1a,234"
        assert df["value"].iloc[1] == "123,abc"

    def test_large_csv(self, large_csv):
        frame = ar.read_csv(large_csv)
        assert frame.shape == (1000, 3)

    def test_memory_usage(self, sample_csv):
        frame = ar.read_csv(sample_csv)
        assert frame.memory_usage() > 0

    def test_repr(self, sample_csv):
        frame = ar.read_csv(sample_csv)
        assert "3 rows" in repr(frame)
        assert "4 cols" in repr(frame)

    def test_len(self, sample_csv):
        frame = ar.read_csv(sample_csv)
        assert len(frame) == 3

    def test_has_column(self, sample_csv):
        frame = ar.read_csv(sample_csv)
        assert frame.has_column("name") is True
        assert frame.has_column("missing") is False

    def test_get_column_dtype(self, sample_csv):
        frame = ar.read_csv(sample_csv)
        assert frame.get_column_dtype("age") == "int64"

    def test_get_column_dtype_missing_raises_key_error(self, sample_csv):
        frame = ar.read_csv(sample_csv)
        with pytest.raises(KeyError, match="Column not found: missing"):
            frame.get_column_dtype("missing")

    def test_header_whitespace(self, tmp_path):

        assert "name" in frame
        assert "missing" not in frame
        assert 123 not in frame

    def test_header_whitespace(self, tmp_path):
        csv_path = str(tmp_path / "whitespace.csv")
        with open(csv_path, "w") as f:
            f.write("name ,  age\nAlice,25\n")

        frame = ar.read_csv(csv_path)
        assert frame.columns == ["name", "age"]

    def test_trim_headers_true_is_default(self, tmp_path):
        csv_path = str(tmp_path / "trim.csv")
        with open(csv_path, "w") as f:
            f.write(" name ,  age \nAlice,30\n")

        frame = ar.read_csv(csv_path)
        assert frame.columns == ["name", "age"]

    def test_trim_headers_false_preserves_spaces(self, tmp_path):
        csv_path = str(tmp_path / "notrim.csv")
        with open(csv_path, "w") as f:
            f.write(" name ,  age \nAlice,30\n")

        frame = ar.read_csv(csv_path, trim_headers=False)
        assert frame.columns == [" name ", "  age "]

    def test_trim_headers_false_scan_csv(self, tmp_path):
        csv_path = str(tmp_path / "scan_notrim.csv")
        with open(csv_path, "w") as f:
            f.write(" score , active \n95,true\n")

        schema = ar.scan_csv(csv_path, trim_headers=False)
        assert " score " in schema
        assert " active " in schema

    def test_unsupported_extension(self, tmp_path):
        import pytest

        frame = ar.read_csv(csv_path)
        assert frame.columns == ["name", "age"]

    def test_trim_headers_false_preserves_spaces(self, tmp_path):
        csv_path = str(tmp_path / "notrim.csv")
        with open(csv_path, "w") as f:
            f.write(" name ,  age \nAlice,30\n")

        frame = ar.read_csv(csv_path, trim_headers=False)
        assert frame.columns == [" name ", "  age "]

    def test_trim_headers_false_scan_csv(self, tmp_path):
        csv_path = str(tmp_path / "scan_notrim.csv")
        with open(csv_path, "w") as f:
            f.write(" score , active \n95,true\n")

        schema = ar.scan_csv(csv_path, trim_headers=False)
        assert " score " in schema
        assert " active " in schema

    # ------------------------------------------------------------------
    # Whitespace-duplicate header tests (issue #117)
    # ------------------------------------------------------------------

    def test_exact_duplicate_headers_rejected(self, tmp_path):
        """Exact duplicate column names are always rejected."""
        csv_path = tmp_path / "dup.csv"
        csv_path.write_text("a,a\n1,2\n")
        with pytest.raises(ar.CsvReadError, match="[Dd]uplicate"):
            ar.read_csv(csv_path)

    def test_whitespace_duplicate_headers_rejected_default_trim(self, tmp_path):
        """Headers differing only by whitespace are rejected (trim_headers=True)."""
        csv_path = tmp_path / "ws_dup.csv"
        csv_path.write_text("a , a\n1,2\n")
        with pytest.raises(
            ar.CsvReadError,
            match="[Dd]uplicate column name",
        ):
            ar.read_csv(csv_path)

    def test_whitespace_duplicate_headers_rejected_no_trim(self, tmp_path):
        """Headers differing only by whitespace are rejected even with trim_headers=False."""
        csv_path = tmp_path / "ws_dup_notrim.csv"
        csv_path.write_text("a , a\n1,2\n")
        with pytest.raises(
            ar.CsvReadError,
            match="[Dd]uplicate column name",
        ):
            ar.read_csv(csv_path, trim_headers=False)

    def test_tab_whitespace_duplicate_headers_rejected(self, tmp_path):
        """Tab-padded headers that collapse to the same name are rejected."""
        csv_path = tmp_path / "tab_dup.csv"
        csv_path.write_bytes(b"a\t,a\n1,2\n")  # "a\t" vs "a" after trim
        with pytest.raises(
            ar.CsvReadError,
            match="[Dd]uplicate column name",
        ):
            ar.read_csv(csv_path)

    def test_mixed_whitespace_duplicate_headers_rejected(self, tmp_path):
        """Mixed leading/trailing spaces and tabs are caught."""
        csv_path = tmp_path / "mixed_ws_dup.csv"
        # " a " and "\ta\t" both trim to "a"
        csv_path.write_bytes(b" a , \ta\t\n1,2\n")
        with pytest.raises(
            ar.CsvReadError,
            match="[Dd]uplicate column name",
        ):
            ar.read_csv(csv_path)

    def test_unique_headers_with_whitespace_accepted(self, tmp_path):
        """Headers that are unique after trimming are accepted normally."""
        csv_path = tmp_path / "unique_ws.csv"
        csv_path.write_text(" name , age \n1,2\n")
        frame = ar.read_csv(csv_path)
        assert frame.columns == ["name", "age"]

    def test_whitespace_duplicate_scan_csv_rejected(self, tmp_path):
        """scan_csv also rejects whitespace-duplicate headers."""
        csv_path = tmp_path / "scan_ws_dup.csv"
        csv_path.write_text("a , a\n1,2\n")
        with pytest.raises(
            ar.CsvReadError,
            match="[Dd]uplicate column name",
        ):
            ar.scan_csv(csv_path)

    def test_whitespace_duplicate_scan_csv_no_trim_rejected(self, tmp_path):
        """scan_csv with trim_headers=False still rejects whitespace-duplicate headers."""
        csv_path = tmp_path / "scan_ws_dup_notrim.csv"
        csv_path.write_text("a , a\n1,2\n")
        with pytest.raises(
            ar.CsvReadError,
            match="[Dd]uplicate column name",
        ):
            ar.scan_csv(csv_path, trim_headers=False)

    def test_whitespace_duplicate_chunked_rejected(self, tmp_path):
        """read_csv_chunked also rejects whitespace-duplicate headers."""
        csv_path = tmp_path / "chunked_ws_dup.csv"
        csv_path.write_text("a , a\n1,2\n")
        with pytest.raises(
            ar.CsvReadError,
            match="[Dd]uplicate column name",
        ):
            list(ar.read_csv_chunked(str(csv_path)))

    def test_whitespace_duplicate_error_message_names_column(self, tmp_path):
        """The error message includes the colliding column name."""
        csv_path = tmp_path / "named_dup.csv"
        csv_path.write_text("score , score\n1,2\n")
        with pytest.raises(ar.CsvReadError, match="score"):
            ar.read_csv(csv_path)

    def test_non_standard_extension_accepted(self, tmp_path):
        """Non-standard extensions no longer raise ValueError (fixes #34)."""
        for ext in (".dat", ".log", ".data", ".pipe"):
            p = tmp_path / f"data{ext}"
            p.write_text("name,age\nAlice,30\n")
            frame = ar.read_csv(str(p))
            assert isinstance(frame, ar.ArFrame)
            assert frame.columns == ["name", "age"]

    def test_tsv_auto_delimiter(self, tmp_path):
        """read_csv auto-uses tab delimiter for .tsv files (fixes #34)."""
        tsv = tmp_path / "data.tsv"
        tsv.write_text("name\tage\nAlice\t30\nBob\t25\n")
        frame = ar.read_csv(str(tsv))
        assert frame.columns == ["name", "age"]
        assert frame.shape == (2, 2)

    def test_tsv_explicit_delimiter_honoured(self, tmp_path):
        """Explicitly supplied delimiter is never overridden for .tsv (fixes #34)."""
        tsv = tmp_path / "pipe.tsv"
        tsv.write_text("name|age\nAlice|30\n")
        frame = ar.read_csv(str(tsv), delimiter="|")
        assert frame.columns == ["name", "age"]
        assert frame.shape == (1, 2)

    def test_tsv_explicit_comma_delimiter_honoured(self, tmp_path):
        """Passing delimiter=',' to a .tsv file must preserve comma parsing (fixes #34)."""
        tsv = tmp_path / "comma.tsv"
        tsv.write_text("name,age\nAlice,30\n")
        frame = ar.read_csv(str(tsv), delimiter=",")
        assert frame.columns == ["name", "age"]
        assert frame.shape == (1, 2)

    def test_read_scan_csv_binary_file_parity(self, tmp_path):
        binary_file = tmp_path / "binary.csv"

        with open(binary_file, "wb") as f:
            f.write(b"\x00\x01\x02")

        expected_message = (
            "CSV input contains NUL bytes and appears to be binary or corrupted"
        )

        with pytest.raises(CsvReadError, match=re.escape(expected_message)):
            ar.read_csv(binary_file)

        with pytest.raises(CsvReadError, match=re.escape(expected_message)):
            ar.scan_csv(binary_file)

    def test_binary_file_rejection(self, tmp_path):
        file_path = str(tmp_path / "data.csv")
        with open(file_path, "wb") as f:
            f.write(b"col1,col2\n\0binary\0,data\n")

        with pytest.raises(
            ar.CsvReadError,
            match="CSV input contains NUL bytes and appears to be binary or corrupted",
        ):
            ar.read_csv(file_path)

    def test_late_binary_file_rejection(self, tmp_path):
        file_path = str(tmp_path / "data.csv")
        with open(file_path, "wb") as f:
            f.write(b"col1,col2\n")
            f.write(b"a,b\n" * 400)
            f.write(b"\0binary,data\n")

        with pytest.raises(
            ar.CsvReadError,
            match="CSV input contains NUL bytes and appears to be binary or corrupted",
        ):
            ar.read_csv(file_path)

    def test_read_with_nulls(self, csv_with_nulls):
        frame = ar.read_csv(csv_with_nulls)
        assert frame.shape == (4, 3)

        df = ar.to_pandas(frame)
        assert df["name"].isna().sum() == 1
        assert df["age"].isna().sum() == 1
        assert df["score"].isna().sum() == 1

        assert pd.isna(df.loc[1, "name"])
        assert pd.isna(df.loc[1, "score"])
        assert pd.isna(df.loc[2, "age"])

        assert df.loc[0, "name"] == "Alice"
        assert df.loc[3, "name"] == "Diana"

    def test_read_messy_nulls(self):
        frame = ar.read_csv(MESSY_CSV)
        assert frame.shape == (3, 3)

        df = ar.to_pandas(frame)
        assert df["revenue"].isna().sum() == 1
        assert pd.isna(df.loc[1, "revenue"])

    def test_empty_csv(self, empty_csv):
        frame = ar.read_csv(empty_csv)
        assert frame.shape == (0, 3)
        assert frame.columns == ["name", "age", "score"]

    def test_csv_with_all_nulls(self, csv_with_all_nulls):
        frame = ar.read_csv(csv_with_all_nulls)
        assert frame.shape == (2, 3)
        df = ar.to_pandas(frame)
        assert df["a"].isna().all()
        assert df["b"].isna().all()
        assert df["c"].isna().all()

    def test_utf8_bom_handling(self, tmp_path):
        csv_path = tmp_path / "bom.csv"
        csv_path.write_bytes(b"\xef\xbb\xbfname,age\nAlice,30\nBob,25\n")

        frame = ar.read_csv(str(csv_path), usecols=["name"])
        assert frame.columns == ["name"]
        assert frame.shape == (2, 1)

        schema = ar.scan_csv(str(csv_path))
        assert "name" in schema
        assert "\ufeffname" not in schema

    def test_invalid_utf8_read_csv_raises_with_path_and_encoding(self, tmp_path):
        csv_path = tmp_path / "bad_utf8.csv"
        csv_path.write_bytes(b"name\n\xff\n")

        with pytest.raises(ar.CsvReadError) as exc_info:
            ar.read_csv(csv_path, encoding="utf-8")

        msg = str(exc_info.value)
        assert "utf-8" in msg.lower()
        assert str(csv_path) in msg
        # This checks that the underlying UTF-8 validation failure remains
        # visible to callers. The match comes from the native parser message,
        # not the wrapper-injected encoding context.
        assert "invalid utf-8" in msg.lower()

    def test_invalid_utf8_scan_csv_raises_with_path_and_encoding(self, tmp_path):
        csv_path = tmp_path / "bad_utf8.csv"
        csv_path.write_bytes(b"name\n\xff\n")

        with pytest.raises(ar.CsvReadError) as exc_info:
            ar.scan_csv(csv_path, encoding="utf-8")

        msg = str(exc_info.value)

        assert "utf-8" in msg.lower()
        assert str(csv_path) in msg
        assert "invalid utf-8" in msg.lower()

    def test_invalid_utf8_read_csv_utf8_alias_also_raises(self, tmp_path):
        csv_path = tmp_path / "bad_utf8.csv"
        csv_path.write_bytes(b"name\n\xff\n")

        with pytest.raises(ar.CsvReadError) as exc_info:
            ar.read_csv(csv_path, encoding="utf8")

        msg = str(exc_info.value)

        assert str(csv_path) in msg
        assert "utf8" in msg.lower() or "utf-8" in msg.lower()
        assert "invalid utf-8" in msg.lower()

    def test_valid_utf8_still_reads(self, tmp_path):
        csv_path = tmp_path / "utf8.csv"
        csv_path.write_text("name\ncafé\n", encoding="utf-8")

        frame = ar.read_csv(csv_path, encoding="utf-8")

        assert frame.shape == (1, 1)

    def test_utf8_sig_still_reads(self, tmp_path):
        csv_path = tmp_path / "utf8sig.csv"
        csv_path.write_bytes(b"\xef\xbb\xbfname\nalice\n")

        frame = ar.read_csv(csv_path, encoding="utf-8")
        df = ar.to_pandas(frame)

        assert list(df.columns) == ["name"]
        assert "\ufeff" not in df.columns[0]
        assert df.iloc[0]["name"] == "alice"

    def test_latin1_transcoding_still_works(self, tmp_path):
        csv_path = tmp_path / "latin1.csv"
        csv_path.write_bytes("name\ncafé\n".encode("latin-1"))

        frame = ar.read_csv(csv_path, encoding="latin-1")
        df = ar.to_pandas(frame)
        assert df["name"].iloc[0] == "café"

    def test_pathlike_input(self, sample_csv):
        frame = ar.read_csv(Path(sample_csv))
        assert frame.shape == (3, 4)

    def test_read_csv_file_like_input_is_copied_in_bounded_chunks(self):
        stream = ChunkTrackingTextStream(["name,age\n", "Alice,30\n", "Bob,25\n"])

        frame = ar.read_csv(stream)
        df = ar.to_pandas(frame)

        assert df["name"].tolist() == ["Alice", "Bob"]
        assert stream.read_sizes
        assert -1 not in stream.read_sizes

    def test_read_csv_chunked_file_like_input_is_copied_in_bounded_chunks(self):
        stream = ChunkTrackingTextStream(["name,age\nAlice,30\n", "Bob,25\n"])

        chunks = list(ar.read_csv_chunked(stream, chunksize=1))

        assert [ar.to_pandas(chunk)["name"].iloc[0] for chunk in chunks] == [
            "Alice",
            "Bob",
        ]
        assert stream.read_sizes
        assert -1 not in stream.read_sizes

    def test_read_csv_chunked_utf8_path_skips_python_nul_prescan(
        self, tmp_path, monkeypatch
    ):
        csv_path = tmp_path / "streaming.csv"
        csv_path.write_text("name,age\nAlice,30\nBob,25\n", encoding="utf-8")
        real_open = builtins.open

        def blocked_binary_open(*args, **kwargs):
            mode = args[1] if len(args) > 1 else kwargs.get("mode", "r")
            if Path(args[0]) == csv_path and mode == "rb":
                raise AssertionError(
                    "read_csv_chunked should not pre-scan the whole UTF-8 file"
                )
            return real_open(*args, **kwargs)

        monkeypatch.setattr(builtins, "open", blocked_binary_open)

        chunks = ar.read_csv_chunked(str(csv_path), chunksize=1)
        first = next(chunks)

        assert ar.to_pandas(first)["name"].tolist() == ["Alice"]

    def test_read_csv_chunked_late_nul_rejected_by_streaming_reader(self, tmp_path):
        csv_path = tmp_path / "late-nul.csv"
        csv_path.write_bytes(b"name,age\nAlice,30\n\0binary,99\n")

        chunks = ar.read_csv_chunked(csv_path, chunksize=1)
        first = next(chunks)

        assert ar.to_pandas(first)["name"].tolist() == ["Alice"]
        with pytest.raises(
            ar.CsvReadError,
            match="CSV input contains NUL bytes and appears to be binary or corrupted",
        ):
            next(chunks)

    def test_file_like_input_rejects_bytes(self):
        with pytest.raises(TypeError, match="file-like objects must return text"):
            ar.read_csv(io.BytesIO(b"name,age\nAlice,30\n"))

    def test_read_csv_encoding_errors_strict(self, tmp_path):
        csv_file = tmp_path / "invalid_utf8.csv"

        csv_file.write_bytes(b"name\nabc\xffdef\n")

        with pytest.raises(ar.CsvReadError):
            ar.read_csv(
                csv_file,
                encoding="utf-8",
                encoding_errors="strict",
            )

    def test_read_csv_encoding_errors_replace(self, tmp_path):
        csv_file = tmp_path / "invalid_utf8.csv"

        csv_file.write_bytes(b"name\nabc\xffdef\n")

        frame = ar.read_csv(
            csv_file,
            encoding="utf-8",
            encoding_errors="replace",
        )

        value = frame["name"][0]

        assert value == "abc�def"
        assert "def" in value

    def test_read_csv_encoding_errors_ignore(self, tmp_path):
        csv_file = tmp_path / "invalid_utf8.csv"

        csv_file.write_bytes(b"name\nabc\xffdef\n")

        frame = ar.read_csv(
            csv_file,
            encoding="utf-8",
            encoding_errors="ignore",
        )

        value = frame["name"][0]

        assert value == "abcdef"

    def test_read_csv_invalid_encoding_errors_mode(self, tmp_path):
        csv_file = tmp_path / "data.csv"

        csv_file.write_text(
            "name\nalice\n",
            encoding="utf-8",
        )

        with pytest.raises(ValueError):
            ar.read_csv(
                csv_file,
                encoding_errors="bad-mode",
            )

    def test_scan_csv_encoding_errors_strict(self, tmp_path):
        csv_file = tmp_path / "invalid_utf8.csv"

        csv_file.write_bytes(b"name\nabc\xffdef\n")

        with pytest.raises(ar.CsvReadError):
            ar.scan_csv(
                csv_file,
                encoding="utf-8",
                encoding_errors="strict",
            )

    def test_scan_csv_encoding_errors_replace(self, tmp_path):
        csv_file = tmp_path / "invalid_utf8.csv"

        csv_file.write_bytes(b"name\nabc\xffdef\n")

        schema = ar.scan_csv(
            csv_file,
            encoding="utf-8",
            encoding_errors="replace",
        )

        assert schema["name"] == "string"

    def test_scan_csv_encoding_errors_ignore(self, tmp_path):
        csv_file = tmp_path / "invalid_utf8.csv"

        csv_file.write_bytes(b"name\nabc\xffdef\n")

        schema = ar.scan_csv(
            csv_file,
            encoding="utf-8",
            encoding_errors="ignore",
        )

        assert schema["name"] == "string"

    def test_non_utf8_encoding(self, tmp_path):
        csv_path = tmp_path / "latin.csv"
        csv_path.write_bytes("name\nAndré\n".encode("latin-1"))

        frame = ar.read_csv(csv_path, encoding="latin-1")
        df = ar.to_pandas(frame)

        assert df["name"].iloc[0] == "André"

    def test_utf16_encoding_with_nul_bytes_reads_successfully(self, tmp_path):
        csv_path = tmp_path / "utf16.csv"
        csv_path.write_text("name,age\nAlice,30\n", encoding="utf-16")

        frame = ar.read_csv(csv_path, encoding="utf-16")
        df = ar.to_pandas(frame)

        assert frame.columns == ["name", "age"]
        assert frame.shape == (1, 2)
        assert df["name"].iloc[0] == "Alice"
        assert df["age"].iloc[0] == 30

    def test_quoted_newline_record(self, tmp_path):
        csv_path = tmp_path / "quoted_newline.csv"
        csv_path.write_bytes(b'id,text\n1,"hello\nworld"\n2,ok\n')

        frame = ar.read_csv(csv_path)
        df = ar.to_pandas(frame)

        assert frame.shape == (2, 2)
        assert df["text"].iloc[0] == "hello\nworld"
        assert df["text"].iloc[1] == "ok"

    def test_unterminated_quote_rejected(self, tmp_path):
        csv_path = tmp_path / "unterminated.csv"
        csv_path.write_text('id,text\n1,"hello\n')

        with pytest.raises(
            ar.CsvReadError, match="Unterminated quoted field starting at line 2"
        ):
            ar.read_csv(csv_path)

    def test_comment_lines_are_skipped(self, tmp_path):
        csv_path = tmp_path / "comments.csv"
        csv_path.write_text(
            "# file generated by export\n"
            "name,note\n"
            "Alice,active\n"
            "  # comment with leading whitespace\n"
            "Bob,finished\n"
        )

        frame = ar.read_csv(csv_path, comment="#")
        df = ar.to_pandas(frame)

        assert frame.shape == (2, 2)
        assert df["name"].tolist() == ["Alice", "Bob"]
        assert ar.scan_csv(csv_path, comment="#") == {"name": "string", "note": "string"}

    def test_comment_character_inside_quotes_is_data(self, tmp_path):
        csv_path = tmp_path / "quoted_comment.csv"
        csv_path.write_text('name,note\nAlice,"# not a comment"\nBob,ok\n')

        frame = ar.read_csv(csv_path, comment="#")
        df = ar.to_pandas(frame)

        assert frame.shape == (2, 2)
        assert df["note"].tolist() == ["# not a comment", "ok"]

    def test_default_keeps_comment_like_lines(self, tmp_path):
        csv_path = tmp_path / "default_comments.csv"
        csv_path.write_text("name,note\n#not,a comment\nAlice,ok\n")

        frame = ar.read_csv(csv_path)
        df = ar.to_pandas(frame)

        assert frame.shape == (2, 2)
        assert df["name"].tolist() == ["#not", "Alice"]

    def test_duplicate_headers_rejected(self, tmp_path):
        csv_path = tmp_path / "duplicate_headers.csv"
        csv_path.write_text("a,a\n1,2\n")

        with pytest.raises(ar.CsvReadError, match="Duplicate column name: a") as exc:
            ar.read_csv(csv_path)

    def test_empty_file_raises(self, tmp_path):
        csv_path = tmp_path / "empty.csv"
        csv_path.write_text("")
        with pytest.raises(ar.CsvReadError, match="CSV file is empty"):
            ar.read_csv(str(csv_path))

    def test_missing_file_passthrough(self, tmp_path):
        with pytest.raises(ar.CsvReadError):
            ar.read_csv(str(tmp_path / "nonexistent.csv"))


class TestScanCsv:
    def test_scan_schema(self, sample_csv):
        schema = ar.scan_csv(sample_csv)
        assert isinstance(schema, dict)
        assert "name" in schema
        assert "age" in schema
        assert schema["age"] == "int64"

    def test_scan_non_utf8_encoding(self, tmp_path):
        csv_path = tmp_path / "latin.csv"
        csv_path.write_bytes("name\nAndré\n".encode("latin-1"))

        schema = ar.scan_csv(csv_path, encoding="latin-1")

        assert schema == {"name": "string"}

    def test_scan_utf16_encoding_with_nul_bytes_reads_successfully(self, tmp_path):
        csv_path = tmp_path / "utf16.csv"
        csv_path.write_text("name,age\nAlice,30\n", encoding="utf-16")

        schema = ar.scan_csv(csv_path, encoding="utf-16")

        assert schema == {"name": "string", "age": "int64"}

    def test_scan_binary_file_rejection(self, tmp_path):
        file_path = str(tmp_path / "data.csv")

        with open(file_path, "wb") as f:
            f.write(b"col1,col2\n\0binary\0,data\n")

        with pytest.raises(
            ar.CsvReadError,
            match="CSV input contains NUL bytes and appears to be binary or corrupted",
        ):
            ar.scan_csv(file_path)

    def test_scan_late_binary_file_outside_sample(self, tmp_path):
        file_path = str(tmp_path / "data.csv")

        with open(file_path, "wb") as f:
            f.write(b"col1,col2\n")
            f.write(b"a,b\n" * 400)
            f.write(b"\0binary,data\n")

        with pytest.raises(
            ar.CsvReadError,
            match="CSV input contains NUL bytes and appears to be binary or corrupted",
        ):
            ar.scan_csv(file_path)

    def test_scan_late_binary_file_rejection_with_larger_sample(self, tmp_path):
        file_path = str(tmp_path / "data.csv")

        with open(file_path, "wb") as f:
            f.write(b"col1,col2\n")
            f.write(b"a,b\n" * 400)
            f.write(b"\0binary,data\n")

        with pytest.raises(
            ar.CsvReadError,
            match="CSV input contains NUL bytes and appears to be binary or corrupted",
        ):
            ar.scan_csv(file_path)

        with pytest.raises(
            ar.CsvReadError,
            match="CSV input contains NUL bytes and appears to be binary or corrupted",
        ):
            ar.scan_csv(file_path, sample_size=500)

    def test_scan_sample_size(self, tmp_path):
        csv_path = tmp_path / "sample.csv"
        csv_path.write_text("id,value\n1,10\n2,20\n3,30\n4,hello\n")

        schema_early = ar.scan_csv(csv_path, sample_size=2)
        assert schema_early["value"] == "int64"

        schema_full = ar.scan_csv(csv_path, sample_size=10)
        assert schema_full["value"] == "string"

    def test_scan_sample_size_invalid(self, sample_csv):

        with pytest.raises(ValueError, match="sample_size must be a positive integer"):
            ar.scan_csv(sample_csv, sample_size=0)

        with pytest.raises(ValueError, match="sample_size must be a positive integer"):
            ar.scan_csv(sample_csv, sample_size=-5)

    def test_scan_sample_size_none_preserves_default(self, tmp_path):
        csv_path = tmp_path / "sample_default.csv"
        csv_path.write_text("id,val\n1,a\n2,b\n3,c\n")

        res_implicit = ar.scan_csv(csv_path)
        res_explicit = ar.scan_csv(csv_path, sample_size=None)

        assert res_implicit == res_explicit

    def test_scan_sample_size_invalid_types(self, sample_csv):
        with pytest.raises(TypeError):
            ar.scan_csv(sample_csv, sample_size=True)

        with pytest.raises(TypeError):
            ar.scan_csv(sample_csv, sample_size=1.5)

        with pytest.raises(TypeError):
            ar.scan_csv(sample_csv, sample_size="100")

    def test_non_utf8_sampling_respects_requested_record_count(self, tmp_path):
        csv_path = tmp_path / "latin1.csv"
        csv_path.write_text("name\nAndré\nBeyoncé\n", encoding="latin-1")

        with _utf8_csv_path(str(csv_path), "latin-1", sample_rows=2) as native_path:
            assert Path(native_path).read_text(encoding="utf-8") == "name\nAndré\n"

    def test_scan_invalid_delimiter(self, tmp_path):
        csv_path = tmp_path / "test.csv"
        csv_path.write_text("a,b\n1,2\n")

        with pytest.raises(ValueError, match="delimiter must be exactly one character"):
            ar.scan_csv(csv_path, delimiter="::")

        with pytest.raises(ValueError, match="delimiter must be exactly one character"):
            ar.scan_csv(csv_path, delimiter="")

        with pytest.raises(TypeError, match="delimiter must be a string"):
            ar.scan_csv(csv_path, delimiter=1)

    def test_scan_empty_file_raises(self, tmp_path):
        csv_path = tmp_path / "empty.csv"
        csv_path.write_text("")
        with pytest.raises(ar.CsvReadError, match="CSV file is empty"):
            ar.scan_csv(str(csv_path))

    def test_scan_missing_file_passthrough(self, tmp_path):
        with pytest.raises(ar.CsvReadError):
            ar.scan_csv(str(tmp_path / "nonexistent.csv"))

    def test_scan_null_values_invalid_type(self):
        with pytest.raises(
            TypeError, match="must be a list of strings, not a bare string"
        ):
            ar.scan_csv("dummy.csv", null_values="NA")
        with pytest.raises(TypeError, match="must be a list of strings"):
            ar.scan_csv("dummy.csv", null_values=("NA",))
        with pytest.raises(TypeError, match="must contain only strings"):
            ar.scan_csv("dummy.csv", null_values=[1])

    def test_scan_schema_preserves_column_order(self, tmp_path):
        csv_path = tmp_path / "order_test.csv"
        csv_path.write_text("z,a,m\n1,2,3\n")

        schema = ar.scan_csv(str(csv_path))
        frame = ar.read_csv(str(csv_path))

        assert list(schema.keys()) == ["z", "a", "m"]
        assert list(frame.columns) == ["z", "a", "m"]

    def test_scan_schema_order_matches_read_csv(self, sample_csv):
        schema = ar.scan_csv(sample_csv)
        frame = ar.read_csv(sample_csv)

        assert list(schema.keys()) == list(frame.columns)

    def test_scan_csv_headers_only_no_data(self, tmp_path):
        csv_path = tmp_path / "headers_only.csv"
        csv_path.write_text("name,age,score\n")

        schema = ar.scan_csv(str(csv_path))
        assert set(schema.keys()) == {"name", "age", "score"}
        assert all(v == "string" for v in schema.values())

    def test_scan_csv_all_null_column(self, tmp_path):
        csv_path = tmp_path / "all_null.csv"
        csv_path.write_text("id,value,comment\n1,,\n2,,\n3,,\n")

        schema = ar.scan_csv(str(csv_path))
        assert schema["id"] == "int64"
        assert schema["value"] == "string"
        assert schema["comment"] == "string"

    def test_scan_csv_mixed_types_infers_string(self, tmp_path):
        csv_path = tmp_path / "mixed_types.csv"
        csv_path.write_text("id,value\n1,100\n2,hello\n3,200\n")

        schema = ar.scan_csv(str(csv_path))
        assert schema["id"] == "int64"
        assert schema["value"] == "string"

    def test_scan_csv_sample_size_affects_type_inference(self, tmp_path):
        csv_path = tmp_path / "sample_type.csv"
        csv_path.write_text("id,value\n1,10\n2,20\n3,30\n4,hello\n")

        schema_early = ar.scan_csv(str(csv_path), sample_size=2)
        assert schema_early["value"] == "int64"

        schema_full = ar.scan_csv(str(csv_path), sample_size=10)
        assert schema_full["value"] == "string"

    def test_scan_csv_single_row(self, tmp_path):
        csv_path = tmp_path / "single_row.csv"
        csv_path.write_text("id,name,active,score\n1,Alice,true,95.5\n")

        schema = ar.scan_csv(str(csv_path))
        assert schema["id"] == "int64"
        assert schema["name"] == "string"
        assert schema["active"] == "bool"
        assert schema["score"] == "float64"

    def test_scan_csv_single_column(self, tmp_path):
        csv_path = tmp_path / "single_column.csv"
        csv_path.write_text("id\n1\n2\n3\n")

        schema = ar.scan_csv(str(csv_path))
        assert len(schema) == 1
        assert schema["id"] == "int64"
    def test_scan_csv_rejects_inconsistent_row_width(self, tmp_path):
        csv_path = tmp_path / "bad_scan.csv"
        csv_path.write_text("a,b\n1,2,3\n")

        with pytest.raises(ar.CsvReadError, match="CSV row 2 has 3 fields; expected 2"):
            ar.scan_csv(csv_path)

    def test_scan_csv_large_integer_overflow_remains_string(self, tmp_path):
        csv_path = tmp_path / "large_integer_scan.csv"
        csv_path.write_text("value\n9223372036854775808\n")

        assert ar.scan_csv(csv_path) == {"value": "string"}

    def test_scan_csv_has_header_false_generates_synthetic_columns(self, tmp_path):
        csv_content = "1,Alice\n2,Bob\n"

        csv_file = tmp_path / "headerless.csv"
        csv_file.write_text(csv_content)

        schema = ar.scan_csv(csv_file, has_header=False)

        assert schema == {
            "col_0": "int64",
            "col_1": "string",
        }

    def test_scan_csv_default_has_header_behavior(self, tmp_path):
        csv_content = "id,name\n1,Alice\n"

        csv_file = tmp_path / "with_header.csv"
        csv_file.write_text(csv_content)

        schema = ar.scan_csv(csv_file)

        assert schema == {
            "id": "int64",
            "name": "string",
        }

    def test_scan_csv_has_header_false_matches_read_csv(self, tmp_path):
        csv_content = "1,Alice\n2,Bob\n"

        csv_file = tmp_path / "headerless_match.csv"
        csv_file.write_text(csv_content)

        frame = ar.read_csv(csv_file, has_header=False)
        schema = ar.scan_csv(csv_file, has_header=False)

        assert list(frame.columns) == list(schema.keys())

    def test_read_csv_encoding_errors_preserve_valid_utf8(
        self,
        tmp_path,
    ):
        csv_file = tmp_path / "mixed_utf8.csv"

        csv_file.write_bytes(b"name\ncaf\xc3\xa9\xff\n")

        frame = ar.read_csv(
            csv_file,
            encoding="utf-8",
            encoding_errors="replace",
        )

        value = frame["name"][0]

        assert value == "café�"

    def test_read_csv_encoding_errors_ignore_preserves_numeric_inference(
        self, tmp_path
    ):
        csv_file = tmp_path / "numeric_ignore.csv"

        csv_file.write_bytes(b"value\n1\xff\n2\n")

        frame = ar.read_csv(
            csv_file,
            encoding="utf-8",
            encoding_errors="ignore",
        )

        values = frame["value"]

        assert values == [1, 2]

    def test_read_csv_encoding_errors_rejects_overlong_utf8(self, tmp_path):
        csv_file = tmp_path / "overlong.csv"

        csv_file.write_bytes(b"name\n\xc0\xaf\n")

        with pytest.raises(ar.CsvReadError):
            ar.read_csv(csv_file, encoding="utf-8", encoding_errors="strict")

    def test_scan_csv_returns_metadata(self, tmp_path):
        csv_path = tmp_path / "metadata.csv"
        csv_path.write_text("id,name\n1,Alice\n2,Bob\n")

        result = ar.scan_csv(csv_path, return_metadata=True)

        assert "schema" in result
        assert "metadata" in result

        assert result["schema"] == {
            "id": "int64",
            "name": "string",
        }

        metadata = result["metadata"]

        assert metadata["delimiter"] == ","
        assert metadata["encoding"] == "utf-8"
        assert metadata["sampled_rows"] == 2

    def test_scan_csv_sample_metadata_counts_requested_rows_with_header(self, tmp_path):
        csv_path = tmp_path / "sample_metadata_header.csv"
        rows = ["id,name"] + [f"{i},row{i}" for i in range(700)]
        csv_path.write_text("\n".join(rows) + "\n")

        result = ar.scan_csv(
            csv_path,
            sample_size=500,
            return_metadata=True,
        )

        assert result["metadata"]["sampled_rows"] == 500
        assert result["schema"] == {
            "id": "int64",
            "name": "string",
        }

    def test_scan_csv_returns_custom_metadata_values(self, tmp_path):
        csv_path = tmp_path / "custom_metadata.csv"
        csv_path.write_text("id;value\n1;100\n2;200\n")

        result = ar.scan_csv(
            csv_path,
            delimiter=";",
            encoding="utf-8",
            sample_size=50,
            return_metadata=True,
        )

        metadata = result["metadata"]

        assert metadata["delimiter"] == ";"
        assert metadata["encoding"] == "utf-8"
        assert metadata["sampled_rows"] == 2

    def test_scan_csv_metadata_reports_actual_sampled_rows(self, tmp_path):
        csv_path = tmp_path / "actual_rows.csv"
        csv_path.write_text("id,name\n1,Alice\n2,Bob\n")

        result = ar.scan_csv(
            csv_path,
            sample_size=100,
            return_metadata=True,
        )

        metadata = result["metadata"]

        assert metadata["sampled_rows"] == 2


# --- Issue #115: quoted multiline round-trip across line endings ---


def test_quoted_field_with_embedded_lf(tmp_path):
    """LF inside quotes must be preserved as field content."""
    csv_file = tmp_path / "test.csv"
    csv_file.write_bytes(b'name,note\nAlice,"line1\nline2"\n')
    df = ar.to_pandas(ar.read_csv(str(csv_file)))
    assert len(df) == 1
    assert df["note"][0] == "line1\nline2"


def test_quoted_field_with_embedded_crlf(tmp_path):
    """CRLF inside quotes must be preserved, not treated as row delimiter."""
    csv_file = tmp_path / "test.csv"
    csv_file.write_bytes(b'name,note\r\nAlice,"line1\r\nline2"\r\n')
    df = ar.to_pandas(ar.read_csv(str(csv_file)))
    assert len(df) == 1
    assert df["note"][0] == "line1\r\nline2"


def test_crlf_line_endings_do_not_preserve_trailing_carriage_return(tmp_path):
    csv_path = tmp_path / "normal_crlf.csv"

    csv_path.write_bytes(b"id,name\r\n1,Alice\r\n2,Bob\r\n")

    frame = ar.read_csv(csv_path)

    df = ar.to_pandas(frame)

    assert df["name"].iloc[0] == "Alice"
    assert df["name"].iloc[1] == "Bob"


def test_embedded_quoted_crlf_is_preserved(tmp_path):
    csv_path = tmp_path / "embedded_crlf.csv"

    csv_path.write_bytes(b'id,notes\r\n1,"hello\r\nworld"\r\n')

    frame = ar.read_csv(csv_path)

    df = ar.to_pandas(frame)

    assert df["notes"].iloc[0] == "hello\r\nworld"


def test_quoted_field_with_embedded_cr(tmp_path):
    """CR-only inside quotes must be preserved as field content."""
    csv_file = tmp_path / "test.csv"
    csv_file.write_bytes(b'name,note\nAlice,"line1\rline2"\n')
    df = ar.to_pandas(ar.read_csv(str(csv_file)))
    assert len(df) == 1
    assert df["note"][0] == "line1\rline2"


class TestArFrameHeadTail:
    def test_head_default(self, sample_csv):
        frame = ar.read_csv(sample_csv)
        result = frame.head()
        assert isinstance(result, ar.ArFrame)
        assert result.shape == (3, 4)

    def test_head_custom_n(self, sample_csv):
        frame = ar.read_csv(sample_csv)
        result = frame.head(2)
        df = ar.to_pandas(result)
        assert result.shape == (2, 4)
        assert df["name"].tolist() == ["Alice", "Bob"]

    def test_head_zero(self, sample_csv):
        frame = ar.read_csv(sample_csv)
        result = frame.head(0)
        assert isinstance(result, ar.ArFrame)
        assert result.shape == (0, 4)

    def test_head_large_n(self, sample_csv):
        frame = ar.read_csv(sample_csv)
        result = frame.head(100)
        assert result.shape == (3, 4)

    def test_head_empty_frame(self, tmp_path):
        csv_path = tmp_path / "empty_rows.csv"
        csv_path.write_text("name,age\n")
        frame = ar.read_csv(csv_path)
        result = frame.head()
        assert result.shape == (0, 2)

    def test_tail_default(self, sample_csv):
        frame = ar.read_csv(sample_csv)
        result = frame.tail()
        assert isinstance(result, ar.ArFrame)
        assert result.shape == (3, 4)

    def test_tail_custom_n(self, sample_csv):
        frame = ar.read_csv(sample_csv)
        result = frame.tail(2)
        df = ar.to_pandas(result)
        assert result.shape == (2, 4)
        assert df["name"].tolist() == ["Bob", "Charlie"]

    def test_tail_zero(self, sample_csv):
        frame = ar.read_csv(sample_csv)
        result = frame.tail(0)
        assert isinstance(result, ar.ArFrame)
        assert result.shape == (0, 4)

    def test_tail_large_n(self, sample_csv):
        frame = ar.read_csv(sample_csv)
        result = frame.tail(100)
        assert result.shape == (3, 4)

    def test_tail_empty_frame(self, tmp_path):
        csv_path = tmp_path / "empty_rows.csv"
        csv_path.write_text("name,age\n")
        frame = ar.read_csv(csv_path)
        result = frame.tail()
        assert result.shape == (0, 2)

    def test_head_invalid_n(self, sample_csv):
        frame = ar.read_csv(sample_csv)
        with pytest.raises(ValueError):
            frame.head(-1)
        with pytest.raises(ValueError):
            frame.head(True)

    def test_tail_invalid_n(self, sample_csv):
        frame = ar.read_csv(sample_csv)
        with pytest.raises(ValueError):
            frame.tail(-1)
        with pytest.raises(ValueError):
            frame.tail(True)


def test_row_split_crlf_outside_quotes(tmp_path):
    """CRLF outside quotes must correctly split into separate rows."""
    csv_file = tmp_path / "test.csv"
    csv_file.write_bytes(b"a,b\r\n1,2\r\n3,4\r\n")
    df = ar.to_pandas(ar.read_csv(str(csv_file)))
    assert len(df) == 2
    assert list(df["a"]) == [1, 3]


def test_scan_csv_non_utf8_multiline_boundary(tmp_path):
    """scan_csv must not split a quoted multiline record at the sample boundary."""
    csv_file = tmp_path / "test_multiline_boundary.csv"
    content_lines = ["id,text"]
    for i in range(1, 9999):
        content_lines.append(f"{i},value")
    content_lines.append('9999,"multiline\nrecord\ncafé"')
    content_lines.append("10000,end")
    csv_content = "\n".join(content_lines)
    csv_file.write_bytes(csv_content.encode("latin-1"))
    schema = ar.scan_csv(str(csv_file), encoding="latin-1")
    assert schema == {"id": "int64", "text": "string"}


def test_scan_csv_type_evidence_after_limit(tmp_path):
    """Type evidence after sample window must not affect inference."""
    csv_file = tmp_path / "test_type_evidence.csv"
    content_lines = ["id,value"]
    for i in range(1, 10005):
        content_lines.append(f"{i},100")
    content_lines.append("10006,3.14")
    csv_content = "\n".join(content_lines)
    csv_file.write_bytes(csv_content.encode("latin-1"))
    schema = ar.scan_csv(str(csv_file), encoding="latin-1")
    assert schema["value"] == "int64"


def test_csv_scan_then_clean_cast_fails_on_late_string(self, tmp_path):
    csv_path = tmp_path / "late_string.csv"
    csv_path.write_text("id,value\n" "1,10\n" "2,20\n" "3,30\n" "4,not_a_number\n")

    schema = ar.scan_csv(str(csv_path), sample_size=3)
    assert schema["value"] == "int64"

    frame = ar.read_csv(str(csv_path))

    with pytest.raises(ar.TypeCastError):
        ar.clean(frame, cast_mapping=schema)


def test_csv_scan_then_clean_cast_succeeds_with_full_sample(self, tmp_path):
    csv_path = tmp_path / "full_sample.csv"
    csv_path.write_text("id,value\n" "1,10\n" "2,20\n" "3,30\n" "4,not_a_number\n")

    schema = ar.scan_csv(str(csv_path), sample_size=None)
    assert schema["value"] == "string"

    frame = ar.read_csv(str(csv_path))
    result = ar.clean(frame, cast_mapping=schema)

    assert result.dtypes["value"] == "string"
def test_strict_mode_rejects_missing_columns(tmp_path):
    csv_path = tmp_path / "strict_missing.csv"
    csv_path.write_text("id,name\n1,Alice\n2\n")

    with pytest.raises(
        ar.CsvReadError,
        match="expected 2",
    ):
        ar.read_csv(csv_path, mode="strict")


def test_read_csv_supports_stringio():
    buffer = io.StringIO("id,name\n1,Alice\n2,Bob\n")

    frame = ar.read_csv(buffer)

    df = ar.to_pandas(frame)

    assert list(df["name"]) == ["Alice", "Bob"]


def test_read_csv_rejects_binary_buffer():
    buffer = io.BytesIO(b"id,name\n1,Alice\n")

    with pytest.raises(
        TypeError,
        match="must return text",
    ):
        ar.read_csv(buffer)


def test_read_csv_path_behavior_unchanged(tmp_path):
    csv_path = tmp_path / "data.csv"
    csv_path.write_text("id,name\n1,Alice\n")

    frame = ar.read_csv(csv_path)

    df = ar.to_pandas(frame)

    assert list(df["name"]) == ["Alice"]


def test_permissive_mode_allows_missing_columns(tmp_path):
    csv_path = tmp_path / "permissive_missing.csv"
    csv_path.write_text("id,name\n1,Alice\n2\n")
    frame = ar.read_csv(csv_path, mode="permissive")
    assert frame.shape == (2, 2)

    df = ar.to_pandas(frame)

    assert df["id"].iloc[0] == 1
    assert df["name"].iloc[0] == "Alice"
    assert pd.isna(df["name"].iloc[1])


def test_invalid_parser_mode(tmp_path):
    csv_path = tmp_path / "invalid_mode.csv"
    csv_path.write_text("id,name\n1,Alice\n")

    with pytest.raises(
        ValueError,
        match="mode must be either",
    ):
        ar.read_csv(csv_path, mode="fast")


def test_default_mode_preserves_strict_behavior(tmp_path):
    csv_path = tmp_path / "default_mode.csv"
    csv_path.write_text("id,name\n1,Alice\n2\n")

    with pytest.raises(
        ar.CsvReadError,
        match="expected 2",
    ):
        ar.read_csv(csv_path)


class TestSniffDelimiter:
    def test_sniff_comma(self, tmp_path):
        csv_path = tmp_path / "comma.csv"
        csv_path.write_text("id,name,age\n1,Alice,30\n2,Bob,25\n")
        assert ar.sniff_delimiter(csv_path) == ","

    def test_sniff_semicolon(self, tmp_path):
        csv_path = tmp_path / "semicolon.csv"
        csv_path.write_text("id;name;age\n1;Alice;30\n2;Bob;25\n")
        assert ar.sniff_delimiter(csv_path) == ";"

    def test_sniff_tab(self, tmp_path):
        csv_path = tmp_path / "tab.tsv"
        csv_path.write_text("id\tname\tage\n1\tAlice\t30\n2\tBob\t25\n")
        assert ar.sniff_delimiter(csv_path) == "\t"

    def test_sniff_pipe(self, tmp_path):
        csv_path = tmp_path / "pipe.txt"
        csv_path.write_text("id|name|age\n1|Alice|30\n2|Bob|25\n")
        assert ar.sniff_delimiter(csv_path) == "|"

    def test_sniff_quoted_delimiters(self, tmp_path):
        csv_path = tmp_path / "quoted.csv"
        csv_path.write_text(
            'id;name;notes\n1;Alice;"likes commas, tabs\tand pipes|"\n2;Bob;"no special characters"\n'
        )
        # Semicolon is the true delimiter, commas/tabs/pipes are only inside quotes
        assert ar.sniff_delimiter(csv_path) == ";"

    def test_sniff_empty_file_raises(self, tmp_path):
        csv_path = tmp_path / "empty.csv"
        csv_path.write_text("")
        with pytest.raises(ar.CsvReadError, match="CSV file is empty"):
            ar.sniff_delimiter(csv_path)

    def test_sniff_ambiguous_no_delimiter_raises(self, tmp_path):
        csv_path = tmp_path / "single_column.csv"
        csv_path.write_text("only_column_name\nval1\nval2\n")
        with pytest.raises(ValueError, match="Could not determine CSV delimiter"):
            ar.sniff_delimiter(csv_path)

    def test_sniff_binary_file_raises(self, tmp_path):
        csv_path = tmp_path / "binary.csv"
        with open(csv_path, "wb") as f:
            f.write(b"col1,col2\n\0binary\0,data\n")
        with pytest.raises(
            ar.CsvReadError,
            match="CSV input contains NUL bytes and appears to be binary or corrupted",
        ):
            ar.sniff_delimiter(csv_path)

    def test_sniff_invalid_types(self, tmp_path):
        csv_path = tmp_path / "dummy.csv"
        csv_path.write_text("a,b\n1,2\n")

        with pytest.raises(TypeError, match="encoding must be a string"):
            ar.sniff_delimiter(csv_path, encoding=123)

        with pytest.raises(TypeError, match="sample_size must be an integer"):
            ar.sniff_delimiter(csv_path, sample_size=True)

        with pytest.raises(TypeError, match="sample_size must be an integer"):
            ar.sniff_delimiter(csv_path, sample_size="100")

        with pytest.raises(ValueError, match="sample_size must be a positive integer"):
            ar.sniff_delimiter(csv_path, sample_size=0)

        with pytest.raises(ValueError, match="sample_size must be a positive integer"):
            ar.sniff_delimiter(csv_path, sample_size=-5)

    def test_sniff_missing_file_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            ar.sniff_delimiter(tmp_path / "nonexistent.csv")

    def test_sniff_tie_ambiguity_raises(self, tmp_path):
        csv_path = tmp_path / "tie.csv"
        # Each line has exactly one comma and one semicolon, producing identical frequencies and consistency scores
        csv_path.write_text("a,b;c\n1,2;3\n4,5;6\n")
        with pytest.raises(
            ValueError,
            match="Could not determine CSV delimiter from sample: multiple candidate delimiters",
        ):
            ar.sniff_delimiter(csv_path)
