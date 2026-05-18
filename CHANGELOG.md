# Changelog

## [1.12.0](https://github.com/im-anishraj/arnio/compare/v1.11.3...v1.12.0) (2026-05-17)


### Features

* add strip_whitespace allocation benchmark ([e2ff584](https://github.com/im-anishraj/arnio/commit/e2ff58416125fe1eae4bef4c204cc52fb248fb86))


### Documentation

* replace ASCII architecture diagram with Mermaid flowchart ([abede39](https://github.com/im-anishraj/arnio/commit/abede392dfd11ac909d273c90cfc01463522004b))

## [1.11.3](https://github.com/im-anishraj/arnio/compare/v1.11.2...v1.11.3) (2026-05-17)


### Documentation

* add API reference skeleton ([5ea384d](https://github.com/im-anishraj/arnio/commit/5ea384d9341aab15fdbe053ff0388d8f1430cf48))

## [1.11.2](https://github.com/im-anishraj/arnio/compare/v1.11.1...v1.11.2) (2026-05-17)


### Bug Fixes

* raise clear errors for unsupported pandas dtypes in from_pandas ([1791e4f](https://github.com/im-anishraj/arnio/commit/1791e4f05242841e7878fd8c03a185bb01c48ae1))
* preserve 1-based source row numbers in schema validation issues ([5f538fd](https://github.com/im-anishraj/arnio/commit/5f538fd2b508b4c791967c8f9b1947387c6467c2))

## [1.11.1](https://github.com/im-anishraj/arnio/compare/v1.11.0...v1.11.1) (2026-05-17)


### Bug Fixes

* skip numeric cast suggestions for identifier-like columns ([cf687e2](https://github.com/im-anishraj/arnio/commit/cf687e2ae83b4cc1c1edef6065920a12fbc7a7ad))

## [1.11.0](https://github.com/im-anishraj/arnio/compare/v1.10.0...v1.11.0) (2026-05-17)


### Features

* add scikit-learn ArnioCleaner transformer ([610a39f](https://github.com/im-anishraj/arnio/commit/610a39fe5ab4a02db2ad7f9c3223896cdf263db5))
* register combine_columns as pipeline step and add test ([beaf402](https://github.com/im-anishraj/arnio/commit/beaf4022ac7dc70cb370d387769fc033beb4454d))

## [1.10.0](https://github.com/im-anishraj/arnio/compare/v1.9.1...v1.10.0) (2026-05-17)


### Features

* add DateTime schema field ([05c26be](https://github.com/im-anishraj/arnio/commit/05c26bebf1cf79bbdbb98157dba1618c61abd08e))
* add normalize_unicode cleaning step ([c8c7c40](https://github.com/im-anishraj/arnio/commit/c8c7c40c9172e83d289b25e2e4b797efd78cd26a))
* add top_values summary for categorical columns ([f593f94](https://github.com/im-anishraj/arnio/commit/f593f94cf331180f29516d1afc217c106a96ad8b))


### Performance Improvements

* add process RSS metrics to benchmark ([6206cbd](https://github.com/im-anishraj/arnio/commit/6206cbda592705d20877d8a89e2f899025f2f329))


### Documentation

* add financial CSV cleaning example notebook ([e9fb6f6](https://github.com/im-anishraj/arnio/commit/e9fb6f6f793538354160584effd87bf866f85eee))

## [1.9.1](https://github.com/im-anishraj/arnio/compare/v1.9.0...v1.9.1) (2026-05-17)


### Performance Improvements

* stream transcode and sample rows for scan_csv schema inference ([713aeaa](https://github.com/im-anishraj/arnio/commit/713aeaa9ccb380bb68568999edc141e1dc73389b))

## [1.9.0](https://github.com/im-anishraj/arnio/compare/v1.8.0...v1.9.0) (2026-05-17)


### Features

* add composite uniqueness validation support ([#495](https://github.com/im-anishraj/arnio/issues/495)) ([8b11e19](https://github.com/im-anishraj/arnio/commit/8b11e19180b97fde1c380857e702d78dc7df8fc8))
* add CountryCode schema validator ([#487](https://github.com/im-anishraj/arnio/issues/487)) ([14a77e5](https://github.com/im-anishraj/arnio/commit/14a77e532409bffc0fdef85fbbbaaa798782dde7))
* add replace_values pipeline step ([#348](https://github.com/im-anishraj/arnio/issues/348)) ([02b297c](https://github.com/im-anishraj/arnio/commit/02b297c0d60fdb4417e801f2f28db92f50441a4c))


### Documentation

* document pandas index conversion behavior ([#407](https://github.com/im-anishraj/arnio/issues/407)) ([327b650](https://github.com/im-anishraj/arnio/commit/327b650bb40b8ba902c5b0dc903b98d5f3e1172e))

## [1.8.0](https://github.com/im-anishraj/arnio/compare/v1.7.0...v1.8.0) (2026-05-17)


### Features

* add ArFrame.select_dtypes for type-based column selection ([7899541](https://github.com/im-anishraj/arnio/commit/7899541113aad0f300decc08b94f285b920f3008))
* add trim_column_names cleaning primitive and pipeline step ([d064335](https://github.com/im-anishraj/arnio/commit/d0643355f1f626a4ee2a4264aea67e316971df76))


### Bug Fixes

* reject impossible schema bounds ([906b286](https://github.com/im-anishraj/arnio/commit/906b286ad0bae551bea56746f90fa95135f749ab))

## [1.7.0](https://github.com/im-anishraj/arnio/compare/v1.6.2...v1.7.0) (2026-05-17)


### Features

* add keep_rows_with_nulls pipeline step ([37dde00](https://github.com/im-anishraj/arnio/commit/37dde009d3899e3647183f34209f171afca11f31))


### Bug Fixes

* add YAML validation for GitHub workflow files ([0c666ca](https://github.com/im-anishraj/arnio/commit/0c666caa0ce937d70fdffc58dee2e8ba12338412))


### Performance Improvements

* add auto-clean memory benchmark ([8bd10f4](https://github.com/im-anishraj/arnio/commit/8bd10f4c7301d210a0dcebb64d27006274308705))

## [1.6.2](https://github.com/im-anishraj/arnio/compare/v1.6.1...v1.6.2) (2026-05-17)


### Documentation

* improve quickstart wording ([a3f37d9](https://github.com/im-anishraj/arnio/commit/a3f37d94146f5f1b3939b0962236242312dadcac))

## [1.6.1](https://github.com/im-anishraj/arnio/compare/v1.6.0...v1.6.1) (2026-05-16)


### Bug Fixes

* preserve column order in scan_csv schema ([a3864f0](https://github.com/im-anishraj/arnio/commit/a3864f0640580acdf979d71c18c25ce8c6a9456d))
* validate missing columns in filter_rows ([e0514ef](https://github.com/im-anishraj/arnio/commit/e0514ef04fea19fb07fd7373539e1a5019e2763b))

## [1.6.0](https://github.com/im-anishraj/arnio/compare/v1.5.1...v1.6.0) (2026-05-16)


### Features

* add to_pandas copy option ([1746fe1](https://github.com/im-anishraj/arnio/commit/1746fe15d5c399d649fff9561a7a02bea147c4de))

## [1.5.1](https://github.com/im-anishraj/arnio/compare/v1.5.0...v1.5.1) (2026-05-16)


### Bug Fixes

* normalize title case across punctuation boundaries ([4a9b947](https://github.com/im-anishraj/arnio/commit/4a9b947f4045edf61839e70247fcce5b54fe5b1d))

## [1.5.0](https://github.com/im-anishraj/arnio/compare/v1.4.0...v1.5.0) (2026-05-16)


### Features

* add is_empty convenience property to ArFrame ([37df94d](https://github.com/im-anishraj/arnio/commit/37df94d0e4f782fc4510ea8ad179960f51c0fc7d))
* add validation summary counts ([#444](https://github.com/im-anishraj/arnio/issues/444)) ([6575491](https://github.com/im-anishraj/arnio/commit/657549174aaca524ce77f169a7e7b3a7b230cba0))


### Bug Fixes

* allow encoded csv nul handling ([5796a35](https://github.com/im-anishraj/arnio/commit/5796a35a32aff5a5d889a72deee255232c527929)), closes [#422](https://github.com/im-anishraj/arnio/issues/422)

## [1.4.0](https://github.com/im-anishraj/arnio/compare/v1.3.1...v1.4.0) (2026-05-16)


### Features

* add bounded profiling sample_size validation ([1e31269](https://github.com/im-anishraj/arnio/commit/1e3126986bdc21e128fc734a71a77aa7f242441a))

## [1.3.1](https://github.com/im-anishraj/arnio/compare/v1.3.0...v1.3.1) (2026-05-16)


### Bug Fixes

* handle empty CSV files with a dedicated error path ([b359173](https://github.com/im-anishraj/arnio/commit/b359173f15b5cf6b4cb68b9f04b418d5380c0c44))

## [1.3.0](https://github.com/im-anishraj/arnio/compare/v1.2.0...v1.3.0) (2026-05-15)


### Features

* add column existence validation helper ([517d1e0](https://github.com/im-anishraj/arnio/commit/517d1e07d3b19252027ecdfac23d17b19e0aa793))
* add pandas integration direction ([#399](https://github.com/im-anishraj/arnio/issues/399)) ([22f9b58](https://github.com/im-anishraj/arnio/commit/22f9b58458383549d97d81ff7828b7a047063525))
* **convert:** preserve DataFrame attrs roundtrip ([4018f27](https://github.com/im-anishraj/arnio/commit/4018f27f76dbb021591b4aa6844e2c130887dceb))


### Bug Fixes

* preserve Int64 dtype for all-null nullable integer columns in from_pandas roundtrip ([#394](https://github.com/im-anishraj/arnio/issues/394)) ([ef726ed](https://github.com/im-anishraj/arnio/commit/ef726ed0e1af588c7c0f74a04e02ccfd6a1d688f))


### Documentation

* add quality and schema architecture flow ([d22fa56](https://github.com/im-anishraj/arnio/commit/d22fa56c393c2005c9a351f30ca6132c4ae3c863))

## [1.2.0](https://github.com/im-anishraj/arnio/compare/v1.1.1...v1.2.0) (2026-05-15)


### Features

* add ArFrame preview method ([814102e](https://github.com/im-anishraj/arnio/commit/814102e35b153cf75b3a759a5e33867edfe03321))
* add ArFrame select_columns helper ([fff406d](https://github.com/im-anishraj/arnio/commit/fff406d9a10943cb6f2bd76d32240933da90ed51))
* add clip_numeric cleaning helper ([4022449](https://github.com/im-anishraj/arnio/commit/4022449c7bbe5e31c94e756ff29a36b4c274a232))
* add drop constant columns ([#357](https://github.com/im-anishraj/arnio/issues/357)) ([3e13d3d](https://github.com/im-anishraj/arnio/commit/3e13d3d576add9fd8113cdf185ca08e61e75c4ee))
* add filter_rows pipeline step ([#288](https://github.com/im-anishraj/arnio/issues/288)) ([a3b7386](https://github.com/im-anishraj/arnio/commit/a3b7386e75bc45c9a7fde403ea373334ef528f75))
* add refactor task issue template ([#334](https://github.com/im-anishraj/arnio/issues/334)) ([6690947](https://github.com/im-anishraj/arnio/commit/6690947bcada6dc825853036a11ad2310acdd4e4))
* add round_numeric_columns cleaning helper ([61cd110](https://github.com/im-anishraj/arnio/commit/61cd1105e60c6daa38d34ef602f3f9fac28de7ea))
* add safe_divide_columns cleaning step ([80e4a65](https://github.com/im-anishraj/arnio/commit/80e4a654d81a1bd95e96b1f5ec83f5f82deff590))
* add trim_headers CSV option ([022460e](https://github.com/im-anishraj/arnio/commit/022460e1fa7e9510960a789aa38f835731dec700))
* add ValidationResult.to_markdown ([168e525](https://github.com/im-anishraj/arnio/commit/168e525409ce3a8d60f972dadacfaab01c4cafa8))
* enhance pull request template with media and performance sections ([#336](https://github.com/im-anishraj/arnio/issues/336)) ([99b588b](https://github.com/im-anishraj/arnio/commit/99b588b62910a68b83abdb39455c0d59de6bba56))


### Bug Fixes

* improve nested object error messages in from_pandas ([ca90974](https://github.com/im-anishraj/arnio/commit/ca90974cdef4b25824525aa2d4482968054adba2))


### Documentation

* add beginner-friendly auto_clean tutorial with profiling and cleaning workflow  ([#326](https://github.com/im-anishraj/arnio/issues/326)) ([b604a0d](https://github.com/im-anishraj/arnio/commit/b604a0d067f6603cf6bb5037b5b33b6ff0c19248))
* add contributor glossary ([#308](https://github.com/im-anishraj/arnio/issues/308)) ([da52804](https://github.com/im-anishraj/arnio/commit/da5280486603e2d630adf33ec8d7162acb9ba0ba))
* add data quality report examples [#279](https://github.com/im-anishraj/arnio/issues/279) ([#295](https://github.com/im-anishraj/arnio/issues/295)) ([ca42e87](https://github.com/im-anishraj/arnio/commit/ca42e87cf2c596b78286ab3fe4ce8a9c305a6f2a))
* add Discord community links ([#305](https://github.com/im-anishraj/arnio/issues/305)) ([64cb4a1](https://github.com/im-anishraj/arnio/commit/64cb4a1d871ac7ec8471e28c5386eb8ebfb20ef4))
* add gssoc faq ([#309](https://github.com/im-anishraj/arnio/issues/309)) ([dc32e56](https://github.com/im-anishraj/arnio/commit/dc32e563ba5ff8e2ed2680dec9451d27c65a14e5))
* add issue triage guide for maintainers ([#300](https://github.com/im-anishraj/arnio/issues/300)) ([2d6dd6f](https://github.com/im-anishraj/arnio/commit/2d6dd6f9c566479757c2146f02e186c1d7d57c2e))
* add release process guide ([#304](https://github.com/im-anishraj/arnio/issues/304)) ([f5e1325](https://github.com/im-anishraj/arnio/commit/f5e13252889865e24cd464379c9fa3974d2fff03))
* align pandas dtype support documentation with implementation ([#327](https://github.com/im-anishraj/arnio/issues/327)) ([badd815](https://github.com/im-anishraj/arnio/commit/badd8150a3859ffb1598bdf21f71a8cd2c4c6b0b))
* fix non-sequential roadmap versions ([#107](https://github.com/im-anishraj/arnio/issues/107)) ([db3b8e4](https://github.com/im-anishraj/arnio/commit/db3b8e47fc721ad899df0b6239bc706824d168a5))
* remove large Discord badge from README ([#307](https://github.com/im-anishraj/arnio/issues/307)) ([1f0ff3a](https://github.com/im-anishraj/arnio/commit/1f0ff3ab15d111344cc9c6281226ef6361f919f9))

## [1.1.1](https://github.com/im-anishraj/arnio/compare/v1.1.0...v1.1.1) (2026-05-14)


### Documentation

* prepare repository for GSSoC contributors ([#289](https://github.com/im-anishraj/arnio/issues/289)) ([d270812](https://github.com/im-anishraj/arnio/commit/d2708126a20d6e12be75a438d631f84aa802e13f))

## [1.1.0](https://github.com/im-anishraj/arnio/compare/v1.0.2...v1.1.0) (2026-05-14)


### Features

* add data quality engine ([6053ab9](https://github.com/im-anishraj/arnio/commit/6053ab93fa29b706a20f5fd8d905f046fedb36c5))
* add data quality engine ([f8abb2f](https://github.com/im-anishraj/arnio/commit/f8abb2f8202e9d1fa394a2e1e97576f003d113b0))

## [1.0.2](https://github.com/im-anishraj/arnio/compare/v1.0.1...v1.0.2) (2026-05-10)


### Documentation

* add language identifiers to unlabeled fenced code blocks (MD040) ([21aad9c](https://github.com/im-anishraj/arnio/commit/21aad9c06e1440efa20d377f7842da6afa8d9095))
* completely redesign README with flagship-quality presentation ([252988a](https://github.com/im-anishraj/arnio/commit/252988a770a0600074734ed44b48e7cbd6763a66))
* completely redesign README with flagship-quality presentation ([5953eb4](https://github.com/im-anishraj/arnio/commit/5953eb4a567e9941a9a5ff3c4bc892a19605c737))

## [1.0.1](https://github.com/im-anishraj/arnio/compare/v1.0.0...v1.0.1) (2026-05-09)


### Documentation

* add architecture guide, reframe benchmarks, add social preview ([f91e69e](https://github.com/im-anishraj/arnio/commit/f91e69e7ffb89adcaa4ed64a5ddd4173e889c045))
* add architecture guide, reframe benchmarks, add social preview ([ab2ddba](https://github.com/im-anishraj/arnio/commit/ab2ddbaf422b582b5fc855df71906612936568e9))
* add comprehensive docstrings to all public Python functions ([3cbe1b3](https://github.com/im-anishraj/arnio/commit/3cbe1b35b95678ecc7aa267663dcd998dd74d0f2))
* duplicated code ([62401a1](https://github.com/im-anishraj/arnio/commit/62401a1418acb149b74697495467fd05e22fa14f))
* enforce conventional commits in contributor guidelines ([d98f6cf](https://github.com/im-anishraj/arnio/commit/d98f6cf208f8acc5d34dc0bee280f28a64cc1dbe))
* remove duplicated code ([0e215f9](https://github.com/im-anishraj/arnio/commit/0e215f9080abbe77183f51a9a1b07e90d60bc54f))

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

## [0.1.3] - 2026-05-06
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
