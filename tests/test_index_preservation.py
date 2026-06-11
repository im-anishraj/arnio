import pandas as pd
import arnio as ar

def test_string_index_roundtrip():
    df = pd.DataFrame(
        {"name": ["Alice", "Bob", "Charlie"]},
        index=["row_1", "row_2", "row_3"]
    )

    frame = ar.from_pandas(df)
    result = ar.to_pandas(frame)

    assert result.index.tolist() == df.index.tolist()


def test_datetime_index_roundtrip():
    df = pd.DataFrame(
        {"value": [1, 2, 3]},
        index=pd.date_range("2025-01-01", periods=3)
    )

    frame = ar.from_pandas(df)
    result = ar.to_pandas(frame)

    assert result.index.equals(df.index)