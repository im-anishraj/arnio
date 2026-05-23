"""Tests for diff_schema function in arnio.schema."""

import pytest
from arnio.schema import Schema, Field, diff_schema, SchemaDiffEntry


class TestDiffSchema:
    """Test suite for diff_schema function."""

    def test_returns_empty_diff_for_identical_schemas(self):
        """diff_schema returns empty list when schemas are identical."""
        s1 = Schema().add("name", dtype="string").add("age", dtype="int")
        s2 = Schema().add("name", dtype="string").add("age", dtype="int")
        diff = diff_schema(s1, s2)
        assert len(diff) == 0

    def test_detects_missing_column_in_second_schema(self):
        """diff_schema detects columns missing from second schema."""
        s1 = Schema().add("name", dtype="string").add("age", dtype="int")
        s2 = Schema().add("name", dtype="string")
        diff = diff_schema(s1, s2)
        missing = [d for d in diff if d.change == "missing_column"]
        assert len(missing) == 1
        assert missing[0].column == "age"
        assert missing[0].expected is not None

    def test_detects_extra_column_in_second_schema(self):
        """diff_schema detects extra columns in second schema."""
        s1 = Schema().add("name", dtype="string")
        s2 = Schema().add("name", dtype="string").add("age", dtype="int")
        diff = diff_schema(s1, s2)
        extra = [d for d in diff if d.change == "extra_column"]
        assert len(extra) == 1
        assert extra[0].column == "age"
        assert extra[0].observed is not None

    def test_detects_dtype_change_between_schemas(self):
        """diff_schema detects dtype changes in common columns."""
        s1 = Schema().add("age", dtype="int")
        s2 = Schema().add("age", dtype="string")
        diff = diff_schema(s1, s2)
        changed = [d for d in diff if d.change == "changed_field" and d.attribute == "dtype"]
        assert len(changed) == 1
        assert changed[0].column == "age"
        assert changed[0].expected == "int"
        assert changed[0].observed == "string"

    def test_detects_nullable_change(self):
        """diff_schema detects nullable attribute changes."""
        s1 = Schema().add("name", dtype="string", nullable=True)
        s2 = Schema().add("name", dtype="string", nullable=False)
        diff = diff_schema(s1, s2)
        changed = [d for d in diff if d.change == "changed_field" and d.attribute == "nullable"]
        assert len(changed) == 1
        assert changed[0].column == "name"

    def test_detects_strict_flag_change(self):
        """diff_schema detects schema-level strict flag changes."""
        s1 = Schema(strict=False)
        s2 = Schema(strict=True)
        diff = diff_schema(s1, s2)
        changed = [d for d in diff if d.change == "changed_schema" and d.attribute == "strict"]
        assert len(changed) == 1
        assert changed[0].expected is False
        assert changed[0].observed is True

    def test_detects_unique_flag_change(self):
        """diff_schema detects schema-level unique flag changes."""
        s1 = Schema(unique=False)
        s2 = Schema(unique=True)
        diff = diff_schema(s1, s2)
        changed = [d for d in diff if d.change == "changed_schema" and d.attribute == "unique"]
        assert len(changed) == 1
        assert changed[0].expected is False
        assert changed[0].observed is True

    def test_accepts_dict_input_for_expected(self):
        """diff_schema accepts dict form of expected schema."""
        expected = {"name": Field(dtype="string")}
        observed = Schema().add("name", dtype="string").add("age", dtype="int")
        diff = diff_schema(expected, observed)
        extra = [d for d in diff if d.change == "extra_column"]
        assert len(extra) == 1
        assert extra[0].column == "age"

    def test_accepts_dict_input_for_observed(self):
        """diff_schema accepts dict form of observed schema."""
        expected = Schema().add("name", dtype="string").add("age", dtype="int")
        observed = {"name": Field(dtype="string")}
        diff = diff_schema(expected, observed)
        missing = [d for d in diff if d.change == "missing_column"]
        assert len(missing) == 1
        assert missing[0].column == "age"

    def test_accepts_dict_input_for_both(self):
        """diff_schema accepts dict form for both expected and observed."""
        expected = {"name": Field(dtype="string")}
        observed = {"age": Field(dtype="int")}
        diff = diff_schema(expected, observed)
        assert len(diff) == 2
        changes = {d.change for d in diff}
        assert changes == {"missing_column", "extra_column"}

    def test_multiple_changed_attributes(self):
        """diff_schema reports all changed attributes for a column."""
        s1 = Schema().add("age", dtype="int", nullable=True)
        s2 = Schema().add("age", dtype="string", nullable=False)
        diff = diff_schema(s1, s2)
        changed = [d for d in diff if d.column == "age" and d.change == "changed_field"]
        assert len(changed) == 2
        attrs = {d.attribute for d in changed}
        assert attrs == {"dtype", "nullable"}

    def test_changed_field_with_only_expected(self):
        """diff_schema handles attribute present only in expected."""
        s1 = Schema().add("name", dtype="string", description="The name")
        s2 = Schema().add("name", dtype="string")
        diff = diff_schema(s1, s2)
        changed = [d for d in diff if d.column == "name" and d.attribute == "description"]
        assert len(changed) == 1

    def test_changed_field_with_only_observed(self):
        """diff_schema handles attribute present only in observed."""
        s1 = Schema().add("name", dtype="string")
        s2 = Schema().add("name", dtype="string", description="The name")
        diff = diff_schema(s1, s2)
        changed = [d for d in diff if d.column == "name" and d.attribute == "description"]
        assert len(changed) == 1