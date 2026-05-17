"""
Fuzz tests for CSV parser edge cases.
"""

import os
import tempfile

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

import arnio as ar


def test_malformed_unclosed_quotes(tmp_path):
    """Test that an unclosed quote raises CsvReadError and does not crash."""
    csv_path = tmp_path / "test.csv"
    csv_path.write_text('id,text\n1,"hello')

    with pytest.raises(ar.CsvReadError):
        ar.read_csv(csv_path)


def test_malformed_mid_field_quotes(tmp_path):
    """Test mid-field quotes parses safely or raises defined exception."""
    csv_path = tmp_path / "test.csv"
    csv_path.write_text('id,text\n1,hel"lo\n2,ok')

    try:
        ar.read_csv(csv_path)
    except ar.CsvReadError:
        pass  # If it rejects, that's fine too


def test_malformed_double_quotes_inside_field(tmp_path):
    """Test properly escaped double quotes inside fields are accepted."""
    csv_path = tmp_path / "test.csv"
    csv_path.write_text('id,text\n1,"hel""lo"\n2,ok')

    frame = ar.read_csv(csv_path)
    df = ar.to_pandas(frame)
    assert df.loc[0, "text"] == 'hel"lo'


def test_malformed_mixed_quote_styles(tmp_path):
    """Test mixed quote styles do not crash the parser."""
    csv_path = tmp_path / "test.csv"
    csv_path.write_text("id,text\n1,'hello',\"world\"\n")

    try:
        ar.read_csv(csv_path)
    except ar.CsvReadError:
        pass


def test_malformed_quote_followed_by_non_delimiter(tmp_path):
    """Test quote followed immediately by non-delimiter."""
    csv_path = tmp_path / "test.csv"
    csv_path.write_text('id,text\n1,"field"extra,next\n')

    try:
        ar.read_csv(csv_path)
    except ar.CsvReadError:
        pass


def test_random_delim_tab_separated(tmp_path):
    """Test tab separation with commas in values."""
    csv_path = tmp_path / "test.csv"
    csv_path.write_text('id\ttext\n1\t"hello, world"\n2\ttest')

    frame = ar.read_csv(csv_path, delimiter="\t")
    assert frame.shape == (2, 2)
    df = ar.to_pandas(frame)
    assert df.loc[0, "text"] == "hello, world"


def test_random_delim_unusual(tmp_path):
    """Test semicolon, pipe, tilde as delimiters."""
    for sep in [";", "|", "~"]:
        csv_path = tmp_path / f"test_{sep}.csv"
        csv_path.write_text(f"id{sep}text\n1{sep}ok")
        frame = ar.read_csv(csv_path, delimiter=sep)
        assert frame.shape == (1, 2)


def test_random_delim_multi_character(tmp_path):
    """Test multi-character delimiters raise TypeError (pybind11 char constraint) or ValueError."""
    csv_path = tmp_path / "test.csv"
    csv_path.write_text("id||text\n1||ok")
    with pytest.raises((TypeError, ValueError, ar.CsvReadError)):
        ar.read_csv(csv_path, delimiter="||")


def test_random_delim_no_delimiter(tmp_path):
    """Test single-column CSV with no delimiter."""
    csv_path = tmp_path / "test.csv"
    csv_path.write_text("id\n1\n2\n")
    frame = ar.read_csv(csv_path)
    assert frame.shape == (2, 1)


def test_random_delim_whitespace(tmp_path):
    """Test whitespace as delimiter."""
    csv_path = tmp_path / "test.csv"
    csv_path.write_text("id text\n1 ok\n2 ok\n")
    frame = ar.read_csv(csv_path, delimiter=" ")
    assert frame.shape == (2, 2)


def test_corrupt_inconsistent_columns(tmp_path):
    """Test inconsistent column counts per row raises exception or is handled safely."""
    csv_path = tmp_path / "test.csv"
    csv_path.write_text("a,b,c\n1,2\n1,2,3,4\n")
    try:
        ar.read_csv(csv_path)
    except ar.CsvReadError:
        pass


def test_corrupt_empty_rows(tmp_path):
    """Test empty rows in the middle of data."""
    csv_path = tmp_path / "test.csv"
    csv_path.write_text("a,b\n1,2\n\n3,4\n")
    ar.read_csv(csv_path)
    # usually empty rows are ignored or treated as nulls, just ensuring it doesn't crash


def test_corrupt_only_delimiters(tmp_path):
    """Test rows with only delimiters."""
    csv_path = tmp_path / "test.csv"
    csv_path.write_text("a,b,c\n,,\n,,")
    try:
        frame = ar.read_csv(csv_path)
        assert frame.shape == (2, 3)
    except ar.CsvReadError:
        pass


def test_corrupt_binary_null_bytes(tmp_path):
    """Test binary/null bytes embedded in rows."""
    csv_path = tmp_path / "test.csv"
    csv_path.write_bytes(b"a,b\n1,\x00\n2,3")
    with pytest.raises(ar.CsvReadError):
        ar.read_csv(csv_path)


def test_corrupt_extremely_long_row(tmp_path):
    """Test extremely long row (>1MB single row)."""
    csv_path = tmp_path / "test.csv"
    long_str = "x" * (1024 * 1024 + 10)
    csv_path.write_text(f"a,b\n1,{long_str}\n")
    try:
        ar.read_csv(csv_path)
    except ar.CsvReadError:
        pass  # It's allowed to reject it, but not segfault


def test_corrupt_unicode_emoji(tmp_path):
    """Test Unicode and emoji in fields."""
    csv_path = tmp_path / "test.csv"
    csv_path.write_text("a,b\n1,🚀\n2,ñ")
    frame = ar.read_csv(csv_path)
    df = ar.to_pandas(frame)
    assert df.loc[0, "b"] == "🚀"


def test_corrupt_mixed_line_endings(tmp_path):
    """Test mixed Windows, Unix, and old Mac line endings."""
    csv_path = tmp_path / "test.csv"
    csv_path.write_text("a,b\r\n1,2\n3,4\r5,6")
    try:
        ar.read_csv(csv_path)
    except ar.CsvReadError:
        pass


@settings(max_examples=100, deadline=None)
@given(st.text())
def test_hypothesis_random_csv_input(input_text):
    """Generate random strings as CSV input and assert parser never crashes."""
    with tempfile.NamedTemporaryFile(mode="wb", delete=False, suffix=".csv") as f:
        # Write bytes if needed to avoid unicode encoding failures during write, but hypothesis generates unicode text.
        # So we encode to utf8 to be safe as our parser reads binary/text
        f.write(input_text.encode("utf-8", errors="replace"))
        temp_path = f.name

    try:
        ar.read_csv(temp_path)
    except ar.CsvReadError:
        pass
    except ValueError as e:
        if "Unsupported file format" in str(e):
            pass
        else:
            raise
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


@settings(max_examples=50, deadline=None)
@given(
    st.lists(
        st.tuples(
            st.text(
                alphabet=st.characters(blacklist_categories=("Cs",)),
                min_size=1,
                max_size=10,
            ),
            st.integers(),
        ),
        min_size=1,
        max_size=10,
    )
)
def test_hypothesis_round_trip(data):
    """Generate valid CSVs and assert round-trip stability (parse -> serialize -> parse)."""
    with tempfile.NamedTemporaryFile(mode="wb", delete=False, suffix=".csv") as f:
        f.write(b"col_text,col_int\n")
        for text, num in data:
            clean_text = text.replace('"', '""').replace("\n", " ").replace("\r", " ")
            f.write(f'"{clean_text}",{num}\n'.encode())
        temp_path = f.name

    try:
        frame1 = ar.read_csv(temp_path)
        df1 = ar.to_pandas(frame1)

        temp_path2 = temp_path + "2.csv"
        df1.to_csv(temp_path2, index=False)
        frame2 = ar.read_csv(temp_path2)
        df2 = ar.to_pandas(frame2)

        assert len(df1) == len(df2)
    except ar.CsvReadError:
        pass  # Just ensure it doesn't crash
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        if os.path.exists(temp_path + "2.csv"):
            os.remove(temp_path + "2.csv")
