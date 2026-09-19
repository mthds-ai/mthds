#!/usr/bin/env bash
# Print what the next deploy would keep and what it would retire. Changes nothing.
#
# Reads the published set from the remote branch rather than through mike, so that asking
# the question never creates a local gh-pages ref and never touches the working tree —
# this is meant to be run while deciding, including from a release worktree.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
KEEP="${1:?Usage: docs-retention-plan.sh <version> [branch]}"
BRANCH="${2:-gh-pages}"

if ! git fetch --quiet origin "$BRANCH" 2>/dev/null; then
    echo "Could not fetch origin/$BRANCH — reading what this checkout already has." >&2
fi

if ! git rev-parse --verify --quiet "refs/remotes/origin/$BRANCH" >/dev/null; then
    echo "Nothing is published yet — there is no origin/$BRANCH."
    exit 0
fi

# A branch with no versions.json is a store that exists but holds nothing.
LISTING=$(git show "origin/$BRANCH:versions.json" 2>/dev/null || echo '[]')
# The directories too, because the deploy removes the ones the index does not name, and a
# checkpoint that omits them cannot be answered for what it does not print.
DIRECTORIES=$(git ls-tree -d --name-only "origin/$BRANCH" 2>/dev/null || true)

python3 "$HERE/docs_retention.py" "$KEEP" --directories "$DIRECTORIES" --explain <<<"$LISTING"
