# Version Resolution

When multiple packages depend on different versions of the same dependency, MTHDS needs a strategy to pick a single version. MTHDS uses **Minimum Version Selection** (MVS), the same approach used by Go modules.

## How MVS Works

Given a set of version constraints for a package, MVS:

1. Collects all version constraints from all dependents (direct and transitive).
2. Lists all available versions from VCS tags.
3. Sorts versions in ascending order.
4. Selects the **minimum** version that satisfies **all** constraints simultaneously.

If no version satisfies all constraints, the resolution fails with an error.

## Constraints Are Floors

Under MVS, a version constraint states the *minimum* version a dependent is known to work with — its **floor**. The resolved version is, for plain floor constraints, the maximum of the declared floors across the graph: high enough for everyone, and never higher than a version some manifest actually names. A newly published release is invisible to resolution until someone deliberately raises a floor to it.

## An Example

Package A requires `>=1.0.0` of Library X. Package B requires `>=1.2.0` of Library X. Available versions of Library X: `1.0.0`, `1.1.0`, `1.2.0`, `1.3.0`, `2.0.0`.

MVS selects `1.2.0` — the minimum version that satisfies both `>=1.0.0` and `>=1.2.0`.

A maximum-version resolver would select `2.0.0`. MVS deliberately avoids this: you get the version you asked for, not the latest one.

## Why MVS?

- **Deterministic** — the same constraints against the same published tags always produce the same result. The build list is fully determined by the manifests and the repositories' published tags: no registry has to be consulted, or even exist, for resolution to succeed.
- **Reproducible** — no dependency on a "latest" query or timestamp. The result depends only on the constraints and the available tags, which is why the [lock file](lock-file.md) is regenerable from them rather than consulted to decide versions — it remains the record that pins what was actually fetched.
- **Explainable** — an agent or a person can predict the resolved versions by reading the manifests, and a resolution error is explainable in one sentence.
- **Simple** — no backtracking solver needed. Sort and pick the first match.
- **Safe for a prompt ecosystem** — a method's payload is prompts, and a "patch" release can change behavior. Because nothing upgrades implicitly, a freshly published version — including a malicious one — is never auto-adopted into anyone's method.

## Adding and Updating: Deliberate Adoption

Because re-resolution alone never moves a version, moving forward is always an explicit edit to `METHODS.toml`, followed by a re-lock:

- **`add`** fetches the dependency's latest version and records it as the floor. Adding a dependency always gets you the newest release, just as it does everywhere else.
- **`update`** raises the floors of your existing dependencies to the latest available versions, then re-locks. This is the deliberate-adoption gesture: you choose when to move, and tooling shows you what moved — the lock's [fingerprint](lock-file.md) field lets that diff be *semantic* (which concepts, pipes, and prompts changed) rather than a wall of text.

From the chair, this feels like any modern package manager: `add` gets latest, `update` gets latest, the lock is committed. What differs is what happens when you do nothing — under MVS, nothing.

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

MVS handles this naturally: it collects both constraints (`^1.0.0` and `^1.2.0`), lists available versions, and picks the minimum version satisfying both. If constraints are incompatible (e.g., `^1.0.0` and `^2.0.0` have no overlapping range), the resolver reports an error. A closure holds exactly one version of a package per address — there are no nested multi-version trees.

## Staying Fresh

MVS trades silent upgrades for deliberate ones, and the gap it opens — transitive dependencies waiting for someone to raise a floor — is closed by tooling rather than resolver policy: registries surface freshness (the resolved version beside the latest published one), and the `update` gesture with its semantic diff makes acting on that signal cheap.

## See Also

- [Specification: Version Resolution Strategy](../spec/namespace-resolution.md#version-resolution-strategy) — normative reference.
- [Specification: Transitive Dependency Resolution](../spec/namespace-resolution.md#transitive-dependency-resolution) — normative reference for transitive resolution rules.
- [Dependencies](dependencies.md) — how to declare version constraints.
- [The Lock File](lock-file.md) — how resolved versions are recorded and verified.
