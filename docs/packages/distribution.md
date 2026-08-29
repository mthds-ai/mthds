---
description: "How MTHDS packages are distributed — Git-federated storage, the address@tag reference grammar, package location by manifest identity, and the two caches."
---

# Distribution

MTHDS packages are distributed using a federated model: decentralized storage with centralized discovery. The repository IS the package — no upload step, no proprietary hosting, no service that must be up for an install to succeed.

## Storage: Git Repositories

Packages live in Git repositories. Authors retain full control, and **publishing is pushing a tag** — nothing else. There is no pack or archive artifact and no registry account on the critical path.

A repository can contain one package at its root, or several packages in subdirectories — a **library repository**. Either way, a specific package is identified by its manifest, never by a directory path (see [Locating a Package Inside a Clone](#locating-a-package-inside-a-clone)).

## The Versioned Reference

One reference grammar names a package everywhere — in tooling, in APIs, and in the lock file:

```
<address>[@<tag>]
```

- The **address** is the package's manifest `address` (see [The Manifest](manifest.md)): hostname/path, e.g. `github.com/acme/legal-tools` or `github.com/mthds/methods/documents`. It is simultaneously the package's identity and its fetch location.
- A **bare address** refers to the repository's default branch at its current HEAD.
- **`@<tag>`** refers to the repository at that Git tag. The recommended tag form is `vX.Y.Z` (e.g. `github.com/acme/legal-tools@v1.2.0`) — the same pinning gesture the [lock file](lock-file.md) formalizes.

## Clone URL Derivation

The first two path segments after the hostname name the repository; the clone URL is derived from them:

```
github.com/acme/legal-tools            → https://github.com/acme/legal-tools.git
github.com/mthds/methods/documents     → https://github.com/mthds/methods.git
```

1. Take the hostname and the first two path segments.
2. Prepend `https://`.
3. Append `.git`.

Any path segments after the first two are not part of the clone URL — they select a package *within* the clone.

!!! note "Open question: hosts with nested repository namespaces"
    The two-segment rule matches hosts whose repositories live at `<host>/<owner>/<repo>` — the layout of every address in this specification. On hosts that allow nested repository namespaces (such as GitLab subgroups), the repository/package boundary inside an address is ambiguous under this rule; how such addresses are partitioned is an open question of the standard, deliberately recorded rather than silently decided. Until it is settled, portable package addresses SHOULD use a `<host>/<owner>/<repo>` repository.

## Locating a Package Inside a Clone

A package is located inside a clone **by manifest identity, not by directory path**. Directory names carry no meaning: a compliant tool scans the clone for `METHODS.toml` files and selects the package whose identity matches the requested address:

- a **repository-root package** matches when its manifest `address` equals the requested address;
- a **package in a library repository** matches when its manifest `address + "/" + name` equals the requested address. For example, a manifest with `address = "github.com/mthds/methods"` and `name = "documents"` is the package `github.com/mthds/methods/documents`, wherever it sits in the repository tree.

If no manifest matches, or more than one does, the tool MUST fail loudly, listing the package identities the clone does contain. It MUST NOT fall back to guessing by directory name.

## Version Tags

Version tags in remote repositories may use a `v` prefix (e.g., `v1.0.0`). The prefix is stripped during version parsing. Both `v1.0.0` and `1.0.0` are recognized.

Tags are listed using `git ls-remote --tags`, and only those that parse as valid semantic versions are considered. Fetching a resolved version clones at its tag: `git clone --depth 1 --branch {tag}`.

!!! note "Open question: version tags in a library repository"
    Git tags are repository-wide, while each package in a library repository carries its own manifest `version`. How repository tags map to per-package versions — per-package tag prefixes are the anticipated direction — is an open question of the standard, deliberately recorded rather than silently decided. Until it is settled, packages that need independently versioned releases SHOULD live in their own repositories, and a library repository SHOULD version its packages in lockstep.

A tag can be re-pointed; the commit it resolved to cannot. Tools therefore record the **resolved commit SHA** of every fetch — it is the provenance entry in the [lock file](lock-file.md) and the honest key for any clone cache. Every fetched-package operation SHOULD be attributable to its `(address, tag, commit)` triple.

## The Two Caches

Two caches with two distinct jobs stand between a remote repository and a running method:

- The **global VCS cache**, `~/.mthds/packages/{address}/{version}/`, holds fetched package sources, shared across projects. Entries are written atomically (staging directory, then rename), the `.git` directory is removed, and each entry records the commit SHA it was fetched at.
- The **project-local method cache**, `.mthds/methods/<name>/` inside the consuming project, is what [closure assembly](../spec/library-crate.md#closure-assembly) reads. It is deterministic by construction: resolution reads only from disk.

**Install is the bridge.** Installing a package's dependencies walks the [lock file](lock-file.md), fetches anything missing into the global cache (verifying the byte hash against the lock — a mismatch is a hard failure), and materializes each locked dependency into the project-local cache. After install, resolving and running the method touches no network.

## Fetched Content and Runtime Policy

A fetched package directory may contain files beyond `.mthds` bundles — documentation, assets, or implementation-specific code. What a runtime *executes* from fetched content is runtime policy, not standard semantics: a runtime MAY refuse fetched executable content, or classes of it, according to its own security model, and SHOULD say so with an error that names the rule rather than silently ignoring files. The standard requires only that the MTHDS content itself — manifest, bundles, lock — be interpreted as specified.

## Discovery: Registry Indexes

One or more [registries](registry.md) index packages without owning them: they crawl known package addresses, parse manifests and bundles, and serve search, package pages, validation badges, and freshness signals.

**The registry is off the install path — by design, not by accident.** Because [version resolution](version-resolution.md) needs nothing beyond the manifests and the repositories' own tags, and packages are fetched straight from their repositories, bare Git access is sufficient to resolve, lock, and install anything. A registry can disappear without breaking a single build.

## Multi-Tier Deployment

MTHDS supports multiple deployment tiers, from local to community-wide:

| Tier | Scope | Typical use |
|------|-------|-------------|
| **Local** | Single `.mthds` file, no manifest | Learning, prototyping, one-off methods |
| **Project** | Package in a project repo | Team methods, versioned with the codebase |
| **Organization** | Private Git hosting + an internal registry index | Company-wide approved methods, governance |
| **Community** | Public Git repos + public registries | The open method ecosystem |

Registry proxy and mirror modes — an organization-tier convenience layer over this model — are a [future direction](future-directions.md); they are additive precisely because the install path never depended on a registry.

## See Also

- [The Registry](registry.md) — the discovery surface that indexes packages.
- [The Lock File](lock-file.md) — how fetched versions are pinned and verified.
- [Version Resolution](version-resolution.md) — how versions are selected.
- [Specification: Library Crate Format](../spec/library-crate.md) — the resolution artifact assembled from the project-local cache.
- [Specification: Fetching Remote Dependencies](../spec/namespace-resolution.md#fetching-remote-dependencies) — normative reference for the fetch algorithm.
- [Specification: Cache Layout](../spec/namespace-resolution.md#cache-layout) — normative reference for cache paths.
