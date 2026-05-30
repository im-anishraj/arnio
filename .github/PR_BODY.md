## Summary
This PR replaces the `std::ostringstream` based string serialization in `drop_duplicates` with proper hash-based comparisons. This avoids expensive string allocations per row and improves performance, bringing it closer to pandas performance parity.

## Linked issue
Fixes #324

## Type of change
- [ ] Bug fix
- [ ] Feature
- [x] Performance improvement
- [ ] Documentation
- [ ] Tests
- [ ] Refactor
- [ ] CI / packaging

## Area
- [ ] CSV parser / I/O
- [x] C++ cleaning engine
- [ ] Python API / ArFrame
- [ ] Pipeline / custom steps
- [ ] Data quality / profiling
- [ ] Schema validation
- [ ] pandas interoperability
- [ ] Docs / website
- [ ] Developer tooling

## Testing
- [x] `make test`
- [x] `make lint`
- [ ] Other:

## Contributor checklist
- [x] I read the contributing guide.
- [x] I kept the PR focused on one issue or one logical change.
- [x] I added or updated tests for behavior changes.
- [x] I added or updated docs/examples for public API changes.
- [x] I checked that generated files, logs, and local build artifacts are not committed.
- [x] My PR title uses Conventional Commits (`feat:`, `fix:`, `docs:`, `test:`, `refactor:`, `chore:`).

## Maintainer notes
N/A
