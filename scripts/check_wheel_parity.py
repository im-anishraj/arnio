#!/usr/bin/env python3
"""
Wheel artifact parity check for arnio.

Receives a pre-built wheel (built by CI before this script runs), installs it
into a fresh venv, then verifies:
  1. All runtime .py files under arnio/ in the source tree are present in the
     installed package (explicit EXCLUDE_ALLOWLIST for intentional omissions).
  2. Every source module that exists is importable from the installed wheel.
  3. arnio.__all__ and arnio.integrations.__all__ (if they exist) contain at
     least the symbols declared in the source __init__.py files.

Exit 0  -> parity check passed.
Exit 1  -> one or more checks failed (details printed to stdout).

Usage:
    python scripts/check_wheel_parity.py path/to/arnio-*.whl

The script assumes it is run from the repository root.
"""

import ast
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import textwrap
import venv

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

PACKAGE_NAME = "arnio"
SOURCE_ROOT = pathlib.Path(__file__).parent.parent  # repo root
PACKAGE_DIR = SOURCE_ROOT / PACKAGE_NAME

# Files intentionally excluded from the wheel (build artefacts, dev helpers).
# Add entries here when a file should NOT be shipped so the check won't flag
# its absence.  Format: "arnio/relative/path.py"
EXCLUDE_ALLOWLIST: set[str] = {
    # e.g. "arnio/_dev_only.py",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _collect_source_py_files() -> set[str]:
    """Return relative paths like ``arnio/cli.py`` for every source .py file."""
    files: set[str] = set()
    for path in PACKAGE_DIR.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        rel = str(path.relative_to(SOURCE_ROOT))
        files.add(rel.replace(os.sep, "/"))
    return files


def _py_file_to_module(rel_path: str) -> str:
    """Convert ``arnio/integrations/polars.py`` -> ``arnio.integrations.polars``."""
    mod = rel_path.replace("/", ".").replace("\\", ".")
    if mod.endswith(".__init__.py"):
        mod = mod[: -len(".__init__.py")]
    elif mod.endswith(".py"):
        mod = mod[:-3]
    return mod


def _collect_source_all_exports(init_path: pathlib.Path) -> list[str]:
    """
    Parse *init_path* with AST and return the contents of its ``__all__`` list.
    Returns an empty list if no ``__all__`` is defined or the file can't be parsed.
    """
    try:
        tree = ast.parse(init_path.read_text(encoding="utf-8"))
    except Exception:
        return []
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and node.targets[0].id == "__all__"
            and isinstance(node.value, (ast.List, ast.Tuple))
        ):
            return [
                elt.s
                for elt in node.value.elts
                if isinstance(elt, ast.Constant) and isinstance(elt.s, str)
            ]
    return []


def _install_wheel(venv_dir: pathlib.Path, wheel_path: pathlib.Path) -> None:
    """Install *wheel_path* into *venv_dir*."""
    python = venv_dir / ("Scripts" if sys.platform == "win32" else "bin") / "python"
    print(f"  Installing wheel: {wheel_path.name} …")
    subprocess.check_call(
        [str(python), "-m", "pip", "install", "--quiet", str(wheel_path)],
    )


def _collect_installed_py_files(
    venv_dir: pathlib.Path, safe_cwd: pathlib.Path
) -> set[str]:
    """Return relative paths for every .py file installed under site-packages/arnio.

    Runs from *safe_cwd* (outside the repo root) so the source tree is never on
    sys.path and the wheel-installed package is what gets found.
    """
    python = venv_dir / ("Scripts" if sys.platform == "win32" else "bin") / "python"
    code = textwrap.dedent(f"""
        import importlib.util, pathlib, json, os, sys
        # Remove any path entries that could resolve to the source tree
        sys.path = [p for p in sys.path if "arnio" not in p.lower() or "site-packages" in p.lower()]
        spec = importlib.util.find_spec("{PACKAGE_NAME}")
        pkg_root = pathlib.Path(spec.origin).parent
        files = set()
        for p in pkg_root.rglob("*.py"):
            if "__pycache__" in p.parts:
                continue
            rel = str(p.relative_to(pkg_root.parent)).replace(os.sep, "/")
            files.add(rel)
        print(json.dumps(sorted(files)))
        """)
    result = subprocess.check_output(
        [str(python), "-c", code], text=True, cwd=str(safe_cwd)
    )
    return set(json.loads(result.strip()))


def _check_imports(
    venv_dir: pathlib.Path, modules: list[str], safe_cwd: pathlib.Path
) -> list[str]:
    """Return modules that failed to import inside the venv.

    Runs from *safe_cwd* (outside the repo root) so only the wheel-installed
    package is visible, not the source tree.

    Failures caused by a missing *third-party* optional dependency (i.e. the
    ModuleNotFoundError names a package outside arnio) are skipped — those
    integrations are intentionally optional and their absence does not indicate
    a wheel packaging problem.
    """
    python = venv_dir / ("Scripts" if sys.platform == "win32" else "bin") / "python"
    failures: list[str] = []
    for mod in modules:
        try:
            subprocess.check_output(
                [str(python), "-c", f"import {mod}"],
                stderr=subprocess.STDOUT,
                text=True,
                cwd=str(safe_cwd),
            )
        except subprocess.CalledProcessError as exc:
            output = exc.output.strip()
            # If the error is a ModuleNotFoundError for a package that is NOT
            # part of arnio itself, it means an optional third-party dependency
            # (e.g. sklearn, polars, duckdb) is not installed.  That is
            # expected in a minimal venv and is not a wheel packaging fault.
            if (
                "ModuleNotFoundError" in output
                and "arnio" not in _extract_missing_module(output)
            ):
                print(f"  SKIP (optional dep missing): {mod}")
                continue
            failures.append(f"{mod}  ->  {output[:200]}")
    return failures


def _extract_missing_module(error_output: str) -> str:
    """Pull the module name out of a ModuleNotFoundError traceback."""
    for line in error_output.splitlines():
        if "ModuleNotFoundError" in line or "No module named" in line:
            # e.g. "ModuleNotFoundError: No module named 'sklearn'"
            parts = line.split("'")
            if len(parts) >= 2:
                return parts[1].split(".")[0]
    return ""


def _check_exports(
    venv_dir: pathlib.Path,
    mod_name: str,
    required: list[str],
    safe_cwd: pathlib.Path,
) -> list[str]:
    """Return symbols missing from mod_name.__all__ in the installed wheel.

    Runs from *safe_cwd* (outside the repo root) so only the wheel-installed
    package is visible, not the source tree.
    """
    if not required:
        return []
    python = venv_dir / ("Scripts" if sys.platform == "win32" else "bin") / "python"
    code = textwrap.dedent(f"""
        import json
        try:
            import {mod_name}
            exports = getattr({mod_name}, "__all__", [])
            print(json.dumps(list(exports)))
        except Exception as e:
            print(json.dumps({{"error": str(e)}}))
        """)
    result = subprocess.check_output(
        [str(python), "-c", code], text=True, cwd=str(safe_cwd)
    )
    parsed = json.loads(result.strip())
    if isinstance(parsed, dict) and "error" in parsed:
        return [f"{mod_name}.__all__: could not inspect — {parsed['error']}"]
    present = set(parsed)
    return [
        f"{mod_name}.__all__ is missing symbol: {sym!r}"
        for sym in required
        if sym not in present
    ]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    if len(sys.argv) < 2:
        print(
            "Usage: python scripts/check_wheel_parity.py <path/to/wheel.whl or dist/>"
        )
        return 1

    arg = pathlib.Path(sys.argv[1])

    # Accept either a direct .whl path or a directory — the latter lets the
    # caller pass "dist/" without shell-globbing (needed on Windows/PowerShell).
    if arg.is_dir():
        wheels = list(arg.glob("*.whl"))
        if not wheels:
            print(f"ERROR: no .whl files found in directory: {arg}")
            return 1
        wheel_path = wheels[0]
    else:
        wheel_path = arg
        if not wheel_path.exists():
            print(f"ERROR: wheel not found: {wheel_path}")
            return 1

    all_failures: list[str] = []

    print("=" * 60)
    print("arnio wheel parity check")
    print(f"Wheel: {wheel_path.name}")
    print("=" * 60)

    # Step A — collect source files and derive modules/exports from source
    print("\n[A] Collecting source .py files …")
    source_files = _collect_source_py_files()
    print(f"    {len(source_files)} .py files found in source tree.")

    # Derive importable module names from every source .py file
    source_modules = [
        _py_file_to_module(f)
        for f in sorted(source_files)
        if f not in EXCLUDE_ALLOWLIST
    ]

    # Read __all__ from source __init__.py files so we check what the source
    # actually declares, not a hardcoded list
    top_init = PACKAGE_DIR / "__init__.py"
    integrations_init = PACKAGE_DIR / "integrations" / "__init__.py"
    source_top_exports = (
        _collect_source_all_exports(top_init) if top_init.exists() else []
    )
    source_int_exports = (
        _collect_source_all_exports(integrations_init)
        if integrations_init.exists()
        else []
    )
    print(f"    arnio.__all__ declares {len(source_top_exports)} symbol(s) in source.")
    print(
        f"    arnio.integrations.__all__ declares "
        f"{len(source_int_exports)} symbol(s) in source."
    )

    # Step B — install wheel into a fresh venv
    # safe_cwd is a temp dir *outside* the repo so subprocess invocations that
    # import arnio cannot accidentally pick up the source tree instead of the
    # wheel-installed package.
    print("\n[B] Creating clean venv and installing wheel …")
    with (
        tempfile.TemporaryDirectory(prefix="arnio_parity_") as venv_path,
        tempfile.TemporaryDirectory(prefix="arnio_cwd_") as safe_cwd_path,
    ):
        venv_dir = pathlib.Path(venv_path)
        safe_cwd = pathlib.Path(safe_cwd_path)
        venv.create(str(venv_dir), with_pip=True, clear=True)
        _install_wheel(venv_dir, wheel_path)

        # Step C — collect installed files
        print("\n[C] Collecting installed .py files …")
        installed_files = _collect_installed_py_files(venv_dir, safe_cwd)
        print(f"    {len(installed_files)} .py files found in installed wheel.")

        # Step D — file parity
        print("\n[D] Checking file parity …")
        missing_in_wheel: list[str] = []
        for f in sorted(source_files):
            if f in EXCLUDE_ALLOWLIST:
                continue
            if f not in installed_files:
                missing_in_wheel.append(f)

        if missing_in_wheel:
            all_failures.append(
                "Files present in source but MISSING from wheel:\n"
                + "\n".join(f"  - {f}" for f in missing_in_wheel)
            )
            print(f"  FAIL: {len(missing_in_wheel)} file(s) missing from wheel.")
        else:
            print("  PASS: all source .py files present in wheel.")

        # Step E — import checks (only modules that exist in source)
        print(f"\n[E] Checking {len(source_modules)} source module(s) are importable …")
        import_failures = _check_imports(venv_dir, source_modules, safe_cwd)
        if import_failures:
            all_failures.append(
                "Modules that failed to import:\n"
                + "\n".join(f"  - {m}" for m in import_failures)
            )
            print(f"  FAIL: {len(import_failures)} import(s) failed.")
        else:
            print(f"  PASS: all {len(source_modules)} modules import cleanly.")

        # Step F — __all__ export checks (derived from source, not hardcoded)
        print("\n[F] Checking __all__ exports …")
        export_failures = _check_exports(
            venv_dir, "arnio", source_top_exports, safe_cwd
        )
        export_failures += _check_exports(
            venv_dir, "arnio.integrations", source_int_exports, safe_cwd
        )
        if export_failures:
            all_failures.append(
                "__all__ export mismatches:\n"
                + "\n".join(f"  - {e}" for e in export_failures)
            )
            print(f"  FAIL: {len(export_failures)} export symbol(s) missing.")
        else:
            print("  PASS: all __all__ exports match source declarations.")

    # Summary
    print("\n" + "=" * 60)
    if all_failures:
        print("RESULT: FAILED\n")
        for failure in all_failures:
            print(failure)
            print()
        return 1
    else:
        print("RESULT: PASSED — wheel is in parity with the source package.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
