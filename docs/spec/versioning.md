---
description: "How MTHDS is versioned — the standard version, the protocol version, what bumps each, and where the numbers appear."
---

# Versioning

MTHDS carries **two version numbers**, and they move independently:

| Number | Governs | Current |
|---|---|---|
| **Standard version** | The language, the native concept set, the manifest and lock formats, the library crate format, the namespace rules | `2.0.0` |
| **Protocol version** | The HTTP runner contract — its routes and their request and response shapes | `0.6.0` |

Both are [Semantic Versioning 2.0.0](https://semver.org/) numbers. Everything else that carries a version — a package's own `version`, a runner's `runner_version`, an implementation's release number — belongs to that package, runner, or implementation and is governed by whoever publishes it.

## The Standard Version

**The standard version is the version of this specification.** The release of the MTHDS specification, the `## [vX.Y.Z]` heading in its changelog, and the `MTHDS_STANDARD_VERSION` constant in every implementation are one number, not three. There is no separate "documentation release number" running alongside it.

It governs everything this specification defines other than the HTTP protocol:

- The [`.mthds` file format](./mthds-format.md) — the language itself: its sections, its keys, its pipe types, its concept structure language.
- The [native concept definitions](./native-concepts.md) — the pinned set every implementation materializes.
- The [`METHODS.toml` format](./manifest-format.md) and the [`methods.lock` format](./lock-format.md).
- The [library crate format](./library-crate.md) and the [namespace resolution rules](./namespace-resolution.md).

### What Bumps the Standard Version

- **MAJOR** — a breaking change to any of the above. A key removed or renamed, a native concept's shape changed, a rule that makes a previously valid bundle, manifest, or lock file invalid, or a previously invalid one valid in a way that changes what an existing document means.
- **MINOR** — an additive change. A new native concept, a new pipe type, a new optional key, a new field type: documents valid under the previous version stay valid and keep their meaning.
- **PATCH** — a change that is normatively inert. A clarification, a corrected example, a reworded rule that states what was already true, a new guide, a typo fix.

A release that changes nothing normative is a **patch** of the standard. That is the deliberate cost of one number: the standard version moves on every release of the specification, and a bump on its own is not evidence that anything changed. What changed is in the [changelog](../changelog.md).

### The Pinned Native Set Under One Number

Because a patch release moves the standard version without touching the native set, the [pinned set](./native-concepts.md) is **identified by the standard version in which it last changed**, not by the current standard version. `native-concepts.md` names that version.

An implementation implementing standard version `V` materializes **the pinned set of the greatest version less than or equal to `V`**. So an implementation of `2.3.0` uses the set pinned at `2.0.0` until a later version pins a new one, and two implementations of different patch or minor versions still byte-agree on materialized natives — which is what makes crate [fingerprints](./library-crate.md#fingerprint) comparable across them.

### `mthds_version` and the Crate Stamp

Two artifacts carry the standard version, and they mean different things:

- A manifest's [`mthds_version`](./manifest-format.md#mthds_version-constraints) is a **constraint**: the versions of the standard the package declares itself compatible with. It is evaluated against the standard version the runtime implements.
- A [library crate](./library-crate.md)'s `mthds_version` is a **stamp**: the exact standard version the crate was normalized against, recording which pinned native set was used.

Because both are compared against the standard version, the standard version MUST NOT move backwards. A crate stamped with an older version names an older pinned set, which is exactly what the stamp is for; a constraint written against an older version stays satisfiable.

## The Protocol Version

The [HTTP runner protocol](./protocol.md) is versioned separately, on its own cadence, because a client gates on it independently of the language it writes methods in. A runner reports it as `protocol_version` from `GET /version`, and it is the `info.version` of the normative [OpenAPI document](./openapi/mthds-protocol.openapi.yaml).

### What Bumps the Protocol Version

- **MAJOR** — a changed shape or a changed meaning. A route removed or renamed, a request or response field removed, renamed, or retyped, a required field added to a request, a status code's meaning changed. A client written against the previous version breaks.
- **MINOR** — an addition. A new route, a new optional request field, a new response field. A client written against the previous version keeps working unmodified.
- **PATCH** — a clarification of the document that changes no shape.

The protocol version is **not** derived from the standard version and never tracks it. A release of the standard that does not touch the protocol leaves the protocol version exactly where it was.

## The Changelog Contract

Every released version heading in [`CHANGELOG.md`](../changelog.md) names the two versions it carries:

```markdown
## [v2.1.0] - 2026-10-14

**MTHDS standard 2.1.0 · MTHDS Protocol 0.6.0**
```

The standard version always equals the heading's own version, by the rule above. The protocol version is repeated on every heading whether or not it moved, so that a reader landing on any release can tell which protocol it shipped without walking backwards through the file.

While a release is being prepared, the entries accumulate under a single `## [Unreleased]` heading that announces the version it will cut, in the same form.

## Where the Numbers Appear

| Number | Where |
|---|---|
| Standard | The specification's release version and its changelog headings |
| Standard | `MTHDS_STANDARD_VERSION` in each implementation |
| Standard | The version `native-concepts.md` pins its set at (the last version in which the set changed) |
| Standard | A manifest's `mthds_version` constraint, evaluated against the runtime's standard version |
| Standard | A library crate's `mthds_version` stamp |
| Protocol | `info.version` in `mthds-protocol.openapi.yaml` |
| Protocol | `protocol_version` in every `GET /version` response |
| Protocol | The conformance statement in [the protocol specification](./protocol.md#conformance) |

An implementation's copies of these numbers are exactly that — copies of a cut made here. Each SHOULD be declared once, in one place, naming this page as its source, so that following a cut is a single edit rather than a search.

## History: The 2.0.0 Unification

The numbers above were not always one system. Before `2.0.0`, the specification published its own release numbers, from `v0.0.1` up to `v0.10.0`, while `MTHDS_STANDARD_VERSION` sat at `1.0.0` — set alongside `v0.1.0` in February 2026 and never moved after that, through the removal of a native concept, the addition of another, three natives whose shape changed, and a set of breaking manifest, lock and resolution rules. Manifests constrained `>=1.0.0`, crates were stamped `1.0.0`, and neither number said what the standard had actually become.

`2.0.0` is the cut that pays that debt and unifies the two numbers into one:

- It is a **major** bump because the changes it accounts for are breaking — see the [changelog](../changelog.md) entries for `v0.8.0`, `v0.9.0`, and `v0.10.0`.
- It moves **forwards** from `1.0.0`, so no artifact in the wild is invalidated by the unification itself: a manifest constraining `>=1.0.0` remains satisfiable, and a crate stamped `1.0.0` still names a real pinned set older than the current one.
- From `2.0.0` onward there is one standard version, and it moves on every release of this specification under the rules above.

The protocol number was reconciled at the same time and kept its value. `0.6.0` is what the normative OpenAPI document and the shipped client libraries had been reporting; the readings that disagreed — a `0.1.0` in a hosted implementation and a "v0.1" in this specification's own conformance sentence — were corrected to follow it.
