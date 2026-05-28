# Maintainer Guide

This guide keeps triage and review consistent during GSSoC 2026 and regular open-source work.

## Triage Policy

Every issue should have:
- One `type:*` label.
- One or more `area:*` labels.
- One `priority:*` label when impact is clear.
- One `level:*` label for GSSoC-scored or contributor-ready work.
- One `size:*` label for estimated PR scope.
- One workflow label such as `status: needs triage`, `status: ready`, `status: claimed`, or `status: blocked`.

Before opening another large issue batch, use
[CORE_STABILITY_SPRINT.md](CORE_STABILITY_SPRINT.md) as the maintainer checklist
for install reliability, correctness, public API stability, benchmarks, and PR
queue hygiene.

## Assignment Policy

- Assign one contributor per issue unless the task is explicitly collaborative.
- Prefer contributors who provide a clear approach, not just "assign me".
- If a contributor is inactive for several days, ask for a status update before reassigning.
- For GSSoC, do not count unassigned duplicate PRs as accepted work.

## Review Standards

Before merging, check:
- The PR links the issue.
- Tests cover the changed behavior.
- Public API changes include docs or examples.
- Error messages are useful to users.
- C++ changes are covered by Python tests or native tests.
- CI passes on supported Python versions.
- The PR title follows Conventional Commits.
- GSSoC PR labels use the exact official strings where applicable:
  `gssoc:approved`, `level:*`, `quality:*`, and `type:*`.

## Release Notes

Release-worthy changes should be easy to describe in one sentence:
- User-visible feature.
- Bug fix.
- Performance improvement.
- Packaging or CI reliability change.
- Documentation improvement that materially helps adoption.

Avoid merging unrelated changes into one PR because it makes release notes and regressions harder to understand.
