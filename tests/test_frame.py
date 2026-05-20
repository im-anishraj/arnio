import pandas as pd

import arnio as ar


def test_repr_html():
    df = pd.DataFrame(
        {
            "name": ["Alice", "Bob"],
            "age": [25, 30],
        }
    )

    frame = ar.from_pandas(df)

    html = frame._repr_html_()

    assert "ArFrame Preview" in html
    assert "2 rows × 2 columns" in html
    assert "name" in html
    assert "age" in html


def test_repr_html_escapes_special_characters():
    df = pd.DataFrame(
        {
            "<script>": ["value"],
        }
    )

    frame = ar.from_pandas(df)

    html = frame._repr_html_()

    assert "<script>" not in html
    assert "&lt;script&gt;" in html
