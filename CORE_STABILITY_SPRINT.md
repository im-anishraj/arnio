# Arnio Core Stability Sprint

This sprint turns Arnio's product direction into an execution checklist. The goal is
to make Arnio trustworthy before expanding the backlog again.

Arnio should be the fast, safe, explicit data-preparation and data-quality layer
for the Python data stack. It should prepare messy data for pandas, NumPy,
scikit-learn, DuckDB, Arrow, notebooks, and CI workflows. It should not try to
replace those tools.

## Sprint Goals

- Make local installation and native extension builds predictable on Windows,
  macOS, and Linux.
- Keep ingestion and cleaning behavior strict, explicit, and free from silent
  data loss.
- Define which public APIs are stable and how future behavior changes are
  deprecated.
- Replace vague performance claims with reproducible benchmark baselines.
- Keep contributor work focused on correctness, tests, docs, and scoped
  integrations.

## Release Gates

Use these gates before calling a release or major contributor batch ready.

| Area | Gate |
|:---|:---|
| Local setup | `pip install -e ".[dev]"` works from a clean checkout on supported platforms. |
| Native extension | Import failures explain exactly which compiler/build dependency is missing. |
| Tests | `pytest tests/ -v` passes in CI and can be reproduced locally after install. |
| Lint/format | `ruff check .` and `black --check .` pass. |
| CSV correctness | Malformed CSV, inconsistent row widths, BOMs, encodings, nulls, and quoted newlines have regression coverage. |
| Cleaning safety | Row-dropping, casting, null handling, and duplicate handling never silently change data without documented behavior. |
| Schema/quality | Validation errors include useful column, rule, and row context where available. |
| Benchmarks | Baselines are populated, deterministic, and include environment details. |
| Docs | Quickstart, troubleshooting, API reference, and examples match current behavior. |
| PR queue | New work is linked to one issue, scoped, labeled, and not duplicated. |

## Stable Public API Candidates

Treat these APIs as the first stability candidates. Changes to their behavior
should be documented, tested, and deprecated before breaking users:

- `read_csv`
- `write_csv`
- `scan_csv`
- `from_pandas`
- `to_pandas`
- `profile`
- `suggest_cleaning`
- `auto_clean`
- `Schema`
- `pipeline`

## What To Prioritize

1. Correctness bugs that can corrupt, drop, or misread data.
2. Build, install, wheel, and import failures that block users from trying Arnio.
3. Missing tests for public behavior and regression-prone edge cases.
4. API documentation gaps where behavior is already implemented but unclear.
5. Performance work only when correctness tests and benchmark baselines exist.

## What To Defer

- Large new feature batches that do not improve trust in the core engine.
- Broad rewrites without a failing test or measurable benchmark target.
- New dependencies unless they unlock a clearly documented integration path.
- Duplicate contributor issues created only to increase activity.

## Contributor Queue Policy

- One issue should map to one PR unless a maintainer explicitly asks otherwise.
- PRs must link the issue they resolve with `Fixes #issue_number` or
  `Closes #issue_number`.
- Duplicate PRs for the same issue should be closed after the best scoped PR is
  identified.
- GSSoC labels must describe the actual work. Do not add higher level, quality,
  or type labels only to increase points.
- During stability work, prefer bugs, tests, docs, and small integration fixes
  over speculative features.

## Definition Of Done

The sprint is successful when a new contributor can install Arnio, run the test
suite, understand the stable APIs, find a focused issue, and open a scoped PR
without maintainer rescue. A user should be able to trust Arnio to prepare data
without silent corruption or unclear behavior.
