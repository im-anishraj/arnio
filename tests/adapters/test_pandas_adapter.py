"""Tests for the pandas adapter."""

import pandas as pd
import pytest

from arnio.adapt._pandas import PandasAdapter


@pytest.fixture
def adapter() -> PandasAdapter:
    df = pd.DataFrame({
        "name": ["Alice", "Bob", "Charlie", None],
        "age": [25, 30, 35, 40],
        "score": [95.5, 87.3, None, 76.1],
        "active": [True, False, True, True],
    })
    return PandasAdapter(df)


class TestReadOperations:
    def test_column_names(self, adapter: PandasAdapter):
        assert adapter.column_names() == ["name", "age", "score", "active"]

    def test_row_count(self, adapter: PandasAdapter):
        assert adapter.row_count() == 4

    def test_column_dtype_string_like(self, adapter: PandasAdapter):
        # pandas 3.x returns 'string' for string columns, pandas 2.x returns 'object'
        assert adapter.column_dtype("name") in ("object", "string")

    def test_column_dtype_int(self, adapter: PandasAdapter):
        assert adapter.column_dtype("age") == "int64"

    def test_column_dtype_float(self, adapter: PandasAdapter):
        assert adapter.column_dtype("score") == "float64"

    def test_column_dtype_bool(self, adapter: PandasAdapter):
        assert adapter.column_dtype("active") == "bool"

    def test_null_count(self, adapter: PandasAdapter):
        assert adapter.null_count("name") == 1
        assert adapter.null_count("age") == 0
        assert adapter.null_count("score") == 1

    def test_unique_count(self, adapter: PandasAdapter):
        assert adapter.unique_count("name") == 3
        assert adapter.unique_count("age") == 4

    def test_duplicate_count(self, adapter: PandasAdapter):
        assert adapter.duplicate_count() == 0

    def test_duplicate_count_with_dupes(self):
        df = pd.DataFrame({"a": [1, 1, 2], "b": [3, 3, 4]})
        adapter = PandasAdapter(df)
        assert adapter.duplicate_count() == 1

    def test_value_counts(self, adapter: PandasAdapter):
        vc = adapter.value_counts("active")
        assert True in vc
        assert isinstance(vc[True], int)

    def test_values_in_set(self, adapter: PandasAdapter):
        count = adapter.values_in_set("age", {25, 30})
        assert count == 2

    def test_regex_match_count(self, adapter: PandasAdapter):
        count = adapter.regex_match_count("name", r"^[A-Z].*")
        assert count == 3  # Alice, Bob, Charlie

    def test_column_values(self, adapter: PandasAdapter):
        values = adapter.column_values("age")
        assert values == [25, 30, 35, 40]

    def test_numeric_stats(self, adapter: PandasAdapter):
        stats = adapter.numeric_stats("age")
        assert stats.min == 25
        assert stats.max == 40
        assert stats.mean == pytest.approx(32.5)

    def test_string_lengths(self, adapter: PandasAdapter):
        lengths = adapter.string_lengths("name")
        assert lengths.min_length == 3  # "Bob"
        assert lengths.max_length == 7  # "Charlie"

    def test_sample(self, adapter: PandasAdapter):
        sampled = adapter.sample(2)
        assert sampled.row_count() == 2


class TestMutatingOperations:
    """Mutating operations mutate the working copy in place."""

    def test_strip_whitespace(self):
        df = pd.DataFrame({"name": ["  Alice  ", "  Bob  "]})
        adapter = PandasAdapter(df)
        result = adapter.working_copy().strip_whitespace()
        assert result.column_values("name") == ["Alice", "Bob"]
        # Original unchanged because we used working_copy()
        assert adapter.column_values("name") == ["  Alice  ", "  Bob  "]

    def test_normalize_case_lower(self):
        df = pd.DataFrame({"name": ["ALICE", "Bob"]})
        adapter = PandasAdapter(df)
        result = adapter.normalize_case(case="lower")
        assert result.column_values("name") == ["alice", "bob"]

    def test_normalize_case_upper(self):
        df = pd.DataFrame({"name": ["alice", "Bob"]})
        adapter = PandasAdapter(df)
        result = adapter.normalize_case(case="upper")
        assert result.column_values("name") == ["ALICE", "BOB"]

    def test_drop_duplicates(self):
        df = pd.DataFrame({"a": [1, 1, 2], "b": [3, 3, 4]})
        adapter = PandasAdapter(df)
        result = adapter.drop_duplicates()
        assert result.row_count() == 2

    def test_drop_nulls(self):
        df = pd.DataFrame({"a": [1, None, 3], "b": [4, 5, None]})
        adapter = PandasAdapter(df)
        result = adapter.drop_nulls()
        assert result.row_count() == 1

    def test_fill_nulls(self):
        df = pd.DataFrame({"a": [1, None, 3]})
        adapter = PandasAdapter(df)
        result = adapter.fill_nulls("a", 0)
        assert result.null_count("a") == 0

    def test_rename_columns(self, adapter: PandasAdapter):
        result = adapter.rename_columns({"name": "full_name"})
        assert "full_name" in result.column_names()
        assert "name" not in result.column_names()

    def test_drop_columns(self, adapter: PandasAdapter):
        result = adapter.drop_columns(["active"])
        assert "active" not in result.column_names()

    def test_slugify_column_names(self):
        df = pd.DataFrame({"First Name": [1], "Email Address": [2]})
        adapter = PandasAdapter(df)
        result = adapter.slugify_column_names()
        assert result.column_names() == ["first_name", "email_address"]

    def test_replace_values(self):
        df = pd.DataFrame({"status": ["active", "inactive", "active"]})
        adapter = PandasAdapter(df)
        result = adapter.replace_values("status", {"active": "on", "inactive": "off"})
        assert result.column_values("status") == ["on", "off", "on"]

    def test_unwrap_returns_dataframe(self, adapter: PandasAdapter):
        result = adapter.unwrap()
        assert isinstance(result, pd.DataFrame)

    def test_standardize_missing(self):
        df = pd.DataFrame({"a": ["hello", "N/A", "null", "world"]})
        adapter = PandasAdapter(df)
        result = adapter.standardize_missing()
        assert result.null_count("a") == 2
