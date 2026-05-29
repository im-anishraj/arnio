# C++ native tests — Phase 0 cross-platform baseline

Temporary baseline from `.github/workflows/cpp-tests-baseline-phase0.yml` (workflow_dispatch).
Drives Phase 1 unification of `ci.yml` `cpp_tests`.

Commands (all platforms):

```bash
pip install pybind11 ninja
cmake -S . -B build -GNinja -DCMAKE_BUILD_TYPE=Debug \
  -DARNIO_BUILD_CPP_TESTS=ON \
  -DCMAKE_PREFIX_PATH="$(python -c "import pybind11; print(pybind11.get_cmake_dir())")"
cmake --build build --parallel
ctest --test-dir build --output-on-failure
```

Windows additionally needs MSVC on `PATH` (`ilammy/msvc-dev-cmd` in CI; x64 Developer Command Prompt locally).

## Results

| Platform | Result | First failing step | Notes |
|----------|--------|-------------------|-------|
| Ubuntu (ubuntu-latest) | _pending CI_ | — | Local WSL: **pass** (4/4 ctest, Ninja single-config, no `--config`) |
| Windows (windows-latest) | _pending CI_ | — | Uses `ilammy/msvc-dev-cmd@v1` before configure |
| macOS (macos-latest) | _pending CI_ | — | Clang; FetchContent Catch2 |

### Generator / `CMAKE_BUILD_TYPE`

| Platform | Generator | `-DCMAKE_BUILD_TYPE=Debug` honored? | `ctest` needs `--config Debug`? |
|----------|-----------|-------------------------------------|----------------------------------|
| Ubuntu | _pending CI_ | — | — |
| Windows | _pending CI_ | — | — |
| macOS | _pending CI_ | — | — |

### MSVC / compile errors (Phase 1 fixes)

_Will fill from failed Windows logs if any._

---

_Last updated: workflow run pending._
