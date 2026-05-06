"""
arnio.cleaning
Data cleaning functions.
"""

from __future__ import annotations

from typing import Any, Optional

from ._core import (
    _drop_nulls,
    _fill_nulls,
    _drop_duplicates,
    _strip_whitespace,
    _normalize_case,
    _rename_columns,
    _cast_types,
)
from .frame import ArFrame


def drop_nulls(
    frame: ArFrame,
    *,
    subset: Optional[list[str]] = None,
) -> ArFrame:
    """Remove rows containing null/empty values."""
    result = _drop_nulls(frame._frame, subset=subset)
    return ArFrame(result)


def fill_nulls(
    frame: ArFrame,
    value: Any,
    *,
    subset: Optional[list[str]] = None,
) -> ArFrame:
    """Replace null/empty values with a given fill value."""
    result = _fill_nulls(frame._frame, value, subset=subset)
    return ArFrame(result)


def drop_duplicates(
    frame: ArFrame,
    *,
    subset: Optional[list[str]] = None,
    keep: str = "first",
) -> ArFrame:
    """Remove duplicate rows."""
    result = _drop_duplicates(frame._frame, subset=subset, keep=keep)
    return ArFrame(result)


def strip_whitespace(
    frame: ArFrame,
    *,
    subset: Optional[list[str]] = None,
) -> ArFrame:
    """Trim leading/trailing whitespace from string columns."""
    result = _strip_whitespace(frame._frame, subset=subset)
    return ArFrame(result)


def normalize_case(
    frame: ArFrame,
    *,
    subset: Optional[list[str]] = None,
    case_type: str = "lower",
) -> ArFrame:
    """Normalize string columns to lower/upper/title case."""
    result = _normalize_case(frame._frame, subset=subset, case_type=case_type)
    return ArFrame(result)


def rename_columns(
    frame: ArFrame,
    mapping: dict[str, str],
) -> ArFrame:
    """Rename columns via a {old: new} dict."""
    result = _rename_columns(frame._frame, mapping)
    return ArFrame(result)


def cast_types(
    frame: ArFrame,
    mapping: dict[str, str],
) -> ArFrame:
    """Cast columns to specified types via {col: type_str} dict."""
    result = _cast_types(frame._frame, mapping)
    return ArFrame(result)


def clean(
    frame: ArFrame,
    *,
    strip_whitespace: bool = True,
    drop_nulls: bool = False,
    drop_duplicates: bool = False,
) -> ArFrame:
    """Convenience function to apply common cleaning operations.
    
    Operations are applied in this order (if enabled):
    1. strip_whitespace
    2. drop_nulls
    3. drop_duplicates
    """
    from .pipeline import pipeline
    
    steps = []
    if strip_whitespace:
        steps.append(("strip_whitespace",))
    if drop_nulls:
        steps.append(("drop_nulls",))
    if drop_duplicates:
        steps.append(("drop_duplicates",))
        
    if not steps:
        return frame
        
    return pipeline(frame, steps)
