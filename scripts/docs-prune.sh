#!/usr/bin/env bash
# Prune the documentation versions and directories the site no longer serves.
#
# This script decides nothing. It reads the branch — mike's index and the directories that
# are actually there — hands both to scripts/docs_retention.py, and carries out what comes
# back, so that a version and its directory can never be judged by two different rules.
#
# Does NOT push — CI pushes gh-pages only after the Vercel deploy succeeds.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MIKE="${1:?Usage: docs-prune.sh <mike-binary> <deploying-version> [branch]}"
KEEP="${2:?Usage: docs-prune.sh <mike-binary> <deploying-version> [branch]}"
BRANCH="${3:-gh-pages}"

# A missing branch is not an error to mike — it reports no versions and exits 0 — so a
# failure here is mike itself failing: the binary absent, the mkdocs config unreadable,
# versions.json corrupt, which raises out of mike rather than being swallowed. Pruning is
# what holds the site under its deploy limit, so that must stop the deploy rather than pass
# for a quiet no-op, which is the very shape of the bug this script replaced. Only stdout is
# captured, because mike writes its warnings to stderr and folding those in would hand the
# JSON reader something that is not JSON.
list_versions() {
    if ! "$MIKE" list --json --branch "$BRANCH"; then
        echo "ERROR: mike list failed on $BRANCH — refusing to deploy unpruned." >&2
        exit 1
    fi
}

branch_exists() {
    git rev-parse --verify --quiet "refs/heads/$BRANCH" >/dev/null
}

tracked_dirs() {
    if branch_exists; then
        git ls-tree -d --name-only "$BRANCH"
    fi
}

# Every question is the same question, asked of the branch as it stands right now.
retention() {
    python3 "$HERE/docs_retention.py" "$KEEP" --directories "$(tracked_dirs)" "$@" <<<"$LISTING"
}

LISTING=$(list_versions)

# Asked before the branch is checked, so that a version number nobody can read — a blank
# one, an alias name — is refused even on a first-ever deploy, where there is nothing to
# prune but there is still something about to be published.
if ! DOOMED=$(retention); then
    echo "ERROR: could not decide what to retain — refusing to prune." >&2
    exit 1
fi

# mike resolves the local branch from its remote-tracking ref on any command, so from here
# on the local branch exists whenever the site has ever been published — but on a
# first-ever deploy there is nothing to resolve and nothing to prune.
if ! branch_exists; then
    echo "No $BRANCH branch yet — nothing to prune."
    exit 0
fi

if [ -n "$DOOMED" ]; then
    echo "Retiring versions: $(echo "$DOOMED" | tr '\n' ' ')"
    # One mike call, so the deletions and the rewritten versions.json are one commit.
    # shellcheck disable=SC2086
    "$MIKE" delete --branch "$BRANCH" $DOOMED
else
    echo "Every published version is retained — nothing to delete."
fi

# mike only ever deletes what versions.json names, so a directory left behind by an earlier
# deploy style, or restored by hand after mike removed it, outlives every prune. Sweep those
# separately and against the branch as the delete left it, so that what survives here is
# exactly what the site publishes — and ask the same script, so that a directory a pin names
# is spared rather than deleted in the same run that reported the pin.
LISTING=$(list_versions)
if ! ORPHANS=$(retention --orphans); then
    echo "ERROR: could not decide what to sweep — refusing to sweep." >&2
    exit 1
fi

if [ -n "$ORPHANS" ]; then
    echo "Removing directories no longer named by versions.json: $(echo "$ORPHANS" | tr '\n' ' ')"
    SWEEP=$(mktemp -d)
    trap 'git worktree remove --force "$SWEEP" 2>/dev/null || true; rm -rf "$SWEEP"' EXIT
    git worktree add --quiet "$SWEEP" "$BRANCH"
    (
        cd "$SWEEP"
        # shellcheck disable=SC2086
        git rm -r --quiet -- $ORPHANS
        git commit --quiet -m "Removed directories not named by versions.json"
    )
else
    echo "No untracked version directories on $BRANCH."
fi

# Read off the branch rather than predicted, so this line states what is there.
echo "Retained: $(git ls-tree -d --name-only "$BRANCH" | tr '\n' ' ')"
