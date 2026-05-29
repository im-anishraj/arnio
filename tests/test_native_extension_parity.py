"""Parity checks for the native `_arnio_cpp` extension surface.

The repository does not currently ship tracked `.pyi` stubs for the extension,
so this test derives the expected public contract from `bindings/bind_arnio.cpp`
and verifies the built runtime module still exposes the same symbols and class
members.
"""

import re
from collections import defaultdict
from pathlib import Path

import pytest


def _parse_binding_contract():
    binding_path = (
        Path(__file__).resolve().parents[1] / "bindings" / "bind_arnio.cpp"
    )
    text = binding_path.read_text(encoding="utf-8")

    top_level_names = set()
    class_methods = defaultdict(set)
    class_attributes = defaultdict(set)
    current_class = None

    for line in text.splitlines():
        enum_match = re.search(r'py::enum_<[^>]+>\(m,\s*"([^"]+)"\)', line)
        if enum_match:
            top_level_names.add(enum_match.group(1))

        class_match = re.search(r'py::class_<[^>]+>\(m,\s*"([^"]+)"\)', line)
        if class_match:
            current_class = class_match.group(1)
            top_level_names.add(current_class)
            continue

        if current_class is not None:
            for method_name in re.findall(r'\.def(?:_static)?\("([^"]+)"', line):
                class_methods[current_class].add(method_name)
            for attribute_name in re.findall(r'\.def_readwrite\("([^"]+)"', line):
                class_attributes[current_class].add(attribute_name)

            if line.strip().endswith(");"):
                current_class = None
                continue

        for name in re.findall(r'm\.def\("([^"]+)"', line):
            top_level_names.add(name)

        for name in re.findall(r'\.value\("([^"]+)"', line):
            top_level_names.add(name)

    return top_level_names, class_methods, class_attributes


def test_native_extension_exports_match_binding_contract():
    cpp = pytest.importorskip("arnio._arnio_cpp")

    expected_names, class_methods, class_attributes = _parse_binding_contract()

    missing_names = sorted(
        name for name in expected_names if not hasattr(cpp, name)
    )
    assert not missing_names, (
        "Native extension is missing expected public symbols: "
        f"{', '.join(missing_names)}"
    )

    for class_name, methods in sorted(class_methods.items()):
        cls = getattr(cpp, class_name)
        missing_methods = sorted(
            method for method in methods if not hasattr(cls, method)
        )
        assert not missing_methods, (
            f"{class_name} is missing expected methods: {', '.join(missing_methods)}"
        )

    for class_name, attributes in sorted(class_attributes.items()):
        instance = getattr(cpp, class_name)()
        missing_attributes = sorted(
            attribute for attribute in attributes if not hasattr(instance, attribute)
        )
        assert not missing_attributes, (
            f"{class_name} is missing expected attributes: "
            f"{', '.join(missing_attributes)}"
        )
