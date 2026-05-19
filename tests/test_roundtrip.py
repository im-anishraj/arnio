import pandas as pd
import arnio as ar

def test_pandas_nullable_dtypes_roundtrip():
    df = pd.DataFrame({
        'int_col': pd.Series([1, None, 3], dtype='Int64'),
        'float_col': pd.Series([1.1, None, 3.3], dtype='Float64'),
        'bool_col': pd.Series([True, None, False], dtype='boolean'),
        'str_col': pd.Series(['a', None, 'c'], dtype='string')
    })

    af = ar.from_pandas(df)
    df2 = ar.to_pandas(af)

    # Assert dtypes roundtrip correctly according to the compatibility matrix
    assert str(df2['int_col'].dtype) == 'Int64'
    assert str(df2['bool_col'].dtype) == 'boolean'
    assert str(df2['str_col'].dtype) == 'string'
    
    # Float64 standard fallback assertion
    assert str(df2['float_col'].dtype) == 'float64'

    # Assert values
    assert df2['int_col'].iloc[0] == 1
    assert pd.isna(df2['int_col'].iloc[1])
    assert df2['int_col'].iloc[2] == 3

    assert df2['bool_col'].iloc[0] is True
    assert pd.isna(df2['bool_col'].iloc[1])
    assert df2['bool_col'].iloc[2] is False

    assert df2['str_col'].iloc[0] == 'a'
    assert pd.isna(df2['str_col'].iloc[1])
    assert df2['str_col'].iloc[2] == 'c'

    assert df2['float_col'].iloc[0] == 1.1
    assert pd.isna(df2['float_col'].iloc[1])
    assert df2['float_col'].iloc[2] == 3.3
