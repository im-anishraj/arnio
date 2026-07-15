"""Tests for the validation engine."""

import pandas as pd

import arnio as ar


class TestValidateBasic:
    """Test ar.validate() basic behavior."""

    def test_valid_data_passes(self):
        df = pd.DataFrame({"name": ["Alice", "Bob"], "age": [25, 30]})
        schema = ar.Schema({"name": ar.String(), "age": ar.Int()})
        result = ar.validate(df, schema)
        assert result.passed
        assert result.error_count == 0

    def test_missing_column_fails(self):
        df = pd.DataFrame({"name": ["Alice"]})
        schema = ar.Schema({"name": ar.String(), "age": ar.Int()})
        result = ar.validate(df, schema)
        assert not result.passed
        assert any(i.rule == "column_exists" for i in result.issues)

    def test_null_in_non_nullable_fails(self):
        df = pd.DataFrame({"name": ["Alice", None]})
        schema = ar.Schema({"name": ar.String(nullable=False)})
        result = ar.validate(df, schema)
        assert not result.passed
        assert any(i.rule == "not_nullable" for i in result.issues)

    def test_nullable_allows_nulls(self):
        df = pd.DataFrame({"name": ["Alice", None]})
        schema = ar.Schema({"name": ar.String(nullable=True)})
        result = ar.validate(df, schema)
        assert result.passed

    def test_strict_mode_rejects_extra_columns(self):
        df = pd.DataFrame({"name": ["Alice"], "extra": [1]})
        schema = ar.Schema({"name": ar.String()}, strict=True)
        result = ar.validate(df, schema)
        assert not result.passed
        assert any(i.rule == "no_extra_columns" for i in result.issues)

    def test_non_strict_ignores_extra_columns(self):
        df = pd.DataFrame({"name": ["Alice"], "extra": [1]})
        schema = ar.Schema({"name": ar.String()})
        result = ar.validate(df, schema)
        assert result.passed

    def test_dict_schema_accepted(self):
        df = pd.DataFrame({"name": ["Alice"]})
        result = ar.validate(df, {"name": ar.String()})
        assert result.passed


class TestValidateConstraints:
    """Test constraint validation."""

    def test_min_max_int(self):
        df = pd.DataFrame({"age": [25, -5, 200]})
        schema = ar.Schema({"age": ar.Int(min=0, max=150)})
        result = ar.validate(df, schema)
        # -5 and 200 should fail
        value_issues = [i for i in result.issues if i.rule == "value_validation"]
        assert len(value_issues) == 2

    def test_allowed_values(self):
        df = pd.DataFrame({"country": ["US", "UK", "XX"]})
        schema = ar.Schema({"country": ar.String(allowed={"US", "UK", "IN"})})
        result = ar.validate(df, schema)
        assert any(i.rule == "allowed_values" for i in result.issues)

    def test_email_validation(self):
        df = pd.DataFrame({"email": ["valid@test.com", "invalid"]})
        schema = ar.Schema({"email": ar.Email()})
        result = ar.validate(df, schema)
        assert any(i.rule == "value_validation" for i in result.issues)

    def test_uniqueness(self):
        df = pd.DataFrame({"id": [1, 2, 2, 3]})
        schema = ar.Schema({"id": ar.Int(unique=True)})
        result = ar.validate(df, schema)
        assert any(i.rule == "unique" for i in result.issues)

    def test_max_errors_limits_output(self):
        df = pd.DataFrame({"age": [-1, -2, -3, -4, -5]})
        schema = ar.Schema({"age": ar.Int(min=0)})
        result = ar.validate(df, schema, max_errors=2)
        assert result.issue_count <= 2

    def test_mixed_type_numeric_vectorization_robustness(self):
        # Chaos test reproduction: mixed types in Int/Float should not crash vectorization
        df = pd.DataFrame({"age": [20, "invalid_age", 15, None]})
        schema = ar.Schema({"age": ar.Int(min=18)})
        result = ar.validate(df, schema)
        
        issues = result.issues
        # Should catch "invalid_age" as not a number
        assert any("Cannot interpret" in i.message and "invalid_age" in i.message for i in issues)
        # Should catch 15 as less than minimum
        assert any("less than minimum" in i.message for i in issues)

    def test_semantic_field_vectorization(self):
        df = pd.DataFrame({"contact": ["valid@test.com", "bad-email", "https://example.com", "not-a-url"]})
        schema = ar.Schema({"contact": ar.Email()})
        result = ar.validate(df, schema)
        # Ensure it works correctly and the issues are registered
        assert result.issue_count == 3
        
        # Test URL
        schema2 = ar.Schema({"contact": ar.URL()})
        result2 = ar.validate(df, schema2)
        assert result2.issue_count == 3


class TestValidationResult:
    """Test ValidationResult output methods."""

    def test_to_dict(self):
        result = ar.validate(
            pd.DataFrame({"x": [1]}),
            {"x": ar.Int()},
        )
        d = result.to_dict()
        assert "passed" in d
        assert "issues" in d

    def test_to_json(self):
        result = ar.validate(
            pd.DataFrame({"x": [1]}),
            {"x": ar.Int()},
        )
        json_str = result.to_json()
        assert '"passed"' in json_str

    def test_to_markdown(self):
        result = ar.validate(
            pd.DataFrame({"x": ["bad"]}),
            {"x": ar.Int()},
        )
        md = result.to_markdown()
        assert "Validation" in md

    def test_to_html(self):
        result = ar.validate(
            pd.DataFrame({"x": [1]}),
            {"x": ar.Int()},
        )
        html = result.to_html()
        assert "Passed" in html

    def test_to_pandas(self):
        result = ar.validate(
            pd.DataFrame({"x": ["bad"]}),
            {"x": ar.Email()},
        )
        issues_df = result.to_pandas()
        assert isinstance(issues_df, pd.DataFrame)
        assert len(issues_df) > 0

    def test_bool_truthiness(self):
        passed = ar.validate(pd.DataFrame({"x": [1]}), {"x": ar.Int()})
        assert bool(passed) is True

        failed = ar.validate(pd.DataFrame({"x": [None]}), {"x": ar.Int(nullable=False)})
        assert bool(failed) is False

    def test_repr(self):
        result = ar.validate(pd.DataFrame({"x": [1]}), {"x": ar.Int()})
        assert "PASSED" in repr(result)


class TestValidateWithDicts:
    """Test validation with dict input."""

    def test_list_of_dicts(self):
        data = [{"name": "Alice", "age": 25}, {"name": "Bob", "age": 30}]
        schema = ar.Schema({"name": ar.String(), "age": ar.Int()})
        result = ar.validate(data, schema)
        assert result.passed
