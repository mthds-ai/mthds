# The Know-How Graph

When packages export typed pipes and concepts into a shared ecosystem, something emerges: the **Know-How Graph** — a typed, searchable network of AI methods that spans packages. Instead of searching for methods by keyword or description, you can ask "I have a `ContractDocument`, I need a `NonCompeteClause`" and the graph finds the methods — or chains of methods — that get you there.

## Pipes as Typed Nodes

Every exported pipe has a typed signature — the concepts it accepts and the concept it produces:

```
extract_clause:          (ContractDocument) → NonCompeteClause
classify_document:       (Document)         → ClassifiedDocument
summarize_findings:      (Text)             → ExecutiveSummary
```

These signatures, combined with the concept refinement hierarchy, form a directed graph:

- **Nodes** are pipe signatures (typed transformations).
- **Edges** are data flow connections — the output concept of one pipe type-matches the input concept of another.
- **Refinement edges** connect concept hierarchies (e.g., `NonCompeteClause` refines `ContractClause` refines `Text`).

## Type-Compatible Discovery

The type system enables queries that text-based discovery cannot support:

| Query | Example |
|-------|---------|
| "I have X, I need Y" | "I have a `Document`, I need a `NonCompeteClause`" — finds all pipes or chains that produce it. |
| "What can I do with X?" | "What pipes accept `ContractDocument` as input?" — shows downstream possibilities. |
| Compatibility check | Before installing a package, verify its pipes are type-compatible with yours. |

Because MTHDS concepts have a refinement hierarchy, type-compatible search understands that a pipe accepting `Text` also accepts `NonCompeteClause` (since `NonCompeteClause` refines `Text` through the refinement chain).

## Auto-Composition

When no single pipe transforms X into Y, the Know-How Graph can find a **chain** through intermediate concepts:

```
Document → [extract_pages] → Page[] → [analyze_content] → AnalysisResult
```

This is auto-composition — discovering multi-step pipelines by traversing the graph. The `mthds pkg graph` command supports this with the `--from` and `--to` options.

## Cross-Package Concept Refinement

Packages can extend another package's vocabulary through concept refinement:

```toml
# In your package, depending on acme_legal
[concept.EmploymentNDA]
description = "A non-disclosure agreement specific to employment contexts"
refines     = "acme_legal->legal.contracts.NonDisclosureAgreement"
```

This builds on `NonDisclosureAgreement` from the `acme_legal` dependency without merging namespaces. The refinement relationship enriches the Know-How Graph: any pipe that accepts `NonDisclosureAgreement` now also accepts `EmploymentNDA`.

## From Packages to Knowledge

The Know-How Graph emerges naturally from the package system:

1. Each package exports pipes with typed signatures.
2. Concepts define a shared vocabulary with refinement hierarchies.
3. Dependencies connect packages, enabling cross-package references.
4. Registry indexes crawl this information and make it searchable.

The result is a federated network of composable, discoverable, type-safe AI methods — where finding the right method is as precise as asking "I have X, I need Y."

The Know-How Graph is infrastructure that agents can navigate. An agent can discover methods by typed signature, compose multi-step chains through intermediate concepts, and build new methods that extend the graph. Each method an agent creates or refines becomes a node that other agents — or humans — can discover and reuse. The graph grows as the ecosystem grows.

The ecosystem follows an open-commons model. Common tasks — contract extraction, document classification, expense processing — get solved once and shared as public packages. Organization-specific workflows stay private simply by not being published. When a package is published, the `exports` field in `METHODS.toml` controls which pipes and concepts are part of the public API, but the fundamental privacy boundary is publication itself.

## See Also

- [The Know-How Graph Viewpoint](https://knowhowgraph.com/) — the extended essay on the Know-How Graph vision and why AI agents need typed methods.
- [Concepts](../language/concepts.md) — how concepts define typed data and refinement.
- [Exports & Visibility](../packages/exports-visibility.md) — which pipes are visible in the graph.
- [Distribution](../packages/distribution.md) — how registries index packages.
- [The Registry](../packages/registry.md) — the HTTP service that exposes the Know-How Graph for remote queries.
- [Registry Search](../packages/registry-search.md) — type-aware search semantics and graph query rules.
