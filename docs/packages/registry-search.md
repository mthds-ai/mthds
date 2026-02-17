---
description: "Type-aware search semantics for the MTHDS registry — concept compatibility, refinement chain walking, and graph query rules."
---

# Registry Search

The registry exposes two search modes: **text search** (substring matching on names and descriptions) and **type-compatible search** (signature-based queries that understand the concept refinement hierarchy). This page specifies the semantics of type-compatible search and graph queries.

## Concept Compatibility

Type-compatible search is built on a single rule:

> An output concept is **compatible** with an input concept if the output concept is exactly the input concept, OR the output concept is a refinement (descendant) of the input concept.

Compatibility is resolved by walking up the refinement chain from the output concept. If any ancestor in the chain matches the input concept, the concepts are compatible.

### Example

Given this refinement chain:

```
NonCompeteClause → ContractClause → Text
```

- `NonCompeteClause` is compatible with `Text` (descendant).
- `NonCompeteClause` is compatible with `ContractClause` (direct child).
- `NonCompeteClause` is compatible with `NonCompeteClause` (identity).
- `Text` is NOT compatible with `NonCompeteClause` (ancestor, not descendant).

The walk is cycle-safe: if a refinement chain contains a cycle (which violates the specification but can occur in malformed data), the walk terminates when a previously visited node is encountered.

## Query Types

### "What can I do with X?"

Given a concept, find all pipes that accept it as input.

A pipe accepts the concept if **any** of its input parameters expects the exact concept or an ancestor concept (i.e., the given concept is compatible with the input expectation via the refinement chain).

**API:**

```
GET /v1/search/typed?accepts=Document
```

**Semantics:**

For each pipe in the graph, for each input parameter:

1. Resolve the `accepts` parameter to a `ConceptId`.
2. Check if the given concept is compatible with the input concept (walk up from the given concept).
3. If any input parameter matches, include the pipe in results.

Each pipe appears at most once in the results, even if multiple input parameters match.

### "What produces Y?"

Given a concept, find all pipes that produce it.

A pipe produces the concept if its output is the exact concept or a refinement (descendant) of the requested concept.

**API:**

```
GET /v1/search/typed?produces=ContractClause
```

**Semantics:**

For each pipe in the graph:

1. Resolve the `produces` parameter to a `ConceptId`.
2. Check if the pipe's output concept is compatible with the requested concept (walk up from the pipe's output).
3. If compatible, include the pipe in results.

### Combined: Accepts and Produces

When both `accepts` and `produces` are specified, the registry returns pipes that satisfy both conditions simultaneously.

**API:**

```
GET /v1/search/typed?accepts=Document&produces=ContractClause
```

### "I have X, I need Y" — Chain Discovery

When no single pipe transforms concept X into concept Y, the registry searches for multi-step pipe chains using breadth-first search (BFS).

**API:**

```
GET /v1/graph/chains?from=__native__::native.Document&to=github.com/acme/legal-tools::legal.contracts.ContractClause&max_depth=3
```

**Algorithm:**

1. Find all starter pipes — those that accept the `from` concept (using "What can I do with X?" logic).
2. Initialize a BFS queue with each starter pipe as a single-step chain.
3. For each chain in the queue:
    - If the last pipe's output is compatible with the `to` concept, record the chain as a result.
    - Otherwise, if the chain has not reached `max_depth`, find all pipes that accept the last pipe's output and extend the chain.
4. Visited pipe keys are tracked per chain to prevent cycles.
5. Results are sorted shortest-first.

The `max_depth` parameter limits the maximum number of pipes in a single chain. The default is `3`.

**Example result:**

A query from `native.Document` to `legal.contracts.ContractClause` might discover:

```
Chain 1 (2 steps):
  extract_pages → extract_clause

Chain 2 (3 steps):
  extract_pages → analyze_content → extract_clause
```

### Compatibility Check

Given two pipe keys, determine whether the output of the first pipe can satisfy any input of the second.

**API:**

```
GET /v1/graph/compatibility?source=pkg::extract_pages&target=pkg::extract_clause
```

**Semantics:**

1. Look up both pipe nodes in the graph.
2. For each input parameter of the target pipe, check if the source pipe's output concept is compatible with the input concept.
3. Return the list of compatible parameter names.

An empty list means the pipes are incompatible.

## Cross-Package Concept Resolution

Type-compatible search works across package boundaries. When a concept in package A refines a concept in package B, the refinement chain spans both packages:

```
Package A:  EmploymentNDA → (refines) → Package B: NonDisclosureAgreement → (refines) → Text
```

Cross-package references are resolved during [graph construction](registry-indexing.md#step-2-resolve-refinement-targets) using the `dependency_aliases` map from `METHODS.toml`:

1. The `refines` string `acme_legal->legal.contracts.NonDisclosureAgreement` is split into alias (`acme_legal`) and remainder (`legal.contracts.NonDisclosureAgreement`).
2. The alias is resolved to a package address via the declaring package's `dependency_aliases`.
3. The concept is looked up in the target package by `concept_ref` or by bare concept code.

This resolution is transitive — a chain can span any number of packages as long as each link has a declared dependency with a valid alias.

## Refinement Chain Resolution

The registry exposes refinement chain information to help clients understand concept hierarchies. Given a concept, the registry walks up through `refines` links and returns the full chain:

```
[EmploymentNDA, NonDisclosureAgreement, ContractClause, Text]
```

The chain starts at the given concept and ends at the root (a concept with no `refines` link, or a native concept). The walk is cycle-safe.

## Concept Identification

Concepts in the graph are identified by a `ConceptId` with two components:

| Field | Description | Example |
|-------|-------------|---------|
| `package_address` | The package that defines the concept. `__native__` for native concepts. | `github.com/acme/legal-tools` |
| `concept_ref` | Domain-qualified concept reference. | `legal.contracts.ContractClause` |

The full node key is `{package_address}::{concept_ref}`.

When search queries use bare concept codes (e.g., `Document` rather than `__native__::native.Document`), the registry SHOULD resolve the code by:

1. Checking native concepts first.
2. Falling back to a unique match across all indexed packages.
3. Returning an error if the code is ambiguous (multiple packages define the same bare code).

## See Also

- [The Registry](registry.md) — API endpoint reference and request/response schemas.
- [Registry Indexing](registry-indexing.md) — how the graph is constructed from package data.
- [The Know-How Graph](../know-how-graph/index.md) — conceptual overview of typed discovery.
- [Concepts](../language/concepts.md) — how concepts define typed data and refinement.
