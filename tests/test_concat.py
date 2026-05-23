import numpy as np
import pandas as pd
import pytest

import arnio as ar
from arnio import ArFrame


def test_basic_concat():
    df1 = pd.DataFrame(
        {"a": [1, 2], "b": [1.5, 2.5], "c": ["x", "y"], "d": [True, False]}
    )
    df2 = pd.DataFrame(
        {"a": [3, 4], "b": [3.5, 4.5], "c": ["z", "w"], "d": [False, True]}
    )

    f1 = ar.from_pandas(df1)
    f2 = ar.from_pandas(df2)

    res = ar.concat([f1, f2])
    assert isinstance(res, ArFrame)
    assert res.shape == (4, 4)
    assert res.columns == ["a", "b", "c", "d"]

    df_res = ar.to_pandas(res)
    pd.testing.assert_frame_equal(
        df_res, pd.concat([df1, df2]).reset_index(drop=True), check_dtype=False
    )


def test_schema_mismatch_raises():
    df1 = pd.DataFrame({"a": [1], "b": [2]})
    df2 = pd.DataFrame({"a": [3], "c": [4]})  # different column name
    df3 = pd.DataFrame({"b": [3], "a": [4]})  # different column order
    df4 = pd.DataFrame(
        {"a": [1.5], "b": [2.5]}
    )  # different dtype for 'a' (float vs int)

    f1 = ar.from_pandas(df1)
    f2 = ar.from_pandas(df2)
    f3 = ar.from_pandas(df3)
    f4 = ar.from_pandas(df4)

    with pytest.raises(ValueError, match="Column names or order do not match"):
        ar.concat([f1, f2])

    with pytest.raises(ValueError, match="Column names or order do not match"):
        ar.concat([f1, f3])

    with pytest.raises(TypeError, match="Column 'a' has mismatched dtypes"):
        ar.concat([f1, f4])


def test_empty_input_raises():
    with pytest.raises(
        ValueError, match="Cannot concatenate an empty list of ArFrames"
    ):
        ar.concat([])

    with pytest.raises(TypeError, match="frames must be a list"):
        ar.concat("not a list")  # type: ignore

    with pytest.raises(
        TypeError, match="All elements in frames must be ArFrame instances"
    ):
        ar.concat([1, 2, 3])  # type: ignore


def test_empty_frames_preserves_schema():
    df1 = pd.DataFrame(columns=["a", "b", "c"]).astype(
        {"a": "Int64", "b": "float64", "c": "string"}
    )
    df2 = pd.DataFrame(columns=["a", "b", "c"]).astype(
        {"a": "Int64", "b": "float64", "c": "string"}
    )

    f1 = ar.from_pandas(df1)
    f2 = ar.from_pandas(df2)

    res = ar.concat([f1, f2])
    assert res.shape == (0, 3)
    assert res.columns == ["a", "b", "c"]
    assert res.dtypes == {"a": "int64", "b": "float64", "c": "string"}

    df_res = ar.to_pandas(res)
    assert len(df_res) == 0
    assert list(df_res.columns) == ["a", "b", "c"]


def test_metadata_preservation_and_isolation():
    df1 = pd.DataFrame({"a": [1]})
    df1.attrs = {"owner": "test", "tags": ["tag1"]}
    df2 = pd.DataFrame({"a": [2]})
    df2.attrs = {"owner": "other"}

    f1 = ar.from_pandas(df1)
    f2 = ar.from_pandas(df2)

    res = ar.concat([f1, f2])
    assert res._attrs == {"owner": "test", "tags": ["tag1"]}

    # Mutating result attrs should not mutate source attrs
    res._attrs["owner"] = "mutated"
    res._attrs["tags"].append("tag2")

    assert f1._attrs == {"owner": "test", "tags": ["tag1"]}

    # Mutating source attrs should not mutate result attrs
    f1._attrs["owner"] = "source-mutated"
    assert res._attrs["owner"] == "mutated"


def test_null_mask_validation():
    df1 = pd.DataFrame(
        {"a": pd.Series([1, pd.NA, 3], dtype="Int64"), "b": [1.5, np.nan, 3.5]}
    )
    df2 = pd.DataFrame(
        {"a": pd.Series([pd.NA, 5, 6], dtype="Int64"), "b": [4.5, 5.5, np.nan]}
    )

    f1 = ar.from_pandas(df1)
    f2 = ar.from_pandas(df2)

    res = ar.concat([f1, f2])
    df_res = ar.to_pandas(res)

    assert df_res["a"].isna().tolist() == [False, True, False, True, False, False]
    assert df_res["b"].isna().tolist() == [False, True, False, False, False, True]

    pd.testing.assert_frame_equal(
        df_res.reset_index(drop=True),
        pd.concat([df1, df2]).reset_index(drop=True),
        check_dtype=False,
    )


def test_ignore_index_validation():
    df1 = pd.DataFrame({"a": [1]})
    f1 = ar.from_pandas(df1)

    # ignore_index=True works
    res = ar.concat([f1, f1], ignore_index=True)
    assert res.shape == (2, 1)

    # ignore_index=False raises ValueError
    with pytest.raises(
        ValueError,
        match="ArFrame does not support index columns; ignore_index must be True",
    ):
        ar.concat([f1, f1], ignore_index=False)

    with pytest.raises(TypeError, match="ignore_index must be a bool"):
        ar.concat([f1, f1], ignore_index="not_a_bool")  # type: ignore
