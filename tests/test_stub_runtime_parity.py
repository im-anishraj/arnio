import importlib
import inspect
import re
from pathlib import Path

import pytest


def _find_stub_file():
    repo_root = Path(__file__).resolve().parent.parent
    candidates = [repo_root / "arnio" / "_arnio_cpp.pyi", repo_root / "arnio" / "_core.pyi"]
    for p in candidates:
        if p.exists():
            return p
    # fallback: first .pyi under arnio/
    for p in (repo_root / "arnio").glob("*.pyi"):
        return p
    return None


@pytest.mark.parametrize("module_name, stub_name", [("arnio._arnio_cpp", "_arnio_cpp.pyi")])
def test_stub_runtime_symbol_parity(module_name, stub_name):
    stub_path = _find_stub_file()
    if stub_path is None:
        pytest.skip("No .pyi stub found in arnio/; skipping parity test")

    try:
        mod = importlib.import_module(module_name)
    except Exception as exc:  # pragma: no cover - import may fail on dev machines
        pytest.skip(f"Could not import {module_name}: {exc}")

    text = stub_path.read_text(encoding="utf8")

    # collect top-level defs and classes (avoid indented methods)
    names = set()
    for m in re.finditer(r"^(?:class|def)\s+([A-Za-z_][A-Za-z0-9_]*)", text, flags=re.MULTILINE):
        names.add(m.group(1))

    assert names, f"No top-level symbols parsed from {stub_path}"

    missing = []
    for name in sorted(names):
        if not hasattr(mod, name):
            missing.append(name)
            continue
        attr = getattr(mod, name)
        # best-effort check: classes should be class-like, defs callable
        if name[0].isupper():
            if not inspect.isclass(attr):
                missing.append(name)
        else:
            if not (callable(attr) or inspect.isbuiltin(attr)):
                missing.append(name)

    if missing:
        pytest.fail(
            f"Runtime module {module_name} is missing symbols or shape for: {', '.join(missing)}\n"
            f"Stub file: {stub_path}"
        )
