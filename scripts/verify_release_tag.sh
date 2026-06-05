#!/usr/bin/env bash
#
# verify_release_tag.sh — verify a release tag before building/publishing.
#
# Format validation alone is not enough: a branch (or any other ref) named
# "v1.2.3" would satisfy the regex and could be checked out and published.
# This script therefore requires the value to resolve specifically to an
# existing Git tag under refs/tags/, then freezes it to the immutable commit
# SHA so every downstream job builds and publishes exactly that commit.
#
# Usage:
#   verify_release_tag.sh <tag_name>
#
# On success it prints two "key=value" lines (tag_name, tag_sha) suitable for
# appending to $GITHUB_OUTPUT, and exits 0. On any failure it prints an error
# and exits non-zero.
#
set -euo pipefail

TAG_NAME="${1:-}"

# 1. Require a value.
if [ -z "${TAG_NAME}" ]; then
  echo "::error::No release tag provided. This is a publish workflow and requires an explicit tag (e.g. v1.2.3)." >&2
  exit 1
fi

# 2. Validate format (vX.Y.Z, optional pre-release suffix like v1.2.3-rc1).
if ! printf '%s' "${TAG_NAME}" | grep -E -q '^v[0-9]+\.[0-9]+\.[0-9]+(-[0-9A-Za-z.-]+)?$'; then
  echo "::error::Invalid release tag '${TAG_NAME}'. Expected the vX.Y.Z convention (e.g. v1.2.3 or v1.2.3-rc1)." >&2
  exit 1
fi

# 3. Make sure tags are present locally. This is a no-op offline or without an
#    'origin' remote (e.g. in unit tests), so failures here are non-fatal.
git fetch origin --force --tags --quiet >/dev/null 2>&1 || true

# 4. Verify the value resolves specifically to a tag under refs/tags/, NOT a
#    branch or arbitrary ref that merely happens to be named like a tag.
if ! git rev-parse --verify --quiet "refs/tags/${TAG_NAME}" >/dev/null; then
  echo "::error::Tag not found: refs/tags/${TAG_NAME}. A branch or other ref with a tag-shaped name is not accepted; create the release tag first." >&2
  exit 1
fi

# 5. Resolve the tag to its immutable commit SHA (peels annotated tags).
TAG_SHA="$(git rev-parse --verify "refs/tags/${TAG_NAME}^{commit}")"

echo "tag_name=${TAG_NAME}"
echo "tag_sha=${TAG_SHA}"

# Human-readable confirmation on stderr so it shows in logs without polluting
# the machine-readable stdout used for $GITHUB_OUTPUT.
echo "Verified release tag '${TAG_NAME}' -> commit ${TAG_SHA}" >&2
