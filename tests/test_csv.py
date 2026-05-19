"""Tests for CSV reading functionality."""

import io
from pathlib import Path

import pandas as pd
import pytest

import arnio as ar
from arnio.io import _utf8_csv_path

MESSY_CSV = str(Path(__file__).parent / "fixtures" / "messy_sales_data.csv")


class TestReadCsv:
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

    def test_unsupported_extension(self, tmp_path):
        import pytest

        file_path = str(tmp_path / "data.json")
        with open(file_path, "w") as f:
            f.write('{"a": 1}')

        with pytest.raises(ValueError, match="Unsupported file format"):
            ar.read_csv(file_path)

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

        with pytest.raises(ar.CsvReadError, match="Unterminated quoted CSV record"):
            ar.read_csv(csv_path)

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
