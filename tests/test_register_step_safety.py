"""Unit tests for pipeline step overwrite protection and custom step registration."""

import sys
from unittest.mock import MagicMock

# Mock the C++ binding extension so we can run Python-only unit tests
# without compiling the C++ code.
mock_cpp = MagicMock()
mock_cpp.Column = MagicMock()
mock_cpp.CsvChunkReader = MagicMock()
mock_cpp.CsvConfig = MagicMock()
mock_cpp.CsvReader = MagicMock()
mock_cpp.CsvWriteConfig = MagicMock()
mock_cpp.CsvWriter = MagicMock()
mock_cpp.DType = MagicMock()
mock_cpp.Frame = MagicMock()
mock_cpp.cast_types = MagicMock()
mock_cpp.clip_numeric = MagicMock()
mock_cpp.drop_duplicates = MagicMock()
mock_cpp.drop_nulls = MagicMock()
mock_cpp.fill_nulls = MagicMock()
mock_cpp.normalize_case = MagicMock()
mock_cpp.rename_columns = MagicMock()
mock_cpp.safe_divide_columns = MagicMock()
mock_cpp.strip_whitespace = MagicMock()

sys.modules["arnio._arnio_cpp"] = mock_cpp

import pytest  # noqa: E402

from arnio.pipeline import (  # noqa: E402
    _BUILTIN_PYTHON_STEP_REGISTRY,
    _PYTHON_STEP_REGISTRY,
    register_step,
    reset_steps,
)


@pytest.fixture(autouse=True)
def restore_python_step_registry():
    """Restore custom pipeline steps after each test."""
    original_registry = dict(_PYTHON_STEP_REGISTRY)
    yield
    _PYTHON_STEP_REGISTRY.clear()
    _PYTHON_STEP_REGISTRY.update(original_registry)


class TestRegisterStepSafety:
    """Tests to verify register_step overwrite protections for Python and C++ built-ins."""

    def test_prevent_overwriting_builtin_python_steps_without_overwrite(self):
        """register_step raises ValueError when trying to register built-in Python step without overwrite."""

        def dummy_step(df):
            return df

        for step in ["filter_rows", "standardize_missing_tokens", "coalesce_columns"]:
            with pytest.raises(ValueError, match="conflicts with built-in Python step"):
                register_step(step, dummy_step)

    def test_prevent_overwriting_builtin_python_steps_with_overwrite(self):
        """register_step raises ValueError when trying to register built-in Python step even with overwrite=True."""

        def dummy_step(df):
            return df

        for step in ["filter_rows", "standardize_missing_tokens", "coalesce_columns"]:
            with pytest.raises(ValueError, match="conflicts with built-in Python step"):
                register_step(step, dummy_step, overwrite=True)

    def test_prevent_overwriting_builtin_cpp_steps_without_overwrite(self):
        """register_step raises ValueError when trying to register built-in C++ step without overwrite."""

        def dummy_step(df):
            return df

        for step in ["drop_nulls", "strip_whitespace", "rename_columns"]:
            with pytest.raises(
                ValueError, match="conflicts with built-in C\\+\\+ step"
            ):
                register_step(step, dummy_step)

    def test_prevent_overwriting_builtin_cpp_steps_with_overwrite(self):
        """register_step raises ValueError when trying to register built-in C++ step even with overwrite=True."""

        def dummy_step(df):
            return df

        for step in ["drop_nulls", "strip_whitespace", "rename_columns"]:
            with pytest.raises(
                ValueError, match="conflicts with built-in C\\+\\+ step"
            ):
                register_step(step, dummy_step, overwrite=True)

    def test_custom_step_registration_and_explicit_overwrite(self):
        """Allows registering a custom step, blocks overwrite by default, but allows it with overwrite=True."""

        def step_v1(df):
            return df

        def step_v2(df):
            return df

        step_name = "test_safety_custom_step"

        # 1. Success on initial registration
        register_step(step_name, step_v1)
        assert step_name in _PYTHON_STEP_REGISTRY
        assert _PYTHON_STEP_REGISTRY[step_name] is step_v1

        # 2. Block overwrite by default
        with pytest.raises(
            ValueError, match="already registered as a custom Python step"
        ):
            register_step(step_name, step_v2)

        # 3. Allow overwrite with overwrite=True
        register_step(step_name, step_v2, overwrite=True)
        assert _PYTHON_STEP_REGISTRY[step_name] is step_v2

    def test_reset_steps_behavior_remains_unchanged(self):
        """reset_steps clears custom registrations and restores built-ins."""

        def custom_step(df):
            return df

        step_name = "test_safety_reset_custom"
        register_step(step_name, custom_step)
        assert step_name in _PYTHON_STEP_REGISTRY

        # Reset steps should remove the custom step but preserve the built-in python steps
        reset_steps()
        assert step_name not in _PYTHON_STEP_REGISTRY
        for step in _BUILTIN_PYTHON_STEP_REGISTRY:
            assert step in _PYTHON_STEP_REGISTRY
