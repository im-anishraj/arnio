"""
arnio._core
Internal module that imports the C++ extension.
"""

try:
    from ._arnio_cpp import (  # type: ignore[import-not-found]  # noqa: I001
        Column as _Column,  # noqa: F401
        CsvConfig as _CsvConfig,  # noqa: F401
        CsvReader as _CsvReader,  # noqa: F401
        DType as _DType,  # noqa: F401
        Frame as _Frame,  # noqa: F401
        cast_types as _cast_types,  # noqa: F401
        drop_duplicates as _drop_duplicates,  # noqa: F401
        drop_nulls as _drop_nulls,  # noqa: F401
        fill_nulls as _fill_nulls,  # noqa: F401
        normalize_case as _normalize_case,  # noqa: F401
        rename_columns as _rename_columns,  # noqa: F401
        strip_whitespace as _strip_whitespace,  # noqa: F401
    )
except ImportError as e:
    raise ImportError(
        "arnio C++ extension (_arnio_cpp) not found. "
        "Please install arnio with: pip install ."
    ) from e
