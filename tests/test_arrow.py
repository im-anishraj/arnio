import pytest

from arnio import ArFrame, from_arrow, to_pandas

# Mark all tests in this file as requiring the 'arrow' dependency
pytestmark = pytest.mark.arrow


@pytest.fixture
def sample_arrow_table():
    pa = pytest.importorskip("pyarrow")
    return pa.Table.from_pydict(
        {
            "int": [1, 2, 3, None],
            "float": [1.1, 2.2, 3.3, None],
            "bool": [True, False, True, None],
            "str": ["a", "b", "c", None],
        }
    )


def test_from_arrow_smoke(sample_arrow_table):
    frame = from_arrow(sample_arrow_table)
    assert isinstance(frame, ArFrame)
    assert frame.shape == (4, 4)


def test_from_arrow_data_integrity(sample_arrow_table):
    import pandas as pd

    frame = from_arrow(sample_arrow_table)
    df = to_pandas(frame)

    assert df["int"].iloc[0] == 1
    assert df["float"].iloc[1] == 2.2
    assert df["bool"].iloc[2]
    assert pd.isna(df["str"].iloc[3])
    assert df["int"].isna().sum() == 1


def test_from_arrow_missing_dependency(monkeypatch):
    import sys

    monkeypatch.setitem(sys.modules, "pyarrow", None)
    with pytest.raises(ImportError, match="pyarrow is not installed"):
        from arnio.convert import from_arrow

        from_arrow(None)


def test_from_arrow_invalid_input():
    pytest.importorskip("pyarrow")
    with pytest.raises(TypeError, match="Expected a PyArrow Table"):
        from_arrow("not a table")


def test_from_arrow_chunked_array():
    pa = pytest.importorskip("pyarrow")
    # Create a table with a chunked array
    arr = pa.chunked_array([[1, 2], [3, 4]])
    table = pa.Table.from_arrays([arr], names=["chunked"])

    frame = from_arrow(table)
    df = to_pandas(frame)

    assert df.shape == (4, 1)
    assert df["chunked"].tolist() == [1, 2, 3, 4]
