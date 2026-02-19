# Version Resolution

When multiple packages depend on different versions of the same dependency, MTHDS needs a strategy to pick a single version. MTHDS uses **Minimum Version Selection** (MVS), the same approach used by Go modules.

## How MVS Works

Given a set of version constraints for a package, MVS:

1. Collects all version constraints from all dependents (direct and transitive).
2. Lists all available versions from VCS tags.
3. Sorts versions in ascending order.
4. Selects the **minimum** version that satisfies **all** constraints simultaneously.

If no version satisfies all constraints, the resolution fails with an error.

## An Example

Package A requires `>=1.0.0` of Library X. Package B requires `>=1.2.0` of Library X. Available versions of Library X: `1.0.0`, `1.1.0`, `1.2.0`, `1.3.0`, `2.0.0`.

MVS selects `1.2.0` — the minimum version that satisfies both `>=1.0.0` and `>=1.2.0`.

A maximum-version resolver would select `2.0.0`. MVS deliberately avoids this: you get the version you asked for, not the latest one.

## Why MVS?

- **Deterministic** — the same set of constraints always produces the same result, regardless of when you run the resolver.
- **Reproducible** — no dependency on a "latest" query or timestamp. The result depends only on the constraints and the available tags.
- **Simple** — no backtracking solver needed. Sort and pick the first match.
- **Conservative** — you get the minimum version that works, reducing the risk of pulling in untested changes.

## Transitive Dependencies

Dependencies are resolved transitively with these rules:

- **Remote dependencies** are resolved recursively. If Package A depends on Package B, and Package B depends on Package C, then Package C is also resolved.
- **Local path dependencies** are resolved at the root level only. They are NOT resolved transitively — only the root package's local paths are honored.
- **Cycle detection** — if a dependency is encountered while it is already being resolved, the resolver reports a cycle error.
- **Diamond dependencies** — when the same package address is required by multiple dependents with different version constraints, MVS selects the minimum version satisfying all constraints simultaneously.

## Diamond Dependencies

Diamond dependencies occur when two or more packages depend on the same third package:

```
Your Package
├── Package A (requires Library X ^1.0.0)
└── Package B (requires Library X ^1.2.0)
```

MVS handles this naturally: it collects both constraints (`^1.0.0` and `^1.2.0`), lists available versions, and picks the minimum version satisfying both. If constraints are contradictory (e.g., `^1.0.0` and `^2.0.0`), the resolver reports an error.

## See Also

- [Specification: Version Resolution Strategy](../spec/namespace-resolution.md#version-resolution-strategy) — normative reference.
- [Specification: Transitive Dependency Resolution](../spec/namespace-resolution.md#transitive-dependency-resolution) — normative reference for transitive resolution rules.
- [Dependencies](dependencies.md) — how to declare version constraints.
- [The Lock File](lock-file.md) — how resolved versions are recorded.
