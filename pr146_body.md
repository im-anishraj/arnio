Fixes #146

## Summary
- add `ar.drop_empty_columns(frame)` to remove columns whose values are entirely null or empty strings
- register `drop_empty_columns` as a built-in pipeline step and export it from the public API
- add focused cleaning and pipeline regression coverage for fully empty, partially empty, and all-columns-dropped cases
- document the new primitive in the README cleaning table

## Verification
- `python -m pytest tests/test_cleaning.py -k "TestDropEmptyColumns"`
- `python -m pytest tests/test_pipeline.py -k "drop_empty_columns"`
- `python -m ruff check arnio/cleaning.py arnio/pipeline.py arnio/__init__.py tests/test_cleaning.py tests/test_pipeline.py`
- `python -m black --check arnio/cleaning.py arnio/pipeline.py arnio/__init__.py tests/test_cleaning.py tests/test_pipeline.py`
