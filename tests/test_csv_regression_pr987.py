import pytest

import arnio as ar
from arnio.exceptions import CsvReadError


def test_line_endings_mixed(tmp_path):
    csv_path = tmp_path / "mixed_endings.csv"
    csv_path.write_bytes(b"name,age\nAlice,25\r\nBob,30\rCharlie,35\n")
    frame = ar.read_csv(str(csv_path))
    df = ar.to_pandas(frame)
    assert len(df) == 3
    assert df["name"].iloc[0] == "Alice"
    assert df["name"].iloc[1] == "Bob"
    assert df["name"].iloc[2] == "Charlie"


def test_multiline_quoted_records(tmp_path):
    csv_path = tmp_path / "multiline.csv"
    csv_path.write_text('id,desc\n1,"hello\nworld"\n2,"escaped ""quote"""\n')
    frame = ar.read_csv(str(csv_path))
    df = ar.to_pandas(frame)
    assert len(df) == 2
    assert df["desc"].iloc[0] == "hello\nworld"
    assert df["desc"].iloc[1] == 'escaped "quote"'


def test_buffer_boundary_edge_cases(tmp_path):
    csv_path = tmp_path / "boundary.csv"
    header = b"pad,val\r\n"
    pad_len = 65536 - len(header) - 1
    row1 = b"a" * (pad_len - 6) + b",test\r\n"
    row2 = b"b,after_boundary\r\n"

    csv_path.write_bytes(header + row1 + row2)

    frame = ar.read_csv(str(csv_path))
    df = ar.to_pandas(frame)
    assert len(df) == 2
    assert df["val"].iloc[0] == "test"
    assert df["val"].iloc[1] == "after_boundary"


def test_nul_byte_exception(tmp_path):
    csv_path = tmp_path / "nul.csv"
    csv_path.write_bytes(b"id,val\n1,a\0b\n")
    with pytest.raises(CsvReadError):
        ar.read_csv(str(csv_path))
