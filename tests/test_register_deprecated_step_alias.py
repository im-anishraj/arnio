"""Tests for _register_deprecated_step_alias in arnio.pipeline."""

import pytest
from arnio.pipeline import (
    _register_deprecated_step_alias,
    _DEPRECATED_STEP_ALIASES,
    UnknownStepError,
)


class TestRegisterDeprecatedStepAlias:
    """Test suite for _register_deprecated_step_alias function."""

    def setup_method(self):
        """Clear deprecated aliases before each test."""
        _DEPRECATED_STEP_ALIASES.clear()

    def teardown_method(self):
        """Clear deprecated aliases after each test."""
        _DEPRECATED_STEP_ALIASES.clear()

    def test_raises_unknown_step_error_for_invalid_target(self):
        """_register_deprecated_step_alias raises UnknownStepError for nonexistent target."""
        with pytest.raises(UnknownStepError):
            _register_deprecated_step_alias("old_name", "nonexistent_step_xyz")

    def test_raises_error_when_old_name_is_existing_step(self):
        """_register_deprecated_step_alias raises when old name is already a step."""
        with pytest.raises(ValueError, match="already registered"):
            _register_deprecated_step_alias("clean", "dedupe")

    def test_raises_error_when_alias_already_points_to_different_target(self):
        """_register_deprecated_step_alias raises when alias already exists with different target."""
        _register_deprecated_step_alias("legacy_step", "dedupe")
        with pytest.raises(ValueError, match="already points to"):
            _register_deprecated_step_alias("legacy_step", "fill_nulls")

    def test_allows_same_alias_registration_twice(self):
        """_register_deprecated_step_alias allows registering same alias to same target twice."""
        _register_deprecated_step_alias("legacy_a", "dedupe")
        _register_deprecated_step_alias("legacy_a", "dedupe")

    def test_stores_alias_mapping(self):
        """_register_deprecated_step_alias stores the alias mapping correctly."""
        _register_deprecated_step_alias("old_clean", "clean")
        assert _DEPRECATED_STEP_ALIASES["old_clean"] == "clean"

    def test_multiple_aliases_for_different_targets(self):
        """_register_deprecated_step_alias can register multiple aliases to different steps."""
        _register_deprecated_step_alias("legacy_a", "clean")
        _register_deprecated_step_alias("legacy_b", "dedupe")
        assert _DEPRECATED_STEP_ALIASES["legacy_a"] == "clean"
        assert _DEPRECATED_STEP_ALIASES["legacy_b"] == "dedupe"

    def test_multiple_aliases_same_target(self):
        """_register_deprecated_step_alias can register multiple aliases to same step."""
        _register_deprecated_step_alias("alias_one", "clean")
        _register_deprecated_step_alias("alias_two", "clean")
        assert _DEPRECATED_STEP_ALIASES["alias_one"] == "clean"
        assert _DEPRECATED_STEP_ALIASES["alias_two"] == "clean"

    def test_alias_targets_valid_step(self):
        """_register_deprecated_step_alias successfully targets a valid step."""
        _register_deprecated_step_alias("old_name", "drop_duplicates")
        assert _DEPRECATED_STEP_ALIASES["old_name"] == "drop_duplicates"