# Maintainer Guide

This guide keeps triage and review consistent during GSSoC 2026 and regular open-source work.

## Triage Policy

Every issue should have:
- One `type:*` label.
- One or more `area:*` labels.
- One `priority:*` label when impact is clear.
- One `level:*` label for GSSoC-scored or contributor-ready work.
- One `size:*` label for estimated PR scope.
- One workflow label such as `status:needs-triage`, `status:ready`, `status:claimed`, or `status:blocked`.

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

## Release & Publishing

Publishing to PyPI is intentionally gated behind an explicit, validated release
tag so that no untagged or arbitrary commit can be published. The
[Build & Publish Wheels](.github/workflows/build_wheels.yml) workflow refuses to
run unless it receives a `tag_name` that (1) matches the `vX.Y.Z` convention (a
pre-release suffix such as `v1.2.3-rc1` is allowed) **and** (2) resolves to an
existing Git tag under `refs/tags/`. A branch or other ref that merely looks
like a tag is rejected. The verified tag is then frozen to its immutable commit
SHA, every build job checks out that SHA, and the publish job re-verifies `HEAD`
before uploading. The guard logic lives in
[`scripts/verify_release_tag.sh`](scripts/verify_release_tag.sh) and is covered
by [`tests/test_verify_release_tag.sh`](tests/test_verify_release_tag.sh) (run
in CI by the *Verify Release Tag Guard* workflow).

There are two supported paths:

- **Automated (preferred).** Merging release-worthy changes to `main` lets
  [Release Please](.github/workflows/release-please.yml) open/maintain a release
  PR. Merging that PR creates the `vX.Y.Z` tag and automatically calls the build
  & publish workflow with it. No manual action is required.
- **Manual release.** If you must trigger publishing by hand, run the
  *Build & Publish Wheels* workflow via **Run workflow** and enter the exact
  release tag (e.g. `v1.2.3`) in the `tag_name` field. The tag is required; an
  empty or non-`vX.Y.Z` value fails immediately before anything is built. The
  workflow checks out that tag, so the tag must already exist and point at the
  commit you intend to release.

To verify a build without any chance of publishing, use the
[Release Dry-Run Checklist](.github/workflows/release-dry-run.yml) workflow,
which builds and smoke-tests the sdist and wheels but never publishes.
