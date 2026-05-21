import io
from pathlib import Path
import pytest
import pandas as pd

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


def test_chunked_parity_skip_nrows(tmp_path):
    csv_path = tmp_path / "chunked.csv"
    csv_path.write_text("id,val\n1,a\n2,b\n3,c\n4,d\n5,e\n")

    f1 = ar.read_csv(str(csv_path), skip_rows=1, nrows=3)
    df1 = ar.to_pandas(f1)

    reader = ar.read_csv_chunked(str(csv_path), chunksize=2, skip_rows=1, nrows=3)
    chunks = list(reader)
    df2 = pd.concat([ar.to_pandas(c) for c in chunks], ignore_index=True)

    assert len(df1) == 3
    assert len(df2) == 3
    assert list(df1["id"]) == [2, 3, 4]
    assert list(df2["id"]) == [2, 3, 4]


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
