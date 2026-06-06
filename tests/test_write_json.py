import json
import pathlib

import pytest

import arnio as ar
from arnio.frame import ArFrame


@pytest.fixture
def sample_frame() -> ArFrame:
    return ar.from_dict(
        {
            "id": [1, 2, 3],
            "name": ["Alice", "Bob", "Charlie"],
            "active": [True, False, True],
        }
    )


def test_write_json_records(sample_frame: ArFrame, tmp_path: pathlib.Path) -> None:
    output_file = tmp_path / "output.json"
    ar.write_json(sample_frame, output_file)

    assert output_file.exists()

    with open(output_file, encoding="utf-8") as f:
        data = json.load(f)

    assert isinstance(data, list)
    assert len(data) == 3
    assert data[0] == {"id": 1, "name": "Alice", "active": True}
    assert data[1] == {"id": 2, "name": "Bob", "active": False}
    assert data[2] == {"id": 3, "name": "Charlie", "active": True}


def test_write_json_list(sample_frame: ArFrame, tmp_path: pathlib.Path) -> None:
    output_file = tmp_path / "output_list.json"
    ar.write_json(sample_frame, output_file, orient="list")

    assert output_file.exists()

    with open(output_file, encoding="utf-8") as f:
        data = json.load(f)

    assert isinstance(data, dict)
    assert "id" in data
    assert "name" in data
    assert "active" in data
    assert data["id"] == [1, 2, 3]
    assert data["name"] == ["Alice", "Bob", "Charlie"]
    assert data["active"] == [True, False, True]


def test_write_json_indent(sample_frame: ArFrame, tmp_path: pathlib.Path) -> None:
    output_file = tmp_path / "output_indent.json"
    ar.write_json(sample_frame, output_file, indent=4)

    with open(output_file, encoding="utf-8") as f:
        content = f.read()

    # Indentation should produce newlines
    assert "\n" in content
    assert '    "id":' in content


def test_write_json_invalid_frame(tmp_path: pathlib.Path) -> None:
    with pytest.raises(TypeError, match="frame must be an ArFrame"):
        ar.write_json({"a": [1]}, tmp_path / "out.json")  # type: ignore


def test_write_json_invalid_path(sample_frame: ArFrame) -> None:
    with pytest.raises(
        TypeError, match="path must be a string, bytes, or os.PathLike object"
    ):
        ar.write_json(sample_frame, 123)  # type: ignore


def test_write_json_unsupported_extension(
    sample_frame: ArFrame, tmp_path: pathlib.Path
) -> None:
    with pytest.raises(
        ValueError, match="Unsupported file format.*only supports .json"
    ):
        ar.write_json(sample_frame, tmp_path / "output.csv")


def test_write_json_unsupported_orient(
    sample_frame: ArFrame, tmp_path: pathlib.Path
) -> None:
    with pytest.raises(ValueError, match="Unsupported orient"):
        ar.write_json(sample_frame, tmp_path / "out.json", orient="split")


def test_write_json_invalid_indent(
    sample_frame: ArFrame, tmp_path: pathlib.Path
) -> None:
    with pytest.raises(TypeError, match="indent must be an integer or None"):
        ar.write_json(sample_frame, tmp_path / "out.json", indent="4")  # type: ignore

    with pytest.raises(ValueError, match="indent must be a non-negative integer"):
        ar.write_json(sample_frame, tmp_path / "out.json", indent=-1)
