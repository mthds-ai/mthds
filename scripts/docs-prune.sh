#!/usr/bin/env bash
# Delete documentation versions listed in versions-to-delete.txt from local gh-pages.
# Skips versions that don't exist. Does NOT push — CI handles that.
set -euo pipefail

PRUNE_FILE="${1:?Usage: docs-prune.sh <versions-to-delete.txt> <mike-binary>}"
MIKE="${2:?Usage: docs-prune.sh <versions-to-delete.txt> <mike-binary>}"

if [ ! -f "$PRUNE_FILE" ]; then
    echo "No prune file found at $PRUNE_FILE — nothing to do."
    exit 0
fi

# Read existing versions once
EXISTING=$("$MIKE" list 2>/dev/null || true)

PRUNED=0
while IFS= read -r version || [ -n "$version" ]; do
    # Skip empty lines and comments
    version=$(echo "$version" | xargs)
    [[ -z "$version" || "$version" == \#* ]] && continue

    if echo "$EXISTING" | grep -q "^${version}\b"; then
        echo "Deleting version: $version"
        "$MIKE" delete "$version"
        PRUNED=$((PRUNED + 1))
    else
        echo "Skipping $version (not found in gh-pages)"
    fi
done < "$PRUNE_FILE"

if [ "$PRUNED" -gt 0 ]; then
    echo "Pruned $PRUNED version(s) from gh-pages."
else
    echo "No versions to prune."
fi
