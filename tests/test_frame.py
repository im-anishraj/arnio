from arnio.frame import ArFrame
from arnio.convert import from_pandas
import pandas as pd
import html


class DummyFrame:
    def shape(self):
        return (5, 2)

    def column_names(self):
        return ["name", "age"]

    def dtypes(self):
        return {"name": "str", "age": "int"}

    def memory_usage(self):
        return 100

    def num_rows(self):
        return 5


def test_repr_html():
    frame = ArFrame(DummyFrame())

    output = frame._repr_html_()

    assert "ArFrame Preview" in output
    assert "5 rows × 2 columns" in output
    assert "name" in output
    assert "age" in output


def test_repr_html_from_pandas():
    df = pd.DataFrame(
        {
            "name": ["Alice", "Bob"],
            "age": [20, 25],
        }
    )

    frame = from_pandas(df)

    output = frame._repr_html_()

    assert "ArFrame Preview" in output
    assert "2 rows × 2 columns" in output
    assert "name" in output
    assert "age" in output


def test_repr_html_escapes_html():
    df = pd.DataFrame({"<script>": ["value"]})

    frame = from_pandas(df)

    output = frame._repr_html_()

    assert html.escape("<script>") in output
    assert "<script>" not in output
