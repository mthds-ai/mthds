# Distribution

MTHDS packages are distributed using a federated model: decentralized storage with centralized discovery.

## Storage: Git Repositories

Packages live in Git repositories. The repository IS the package — no upload step, no proprietary hosting. Authors retain full control.

A repository can contain one package (at the root) or multiple packages (in subdirectories with distinct addresses).

## Addressing and Fetching

Package addresses map directly to Git clone URLs:

1. Prepend `https://`.
2. Append `.git` (if not already present).

```
github.com/acme/legal-tools → https://github.com/acme/legal-tools.git
```

The resolution chain when fetching a dependency:

1. **Local path** — if the dependency has a `path` field in `METHODS.toml`, resolve from the local filesystem.
2. **Local cache** — check `~/.mthds/packages/{address}/{version}/` for a cached copy.
3. **VCS fetch** — clone the repository at the resolved version tag using `git clone --depth 1 --branch {tag}`.

## Version Tags

Version tags in remote repositories may use a `v` prefix (e.g., `v1.0.0`). The prefix is stripped during version parsing. Both `v1.0.0` and `1.0.0` are recognized.

Tags are listed using `git ls-remote --tags`, and only those that parse as valid semantic versions are considered.

## Package Cache

Fetched packages are cached locally to avoid repeated clones:

```
~/.mthds/packages/{address}/{version}/
```

For example:

```
~/.mthds/packages/github.com/acme/legal-tools/1.0.0/
```

The `.git` directory is removed from cached copies to save space. Cache writes use a staging directory with atomic rename for safety.

## Discovery: Registry Indexes

One or more registry services index packages without owning them. A registry provides:

- **Search** — by domain, by concept, by pipe signature, by description.
- **Type-compatible search** — "find all pipes that accept `LoanApplication` and produce something refining `RiskAssessment`" (enabled by the MTHDS type system).
- **Metadata** — versions, descriptions, licenses, dependency graphs.
- **Concept/pipe browsing** — navigate the refinement hierarchy, explore pipe signatures.

Registries build their index by crawling known package addresses, parsing `METHODS.toml` for metadata, and parsing `.mthds` files for concept definitions and pipe signatures. No data is duplicated — everything is derived from the source files.

## Multi-Tier Deployment

MTHDS supports multiple deployment tiers, from local to community-wide:

| Tier | Scope | Typical use |
|------|-------|-------------|
| **Local** | Single `.mthds` file, no manifest | Learning, prototyping, one-off methods |
| **Project** | Package in a project repo | Team methods, versioned with the codebase |
| **Organization** | Internal registry/proxy | Company-wide approved methods, governance |
| **Community** | Public Git repos + public registries | Open-source Know-How Graph |

## See Also

- [The Registry](registry.md) — the HTTP service that indexes packages and powers discovery.
- [Registry Distribution Protocol](registry-distribution.md) — proxy chains, signed manifests, and multi-tier deployment.
- [Specification: Fetching Remote Dependencies](../spec/namespace-resolution.md#fetching-remote-dependencies) — normative reference for the fetch algorithm.
- [Specification: Cache Layout](../spec/namespace-resolution.md#cache-layout) — normative reference for cache paths.
- [The Lock File](lock-file.md) — how fetched versions are pinned.
- [The Know-How Graph](../know-how-graph/index.md) — typed discovery across packages.
