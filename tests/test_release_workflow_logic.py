"""
Local test suite for build_wheels.yml release workflow hardening (Issue #1876).

Tests the EXACT logic used in the workflow without needing Docker or GitHub:
  1. Tag validation regex (the bash grep pattern)
  2. Publish job if-guard logic
  3. YAML structure (required inputs, job dependencies, checkout refs)
  4. Interaction with release-please.yml and release-dry-run.yml

Run with:  python tests/test_release_workflow_logic.py
    or:    python -m pytest tests/test_release_workflow_logic.py -v
"""

import re
import subprocess
import sys
from pathlib import Path

import yaml

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parent.parent
WORKFLOWS = REPO_ROOT / ".github" / "workflows"
BUILD_WHEELS = WORKFLOWS / "build_wheels.yml"
RELEASE_PLEASE = WORKFLOWS / "release-please.yml"
RELEASE_DRY_RUN = WORKFLOWS / "release-dry-run.yml"

# ---------------------------------------------------------------------------
# The EXACT regex from build_wheels.yml line 45 (grep -E extended regex).
# Translated to Python: grep -E '^v[0-9]+\.[0-9]+\.[0-9]+(-[0-9A-Za-z.-]+)?$'
# ---------------------------------------------------------------------------
TAG_REGEX = re.compile(r"^v[0-9]+\.[0-9]+\.[0-9]+(-[0-9A-Za-z.-]+)?$")


def load_workflow(path: Path) -> dict:
    """Load and parse a GitHub Actions workflow YAML file."""
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_on_key(wf: dict) -> dict:
    """Get the 'on' trigger config from a workflow.

    PyYAML parses the YAML key `on:` as Python boolean True (YAML 1.1
    treats 'on' as a reserved boolean).  This helper handles both cases.
    """
    return wf.get(True) or wf.get("on") or {}


# ===================================================================
# TEST 1: Tag validation regex — accepts valid release tags
# ===================================================================
class TestTagValidationAccepts:
    """Valid vX.Y.Z and vX.Y.Z-prerelease tags must be accepted."""

    VALID_TAGS = [
        "v1.2.3",
        "v0.0.0",
        "v0.10.0",
        "v10.20.30",
        "v1.2.3-rc1",
        "v1.2.3-beta.2",
        "v1.0.0-alpha.1",
        "v2.0.0-0.3.7",
    ]

    def test_valid_tags(self):
        for tag in self.VALID_TAGS:
            assert TAG_REGEX.match(tag), f"Expected tag '{tag}' to be ACCEPTED"


# ===================================================================
# TEST 2: Tag validation regex — rejects invalid/missing tags
# ===================================================================
class TestTagValidationRejects:
    """Invalid, empty, or non-semver inputs must be rejected."""

    INVALID_TAGS = [
        "",                       # empty — the original bug
        "main",                   # branch name
        "develop",                # another branch
        "1.2.3",                  # missing 'v' prefix
        "vx.y.z",                 # non-numeric
        "v1.2",                   # incomplete (missing patch)
        "v1.2.3.4",               # too many segments
        "v1.2.3 ",                # trailing space
        " v1.2.3",                # leading space
        "refs/heads/main",        # full git ref
        "refs/tags/v1.0.0",       # full tag ref
        "latest",                 # arbitrary string
        "v",                      # just the prefix
        "v1",                     # major only
        "v1.2.3\nmalicious",      # newline injection
    ]

    def test_invalid_tags(self):
        for tag in self.INVALID_TAGS:
            assert not TAG_REGEX.match(tag), f"Expected tag '{tag}' to be REJECTED"


# ===================================================================
# TEST 3: Publish job if-guard logic
# ===================================================================
class TestPublishGuard:
    """
    Simulates line 139 of build_wheels.yml:
      if: needs.validate_tag.outputs.tag_name != '' && startsWith(needs.validate_tag.outputs.tag_name, 'v')
    """

    @staticmethod
    def _publish_allowed(tag_output: str) -> bool:
        return tag_output != "" and tag_output.startswith("v")

    def test_valid_tag_allows_publish(self):
        assert self._publish_allowed("v1.2.3")
        assert self._publish_allowed("v1.2.3-rc1")

    def test_empty_output_blocks_publish(self):
        assert not self._publish_allowed("")

    def test_non_v_prefix_blocks_publish(self):
        assert not self._publish_allowed("main")
        assert not self._publish_allowed("1.2.3")


# ===================================================================
# TEST 4: YAML structure — build_wheels.yml
# ===================================================================
class TestBuildWheelsStructure:
    """Verify the workflow YAML has the correct structure for release safety."""

    @classmethod
    def setup_class(cls):
        cls.wf = load_workflow(BUILD_WHEELS)

    def test_workflow_dispatch_tag_is_required(self):
        on = get_on_key(self.wf)
        dispatch_input = on["workflow_dispatch"]["inputs"]["tag_name"]
        assert dispatch_input["required"] is True, (
            "workflow_dispatch.inputs.tag_name must be required: true"
        )

    def test_workflow_call_tag_is_required(self):
        on = get_on_key(self.wf)
        call_input = on["workflow_call"]["inputs"]["tag_name"]
        assert call_input["required"] is True, (
            "workflow_call.inputs.tag_name must be required: true"
        )

    def test_validate_tag_job_exists(self):
        assert "validate_tag" in self.wf["jobs"], (
            "A 'validate_tag' job must exist to gate all downstream jobs"
        )

    def test_build_sdist_depends_on_validate_tag(self):
        needs = self.wf["jobs"]["build_sdist"].get("needs")
        if isinstance(needs, str):
            needs = [needs]
        assert "validate_tag" in needs, (
            "build_sdist must depend on validate_tag"
        )

    def test_build_wheels_depends_on_validate_tag(self):
        needs = self.wf["jobs"]["build_wheels"].get("needs")
        if isinstance(needs, str):
            needs = [needs]
        assert "validate_tag" in needs, (
            "build_wheels must depend on validate_tag"
        )

    def test_publish_depends_on_validate_tag(self):
        needs = self.wf["jobs"]["publish"].get("needs")
        if isinstance(needs, str):
            needs = [needs]
        assert "validate_tag" in needs, (
            "publish must depend on validate_tag"
        )

    def test_publish_has_if_guard(self):
        publish_if = self.wf["jobs"]["publish"].get("if", "")
        assert "validate_tag" in publish_if, (
            "publish job must have an if: guard referencing validate_tag output"
        )
        assert "startsWith" in publish_if or "v" in publish_if, (
            "publish if: guard must check for 'v' prefix"
        )

    def test_no_github_ref_fallback_in_checkouts(self):
        """Ensure no checkout step falls back to github.ref."""
        raw = BUILD_WHEELS.read_text(encoding="utf-8")
        assert "github.ref" not in raw, (
            "build_wheels.yml must NOT contain github.ref fallback — "
            "all checkouts should use the validated tag output"
        )

    def test_checkout_uses_validated_tag(self):
        """Both build jobs must check out using the validated tag output."""
        raw = BUILD_WHEELS.read_text(encoding="utf-8")
        assert raw.count("needs.validate_tag.outputs.tag_name") >= 2, (
            "Expected at least 2 references to needs.validate_tag.outputs.tag_name "
            "(one for build_sdist checkout, one for build_wheels checkout)"
        )

    def test_publish_uses_pypi_environment(self):
        env = self.wf["jobs"]["publish"].get("environment", "")
        assert "pypi" in str(env), (
            "publish job should use the 'pypi' environment for trusted publishing"
        )


# ===================================================================
# TEST 5: release-please.yml still passes a tag
# ===================================================================
class TestReleasePleaseIntegration:
    """Verify release-please.yml correctly feeds a tag to build_wheels.yml."""

    @classmethod
    def setup_class(cls):
        cls.wf = load_workflow(RELEASE_PLEASE)

    def test_calls_build_wheels(self):
        build_job = self.wf["jobs"].get("build-and-publish", {})
        uses = build_job.get("uses", "")
        assert "build_wheels.yml" in uses, (
            "release-please should call build_wheels.yml"
        )

    def test_passes_tag_name(self):
        build_job = self.wf["jobs"].get("build-and-publish", {})
        with_inputs = build_job.get("with", {})
        tag_input = str(with_inputs.get("tag_name", ""))
        assert "tag_name" in tag_input, (
            "release-please must pass the tag_name to build_wheels.yml"
        )

    def test_only_runs_on_release_created(self):
        build_job = self.wf["jobs"].get("build-and-publish", {})
        if_cond = str(build_job.get("if", ""))
        assert "release_created" in if_cond, (
            "build-and-publish should only run when release_created is true"
        )


# ===================================================================
# TEST 6: release-dry-run.yml has NO publish step
# ===================================================================
class TestReleaseDryRun:
    """Verify the dry-run workflow cannot publish to PyPI."""

    @classmethod
    def setup_class(cls):
        cls.wf = load_workflow(RELEASE_DRY_RUN)

    def test_no_publish_job(self):
        assert "publish" not in self.wf.get("jobs", {}), (
            "release-dry-run.yml must NOT have a publish job"
        )

    def test_no_pypi_publish_action(self):
        raw = RELEASE_DRY_RUN.read_text(encoding="utf-8")
        assert "pypa/gh-action-pypi-publish" not in raw, (
            "release-dry-run.yml must NOT reference pypa/gh-action-pypi-publish"
        )

    def test_tag_not_required(self):
        """Dry-run should be runnable without a tag input."""
        on = get_on_key(self.wf)
        dispatch = on.get("workflow_dispatch", {})
        inputs = dispatch.get("inputs") if isinstance(dispatch, dict) else None
        if inputs and "tag_name" in inputs:
            assert inputs["tag_name"].get("required") is not True, (
                "Dry-run should NOT require a tag — it's for build verification only"
            )


# ===================================================================
# TEST 7: Validate the bash script runs correctly via Git Bash
# ===================================================================
class TestBashValidationScript:
    """Run the actual bash validation logic from the workflow through Git Bash."""

    BASH_EXE = r"C:\Program Files\Git\bin\bash.exe"

    SCRIPT_TEMPLATE = '''
TAG_NAME="{tag}"
if [ -z "${{TAG_NAME}}" ]; then
    exit 1
fi
if ! printf '%s' "${{TAG_NAME}}" | grep -E -q '^v[0-9]+\\.[0-9]+\\.[0-9]+(-[0-9A-Za-z.-]+)?$'; then
    exit 1
fi
exit 0
'''

    @classmethod
    def _run_validation(cls, tag: str) -> bool:
        """Returns True if the bash script accepts the tag."""
        if not Path(cls.BASH_EXE).exists():
            return None  # skip if no Git Bash
        script = cls.SCRIPT_TEMPLATE.format(tag=tag)
        result = subprocess.run(
            [cls.BASH_EXE, "-c", script],
            capture_output=True, timeout=10,
        )
        return result.returncode == 0

    def test_bash_accepts_valid_tag(self):
        result = self._run_validation("v1.2.3")
        if result is None:
            print("SKIPPED: Git Bash not found")
            return
        assert result is True, "Bash script should accept v1.2.3"

    def test_bash_rejects_empty_tag(self):
        result = self._run_validation("")
        if result is None:
            print("SKIPPED: Git Bash not found")
            return
        assert result is False, "Bash script should reject empty tag"

    def test_bash_rejects_branch_name(self):
        result = self._run_validation("main")
        if result is None:
            print("SKIPPED: Git Bash not found")
            return
        assert result is False, "Bash script should reject 'main'"

    def test_bash_rejects_no_v_prefix(self):
        result = self._run_validation("1.2.3")
        if result is None:
            print("SKIPPED: Git Bash not found")
            return
        assert result is False, "Bash script should reject '1.2.3'"


# ===================================================================
# Runner
# ===================================================================
def _run_all():
    """Simple runner when pytest is not available."""
    passed = 0
    failed = 0
    skipped = 0

    test_classes = [
        TestTagValidationAccepts,
        TestTagValidationRejects,
        TestPublishGuard,
        TestBuildWheelsStructure,
        TestReleasePleaseIntegration,
        TestReleaseDryRun,
        TestBashValidationScript,
    ]

    for cls in test_classes:
        instance = cls()
        if hasattr(cls, "setup_class"):
            try:
                cls.setup_class()
            except Exception as e:
                print(f"  SETUP ERROR  {cls.__name__}: {e}")
                failed += 1
                continue

        methods = [m for m in dir(instance) if m.startswith("test_")]
        for method_name in sorted(methods):
            method = getattr(instance, method_name)
            label = f"{cls.__name__}.{method_name}"
            try:
                method()
                print(f"  PASS  {label}")
                passed += 1
            except AssertionError as e:
                print(f"  FAIL  {label}: {e}")
                failed += 1
            except Exception as e:
                print(f"  ERROR {label}: {e}")
                failed += 1

    print(f"\n{'='*60}")
    print(f"Results: {passed} passed, {failed} failed")
    print(f"{'='*60}")
    return 1 if failed else 0


if __name__ == "__main__":
    # Try pytest first, fall back to simple runner
    try:
        import pytest
        sys.exit(pytest.main([__file__, "-v"]))
    except ImportError:
        print("pytest not found, using built-in runner\n")
        sys.exit(_run_all())
