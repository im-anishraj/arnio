
import pytest
import arnio as ar


_INVALID_DELIMITERS = [
    pytest.param("\n", id="newline"),
    pytest.param("\r", id="carriage-return"),
    pytest.param("\0", id="NUL"),
    pytest.param('"',  id="double-quote"),
]

_CSV_CONTENT = "a,b\n1,2\n3,4\n"



# read_csv


@pytest.mark.parametrize("delim", _INVALID_DELIMITERS)
def test_read_csv_rejects_invalid_delimiter(delim, tmp_path):
    csv_file = tmp_path / "sample.csv"
    csv_file.write_text(_CSV_CONTENT, newline="")

    with pytest.raises(ValueError, match="delimiter"):
        ar.read_csv(str(csv_file), delimiter=delim)



# read_csv_chunked


@pytest.mark.parametrize("delim", _INVALID_DELIMITERS)
def test_read_csv_chunked_rejects_invalid_delimiter(delim, tmp_path):
    csv_file = tmp_path / "sample.csv"
    csv_file.write_text(_CSV_CONTENT, newline="")

    with pytest.raises(ValueError, match="delimiter"):
        # Consume the generator so validation actually runs.
        list(ar.read_csv_chunked(str(csv_file), delimiter=delim))



# scan_csv


@pytest.mark.parametrize("delim", _INVALID_DELIMITERS)
def test_scan_csv_rejects_invalid_delimiter(delim, tmp_path):
    csv_file = tmp_path / "sample.csv"
    csv_file.write_text(_CSV_CONTENT, newline="")

    with pytest.raises(ValueError, match="delimiter"):
        ar.scan_csv(str(csv_file), delimiter=delim)


# Sanity: valid non-default delimiters still work


@pytest.mark.parametrize("delim,content", [
    pytest.param("|",  "a|b\n1|2\n",  id="pipe"),
    pytest.param(";",  "a;b\n1;2\n",  id="semicolon"),
    pytest.param("\t", "a\tb\n1\t2\n", id="tab"),
])
def test_read_csv_accepts_valid_delimiter(delim, content, tmp_path):
    csv_file = tmp_path / "sample.csv"
    csv_file.write_text(content, newline="")

    frame = ar.read_csv(str(csv_file), delimiter=delim)
    assert frame.shape == (1, 2)
    assert list(frame.columns) == ["a", "b"]
