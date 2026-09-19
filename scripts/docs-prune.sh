#!/usr/bin/env bash
# Retain only the documentation version being deployed.
#
# The specification site serves one version of the standard: the current one, under
# its own number and under the `latest` alias mike copies from it. Every other version
# on the local gh-pages branch is deleted here, and so is every directory mike's
# versions.json no longer names, so that the branch holds exactly what it publishes.
#
# Does NOT push — CI pushes gh-pages only after the Vercel deploy succeeds.
set -euo pipefail

MIKE="${1:?Usage: docs-prune.sh <mike-binary> <keep-version> [branch]}"
KEEP="${2:?Usage: docs-prune.sh <mike-binary> <keep-version> [branch]}"
BRANCH="${3:-gh-pages}"

# A blank or malformed version would mean deleting everything and publishing nothing,
# so refuse rather than prune on a value we cannot read.
if ! [[ "$KEEP" =~ ^[0-9]+\.[0-9]+\.[0-9]+([-+][0-9A-Za-z.-]+)?$ ]]; then
    echo "ERROR: refusing to prune — '$KEEP' is not a version number." >&2
    exit 1
fi

# Only stdout is captured: mike writes its warnings to stderr, and folding those into
# the capture would hand the JSON reader something that is not JSON.
if ! LISTING=$("$MIKE" list --json --branch "$BRANCH"); then
    echo "mike list failed — nothing to prune."
    exit 0
fi

# mike resolves the local branch from its remote-tracking ref on any command, so from
# here on the local branch exists whenever the site has ever been published — but on a
# first-ever deploy there is nothing to resolve and nothing to prune.
if ! git rev-parse --verify --quiet "refs/heads/$BRANCH" >/dev/null; then
    echo "No $BRANCH branch yet — nothing to prune."
    exit 0
fi

read_listing() {
    KEEP="$KEEP" python3 -c "$1" <<<"$LISTING"
}

DOOMED=$(read_listing '
import json, os, sys
keep = os.environ["KEEP"]
print("\n".join(v["version"] for v in json.load(sys.stdin) if v["version"] != keep))
')

if [ -n "$DOOMED" ]; then
    echo "Deleting versions: $(echo "$DOOMED" | tr '\n' ' ')"
    # One mike call, so the deletions and the rewritten versions.json are one commit.
    # shellcheck disable=SC2086
    "$MIKE" delete --branch "$BRANCH" $DOOMED
else
    echo "No version other than $KEEP is deployed — nothing to delete."
fi

# mike only ever deletes what versions.json names, so a directory left behind by an
# earlier deploy style outlives every prune. Sweep those separately, against the index
# as the delete left it, so that what survives here is exactly what the site publishes.
LISTING=$("$MIKE" list --json --branch "$BRANCH")
PUBLISHED=$(read_listing '
import json, sys
for v in json.load(sys.stdin):
    print(v["version"])
    for alias in v["aliases"]:
        print(alias)
')
# KEEP joins them because on a release it is not deployed yet — mike adds it next.
PUBLISHED=$(printf '%s\n%s\n' "$PUBLISHED" "$KEEP" | sed '/^$/d' | sort -u)

TRACKED=$(git ls-tree -d --name-only "$BRANCH" | sort)
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

echo "Retained: $KEEP"
