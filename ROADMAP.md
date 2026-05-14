# Arnio Roadmap

This roadmap is a maintainer-level guide for contributors. It is intentionally practical: correctness first, then developer experience, then performance and scale.

## Current Focus

- Make CSV parsing and cleaning behavior predictable across platforms.
- Expand the data quality and schema validation layer.
- Improve contributor onboarding for GSSoC 2026.
- Increase unit, integration, packaging, and benchmark coverage.
- Keep PyPI releases reliable and easy to verify.

## Near Term

- Harden CSV edge cases: row width validation, comments, encodings, malformed quotes, delimiter detection, and better diagnostics.
- Make `ArFrame` easier to inspect and test with row previews, column access, equality, and copy behavior.
- Expand pipeline ergonomics with validation, registry introspection, and safer custom step execution.
- Add more schema validators for real-world data contracts.
- Build reproducible performance baselines and regression checks.

## Mid Term

- Chunked and streaming processing for datasets that do not fit comfortably in memory.
- Native writers for CSV and other common export formats.
- Better pandas interoperability for datetime, categorical, nullable, and timedelta types.
- More automatic data quality suggestions with confidence levels and explainable actions.
- Documentation site with API reference, tutorials, recipes, and contribution tracks.

## Long Term

- Parallel column processing and lower-copy cleaning paths.
- SIMD-aware string operations where measurable.
- Larger file format support, including JSON Lines and Parquet.
- Stable plugin-style extension points for custom cleaning and validation.
- Enterprise-friendly data contracts, audit reports, and CI validation workflows.

## Product Direction

Arnio should become the fast, explicit preparation layer before pandas: inspect messy data, clean it predictably, validate it against contracts, and hand a trustworthy DataFrame to the rest of the Python ecosystem.
