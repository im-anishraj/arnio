"""Tests for _register_deprecated_step_alias in arnio.pipeline."""

import pandas as pd
import pytest

import arnio as ar
from arnio.pipeline import (
    _DEPRECATED_STEP_ALIASES,
    UnknownStepError,
    _register_deprecated_step_alias,
    _resolve_step_name,
)


@pytest.fixture(autouse=True)
def restore_aliases():
    """Preserve and restore _DEPRECATED_STEP_ALIASES around each test."""
    original_aliases = dict(_DEPRECATED_STEP_ALIASES)
    yield
    _DEPRECATED_STEP_ALIASES.clear()
    _DEPRECATED_STEP_ALIASES.update(original_aliases)


class TestRegisterDeprecatedStepAlias:
    """Test suite for _register_deprecated_step_alias function."""

    def test_raises_unknown_step_error_for_invalid_target(self):
        """_register_deprecated_step_alias raises UnknownStepError for nonexistent target."""
        with pytest.raises(UnknownStepError):
            _register_deprecated_step_alias("old_name", "nonexistent_step_xyz")

    def test_raises_error_when_old_name_is_existing_step(self):
        """_register_deprecated_step_alias raises when old name is already a step."""
        with pytest.raises(ValueError, match="already registered"):
            _register_deprecated_step_alias("strip_whitespace", "drop_duplicates")

    def test_raises_error_when_alias_already_points_to_different_target(self):
        """_register_deprecated_step_alias raises when alias already exists with different target."""
        _register_deprecated_step_alias("legacy_step", "drop_duplicates")
        with pytest.raises(ValueError, match="already points to"):
            _register_deprecated_step_alias("legacy_step", "fill_nulls")

    def test_allows_same_alias_registration_twice(self):
        """_register_deprecated_step_alias allows registering same alias to same target twice."""
        _register_deprecated_step_alias("legacy_a", "drop_duplicates")
        _register_deprecated_step_alias("legacy_a", "drop_duplicates")
        assert _DEPRECATED_STEP_ALIASES["legacy_a"] == "drop_duplicates"

    def test_stores_alias_mapping(self):
        """_register_deprecated_step_alias stores the alias mapping correctly."""
        _register_deprecated_step_alias("old_strip", "strip_whitespace")
        assert _DEPRECATED_STEP_ALIASES["old_strip"] == "strip_whitespace"

    def test_multiple_aliases_for_different_targets(self):
        """_register_deprecated_step_alias can register multiple aliases to different steps."""
        _register_deprecated_step_alias("legacy_a", "strip_whitespace")
        _register_deprecated_step_alias("legacy_b", "drop_duplicates")
        assert _DEPRECATED_STEP_ALIASES["legacy_a"] == "strip_whitespace"
        assert _DEPRECATED_STEP_ALIASES["legacy_b"] == "drop_duplicates"

    def test_multiple_aliases_same_target(self):
        """_register_deprecated_step_alias can register multiple aliases to same step."""
        _register_deprecated_step_alias("alias_one", "strip_whitespace")
        _register_deprecated_step_alias("alias_two", "strip_whitespace")
        assert _DEPRECATED_STEP_ALIASES["alias_one"] == "strip_whitespace"
        assert _DEPRECATED_STEP_ALIASES["alias_two"] == "strip_whitespace"

    def test_alias_resolution_behavior_emits_deprecation_warning(self):
        """Verifies that resolving an alias returns target and raises DeprecationWarning."""
        _register_deprecated_step_alias("legacy_strip", "strip_whitespace")

        with pytest.warns(
            DeprecationWarning, match="Pipeline step 'legacy_strip' is deprecated"
        ):
            resolved = _resolve_step_name("legacy_strip", _DEPRECATED_STEP_ALIASES)

        assert resolved == "strip_whitespace"

    def test_pipeline_executes_using_deprecated_alias(self):
        """Verifies that ar.pipeline resolves and executes a registered deprecated alias."""
        _register_deprecated_step_alias("legacy_strip", "strip_whitespace")

        frame = ar.from_pandas(pd.DataFrame({"name": [" Alice ", " Bob "]}))

        with pytest.warns(
            DeprecationWarning,
            match="Pipeline step 'legacy_strip' is deprecated; use 'strip_whitespace'",
        ):
            result = ar.pipeline(frame, [("legacy_strip",)])

        df = ar.to_pandas(result)
        assert list(df["name"]) == ["Alice", "Bob"]
