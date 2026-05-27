import pandas as pd
import pytest

import arnio as ar


def test_public_exception_hierarchy():
    public_exceptions = [
        ar.ArnioError,
        ar.CsvReadError,
        ar.TypeCastError,
        ar.UnknownStepError,
    ]

    for exc_type in public_exceptions:
        assert issubclass(exc_type, Exception)

    for exc_type in public_exceptions[1:]:
        assert issubclass(exc_type, ar.ArnioError)


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


def test_pipeline_step_error_properties_and_message():
    orig_err = ValueError("Invalid input value")
    step_err = ar.PipelineStepError("normalize_age", orig_err)

    assert step_err.step_name == "normalize_age"
    assert step_err.orig_err is orig_err
    assert "normalize_age" in str(step_err)
    assert "Invalid input value" in str(step_err)


def test_jsonl_read_error_inheritance():
    assert issubclass(ar.JsonlReadError, ar.ArnioError)

