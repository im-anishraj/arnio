"""Tests for register_validator and Custom validator in arnio.schema."""

import pytest

from arnio import schema
from arnio.schema import Custom, register_validator


class TestRegisterValidator:
    """Test suite for register_validator function."""

    def setup_method(self):
        """Save original validators state before each test."""
        self._original_validators = dict(schema._CUSTOM_VALIDATORS)

    def teardown_method(self):
        """Restore original validators state after each test."""
        schema._CUSTOM_VALIDATORS.clear()
        schema._CUSTOM_VALIDATORS.update(self._original_validators)

    def test_register_custom_validator_by_name(self):
        """register_validator registers a validator function under a name."""

        def my_validator(value):
            return isinstance(value, int) and value > 0

        register_validator("positive_int", my_validator)
        assert "positive_int" in schema._CUSTOM_VALIDATORS
        assert schema._CUSTOM_VALIDATORS["positive_int"] is my_validator

    def test_register_validator_returns_none(self):
        """register_validator returns None on success."""

        def my_validator(value):
            return True

        result = register_validator("test_validator", my_validator)
        assert result is None

    def test_raises_type_error_when_fn_not_callable(self):
        """register_validator raises TypeError when fn is not callable."""
        with pytest.raises(TypeError, match="fn must be callable"):
            register_validator("not_callable", "not a function")

    def test_raises_type_error_when_fn_is_none(self):
        """register_validator raises TypeError when fn is None."""
        with pytest.raises(TypeError, match="fn must be callable"):
            register_validator("none_fn", None)

    def test_raises_value_error_when_name_is_empty_string(self):
        """register_validator raises ValueError when name is empty string."""
        with pytest.raises(ValueError, match="non-empty string"):
            register_validator("", lambda x: True)

    def test_raises_value_error_when_name_is_not_string(self):
        """register_validator raises ValueError when name is not a string."""
        with pytest.raises(ValueError, match="non-empty string"):
            register_validator(123, lambda x: True)

    def test_overwrites_existing_validator(self):
        """register_validator allows overwriting an existing validator."""

        def validator_a(value):
            return value > 0

        def validator_b(value):
            return value < 0

        register_validator("my_validator", validator_a)
        assert schema._CUSTOM_VALIDATORS["my_validator"] is validator_a

        register_validator("my_validator", validator_b)
        assert schema._CUSTOM_VALIDATORS["my_validator"] is validator_b


class TestCustomValidator:
    """Test suite for Custom validator field factory."""

    def setup_method(self):
        """Save original validators state before each test."""
        self._original_validators = dict(schema._CUSTOM_VALIDATORS)

    def teardown_method(self):
        """Restore original validators state after each test."""
        schema._CUSTOM_VALIDATORS.clear()
        schema._CUSTOM_VALIDATORS.update(self._original_validators)

    def test_custom_validator_stores_name(self):
        """Custom stores the validator name correctly in semantic field."""

        def my_validator(value):
            return True

        register_validator("test_name", my_validator)
        field = Custom("test_name")

        assert field.semantic == "custom:test_name"

    def test_custom_validator_default_nullable(self):
        """Custom defaults nullable to True."""

        def my_validator(value):
            return True

        register_validator("test_nullable", my_validator)
        field = Custom("test_nullable")

        assert field.nullable is True

    def test_custom_validator_default_unique(self):
        """Custom defaults unique to False."""

        def my_validator(value):
            return True

        register_validator("test_unique", my_validator)
        field = Custom("test_unique")

        assert field.unique is False

    def test_custom_validator_explicit_nullable_false(self):
        """Custom respects explicit nullable=False."""

        def my_validator(value):
            return True

        register_validator("test_nullable_false", my_validator)
        field = Custom("test_nullable_false", nullable=False)

        assert field.nullable is False

    def test_custom_validator_explicit_unique_true(self):
        """Custom respects explicit unique=True."""

        def my_validator(value):
            return True

        register_validator("test_unique_true", my_validator)
        field = Custom("test_unique_true", unique=True)

        assert field.unique is True

    def test_custom_validator_default_severity(self):
        """Custom defaults severity to error."""

        def my_validator(value):
            return True

        register_validator("test_severity", my_validator)
        field = Custom("test_severity")

        assert field.severity == "error"

    def test_custom_validator_explicit_severity(self):
        """Custom respects explicit severity parameter."""

        def my_validator(value):
            return True

        register_validator("test_severity_warn", my_validator)
        field = Custom("test_severity_warn", severity="warning")

        assert field.severity == "warning"

    def test_custom_raises_when_validator_not_registered(self):
        """Custom raises ValueError when validator name not registered."""
        with pytest.raises(ValueError, match="No validator registered"):
            Custom("nonexistent_validator_name_xyz")

    def test_custom_repr_contains_name(self):
        """Custom repr includes the validator name."""

        def my_validator(value):
            return True

        register_validator("repr_test", my_validator)
        field = Custom("repr_test")

        assert "repr_test" in repr(field)

    def test_custom_in_schema_integration(self):
        """Custom validator can be used in a Schema definition."""

        def is_positive(value):
            return isinstance(value, (int, float)) and value > 0

        register_validator("positive", is_positive)

        field = Custom("positive", nullable=False)
        assert field.semantic == "custom:positive"
        assert field.nullable is False

    def test_multiple_custom_validators_in_schema(self):
        """Multiple Custom validators can coexist in a schema."""

        def is_positive(value):
            return isinstance(value, (int, float)) and value > 0

        def is_email_format(value):
            return isinstance(value, str) and "@" in value

        register_validator("positive", is_positive)
        register_validator("email", is_email_format)

        f1 = Custom("positive")
        f2 = Custom("email")

        assert f1.semantic == "custom:positive"
        assert f2.semantic == "custom:email"


class TestCustomValidatorReturnNormalization:
    """Regression tests for issue #1469.

    Custom validators must return a strict bool. The normalization contract:
    - True  → passes validation
    - False → fails validation (row reported as invalid)
    - None  → fails validation (row reported as invalid)
    - pd.NA → fails validation (row reported as invalid, no TypeError)
    - any other non-bool value → raises TypeError naming the validator
    """

    def setup_method(self):
        self._original_validators = dict(schema._CUSTOM_VALIDATORS)

    def teardown_method(self):
        schema._CUSTOM_VALIDATORS.clear()
        schema._CUSTOM_VALIDATORS.update(self._original_validators)

    def test_validator_returning_true_passes(self):
        """True return value marks the row as valid."""
        import arnio as ar
        import pandas as pd

        register_validator("always_true", lambda v: True)
        frame = ar.from_pandas(pd.DataFrame({"x": [1, 2, 3]}))
        result = ar.validate(frame, {"x": ar.Custom("always_true")})
        assert result.passed
        assert result.issue_count == 0

    def test_validator_returning_false_fails(self):
        """False return value marks the row as invalid with a structured issue."""
        import arnio as ar
        import pandas as pd

        register_validator("always_false", lambda v: False)
        frame = ar.from_pandas(pd.DataFrame({"x": [1, 2, 3]}))
        result = ar.validate(frame, {"x": ar.Custom("always_false")})
        assert not result.passed
        assert result.issue_count == 3
        assert all(i.rule == "custom" for i in result.issues)

    def test_validator_returning_none_fails(self):
        """None return value is treated as a validation failure, not an error."""
        import arnio as ar
        import pandas as pd

        register_validator("returns_none", lambda v: None)
        frame = ar.from_pandas(pd.DataFrame({"x": [1, 2]}))
        result = ar.validate(frame, {"x": ar.Custom("returns_none")})
        assert not result.passed
        assert all(i.rule == "custom" for i in result.issues)

    def test_validator_returning_pd_na_fails(self):
        """pd.NA return value is treated as a validation failure, not a TypeError."""
        import arnio as ar
        import pandas as pd

        register_validator(
            "nullable_bool",
            lambda v: pd.NA if v == 0 else True,
        )
        frame = ar.from_pandas(pd.DataFrame({"x": [1, 0, -1]}))
        # Before the fix this raised: TypeError: boolean value of NA is ambiguous
        result = ar.validate(frame, {"x": ar.Custom("nullable_bool")})
        assert not result.passed
        failing = [i for i in result.issues if i.rule == "custom"]
        assert len(failing) == 1
        assert failing[0].row_index == 1  # the row where v == 0

    def test_validator_returning_non_bool_raises_type_error(self):
        """A non-bool, non-None, non-NA return value raises TypeError naming the validator."""
        import arnio as ar
        import pandas as pd

        register_validator("returns_int", lambda v: 1)
        frame = ar.from_pandas(pd.DataFrame({"x": [42]}))
        with pytest.raises(TypeError, match="returns_int"):
            ar.validate(frame, {"x": ar.Custom("returns_int")})

    def test_validator_returning_string_raises_type_error(self):
        """A string return value raises TypeError naming the validator."""
        import arnio as ar
        import pandas as pd

        register_validator("returns_str", lambda v: "yes")
        frame = ar.from_pandas(pd.DataFrame({"x": [1]}))
        with pytest.raises(TypeError, match="returns_str"):
            ar.validate(frame, {"x": ar.Custom("returns_str")})

    def test_mixed_true_false_none_pd_na(self):
        """Mixed True/False/None/pd.NA: only True rows pass, others fail."""
        import arnio as ar
        import pandas as pd

        def mixed_validator(v):
            if v == 1:
                return True
            if v == 2:
                return False
            if v == 3:
                return None
            if v == 4:
                return pd.NA
            return True

        register_validator("mixed", mixed_validator)
        frame = ar.from_pandas(pd.DataFrame({"x": [1, 2, 3, 4, 5]}))
        result = ar.validate(frame, {"x": ar.Custom("mixed")})
        assert not result.passed
        failing_rows = {i.row_index for i in result.issues if i.rule == "custom"}
        # rows at index 1 (v=2), 2 (v=3), 3 (v=4) should fail
        assert failing_rows == {1, 2, 3}
