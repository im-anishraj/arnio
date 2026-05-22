import pandas as pd
import pytest

import arnio as ar
from arnio.cleaning import replace_values
from arnio.convert import to_pandas


def test_replace_values_parity_and_null_handling():
    # 1. Base ArFrame input preparation
    data = {"A": ["active", "pending", None, "active"], "B": [1, 2, 3, 4]}
    df_raw = pd.DataFrame(data)
    frame = ar.from_pandas(df_raw)

    # Specific column mapping execution validation
    res_col = replace_values(frame, {"active": "enabled"}, column="A")
    assert to_pandas(res_col)["A"].iloc[0] == "enabled"

    # Null-key mapping structure using explicit pd.isna checks to handle pd.NA variants safely
    res_null_key = replace_values(frame, {None: "missing"}, column="A")
    assert to_pandas(res_null_key)["A"].iloc[2] == "missing"

    # Value mapped to null constraint check
    res_val_to_null = replace_values(frame, {"pending": None}, column="A")
    assert pd.isna(to_pandas(res_val_to_null)["A"].iloc[1])

    # Whole-frame replacement execution context (column=None)
    res_frame = replace_values(frame, {"active": "processed"}, column=None)
    assert to_pandas(res_frame)["A"].iloc[0] == "processed"

    # 2. Raw direct Pandas DataFrame input parity verification
    df_direct = pd.DataFrame(data)
    res_pandas = replace_values(df_direct, {"active": "verified"}, column="A")
    assert isinstance(res_pandas, pd.DataFrame)
    assert res_pandas["A"].iloc[0] == "verified"

    # 3. Validation exceptions structures checking
    # Empty mapping constraints violation handling
    with pytest.raises(ValueError):
        replace_values(frame, {})

    # Invalid mapping type check handling
    with pytest.raises(TypeError):
        replace_values(frame, "invalid_mapping_type")

    # Missing/invalid target column lookup error routing
    with pytest.raises(KeyError):
        replace_values(frame, {"active": "enabled"}, column="non_existent_column")
