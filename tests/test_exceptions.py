"""Tests for arnio.exceptions."""


from arnio.exceptions import (
    AdapterError,
    ArnioError,
    CleaningError,
    PipelineError,
    SchemaError,
    ValidationError,
)


class TestExceptionHierarchy:
    """All exceptions inherit from ArnioError."""

    def test_schema_error_is_arnio_error(self):
        assert issubclass(SchemaError, ArnioError)

    def test_adapter_error_is_arnio_error(self):
        assert issubclass(AdapterError, ArnioError)

    def test_validation_error_is_arnio_error(self):
        assert issubclass(ValidationError, ArnioError)

    def test_cleaning_error_is_arnio_error(self):
        assert issubclass(CleaningError, ArnioError)

    def test_pipeline_error_is_arnio_error(self):
        assert issubclass(PipelineError, ArnioError)


class TestAdapterError:
    """AdapterError provides helpful messages."""

    def test_message_includes_type(self):
        err = AdapterError(42)
        assert "int" in str(err)

    def test_message_includes_supported_types(self):
        err = AdapterError("string")
        assert "pandas" in str(err).lower()


class TestValidationError:
    """ValidationError carries structured issues."""

    def test_empty_issues_by_default(self):
        err = ValidationError("test")
        assert err.issues == []

    def test_issues_attached(self):
        from arnio.validate._result import Issue
        issues = [Issue(column="x", rule="test", message="bad")]
        err = ValidationError("test", issues=issues)
        assert len(err.issues) == 1


class TestCleaningError:
    """CleaningError includes step name."""

    def test_step_name_in_message(self):
        err = CleaningError("my_step", "something broke")
        assert "my_step" in str(err)
        assert err.step_name == "my_step"


class TestPipelineError:
    """PipelineError includes step name and index."""

    def test_step_info(self):
        cause = ValueError("bad value")
        err = PipelineError("my_step", 3, cause)
        assert err.step_name == "my_step"
        assert err.step_index == 3
        assert "step 3" in str(err)
