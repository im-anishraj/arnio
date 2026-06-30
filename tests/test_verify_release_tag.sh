#!/usr/bin/env bash
#
# Tests for scripts/verify_release_tag.sh.
#
# Proves the release-tag guard accepts a real existing tag and rejects the
# unsafe cases the maintainer flagged: a missing tag, a branch with a
# tag-shaped name, and an input that is not vX.Y.Z.
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERIFY="${SCRIPT_DIR}/scripts/verify_release_tag.sh"

PASS=0
FAIL=0

# run_case <description> <expect: pass|fail> <tag_name>
run_case() {
  local desc="$1" expect="$2" tag="$3"
  local out rc=0
  out="$(bash "${VERIFY}" "${tag}" 2>/dev/null)" || rc=$?

  if [ "${expect}" = "pass" ] && [ "${rc}" -eq 0 ]; then
    if printf '%s' "${out}" | grep -q '^tag_sha=[0-9a-f]\{7,\}$'; then
      echo "ok   - ${desc} (resolved to commit)"
      PASS=$((PASS + 1))
      return
    fi
    echo "FAIL - ${desc}: passed but no tag_sha output"
    FAIL=$((FAIL + 1))
    return
  fi

  if [ "${expect}" = "fail" ] && [ "${rc}" -ne 0 ]; then
    echo "ok   - ${desc} (rejected)"
    PASS=$((PASS + 1))
    return
  fi

  echo "FAIL - ${desc}: expected ${expect} but rc=${rc}"
  FAIL=$((FAIL + 1))
}

# Build an isolated repo with a single commit; no 'origin' remote so the
# script's `git fetch origin` is a harmless no-op.
WORK="$(mktemp -d)"
trap 'rm -rf "${WORK}"' EXIT
cd "${WORK}"
git init -q
git config user.email test@example.com
git config user.name test
git commit -q --allow-empty -m "initial"

# 1. Existing tag is accepted and resolves to a commit.
git tag v1.2.3
run_case "existing tag v1.2.3 accepted" pass "v1.2.3"

# 5. (covered above) tag resolves to a commit SHA — asserted by run_case.

# 2. Missing tag is rejected.
run_case "missing tag v9.9.9 rejected" fail "v9.9.9"

# 3. Branch named like a tag (no such tag) is rejected — the key concern.
git checkout -q -b v4.5.6
git checkout -q -
run_case "branch v4.5.6 with no tag rejected" fail "v4.5.6"

# 4. Invalid format is rejected.
run_case "non-version 'main' rejected" fail "main"
run_case "empty input rejected" fail ""
run_case "partial version v1.2 rejected" fail "v1.2"

echo "-------------------------------------"
echo "passed: ${PASS}  failed: ${FAIL}"
[ "${FAIL}" -eq 0 ]
