---
description: "The methods.lock file records exact resolved versions, integrity hashes, and semantic fingerprints for verifiable MTHDS installs."
---

# The Lock File

The `methods.lock` file records the exact resolved versions, integrity hashes, and semantic fingerprints for all remote dependencies. It makes installs verifiable — every developer and CI system can prove it fetched the same bytes, carrying the same meaning, that the original resolution saw.

## What It Looks Like

```toml
["github.com/mthds/document-processing"]
version     = "1.2.3"
hash        = "sha256:a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2"
fingerprint = "7c9e2b4f8a1d3e5c7b9f2a4d6e8c1b3f5a7d9e2c4b6f8a1d3e5c7b9f2a4d6e8c"
source      = "https://github.com/mthds/document-processing.git"
commit      = "8f5b2c1a9d3e7f4b6a8c2e5d1f9b3a7c4e6d8f2b"

["github.com/mthds/scoring-lib"]
version     = "0.5.1"
hash        = "sha256:e5f6a7b8c9d0e5f6a7b8c9d0e5f6a7b8c9d0e5f6a7b8c9d0e5f6a7b8c9d0e5f6"
fingerprint = "2d4f6a8c1e3b5d7f9a2c4e6b8d1f3a5c7e9b2d4f6a8c1e3b5d7f9a2c4e6b8d1f"
source      = "https://github.com/mthds/scoring-lib.git"
commit      = "3a7c4e6d8f2b8f5b2c1a9d3e7f4b6a8c2e5d1f9b"
```

Each entry records a package address, the exact resolved version, a SHA-256 integrity hash of the fetched bytes, the semantic fingerprint of what those bytes mean, the HTTPS clone URL, and the commit the version tag pointed to when it was locked.

## Why the Lock Is Regenerable

Version resolution is [Minimum Version Selection](version-resolution.md): the resolved versions are fully determined by the manifests, with no dependency on when you resolve or what was published in the meantime. The lock file can therefore always be regenerated from the manifests plus the fetched sources, and regeneration reproduces the same entries. It is a verification record — proof of what was fetched and what it meant — not the thing that decides versions. (`go.sum` plays the same role next to `go.mod`.)

## File Location

The lock file must be named `methods.lock` and placed at the package root, alongside `METHODS.toml`. It should be committed to version control.

## Locked Package Fields

| Field | Description |
|-------|-------------|
| `version` | The exact resolved version (valid semver). |
| `hash` | SHA-256 integrity **byte hash** of the fetched package directory (`sha256:` followed by 64 hex characters) — what was fetched. |
| `fingerprint` | The [library crate fingerprint](../spec/library-crate.md#fingerprint) of the dependency's resolved content (64 lowercase hex characters) — what it means. Stable across reformatting; moves exactly when the dependency's effective type surface, prompts, or entry points change. |
| `source` | The HTTPS clone URL the package was fetched from. Ends with `.git`. |
| `commit` | The commit SHA the resolved version tag pointed to at lock time. A tag can be re-pointed; the commit cannot — it is the provenance record and the honest cache key. |

The byte hash and the fingerprint are two different questions answered side by side: *did I fetch the same bytes?* and *does it still mean the same thing?* A dependency update whose fingerprint is unchanged changed nothing a consumer can observe; one whose fingerprint moved can be shown as a semantic diff before you adopt it.

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

The lock file is regenerated whenever the manifests change or a tool re-locks:

- `mthds package lock` — resolves all dependencies from the manifests and writes the lock file.
- `mthds package add` — records the new dependency's latest version as its floor in `METHODS.toml`, then re-locks.
- `mthds package update` — raises the floors in `METHODS.toml` to the latest available versions, then re-locks, showing what moved. Under MVS nothing moves without a manifest edit — updating is a deliberate gesture, not a side effect of installing.

## Verification

When installing from a lock file, the tool:

1. Locates the fetched or cached package directory for each entry.
2. Recomputes the SHA-256 byte hash using the algorithm above.
3. Compares the computed hash with the lock file's `hash` field.
4. Rejects the installation if any hash does not match — a hard failure, never a warning.

## Deterministic Output

Lock file entries are sorted by package address (lexicographic ascending) to produce clean version control diffs.

## See Also

- [Specification: methods.lock Format](../spec/lock-format.md) — normative reference.
- [Specification: Library Crate Format](../spec/library-crate.md) — the resolution artifact whose fingerprint the lock records.
- [Distribution](distribution.md) — how packages are fetched and cached.
- [Version Resolution](version-resolution.md) — how versions are selected.
