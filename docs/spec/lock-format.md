---
description: "Formal specification of the methods.lock file format — resolved versions, integrity hashes, and reproducible dependency resolution."
---

# methods.lock Format

The `methods.lock` file records the exact resolved versions and integrity hashes for all remote dependencies, enabling reproducible builds. It is auto-generated and SHOULD be committed to version control.

## File Name and Location

The lock file MUST be named `methods.lock` and MUST be located at the root of the package directory, alongside `METHODS.toml`.

## File Encoding and Syntax

`methods.lock` MUST be a valid TOML document encoded in UTF-8.

## Structure

The lock file is a flat TOML document where each top-level table key is a package address, and the value is a table containing the locked metadata for that package.

```toml
["github.com/mthds/document-processing"]
version = "1.2.3"
hash    = "sha256:a1b2c3d4e5f6..."
source  = "https://github.com/mthds/document-processing"

["github.com/mthds/scoring-lib"]
version = "0.5.1"
hash    = "sha256:e5f6a7b8c9d0..."
source  = "https://github.com/mthds/scoring-lib"
```

Because package addresses contain dots and slashes, they MUST be quoted as TOML keys.

## Locked Package Fields

Each entry in the lock file contains:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `version` | string | Yes | The exact resolved version. MUST be valid semver. |
| `hash` | string | Yes | Integrity hash of the package contents. MUST match the pattern `sha256:[0-9a-f]{64}`. |
| `source` | string | Yes | The HTTPS URL from which the package was fetched. MUST start with `https://`. |

## Hash Computation

The integrity hash is a deterministic SHA-256 hash of the package directory contents, computed as follows:

1. Collect all regular files recursively under the package directory.
2. Exclude any path containing `.git` in its components.
3. Sort files by their POSIX-normalized relative path (for cross-platform determinism).
4. For each file in sorted order, feed into the hasher:
   a. The relative path string, encoded as UTF-8.
   b. The raw file bytes.
5. The resulting hash is formatted as `sha256:` followed by the 64-character lowercase hex digest.

## Which Packages Are Locked

- **Remote dependencies** (those without a `path` field in the root manifest) are locked, including all transitive remote dependencies.
- **Local path dependencies** are NOT locked. They are resolved from the filesystem at load time and are expected to change during development.

## When the Lock File Updates

The lock file is regenerated when:

- `mthds pkg lock` is run — resolves all dependencies and writes the lock file.
- `mthds pkg update` is run — re-resolves to latest compatible versions and rewrites the lock file.
- `mthds pkg add` is run — adds a new dependency and may trigger re-resolution.

## Verification

When installing from a lock file (`mthds pkg install`), a compliant implementation MUST:

1. For each entry in the lock file, locate the corresponding cached package directory.
2. Recompute the SHA-256 hash of the cached directory using the algorithm described above.
3. Compare the computed hash with the `hash` field in the lock file.
4. Reject the installation if any hash does not match (integrity failure).

## Deterministic Output

Lock file entries MUST be sorted by package address (lexicographic ascending) to produce deterministic output suitable for clean version control diffs.

An empty lock file (no remote dependencies) MAY be an empty file or absent entirely.
