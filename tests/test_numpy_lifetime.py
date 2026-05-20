"""
Regression tests for NumPy binding lifetime safety (fixes #28).

to_numpy_float() and to_numpy_int() previously returned zero-copy NumPy
views into the C++ vector memory.  The NumPy array's lifetime was tied to
the Column Python wrapper via the `base` argument, which in turn was pinned
to the Frame via pybind11's reference_internal policy.  While that chain was
technically intact, any subtle change to the binding or call-site could
silently break it — and the issue was not covered by any test.

Fix applied: both methods now allocate a fresh NumPy-owned buffer and
memcpy the column data into it.  The resulting array has base=None, meaning
it holds no reference to the C++ Column or Frame objects whatsoever.  GC
cannot create a dangling pointer regardless of object lifetimes.

These tests verify:
  - Correct values after source Frame/Column are GC'd (primary goal)
  - arr.base is None (proves the copy path, would catch a regression to
    the zero-copy path where base != None)
  - Independence: mutating one copy does not affect another
  - Edge cases: empty, single-element, large columns

To confirm these tests would catch a regression, note that if `base` were
set to col_obj (the old zero-copy path), test_float_array_owns_its_buffer
and test_int_array_owns_its_buffer would both fail with `arr.base is not None`.
"""

import gc

import numpy as np
import pandas as pd
import pytest

import arnio as ar

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_float_frame():
    return ar.from_pandas(pd.DataFrame({"v": [1.5, 2.5, 3.5]}))


def _make_int_frame():
    return ar.from_pandas(
        pd.DataFrame({"n": pd.array([10, 20, 30], dtype=pd.Int64Dtype())})
    )


def _make_multicolumn_frame():
    return ar.from_pandas(
        pd.DataFrame(
            {
                "x": [0.1, 0.2, 0.3],
                "y": pd.array([1, 2, 3], dtype=pd.Int64Dtype()),
            }
        )
    )


# ---------------------------------------------------------------------------
# Buffer ownership — proves the copy path is active
# ---------------------------------------------------------------------------


class TestBufferOwnership:
    def test_float_array_owns_its_buffer(self):
        """
        After the fix, to_numpy_float() returns a copy-owned array.
        arr.base is None proves no C++ object is being referenced.

        If this test fails with `arr.base is not None`, the binding has
        regressed to the zero-copy path and is vulnerable to #28.
        """
        frame = _make_float_frame()
        arr = frame._frame.column_by_index(0).to_numpy_float()
        assert arr.base is None, (
            "to_numpy_float() returned a zero-copy view (base != None). "
            "Expected a copy-owned buffer after the #28 fix."
        )

    def test_int_array_owns_its_buffer(self):
        """
        After the fix, to_numpy_int() returns a copy-owned array.
        arr.base is None proves no C++ object is being referenced.

        If this test fails with `arr.base is not None`, the binding has
        regressed to the zero-copy path and is vulnerable to #28.
        """
        frame = _make_int_frame()
        arr = frame._frame.column_by_index(0).to_numpy_int()
        assert arr.base is None, (
            "to_numpy_int() returned a zero-copy view (base != None). "
            "Expected a copy-owned buffer after the #28 fix."
        )

    def test_float_array_is_writable(self):
        """Copy-owned arrays are writable — no read-only protection needed."""
        frame = _make_float_frame()
        arr = frame._frame.column_by_index(0).to_numpy_float()
        arr[0] = -1.0
        assert arr[0] == -1.0

    def test_int_array_is_writable(self):
        frame = _make_int_frame()
        arr = frame._frame.column_by_index(0).to_numpy_int()
        arr[0] = 999
        assert arr[0] == 999


# ---------------------------------------------------------------------------
# GC-stress: values survive after source Frame/Column are collected
# ---------------------------------------------------------------------------


class TestFloatNumpyLifetime:
    def test_float_values_survive_frame_and_column_gc(self):
        """
        Primary regression test for #28: del frame + del col + gc.collect()
        before reading the array.  With copy-owned buffers, GC cannot reach
        the array data regardless of what happens to the Column or Frame.
        """
        frame = _make_float_frame()
        col = frame._frame.column_by_index(0)
        arr = col.to_numpy_float()

        del col
        del frame
        gc.collect()
        gc.collect()

        assert pytest.approx(arr[0]) == 1.5
        assert pytest.approx(arr[1]) == 2.5
        assert pytest.approx(arr[2]) == 3.5

    def test_float_values_survive_multiple_gc_cycles(self):
        def _get():
            f = _make_float_frame()
            return f._frame.column_by_index(0).to_numpy_float()

        arr = _get()
        for _ in range(5):
            gc.collect()

        assert pytest.approx(list(arr)) == [1.5, 2.5, 3.5]

    def test_float_dtype_survives_gc(self):
        def _get():
            f = _make_float_frame()
            return f._frame.column_by_index(0).to_numpy_float()

        arr = _get()
        gc.collect()
        assert arr.dtype == np.float64

    def test_float_shape_survives_gc(self):
        def _get():
            f = _make_float_frame()
            return f._frame.column_by_index(0).to_numpy_float()

        arr = _get()
        gc.collect()
        assert arr.shape == (3,)


class TestIntNumpyLifetime:
    def test_int_values_survive_frame_and_column_gc(self):
        """Primary regression test for #28 (INT64 variant)."""
        frame = _make_int_frame()
        col = frame._frame.column_by_index(0)
        arr = col.to_numpy_int()

        del col
        del frame
        gc.collect()
        gc.collect()

        assert list(arr) == [10, 20, 30]

    def test_int_values_survive_multiple_gc_cycles(self):
        def _get():
            f = _make_int_frame()
            return f._frame.column_by_index(0).to_numpy_int()

        arr = _get()
        for _ in range(5):
            gc.collect()

        assert list(arr) == [10, 20, 30]

    def test_int_dtype_survives_gc(self):
        def _get():
            f = _make_int_frame()
            return f._frame.column_by_index(0).to_numpy_int()

        arr = _get()
        gc.collect()
        assert arr.dtype == np.int64


# ---------------------------------------------------------------------------
# Copy isolation — mutating one array cannot affect another
# ---------------------------------------------------------------------------


class TestCopyIsolation:
    def test_two_float_copies_are_independent(self):
        """
        Two to_numpy_float() calls on the same Column produce independent
        copies.  Mutating one must not affect the other.
        """
        frame = _make_float_frame()
        col = frame._frame.column_by_index(0)
        arr1 = col.to_numpy_float()
        arr2 = col.to_numpy_float()

        arr1[0] = -999.0
        assert pytest.approx(arr2[0]) == 1.5

    def test_two_int_copies_are_independent(self):
        frame = _make_int_frame()
        col = frame._frame.column_by_index(0)
        arr1 = col.to_numpy_int()
        arr2 = col.to_numpy_int()

        arr1[0] = -999
        assert arr2[0] == 10

    def test_mutating_copy_does_not_affect_frame(self):
        """
        Mutating the returned NumPy array must not modify the C++ Frame's
        internal data (copy semantics guarantee this).
        """
        frame = _make_float_frame()
        arr = frame._frame.column_by_index(0).to_numpy_float()

        arr[0] = -999.0

        # Read back from the frame — should still see original value
        second = frame._frame.column_by_index(0).to_numpy_float()
        assert pytest.approx(second[0]) == 1.5


# ---------------------------------------------------------------------------
# Multi-column: both columns survive GC
# ---------------------------------------------------------------------------


class TestMultiColumnLifetime:
    def test_both_columns_survive_frame_gc(self):
        frame = _make_multicolumn_frame()
        arr_x = frame._frame.column_by_index(0).to_numpy_float()
        arr_y = frame._frame.column_by_index(1).to_numpy_int()

        del frame
        gc.collect()

        assert pytest.approx(list(arr_x)) == [0.1, 0.2, 0.3]
        assert list(arr_y) == [1, 2, 3]


# ---------------------------------------------------------------------------
# High-frequency GC stress (simulates to_pandas() loop)
# ---------------------------------------------------------------------------


class TestHighFrequencyGcStress:
    def test_repeated_frame_column_array_cycle(self):
        """
        Simulates the exact pattern in convert.py's to_pandas() loop:
        create frame, call column_by_index + to_numpy_* per column, discard
        the frame, then verify the surviving arrays.

        50 iterations with gc.collect() between each to maximise pressure.
        """
        expected_float = [float(i) * 0.5 for i in range(10)]
        expected_int = list(range(10))

        arrays = []
        for _ in range(50):
            df = pd.DataFrame(
                {
                    "f": expected_float,
                    "i": pd.array(expected_int, dtype=pd.Int64Dtype()),
                }
            )
            frame = ar.from_pandas(df)
            arr_f = frame._frame.column_by_index(0).to_numpy_float()
            arr_i = frame._frame.column_by_index(1).to_numpy_int()
            arrays.append((arr_f, arr_i))
            del frame
            gc.collect()

        for arr_f, arr_i in arrays:
            assert pytest.approx(list(arr_f)) == expected_float
            assert list(arr_i) == expected_int


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_empty_float_column(self):
        df = pd.DataFrame({"v": pd.Series([], dtype="float64")})
        frame = ar.from_pandas(df)
        arr = frame._frame.column_by_index(0).to_numpy_float()
        del frame
        gc.collect()
        assert arr.shape == (0,)
        assert arr.dtype == np.float64
        assert arr.base is None

    def test_empty_int_column(self):
        df = pd.DataFrame({"v": pd.Series([], dtype=pd.Int64Dtype())})
        frame = ar.from_pandas(df)
        arr = frame._frame.column_by_index(0).to_numpy_int()
        del frame
        gc.collect()
        assert arr.shape == (0,)
        assert arr.base is None

    def test_single_element_float(self):
        df = pd.DataFrame({"v": [42.0]})
        frame = ar.from_pandas(df)
        arr = frame._frame.column_by_index(0).to_numpy_float()
        del frame
        gc.collect()
        assert pytest.approx(arr[0]) == 42.0

    def test_single_element_int(self):
        df = pd.DataFrame({"v": pd.array([7], dtype=pd.Int64Dtype())})
        frame = ar.from_pandas(df)
        arr = frame._frame.column_by_index(0).to_numpy_int()
        del frame
        gc.collect()
        assert arr[0] == 7

    def test_large_float_column(self):
        data = [float(i) / 3.0 for i in range(10_000)]
        df = pd.DataFrame({"v": data})
        frame = ar.from_pandas(df)
        arr = frame._frame.column_by_index(0).to_numpy_float()
        del frame
        for _ in range(3):
            gc.collect()
        assert pytest.approx(arr[0]) == data[0]
        assert pytest.approx(arr[9999]) == data[9999]

    def test_large_int_column(self):
        data = list(range(10_000))
        df = pd.DataFrame({"v": pd.array(data, dtype=pd.Int64Dtype())})
        frame = ar.from_pandas(df)
        arr = frame._frame.column_by_index(0).to_numpy_int()
        del frame
        for _ in range(3):
            gc.collect()
        assert arr[0] == 0
        assert arr[9999] == 9999
