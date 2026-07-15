"""Tests for the cleaning engine and Pipeline."""

import pandas as pd
import pytest

import arnio as ar
from arnio.exceptions import CleaningError


class TestCleanBasic:
    """Test ar.clean() basic behavior."""

    def test_strip_whitespace(self):
        df = pd.DataFrame({"name": ["  Alice  ", "  Bob  "]})
        result = ar.clean(df, ["strip_whitespace"])
        assert isinstance(result, pd.DataFrame)
        assert result["name"].tolist() == ["Alice", "Bob"]

    def test_drop_duplicates(self):
        df = pd.DataFrame({"a": [1, 1, 2], "b": [3, 3, 4]})
        result = ar.clean(df, ["drop_duplicates"])
        assert len(result) == 2

    def test_normalize_case_lower(self):
        df = pd.DataFrame({"name": ["ALICE", "BOB"]})
        result = ar.clean(df, [("normalize_case", {"case": "lower"})])
        assert result["name"].tolist() == ["alice", "bob"]

    def test_drop_nulls(self):
        df = pd.DataFrame({"a": [1, None, 3]})
        result = ar.clean(df, ["drop_nulls"])
        assert len(result) == 2

    def test_fill_nulls(self):
        df = pd.DataFrame({"a": [1, None, 3]})
        result = ar.clean(df, [("fill_nulls", {"column": "a", "value": 0})])
        assert result["a"].isna().sum() == 0

    def test_slugify_column_names(self):
        df = pd.DataFrame({"First Name": [1], "Email Address": [2]})
        result = ar.clean(df, ["slugify_column_names"])
        assert list(result.columns) == ["first_name", "email_address"]

    def test_rename_columns(self):
        df = pd.DataFrame({"old": [1]})
        result = ar.clean(df, [("rename_columns", {"mapping": {"old": "new"}})])
        assert "new" in result.columns

    def test_drop_columns(self):
        df = pd.DataFrame({"keep": [1], "drop": [2]})
        result = ar.clean(df, [("drop_columns", {"columns": ["drop"]})])
        assert "drop" not in result.columns

    def test_multiple_steps(self):
        df = pd.DataFrame({"name": ["  ALICE  ", "  ALICE  ", "  BOB  "]})
        result = ar.clean(df, [
            "strip_whitespace",
            ("normalize_case", {"case": "lower"}),
            "drop_duplicates",
        ])
        assert len(result) == 2
        assert result["name"].tolist() == ["alice", "bob"]

    def test_unknown_step_raises(self):
        df = pd.DataFrame({"a": [1]})
        with pytest.raises(CleaningError):
            ar.clean(df, ["nonexistent_step"])

    def test_type_preserved_pandas(self):
        df = pd.DataFrame({"a": [1, 2, 3]})
        result = ar.clean(df, ["drop_duplicates"])
        assert isinstance(result, pd.DataFrame)

    def test_type_preserved_dicts(self):
        data = [{"a": 1}, {"a": 2}]
        result = ar.clean(data, ["drop_duplicates"])
        assert isinstance(result, list)


class TestPipeline:
    """Test ar.Pipeline."""

    def test_pipeline_creation(self):
        pipe = ar.Pipeline([
            "strip_whitespace",
            "drop_duplicates",
            ("normalize_case", {"case": "lower"}),
        ])
        assert len(pipe) == 3

    def test_pipeline_run(self):
        df = pd.DataFrame({"name": ["  ALICE  ", "  BOB  "]})
        pipe = ar.Pipeline(["strip_whitespace", ("normalize_case", {"case": "lower"})])
        result = pipe.run(df)
        assert result["name"].tolist() == ["alice", "bob"]

    def test_pipeline_to_dict(self):
        pipe = ar.Pipeline(["strip_whitespace", "drop_duplicates"])
        d = pipe.to_dict()
        assert "steps" in d
        assert len(d["steps"]) == 2

    def test_pipeline_from_dict(self):
        d = {"steps": [{"name": "strip_whitespace", "params": {}}, {"name": "drop_duplicates", "params": {}}]}
        pipe = ar.Pipeline.from_dict(d)
        assert len(pipe) == 2

    def test_pipeline_json_roundtrip(self):
        pipe = ar.Pipeline(["strip_whitespace", ("normalize_case", {"case": "upper"})])
        json_str = pipe.to_json()
        restored = ar.Pipeline.from_json(json_str)
        assert len(restored) == len(pipe)

    def test_pipeline_repr(self):
        pipe = ar.Pipeline(["strip_whitespace"])
        assert "Pipeline" in repr(pipe)


class TestStepRegistry:
    """Test step registration."""

    def test_list_steps(self):
        steps = ar.list_steps()
        assert "strip_whitespace" in steps
        assert "drop_duplicates" in steps

    def test_register_custom_step(self):
        def my_step(adapter):
            return adapter

        ar.register_step("test_custom", my_step)
        assert "test_custom" in ar.list_steps()
        ar.unregister_step("test_custom")
        assert "test_custom" not in ar.list_steps()

    def test_cannot_overwrite_builtin(self):
        with pytest.raises(CleaningError):
            ar.register_step("strip_whitespace", lambda a: a)

    def test_unregister_unknown_raises(self):
        with pytest.raises(CleaningError):
            ar.unregister_step("nonexistent")

    def test_unregister_builtin_raises(self):
        with pytest.raises(CleaningError):
            ar.unregister_step("strip_whitespace")
