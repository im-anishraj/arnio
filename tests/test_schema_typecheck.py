import pytest

import arnio as ar


def test_schema_raises_type_error_for_list_of_fields():
    with pytest.raises(TypeError, match="Schema 'fields' must be a mapping"):
        ar.Schema([ar.String()])
