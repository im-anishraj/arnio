import pandas as pd
import arnio as ar

def test_string_index_roundtrip():
    df = pd.DataFrame(
        {"a": [1, 2, 3]},
        index=["r1", "r2", "r3"]
    )

    frame = ar.from_pandas(df)
    out = ar.to_pandas(frame)

    assert list(out.index) == ["r1", "r2", "r3"]

def test_range_index_no_change():
    df = pd.DataFrame({"a": [1, 2, 3]})

    frame = ar.from_pandas(df)
    out = ar.to_pandas(frame)

    assert isinstance(out.index, pd.RangeIndex)

