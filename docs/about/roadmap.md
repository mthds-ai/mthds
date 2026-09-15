---
description: "Planned directions for MTHDS: dependency implementation, cross-package crate fold-in, registry growth, and the specified future directions."
---

# Roadmap

The MTHDS standard is at version `2.0.0`. This page outlines planned and potential directions for future development.

## Near-Term

- **Dependency implementation.** The `[dependencies]` section, Minimum Version Selection, lock generation, and install-time verification are fully specified (see the [manifest](../spec/manifest-format.md#the-dependencies-section) and [lock](../spec/lock-format.md) specifications); bringing the reference implementations into conformance is the standard's main open implementation item.
- **Cross-package crate fold-in.** The [library crate](../spec/library-crate.md) specifies its multi-package keyspace (host-relative `::` address keys); applying the fold-in pass — producing a self-contained crate for a closure that spans packages — is the other open implementation item.
- **Registry growth.** The registry surface is specified at [The Registry](../packages/registry.md) — index, package pages, validation badges, freshness signals — and the live index at [mthds.sh](https://mthds.sh) grows toward it.
- **Cross-package concept refinement validation at install time.** The specification allows validation of concept refinement across packages at both install time and load time. The current reference implementation validates at load time only. Install-time validation would detect breaking changes earlier.

## Future Directions

Typed signature search, the Know-How Graph's query surface, signed manifests with a trust store, and registry proxy/mirror chains are worked-out ambitions preserved on the [Future Directions](../packages/future-directions.md) page — deliberately kept distinct from the specified system.

## Long-Term

- **Conditional concept fields.** Allow concept structure fields to be conditionally present based on the values of other fields.
- **Runtime interoperability standard.** A specification for how different MTHDS runtimes can exchange concept instances, enabling cross-runtime pipe invocation.

## Contributing to the Roadmap

The roadmap is shaped by community needs. If you have a use case that the standard does not yet support, open an issue in the MTHDS standard repository. Proposals that include concrete `.mthds` examples demonstrating the need are especially helpful.
