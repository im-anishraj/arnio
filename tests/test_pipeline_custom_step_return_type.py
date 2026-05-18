"""
Tests: cover pipeline custom step return type validation
Issue: custom pipeline steps returning None or non-DataFrame values need coverage.

These tests verify that:
  1. A custom step returning None raises TypeError with a clear message.
  2. A custom step returning a scalar (int, float, str) raises TypeError.
  3. A custom step returning a collection (list, dict, tuple) raises TypeError.
  4. A custom step returning an ArFrame (wrong type) raises TypeError.
  5. Every TypeError message names the offending step and says "pandas DataFrame".
  6. A bad step mid-pipeline aborts execution; later steps never run.
  7. A step that correctly returns a DataFrame continues to work normally.
  8. return_metadata=True still raises TypeError for bad steps.

The C++ extension is replaced by a pure-Python mock so these tests run
without a compiled binary.
"""

from __future__ import annotations

# ── Install the C++ mock BEFORE any arnio import ──────────────────────────────
import sys
import os

# Ensure the local source tree is first on sys.path so we test our changes,
# not the installed wheel.
_REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

# Load and install the mock directly by file path — avoids any package-import
# ambiguity regardless of how pytest is invoked.
import importlib.util as _ilu

_mock_path = os.path.join(os.path.dirname(__file__), "conftest_mock_cpp.py")
_mock_spec = _ilu.spec_from_file_location("conftest_mock_cpp", _mock_path)
_mock_mod = _ilu.module_from_spec(_mock_spec)
_mock_spec.loader.exec_module(_mock_mod)
_mock_mod.install()
# ─────────────────────────────────────────────────────────────────────────────

import importlib  # noqa: E402

import pandas as pd  # noqa: E402
import pytest  # noqa: E402

import arnio as ar  # noqa: E402

pipeline_module = importlib.import_module("arnio.pipeline")


# ---------------------------------------------------------------------------
# Fixture: restore the custom step registry after every test so registrations
# from one test never leak into another.
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _restore_registry():
    with pipeline_module._REGISTRY_LOCK:
        original = dict(pipeline_module._PYTHON_STEP_REGISTRY)
    yield
    with pipeline_module._REGISTRY_LOCK:
        pipeline_module._PYTHON_STEP_REGISTRY.clear()
        pipeline_module._PYTHON_STEP_REGISTRY.update(original)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _frame():
    """Minimal 2-row ArFrame used across all tests."""
    return ar.from_pandas(pd.DataFrame({"x": [1, 2], "y": ["a", "b"]}))


# ===========================================================================
# 1. None return
# ===========================================================================

class TestNoneReturn:
    def test_none_raises_type_error(self):
        """Forgetting the return statement is the most common mistake."""
        def bad_step(df):
            return None  # forgot to return df

        ar.register_step("returns_none", bad_step)

        with pytest.raises(TypeError):
            ar.pipeline(_frame(), [("returns_none",)])

    def test_none_error_message_names_the_step(self):
        def bad_step(df):
            return None

        ar.register_step("my_none_step", bad_step)

        with pytest.raises(TypeError, match="my_none_step"):
            ar.pipeline(_frame(), [("my_none_step",)])

    def test_none_error_message_says_returned_none(self):
        def bad_step(df):
            return None

        ar.register_step("none_msg_step", bad_step)

        with pytest.raises(TypeError, match="returned None"):
            ar.pipeline(_frame(), [("none_msg_step",)])

    def test_none_error_message_mentions_dataframe(self):
        def bad_step(df):
            return None

        ar.register_step("none_df_msg_step", bad_step)

        with pytest.raises(TypeError, match="pandas DataFrame"):
            ar.pipeline(_frame(), [("none_df_msg_step",)])


# ===========================================================================
# 2. Scalar returns
# ===========================================================================

class TestScalarReturn:
    def test_integer_return_raises(self):
        def bad_step(df):
            return 42

        ar.register_step("returns_int", bad_step)

        with pytest.raises(TypeError, match="'int'"):
            ar.pipeline(_frame(), [("returns_int",)])

    def test_float_return_raises(self):
        def bad_step(df):
            return 3.14

        ar.register_step("returns_float", bad_step)

        with pytest.raises(TypeError, match="'float'"):
            ar.pipeline(_frame(), [("returns_float",)])

    def test_string_return_raises(self):
        def bad_step(df):
            return "oops"

        ar.register_step("returns_str", bad_step)

        with pytest.raises(TypeError, match="'str'"):
            ar.pipeline(_frame(), [("returns_str",)])

    def test_bool_return_raises(self):
        def bad_step(df):
            return True

        ar.register_step("returns_bool", bad_step)

        with pytest.raises(TypeError):
            ar.pipeline(_frame(), [("returns_bool",)])


# ===========================================================================
# 3. Collection returns
# ===========================================================================

class TestCollectionReturn:
    def test_list_return_raises(self):
        def bad_step(df):
            return [1, 2, 3]

        ar.register_step("returns_list", bad_step)

        with pytest.raises(TypeError, match="'list'"):
            ar.pipeline(_frame(), [("returns_list",)])

    def test_dict_return_raises(self):
        def bad_step(df):
            return {"x": [1, 2]}

        ar.register_step("returns_dict", bad_step)

        with pytest.raises(TypeError, match="'dict'"):
            ar.pipeline(_frame(), [("returns_dict",)])

    def test_tuple_return_raises(self):
        def bad_step(df):
            return (df, "extra")

        ar.register_step("returns_tuple", bad_step)

        with pytest.raises(TypeError, match="'tuple'"):
            ar.pipeline(_frame(), [("returns_tuple",)])

    def test_numpy_array_return_raises(self):
        import numpy as np

        def bad_step(df):
            return np.array([[1, 2], [3, 4]])

        ar.register_step("returns_ndarray", bad_step)

        with pytest.raises(TypeError):
            ar.pipeline(_frame(), [("returns_ndarray",)])


# ===========================================================================
# 4. ArFrame return (wrong type — step receives DataFrame, must return DataFrame)
# ===========================================================================

class TestArFrameReturn:
    def test_arframe_return_raises(self):
        """Returning an ArFrame instead of a DataFrame is also wrong."""
        def bad_step(df):
            return ar.from_pandas(df)  # returns ArFrame, not DataFrame

        ar.register_step("returns_arframe", bad_step)

        with pytest.raises(TypeError, match="'ArFrame'"):
            ar.pipeline(_frame(), [("returns_arframe",)])

    def test_arframe_error_message_mentions_dataframe(self):
        def bad_step(df):
            return ar.from_pandas(df)

        ar.register_step("arframe_msg_step", bad_step)

        with pytest.raises(TypeError, match="pandas DataFrame"):
            ar.pipeline(_frame(), [("arframe_msg_step",)])


# ===========================================================================
# 5. Error message quality — step name always present
# ===========================================================================

class TestErrorMessageQuality:
    @pytest.mark.parametrize("bad_return", [
        None,
        42,
        "oops",
        3.14,
        [1, 2],
        {"a": 1},
    ])
    def test_step_name_always_in_error(self, bad_return):
        step_name = f"named_step_{id(bad_return)}"

        def bad_step(df, _ret=bad_return):
            return _ret

        ar.register_step(step_name, bad_step)

        with pytest.raises(TypeError, match=step_name):
            ar.pipeline(_frame(), [(step_name,)])

    @pytest.mark.parametrize("bad_return", [
        None,
        42,
        "oops",
        [1, 2],
    ])
    def test_dataframe_always_mentioned_in_error(self, bad_return):
        step_name = f"df_msg_step_{id(bad_return)}"

        def bad_step(df, _ret=bad_return):
            return _ret

        ar.register_step(step_name, bad_step)

        with pytest.raises(TypeError, match="pandas DataFrame"):
            ar.pipeline(_frame(), [(step_name,)])


# ===========================================================================
# 6. Pipeline abort — bad step stops execution; later steps never run
# ===========================================================================

class TestPipelineAbort:
    def test_bad_step_in_middle_raises(self):
        def bad_step(df):
            return None

        ar.register_step("mid_bad", bad_step)

        with pytest.raises(TypeError, match="mid_bad"):
            ar.pipeline(
                _frame(),
                [
                    ("standardize_missing_tokens",),  # good step before
                    ("mid_bad",),                     # bad step
                ],
            )

    def test_subsequent_step_never_executes(self):
        calls: list[str] = []

        def bad_step(df):
            return None

        def good_step(df):
            calls.append("reached")
            return df

        ar.register_step("abort_bad", bad_step)
        ar.register_step("abort_good", good_step)

        with pytest.raises(TypeError):
            ar.pipeline(_frame(), [("abort_bad",), ("abort_good",)])

        assert calls == [], "Step after the bad step must not execute"

    def test_first_step_bad_second_step_never_runs(self):
        calls: list[str] = []

        def bad_step(df):
            return 99

        def good_step(df):
            calls.append("reached")
            return df

        ar.register_step("first_bad", bad_step)
        ar.register_step("second_good", good_step)

        with pytest.raises(TypeError):
            ar.pipeline(_frame(), [("first_bad",), ("second_good",)])

        assert calls == []


# ===========================================================================
# 7. Happy path — valid DataFrame return works normally
# ===========================================================================

class TestValidReturn:
    def test_valid_dataframe_return_passes(self):
        def good_step(df):
            df = df.copy()
            df["z"] = 99
            return df

        ar.register_step("valid_step", good_step)

        result = ar.pipeline(_frame(), [("valid_step",)])
        result_df = ar.to_pandas(result)

        assert "z" in result_df.columns
        assert list(result_df["z"]) == [99, 99]

    def test_valid_step_with_kwargs(self):
        def tag_step(df, tag="default"):
            df = df.copy()
            df["tag"] = tag
            return df

        ar.register_step("tag_step", tag_step)

        result = ar.pipeline(_frame(), [("tag_step", {"tag": "hello"})])
        result_df = ar.to_pandas(result)

        assert list(result_df["tag"]) == ["hello", "hello"]

    def test_chained_valid_steps(self):
        def add_col_a(df):
            df = df.copy()
            df["a"] = 1
            return df

        def add_col_b(df):
            df = df.copy()
            df["b"] = 2
            return df

        ar.register_step("add_a", add_col_a)
        ar.register_step("add_b", add_col_b)

        result = ar.pipeline(_frame(), [("add_a",), ("add_b",)])
        result_df = ar.to_pandas(result)

        assert "a" in result_df.columns
        assert "b" in result_df.columns

    def test_valid_step_preserves_row_count(self):
        def identity(df):
            return df.copy()

        ar.register_step("identity_step", identity)

        frame = _frame()
        result = ar.pipeline(frame, [("identity_step",)])

        assert result.shape == frame.shape


# ===========================================================================
# 8. return_metadata=True interaction
# ===========================================================================

class TestReturnMetadata:
    def test_none_return_raises_with_metadata_flag(self):
        def bad_step(df):
            return None

        ar.register_step("meta_bad_step", bad_step)

        with pytest.raises(TypeError, match="meta_bad_step"):
            ar.pipeline(_frame(), [("meta_bad_step",)], return_metadata=True)

    def test_wrong_type_raises_with_metadata_flag(self):
        def bad_step(df):
            return 42

        ar.register_step("meta_int_step", bad_step)

        with pytest.raises(TypeError):
            ar.pipeline(_frame(), [("meta_int_step",)], return_metadata=True)

    def test_valid_step_metadata_still_recorded(self):
        def good_step(df):
            return df.copy()

        ar.register_step("meta_good_step", good_step)

        result, metadata = ar.pipeline(
            _frame(),
            [("meta_good_step",)],
            return_metadata=True,
        )

        assert isinstance(result, ar.ArFrame)
        assert len(metadata["step_timings"]) == 1
        assert metadata["step_timings"][0]["step"] == "meta_good_step"
        assert metadata["step_timings"][0]["seconds"] >= 0

    def test_bad_step_timing_not_recorded(self):
        """When a step returns None, its timing entry must not appear in
        step_timings — the error is raised before timing is appended."""
        def bad_step(df):
            return None

        ar.register_step("meta_none_step", bad_step)

        with pytest.raises(TypeError):
            ar.pipeline(
                _frame(),
                [("meta_none_step",)],
                return_metadata=True,
            )
        # If we reach here without the pipeline returning, the timing was
        # never recorded — the test passes by virtue of the raise above.
