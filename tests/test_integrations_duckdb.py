"""Tests for DuckDB integration helpers."""

import pytest

import arnio as ar


def test_register_duckdb_basic():
    duckdb = pytest.importorskip("duckdb")
    import pandas as pd

    df = pd.DataFrame({"name": ["Alice", "Bob"], "age": [25, 30]})
    frame = ar.from_pandas(df)
    conn = duckdb.connect()

    ar.register_duckdb(frame, conn, "users")
    result = conn.execute("SELECT * FROM users").fetchdf()

    assert list(result.columns) == ["name", "age"]
    assert len(result) == 2


def test_register_duckdb_invalid_frame():
    duckdb = pytest.importorskip("duckdb")
    conn = duckdb.connect()

    with pytest.raises(TypeError):
        ar.register_duckdb("not_a_frame", conn, "test")


def test_register_duckdb_empty_name():
    duckdb = pytest.importorskip("duckdb")
    import pandas as pd

    frame = ar.from_pandas(pd.DataFrame({"a": [1]}))
    conn = duckdb.connect()

    with pytest.raises(ValueError):
        ar.register_duckdb(frame, conn, "")


def test_register_duckdb_invalid_connection_object():
    import pandas as pd

    frame = ar.from_pandas(pd.DataFrame({"a": [1]}))

    with pytest.raises(
        TypeError,
        match="conn must be a DuckDB connection with a callable register\\(\\) method",
    ):
        ar.register_duckdb(frame, object(), "tbl")


def test_register_duckdb_none_connection():
    import pandas as pd

    frame = ar.from_pandas(pd.DataFrame({"a": [1]}))

    with pytest.raises(
        TypeError,
        match="conn must be a DuckDB connection with a callable register\\(\\) method",
    ):
        ar.register_duckdb(frame, None, "tbl")


def test_register_duckdb_noncallable_register_attribute():
    import pandas as pd

    class FakeConnection:
        register = 123

    frame = ar.from_pandas(pd.DataFrame({"a": [1]}))

    with pytest.raises(
        TypeError,
        match="conn must be a DuckDB connection with a callable register\\(\\) method",
    ):
        ar.register_duckdb(frame, FakeConnection(), "tbl")


def test_register_duckdb_whitespace_only_name_space():
    import pandas as pd

    class FakeConnection:
        def register(self, name, df):
            pass

    frame = ar.from_pandas(pd.DataFrame({"a": [1]}))

    with pytest.raises(ValueError, match="whitespace-only"):
        ar.register_duckdb(frame, FakeConnection(), " ")


def test_register_duckdb_whitespace_only_name_tab():
    import pandas as pd

    class FakeConnection:
        def register(self, name, df):
            pass

    frame = ar.from_pandas(pd.DataFrame({"a": [1]}))

    with pytest.raises(ValueError, match="whitespace-only"):
        ar.register_duckdb(frame, FakeConnection(), "\t")


def test_register_duckdb_whitespace_only_name_newline():
    import pandas as pd

    class FakeConnection:
        def register(self, name, df):
            pass

    frame = ar.from_pandas(pd.DataFrame({"a": [1]}))

    with pytest.raises(ValueError, match="whitespace-only"):
        ar.register_duckdb(frame, FakeConnection(), "\n")


def test_register_duckdb_valid_name_passes():
    import pandas as pd

    registered = {}

    class FakeConnection:
        def register(self, name, df):
            registered["name"] = name

    frame = ar.from_pandas(pd.DataFrame({"a": [1]}))
    ar.register_duckdb(frame, FakeConnection(), "my_table")

    assert registered["name"] == "my_table"
