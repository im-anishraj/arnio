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
