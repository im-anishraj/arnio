# Arnio CI Visibility Policy

This policy documents the PR checks maintainers should see before reviewing or
merging code-changing pull requests. It covers fork PRs where GitHub may wait
for maintainer approval before running Actions.

## Expected PR Signal

For a code-changing pull request targeting `main`, maintainers should be able to
see an Arnio-owned CI signal after any required GitHub approval step:

- `PR Guard` checks sensitive workflow changes and stray root files.
- `CI` runs lint, C++ native tests, the Python test matrix, notebook smoke
  tests, and scikit-learn integration tests.
- `Examples Smoke` runs the public example scripts, including the DuckDB smoke
  example.
- `Compatibility Matrix` runs for runtime, test, dependency, and matrix workflow
  changes.

Additional path-scoped workflows may also appear for packaging, optional
dependency, website, wheel, or release-related files. External checks such as
Vercel are useful, but they are not a substitute for Arnio CI.

## Fork PR Approval Path

GitHub can hold workflow runs from a fork or first-time contributor until a
maintainer with write access approves them. When a PR shows only Vercel or other
external checks:

1. Open the PR checks list and the repository Actions tab for pending workflow
   approval notices.
2. Inspect the PR diff, especially `.github/workflows/`, before approving the
   run.
3. Approve the GitHub Actions run only when the workflow changes are expected
   for the issue and safe to execute.
4. Wait for the Arnio CI signal above to appear and complete.
5. Do not merge code-changing PRs that show only Vercel or another external
   check with no Arnio CI result.

If the Arnio CI workflows still do not appear after maintainer approval, check
the workflow triggers, path filters, repository Actions settings, and any
maintainer-side branch protection or ruleset configuration before review.

## Workflow Trigger Policy

Workflows that check out, build, test, lint, or otherwise execute contributor
code must use the `pull_request` event with read-only repository permissions.
Do not add `pull_request_target` to those workflows.

`pull_request_target` may only be considered for metadata-only automation that
does not check out or execute untrusted contributor code. That requires explicit
maintainer review before it is added.

## Maintainer Merge Gate

Branch protection or repository rulesets are configured outside pull requests,
but the policy expectation is clear: code-changing PRs should not be merged when
only external checks are visible. Require the Arnio-owned CI signal that matches
the changed files, then review the PR.
