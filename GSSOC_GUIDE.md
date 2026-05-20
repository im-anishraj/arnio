# GSSoC 2026 Contributor Guide

Arnio is a GSSoC 2026 project focused on fast, reliable data preparation before pandas. The best contributions improve correctness, usability, test coverage, performance, documentation, and contributor experience.

## Before You Start

1. Read the issue carefully.
2. Search for existing PRs for the same issue.
3. Comment with a short implementation approach.
4. Wait for maintainer assignment before starting scored GSSoC work.
5. Keep one issue to one PR unless a maintainer asks otherwise.

## GSSoC FAQ

**How do I set up the project locally?**
Clone the repo, install dev dependencies with `pip install -e ".[dev]"`, install pre-commit hooks, and run `pytest tests/ -v`. On Windows, install Visual Studio Build Tools with the "Desktop development with C++" workload first.

**How does issue assignment work?**
For GSSoC-scored work, maintainers expect contributors to comment with a short implementation approach and wait for assignment before starting.

**How do I claim an issue?**
Read the issue carefully, search for existing PRs, then comment with a short plan so maintainers can review and assign the work.

**Can I start working before I am assigned?**
For scored GSSoC work, no. Wait for maintainer assignment before you start so work is not duplicated.

**Should one PR cover more than one issue?**
Usually no. Keep one issue to one PR unless a maintainer explicitly asks otherwise.

**What should I expect during PR review?**
Maintainers may ask for tests, doc updates, edge cases, or a narrower scope. Respond politely and clearly during review.

**What testing or linting should I run before opening a PR?**
Run tests before requesting review. A good local checklist is `pytest tests/ -v`, and if you are using the full contributor workflow, also run `make test` and `make lint`.

**What contribution etiquette should I follow?**
Keep your PR focused, avoid editing unrelated files, and keep formatting-only changes separate from feature work.

**Can I open a PR if someone already has the issue or PR in progress?**
Do not open duplicate PRs for the same issue. Unassigned duplicate PRs do not count as accepted GSSoC work.

**Where should I ask questions if I get stuck?**
Use Discord for quick setup or onboarding help, GitHub Discussions for general questions, and issue or PR comments as the source of truth for task-specific work and reviews.

**What information should I include when asking for help?**
Share what you tried, the exact command or code, the error output, and your operating system and Python version.

## Good First Contributions

Start with issues labeled:
- `gssoc: good first issue`
- `difficulty: beginner`
- `size: xs` or `size: s`
- `status: ready`

Good first tasks usually involve tests, docs, examples, small API validation, or focused Python wrappers.

## Contribution Levels

| Level | Typical work | Expected scope |
|:---|:---|:---|
| Level 1 | Docs, examples, small tests, minor validations | 1-2 files, low risk |
| Level 2 | New Python API behavior, broader tests, compatibility improvements | Focused feature or bug fix |
| Level 3 | C++ parser/engine work, performance work, architecture-level behavior | Requires careful design and benchmarks |

## Local Setup

```bash
git clone https://github.com/im-anishraj/arnio.git
cd arnio
pip install -e ".[dev]"
pre-commit install
pytest tests/ -v
```

On Windows, install Visual Studio Build Tools with the "Desktop development with C++" workload before building from source.

## What Maintainers Expect

- Link your issue in the PR description.
- Run tests before requesting review.
- Add tests for every behavior change.
- Update docs when public APIs change.
- Keep formatting changes separate from feature work.
- Respond politely and clearly during review.

## What To Avoid

- Duplicate PRs.
- Unassigned GSSoC PRs for claimed issues.
- Huge refactors mixed with a small fix.
- AI-generated bulk changes without understanding or tests.
- Editing unrelated files.
- Adding dependencies without maintainer approval.

## Asking for Help

Use Discussions for questions and issue comments for task-specific updates. If you get stuck, share:
- What you tried.
- The exact command or code.
- The error output.
- Your operating system and Python version.

## Maintainer Promise

We will try to keep issues scoped, labels meaningful, and review feedback actionable. The goal is not just to merge code, but to help contributors learn how real production Python/C++ libraries are maintained.
