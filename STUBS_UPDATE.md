Updating _arnio_cpp type stubs
==============================

The C++ extension `_arnio_cpp` uses a handwritten stub file at
`arnio/_arnio_cpp.pyi` for autocomplete and mypy support.

When the C++ API changes:

1. Update `arnio/_arnio_cpp.pyi` to match the exported pybind11 API.
2. Keep names, parameters, and return types aligned with Python call sites.
3. Run:

```bash
python -m mypy arnio --show-error-codes
```

If mypy reports mismatches, adjust the stub or the Python call site.