"""Tests: custom pipeline step return-type validation (Fixes #630).

Covers the validation guard added to the Python custom-step path in
arnio/pipeline.py that raises TypeError before from_pandas() is reached
when a step returns None or a non-DataFrame value.
"""

import importlib

import numpy as np
import pandas as pd
import pytest

import arnio as ar

pipeline_module = importlib.import_module("arnio.pipeline")


@pytest.fixture(autouse=True)
def restore_python_step_registry():
    """Restore the custom step registry after every test.

    Mirrors the fixture in test_pipeline.py so step registrations from one
    test never leak into another.
    """
    with pipeline_module._REGISTRY_LOCK:
        original = dict(pipeline_module._PYTHON_STEP_REGISTRY)
    yield
    with pipeline_module._REGISTRY_LOCK:
        pipeline_module._PYTHON_STEP_REGISTRY.clear()
        pipeline_module._PYTHON_STEP_REGISTRY.update(original)


@pytest.fixture()
def small_frame():
    """Minimal 2-row ArFrame reused across tests."""
    return ar.from_pandas(pd.DataFrame({"x": [1, 2], "y": ["a", "b"]}))


# ---------------------------------------------------------------------------
# None return
# ---------------------------------------------------------------------------


def test_none_return_raises_type_error(small_frame):
    """Forgetting the return statement is the most common mistake."""

    def bad_step(df):
        return None  # forgot to return df

    ar.register_step("returns_none", bad_step)

    with pytest.raises(TypeError, match="returned None"):
        ar.pipeline(small_frame, [("returns_none",)])


def test_none_error_names_the_step(small_frame):
    def bad_step(df):
        return None

    ar.register_step("my_none_step", bad_step)

    with pytest.raises(TypeError, match="my_none_step"):
        ar.pipeline(small_frame, [("my_none_step",)])


def test_none_error_mentions_dataframe(small_frame):
    def bad_step(df):
        return None

    ar.register_step("none_df_step", bad_step)

    with pytest.raises(TypeError, match="pandas DataFrame"):
        ar.pipeline(small_frame, [("none_df_step",)])


# ---------------------------------------------------------------------------
# Scalar returns
# ---------------------------------------------------------------------------


def test_integer_return_raises(small_frame):
    def bad_step(df):
        return 42

    ar.register_step("returns_int", bad_step)

    with pytest.raises(TypeError, match="'int'"):
        ar.pipeline(small_frame, [("returns_int",)])


def test_float_return_raises(small_frame):
    def bad_step(df):
        return 3.14

    ar.register_step("returns_float", bad_step)

    with pytest.raises(TypeError, match="'float'"):
        ar.pipeline(small_frame, [("returns_float",)])


def test_string_return_raises(small_frame):
    def bad_step(df):
        return "oops"

    ar.register_step("returns_str", bad_step)

    with pytest.raises(TypeError, match="'str'"):
        ar.pipeline(small_frame, [("returns_str",)])


# ---------------------------------------------------------------------------
# Collection returns
# ---------------------------------------------------------------------------


def test_list_return_raises(small_frame):
    def bad_step(df):
        return [1, 2, 3]

    ar.register_step("returns_list", bad_step)

    with pytest.raises(TypeError, match="'list'"):
        ar.pipeline(small_frame, [("returns_list",)])


def test_dict_return_raises(small_frame):
    def bad_step(df):
        return {"x": [1, 2]}

    ar.register_step("returns_dict", bad_step)

    with pytest.raises(TypeError, match="'dict'"):
        ar.pipeline(small_frame, [("returns_dict",)])


def test_tuple_return_raises(small_frame):
    def bad_step(df):
        return (df, "extra")

    ar.register_step("returns_tuple", bad_step)

    with pytest.raises(TypeError, match="'tuple'"):
        ar.pipeline(small_frame, [("returns_tuple",)])


def test_numpy_array_return_raises(small_frame):
    def bad_step(df):
        return np.array([[1, 2], [3, 4]])

    ar.register_step("returns_ndarray", bad_step)

    with pytest.raises(TypeError):
        ar.pipeline(small_frame, [("returns_ndarray",)])


# ---------------------------------------------------------------------------
# ArFrame return (wrong type — step receives DataFrame, must return DataFrame)
# ---------------------------------------------------------------------------


def test_arframe_return_raises(small_frame):
    """Returning an ArFrame instead of a DataFrame is also wrong."""

    def bad_step(df):
        return ar.from_pandas(df)  # ArFrame, not DataFrame

    ar.register_step("returns_arframe", bad_step)

    with pytest.raises(TypeError, match="'ArFrame'"):
        ar.pipeline(small_frame, [("returns_arframe",)])


# ---------------------------------------------------------------------------
# Pipeline abort — bad step stops execution; later steps never run
# ---------------------------------------------------------------------------


def test_subsequent_step_never_executes_after_bad_step(small_frame):
    calls = []

    def bad_step(df):
        return None

    def good_step(df):
        calls.append("reached")
        return df

    ar.register_step("abort_bad", bad_step)
    ar.register_step("abort_good", good_step)

    with pytest.raises(TypeError):
        ar.pipeline(small_frame, [("abort_bad",), ("abort_good",)])

    assert calls == [], "Step after the bad step must not execute"


def test_bad_step_mid_pipeline_raises_at_that_step(small_frame):
    def bad_step(df):
        return None

    ar.register_step("mid_bad", bad_step)

    with pytest.raises(TypeError, match="mid_bad"):
        ar.pipeline(
            small_frame,
            [
                ("standardize_missing_tokens",),
                ("mid_bad",),
            ],
        )


# ---------------------------------------------------------------------------
# Happy path — valid DataFrame return works normally
# ---------------------------------------------------------------------------


def test_valid_dataframe_return_passes(small_frame):
    def good_step(df):
        df = df.copy()
        df["z"] = 99
        return df

    ar.register_step("valid_step", good_step)

    result = ar.pipeline(small_frame, [("valid_step",)])
    result_df = ar.to_pandas(result)

    assert "z" in result_df.columns
    assert list(result_df["z"]) == [99, 99]


def test_valid_step_with_kwargs_passes(small_frame):
    def tag_step(df, tag="default"):
        df = df.copy()
        df["tag"] = tag
        return df

    ar.register_step("tag_step", tag_step)

    result = ar.pipeline(small_frame, [("tag_step", {"tag": "hello"})])
    result_df = ar.to_pandas(result)

    assert list(result_df["tag"]) == ["hello", "hello"]


def test_custom_step_receives_writable_numeric_array():
    frame = ar.from_pandas(pd.DataFrame({"x": [1.0, 2.0]}))
    writeable_flags = []

    def mutate_numpy_in_place(df):
        values = df["x"].to_numpy()
        writeable_flags.append(values.flags.writeable)
        values[0] = 99.0
        return df

    ar.register_step("mutate_numpy_in_place", mutate_numpy_in_place)

    result = ar.pipeline(frame, [("mutate_numpy_in_place",)])
    result_df = ar.to_pandas(result)

    assert writeable_flags == [True]
    assert list(result_df["x"]) == [99.0, 2.0]


# ---------------------------------------------------------------------------
# return_metadata=True compatibility
# ---------------------------------------------------------------------------


def test_none_return_raises_with_return_metadata(small_frame):
    def bad_step(df):
        return None

    ar.register_step("meta_bad_step", bad_step)

    with pytest.raises(TypeError, match="meta_bad_step"):
        ar.pipeline(small_frame, [("meta_bad_step",)], return_metadata=True)


def test_wrong_type_raises_with_return_metadata(small_frame):
    def bad_step(df):
        return 42

    ar.register_step("meta_int_step", bad_step)

    with pytest.raises(TypeError):
        ar.pipeline(small_frame, [("meta_int_step",)], return_metadata=True)


def test_valid_step_metadata_recorded(small_frame):
    def good_step(df):
        return df.copy()

    ar.register_step("meta_good_step", good_step)

    result, metadata = ar.pipeline(
        small_frame,
        [("meta_good_step",)],
        return_metadata=True,
    )

    assert isinstance(result, ar.ArFrame)
    assert len(metadata["step_timings"]) == 1
    assert metadata["step_timings"][0]["step"] == "meta_good_step"
    assert metadata["step_timings"][0]["seconds"] >= 0
