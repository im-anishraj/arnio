# GSSoC 2026 Contributor Guide

Arnio is a GSSoC 2026 project focused on fast, reliable data preparation before pandas. The best contributions improve correctness, usability, test coverage, performance, documentation, and contributor experience.

## Before You Start

1. Read the issue carefully.
2. Search for existing PRs for the same issue.
3. Comment with a short implementation approach.
4. Wait for maintainer assignment before starting scored GSSoC work.
5. Keep one issue to one PR unless a maintainer asks otherwise.

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
