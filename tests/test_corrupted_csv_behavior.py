import pytest

import arnio as ar
from arnio import CsvReadError


def test_strict_mode_rejects_extra_columns(tmp_path):
    path = tmp_path / "extra_columns.csv"
    path.write_text("name,age\nAlice,22\nBob,25,extra\n", encoding="utf-8")

    with pytest.raises(CsvReadError):
        ar.read_csv(path, mode="strict")


def test_permissive_mode_handles_missing_trailing_fields(tmp_path):
    path = tmp_path / "missing_field.csv"
    path.write_text("name,age,city\nAlice,22,Kolkata\nBob,25\n", encoding="utf-8")

    frame = ar.read_csv(path, mode="permissive")
    df = ar.to_pandas(frame)

    assert list(df.columns) == ["name", "age", "city"]
    assert df.loc[1, "name"] == "Bob"


def test_malformed_quote_behavior_uses_parser(tmp_path):
    path = tmp_path / "malformed_quote.csv"
    path.write_text('name,comment\nAlice,"hello\nBob,world\n', encoding="utf-8")

    with pytest.raises(CsvReadError):
        ar.read_csv(path, mode="strict")


def test_encoding_error_is_reported(tmp_path):
    path = tmp_path / "invalid_utf8.csv"
    path.write_bytes(b"name,comment\nAlice,\xff\n")

    with pytest.raises(CsvReadError):
        ar.read_csv(path, encoding="utf-8", encoding_errors="strict")


def test_encoding_replace_allows_invalid_bytes(tmp_path):
    path = tmp_path / "replace_invalid_utf8.csv"
    path.write_bytes(b"name,comment\nAlice,\xff\n")

    frame = ar.read_csv(path, encoding="utf-8", encoding_errors="replace")
    df = ar.to_pandas(frame)

    assert df.loc[0, "name"] == "Alice"


def test_scan_csv_rejects_corrupted_input(tmp_path):
    path = tmp_path / "corrupted.csv"
    path.write_bytes(b"name,age\nAlice,\x0022\n")

    with pytest.raises(CsvReadError):
        ar.scan_csv(path)
