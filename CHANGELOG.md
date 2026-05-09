# Changelog

## [Unreleased]
### Fixed
- Fixed type consistency check in Column (#52)

## [1.0.0] - 2026-05-08
### Added
- **Cross-Platform Wheels**: Full `cibuildwheel` automation delivering pre-compiled native wheels for Windows, Linux, and macOS (Intel & Apple Silicon).
- **Google Colab Compatibility**: Linux wheels are now fully `manylinux` compliant, allowing `pip install arnio` to work out-of-the-box on Colab and Ubuntu.
- **Production-Grade Packaging**: Resolved `ModuleNotFoundError` by removing double-nesting issues in `scikit-build-core` config.
- **CI/CD Excellence**: Fully automated PyPI publishing pipeline via Trusted Publishing with integrated source distributions (`sdist`).
- **Stable API**: Officially marked `arnio` as stable for production workloads with "Development Status :: 5 - Production/Stable".

### Fixed
- Migrated from `FetchContent` to `find_package(pybind11)` for faster, offline, and more robust cross-platform builds.
- Refactored `cibuildwheel` configuration entirely into `pyproject.toml` for standard and declarative packaging.

## [0.1.3] - 2026-05-XX
### Fixed
- `normalize_case()` now accepts `case_type` kwarg as documented in README
  (previously accepted `case=`, causing TypeError for all README users)
- `to_pandas()` completely rewritten using zero-copy NumPy buffer interface —
  eliminates O(rows × cols) pybind11 boundary crossings, restoring actual 
  performance advantage over pandas
- `from_pandas()` implemented with correct null handling and round-trip fidelity

### Added
- `ar.register_step(name, fn)` — register pure-Python pipeline steps without C++
- `arnio.exceptions` module with `ArnioError`, `UnknownStepError`, `CsvReadError`, 
  `TypeCastError` — replaces opaque C++ errors with actionable messages
- `arnio.__version__` now available programmatically
- `benchmarks/generate_data.py` — deterministic 1M row test dataset generator
- `benchmarks/benchmark_vs_pandas.py` — reproducible end-to-end benchmark

### Fixed (Internal)
- CI now verifies compilation on Ubuntu and Windows across Python 3.9–3.12

## [0.1.2] - 2026-05-03
### Fixed
- Stability improvements and initial PyPI release
