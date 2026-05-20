from arnio.frame import ArFrame
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


class EscapeFrame:
    def shape(self):
        return (1, 1)

    def column_names(self):
        return ["<script>"]

    def dtypes(self):
        return {"<script>": "str"}

    def memory_usage(self):
        return 10

    def num_rows(self):
        return 1


def test_repr_html_escapes_html():
    frame = ArFrame(EscapeFrame())

    output = frame._repr_html_()

    assert html.escape("<script>") in output
    assert "<script>" not in output
