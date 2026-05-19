import pytest

import arnio as ar


def test_invalid_utf8_raises_csv_read_error(tmp_path):
    p = tmp_path / "bad_utf8.csv"
    p.write_bytes(b"name\n\xff\n")
    with pytest.raises(ar.CsvReadError, match="invalid byte sequence"):
        ar.read_csv(p, encoding="utf-8")


def test_invalid_utf8_error_contains_path(tmp_path):
    p = tmp_path / "bad_utf8.csv"
    p.write_bytes(b"name\n\xff\n")
    with pytest.raises(ar.CsvReadError, match=str(p)):
        ar.read_csv(p, encoding="utf-8")


def test_valid_utf8_passes(tmp_path):
    p = tmp_path / "good.csv"
    p.write_bytes("name\n\xe9\xe0\xfc\n".encode())
    frame = ar.read_csv(p, encoding="utf-8")
    assert frame.shape[0] == 1


def test_bom_utf8_sig_passes(tmp_path):
    p = tmp_path / "bom.csv"
    p.write_bytes("name\nhello\n".encode("utf-8-sig"))
    frame = ar.read_csv(p, encoding="utf-8-sig")
    assert frame.shape[0] == 1


def test_non_utf8_encoding_not_validated(tmp_path):
    """latin-1 bytes must not trigger the UTF-8 validator."""
    p = tmp_path / "latin1.csv"
    p.write_bytes(b"name\n\xe9\n")  # é in latin-1
    frame = ar.read_csv(p, encoding="latin-1")
    assert frame.shape[0] == 1


def test_scan_csv_invalid_utf8_raises(tmp_path):
    p = tmp_path / "bad_utf8.csv"
    p.write_bytes(b"name\n\xff\n")
    try:
        ar.scan_csv(p, encoding="utf-8")
    except TypeError:
        pytest.skip("scan_csv does not accept encoding parameter")
    except ar.CsvReadError as exc:
        assert "invalid byte sequence" in str(exc)
    else:
        pytest.fail("Expected CsvReadError was not raised")
