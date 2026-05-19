"""
Regression tests verifying arnio works with the oldest supported
pandas (>=1.5) and numpy (>=1.23) versions declared in pyproject.toml.
"""

import numpy as np
import pandas as pd

import arnio


def test_pandas_numpy_versions():
    """Ensure installed versions meet minimum requirements."""
    assert tuple(int(x) for x in pd.__version__.split(".")[:2]) >= (
        1,
        5,
    ), f"pandas {pd.__version__} is below minimum 1.5"
    assert tuple(int(x) for x in np.__version__.split(".")[:2]) >= (
        1,
        23,
    ), f"numpy {np.__version__} is below minimum 1.23"


def test_read_csv_with_oldest_deps(tmp_path):
    """read_csv works correctly under minimum pandas/numpy versions."""
    csv = tmp_path / "compat.csv"
    csv.write_text("name,age,score\nAlice,30,95.5\nBob,25,88.0\n")
    frame = arnio.read_csv(str(csv))
    assert frame is not None


def test_pandas_interop_with_oldest_deps(tmp_path):
    """to_pandas() produces a valid DataFrame under minimum versions."""
    csv = tmp_path / "compat.csv"
    csv.write_text("name,age,score\nAlice,30,95.5\nBob,25,88.0\n")
    frame = arnio.read_csv(str(csv))
    df = arnio.to_pandas(frame)
    assert isinstance(df, pd.DataFrame)
    assert list(df.columns) == ["name", "age", "score"]
    assert len(df) == 2


def test_numpy_dtype_compatibility(tmp_path):
    """Numeric columns produce numpy-compatible dtypes."""
    csv = tmp_path / "compat.csv"
    csv.write_text("name,age,score\nAlice,30,95.5\nBob,25,88.0\n")
    frame = arnio.read_csv(str(csv))
    df = arnio.to_pandas(frame)
    age_kind = (
        df["age"].dtype.kind
        if hasattr(df["age"].dtype, "kind")
        else str(df["age"].dtype)
    )
    score_kind = (
        df["score"].dtype.kind
        if hasattr(df["score"].dtype, "kind")
        else str(df["score"].dtype)
    )
    assert age_kind in ("i", "u", "f") or str(df["age"].dtype) in (
        "Int64",
        "Int32",
        "int64",
        "int32",
    )
    assert score_kind in ("f",) or str(df["score"].dtype) in ("Float64", "float64")
