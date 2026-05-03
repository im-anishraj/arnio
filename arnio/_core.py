"""
arnio._core
Internal module that imports the C++ extension.
"""

try:
    from ._arnio_cpp import (  # type: ignore[import-not-found]
        Frame as _Frame,
        Column as _Column,
        CsvConfig as _CsvConfig,
        CsvReader as _CsvReader,
        DType as _DType,
        drop_nulls as _drop_nulls,
        fill_nulls as _fill_nulls,
        drop_duplicates as _drop_duplicates,
        strip_whitespace as _strip_whitespace,
        normalize_case as _normalize_case,
        rename_columns as _rename_columns,
        cast_types as _cast_types,
    )
except ImportError as e:
    raise ImportError(
        "arnio C++ extension (_arnio_cpp) not found. "
        "Please install arnio with: pip install ."
    ) from e
