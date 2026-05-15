from arnio.frame import ArFrame


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

    html = frame._repr_html_()

    assert "ArFrame Preview" in html
    assert "5 rows × 2 columns" in html
    assert "name" in html
    assert "age" in html