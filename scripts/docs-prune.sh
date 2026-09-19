#!/usr/bin/env bash
# Prune the documentation versions the site no longer serves.
#
# What is retained is scripts/docs_retention.py's to decide — the version being deployed,
# the release before it, and whatever pyproject.toml pins. Every other version on the
# local gh-pages branch is deleted here, and so is every directory mike's versions.json
# no longer names, so that the branch holds exactly what the site publishes.
#
# Does NOT push — CI pushes gh-pages only after the Vercel deploy succeeds.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MIKE="${1:?Usage: docs-prune.sh <mike-binary> <deploying-version> [branch]}"
KEEP="${2:?Usage: docs-prune.sh <mike-binary> <deploying-version> [branch]}"
BRANCH="${3:-gh-pages}"

# A missing branch is not an error to mike — it reports no versions and exits 0 — so a
# failure here is mike itself failing: the binary absent, the mkdocs config unreadable,
# versions.json corrupt. Pruning is what holds the site under its deploy limit, so that
# must stop the deploy rather than pass for a quiet no-op, which is the very shape of
# the bug this script replaced. Only stdout is captured, because mike writes its
# warnings to stderr and folding those in would hand the JSON reader something that is
# not JSON.
list_versions() {
    if ! "$MIKE" list --json --branch "$BRANCH"; then
        echo "ERROR: mike list failed on $BRANCH — refusing to deploy unpruned." >&2
        exit 1
    fi
}

LISTING=$(list_versions)

# Decided before the branch is checked, so that a version number nobody can read — a
# blank one, an alias name — is refused even on a first-ever deploy, where there is
# nothing to prune but there is still something about to be published.
if ! DOOMED=$(python3 "$HERE/docs_retention.py" "$KEEP" <<<"$LISTING"); then
    echo "ERROR: could not decide what to retain — refusing to prune." >&2
    exit 1
fi

# mike resolves the local branch from its remote-tracking ref on any command, so from
# here on the local branch exists whenever the site has ever been published — but on a
# first-ever deploy there is nothing to resolve and nothing to prune.
if ! git rev-parse --verify --quiet "refs/heads/$BRANCH" >/dev/null; then
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

# mike only ever deletes what versions.json names, so a directory left behind by an
# earlier deploy style outlives every prune. Sweep those separately, against the index
# as the delete left it, so that what survives here is exactly what the site publishes.
LISTING=$(list_versions)
PUBLISHED=$(python3 -c '
import json, sys
for v in json.load(sys.stdin):
    print(v["version"])
    for alias in v["aliases"]:
        print(alias)
' <<<"$LISTING")
# KEEP joins them because on a release it is not deployed yet — mike adds it next.
PUBLISHED=$(printf '%s\n%s\n' "$PUBLISHED" "$KEEP" | sed '/^$/d' | sort -u)

# Only version-shaped directories are candidates. Every directory on this branch is
# mike's, so in principle anything unnamed is stale — but this deletes from the
# published site unattended, and a directory arriving here by some route nobody has
# thought of yet should survive to be looked at rather than vanish on the next deploy.
TRACKED=$(git ls-tree -d --name-only "$BRANCH" | grep -E '^[0-9]+\.[0-9]+\.[0-9]+([-+][0-9A-Za-z.-]+)?$' | sort || true)
ORPHANS=$(comm -23 <(printf '%s\n' "$TRACKED") <(printf '%s\n' "$PUBLISHED"))

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

echo "Retained: $(echo "$PUBLISHED" | tr '\n' ' ')"
