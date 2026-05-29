import re
import sys
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

PROJECT_ROOT = Path(__file__).parent.parent
PYPROJECT_PATH = PROJECT_ROOT / "pyproject.toml"


def test_pyproject_metadata_is_valid():
    """Validate python packaging metadata in pyproject.toml."""
    with PYPROJECT_PATH.open("rb") as f:
        pyproject = tomllib.load(f)

    project = pyproject.get("project", {})

    # 1. requires-python
    requires_python = project.get("requires-python")
    assert requires_python is not None, "requires-python must be specified"
    assert requires_python.startswith(">="), "requires-python should start with >="

    min_version = requires_python.replace(">=", "").strip()

    # 2. python version classifiers
    classifiers = project.get("classifiers", [])
    python_classifiers = [
        c.replace("Programming Language :: Python :: ", "")
        for c in classifiers
        if c.startswith("Programming Language :: Python ::")
    ]

    assert (
        "3" in python_classifiers
    ), "Must include 'Programming Language :: Python :: 3'"
    assert (
        min_version in python_classifiers
    ), f"Missing classifier for min version {min_version}"

    # 3. project URLs
    urls = project.get("urls", {})
    assert urls, "Project URLs must be defined"

    required_url_keys = {"Homepage", "Repository", "Issues"}
    missing_urls = required_url_keys - urls.keys()
    assert not missing_urls, f"Missing required URLs: {missing_urls}"

    for name, url in urls.items():
        assert url.startswith("http"), f"URL for {name} must be valid HTTP/HTTPS"

    # 4. Metadata consistency
    # Name and version should be present
    assert project.get("name"), "Project name must be specified"
    assert project.get("version"), "Project version must be specified"
    assert project.get("description"), "Project description must be specified"


def test_release_workflow_version_regex():
    version_pattern = r"^\d+\.\d+\.\d+(?:-[a-zA-Z0-9.-]+)?$"

    with PYPROJECT_PATH.open("rb") as f:
        pyproject = tomllib.load(f)
    current_version = pyproject.get("project", {}).get("version", "")
    assert (
        bool(re.match(version_pattern, current_version)) is True
    ), f"Current version '{current_version}' fails validation pattern"

    assert bool(re.match(version_pattern, "1.18.0")) is True
    assert bool(re.match(version_pattern, "0.1.0")) is True
    assert bool(re.match(version_pattern, "1.18.0-rc.1")) is True

    assert bool(re.match(version_pattern, "1.18.0oops")) is False
    assert bool(re.match(version_pattern, "1.2.3valid-until-here")) is False
    assert bool(re.match(version_pattern, "v1.0.0")) is False
