"""Tests for ArFrame.memory_usage(deep=False/True)."""

import pandas as pd

import arnio as ar


class TestMemoryUsageShallow:
    """memory_usage() with default deep=False — backward-compatible behaviour."""

    def test_returns_positive_int_for_int_frame(self):
        df = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})
        frame = ar.from_pandas(df)
        result = frame.memory_usage()
        assert isinstance(result, int)
        assert result > 0

    def test_returns_positive_int_for_float_frame(self):
        df = pd.DataFrame({"x": [1.1, 2.2, 3.3]})
        frame = ar.from_pandas(df)
        assert frame.memory_usage() > 0

    def test_returns_positive_int_for_bool_frame(self):
        df = pd.DataFrame({"flag": [True, False, True]})
        frame = ar.from_pandas(df)
        assert frame.memory_usage() > 0

    def test_returns_positive_int_for_string_frame(self):
        df = pd.DataFrame({"name": ["Alice", "Bob", "Charlie"]})
        frame = ar.from_pandas(df)
        assert frame.memory_usage() > 0

    def test_returns_positive_int_for_mixed_frame(self):
        df = pd.DataFrame(
            {
                "name": ["Alice", "Bob"],
                "age": [30, 25],
                "score": [9.5, 8.1],
                "active": [True, False],
            }
        )
        frame = ar.from_pandas(df)
        assert frame.memory_usage() > 0

    def test_empty_frame_returns_nonnegative(self):
        """An empty ArFrame must not raise and must return a non-negative int."""
        frame = ar.from_pandas(pd.DataFrame())
        result = frame.memory_usage()
        assert isinstance(result, int)
        assert result >= 0

    def test_explicit_false_matches_default(self):
        """memory_usage(deep=False) must equal memory_usage()."""
        df = pd.DataFrame({"text": ["hello", "world"]})
        frame = ar.from_pandas(df)
        assert frame.memory_usage(deep=False) == frame.memory_usage()


class TestMemoryUsageDeep:
    """memory_usage(deep=True) — precise estimate including string heap bytes."""

    def test_deep_greater_than_shallow_for_string_column(self):
        """For a string frame deep=True must report MORE bytes than deep=False."""
        # Use strings long enough to guarantee heap allocation (> SSO buffer).
        long_strings = ["x" * 100, "y" * 200, "z" * 300]
        df = pd.DataFrame({"text": long_strings})
        frame = ar.from_pandas(df)
        assert frame.memory_usage(deep=True) > frame.memory_usage(deep=False)

    def test_deep_equals_shallow_for_int_column(self):
        """For numeric columns deep has no extra effect — both values are equal."""
        df = pd.DataFrame({"n": [1, 2, 3, 4, 5]})
        frame = ar.from_pandas(df)
        assert frame.memory_usage(deep=True) == frame.memory_usage(deep=False)

    def test_deep_equals_shallow_for_float_column(self):
        df = pd.DataFrame({"f": [1.0, 2.0, 3.0]})
        frame = ar.from_pandas(df)
        assert frame.memory_usage(deep=True) == frame.memory_usage(deep=False)

    def test_deep_equals_shallow_for_bool_column(self):
        df = pd.DataFrame({"b": [True, False, True]})
        frame = ar.from_pandas(df)
        assert frame.memory_usage(deep=True) == frame.memory_usage(deep=False)

    def test_deep_greater_for_mixed_frame_with_strings(self):
        """Mixed frame: deep > shallow because of string columns."""
        df = pd.DataFrame(
            {
                "name": ["Alice" * 10, "Bob" * 20],
                "age": [30, 25],
            }
        )
        frame = ar.from_pandas(df)
        assert frame.memory_usage(deep=True) > frame.memory_usage(deep=False)

    def test_longer_strings_use_more_deep_memory(self):
        """A frame with longer strings must report more deep memory."""
        short_frame = ar.from_pandas(pd.DataFrame({"t": ["hi", "ok"]}))
        long_frame = ar.from_pandas(pd.DataFrame({"t": ["x" * 500, "y" * 500]}))
        assert long_frame.memory_usage(deep=True) > short_frame.memory_usage(deep=True)

    def test_deep_returns_int(self):
        df = pd.DataFrame({"s": ["hello", "world"]})
        frame = ar.from_pandas(df)
        assert isinstance(frame.memory_usage(deep=True), int)

    def test_empty_frame_deep_returns_nonnegative(self):
        frame = ar.from_pandas(pd.DataFrame())
        assert frame.memory_usage(deep=True) >= 0

    def test_null_string_column_deep_does_not_crash(self):
        """Columns with null strings must not raise under deep=True."""
        df = pd.DataFrame({"name": ["Alice", None, "Charlie"]}, dtype=object)
        frame = ar.from_pandas(df)
        result = frame.memory_usage(deep=True)
        assert isinstance(result, int)
        assert result > 0
