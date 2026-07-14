"""
Parity tests for slugify_column_names and rename_columns_matching.
Ensures both are importable, listed in list_steps(), and functional.
"""

from __future__ import annotations

import arnio as ar


def _make_frame():
    return ar.from_records(
        [{"First Name": "Alice", "temp_age": 30}, {"First Name": "Bob", "temp_age": 25}]
    )


# ---------- export parity ----------


def test_slugify_column_names_is_exported():
    assert hasattr(
        ar, "slugify_column_names"
    ), "ar.slugify_column_names missing from public API"


def test_rename_columns_matching_is_exported():
    assert hasattr(
        ar, "rename_columns_matching"
    ), "ar.rename_columns_matching missing from public API"


# ---------- pipeline registry parity ----------


def test_slugify_column_names_in_list_steps():
    assert (
        "slugify_column_names" in ar.list_steps()
    ), "slugify_column_names not registered as a pipeline step"


def test_rename_columns_matching_in_list_steps():
    assert (
        "rename_columns_matching" in ar.list_steps()
    ), "rename_columns_matching not registered as a pipeline step"


# ---------- functional ----------


def test_slugify_column_names_functional():
    frame = _make_frame()
    result = ar.slugify_column_names(frame)
    cols = result.columns
    assert "first_name" in cols, f"Expected 'first_name' in columns, got {cols}"
    assert "temp_age" in cols, f"Expected 'temp_age' in columns, got {cols}"


def test_rename_columns_matching_functional():
    frame = _make_frame()
    result = ar.rename_columns_matching(frame, r"^temp_", "")
    cols = result.columns
    assert "age" in cols, f"Expected 'age' in columns, got {cols}"
    assert "First Name" in cols, f"Expected 'First Name' in columns, got {cols}"


# ---------- pipeline step functional ----------


def test_slugify_column_names_as_pipeline_step():
    frame = _make_frame()
    result = ar.pipeline(frame, steps=[("slugify_column_names",)])
    assert "first_name" in result.columns


def test_rename_columns_matching_as_pipeline_step():
    frame = _make_frame()
    result = ar.pipeline(
        frame,
        steps=[("rename_columns_matching", {"pattern": r"^temp_", "replacement": ""})],
    )
    assert "age" in result.columns
