"""Tests for diff_schema function in arnio.schema."""
import pytest

from arnio.schema import Field, Schema, SchemaDiff, SchemaDiffEntry, diff_schema


class TestDiffSchema:
    """Test suite for diff_schema function."""

    def test_returns_empty_diff_for_identical_schemas(self):
        """diff_schema returns empty list when schemas are identical."""
        s1 = Schema(fields={"name": Field(dtype="string"), "age": Field(dtype="int")})
        s2 = Schema(fields={"name": Field(dtype="string"), "age": Field(dtype="int")})
        diff = diff_schema(s1, s2)
        assert diff.difference_count == 0
        assert diff.changed is False

    def test_detects_missing_column_in_second_schema(self):
        """diff_schema detects columns missing from second schema."""
        s1 = Schema(fields={"name": Field(dtype="string"), "age": Field(dtype="int")})
        s2 = Schema(fields={"name": Field(dtype="string")})
        diff = diff_schema(s1, s2)
        missing = [d for d in diff.differences if d.change == "missing_column"]
        assert len(missing) == 1
        assert missing[0].column == "age"
        assert missing[0].expected is not None

    def test_detects_extra_column_in_second_schema(self):
        """diff_schema detects extra columns in second schema."""
        s1 = Schema(fields={"name": Field(dtype="string")})
        s2 = Schema(fields={"name": Field(dtype="string"), "age": Field(dtype="int")})
        diff = diff_schema(s1, s2)
        extra = [d for d in diff.differences if d.change == "extra_column"]
        assert len(extra) == 1
        assert extra[0].column == "age"
        assert extra[0].observed is not None

    def test_detects_dtype_change_between_schemas(self):
        """diff_schema detects dtype changes in common columns."""
        s1 = Schema(fields={"age": Field(dtype="int")})
        s2 = Schema(fields={"age": Field(dtype="string")})
        diff = diff_schema(s1, s2)
        changed = [
            d
            for d in diff.differences
            if d.change == "changed_field" and d.attribute == "dtype"
        ]
        assert len(changed) == 1
        assert changed[0].column == "age"
        assert changed[0].expected == "int"
        assert changed[0].observed == "string"

    def test_detects_nullable_change(self):
        """diff_schema detects nullable attribute changes."""
        s1 = Schema(fields={"name": Field(dtype="string", nullable=True)})
        s2 = Schema(fields={"name": Field(dtype="string", nullable=False)})
        diff = diff_schema(s1, s2)
        changed = [
            d
            for d in diff.differences
            if d.change == "changed_field" and d.attribute == "nullable"
        ]
        assert len(changed) == 1
        assert changed[0].column == "name"
        assert changed[0].expected is True
        assert changed[0].observed is False

    def test_detects_strict_flag_change(self):
        """diff_schema detects schema-level strict flag changes."""
        s1 = Schema(fields={"name": Field(dtype="string")}, strict=False)
        s2 = Schema(fields={"name": Field(dtype="string")}, strict=True)
        diff = diff_schema(s1, s2)
        changed = [
            d
            for d in diff.differences
            if d.change == "changed_schema" and d.attribute == "strict"
        ]
        assert len(changed) == 1
        assert changed[0].expected is False
        assert changed[0].observed is True

    def test_detects_unique_flag_change(self):
        """diff_schema detects schema-level unique flag changes."""
        s1 = Schema(fields={"name": Field(dtype="string")}, unique=["name"])
        s2 = Schema(fields={"name": Field(dtype="string")}, unique=None)
        diff = diff_schema(s1, s2)
        changed = [
            d
            for d in diff.differences
            if d.change == "changed_schema" and d.attribute == "unique"
        ]
        assert len(changed) == 1
        assert changed[0].expected == ("name",)
        assert changed[0].observed is None

    def test_accepts_dict_input_for_expected(self):
        """diff_schema accepts dict form of expected schema."""
        expected = {"name": Field(dtype="string")}
        observed = Schema(
            fields={"name": Field(dtype="string"), "age": Field(dtype="int")}
        )
        diff = diff_schema(expected, observed)
        extra = [d for d in diff.differences if d.change == "extra_column"]
        assert len(extra) == 1
        assert extra[0].column == "age"

    def test_accepts_dict_input_for_observed(self):
        """diff_schema accepts dict form of observed schema."""
        expected = Schema(
            fields={"name": Field(dtype="string"), "age": Field(dtype="int")}
        )
        observed = {"name": Field(dtype="string")}
        diff = diff_schema(expected, observed)
        missing = [d for d in diff.differences if d.change == "missing_column"]
        assert len(missing) == 1
        assert missing[0].column == "age"

    def test_accepts_dict_input_for_both(self):
        """diff_schema accepts dict form for both expected and observed."""
        expected = {"name": Field(dtype="string")}
        observed = {"age": Field(dtype="int")}
        diff = diff_schema(expected, observed)
        assert diff.difference_count == 2
        changes = {d.change for d in diff.differences}
        assert changes == {"missing_column", "extra_column"}

    def test_multiple_changed_attributes(self):
        """diff_schema reports all changed attributes for a column."""
        s1 = Schema(fields={"age": Field(dtype="int", nullable=True)})
        s2 = Schema(fields={"age": Field(dtype="string", nullable=False)})
        diff = diff_schema(s1, s2)
        changed = [
            d
            for d in diff.differences
            if d.column == "age" and d.change == "changed_field"
        ]
        assert len(changed) == 2
        attrs = {d.attribute for d in changed}
        assert attrs == {"dtype", "nullable"}

    def test_changed_field_with_only_expected(self):
        """diff_schema handles attribute present only in expected."""
        s1 = Schema(fields={"name": Field(dtype="string", pattern="^[A-Z][a-z]+$")})
        s2 = Schema(fields={"name": Field(dtype="string")})
        diff = diff_schema(s1, s2)
        changed = [
            d
            for d in diff.differences
            if d.column == "name" and d.attribute == "pattern"
        ]
        assert len(changed) == 1
        assert changed[0].expected == "^[A-Z][a-z]+$"
        assert changed[0].observed is None

    def test_changed_field_with_only_observed(self):
        """diff_schema handles attribute present only in observed."""
        s1 = Schema(fields={"name": Field(dtype="string")})
        s2 = Schema(fields={"name": Field(dtype="string", pattern="^[A-Z][a-z]+$")})
        diff = diff_schema(s1, s2)
        changed = [
            d
            for d in diff.differences
            if d.column == "name" and d.attribute == "pattern"
        ]
        assert len(changed) == 1
        assert changed[0].expected is None
        assert changed[0].observed == "^[A-Z][a-z]+$"

    def test_schema_diff_validation_exceptions(self):
        """Check SchemaDiffEntry raises appropriate errors for bad validation paths."""
        with pytest.raises(TypeError, match="change must be a string"):
            SchemaDiffEntry(column="test_col", change=123)

        with pytest.raises(ValueError, match="change cannot be an empty string"):
            SchemaDiffEntry(column="test_col", change="   ")

        with pytest.raises(TypeError, match="column must be a string or None"):
            SchemaDiffEntry(column=123, change="modified")

        with pytest.raises(TypeError, match="attribute must be a string or None"):
            SchemaDiffEntry(column="test_col", change="modified", attribute=123)

        # Test valid instantiation creates entry successfully
        entry = SchemaDiffEntry(column="test_col", change="modified", attribute="dtype")
        assert entry.column == "test_col"
        assert entry.change == "modified"
        assert entry.attribute == "dtype"