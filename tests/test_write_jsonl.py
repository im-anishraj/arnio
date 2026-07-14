import inspect
import json

import pandas as pd
import pytest

import arnio as ar


def test_write_jsonl_normal_frame(tmp_path):
    frame = ar.from_pandas(
        pd.DataFrame({"id": [1, 2], "name": ["Alice", "Bob"], "score": [10.5, None]})
    )
    path = tmp_path / "test.jsonl"
    ar.write_jsonl(frame, path)
    text = path.read_text(encoding="utf-8")
    assert text.endswith("\n")
    lines = text.splitlines()
    assert len(lines) == 2
    assert [json.loads(line) for line in lines] == [
        {"id": 1, "name": "Alice", "score": 10.5},
        {"id": 2, "name": "Bob", "score": None},
    ]


def test_write_jsonl_empty_frame(tmp_path):
    frame = ar.from_pandas(pd.DataFrame({"id": [], "name": []}))

    path = tmp_path / "empty.jsonl"
    ar.write_jsonl(frame, path)

    assert path.read_text(encoding="utf-8") == ""


@pytest.mark.parametrize("suffix", [".jsonl", ".ndjson"])
def test_write_jsonl_supported_extensions(tmp_path, suffix):
    frame = ar.from_pandas(pd.DataFrame({"id": [1]}))

    path = tmp_path / f"out{suffix}"
    ar.write_jsonl(frame, path)

    assert json.loads(path.read_text(encoding="utf-8").strip()) == {"id": 1}


def test_write_jsonl_rejects_unsupported_extension(tmp_path):
    frame = ar.from_pandas(pd.DataFrame({"id": [1]}))

    with pytest.raises(ValueError, match=".jsonl|.ndjson"):
        ar.write_jsonl(frame, tmp_path / "out.json")


def test_write_jsonl_rejects_invalid_frame(tmp_path):
    with pytest.raises(TypeError, match="frame must be an ArFrame"):
        ar.write_jsonl(object(), tmp_path / "out.jsonl")


def test_write_jsonl_rejects_invalid_path():
    frame = ar.from_pandas(pd.DataFrame({"id": [1]}))

    with pytest.raises(TypeError, match="path must be"):
        ar.write_jsonl(frame, 123)


def test_write_jsonl_rejects_invalid_encoding(tmp_path):
    frame = ar.from_pandas(pd.DataFrame({"id": [1]}))

    with pytest.raises((TypeError, ValueError)):
        ar.write_jsonl(frame, tmp_path / "out.jsonl", encoding="not-a-real-codec")


def test_write_jsonl_rejects_invalid_encoding_errors(tmp_path):
    frame = ar.from_pandas(pd.DataFrame({"id": [1]}))

    with pytest.raises(ValueError, match="encoding_errors"):
        ar.write_jsonl(frame, tmp_path / "out.jsonl", encoding_errors="bad-mode")


def test_write_jsonl_non_utf8_output(tmp_path):
    frame = ar.from_pandas(pd.DataFrame({"name": ["café"]}))

    path = tmp_path / "latin1.jsonl"
    ar.write_jsonl(frame, path, encoding="latin-1")

    assert path.read_text(encoding="latin-1") == '{"name":"café"}\n'


def test_write_jsonl_encoding_errors_replace(tmp_path):
    frame = ar.from_pandas(pd.DataFrame({"name": ["₹"]}))

    path = tmp_path / "latin1.jsonl"
    ar.write_jsonl(
        frame,
        path,
        encoding="latin-1",
        encoding_errors="replace",
    )

    assert path.read_text(encoding="latin-1") == '{"name":"?"}\n'


def test_write_jsonl_is_exported():
    assert hasattr(ar, "write_jsonl")


def test_write_jsonl_signature():

    sig = inspect.signature(ar.write_jsonl)
    assert list(sig.parameters) == [
        "frame",
        "path",
        "encoding",
        "encoding_errors",
    ]
    assert sig.parameters["encoding"].default == "utf-8"
    assert sig.parameters["encoding_errors"].default == "strict"
