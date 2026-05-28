import pandas as pd
import pytest

import arnio as ar


def test_public_exception_hierarchy():
    public_exceptions = [
        ar.ArnioError,
        ar.CsvReadError,
        ar.JsonlReadError,
        ar.TypeCastError,
        ar.UnknownStepError,
    ]

    for exc_type in public_exceptions:
        assert issubclass(exc_type, Exception)

    for exc_type in public_exceptions[1:]:
        assert issubclass(exc_type, ar.ArnioError)


def test_jsonl_read_error_for_malformed_json_has_clear_message(tmp_path):
    bad_jsonl = tmp_path / "bad.jsonl"
    bad_jsonl.write_text('{"key": "value"}\n{invalid json}\n')

    with pytest.raises(ar.JsonlReadError) as exc_info:
        ar.read_jsonl(str(bad_jsonl))

    message = str(exc_info.value)
    assert message
    assert "invalid json" in message.lower()
    assert "line 2" in message.lower()


def test_jsonl_read_error_for_non_dict_json_has_clear_message(tmp_path):
    array_jsonl = tmp_path / "array.jsonl"
    array_jsonl.write_text("[1, 2, 3]\n")

    with pytest.raises(ar.JsonlReadError) as exc_info:
        ar.read_jsonl(str(array_jsonl))

    message = str(exc_info.value)
    assert message
    assert "expected a json object" in message.lower()
    assert "line 1" in message.lower()


def test_csv_read_error_for_missing_file_has_clear_message(tmp_path):
    missing_path = tmp_path / "missing.csv"

    with pytest.raises(ar.CsvReadError) as exc_info:
        ar.read_csv(str(missing_path))

    message = str(exc_info.value)
    assert message
    assert "cannot open file" in message.lower()


def test_type_cast_error_for_unknown_target_dtype_has_clear_message():
    frame = ar.from_pandas(pd.DataFrame({"age": [20, 30]}))

    with pytest.raises(ar.TypeCastError) as exc_info:
        ar.cast_types(frame, {"age": "decimal"})

    message = str(exc_info.value)
    assert message
    assert "unknown target dtype" in message.lower()


def test_unknown_step_error_has_clear_message():
    frame = ar.from_pandas(pd.DataFrame({"age": [20, 30]}))

    with pytest.raises(ar.UnknownStepError) as exc_info:
        ar.pipeline(frame, [("nonexistent_op",)])

    message = str(exc_info.value)
    assert message
    assert "unknown pipeline step" in message.lower()
    assert "available steps" in message.lower()


def test_jsonl_read_error_is_arnio_error():
    assert issubclass(ar.JsonlReadError, ar.ArnioError)
    assert issubclass(ar.JsonlReadError, Exception)


def test_jsonl_read_error_for_missing_file_has_clear_message(tmp_path):
    missing_path = tmp_path / "missing.jsonl"

    with pytest.raises(ar.JsonlReadError) as exc_info:
        ar.read_jsonl(str(missing_path))

    message = str(exc_info.value)
    assert message
    assert "missing.jsonl" in message


def test_jsonl_read_error_for_empty_file_has_clear_message(tmp_path):
    empty_file = tmp_path / "empty.jsonl"
    empty_file.write_text("", encoding="utf-8")

    with pytest.raises(ar.JsonlReadError) as exc_info:
        ar.read_jsonl(str(empty_file))

    message = str(exc_info.value)
    assert message
    assert "empty" in message.lower()


def test_jsonl_read_error_for_blank_lines_only_file(tmp_path):
    blank_file = tmp_path / "blank.jsonl"
    blank_file.write_text("\n\n   \n\t\n", encoding="utf-8")

    with pytest.raises(ar.JsonlReadError) as exc_info:
        ar.read_jsonl(str(blank_file))

    message = str(exc_info.value)
    assert message
    assert "empty" in message.lower()


def test_jsonl_read_error_for_invalid_json_includes_line_number(tmp_path):
    bad_json_file = tmp_path / "bad.jsonl"
    bad_json_file.write_text(
        '{"name": "Alice"}\n' "NOT VALID JSON\n" '{"name": "Bob"}\n',
        encoding="utf-8",
    )

    with pytest.raises(ar.JsonlReadError) as exc_info:
        ar.read_jsonl(str(bad_json_file))

    message = str(exc_info.value)
    assert message
    assert "line 2" in message


def test_jsonl_read_error_for_non_object_json_line(tmp_path):
    array_file = tmp_path / "array.jsonl"
    array_file.write_text(
        '{"name": "Alice"}\n' "[1, 2, 3]\n",
        encoding="utf-8",
    )

    with pytest.raises(ar.JsonlReadError) as exc_info:
        ar.read_jsonl(str(array_file))

    message = str(exc_info.value)
    assert message
    assert "line 2" in message
    assert "json object" in message.lower()


def test_jsonl_read_error_for_invalid_json_on_first_line(tmp_path):
    bad_first = tmp_path / "bad_first.jsonl"
    bad_first.write_text("{invalid json}\n", encoding="utf-8")

    with pytest.raises(ar.JsonlReadError) as exc_info:
        ar.read_jsonl(str(bad_first))

    message = str(exc_info.value)
    assert message
    assert "line 1" in message


def test_jsonl_read_error_can_be_caught_as_arnio_error(tmp_path):
    missing_path = tmp_path / "nope.jsonl"

    with pytest.raises(ar.ArnioError):
        ar.read_jsonl(str(missing_path))


def test_jsonl_read_error_message_is_non_empty_string():
    err = ar.JsonlReadError("test error message")
    assert str(err) == "test error message"
