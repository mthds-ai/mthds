---
description: "Search for and discover existing MTHDS methods — by text, by domain, or by typed signature using the know-how graph."
---

# Discover Methods

This guide shows how to search for and discover existing MTHDS methods — by text, by domain, or by typed signature.

## Searching by Text

The simplest search is a text query:

```bash
mthds pkg search "contract"
```

This searches concepts and pipes for the term "contract" (case-insensitive substring match) and displays matching results in tables showing package, name, domain, description, and export status.

To narrow results:

```bash
# Show only concepts
mthds pkg search "contract" --concept

# Show only pipes
mthds pkg search "contract" --pipe

# Filter by domain
mthds pkg search "extract" --domain legal.contracts
```

## Searching by Type ("I Have X, I Need Y")

MTHDS enables something that text-based discovery cannot: **type-compatible search**. Instead of searching by name, you search by what data types a pipe accepts or produces.

### "What can I do with X?"

Find all pipes that accept a given concept:

```bash
mthds pkg search --accepts Document
```

This returns every pipe whose input type is `Document` or a concept that `Document` refines. Because the search understands the concept refinement hierarchy, it finds pipes you might not discover through text search alone.

### "What produces Y?"

Find all pipes that produce a given concept:

```bash
mthds pkg search --produces NonCompeteClause
```

### Combining Accepts and Produces

Find pipes that bridge two types:

```bash
mthds pkg search --accepts Document --produces NonCompeteClause
```

## Exploring the Know-How Graph

For more advanced queries — multi-step chains, compatibility checks, auto-composition — use the `mthds pkg graph` command.

### Finding Chains

When no single pipe transforms X into Y, the graph can find multi-step chains:

```bash
mthds pkg graph \
  --from "__native__::native.Document" \
  --to "github.com/acme/legal-tools::legal.contracts.NonCompeteClause"
```

This might discover a chain like:

```
1. extract_pages -> analyze_content -> extract_clause
```

With `--compose`, it generates a ready-to-use MTHDS snippet:

```bash
mthds pkg graph \
  --from "__native__::native.Document" \
  --to "github.com/acme/legal-tools::legal.contracts.NonCompeteClause" \
  --compose
```

### Checking Compatibility

Before wiring two pipes together, verify they are type-compatible:

```bash
mthds pkg graph --check "pkg_a::extract_pages,pkg_a::analyze_content"
```

This reports whether the output of the first pipe matches any input of the second.

## Searching Cached Packages

By default, search and graph commands operate on the current project. To search across all cached packages (everything you have installed):

```bash
mthds pkg search "scoring" --cache
mthds pkg graph --from "__native__::native.Text" --cache
```

## Inspecting a Package

To see the full contents of a specific package — its domains, concepts, and pipe signatures:

```bash
mthds pkg inspect github.com/acme/legal-tools
```

This displays detailed tables for every domain, concept (including structure fields and refinement), and pipe (including inputs, outputs, and export status).

## Building the Index

Before searching, you may want to build or refresh the package index:

```bash
# Index the current project
mthds pkg index

# Index all cached packages
mthds pkg index --cache
```

The index is built automatically when you run search or graph commands, but building it explicitly lets you verify what packages are available.

## See Also

- [The Know-How Graph](../know-how-graph/index.md) — how typed signatures enable semantic discovery.
- [Cross-Package References](../packages/cross-package-references.md) — how to use discovered pipes in your bundles.
- [Use Dependencies](use-dependencies.md) — how to add a discovered package as a dependency.
- [The Registry](../packages/registry.md) — query remote registries for packages beyond your local cache.
- [Registry Search](../packages/registry-search.md) — type-aware search semantics and concept compatibility rules.
