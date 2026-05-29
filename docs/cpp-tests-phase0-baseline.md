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
| Ubuntu (ubuntu-latest) | **pass** | — | 4/4 ctest; [run 26637563979](https://github.com/shreyansh-tech21/arnio/actions/runs/26637563979) |
| Windows (windows-latest) | **pass** | — | Requires `ilammy/msvc-dev-cmd@v1` before configure; no `/WX` failures |
| macOS (macos-latest) | **pass** | — | FetchContent Catch2 OK; Clang; 4/4 ctest |

Local WSL (Ubuntu): **pass** — same cmake/ctest sequence, Ninja single-config.

### Generator / `CMAKE_BUILD_TYPE`

| Platform | Generator | `-DCMAKE_BUILD_TYPE=Debug` honored? | `ctest` needs `--config Debug`? |
|----------|-----------|-------------------------------------|----------------------------------|
| Ubuntu | Ninja | Yes (`CMAKE_BUILD_TYPE:STRING=Debug`) | **No** |
| Windows | Ninja | Yes | **No** |
| macOS | Ninja | Yes | **No** |

### MSVC / compile errors (Phase 1 fixes)

None on current `main` baseline — no code changes required for green cpp_tests on Windows with MSVC + Ninja.

## Phase 1 YAML checklist (from Phase 0)

1. **Matrix** `cpp_tests` on `ubuntu-latest`, `windows-latest`, `macos-latest` (or start with Windows/macOS only if Ubuntu job already exists).
2. **All runners:** `actions/setup-python@v6` with `3.12`, `pip install pybind11 ninja`, explicit `-GNinja`.
3. **Windows only:** `ilammy/msvc-dev-cmd@v1` (or `microsoft/setup-msvc` + dev cmd) **before** configure — without it, CMake may pick GCC or `cl` is missing.
4. **Ubuntu only:** keep `apt` `cmake` / `ninja-build` / `python3-dev` **or** rely on pip Ninja + setup-python (Phase 0 used both apt and pip).
5. **Do not** use Visual Studio multi-config generator in CI; if you ever do, add `--config Debug` to `cmake --build` and `ctest`.
6. **No** `--config` needed with Ninja + `-DCMAKE_BUILD_TYPE=Debug` on any of the three GHA images (verified).

---

_CI run: https://github.com/shreyansh-tech21/arnio/actions/runs/26637563979 — branch `ci/cpp-tests-cross-platform`._
