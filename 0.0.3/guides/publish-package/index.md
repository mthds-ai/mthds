# Publish a Package

This guide walks you through preparing a package for distribution and creating a version tag.

## Prerequisites

Before publishing:

- Your package has a `METHODS.toml` with a valid `address` and `version`.
- All `.mthds` files parse without error.
- If you have remote dependencies, a `methods.lock` file exists and is up to date.
- Your git working directory is clean (all changes committed).

## Step 1: Validate for Publishing

Run the publish validation:

```bash
mthds pkg publish
```

This runs 15 checks across seven categories (manifest, bundles, exports, visibility, dependencies, lock file, git). The output shows errors and warnings:

```
┌──────────────────────────────────────────────────────────┐
│ Errors                                                    │
├──────────┬─────────────────────────────┬─────────────────┤
│ Category │ Message                     │ Suggestion      │
├──────────┼─────────────────────────────┼─────────────────┤
│ export   │ Exported pipe 'old_pipe'    │ Remove from     │
│          │ in domain 'legal' not found │ [exports.legal] │
│          │ in bundles                  │ or add it       │
└──────────┴─────────────────────────────┴─────────────────┘

1 error(s), 0 warning(s)
Package is NOT ready for distribution.
```

Fix all errors before proceeding. Warnings are advisory — they flag things like missing `authors` or `license` fields, which are recommended but not required.

## Step 2: Fix Issues

Common issues and how to fix them:

| Issue | Fix |
|-------|-----|
| Exported pipe not found in bundles | Remove the pipe from `[exports]` or add it to a `.mthds` file. |
| Lock file missing | Run `mthds pkg lock`. |
| Git working directory has uncommitted changes | Commit or stash changes. |
| Git tag already exists | Bump the `version` in `METHODS.toml`. |
| Wildcard version on dependency | Pin to a specific constraint (e.g., `^1.0.0`). |

## Step 3: Create a Version Tag

Once all checks pass, create a git tag:

```bash
mthds pkg publish --tag
```

This validates the package and, on success, creates a local git tag `v{version}` (e.g., `v0.3.0`).

## Step 4: Push

Push your code and the tag to make the package available:

```bash
git push origin main
git push origin v0.3.0
```

Other packages can now depend on yours using the address and version:

```toml
[dependencies]
legal = { address = "github.com/yourorg/legal-tools", version = "^0.3.0" }
```

## Version Bumping

When you make changes and want to publish a new version:

1. Update the `version` field in `METHODS.toml`.
2. Update `methods.lock` if dependencies changed (`mthds pkg lock`).
3. Commit all changes.
4. Run `mthds pkg publish --tag`.
5. Push code and tag.

Follow [Semantic Versioning](https://semver.org/): increment the major version for breaking changes, minor for new features, and patch for fixes.

## See Also

- [The Manifest](../packages/manifest.md) — `address` and `version` field requirements.
- [The Lock File](../packages/lock-file.md) — what gets locked and when.
- [Distribution](../packages/distribution.md) — how packages are fetched by consumers.
- [Registry Distribution Protocol](../packages/registry-distribution.md) — how to notify registries after publishing.
