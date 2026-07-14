import arnio as ar


def test_frame_to_csv_basic(tmp_path):
    records = [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]
    frame = ar.ArFrame.from_records(records, columns=["id", "name"])

    out_path = tmp_path / "out.csv"

    # Use the convenience method
    frame.to_csv(out_path)

    assert out_path.exists()

    # Verify the contents were written correctly
    read_back = ar.read_csv(out_path)
    assert read_back.shape == (2, 2)
    assert read_back.columns == ["id", "name"]


def test_frame_to_csv_kwargs(tmp_path):
    records = [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]
    frame = ar.ArFrame.from_records(records, columns=["id", "name"])

    out_path = tmp_path / "out_kwargs.csv"

    # Test with kwargs
    frame.to_csv(out_path, delimiter="\t", write_header=False)

    assert out_path.exists()

    # Read back with matching kwargs
    read_back = ar.read_csv(out_path, delimiter="\t", has_header=False)
    assert read_back.shape == (2, 2)
    # the schema inference should assign generic col names since has_header=False
