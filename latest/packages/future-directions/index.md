# Future Directions

This page preserves the package ecosystem's more ambitious designs as explicit **future directions**: worked-out ideas the standard intends to grow into, kept distinct from the specified system so that neither is mistaken for the other. Nothing on this page is normative, and no compliant tool or registry is expected to implement any of it today.

Each direction is compatible with the invariants of the specified system — in particular, that [the registry is off the install path](registry.md#role-in-the-ecosystem) and that [resolution is deterministic from manifests alone](version-resolution.md). These are additive layers, which is precisely why they can wait.

## Typed Signature Search

Text search finds methods by name and description. Typed search would find them by **what they transform**: every exported pipe has a typed signature — the concepts it accepts and the concept it produces — and, combined with the concept refinement hierarchy, those signatures support queries text cannot answer.

The compatibility rule at the core:

> An output concept is compatible with an input concept if the output concept is exactly the input concept, or a refinement (descendant) of it.

Compatibility is resolved by walking up the refinement chain from the output concept — cycle-safe, and spanning packages wherever a concept refines a dependency's concept. On top of that rule, a registry could serve:

- **"What can I do with X?"** — all pipes accepting a given concept as input (`GET /v1/search/typed?accepts=Document`).
- **"What produces Y?"** — all pipes whose output is the concept or a refinement of it (`GET /v1/search/typed?produces=ContractClause`).
- **Both at once** — pipes bridging two types.

## The Know-How Graph

Typed signatures generalize into the **Know-How Graph** — a directed graph over an entire registry index in which concepts and pipes are nodes, refinement links and type-compatible data flows are edges, and identity is carried by address-prefixed keys (`{package_address}::{concept_ref}`, with `__native__` as the synthetic address of native concepts — the same `::` scheme the [library crate](../spec/library-crate.md#1-merge) uses for dependency-contributed entries).

The graph would enable:

- **Chain discovery** — "I have X, I need Y": when no single pipe transforms one concept into another, a breadth-first search over data-flow edges finds multi-step chains through intermediate concepts, shortest first, up to a depth bound.
- **Compatibility checks** — given two pipes, whether the output of the first can satisfy an input of the second, and through which parameter.
- **Auto-composition** — turning a discovered chain into a ready-to-use `PipeSequence` skeleton.

Constructing the graph is an indexing concern layered over the specified pipeline: resolve every concept reference (including cross-package `refines` targets through declared aliases) to an address-prefixed identity, build refinement edges, and connect pipes whose types are compatible — excluding, rather than guessing at, anything unresolvable. Type-driven results would be ranked purely by types: social signals never influence them.

The vision — a federated, typed, searchable network of AI methods that agents can navigate and extend — is described on [The Know-How Graph](../know-how-graph/index.md).

## Signed Manifests and a Trust Store

The specified integrity chain is content-derived: the lock's byte hash and crate fingerprint are recomputable by anyone from source (see [The Lock File](lock-file.md)). Signed manifests would add **provenance** on top — *who published this* — for ecosystems that need it:

- A detached signature object binding the SHA-256 of the raw `METHODS.toml` bytes to an Ed25519 signature, with the signer identity, a timestamp, and a `public_key_id` for key rotation.
- Verification: recompute the manifest digest, reconstruct the canonical signing payload (sorted-key JSON, no whitespace), verify the signature against the identified public key.
- A two-level trust store for public keys: system-wide (`~/.mthds/trust/`) and per-project (`.mthds/trust/`).

A client would never treat an unsigned package as verified — but signing remains an opt-in layer for organizational and enterprise policies, not a prerequisite for participating in the ecosystem.

## Registry Proxy and Mirror Chains

For availability, governance, and air-gapped environments, clients could be configured with an ordered list of registries, analogous to Go's `GOPROXY` protocol:

```
MTHDS_REGISTRY=https://registry.internal.acme.com,https://community.mthds.ai,direct
```

- A **proxy** registry forwards requests to an upstream and caches responses.
- A **mirror** registry maintains a synchronized full copy of an upstream's index and serves it locally.
- The terminal `direct` entry bypasses registries and fetches straight from Git — which is also the specified system's only behavior today, and the reason proxy chains are purely additive: the fallback every chain ends in is the thing that already works.

An organization-tier registry in such a chain could index private packages, enforce approval policies before exposing external ones, and cache community packages for isolated networks.

## See Also

- [The Registry](registry.md) — the specified registry surface these directions extend.
- [Registry Indexing](registry-indexing.md) — the specified indexing pipeline.
- [The Know-How Graph](../know-how-graph/index.md) — the vision these capabilities serve.
- [Distribution](distribution.md) — the federated model none of this changes.
