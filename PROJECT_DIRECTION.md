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

## Near-Term Integration Roadmap

1. Pandas accessor: `df.arnio.clean()`, `df.arnio.profile()`,
   `df.arnio.validate()`.
2. scikit-learn transformer for preprocessing pipelines.
3. Arrow bridge for DuckDB, Polars, and PyArrow workflows.
4. NumPy preparation helpers for numeric/modeling workflows.
5. Interoperability examples that show Arnio working with popular libraries.
