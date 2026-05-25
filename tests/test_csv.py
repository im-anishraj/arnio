"""Tests for CSV reading functionality."""

import builtins
import io
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

    def test_read_csv_dtype_parse_failure_becomes_null(self, tmp_path):
        path = tmp_path / "parse_failure.csv"
        path.write_text("quantity\nabc\n")

        frame = ar.read_csv(
            path,
            dtype={"quantity": "int64"},
        )

        pdf = ar.to_pandas(frame)

        assert frame.dtypes["quantity"] == "int64"
        assert pdf["quantity"].isna().tolist() == [True]

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

    def test_contains_operator(self, sample_csv):
        frame = ar.read_csv(sample_csv)

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

    def test_tsv_delimiter(self, tmp_path):
        csv_path = tmp_path / "data.tsv"
        csv_path.write_text("name\tage\tcity\nAlice\t30\tNYC\nBob\t25\tLA\n")
        frame = ar.read_csv(str(csv_path))
        assert frame.shape == (2, 3)
        assert frame.columns == ["name", "age", "city"]

    def test_custom_delimiter(self, tmp_path):
        csv_path = tmp_path / "data.csv"
        csv_path.write_text("name|age|city\nAlice|30|NYC\nBob|25|LA\n")
        frame = ar.read_csv(str(csv_path), delimiter="|")
        assert frame.shape == (2, 3)
        assert list(ar.to_pandas(frame)["name"]) == ["Alice", "Bob"]

    def test_duplicate_headers_rejected(self, tmp_path):
        csv_path = tmp_path / "duplicate_headers.csv"
        csv_path.write_text("a,a\n1,2\n")

        with pytest.raises(ar.CsvReadError, match="Duplicate column name: a"):
            ar.read_csv(csv_path)

    def test_empty_file_raises(self, tmp_path):
        csv_path = tmp_path / "empty.csv"
        csv_path.write_text("")
        with pytest.raises(ar.CsvReadError, match="CSV file is empty"):
            ar.read_csv(str(csv_path))

    def test_missing_file_passthrough(self, tmp_path):
        with pytest.raises(ar.CsvReadError):
            ar.read_csv(str(tmp_path / "nonexistent.csv"))

    def test_read_csv_permission_error_includes_path_and_os_reason(
        self, tmp_path, monkeypatch
    ):
        csv_path = tmp_path / "permission.csv"
        csv_path.write_text("a,b\n1,2\n")
        csv_path_str = str(csv_path)
        real_open = builtins.open

        def blocked_open(*args, **kwargs):
            if args[0] == csv_path_str and args[1] == "rb":
                raise PermissionError(13, "Access is denied")
            return real_open(*args, **kwargs)

        monkeypatch.setattr(builtins, "open", blocked_open)

        with pytest.raises(
            CsvReadError,
            match="Could not access CSV file .+: Access is denied",
        ) as exc_info:
            ar.read_csv(csv_path)
        assert repr(str(csv_path)) in str(exc_info.value)

    def test_read_csv_non_utf8_permission_error_includes_path_and_os_reason(
        self, tmp_path, monkeypatch
    ):
        csv_path = tmp_path / "permission-latin1.csv"
        csv_path.write_bytes("name\nAndr\xe9\n".encode("latin-1"))
        csv_path_str = str(csv_path)
        real_open = builtins.open

        def blocked_open(*args, **kwargs):
            if args[0] == csv_path_str and kwargs.get("encoding") == "latin-1":
                raise PermissionError(13, "Access is denied")
            return real_open(*args, **kwargs)

        monkeypatch.setattr(builtins, "open", blocked_open)

        with pytest.raises(
            CsvReadError,
            match="Could not access CSV file .+: Access is denied",
        ) as exc_info:
            ar.read_csv(csv_path, encoding="latin-1")
        assert repr(str(csv_path)) in str(exc_info.value)

    def test_null_values_default_preserves_empty_only_behavior(self, tmp_path):
        csv_path = tmp_path / "default_nulls.csv"
        csv_path.write_text("a,b\n,1\nNA,2\n")
        frame = ar.read_csv(csv_path)
        df = ar.to_pandas(frame)
        assert pd.isna(df.loc[0, "a"])
        assert df.loc[1, "a"] == "NA"
        assert frame.dtypes["a"] == "string"

    def test_null_values_custom_is_case_insensitive(self, tmp_path):
        csv_path = tmp_path / "case_nulls.csv"
        csv_path.write_text("a\nNa\nnA\nna\n")
        frame = ar.read_csv(csv_path, null_values=["NA"])
        df = ar.to_pandas(frame)
        assert df["a"].isna().sum() == 3

    def test_null_values_custom_preserves_type_inference(self, tmp_path):
        csv_path = tmp_path / "type_infer.csv"
        csv_path.write_text("a\n1\nNA\n3\n")
        frame = ar.read_csv(csv_path, null_values=["NA"])
        assert frame.dtypes["a"] == "int64"

    def test_null_values_empty_disables_default_empty_null(self, tmp_path):
        csv_path = tmp_path / "empty_nulls.csv"
        csv_path.write_text("a,b\n,1\nNA,2\n")
        frame = ar.read_csv(csv_path, null_values=[])
        df = ar.to_pandas(frame)
        assert df.loc[0, "a"] == ""
        assert df.loc[1, "a"] == "NA"

    def test_null_values_custom_overrides_defaults(self, tmp_path):
        csv_path = tmp_path / "custom_nulls.csv"
        csv_path.write_text("a,b\n,1\nMISSING,2\n")
        frame = ar.read_csv(csv_path, null_values=["MISSING"])
        df = ar.to_pandas(frame)
        assert df.loc[0, "a"] == ""
        assert pd.isna(df.loc[1, "a"])

    def test_null_values_read_and_scan_csv_parity(self, tmp_path):
        csv_path = tmp_path / "parity.csv"
        csv_path.write_text("a\n1\nNA\n3\n")

        default_frame = ar.read_csv(csv_path)
        default_schema = ar.scan_csv(csv_path)
        assert default_frame.dtypes["a"] == "string"
        assert default_schema["a"] == "string"

        custom_frame = ar.read_csv(csv_path, null_values=["NA"])
        custom_schema = ar.scan_csv(csv_path, null_values=["NA"])
        assert custom_frame.dtypes["a"] == "int64"
        assert custom_schema["a"] == "int64"

    def test_null_values_invalid_type(self):
        with pytest.raises(
            TypeError, match="must be a list of strings, not a bare string"
        ):
            ar.read_csv("dummy.csv", null_values="NA")
        with pytest.raises(TypeError, match="must be a list of strings"):
            ar.read_csv("dummy.csv", null_values=("NA",))
        with pytest.raises(TypeError, match="must contain only strings"):
            ar.read_csv("dummy.csv", null_values=[1])

    def test_read_csv_handles_very_long_single_field(self, tmp_path):
        long_text = "a" * 100000

        csv_path = tmp_path / "long_field.csv"
        csv_path.write_text(f"id,text\n1,{long_text}\n")

        frame = ar.read_csv(csv_path)
        df = ar.to_pandas(frame)

        assert df["text"].iloc[0] == long_text
        assert len(df["text"].iloc[0]) == 100000

    def test_read_csv_handles_very_long_quoted_field(self, tmp_path):
        long_text = "b" * 120000

        csv_path = tmp_path / "quoted_long_field.csv"
        csv_path.write_text(f'id,text\n1,"{long_text}"\n')

        frame = ar.read_csv(csv_path)
        df = ar.to_pandas(frame)

        assert df["text"].iloc[0] == long_text
        assert len(df["text"].iloc[0]) == 120000

    def test_read_csv_handles_mixed_normal_and_large_fields(self, tmp_path):
        long_text = "x" * 80000

        csv_path = tmp_path / "mixed_large_fields.csv"
        csv_path.write_text(f"id,text\n1,hello\n2,{long_text}\n3,world\n")

        frame = ar.read_csv(csv_path)
        df = ar.to_pandas(frame)

        assert df["text"].iloc[0] == "hello"
        assert df["text"].iloc[1] == long_text
        assert df["text"].iloc[2] == "world"

    def test_read_csv_encoding_errors_replace_header(self, tmp_path):
        csv_file = tmp_path / "invalid_header.csv"

        csv_file.write_bytes(b"na\xffme\nalice\n")

        frame = ar.read_csv(
            csv_file,
            encoding="utf-8",
            encoding_errors="replace",
        )

        columns = frame.columns

        assert columns == ["na�me"]

    def test_read_csv_encoding_errors_ignore_header(self, tmp_path):
        csv_file = tmp_path / "invalid_header.csv"

        csv_file.write_bytes(b"na\xffme\nalice\n")

        frame = ar.read_csv(
            csv_file,
            encoding="utf-8",
            encoding_errors="ignore",
        )

        columns = frame.columns

        assert columns == ["name"]

    def test_read_csv_encoding_errors_strict_header(self, tmp_path):
        csv_file = tmp_path / "invalid_header.csv"

        csv_file.write_bytes(b"na\xffme\nalice\n")

        with pytest.raises(ar.CsvReadError):
            ar.read_csv(
                csv_file,
                encoding="utf-8",
                encoding_errors="strict",
            )


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

    def test_scan_csv_with_thousands_separator(self, tmp_path):
        csv_path = tmp_path / "scan_thousands.csv"
        csv_path.write_text('value\n"1,234"\n')
        schema = ar.scan_csv(csv_path, thousands_separator=",")
        assert schema["value"] == "int64"

    def test_scan_read_thousands_separator_parity(self, tmp_path):
        csv_path = tmp_path / "parity.csv"
        csv_path.write_text('value\n"1,234"\n')
        schema = ar.scan_csv(csv_path, thousands_separator=",")
        frame = ar.read_csv(csv_path, thousands_separator=",")
        assert schema["value"] == frame.dtypes["value"]
        assert schema["value"] == "int64"

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

    def test_non_utf8_sampling_preserves_quoted_field_text(self, tmp_path):
        csv_path = tmp_path / "latin1_quoted.csv"
        source_text = 'name,notes\r\nAlice,"caf\xe9,\r\nline2"\r\nBob,done\r\n'
        csv_path.write_bytes(source_text.encode("latin-1"))

        with _utf8_csv_path(str(csv_path), "latin-1", sample_rows=2) as native_path:
            assert Path(native_path).read_bytes().decode("utf-8") == (
                'name,notes\r\nAlice,"café,\r\nline2"\r\n'
            )

    def test_scan_non_utf8_crlf_split_across_chunk_boundary(self, tmp_path):
        csv_path = tmp_path / "latin1_crlf_boundary.csv"
        header = "pad,value\r\n"
        row1 = f"{'x' * 8176},100\r\n"
        row2 = "y,hello\r\n"
        row3 = "z,200\r\n"
        csv_path.write_bytes((header + row1 + row2 + row3).encode("latin-1"))

        schema = ar.scan_csv(csv_path, encoding="latin-1", sample_size=3)

        assert schema == {"pad": "string", "value": "string"}

    def test_scan_sample_size_non_utf8_does_not_leak_later_type_evidence(
        self, tmp_path
    ):
        csv_path = tmp_path / "latin1_sample_limit.csv"
        csv_path.write_bytes("id,value\n1,100\n2,200\n3,ol\xe1\n".encode("latin-1"))

        schema_limited = ar.scan_csv(csv_path, encoding="latin-1", sample_size=2)
        schema_full = ar.scan_csv(csv_path, encoding="latin-1", sample_size=4)

        assert schema_limited["value"] == "int64"
        assert schema_full["value"] == "string"

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

    def test_scan_csv_permission_error_includes_path_and_os_reason(
        self, tmp_path, monkeypatch
    ):
        csv_path = tmp_path / "scan-permission.csv"
        csv_path.write_text("a,b\n1,2\n")
        csv_path_str = str(csv_path)
        real_open = builtins.open

        def blocked_open(*args, **kwargs):
            if args[0] == csv_path_str and args[1] == "rb":
                raise PermissionError(13, "Access is denied")
            return real_open(*args, **kwargs)

        monkeypatch.setattr(builtins, "open", blocked_open)

        with pytest.raises(
            CsvReadError,
            match="Could not access CSV file .+: Access is denied",
        ) as exc_info:
            ar.scan_csv(csv_path)
        assert repr(str(csv_path)) in str(exc_info.value)

    def test_scan_non_standard_extension_accepted(self, tmp_path):
        """Non-standard extensions no longer raise ValueError in scan_csv (fixes #34)."""
        for ext in (".dat", ".log", ".data"):
            p = tmp_path / f"data{ext}"
            p.write_text("name,age\nAlice,30\n")
            schema = ar.scan_csv(str(p))
            assert set(schema.keys()) == {"name", "age"}

    def test_scan_tsv_auto_delimiter(self, tmp_path):
        """scan_csv auto-uses tab delimiter for .tsv files (fixes #34)."""
        tsv = tmp_path / "data.tsv"
        tsv.write_text("name\tage\nAlice\t30\nBob\t25\n")
        schema = ar.scan_csv(str(tsv))
        assert set(schema.keys()) == {"name", "age"}

    def test_scan_tsv_explicit_delimiter_honoured(self, tmp_path):
        """Explicitly supplied delimiter is never overridden for .tsv (fixes #34)."""
        tsv = tmp_path / "pipe.tsv"
        tsv.write_text("name|age\nAlice|30\n")
        schema = ar.scan_csv(str(tsv), delimiter="|")
        assert set(schema.keys()) == {"name", "age"}

    def test_scan_tsv_explicit_comma_delimiter_honoured(self, tmp_path):
        """Passing delimiter=',' to a .tsv file must preserve comma parsing (fixes #34)."""
        tsv = tmp_path / "comma.tsv"
        tsv.write_text("name,age\nAlice,30\n")
        schema = ar.scan_csv(str(tsv), delimiter=",")
        assert set(schema.keys()) == {"name", "age"}

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


def test_trailing_delimiter_creates_empty_field(tmp_path):
    csv_path = tmp_path / "trailing.csv"

    csv_path.write_text("id,name,value\n1,Alice,\n")

    frame = ar.read_csv(csv_path)

    df = ar.to_pandas(frame)

    assert df.shape == (1, 3)
    assert df["id"].iloc[0] == 1
    assert df["name"].iloc[0] == "Alice"
    assert pd.isna(df["value"].iloc[0])


def test_multiple_trailing_delimiters_create_empty_fields(tmp_path):
    csv_path = tmp_path / "multiple_trailing.csv"

    csv_path.write_text("a,b,c,d\n1,2,,\n")

    frame = ar.read_csv(csv_path)

    df = ar.to_pandas(frame)

    assert df.shape == (1, 4)
    assert df["a"].iloc[0] == 1
    assert df["b"].iloc[0] == 2
    assert pd.isna(df["c"].iloc[0])
    assert pd.isna(df["d"].iloc[0])


def test_extra_non_empty_field_still_rejected(tmp_path):
    csv_path = tmp_path / "extra_non_empty.csv"

    csv_path.write_text("id,name\n1,Alice,EXTRA\n")

    with pytest.raises(
        ar.CsvReadError,
        match="expected 2",
    ):
        ar.read_csv(csv_path)


def test_extra_empty_field_is_rejected(tmp_path):
    csv_path = tmp_path / "extra_empty.csv"

    csv_path.write_text("id,name\n1,Alice,\n")

    with pytest.raises(
        ar.CsvReadError,
        match="CSV row 2 has 3 fields; expected 2",
    ):
        ar.read_csv(csv_path)


def test_permissive_mode_rejects_extra_fields(tmp_path):
    csv_path = tmp_path / "permissive_extra.csv"

    csv_path.write_text("id,name\n1,Alice,EXTRA\n")

    with pytest.raises(
        ar.CsvReadError,
        match="CSV row 2 has 3 fields; expected 2",
    ):
        ar.read_csv(csv_path, mode="permissive")


def test_scan_csv_rejects_extra_empty_field(tmp_path):
    csv_path = tmp_path / "scan_extra_empty.csv"

    csv_path.write_text("id,name\n1,Alice,\n")

    with pytest.raises(
        ar.CsvReadError,
        match="CSV row 2 has 3 fields; expected 2",
    ):
        ar.scan_csv(csv_path)


def test_read_csv_chunked_rejects_extra_empty_field(tmp_path):
    csv_path = tmp_path / "chunked_extra_empty.csv"

    csv_path.write_text("id,name\n1,Alice\n2,Bob,\n")

    with pytest.raises(
        ar.CsvReadError,
        match="CSV row 3 has 3 fields; expected 2",
    ):
        list(ar.read_csv_chunked(csv_path, chunksize=1))


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


def test_scan_csv_non_utf8_quoted_field_schema_preserved(tmp_path):
    csv_file = tmp_path / "quoted_latin1.csv"
    csv_file.write_bytes(
        'id,text\r\n1,"caf\xe9,\r\nline2"\r\n2,done\r\n'.encode("latin-1")
    )

    schema = ar.scan_csv(str(csv_file), encoding="latin-1")

    assert schema == {"id": "int64", "text": "string"}


def test_read_csv_non_utf8_quoted_multiline_round_trips(tmp_path):
    """read_csv must preserve quoted multiline records through non-UTF-8 transcoding."""
    csv_file = tmp_path / "test_multiline_latin1.csv"
    csv_file.write_bytes(
        'id,text\n1,"line1\ncaf\xe9\nline3"\n2,done\n'.encode("latin-1")
    )

    df = ar.to_pandas(ar.read_csv(str(csv_file), encoding="latin-1"))

    assert list(df["id"]) == [1, 2]
    assert df["text"].iloc[0] == "line1\ncafé\nline3"
    assert df["text"].iloc[1] == "done"


def test_scan_csv_utf8_quoted_field_behavior_unchanged(tmp_path):
    csv_file = tmp_path / "quoted_utf8.csv"
    csv_file.write_bytes(b'id,text\r\n1,"cafe,\r\nline2"\r\n2,done\r\n')

    schema = ar.scan_csv(str(csv_file))

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


# --- Issue #119: Preserve leading-zero identifier columns ---


class TestLeadingZeroIdentifiers:
    """Test type inference for identifier-like values with leading zeros.

    These tests ensure that columns with leading-zero identifiers (ZIP codes,
    account IDs, product codes) are preserved as strings, not converted to
    integers that lose the leading zeros.
    """

    def test_zip_code_leading_zeros_preserved(self, tmp_path):
        """ZIP codes with leading zeros should remain strings."""
        csv_path = tmp_path / "zips.csv"
        csv_path.write_text("zip_code\n00123\n00045\n12345\n")
        frame = ar.read_csv(str(csv_path))
        df = ar.to_pandas(frame)

        # All values should be strings to preserve leading zeros
        assert frame.dtypes["zip_code"] == "string"
        assert df["zip_code"].iloc[0] == "00123"
        assert df["zip_code"].iloc[1] == "00045"
        assert df["zip_code"].iloc[2] == "12345"

    def test_account_id_with_leading_zeros(self, tmp_path):
        """Account IDs with leading zeros should remain strings."""
        csv_path = tmp_path / "accounts.csv"
        csv_path.write_text("account_id\n00001\n00002\n00010\n")
        frame = ar.read_csv(str(csv_path))
        df = ar.to_pandas(frame)

        assert frame.dtypes["account_id"] == "string"
        assert df["account_id"].iloc[0] == "00001"
        assert df["account_id"].iloc[1] == "00002"
        assert df["account_id"].iloc[2] == "00010"

    def test_product_code_leading_zeros(self, tmp_path):
        """Product codes starting with zero should remain strings."""
        csv_path = tmp_path / "products.csv"
        csv_path.write_text("product_code\n012345\n012346\n112347\n")
        frame = ar.read_csv(str(csv_path))
        df = ar.to_pandas(frame)

        assert frame.dtypes["product_code"] == "string"
        assert df["product_code"].iloc[0] == "012345"
        assert df["product_code"].iloc[1] == "012346"
        assert df["product_code"].iloc[2] == "112347"

    def test_mixed_leading_zeros_in_identifier_column(self, tmp_path):
        """Column with mix of leading-zero and non-leading values should be string."""
        csv_path = tmp_path / "mixed_ids.csv"
        csv_path.write_text("id\n00001\n00999\n12345\n")
        frame = ar.read_csv(str(csv_path))
        df = ar.to_pandas(frame)

        # Once we see a leading-zero value, the column should infer as string
        assert frame.dtypes["id"] == "string"
        assert df["id"].iloc[0] == "00001"
        assert df["id"].iloc[2] == "12345"

    def test_single_zero_still_numeric(self, tmp_path):
        """Single '0' should still infer as numeric (not identifier-like)."""
        csv_path = tmp_path / "zeros.csv"
        csv_path.write_text("value\n0\n1\n2\n")
        frame = ar.read_csv(str(csv_path))

        assert frame.dtypes["value"] == "int64"

    def test_multiple_zeros_like_postal_code(self, tmp_path):
        """Multiple leading zeros (00, 000, etc.) should infer as string."""
        csv_path = tmp_path / "postal.csv"
        csv_path.write_text("code\n00\n000\n0001\n")
        frame = ar.read_csv(str(csv_path))
        df = ar.to_pandas(frame)

        # Multiple leading zeros in context with more digits = identifier-like
        assert frame.dtypes["code"] == "string"
        assert df["code"].iloc[0] == "00"
        assert df["code"].iloc[1] == "000"

    def test_leading_zeros_quoted_values(self, tmp_path):
        """Quoted leading-zero values should be preserved as strings."""
        csv_path = tmp_path / "quoted.csv"
        csv_path.write_text('id\n"00123"\n"00456"\n')
        frame = ar.read_csv(str(csv_path))
        df = ar.to_pandas(frame)

        assert frame.dtypes["id"] == "string"
        assert df["id"].iloc[0] == "00123"
        assert df["id"].iloc[1] == "00456"

    def test_genuine_numeric_column_still_works(self, tmp_path):
        """Purely numeric columns without leading zeros should remain int64."""
        csv_path = tmp_path / "pure_numeric.csv"
        csv_path.write_text("value\n123\n456\n789\n")
        frame = ar.read_csv(str(csv_path))

        assert frame.dtypes["value"] == "int64"

    def test_float_column_unaffected(self, tmp_path):
        """Float columns should infer correctly regardless of zeros."""
        csv_path = tmp_path / "floats.csv"
        csv_path.write_text("value\n1.5\n2.7\n3.14\n")
        frame = ar.read_csv(str(csv_path))

        assert frame.dtypes["value"] == "float64"

    def test_multiple_columns_with_leading_zeros(self, tmp_path):
        """Multiple ID columns with leading zeros should all be strings."""
        csv_path = tmp_path / "multi_ids.csv"
        csv_path.write_text(
            "zip,account,product\n00123,00001,012345\n00456,00002,012346\n"
        )
        frame = ar.read_csv(str(csv_path))

        assert frame.dtypes["zip"] == "string"
        assert frame.dtypes["account"] == "string"
        assert frame.dtypes["product"] == "string"

    def test_leading_zeros_with_nulls(self, tmp_path):
        """Leading-zero identifiers mixed with empty cells should infer correctly."""
        csv_path = tmp_path / "ids_nulls.csv"
        # Use a second column to ensure the empty field is preserved as a row
        csv_path.write_text("id,value\n00123,abc\n,def\n00456,ghi\n")
        frame = ar.read_csv(str(csv_path))
        df = ar.to_pandas(frame)

        assert frame.dtypes["id"] == "string"
        assert df["id"].iloc[0] == "00123"
        assert pd.isna(df["id"].iloc[1])
        assert df["id"].iloc[2] == "00456"

    def test_scan_csv_leading_zeros(self, tmp_path):
        """scan_csv should also preserve leading-zero identifier inference."""
        csv_path = tmp_path / "scan_ids.csv"
        csv_path.write_text("zip\n00123\n00456\n")
        schema = ar.scan_csv(str(csv_path))

        assert schema["zip"] == "string"

    def test_leading_zeros_with_thousands_separator(self, tmp_path):
        """Leading zeros should not interfere with thousands separator handling."""
        csv_path = tmp_path / "leading_thousands.csv"
        csv_path.write_text('value\n"1,000"\n"2,000"\n')
        frame = ar.read_csv(str(csv_path), thousands_separator=",")
        df = ar.to_pandas(frame)

        # No leading zeros here, should still infer as int64
        assert frame.dtypes["value"] == "int64"
        assert df["value"].iloc[0] == 1000

    def test_leading_zeros_uppercase_letters(self, tmp_path):
        """Leading zeros with letters should remain string (already handled)."""
        csv_path = tmp_path / "alphanumeric.csv"
        csv_path.write_text("code\n00A1B\n00C2D\n")
        frame = ar.read_csv(str(csv_path))
        df = ar.to_pandas(frame)

        assert frame.dtypes["code"] == "string"
        assert df["code"].iloc[0] == "00A1B"


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


class TestArFrameGetItem:
    def test_getitem_existing_column(self, sample_csv):
        frame = ar.read_csv(sample_csv)
        result = frame["name"]
        assert isinstance(result, list)
        assert result == ["Alice", "Bob", "Charlie"]

    def test_getitem_integer_column(self, sample_csv):
        frame = ar.read_csv(sample_csv)
        result = frame["age"]
        assert isinstance(result, list)
        assert result == [30, 25, 35]

    def test_getitem_bool_column(self, sample_csv):
        frame = ar.read_csv(sample_csv)
        result = frame["active"]
        assert isinstance(result, list)
        assert result == [True, False, True]

    def test_getitem_missing_column_raises_keyerror(self, sample_csv):
        frame = ar.read_csv(sample_csv)
        with pytest.raises(KeyError):
            frame["nonexistent"]

    def test_getitem_non_string_key_raises_typeerror(self, sample_csv):
        frame = ar.read_csv(sample_csv)
        with pytest.raises(TypeError):
            frame[0]

    def test_getitem_empty_frame(self, tmp_path):
        csv_path = tmp_path / "empty_rows.csv"
        csv_path.write_text("name,age\n")
        frame = ar.read_csv(csv_path)
        result = frame["name"]
        assert result == []

    def test_getitem_column_with_nulls(self, csv_with_nulls):
        frame = ar.read_csv(csv_with_nulls)
        result = frame["name"]
        assert isinstance(result, list)
        assert result[0] == "Alice"

    def test_getitem_column_with_spaces(self, tmp_path):
        csv_path = tmp_path / "spaces.csv"
        csv_path.write_text("first name,last name\nJohn,Doe\n")
        frame = ar.read_csv(csv_path)
        result = frame["first name"]
        assert result == ["John"]


class TestReadCsvSkipRows:
    def test_skiprows_basic(self, tmp_path):
        csv_path = tmp_path / "meta.csv"
        csv_path.write_text("skip1\nskip2\nname,age\nAlice,30\nBob,25\n")
        frame = ar.read_csv(csv_path, skiprows=2)
        assert frame.columns == ["name", "age"]
        assert frame.shape == (2, 2)
        df = ar.to_pandas(frame)
        assert df["name"].tolist() == ["Alice", "Bob"]

    def test_skiprows_with_no_header(self, tmp_path):
        """skiprows with has_header=False skips data rows, columns are auto-named."""
        csv_path = tmp_path / "noheader.csv"
        csv_path.write_text("junk\n1,Alice\n2,Bob\n")
        frame = ar.read_csv(csv_path, skiprows=1, has_header=False)
        assert frame.shape == (2, 2)
        df = ar.to_pandas(frame)
        assert df["col_0"].tolist() == [1, 2]

    def test_skiprows_with_nrows(self, tmp_path):
        csv_path = tmp_path / "combo.csv"
        csv_path.write_text("skip\nname,age\nAlice,30\nBob,25\nCharlie,35\n")
        frame = ar.read_csv(csv_path, skiprows=1, nrows=2)
        assert frame.shape == (2, 2)
        df = ar.to_pandas(frame)
        assert df["name"].tolist() == ["Alice", "Bob"]

    def test_skiprows_zero_is_noop(self, tmp_path):
        """skiprows=0 behaves identically to not passing skiprows."""
        csv_path = tmp_path / "noop.csv"
        csv_path.write_text("name,age\nAlice,30\n")
        frame = ar.read_csv(csv_path, skiprows=0)
        assert frame.shape == (1, 2)

    def test_skiprows_skips_all_data_rows(self, tmp_path):
        """Skipping more rows than exist yields an empty frame."""
        csv_path = tmp_path / "skipall.csv"
        csv_path.write_text("skip1\nskip2\nname,age\nAlice,30\n")
        frame = ar.read_csv(csv_path, skiprows=10)
        assert frame.shape == (0, 0)

    def test_skiprows_invalid_negative(self, tmp_path):
        csv_path = tmp_path / "data.csv"
        csv_path.write_text("a,b\n1,2\n")
        with pytest.raises(ValueError, match="non-negative"):
            ar.read_csv(csv_path, skiprows=-1)

    def test_skiprows_invalid_bool(self, tmp_path):
        csv_path = tmp_path / "data.csv"
        csv_path.write_text("a,b\n1,2\n")
        with pytest.raises(TypeError, match="integer"):
            ar.read_csv(csv_path, skiprows=True)

    def test_skiprows_invalid_float(self, tmp_path):
        csv_path = tmp_path / "data.csv"
        csv_path.write_text("a,b\n1,2\n")
        with pytest.raises(TypeError, match="integer"):
            ar.read_csv(csv_path, skiprows=1.5)


class TestInferTypeLocaleAndNumericEdgeCases:
    def test_float_decimal_dot(self, tmp_path):
        path = tmp_path / "decimal.csv"
        path.write_text("v\n3.14\n")
        assert ar.read_csv(path).dtypes["v"] == "float64"

    def test_whitespace_padded_int(self, tmp_path):
        path = tmp_path / "ws_int.csv"
        path.write_text("v\n 123 \n")
        assert ar.read_csv(path).dtypes["v"] == "int64"

    def test_whitespace_padded_float(self, tmp_path):
        path = tmp_path / "ws_float.csv"
        path.write_text("v\n 3.14 \n")
        assert ar.read_csv(path).dtypes["v"] == "float64"

    def test_whitespace_padded_bool(self, tmp_path):
        path = tmp_path / "ws_bool.csv"
        path.write_text("flag\n true \n")
        assert ar.read_csv(path).dtypes["flag"] == "bool"

    def test_special_float_tokens_infer_float64(self, tmp_path):
        path = tmp_path / "special.csv"
        path.write_text("v\ninf\n-inf\nnan\n")
        assert ar.read_csv(path).dtypes["v"] == "float64"

    def test_scientific_notation_lower(self, tmp_path):
        path = tmp_path / "sci_lower.csv"
        path.write_text("v\n1e10\n")
        assert ar.read_csv(path).dtypes["v"] == "float64"

    def test_scientific_notation_upper(self, tmp_path):
        path = tmp_path / "sci_upper.csv"
        path.write_text("v\n1E10\n")
        assert ar.read_csv(path).dtypes["v"] == "float64"

    def test_integer_overflow_remains_string(self, tmp_path):
        path = tmp_path / "overflow.csv"
        path.write_text("v\n9223372036854775808\n")
        frame = ar.read_csv(path)
        df = ar.to_pandas(frame)
        assert frame.dtypes["v"] == "string"
        assert df["v"].iloc[0] == "9223372036854775808"

    def test_integer_overflow_mixed_column_string(self, tmp_path):
        path = tmp_path / "overflow_mixed.csv"
        path.write_text("v\n1\n9223372036854775808\n")
        frame = ar.read_csv(path)
        df = ar.to_pandas(frame)
        assert frame.dtypes["v"] == "string"
        assert list(df["v"]) == ["1", "9223372036854775808"]


class TestCastTypes:
    def test_cast_valid_string_to_int(self, tmp_path):
        csv_path = tmp_path / "data.csv"
        csv_path.write_text("value\n1\n2\n3\n")
        frame = ar.read_csv(csv_path)
        result = ar.cast_types(frame, {"value": "int64"})
        assert result.dtypes["value"] == "int64"

    def test_cast_invalid_string_to_int_raises(self, tmp_path):
        csv_path = tmp_path / "data.csv"
        csv_path.write_text("value\nhello\nworld\n")
        frame = ar.read_csv(csv_path)
        with pytest.raises(ar.TypeCastError):
            ar.cast_types(frame, {"value": "int64"})

    def test_cast_invalid_string_to_int_coerce(self, tmp_path):
        csv_path = tmp_path / "data.csv"
        csv_path.write_text("value\n1\nhello\n3\n")
        frame = ar.read_csv(csv_path)
        result = ar.cast_types(frame, {"value": "int64"}, errors="coerce")
        df = ar.to_pandas(result)
        assert result.dtypes["value"] == "int64"
        assert pd.isna(df["value"].iloc[1])

    def test_cast_mixed_valid_invalid_raises_by_default(self, tmp_path):
        csv_path = tmp_path / "data.csv"
        csv_path.write_text("value\n1\nabc\n3\n")
        frame = ar.read_csv(csv_path)
        with pytest.raises(ar.TypeCastError):
            ar.cast_types(frame, {"value": "int64"})

    def test_cast_float_string_to_int_raises(self, tmp_path):
        csv_path = tmp_path / "data.csv"
        csv_path.write_text("value\n1.5\n2.7\n")
        frame = ar.read_csv(csv_path)
        with pytest.raises(ar.TypeCastError):
            ar.cast_types(frame, {"value": "int64"})


class TestFromPandas:
    def test_nullable_int_column(self):
        df = pd.DataFrame({"value": pd.array([1, 2, None], dtype="Int64")})
        frame = ar.from_pandas(df)
        assert frame.dtypes["value"] == "int64"

    def test_nullable_float_column(self):
        df = pd.DataFrame({"value": pd.array([1.1, 2.2, None], dtype="Float64")})
        frame = ar.from_pandas(df)
        assert frame.dtypes["value"] == "float64"

    def test_nullable_boolean_column(self):
        df = pd.DataFrame({"flag": pd.array([True, False, None], dtype="boolean")})
        frame = ar.from_pandas(df)
        assert frame.dtypes["flag"] == "bool"

    def test_nullable_int_null_preserved(self):
        df = pd.DataFrame({"value": pd.array([1, None, 3], dtype="Int64")})
        frame = ar.from_pandas(df)
        result = ar.to_pandas(frame)
        assert pd.isna(result["value"].iloc[1])

    def test_nullable_bool_null_preserved(self):
        df = pd.DataFrame({"flag": pd.array([True, None, False], dtype="boolean")})
        frame = ar.from_pandas(df)
        result = ar.to_pandas(frame)
        assert pd.isna(result["flag"].iloc[1])


class TestEdgeCaseCsvShapes:
    def test_single_row_csv(self, tmp_path):
        csv_path = tmp_path / "single_row.csv"
        csv_path.write_text("name,age,score\nAlice,30,95\n")
        frame = ar.read_csv(csv_path)
        assert frame.shape == (1, 3)
        assert frame.columns == ["name", "age", "score"]
        df = ar.to_pandas(frame)
        assert df["name"].iloc[0] == "Alice"
        assert df["age"].iloc[0] == 30

    def test_single_column_csv(self, tmp_path):
        csv_path = tmp_path / "single_col.csv"
        csv_path.write_text("name\nAlice\nBob\nCharlie\n")
        frame = ar.read_csv(csv_path)
        assert frame.shape == (3, 1)
        assert frame.columns == ["name"]
        df = ar.to_pandas(frame)
        assert list(df["name"]) == ["Alice", "Bob", "Charlie"]

    def test_single_row_scan_csv(self, tmp_path):
        csv_path = tmp_path / "single_row.csv"
        csv_path.write_text("name,age\nAlice,30\n")
        schema = ar.scan_csv(csv_path)
        assert "name" in schema
        assert "age" in schema
        assert len(schema) == 2

    def test_single_column_scan_csv(self, tmp_path):
        csv_path = tmp_path / "single_col.csv"
        csv_path.write_text("score\n10\n20\n30\n")
        schema = ar.scan_csv(csv_path)
        assert "score" in schema
        assert len(schema) == 1


class TestUnicodeFilePath:
    """read_csv and scan_csv must work with non-ASCII characters in the path."""

    def test_read_csv_unicode_filename(self, tmp_path, unicode_csv):
        csv_path = tmp_path / "用户数据.csv"
        csv_path.write_text(unicode_csv, encoding="utf-8")
        frame = ar.read_csv(str(csv_path))
        assert frame.columns == ["name", "value"]
        assert frame.shape == (2, 2)

    def test_scan_csv_unicode_filename(self, tmp_path, unicode_csv):
        csv_path = tmp_path / "用户数据.csv"
        csv_path.write_text(unicode_csv, encoding="utf-8")
        schema = ar.scan_csv(str(csv_path))
        assert schema == {"name": "string", "value": "int64"}

    def test_read_csv_unicode_directory(self, tmp_path, unicode_csv):
        folder = tmp_path / "données"
        folder.mkdir()
        csv_path = folder / "data.csv"
        csv_path.write_text(unicode_csv, encoding="utf-8")
        frame = ar.read_csv(str(csv_path))
        assert frame.shape == (2, 2)

    def test_scan_csv_unicode_directory(self, tmp_path, unicode_csv):
        folder = tmp_path / "données"
        folder.mkdir()
        csv_path = folder / "data.csv"
        csv_path.write_text(unicode_csv, encoding="utf-8")
        schema = ar.scan_csv(str(csv_path))
        assert schema == {"name": "string", "value": "int64"}

    def test_chunked_read_unicode_path(self, tmp_path, unicode_csv):
        folder = tmp_path / "用户"
        folder.mkdir()

        csv_path = folder / "数据.csv"
        csv_path.write_text(unicode_csv, encoding="utf-8")

        chunks = ar.read_csv_chunked(str(csv_path), chunksize=1)
        chunks = list(chunks)

        assert len(chunks) > 0

        assert chunks[0].shape[1] == 2

        total_rows = sum(chunk.shape[0] for chunk in chunks)
        assert total_rows == 2


# --- Issue #113: unterminated quoted field errors must include line number ---


class TestUnterminatedQuoteLocation:
    """Regression tests for #113 — CsvReadError must include the line number
    where an unterminated quoted field begins so users can locate the problem
    in their input file quickly."""

    def test_error_message_includes_line_number(self, tmp_path):
        # Unterminated quote starts on line 2 (after the header).
        csv_path = tmp_path / "bad.csv"
        csv_path.write_text('name,note\nAlice,"unterminated\n')
        with pytest.raises(ar.CsvReadError, match="line 2"):
            ar.read_csv(csv_path)

    def test_error_message_includes_correct_line_for_later_row(self, tmp_path):
        # Two valid rows, then an unterminated quote on line 4.
        csv_path = tmp_path / "bad.csv"
        csv_path.write_text('a,b\n1,ok\n2,fine\n3,"oops\n')
        with pytest.raises(ar.CsvReadError, match="line 4"):
            ar.read_csv(csv_path)

    def test_error_message_includes_line_for_multiline_field_start(self, tmp_path):
        # A valid multiline field followed by an unterminated one.
        # Valid: rows 1-3 (header + "hello\nworld" spanning lines 2-3).
        # Invalid: unterminated quote starts on line 4.
        csv_path = tmp_path / "bad.csv"
        csv_path.write_bytes(b'id,text\n1,"hello\nworld"\n2,"oops\n')
        with pytest.raises(ar.CsvReadError, match="line 4"):
            ar.read_csv(csv_path)

    def test_error_message_says_unterminated_quoted_field(self, tmp_path):
        # The error message must mention "Unterminated quoted field".
        csv_path = tmp_path / "bad.csv"
        csv_path.write_text('x\n"no close\n')
        with pytest.raises(ar.CsvReadError, match="Unterminated quoted field"):
            ar.read_csv(csv_path)

    def test_valid_multiline_field_still_parses(self, tmp_path):
        # A properly closed multiline field must NOT raise.
        csv_path = tmp_path / "ok.csv"
        csv_path.write_bytes(b'id,text\n1,"hello\nworld"\n')
        frame = ar.read_csv(csv_path)
        assert frame.shape == (1, 2)
        df = ar.to_pandas(frame)
        assert df["text"].iloc[0] == "hello\nworld"

    def test_no_header_unterminated_quote_line_number(self, tmp_path):
        # Without a header, the unterminated quote is on line 1.
        csv_path = tmp_path / "bad.csv"
        csv_path.write_text('"oops\n')
        with pytest.raises(ar.CsvReadError, match="line 1"):
            ar.read_csv(csv_path, has_header=False)


class TestArFrameToDict:
    def test_to_dict_basic(self, sample_csv):
        frame = ar.read_csv(sample_csv)
        result = frame.to_dict()
        assert isinstance(result, dict)
        assert list(result.keys()) == ["name", "age", "email", "active"]

    def test_to_dict_values_are_lists(self, sample_csv):
        frame = ar.read_csv(sample_csv)
        result = frame.to_dict()
        for val in result.values():
            assert isinstance(val, list)

    def test_to_dict_string_column(self, sample_csv):
        frame = ar.read_csv(sample_csv)
        result = frame.to_dict()
        assert result["name"] == ["Alice", "Bob", "Charlie"]

    def test_to_dict_integer_column(self, sample_csv):
        frame = ar.read_csv(sample_csv)
        result = frame.to_dict()
        assert result["age"] == [30, 25, 35]

    def test_to_dict_bool_column(self, sample_csv):
        frame = ar.read_csv(sample_csv)
        result = frame.to_dict()
        assert result["active"] == [True, False, True]

    def test_to_dict_preserves_column_order(self, sample_csv):
        frame = ar.read_csv(sample_csv)
        result = frame.to_dict()
        assert list(result.keys()) == frame.columns

    def test_to_dict_empty_frame(self, tmp_path):
        csv_path = tmp_path / "empty_rows.csv"
        csv_path.write_text("name,age\n")
        frame = ar.read_csv(csv_path)
        result = frame.to_dict()
        assert result == {"name": [], "age": []}

    def test_to_dict_with_nulls(self, csv_with_nulls):
        frame = ar.read_csv(csv_with_nulls)
        result = frame.to_dict()
        assert isinstance(result, dict)
        assert result["name"][0] == "Alice"

    def test_to_dict_single_column(self, tmp_path):
        csv_path = tmp_path / "single.csv"
        csv_path.write_text("value\n1\n2\n3\n")
        frame = ar.read_csv(csv_path)
        result = frame.to_dict()
        assert result == {"value": [1, 2, 3]}

    def test_to_dict_consistent_with_getitem(self, sample_csv):
        frame = ar.read_csv(sample_csv)
        result = frame.to_dict()
        for col in frame.columns:
            assert result[col] == frame[col]


class TestArFrameStr:
    def test_str_contains_shape(self, sample_csv):
        frame = ar.read_csv(sample_csv)
        result = str(frame)
        assert "3" in result
        assert "4" in result

    def test_str_contains_column_names(self, sample_csv):
        frame = ar.read_csv(sample_csv)
        result = str(frame)
        assert "name" in result
        assert "age" in result

    def test_str_contains_data_values(self, sample_csv):
        frame = ar.read_csv(sample_csv)
        result = str(frame)
        assert "Alice" in result

    def test_str_contains_dtypes(self, sample_csv):
        frame = ar.read_csv(sample_csv)
        result = str(frame)
        assert "string" in result or "int64" in result

    def test_str_empty_frame(self, tmp_path):
        csv_path = tmp_path / "empty_rows.csv"
        csv_path.write_text("name,age\n")
        frame = ar.read_csv(csv_path)
        result = str(frame)
        assert "empty" in result.lower() or "0" in result

    def test_str_large_frame_shows_truncation(self, large_csv):
        frame = ar.read_csv(large_csv)
        result = str(frame)
        assert "more rows" in result

    def test_str_returns_string(self, sample_csv):
        frame = ar.read_csv(sample_csv)
        assert isinstance(str(frame), str)
