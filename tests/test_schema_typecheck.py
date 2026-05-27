import pytest

import arnio as ar


def test_schema_raises_type_error_for_list_of_fields():
    with pytest.raises(TypeError, match="Schema 'fields' must be a mapping"):
        ar.Schema([ar.String()])


def test_schema_raises_type_error_for_integer_key():
    with pytest.raises(TypeError, match="Schema field names must be strings"):
        ar.Schema({1: ar.String()})


def test_schema_raises_type_error_for_none_key():
    with pytest.raises(TypeError, match="Schema field names must be strings"):
        ar.Schema({None: ar.String()})


def test_schema_raises_type_error_for_tuple_key():
    with pytest.raises(TypeError, match="Schema field names must be strings"):
        ar.Schema({("a", "b"): ar.String()})


@pytest.mark.parametrize("bad_strict", ["yes", 1, None, 0, "false", 1.0])
def test_schema_strict_rejects_non_bool(bad_strict):
    with pytest.raises(TypeError, match="strict.*bool"):
        ar.Schema({"x": ar.Int64()}, strict=bad_strict)


def test_schema_strict_accepts_true():
    schema = ar.Schema({"x": ar.Int64()}, strict=True)
    assert schema.strict is True


def test_schema_strict_accepts_false():
    schema = ar.Schema({"x": ar.Int64()}, strict=False)
    assert schema.strict is False
