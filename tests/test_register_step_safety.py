"""Unit tests for pipeline step overwrite protection and custom step registration."""

import pytest  # noqa: E402

from arnio.pipeline import (  # noqa: E402
    _BUILTIN_PYTHON_STEP_REGISTRY,
    _PYTHON_STEP_REGISTRY,
    list_steps,
    register_step,
    reset_steps,
    unregister_step,
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


class TestUnregisterStepBuiltinAlias:
    """Regression tests for the custom-alias-of-builtin-function unregister bug.

    Previously, unregister_step() used _is_builtin_python_step() which checked
    the function's __module__ attribute.  This incorrectly blocked removal of
    user-registered aliases whose callable originated in arnio.cleaning.
    The fix switches the guard to a membership check against
    _BUILTIN_PYTHON_STEP_REGISTRY (keyed by *registered name*).
    """

    def test_custom_alias_of_builtin_function_can_be_unregistered(self):
        """A user-defined alias for a built-in cleaning function is removable.

        Regression: unregister_step() previously raised UnknownStepError for
        any alias whose underlying function originated in arnio.cleaning.
        """
        import arnio.cleaning as cleaning

        alias = "tmp_strip_alias_safety_test"

        # Precondition: alias must not already exist
        assert alias not in _PYTHON_STEP_REGISTRY

        # 1. Register a custom alias pointing to a built-in cleaning function
        register_step(alias, cleaning.normalize_whitespace)

        # 2. The alias should appear in list_steps()
        assert alias in list_steps()

        # 3. Unregistering the alias must succeed (this was the bug)
        unregister_step(alias)

        # 4. The alias must no longer appear in list_steps()
        assert alias not in list_steps()
        assert alias not in _PYTHON_STEP_REGISTRY

    def test_builtin_python_step_names_remain_protected(self):
        """Actual built-in Python step names cannot be unregistered.

        Ensures the fix does not weaken protection for real built-in names
        such as 'filter_rows', 'normalize_whitespace', 'coalesce_columns'.
        """
        from arnio.exceptions import UnknownStepError

        for step_name in list(_BUILTIN_PYTHON_STEP_REGISTRY):
            with pytest.raises(UnknownStepError):
                unregister_step(step_name)
