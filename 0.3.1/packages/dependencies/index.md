# Dependencies

> **Not yet implemented.** Dependencies between packages are planned but not yet supported. The documentation below describes the intended behavior for a future release.

Dependencies allow a package to build on other packages. Each dependency is declared in the `[dependencies]` section of `METHODS.toml` with an alias, an address, and a version constraint.

## Declaring Dependencies

```toml
[dependencies]
docproc     = { address = "github.com/mthds/document-processing", version = "^1.0.0" }
scoring_lib = { address = "github.com/mthds/scoring-lib", version = "^0.5.0" }
```

Each key (`docproc`, `scoring_lib`) is the **alias** — a short `snake_case` name used in [cross-package references](cross-package-references.md) (`alias->domain.name`).

## Dependency Fields

| Field | Required | Description |
|-------|----------|-------------|
| `address` | Yes | The dependency's package address (hostname/path pattern). |
| `version` | Yes | Version constraint (see below). |
| `path` | No | Local filesystem path, for development-time workflows. |

## Aliases

The alias is the TOML key for each dependency entry. It must be `snake_case` (matching `[a-z][a-z0-9_]*`), and all aliases within a single manifest must be unique.

Aliases appear in cross-package references:

```toml
steps = [
    { pipe = "docproc->extraction.extract_text", result = "pages" },
    { pipe = "scoring_lib->scoring.compute_weighted_score", result = "score" },
]
```

Choose aliases that are short, meaningful, and easy to read in references.

## Version Constraints

Version constraints specify which versions of a dependency are acceptable:

| Form | Syntax | Example | Meaning |
|------|--------|---------|---------|
| Exact | `MAJOR.MINOR.PATCH` | `1.0.0` | Exactly this version. |
| Caret | `^MAJOR.MINOR.PATCH` | `^1.0.0` | Compatible release (same major version). |
| Tilde | `~MAJOR.MINOR.PATCH` | `~1.0.0` | Approximately compatible (same major.minor). |
| Greater-or-equal | `>=MAJOR.MINOR.PATCH` | `>=1.0.0` | This version or newer. |
| Less-than | `<MAJOR.MINOR.PATCH` | `<2.0.0` | Older than this version. |
| Compound | constraint `, ` constraint | `>=1.0.0, <2.0.0` | Both constraints must be satisfied. |
| Wildcard | `*`, `MAJOR.*` | `1.*` | Any version matching the prefix. |

Additional operators `>`, `<=`, `==`, and `!=` are also supported. Partial versions are allowed: `1.0` is equivalent to `1.0.*`.

## Local Path Dependencies

For development-time workflows where packages are co-located on disk, add a `path` field:

```toml
[dependencies]
scoring = { address = "github.com/mthds/scoring-lib", version = "^0.5.0", path = "../scoring-lib" }
```

When `path` is set, the dependency is resolved from the local filesystem instead of being fetched via VCS. The path is resolved relative to the directory containing `METHODS.toml`.

This is similar to Cargo's `path` dependencies or Go's `replace` directives.

**Important behaviors of local path dependencies:**

- They are NOT resolved transitively — only the root package's local paths are honored.
- They are excluded from the [lock file](lock-file.md).
- When publishing, the `path` field is informational — consumers fetch via the `address`.

## See Also

- [Specification: The `[dependencies]` Section](../spec/manifest-format.md#the-dependencies-section) — normative reference for all fields.
- [Specification: Version Constraint Syntax](../spec/manifest-format.md#version-constraint-syntax) — full syntax reference.
- [Version Resolution](version-resolution.md) — how dependency versions are selected.
- [Cross-Package References](cross-package-references.md) — how aliases are used in `.mthds` files.
