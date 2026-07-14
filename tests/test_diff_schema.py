"""Tests for diff_schema function in arnio.schema."""

import pytest

from arnio.schema import (
    Field,
    Schema,
    SchemaDiff,
    SchemaDiffEntry,
    diff_schema,
)


def _rule_alpha(df):
    return []


def _rule_beta(df):
    return []


def _make_same_named_rule():
    def same_rule_name(df):
        return []

    return same_rule_name


class _CallableRule:
    def __call__(self, df):
        return []


class _OtherCallableRule:
    def __call__(self, df):
        return []


class TestDiffSchema:
    """Test suite for diff_schema function."""

    def test_returns_empty_diff_for_identical_schemas(self):
        """diff_schema returns empty list when schemas are identical."""
        s1 = Schema(fields={"name": Field(dtype="string"), "age": Field(dtype="int64")})
        s2 = Schema(fields={"name": Field(dtype="string"), "age": Field(dtype="int64")})
        diff = diff_schema(s1, s2)
        assert diff.difference_count == 0
        assert diff.changed is False

    def test_detects_missing_column_in_second_schema(self):
        """diff_schema detects columns missing from second schema."""
        s1 = Schema(fields={"name": Field(dtype="string"), "age": Field(dtype="int64")})
        s2 = Schema(fields={"name": Field(dtype="string")})
        diff = diff_schema(s1, s2)
        missing = [d for d in diff.differences if d.change == "missing_column"]
        assert len(missing) == 1
        assert missing[0].column == "age"
        assert missing[0].expected is not None

    def test_detects_extra_column_in_second_schema(self):
        """diff_schema detects extra columns in second schema."""
        s1 = Schema(fields={"name": Field(dtype="string")})
        s2 = Schema(fields={"name": Field(dtype="string"), "age": Field(dtype="int64")})
        diff = diff_schema(s1, s2)
        extra = [d for d in diff.differences if d.change == "extra_column"]
        assert len(extra) == 1
        assert extra[0].column == "age"
        assert extra[0].observed is not None

    def test_detects_dtype_change_between_schemas(self):
        """diff_schema detects dtype changes in common columns."""
        s1 = Schema(fields={"age": Field(dtype="int64")})
        s2 = Schema(fields={"age": Field(dtype="string")})
        diff = diff_schema(s1, s2)
        changed = [
            d
            for d in diff.differences
            if d.change == "changed_field" and d.attribute == "dtype"
        ]
        assert len(changed) == 1
        assert changed[0].column == "age"
        assert changed[0].expected == "int64"
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

    def test_detects_rules_present_vs_absent(self):
        """diff_schema detects schema-level rules added or removed."""
        expected = Schema(fields={"name": Field(dtype="string")}, rules=[_rule_alpha])
        observed = Schema(fields={"name": Field(dtype="string")})

        diff = diff_schema(expected, observed)
        changed = [
            d
            for d in diff.differences
            if d.change == "changed_schema" and d.attribute == "rules"
        ]

        assert len(changed) == 1
        assert changed[0].column is None
        assert changed[0].expected == ("_rule_alpha",)
        assert changed[0].observed is None

    def test_same_named_rules_are_unchanged(self):
        """diff_schema treats rules with the same visible name as unchanged."""
        expected = Schema(
            fields={"name": Field(dtype="string")},
            rules=[_make_same_named_rule()],
        )
        observed = Schema(
            fields={"name": Field(dtype="string")},
            rules=[_make_same_named_rule()],
        )

        diff = diff_schema(expected, observed)

        assert diff.changed is False
        assert diff.difference_count == 0

    def test_detects_different_rule_names(self):
        """diff_schema detects changed visible rule identities."""
        expected = Schema(fields={"name": Field(dtype="string")}, rules=[_rule_alpha])
        observed = Schema(fields={"name": Field(dtype="string")}, rules=[_rule_beta])

        diff = diff_schema(expected, observed)
        changed = [
            d
            for d in diff.differences
            if d.change == "changed_schema" and d.attribute == "rules"
        ]

        assert len(changed) == 1
        assert changed[0].expected == ("_rule_alpha",)
        assert changed[0].observed == ("_rule_beta",)

    def test_detects_rule_count_changes(self):
        """diff_schema detects rule list length changes."""
        expected = Schema(
            fields={"name": Field(dtype="string")},
            rules=[_rule_alpha, _rule_beta],
        )
        observed = Schema(fields={"name": Field(dtype="string")}, rules=[_rule_alpha])

        diff = diff_schema(expected, observed)
        changed = [
            d
            for d in diff.differences
            if d.change == "changed_schema" and d.attribute == "rules"
        ]

        assert len(changed) == 1
        assert changed[0].expected == ("_rule_alpha", "_rule_beta")
        assert changed[0].observed == ("_rule_alpha",)

    def test_rule_callable_object_fallback_uses_type_name(self):
        """diff_schema names callable rule objects by their callable type."""
        expected = Schema(
            fields={"name": Field(dtype="string")},
            rules=[_CallableRule()],
        )
        observed = Schema(
            fields={"name": Field(dtype="string")},
            rules=[_OtherCallableRule()],
        )

        diff = diff_schema(expected, observed)
        changed = [
            d
            for d in diff.differences
            if d.change == "changed_schema" and d.attribute == "rules"
        ]

        assert len(changed) == 1
        assert changed[0].expected == ("_CallableRule",)
        assert changed[0].observed == ("_OtherCallableRule",)

    def test_rules_difference_renders_in_markdown(self):
        """diff_schema markdown includes schema-level rules differences."""
        expected = Schema(fields={"name": Field(dtype="string")}, rules=[_rule_alpha])
        observed = Schema(fields={"name": Field(dtype="string")})

        markdown = diff_schema(expected, observed).to_markdown()

        assert "|  | changed_schema | rules |" in markdown
        assert "_rule_alpha" in markdown

    def test_accepts_dict_input_for_expected(self):
        """diff_schema accepts dict form of expected schema."""
        expected = {"name": Field(dtype="string")}
        observed = Schema(
            fields={"name": Field(dtype="string"), "age": Field(dtype="int64")}
        )
        diff = diff_schema(expected, observed)
        extra = [d for d in diff.differences if d.change == "extra_column"]
        assert len(extra) == 1
        assert extra[0].column == "age"

    def test_accepts_dict_input_for_observed(self):
        """diff_schema accepts dict form of observed schema."""
        expected = Schema(
            fields={"name": Field(dtype="string"), "age": Field(dtype="int64")}
        )
        observed = {"name": Field(dtype="string")}
        diff = diff_schema(expected, observed)
        missing = [d for d in diff.differences if d.change == "missing_column"]
        assert len(missing) == 1
        assert missing[0].column == "age"

    def test_accepts_dict_input_for_both(self):
        """diff_schema accepts dict form for both expected and observed."""
        expected = {"name": Field(dtype="string")}
        observed = {"age": Field(dtype="int64")}
        diff = diff_schema(expected, observed)
        assert diff.difference_count == 2
        changes = {d.change for d in diff.differences}
        assert changes == {"missing_column", "extra_column"}

    def test_multiple_changed_attributes(self):
        """diff_schema reports all changed attributes for a column."""
        s1 = Schema(fields={"age": Field(dtype="int64", nullable=True)})
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

    def test_severity_warning_to_error(self):
        """diff_schema detects severity change from warning to error."""
        expected = Schema({"age": Field(dtype="int64", severity="warning")})
        observed = Schema({"age": Field(dtype="int64", severity="error")})
        diff = diff_schema(expected, observed)
        assert diff.changed is True
        assert diff.difference_count == 1
        assert diff.differences[0].attribute == "severity"

    def test_severity_error_to_warning(self):
        """diff_schema detects severity change from error to warning."""
        expected = Schema({"age": Field(dtype="int64", severity="error")})
        observed = Schema({"age": Field(dtype="int64", severity="warning")})
        diff = diff_schema(expected, observed)
        assert diff.changed is True
        assert diff.difference_count == 1
        assert diff.differences[0].attribute == "severity"

    def test_schemadiffentry_rejects_invalid_column_type(self):
        with pytest.raises(TypeError):
            SchemaDiffEntry(column=1, change="missing_column")

    def test_schemadiffentry_rejects_invalid_attribute_type(self):
        with pytest.raises(TypeError):
            SchemaDiffEntry(
                column="age",
                change="changed_field",
                attribute=123,
            )

    def test_schemadiffentry_rejects_invalid_change_type(self):
        with pytest.raises(TypeError):
            SchemaDiffEntry(
                column="age",
                change=123,
            )

    def test_schemadiff_rejects_non_list_differences(self):
        with pytest.raises(TypeError):
            SchemaDiff("abc")

    def test_schemadiff_rejects_non_entry_objects(self):
        with pytest.raises(TypeError):
            SchemaDiff([1, 2, 3])
