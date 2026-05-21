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
    csv_path.write_bytes(b'id,desc\n1,"hello\nworld"\n2,"escaped ""quote"""\n')
    frame = ar.read_csv(str(csv_path))
    df = ar.to_pandas(frame)
    assert len(df) == 2
    assert df["desc"].iloc[0] == "hello\nworld"
    assert df["desc"].iloc[1] == 'escaped "quote"'


def test_buffer_boundary_edge_cases(tmp_path):
    csv_path = tmp_path / "boundary.csv"
    header = b"pad,val\r\n"
    # We want to cross the boundary right between \r and \n at the end of a record.
    # The record should also contain a multiline quoted field.
    # len(header) = 9
    # We want row1_part1 to be 65527 bytes, ending in \r.
    # The suffix of row1_part1 is b',"hello\nworld"\r' which is 16 bytes.
    # So padding is 65527 - 16 = 65511 bytes.
    padding = b"a" * 65511
    row1_part1 = padding + b',"hello\nworld"\r'
    row1_part2 = b"\n"
    row2 = b"b,after_boundary\r\n"

    csv_path.write_bytes(header + row1_part1 + row1_part2 + row2)

    frame = ar.read_csv(str(csv_path))
    df = ar.to_pandas(frame)
    assert len(df) == 2
    assert df["val"].iloc[0] == "hello\nworld"
    assert df["val"].iloc[1] == "after_boundary"


def test_nul_byte_exception(tmp_path):
    csv_path = tmp_path / "nul.csv"
    csv_path.write_bytes(b"id,val\n1,a\0b\n")
    with pytest.raises(CsvReadError):
        ar.read_csv(str(csv_path))


def test_read_csv_skiprows_nrows(tmp_path):
    csv_path = tmp_path / "skip_nrows.csv"
    lines = ["skip_metadata_1", "skip_metadata_2", "id,val"]
    for i in range(10):
        lines.append(f"{i},val_{i}")
    csv_path.write_text("\n".join(lines))

    frame = ar.read_csv(str(csv_path), skiprows=2, nrows=5)
    df = ar.to_pandas(frame)
    assert len(df) == 5
    assert list(df["id"]) == [0, 1, 2, 3, 4]


def test_csv_readers_parity_multiline_mixed(tmp_path):
    import pandas as pd

    csv_path = tmp_path / "parity.csv"
    # Mixed line endings and multiline quoted records
    csv_path.write_bytes(
        b"id,val\r\n"
        b'1,"line1\nline2"\n'
        b"2,normal\r\n"
        b'3,"another\r\nquote"\n'
        b"4,end\r"
    )

    df_read = ar.to_pandas(ar.read_csv(str(csv_path)))

    chunks = list(ar.read_csv_chunked(str(csv_path), chunksize=2))
    df_chunked = pd.concat([ar.to_pandas(c) for c in chunks], ignore_index=True)

    df_scan = ar.to_pandas(ar.scan_csv(str(csv_path)).collect())

    pd.testing.assert_frame_equal(df_read, df_chunked)
    pd.testing.assert_frame_equal(df_read, df_scan)
