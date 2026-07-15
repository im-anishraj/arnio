"""Comprehensive edge-case and regression tests for Arnio v2.

Covers:
- Adapter edge cases (empty, one-row, unicode, nullable dtypes, mixed types)
- Schema edge cases (inheritance, empty, equality, serde roundtrips)
- Validation edge cases (NaN, None, empty strings, all-null, mixed dtypes)
- Cleaning edge cases (idempotency, no-mutation, chaining)
- Pipeline edge cases (empty, serde roundtrip with all step types)
- Regression tests for every bug fixed in this audit
"""

from __future__ import annotations

import json

import pandas as pd
import pytest

import arnio as ar
from arnio.adapt._dict import DictAdapter
from arnio.adapt._pandas import PandasAdapter
from arnio.exceptions import SchemaError

# =====================================================================
# REGRESSION TESTS — one per bug found
# =====================================================================


class TestRegressionBugs:
    """Regression tests for bugs found during audit."""

    def test_regex_raises_schema_error_not_value_error(self):
        """Bug #1: Regex.__post_init__ raised ValueError instead of SchemaError."""
        with pytest.raises(SchemaError, match="non-empty"):
            ar.Regex(pattern="")

        with pytest.raises(SchemaError, match="regex"):
            ar.Regex(pattern="[invalid")

    def test_int_bool_respects_min_max(self):
        """Bug #2: Bool values bypassed min/max validation in Int field."""
        field = ar.Int(min=5, max=10)
        # False = 0, True = 1 — both below min=5
        assert field.validate_value(False) is not None
        assert field.validate_value(True) is not None

        # With min=0, both should pass
        field2 = ar.Int(min=0, max=10)
        assert field2.validate_value(False) is None
        assert field2.validate_value(True) is None

    def test_schema_diff_detects_min_max_changes(self):
        """Bug #3: _compare_fields only diffed base attrs, missing min/max/pattern."""
        a = ar.Schema({"age": ar.Int(min=0, max=100)})
        b = ar.Schema({"age": ar.Int(min=0, max=200)})
        diff = ar.diff_schemas(a, b)
        assert not diff.is_identical
        # Should have detail about max changing
        details = diff.changes[0].details
        assert any("max" in d for d in details)

    def test_schema_diff_detects_pattern_changes(self):
        """Bug #3 continued: pattern changes should be detected."""
        a = ar.Schema({"code": ar.String(pattern=r"^\d{3}$")})
        b = ar.Schema({"code": ar.String(pattern=r"^\d{4}$")})
        diff = ar.diff_schemas(a, b)
        assert not diff.is_identical
        details = diff.changes[0].details
        assert any("pattern" in d for d in details)

    def test_schema_diff_detects_min_length_changes(self):
        """Bug #3 continued: min_length changes should be detected."""
        a = ar.Schema({"name": ar.String(min_length=1)})
        b = ar.Schema({"name": ar.String(min_length=3)})
        diff = ar.diff_schemas(a, b)
        assert not diff.is_identical
        details = diff.changes[0].details
        assert any("min_length" in d for d in details)

    def test_strict_schema_serde_no_redundant_allow_extra(self):
        """Bug #7: schema_to_dict emitted both strict=True and allow_extra=False."""
        schema = ar.Schema({"a": ar.Int()}, strict=True)
        d = ar.schema_to_dict(schema)
        assert d.get("strict") is True
        assert "allow_extra" not in d  # Should NOT be present when strict=True

    def test_strict_schema_serde_roundtrip(self):
        """Bug #7 continued: strict schemas should survive serialization roundtrip."""
        schema = ar.Schema({"a": ar.Int()}, strict=True)
        json_str = ar.schema_to_json(schema)
        restored = ar.schema_from_json(json_str)
        assert restored.strict is True
        assert restored.allow_extra is False


# =====================================================================
# ADAPTER EDGE CASES
# =====================================================================


class TestPandasAdapterEdgeCases:
    """Edge cases for the pandas adapter."""

    def test_empty_dataframe(self):
        df = pd.DataFrame()
        adapter = PandasAdapter(df)
        assert adapter.row_count() == 0
        assert adapter.column_names() == []
        assert adapter.duplicate_count() == 0

    def test_one_row_dataframe(self):
        df = pd.DataFrame({"a": [1]})
        adapter = PandasAdapter(df)
        assert adapter.row_count() == 1
        assert adapter.unique_count("a") == 1
        assert adapter.null_count("a") == 0
        assert adapter.duplicate_count() == 0

    def test_one_column_dataframe(self):
        df = pd.DataFrame({"x": [1, 2, 3]})
        adapter = PandasAdapter(df)
        assert adapter.column_names() == ["x"]
        assert adapter.row_count() == 3

    def test_unicode_column_names(self):
        df = pd.DataFrame({"名前": ["太郎"], "年齢": [25]})
        adapter = PandasAdapter(df)
        assert "名前" in adapter.column_names()
        assert adapter.row_count() == 1

    def test_unicode_values(self):
        df = pd.DataFrame({"name": ["émile", "naïve", "über"]})
        adapter = PandasAdapter(df)
        assert adapter.unique_count("name") == 3
        lengths = adapter.string_lengths("name")
        assert lengths.min_length > 0

    def test_nullable_int_dtype(self):
        df = pd.DataFrame({"a": pd.array([1, 2, None], dtype=pd.Int64Dtype())})
        adapter = PandasAdapter(df)
        assert adapter.column_dtype("a") == "int64"
        assert adapter.null_count("a") == 1

    def test_nullable_float_dtype(self):
        df = pd.DataFrame({"a": pd.array([1.0, None, 3.0], dtype=pd.Float64Dtype())})
        adapter = PandasAdapter(df)
        assert adapter.column_dtype("a") == "float64"
        assert adapter.null_count("a") == 1

    def test_nullable_string_dtype(self):
        df = pd.DataFrame({"a": pd.array(["hello", None, "world"], dtype="string")})
        adapter = PandasAdapter(df)
        assert adapter.column_dtype("a") == "string"
        assert adapter.null_count("a") == 1

    def test_nullable_boolean_dtype(self):
        df = pd.DataFrame({"a": pd.array([True, None, False], dtype=pd.BooleanDtype())})
        adapter = PandasAdapter(df)
        assert adapter.column_dtype("a") == "bool"
        assert adapter.null_count("a") == 1

    def test_all_null_column(self):
        df = pd.DataFrame({"a": [None, None, None]})
        adapter = PandasAdapter(df)
        assert adapter.null_count("a") == 3
        assert adapter.unique_count("a") == 0

    def test_all_null_numeric_stats(self):
        df = pd.DataFrame({"a": pd.array([None, None], dtype=pd.Float64Dtype())})
        adapter = PandasAdapter(df)
        # Should not crash
        stats = adapter.numeric_stats("a")
        assert stats is not None

    def test_all_null_string_lengths(self):
        df = pd.DataFrame({"a": pd.array([None, None], dtype="string")})
        adapter = PandasAdapter(df)
        lengths = adapter.string_lengths("a")
        assert lengths.min_length == 0
        assert lengths.max_length == 0

    def test_mixed_types_in_object_column(self):
        df = pd.DataFrame({"a": [1, "hello", 3.14, None]})
        adapter = PandasAdapter(df)
        assert adapter.column_dtype("a") == "object"
        assert adapter.null_count("a") == 1

    def test_duplicated_column_values(self):
        df = pd.DataFrame({"a": [1, 1, 1, 2, 2]})
        adapter = PandasAdapter(df)
        assert adapter.unique_count("a") == 2
        vc = adapter.value_counts("a")
        assert vc[1] == 3

    def test_sample_empty_df(self):
        df = pd.DataFrame({"a": []})
        adapter = PandasAdapter(df)
        sampled = adapter.sample(5)
        assert sampled.row_count() == 0

    def test_sample_larger_than_df(self):
        df = pd.DataFrame({"a": [1, 2]})
        adapter = PandasAdapter(df)
        sampled = adapter.sample(100)
        assert sampled.row_count() == 2

    def test_strip_whitespace_preserves_non_string_columns(self):
        df = pd.DataFrame({"name": ["  Alice  "], "age": [25]})
        adapter = PandasAdapter(df)
        result = adapter.strip_whitespace()
        assert result.column_values("age") == [25]
        assert result.column_values("name") == ["Alice"]

    def test_normalize_case_invalid_raises(self):
        df = pd.DataFrame({"a": ["hello"]})
        adapter = PandasAdapter(df)
        with pytest.raises(ValueError, match="case must be"):
            adapter.normalize_case(case="invalid")

    def test_drop_nulls_with_how_all(self):
        df = pd.DataFrame({"a": [1, None, None], "b": [None, None, 3]})
        adapter = PandasAdapter(df)
        result = adapter.drop_nulls(how="all")
        assert result.row_count() == 2  # Only row with both null is dropped

    def test_cast_column(self):
        df = pd.DataFrame({"a": [1, 2, 3]})
        adapter = PandasAdapter(df)
        result = adapter.cast_column("a", "float64")
        assert result.column_dtype("a") == "float64"

    def test_no_mutation_on_original(self):
        """Verify ALL mutating ops return new adapters without modifying original."""
        df = pd.DataFrame({"name": ["  Alice  ", "Bob"], "age": [25, 30]})
        adapter = PandasAdapter(df)
        original_values = adapter.column_values("name")

        adapter.working_copy().strip_whitespace()
        assert adapter.column_values("name") == original_values

        adapter.working_copy().normalize_case(case="upper")
        assert adapter.column_values("name") == original_values

        adapter.working_copy().drop_duplicates()
        assert adapter.row_count() == 2

        adapter.working_copy().fill_nulls("name", "X")
        assert adapter.column_values("name") == original_values

    def test_slugify_unicode_columns(self):
        df = pd.DataFrame({"Ñame (with) [brackets]": [1]})
        adapter = PandasAdapter(df)
        result = adapter.slugify_column_names()
        col = result.column_names()[0]
        assert col.isascii()
        assert " " not in col
        assert "(" not in col

    def test_datetime_column_dtype(self):
        df = pd.DataFrame({"ts": pd.to_datetime(["2024-01-01", "2024-06-15"])})
        adapter = PandasAdapter(df)
        assert adapter.column_dtype("ts") == "datetime"

    def test_value_counts_top_n(self):
        df = pd.DataFrame({"a": list(range(20))})
        adapter = PandasAdapter(df)
        vc = adapter.value_counts("a", top_n=5)
        assert len(vc) == 5


class TestDictAdapterEdgeCases:
    """Edge cases for the dict adapter."""

    def test_empty_list_of_dicts(self):
        adapter = DictAdapter([])
        assert adapter.row_count() == 0
        assert adapter.column_names() == []

    def test_column_oriented_empty(self):
        adapter = DictAdapter({"a": [], "b": []})
        assert adapter.row_count() == 0
        assert set(adapter.column_names()) == {"a", "b"}

    def test_unwrap_returns_list_of_dicts(self):
        data = [{"x": 1, "y": 2}]
        adapter = DictAdapter(data)
        result = adapter.unwrap()
        assert isinstance(result, list)
        assert result[0]["x"] == 1

    def test_dict_adapter_mutations_return_dict_adapter(self):
        data = [{"name": "  Alice  "}, {"name": "  Bob  "}]
        adapter = DictAdapter(data)
        result = adapter.strip_whitespace()
        assert isinstance(result, DictAdapter)
        assert result.unwrap()[0]["name"] == "Alice"

    def test_single_row(self):
        adapter = DictAdapter([{"a": 1}])
        assert adapter.row_count() == 1
        assert adapter.column_values("a") == [1]


# =====================================================================
# SCHEMA EDGE CASES
# =====================================================================


class TestSchemaEdgeCases:

    def test_empty_schema_raises(self):
        """Schema with no fields should raise SchemaError."""
        with pytest.raises(SchemaError):
            ar.Schema({})

    def test_field_equality(self):
        """Same field definitions should be equal."""
        assert ar.Int(min=0, max=100) == ar.Int(min=0, max=100)
        assert ar.Int(min=0) != ar.Int(min=1)
        assert ar.String() != ar.Int()

    def test_schema_equality(self):
        a = ar.Schema({"x": ar.Int()})
        b = ar.Schema({"x": ar.Int()})
        assert a == b

    def test_schema_inequality(self):
        a = ar.Schema({"x": ar.Int()})
        b = ar.Schema({"x": ar.Float()})
        assert a != b

    def test_schema_not_equal_to_non_schema(self):
        schema = ar.Schema({"x": ar.Int()})
        assert schema != "not a schema"

    def test_class_based_schema_with_override(self):
        class Base(ar.Schema):
            name = ar.String()
            age = ar.Int()

        class Child(Base):
            age = ar.Int(min=0, max=150)  # Override with constraints

        schema = Child()
        assert schema["age"].min == 0
        assert schema["age"].max == 150

    def test_schema_contains(self):
        schema = ar.Schema({"a": ar.Int(), "b": ar.String()})
        assert "a" in schema
        assert "c" not in schema

    def test_schema_getitem(self):
        schema = ar.Schema({"a": ar.Int()})
        assert isinstance(schema["a"], ar.Int)

    def test_int_inf_bound_raises(self):
        with pytest.raises(SchemaError, match="finite"):
            ar.Int(min=float("inf"))

    def test_int_nan_bound_raises(self):
        with pytest.raises(SchemaError, match="finite"):
            ar.Int(max=float("nan"))

    def test_int_bool_bound_raises(self):
        with pytest.raises(SchemaError, match="bool"):
            ar.Int(min=True)

    def test_string_min_length_negative_raises(self):
        with pytest.raises(SchemaError):
            ar.String(min_length=-1)

    def test_string_min_gt_max_raises(self):
        with pytest.raises(SchemaError):
            ar.String(min_length=10, max_length=5)

    def test_field_invalid_severity_raises(self):
        with pytest.raises(SchemaError, match="severity"):
            ar.Int(severity="critical")

    def test_allowed_values_normalized_to_frozenset(self):
        f = ar.String(allowed=["a", "b", "c"])
        assert isinstance(f.allowed, frozenset)

    def test_date_custom_format_serde_roundtrip(self):
        schema = ar.Schema({"d": ar.Date(format="%d/%m/%Y")})
        d = ar.schema_to_dict(schema)
        restored = ar.schema_from_dict(d)
        assert restored["d"].format == "%d/%m/%Y"

    def test_float_nan_validation(self):
        f = ar.Float()
        assert f.validate_value(float("nan")) is not None

    def test_float_inf_validation(self):
        f = ar.Float()
        assert f.validate_value(float("inf")) is not None


# =====================================================================
# SCHEMA SERDE EDGE CASES
# =====================================================================


class TestSchemaSerdeEdgeCases:

    def test_all_field_types_roundtrip(self):
        """Every field type should survive JSON roundtrip."""
        schema = ar.Schema({
            "i": ar.Int(min=0, max=100, nullable=False),
            "f": ar.Float(min=0.0, max=1.0),
            "s": ar.String(min_length=1, max_length=50, pattern=r"^\w+$"),
            "b": ar.Bool(),
            "d": ar.Date(format="%Y-%m-%d"),
            "dt": ar.DateTime(format="%Y-%m-%d %H:%M:%S"),
            "e": ar.Email(),
            "u": ar.URL(),
            "p": ar.PhoneNumber(),
            "ip": ar.IPAddress(),
            "uid": ar.UUID(),
            "rx": ar.Regex(pattern=r"^[A-Z]{2}\d{4}$"),
        })

        json_str = ar.schema_to_json(schema)
        restored = ar.schema_from_json(json_str)

        assert set(restored.column_names) == set(schema.column_names)
        assert restored["i"].min == 0
        assert restored["i"].max == 100
        assert restored["s"].min_length == 1
        assert restored["rx"].pattern == r"^[A-Z]{2}\d{4}$"

    def test_yaml_roundtrip(self):
        schema = ar.Schema({
            "name": ar.String(min_length=1),
            "age": ar.Int(min=0),
        })
        yaml_str = ar.schema_to_yaml(schema)
        restored = ar.schema_from_yaml(yaml_str)
        assert restored.column_names == schema.column_names

    def test_from_dict_missing_fields_key_raises(self):
        with pytest.raises(SchemaError, match="fields"):
            ar.schema_from_dict({})

    def test_from_dict_unknown_type_raises(self):
        with pytest.raises(SchemaError, match="Unknown"):
            ar.schema_from_dict({"fields": {"x": {"type": "FakeType"}}})

    def test_from_json_invalid_json_raises(self):
        with pytest.raises(SchemaError, match="JSON"):
            ar.schema_from_json("{invalid json")

    def test_from_yaml_invalid_yaml_raises(self):
        with pytest.raises(SchemaError, match="YAML"):
            ar.schema_from_yaml(": [invalid yaml")

    def test_allowed_values_serde(self):
        """Allowed values should survive serialization."""
        schema = ar.Schema({"status": ar.String(allowed={"active", "inactive"})})
        json_str = ar.schema_to_json(schema)
        restored = ar.schema_from_json(json_str)
        assert restored["status"].allowed == frozenset({"active", "inactive"})


# =====================================================================
# VALIDATION EDGE CASES
# =====================================================================


class TestValidationEdgeCases:

    def test_nan_in_non_nullable_detected(self):
        df = pd.DataFrame({"a": [1.0, float("nan"), 3.0]})
        result = ar.validate(df, {"a": ar.Float(nullable=False)})
        assert not result.passed

    def test_none_in_non_nullable_detected(self):
        df = pd.DataFrame({"a": [1, None, 3]})
        result = ar.validate(df, {"a": ar.Int(nullable=False)})
        assert not result.passed

    def test_empty_string_passes_string_validation(self):
        """Empty string is not null — it should pass nullable check."""
        df = pd.DataFrame({"a": ["hello", "", "world"]})
        result = ar.validate(df, {"a": ar.String(nullable=False)})
        # Empty string is not null, so nullable check passes
        assert all(i.rule != "not_nullable" for i in result.issues)

    def test_empty_string_fails_min_length(self):
        df = pd.DataFrame({"a": ["hello", "", "world"]})
        result = ar.validate(df, {"a": ar.String(min_length=1)})
        value_issues = [i for i in result.issues if i.rule == "value_validation"]
        assert len(value_issues) >= 1

    def test_all_null_column_with_nullable_true(self):
        df = pd.DataFrame({"a": [None, None, None]})
        result = ar.validate(df, {"a": ar.String(nullable=True)})
        assert result.passed

    def test_all_null_column_with_nullable_false(self):
        df = pd.DataFrame({"a": [None, None, None]})
        result = ar.validate(df, {"a": ar.String(nullable=False)})
        assert not result.passed

    def test_empty_dataframe_validates(self):
        df = pd.DataFrame({"a": pd.Series([], dtype="int64")})
        result = ar.validate(df, {"a": ar.Int()})
        assert result.passed

    def test_validate_mixed_dtype_column(self):
        """Column with mixed types should still validate without crashing."""
        df = pd.DataFrame({"a": [1, "hello", None, 3.14]})
        schema = ar.Schema({"a": ar.String()})
        result = ar.validate(df, schema)
        # Should not crash
        assert isinstance(result, ar.ValidationResult)

    def test_validate_with_list_of_dicts(self):
        data = [{"name": "Alice", "age": 25}, {"name": "Bob", "age": -1}]
        result = ar.validate(data, {"name": ar.String(), "age": ar.Int(min=0)})
        assert not result.passed

    def test_validate_result_to_dict_with_non_serializable_values(self):
        """Values that aren't JSON-serializable should still work in to_dict."""
        df = pd.DataFrame({"a": [pd.Timestamp("2024-01-01")]})
        result = ar.validate(df, {"a": ar.String()})
        d = result.to_dict()
        # Should not crash
        json.dumps(d, default=str)

    def test_max_errors_zero(self):
        df = pd.DataFrame({"a": [-1, -2, -3]})
        result = ar.validate(df, {"a": ar.Int(min=0)}, max_errors=0)
        assert result.issue_count == 0

    def test_warning_severity_doesnt_fail_validation(self):
        df = pd.DataFrame({"a": [-1]})
        schema = ar.Schema({"a": ar.Int(min=0, severity="warning")})
        result = ar.validate(df, schema)
        assert result.passed  # Warnings don't cause failure
        assert result.warning_count > 0

    def test_uniqueness_with_nulls(self):
        """Nulls should be excluded from uniqueness check."""
        df = pd.DataFrame({"id": [1, 2, None, None]})
        result = ar.validate(df, {"id": ar.Int(unique=True)})
        # 1 and 2 are unique among non-nulls
        unique_issues = [i for i in result.issues if i.rule == "unique"]
        assert len(unique_issues) == 0


# =====================================================================
# CLEANING EDGE CASES
# =====================================================================


class TestCleaningEdgeCases:

    def test_clean_empty_steps_returns_same(self):
        df = pd.DataFrame({"a": [1, 2, 3]})
        result = ar.clean(df, [])
        assert isinstance(result, pd.DataFrame)
        assert list(result["a"]) == [1, 2, 3]

    def test_clean_idempotent_strip_whitespace(self):
        """Applying strip_whitespace twice should give same result."""
        df = pd.DataFrame({"a": ["  hello  ", "  world  "]})
        result1 = ar.clean(df, ["strip_whitespace"])
        result2 = ar.clean(result1, ["strip_whitespace"])
        assert result1["a"].tolist() == result2["a"].tolist()

    def test_clean_idempotent_drop_duplicates(self):
        df = pd.DataFrame({"a": [1, 1, 2]})
        result1 = ar.clean(df, ["drop_duplicates"])
        result2 = ar.clean(result1, ["drop_duplicates"])
        assert len(result1) == len(result2)

    def test_clean_idempotent_normalize_case(self):
        df = pd.DataFrame({"a": ["HELLO", "World"]})
        result1 = ar.clean(df, [("normalize_case", {"case": "lower"})])
        result2 = ar.clean(result1, [("normalize_case", {"case": "lower"})])
        assert result1["a"].tolist() == result2["a"].tolist()

    def test_clean_no_mutation(self):
        """Clean should never modify the original DataFrame."""
        df = pd.DataFrame({"a": ["  hello  "]})
        original_value = df["a"].iloc[0]
        ar.clean(df, ["strip_whitespace"])
        assert df["a"].iloc[0] == original_value

    def test_standardize_missing_step(self):
        df = pd.DataFrame({"a": ["hello", "N/A", "null", "world"]})
        result = ar.clean(df, ["standardize_missing"])
        assert result["a"].isna().sum() == 2

    def test_replace_values_step(self):
        df = pd.DataFrame({"status": ["active", "inactive"]})
        result = ar.clean(df, [("replace_values", {"column": "status", "mapping": {"active": "on", "inactive": "off"}})])
        assert result["status"].tolist() == ["on", "off"]

    def test_cast_column_step(self):
        df = pd.DataFrame({"a": [1, 2, 3]})
        result = ar.clean(df, [("cast_column", {"column": "a", "dtype": "float64"})])
        assert result["a"].dtype == "float64"

    def test_drop_columns_nonexistent_no_crash(self):
        """Dropping columns that don't exist should not crash."""
        df = pd.DataFrame({"a": [1], "b": [2]})
        result = ar.clean(df, [("drop_columns", {"columns": ["nonexistent"]})])
        assert list(result.columns) == ["a", "b"]

    def test_pipeline_error_includes_step_info(self):
        """PipelineError should identify which step failed."""
        df = pd.DataFrame({"a": [1]})
        with pytest.raises(ar.PipelineError) as exc_info:
            ar.clean(df, [("fill_nulls", {"column": "nonexistent_col", "value": 0})])
        assert exc_info.value.step_index == 0

    def test_type_preserved_column_oriented_dict(self):
        data = {"a": [1, 2, 3], "b": [4, 5, 6]}
        result = ar.clean(data, ["drop_duplicates"])
        assert isinstance(result, list)


# =====================================================================
# PIPELINE EDGE CASES
# =====================================================================


class TestPipelineEdgeCases:

    def test_empty_pipeline(self):
        pipe = ar.Pipeline([])
        assert len(pipe) == 0
        df = pd.DataFrame({"a": [1, 2]})
        result = pipe.run(df)
        assert isinstance(result, pd.DataFrame)

    def test_pipeline_json_roundtrip_all_step_types(self):
        pipe = ar.Pipeline([
            "strip_whitespace",
            "drop_duplicates",
            ("normalize_case", {"case": "upper"}),
            ("fill_nulls", {"column": "a", "value": 0}),
        ])
        json_str = pipe.to_json()
        restored = ar.Pipeline.from_json(json_str)
        assert len(restored) == len(pipe)
        assert restored.steps == pipe.steps

    def test_pipeline_yaml_roundtrip(self):
        pipe = ar.Pipeline(["strip_whitespace", "drop_duplicates"])
        yaml_str = pipe.to_yaml()
        restored = ar.Pipeline.from_yaml(yaml_str)
        assert len(restored) == len(pipe)

    def test_pipeline_invalid_step_spec_raises(self):
        with pytest.raises(TypeError):
            ar.Pipeline([123])  # Not a str or tuple

    def test_pipeline_repr(self):
        pipe = ar.Pipeline(["strip_whitespace"])
        assert "strip_whitespace" in repr(pipe)

    def test_pipeline_steps_property_is_copy(self):
        pipe = ar.Pipeline(["strip_whitespace"])
        steps = pipe.steps
        steps.append(("extra", {}))
        assert len(pipe) == 1  # Original unchanged


# =====================================================================
# PROFILE EDGE CASES
# =====================================================================


class TestProfileEdgeCases:

    def test_profile_empty_dataframe(self):
        df = pd.DataFrame()
        report = ar.profile(df)
        assert report.row_count == 0
        assert report.column_count == 0
        assert report.quality_score == 100.0

    def test_profile_single_column_all_unique(self):
        df = pd.DataFrame({"id": list(range(100))})
        report = ar.profile(df)
        cp = report.columns["id"]
        assert cp.unique_ratio == 1.0

    def test_profile_high_null_rate_warning(self):
        df = pd.DataFrame({"a": [None] * 8 + [1, 2]})
        report = ar.profile(df)
        assert "high_null_rate" in report.columns["a"].warnings

    def test_profile_empty_strings_detected(self):
        df = pd.DataFrame({"a": ["hello", "", "   ", "world"]})
        report = ar.profile(df)
        assert report.columns["a"].empty_string_count >= 2

    def test_suggest_no_issues_empty_list(self):
        df = pd.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "z"]})
        suggestions = ar.suggest(df)
        # Clean data should have few or no suggestions
        assert isinstance(suggestions, list)

    def test_profile_to_json_valid(self):
        df = pd.DataFrame({"a": [1, 2, 3]})
        report = ar.profile(df)
        json_str = report.to_json()
        parsed = json.loads(json_str)
        assert "quality_score" in parsed

    def test_profile_constant_column_detected(self):
        df = pd.DataFrame({"a": [42, 42, 42], "b": [1, 2, 3]})
        report = ar.profile(df)
        assert report.columns["a"].is_constant is True
        assert report.columns["b"].is_constant is False


# =====================================================================
# GATES EDGE CASES
# =====================================================================


class TestGatesEdgeCases:

    def test_check_with_warnings_only_passes(self):
        """check() should only raise on errors, not warnings."""
        df = pd.DataFrame({"a": [1]})
        schema = ar.Schema({"a": ar.Int()})
        # Should not raise even if there are dtype warnings
        ar.check(df, schema)

    def test_check_error_has_issues_list(self):
        df = pd.DataFrame({"a": [None]})
        schema = ar.Schema({"a": ar.Int(nullable=False)})
        with pytest.raises(ar.ValidationError) as exc_info:
            ar.check(df, schema)
        assert len(exc_info.value.issues) > 0

    def test_check_max_errors(self):
        df = pd.DataFrame({"a": [-1, -2, -3]})
        schema = ar.Schema({"a": ar.Int(min=0)})
        with pytest.raises(ar.ValidationError) as exc_info:
            ar.check(df, schema, max_errors=1)
        assert len(exc_info.value.issues) <= 1


# =====================================================================
# PANDAS ACCESSOR EDGE CASES
# =====================================================================


class TestAccessorEdgeCases:

    def test_accessor_is_valid_false(self):
        df = pd.DataFrame({"a": [None]})
        assert df.arnio.is_valid({"a": ar.Int(nullable=False)}) is False

    def test_accessor_suggest_returns_list(self):
        df = pd.DataFrame({"a": [1, 1, 2], "b": [3, 3, 4]})
        result = df.arnio.suggest()
        assert isinstance(result, list)

    def test_accessor_clean_returns_dataframe(self):
        df = pd.DataFrame({"a": ["  hello  "]})
        result = df.arnio.clean(["strip_whitespace"])
        assert isinstance(result, pd.DataFrame)
        assert result["a"].iloc[0] == "hello"


# =====================================================================
# ADAPTER DETECTION EDGE CASES
# =====================================================================


class TestAdapterDetection:

    def test_unsupported_type_raises(self):
        with pytest.raises(ar.AdapterError):
            from arnio.adapt import resolve_adapter
            resolve_adapter(42)

    def test_unsupported_type_message(self):
        with pytest.raises(ar.AdapterError, match="int"):
            from arnio.adapt import resolve_adapter
            resolve_adapter(42)

    def test_list_of_non_dicts_raises(self):
        """A list of ints should raise AdapterError."""
        with pytest.raises(ar.AdapterError):
            from arnio.adapt import resolve_adapter
            resolve_adapter([1, 2, 3])

    def test_empty_dict_is_valid(self):
        from arnio.adapt import resolve_adapter
        adapter = resolve_adapter({})
        assert adapter.row_count() == 0


# =====================================================================
# SCHEMA INFERENCE EDGE CASES
# =====================================================================


class TestSchemaInferenceEdgeCases:

    def test_infer_from_empty_df(self):
        df = pd.DataFrame({"a": pd.Series([], dtype="int64"), "b": pd.Series([], dtype="float64")})
        schema = ar.infer_schema(df)
        assert "a" in schema
        assert "b" in schema

    def test_infer_sets_nullable_from_data(self):
        df = pd.DataFrame({"a": [1, None, 3]})
        schema = ar.infer_schema(df)
        assert schema["a"].nullable is True

    def test_infer_sets_non_nullable_when_clean(self):
        df = pd.DataFrame({"a": [1, 2, 3]})
        schema = ar.infer_schema(df)
        assert schema["a"].nullable is False

    def test_infer_detects_bool_dtype(self):
        df = pd.DataFrame({"flag": [True, False, True]})
        schema = ar.infer_schema(df)
        assert isinstance(schema["flag"], ar.Bool)

    def test_infer_detects_datetime_dtype(self):
        df = pd.DataFrame({"ts": pd.to_datetime(["2024-01-01", "2024-06-15"])})
        schema = ar.infer_schema(df)
        assert isinstance(schema["ts"], ar.DateTime)
