# The Know-How Graph

The package system provides the infrastructure for something unique to MTHDS: the **Know-How Graph** — a typed, searchable network of AI methods that spans packages.

## Pipes as Typed Nodes

Every exported pipe has a typed signature — the concepts it accepts and the concept it produces:

```
extract_clause:          (ContractDocument) → NonCompeteClause
classify_document:       (Document)         → ClassifiedDocument
compute_weighted_score:  (Text)             → ScoreResult
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

## See Also

- [Concepts](../language/concepts.md) — how concepts define typed data and refinement.
- [Exports & Visibility](../packages/exports-visibility.md) — which pipes are visible in the graph.
- [Distribution](../packages/distribution.md) — how registries index packages.
- [The Registry](../packages/registry.md) — the HTTP service that exposes the Know-How Graph for remote queries.
- [Registry Search](../packages/registry-search.md) — type-aware search semantics and graph query rules.
