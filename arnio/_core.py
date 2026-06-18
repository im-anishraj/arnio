"""
arnio._core
Internal module that imports the C++ extension.
"""

try:
    from ._arnio_cpp import (  # noqa: F401, I001
        Column as _Column,
        CsvChunkReader as _CsvChunkReader,
        CsvConfig as _CsvConfig,
        CsvReader as _CsvReader,
        CsvWriteConfig as _CsvWriteConfig,
        CsvWriter as _CsvWriter,
        DType as _DType,
        Frame as _Frame,
        cast_types as _cast_types,
        clip_numeric as _clip_numeric,
        drop_duplicates as _drop_duplicates,
        drop_nulls as _drop_nulls,
        fill_nulls as _fill_nulls,
        normalize_case as _normalize_case,
        rename_columns as _rename_columns,
        safe_divide_columns as _safe_divide_columns,
        strip_whitespace as _strip_whitespace,
        create_rolling_windows,
    )
except ImportError as e:
    raise ImportError(
        "arnio C++ extension (_arnio_cpp) not found.\n"
        "Install from source: pip install -e .\n"
        "Windows: Install 'Desktop development with C++' in Visual Studio Build Tools, or use WSL.\n"
        "Linux/macOS: Ensure gcc or clang is installed."
    ) from e
