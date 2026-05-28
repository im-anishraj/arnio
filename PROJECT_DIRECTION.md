# Arnio Project Direction

Arnio is a fast data-preparation layer for the Python data ecosystem.

The project is not trying to replace pandas, NumPy, scikit-learn, DuckDB, or
Arrow. Arnio should make those tools easier to use by handling the messy,
repetitive, and risky preparation work before data reaches analysis, modeling,
or storage workflows.

## Core Identity

Arnio focuses on:

- fast CSV ingestion and schema scanning
- predictable cleaning pipelines
- data quality profiling
- schema validation and data contracts
- safe pandas interoperability
- integrations that fit existing data workflows

The existing C++ runtime, `ArFrame`, cleaning primitives, and schema layer
remain the foundation. Integrations are the next layer built on top of that
foundation.

## Product Pillars

Arnio should grow around five practical pillars:

1. **Ingest safely**: read messy CSV, JSONL, and tabular data with clear errors
   for malformed input instead of silent corruption.
2. **Clean predictably**: make pipeline steps explicit, composable, and tested so
   users understand when rows, columns, or dtypes change.
3. **Validate trust**: provide schemas, quality gates, profiling, and reports
   that can be used in notebooks and CI.
4. **Interoperate cleanly**: hand trustworthy data to pandas, NumPy,
   scikit-learn, DuckDB, Arrow, and Parquet workflows without pretending to
   replace them.
5. **Prove performance**: back speed claims with reproducible benchmarks and
   environment details, not vague comparisons.

## Product Positioning

Use this framing when writing docs, issues, release notes, or examples:

> Arnio prepares messy data for the Python data stack.

Good examples:

- Clean with Arnio, analyze with pandas.
- Validate with Arnio, train with scikit-learn.
- Profile with Arnio, query with DuckDB.
- Prepare with Arnio, exchange with Arrow.

Avoid framing Arnio as a pandas replacement. Arnio should be useful to people
who already love pandas and simply want fewer fragile preprocessing chains.

## Contributor Guidance

Existing issues around parsing, cleaning, schema validation, profiling,
performance, and packaging are still important. They directly improve the
foundation that integrations rely on.

New integration work should be:

- small and focused
- compatible with existing public APIs
- tested against real user workflows
- documented with short examples
- careful about optional dependencies

Prefer additive APIs over breaking changes.

Before opening large new feature batches, maintainers should first complete the
[Core Stability Sprint](CORE_STABILITY_SPRINT.md). That sprint defines the
install, correctness, API, benchmark, and contributor gates that make future
growth sustainable.

## Near-Term Integration Roadmap

1. Pandas accessor: `df.arnio.clean()`, `df.arnio.profile()`,
   `df.arnio.validate()`.
2. scikit-learn transformer for preprocessing pipelines.
3. Arrow bridge for DuckDB, Polars, and PyArrow workflows.
4. NumPy preparation helpers for numeric/modeling workflows.
5. Interoperability examples that show Arnio working with popular libraries.
