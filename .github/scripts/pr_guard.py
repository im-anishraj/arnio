import json
import os
import subprocess
import sys

pr_labels_env = os.environ.get("PR_LABELS", "[]")
try:
    pr_labels = json.loads(pr_labels_env)
except Exception:
    pr_labels = []

is_ci_packaging = "area:ci-packaging" in pr_labels

base_ref = os.environ.get("GITHUB_BASE_REF", "main")
try:
    # Get the list of all files changed in this PR compared to the base branch,
    # including deletions so removed workflow files are also guarded.
    cmd = ["git", "diff", "--name-only", f"origin/{base_ref}...HEAD"]
    output = subprocess.check_output(cmd, text=True)
except subprocess.CalledProcessError as e:
    print(f"Failed to run git diff: {e}")
    sys.exit(1)

changed_files = [line.strip() for line in output.splitlines() if line.strip()]

# Get list of added files specifically to check for new stray root files
try:
    added_cmd = [
        "git",
        "diff",
        "--name-only",
        "--diff-filter=A",
        f"origin/{base_ref}...HEAD",
    ]
    added_output = subprocess.check_output(added_cmd, text=True)
except subprocess.CalledProcessError:
    added_output = ""

added_files = [line.strip() for line in added_output.splitlines() if line.strip()]

errors = []

# Rule 1: Guard .github/workflows/
if not is_ci_packaging:
    for file in changed_files:
        if file.startswith(".github/workflows/"):
            errors.append(
                f'[SECURITY RISK] Modified workflow file "{file}". This requires explicit maintainer review.'
            )
else:
    print(
        "[INFO] Bypassing workflow modification guard because `area:ci-packaging` label is present."
    )

# Rule 2: Guard against stray root-level files
# Allowed root file extensions and exact names for new additions
allowed_root_exts = {
    ".md",
    ".txt",
    ".toml",
    ".ini",
    ".yml",
    ".yaml",
    ".svg",
    ".png",
    ".jpg",
}
allowed_root_names = {
    "Makefile",
    "LICENSE",
    "setup.py",
    ".gitignore",
    ".clang-format",
    ".pre-commit-config.yaml",
}

for file in added_files:
    dirname = os.path.dirname(file)
    basename = os.path.basename(file)

    if dirname == "":  # It is a root file
        ext = os.path.splitext(basename)[1].lower()
        if ext not in allowed_root_exts and basename not in allowed_root_names:
            errors.append(
                f'[STRAY FILE DETECTED] Added unrecognized root-level file "{file}". If this is intentional, please request maintainer review and ask for the root-file allowlist in .github/scripts/pr_guard.py to be updated as part of this PR. Otherwise, please remove it.'
            )

if errors:
    print("[PR GUARD FAILED]\n")
    for err in errors:
        print(err)
    print(
        "\nIf you are a contributor, please revert these files or keep your PR strictly scoped to your issue."
    )
    sys.exit(1)
else:
    print(
        "[PASS] PR Guard passed. No sensitive workflow modifications or stray root files detected."
    )
