## Summary
<!-- What changed and why? Keep this short but specific. -->

<!-- Need quick setup or contribution help? Join Discord: https://discord.gg/xsEw7r78M -->

## Linked issue
<!-- Use "Fixes #123" when the PR fully resolves an issue. Use "Refs #123" for partial work. -->

## Type of change
- [ ] Bug fix
- [ ] Feature
- [ ] Performance improvement
- [ ] Documentation
- [ ] Tests
- [ ] Refactor
- [ ] CI / packaging

## Area
- [ ] CSV parser / I/O
- [ ] C++ cleaning engine
- [ ] Python API / ArFrame
- [ ] Pipeline / custom steps
- [ ] Data quality / profiling
- [ ] Schema validation
- [ ] pandas interoperability
- [ ] Docs / website
- [ ] Developer tooling

## Testing
<!-- Paste commands you ran and summarize the result. -->
- [ ] `make test` (or `python -m pytest tests -v --cov=arnio`)
```markdown
- [ ] `make lint` (or run separately:
  ```bash
  python scripts/check_docs_utf8.py
  python -m black --check --diff .
  python -m ruff check . --extend-exclude "*.ipynb"
  python -m mypy --config-file mypy.ini
  find cpp/ bindings/ -type f \( -name '*.cpp' -o -name '*.h' \) | xargs clang-format --dry-run --Werror
  ```
)
- [ ] optionally `python -m pytest tests -v --tb=short -x`
- [ ] Other:

## Screenshots / Media
<!-- If this PR changes the UI, README visuals, or terminal output, add a screenshot or GIF. -->

## Performance Impact
<!-- If this PR affects speed or memory, paste a snippet from `make benchmark` or other tools. -->

## GSSoC labels
<!-- Maintainers only: use exact scoring labels where applicable, for example `gssoc:approved`, `level:beginner`, `quality:clean`, and `type:bug`. Do not add labels only to increase points. -->

## Contributor checklist
- [ ] I read the contributing guide.
- [ ] I kept the PR focused on one issue or one logical change.
- [ ] I added or updated tests for behavior changes.
- [ ] I added or updated docs/examples for public API changes.
- [ ] I checked that generated files, logs, and local build artifacts are not committed.
- [ ] My PR title uses Conventional Commits (`feat:`, `fix:`, `docs:`, `test:`, `refactor:`, `chore:`).

## Maintainer notes
<!-- Optional: risks, migration notes, release notes, or follow-up work. -->
