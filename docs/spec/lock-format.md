---
description: "Formal specification of the methods.lock file format — resolved versions, integrity hashes, semantic fingerprints, and install-time verification."
---

# methods.lock Format

The `methods.lock` file records, for every remote dependency of a package, the exact resolved version, an integrity hash of what was fetched, the semantic fingerprint of what it means, and the provenance of where it came from. It is auto-generated and SHOULD be committed to version control.

!!! note "Implementation status"
    The lock file is committed design. This section is the contract implementations are brought into conformance with — the same forward-contract convention the [Library Crate Format](./library-crate.md#specification-status) uses for its unrealized sections. Conformance is asserted against this document as each piece lands.

## A Verification Record, Not a Resolution Record

Because version resolution is [Minimum Version Selection](./namespace-resolution.md#version-resolution-strategy), the build list is fully determined by the manifests and the published version tags — no resolution-time state and no registry oracle enters it: the lock file can be regenerated at any time from the manifests plus the fetched sources, and regeneration reproduces the same entries as long as the published tag set has not changed. The lock is therefore a **verification record** — it exists so that a later install can prove it fetched the same bytes and the same meaning the original resolution saw — not a resolution record that a resolver consults to decide versions. This is the same relationship `go.sum` has to `go.mod`.

## File Name and Location

The lock file MUST be named `methods.lock` and MUST be located at the root of the package directory, alongside `METHODS.toml`.

## File Encoding and Syntax

`methods.lock` MUST be a valid TOML document encoded in UTF-8.

## Structure

The lock file is a flat TOML document where each top-level table key is a package address, and the value is a table containing the locked metadata for that package.

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

Because package addresses contain dots and slashes, they MUST be quoted as TOML keys.

## Locked Package Fields

Each entry in the lock file contains:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `version` | string | Yes | The exact resolved version. MUST be valid semver. |
| `hash` | string | Yes | Integrity **byte hash** of the fetched package directory. MUST match the pattern `sha256:[0-9a-f]{64}`. Records *what was fetched*. |
| `fingerprint` | string | Yes | The **semantic fingerprint** of the dependency's resolved content — the [library crate fingerprint](./library-crate.md#fingerprint) of the library the dependency's package resolves into, as a 64-character lowercase hex digest. Records *what it means*. |
| `source` | string | Yes | The HTTPS clone URL the package was fetched from, derived from the address (see [Fetching Remote Dependencies](./namespace-resolution.md#fetching-remote-dependencies)). MUST start with `https://` and MUST end with `.git`. |
| `commit` | string | Yes | The commit SHA the resolved version tag pointed to at lock time, as a 40-character lowercase hex digest. Provenance: a tag can be re-pointed; the commit cannot. It is also the honest cache key for tooling that caches clones. |

The `hash` and the `fingerprint` are two deliberately distinct digests joined per dependency at this one point. The byte hash is transport integrity: it changes when any fetched byte changes, including formatting and comments. The fingerprint is semantic identity: it is stable across reformatting and changes exactly when the dependency's effective type surface, prompts, or entry points change. Together they let tooling verify a fetch and explain an update — a version bump whose fingerprint is unchanged changed nothing a consumer can observe; one whose fingerprint moved can be diffed semantically.

## Hash Computation

The integrity hash is a deterministic SHA-256 hash of the package directory contents, computed as follows:

1. Collect all regular files recursively under the package directory.
2. Exclude any path containing `.git` in its components.
3. Sort files by their POSIX-normalized relative path (for cross-platform determinism).
4. For each file in sorted order, feed into the hasher:
   a. The relative path string, encoded as UTF-8.
   b. The raw file bytes.
5. The resulting hash is formatted as `sha256:` followed by the 64-character lowercase hex digest.

## Fingerprint Computation

The `fingerprint` is the [library crate fingerprint](./library-crate.md#fingerprint) of the dependency's resolved content: the dependency package is resolved into a library on its own (its bundles as the host, its own dependencies folded in per that specification), normalized, and fingerprinted per the crate specification's canonicalization rules. It is recomputable by any consumer from the fetched source — no registry or third party has to be trusted to have computed it honestly.

## Which Packages Are Locked

- **Remote dependencies** (those without a `path` field in the root manifest) are locked, including all transitive remote dependencies.
- **Local path dependencies** are NOT locked. They are resolved from the filesystem at load time and are expected to change during development.

## When the Lock File Updates

The lock file is regenerated when the manifests change or when a tool re-locks:

- **`lock`** — resolves all dependencies from the manifests and writes the lock file. Because resolution is deterministic, re-running `lock` against unchanged manifests and an unchanged published tag set reproduces the same file.
- **`add`** — records the added dependency's latest version as its floor in `METHODS.toml`, then re-locks.
- **`update`** — raises the floors in `METHODS.toml` to the latest available versions, then re-locks. Under MVS, re-resolution alone never moves a version: updating is a deliberate manifest edit, and the re-lock records its result. See [Version Resolution Strategy](./namespace-resolution.md#version-resolution-strategy).

## Verification

When installing from a lock file, a compliant implementation MUST:

1. For each entry in the lock file, locate the corresponding fetched or cached package directory.
2. Recompute the SHA-256 byte hash of that directory using the algorithm described above.
3. Compare the computed hash with the `hash` field in the lock file.
4. Reject the installation if any hash does not match (integrity failure). A mismatch is a hard failure, never a warning.

An implementation SHOULD additionally recompute the `fingerprint` and report a mismatch: a byte hash that matches while the fingerprint does not indicates a defect in one of the implementations, since the fingerprint is a pure function of the fetched content.

## Deterministic Output

Lock file entries MUST be sorted by package address (lexicographic ascending) to produce deterministic output suitable for clean version control diffs.

An empty lock file (no remote dependencies) MAY be an empty file or absent entirely.
