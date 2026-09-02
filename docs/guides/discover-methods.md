---
description: "Find existing MTHDS methods — browse and search a registry, read package pages, judge freshness and validation, and adopt what you find."
---

# Discover Methods

This guide shows how to find existing MTHDS methods and adopt them — by browsing a registry, reading package pages, and turning a discovery into a dependency.

## Browse a Registry

A [registry](../packages/registry.md) indexes published packages without hosting them — the public MTHDS registry runs at [mthds.sh](https://mthds.sh). Browsing gives you the ecosystem view: what exists, what is popular, and what is fresh.

Text search matches package names, concept codes, pipe codes, descriptions, and domain codes:

```
contract          → packages and pipes about contracts
legal.contracts   → everything in that domain
```

## Read the Package Page

A package page renders the registry's [index entry](../packages/registry.md#the-index-entry) — everything you need to evaluate a method before adopting it:

- **Identity** — the address (which is also how you will fetch it), the name, the version, the description, the license.
- **The entry point** — the `main_pipe`, when the package declares one: what runs if you invoke the package by address.
- **The public surface** — the exported pipes with their typed signatures (inputs and output), and the concepts they speak.
- **Dependencies** — what the package itself builds on.
- **Validation** — whether the registry validated this version (see [Validation Badges](../packages/registry.md#validation-badges)): a badge tied to a specific published version, not a floating claim.
- **Freshness** — when it was last updated and last indexed, and how far its latest version is from what consumers resolve.

## Try It by Address

Because the [address doubles as the fetch location](../packages/distribution.md#the-versioned-reference), a discovered package can be fetched and run directly — no install ceremony:

```
github.com/acme/legal-tools            # the default branch's latest state
github.com/acme/legal-tools@v1.2.0     # the repository at that tag
```

Running a package by its versioned reference executes its `main_pipe`. Trying a method at a pinned tag is the honest way to evaluate it: you see exactly what a locked dependency on that version would give you.

## Adopt What You Found

When a method earns a place in your own package, declare it:

```bash
mthds package add github.com/acme/legal-tools --alias acme_legal --version "^1.2.0"
```

and reference its exported pipes with the `->` syntax:

```toml
steps = [
    { pipe = "acme_legal->legal.contracts.extract_clause", result = "clauses" },
]
```

See [Use Dependencies](use-dependencies.md) for the full workflow.

## Typed Discovery: A Future Direction

Search by *typed signature* — "I have a `Document`, I need a `NonCompeteClause`", answered from pipe signatures and the concept refinement hierarchy, including multi-step chains — is where discovery is headed. It is specified as a [future direction](../packages/future-directions.md) of the registry, and the vision behind it is [The Know-How Graph](../know-how-graph/index.md).

## See Also

- [The Registry](../packages/registry.md) — the index surface behind discovery.
- [Distribution](../packages/distribution.md) — the versioned reference grammar and how fetching works.
- [Use Dependencies](use-dependencies.md) — how to add a discovered package as a dependency.
- [Future Directions](../packages/future-directions.md) — typed search and the Know-How Graph.
