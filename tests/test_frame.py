"""
Tests for ArFrame.drop_columns
"""
import pytest
import arnio


def make_frame():
    """Helper to create a simple test frame."""
    import arnio
    return arnio.read_csv("tests/fixtures/messy_sales_data.csv")


def test_drop_single_column():
    """Dropping one column should remove it from the result."""
    frame = make_frame()
    original_cols = frame.columns
    result = frame.drop_columns([original_cols[0]])
    assert original_cols[0] not in result.columns


def test_drop_preserves_order():
    """Remaining columns should stay in original order."""
    frame = make_frame()
    cols = frame.columns
    result = frame.drop_columns([cols[0]])
    assert result.columns == cols[1:]


def test_drop_empty_list():
    """Dropping nothing should return a frame with same columns."""
    frame = make_frame()
    result = frame.drop_columns([])
    assert result.columns == frame.columns


def test_drop_unknown_column():
    """Dropping a non-existent column should raise KeyError."""
    frame = make_frame()
    with pytest.raises(KeyError):
        frame.drop_columns(["this_does_not_exist"])


def test_drop_all_columns():
    """Dropping all columns should return an empty frame."""
    frame = make_frame()
    result = frame.drop_columns(frame.columns)
    assert result.columns == []
