# Contributing to Arnio

First off, thank you for considering contributing to Arnio. Whether you're fixing a bug, adding a new pipeline step, improving tests, or writing documentation, your help makes the project stronger.

If you are contributing through GSSoC 2026, read [GSSOC_GUIDE.md](../GSSOC_GUIDE.md) before asking to be assigned.

## Quick Start (Local Setup)

To set up your local development environment:

### macOS / Linux
```bash
git clone https://github.com/im-anishraj/arnio.git
cd arnio
make install
make test
make lint
```

### Windows Setup
Install [Visual Studio Build Tools](https://visualstudio.microsoft.com/downloads/#build-tools-for-visual-studio-2022) with the "Desktop development with C++" workload, then run:

```bash
git clone https://github.com/im-anishraj/arnio.git
cd arnio
pip install -e ".[dev]"
pre-commit install
```
Alternatively, use WSL for a faster setup experience.

**Windows users:** Install `make` via [Chocolatey](https://chocolatey.org/): `choco install make`  
Or run the commands manually — each `make` target is just one or two commands inside the `Makefile`.

---

## Adding a Pure Python Pipeline Step (No C++ Required)

Most new features do not require touching C++! You can write a pure Python step and register it with Arnio. This is how 90% of GSSoC contributors will contribute.

1. Write a function that accepts and returns a `pd.DataFrame`.
2. Register it before calling `pipeline()`.
3. Write tests in `tests/test_cleaning.py`.
4. Open a PR.

### Example
```python
import arnio as ar

def remove_special_chars(df, columns=None):
    cols = columns or df.select_dtypes("object").columns
    for col in cols:
        df[col] = df[col].str.replace(r"[^a-zA-Z0-9\s]", "", regex=True)
    return df

ar.register_step("remove_special_chars", remove_special_chars)
```

### Contribution Testing Standard
When adding new pipeline steps (like the Python registry example above), you must write tests that mirror the round-trip verification pattern.

Example in `tests/test_cleaning.py`:
```python
def test_remove_special_chars(sample_csv):
    ar.register_step("remove_special_chars", remove_special_chars)
    frame = ar.read_csv(sample_csv)
    
    result = ar.pipeline(frame, [
        ("remove_special_chars",),
    ])
    df = ar.to_pandas(result)
    
    assert "name" in df.columns
    # Add your specific assertions here
```

---

## Pull Request Process

1. Fork the repo and create your branch from `main`.
2. Claim one issue by commenting with your approach. Wait for maintainer confirmation before starting GSSoC-scored work.
3. Keep your PR focused. One issue should normally mean one pull request.
4. If you've added code that should be tested, add tests.
5. If you've changed public behavior, update documentation or examples.
6. Ensure the test suite passes (`make test`).
7. Ensure your code passes linting (`make lint`). This is a required pre-PR step.
8. Open the pull request and link the issue with `Fixes #issue-number` when complete.
9. Ensure your PR title follows **Conventional Commits**.

### Review expectations

- Do not open duplicate PRs for the same issue.
- Do not mix unrelated formatting, refactors, and features in one PR.
- Do not edit generated files, build output, cache folders, or local logs.
- Be patient during review. Maintainers may ask for tests, edge cases, or a narrower scope.
- If you stop working on an assigned issue, please comment so it can be reassigned.

### Commit Message Convention
We use an automated release system that relies on [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/). Your PR title must use one of the following prefixes:
- `feat:` for new features (e.g., `feat: add robust boolean parsing`)
- `fix:` for bug fixes (e.g., `fix: memory leak in string allocation`)
- `docs:` for documentation changes
- `chore:` for maintenance (e.g., CI/CD changes)

This allows our CI to automatically generate changelogs and bump version numbers.

We use `black`, `ruff`, and `clang-format` to format our code. `pre-commit` will run these automatically before each commit if installed.

