import pytest

from arnio.cleaning import rolling_window


def test_rolling_window_valid():
    """Test standard sliding window extraction."""
    data = [1.0, 2.0, 3.0, 4.0, 5.0]
    result = rolling_window(data, window_size=3)
    assert result == [[1.0, 2.0, 3.0], [2.0, 3.0, 4.0], [3.0, 4.0, 5.0]]


def test_rolling_window_exact_size():
    """Test when window size equals data size."""
    data = [1.0, 2.0]
    result = rolling_window(data, window_size=2)
    assert result == [[1.0, 2.0]]


def test_rolling_window_invalid_zero():
    """Test that window_size of 0 raises an error."""
    with pytest.raises(ValueError, match="must be greater than 0"):
        rolling_window([1.0, 2.0], window_size=0)


def test_rolling_window_too_large():
    """Test that window_size larger than data raises an error."""
    with pytest.raises(ValueError, match="cannot be larger than the input"):
        rolling_window([1.0, 2.0], window_size=5)


def test_rolling_window_reject_bool():
    """Test that boolean values are explicitly rejected for window_size."""
    with pytest.raises(TypeError, match="window_size must be an integer"):
        rolling_window([1.0, 2.0, 3.0], window_size=True)
