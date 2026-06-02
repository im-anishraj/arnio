from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).parent.parent
WORKFLOW_DIR = PROJECT_ROOT / ".github" / "workflows"


def load_workflow(name: str) -> dict:
    with (WORKFLOW_DIR / name).open(encoding="utf-8") as workflow_file:
        return yaml.load(workflow_file, Loader=yaml.BaseLoader)


def workflow_triggers(workflow: dict) -> dict:
    return workflow.get("on", {})


def test_required_pr_ci_workflows_run_on_pull_requests_without_target_event():
    required_workflows = {
        "ci.yml": {"lint", "cpp_tests", "build_and_test"},
        "examples-smoke.yml": {"examples-core", "examples-duckdb"},
        "compat-matrix.yml": {"compat"},
        "pr-guard.yml": {"guard-sensitive-paths"},
    }

    for workflow_name, expected_jobs in required_workflows.items():
        workflow = load_workflow(workflow_name)
        triggers = workflow_triggers(workflow)

        assert "pull_request" in triggers, f"{workflow_name} must run on PRs"
        assert (
            "pull_request_target" not in triggers
        ), f"{workflow_name} must not run untrusted PR code via pull_request_target"

        actual_jobs = set(workflow.get("jobs", {}))
        assert expected_jobs <= actual_jobs


def test_pr_ci_workflows_use_read_only_contents_permissions():
    for workflow_name in (
        "ci.yml",
        "examples-smoke.yml",
        "compat-matrix.yml",
        "pr-guard.yml",
    ):
        workflow = load_workflow(workflow_name)

        assert workflow.get("permissions", {}).get("contents") == "read"


def test_ci_visibility_policy_is_documented_for_contributors_and_maintainers():
    policy_doc = PROJECT_ROOT / ".github" / "CI_VISIBILITY.md"
    contributor_doc = PROJECT_ROOT / ".github" / "CONTRIBUTING.md"
    maintainer_doc = PROJECT_ROOT / "MAINTAINERS.md"
    pr_template = PROJECT_ROOT / ".github" / "PULL_REQUEST_TEMPLATE.md"

    assert policy_doc.exists()

    policy_text = policy_doc.read_text(encoding="utf-8")
    for required_text in (
        "first-time contributor",
        "maintainer approval",
        "pull_request_target",
        "Do not merge",
        "Vercel",
        "CI",
        "Examples Smoke",
        "Compatibility Matrix",
        "PR Guard",
    ):
        assert required_text in policy_text

    assert "CI visibility" in contributor_doc.read_text(encoding="utf-8")
    assert "CI visibility" in maintainer_doc.read_text(encoding="utf-8")
    assert "Arnio CI signal" in pr_template.read_text(encoding="utf-8")
