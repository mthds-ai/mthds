# The Lock File

The `methods.lock` file records the exact resolved versions and integrity hashes for all remote dependencies. It enables reproducible builds — every developer and CI system gets the same dependency versions.

## What It Looks Like

```toml
["github.com/mthds/document-processing"]
version = "1.2.3"
hash    = "sha256:a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2"
source  = "https://github.com/mthds/document-processing"

["github.com/mthds/scoring-lib"]
version = "0.5.1"
hash    = "sha256:e5f6a7b8c9d0e5f6a7b8c9d0e5f6a7b8c9d0e5f6a7b8c9d0e5f6a7b8c9d0e5f6"
source  = "https://github.com/mthds/scoring-lib"
```

Each entry records a package address, the exact resolved version, a SHA-256 integrity hash, and the HTTPS source URL.

## File Location

The lock file must be named `methods.lock` and placed at the package root, alongside `METHODS.toml`. It should be committed to version control.

## Locked Package Fields

| Field | Description |
|-------|-------------|
| `version` | The exact resolved version (valid semver). |
| `hash` | SHA-256 integrity hash of the package contents (`sha256:` followed by 64 hex characters). |
| `source` | The HTTPS URL from which the package was fetched. |

## Which Packages Are Locked

- **Remote dependencies** (those without a `path` field) are locked, including all transitive remote dependencies.
- **Local path dependencies** are NOT locked. They are resolved from the filesystem at load time and are expected to change during development.

## How the Hash Is Computed

The integrity hash is a deterministic SHA-256 hash of the package directory:

1. Collect all regular files recursively under the package directory.
2. Exclude any path containing `.git` in its components.
3. Sort files by their POSIX-normalized relative path (for cross-platform determinism).
4. For each file in sorted order, feed into the hasher:
    - The relative path string, encoded as UTF-8.
    - The raw file bytes.
5. Format as `sha256:` followed by the 64-character lowercase hex digest.

## When the Lock File Updates

The lock file is regenerated when:

- `mthds pkg lock` is run — resolves all dependencies and writes the lock file.
- `mthds pkg update` is run — re-resolves to latest compatible versions and rewrites the lock file.
- `mthds pkg add` is run — adds a new dependency and may trigger re-resolution.

## Verification

When installing from a lock file (`mthds pkg install`), the runtime:

1. Locates the cached package directory for each entry.
2. Recomputes the SHA-256 hash using the algorithm above.
3. Compares the computed hash with the lock file's `hash` field.
4. Rejects the installation if any hash does not match.

## Deterministic Output

Lock file entries are sorted by package address (lexicographic ascending) to produce clean version control diffs.

## See Also

- [Specification: methods.lock Format](../spec/lock-format.md) — normative reference.
- [Distribution](distribution.md) — how packages are fetched and cached.
- [Version Resolution](version-resolution.md) — how versions are selected.
