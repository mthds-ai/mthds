# Registry Indexing

A registry builds its index by crawling Git-hosted packages, parsing their manifests and bundles, and constructing a [Know-How Graph](../know-how-graph/index.md) from the extracted metadata. This page specifies the indexing pipeline.

## Indexing Pipeline

The indexing pipeline transforms a package address into a `PackageIndexEntry`:

```
address → git clone → parse METHODS.toml → scan .mthds files → PackageIndexEntry
```

### Step 1: Clone the Repository

The registry resolves the package address to a Git clone URL:

1. Prepend `https://`.
2. Append `.git` (if not already present).

```
github.com/acme/legal-tools → https://github.com/acme/legal-tools.git
```

The registry MUST use `git ls-remote --tags` to enumerate available version tags before cloning. Only tags that parse as valid [semantic versions](../packages/version-resolution.md) are considered. Both `v`-prefixed (e.g., `v1.0.0`) and bare (e.g., `1.0.0`) tags are recognized.

The registry clones at the latest stable version tag using `git clone --depth 1 --branch {tag}`.

### Step 2: Parse the Manifest

The registry reads `METHODS.toml` from the package root. This provides:

| Field | Type | Description |
|-------|------|-------------|
| `address` | `string` | Package address (e.g., `github.com/acme/legal-tools`). |
| `version` | `string` | Semantic version (e.g., `1.2.0`). |
| `description` | `string` | Human-readable package description. |
| `authors` | `list[string]` | Package authors. |
| `license` | `string \| null` | SPDX license identifier. |
| `dependencies` | `table[alias, PackageDependency]` | Declared dependencies with address, version constraint, and alias. |
| `exports` | `table[domain_path, DomainExports]` | Which pipes are publicly visible, grouped by domain path. |

If `METHODS.toml` is missing or fails validation, the registry MUST skip the package and log a warning. A malformed manifest MUST NOT cause the registry to stop indexing other packages.

### Step 3: Scan Bundles

The registry collects all `.mthds` files recursively from the package root. For each bundle file, it parses the MTHDS content and extracts:

**Domains:**

Each bundle declares a domain. The registry builds a `DomainEntry` for each unique domain encountered:

```json
{
  "domain_code": "legal.contracts",
  "description": "Contract processing domain"
}
```

**Concepts:**

Each concept definition produces a `ConceptEntry`:

```json
{
  "concept_code": "ContractClause",
  "domain_code": "legal.contracts",
  "concept_ref": "legal.contracts.ContractClause",
  "description": "A single clause extracted from a contract",
  "refines": "native.Text",
  "structure_fields": ["clause_type", "text", "section_number"]
}
```

The `concept_ref` is always `{domain_code}.{concept_code}`. The `refines` field is the raw string from the bundle — it is resolved to a cross-package identity during [graph construction](#know-how-graph-construction).

**Pipes:**

Each pipe definition produces a `PipeSignature`:

```json
{
  "pipe_code": "extract_clause",
  "pipe_type": "PipeLLM",
  "domain_code": "legal.contracts",
  "description": "Extract a specific clause from a contract document",
  "input_specs": { "source": "ContractDocument" },
  "output_spec": "ContractClause",
  "is_exported": true
}
```

The `is_exported` flag is determined by the manifest's `[exports]` section:

- If the manifest declares exports for the pipe's domain and the pipe code appears in the exports list, `is_exported` is `true`.
- If no exports are declared at all (no manifest), all pipes are considered exported.

### Step 4: Assemble the Index Entry

The registry assembles a `PackageIndexEntry` from the parsed manifest and scanned bundles:

```json
{
  "address": "github.com/acme/legal-tools",
  "version": "1.2.0",
  "description": "Contract analysis and clause extraction methods",
  "authors": ["Acme Legal Team"],
  "license": "Apache-2.0",
  "domains": [
    { "domain_code": "legal.contracts", "description": "Contract processing domain" }
  ],
  "concepts": [ ... ],
  "pipes": [ ... ],
  "dependencies": ["github.com/mthds/document-processing"],
  "dependency_aliases": { "doc_processing": "github.com/mthds/document-processing" }
}
```

The `dependencies` list contains raw addresses. The `dependency_aliases` map aliases to addresses, enabling [cross-package concept resolution](registry-search.md#cross-package-concept-resolution) during graph construction.

Domains are sorted alphabetically by `domain_code`. Parse errors in individual bundles are logged as warnings — a single broken bundle MUST NOT prevent the rest of the package from being indexed.

## The Package Index

The `PackageIndex` is the collection of all `PackageIndexEntry` records, keyed by address:

```json
{
  "entries": {
    "github.com/acme/legal-tools": { ... },
    "github.com/mthds/document-processing": { ... }
  }
}
```

Operations on the index:

| Operation | Description |
|-----------|-------------|
| `add_entry` | Add or replace a package entry by address. |
| `get_entry` | Retrieve an entry by address. Returns null if not indexed. |
| `remove_entry` | Remove an entry by address. Returns whether the entry existed. |
| `all_concepts` | Return all concepts across all packages as `(address, ConceptEntry)` pairs. |
| `all_pipes` | Return all pipes across all packages as `(address, PipeSignature)` pairs. |

## Know-How Graph Construction

After building the package index, the registry enables the Know-How Graph — a directed graph of concepts and pipes that enables [type-aware search](registry-search.md). The construction follows these steps:

### Step 1: Build Concept Nodes

For every concept in every indexed package, the registry creates a `ConceptNode` with a globally unique `ConceptId`:

```json
{
  "concept_id": {
    "package_address": "github.com/acme/legal-tools",
    "concept_ref": "legal.contracts.ContractClause"
  },
  "description": "A single clause extracted from a contract",
  "refines": null,
  "structure_fields": ["clause_type", "text", "section_number"]
}
```

The node key is `{package_address}::{concept_ref}` (e.g., `github.com/acme/legal-tools::legal.contracts.ContractClause`).

The registry MUST also create concept nodes for all native concepts (`Text`, `Image`, `Document`, `Html`, `TextAndImages`, `Number`, `ImgGenPrompt`, `Page`, `JSON`, `Anything`, `Dynamic`). Native concepts use the package address `__native__` and concept references prefixed with `native.` (e.g., `native.Text`).

### Step 2: Resolve Refinement Targets

For each concept with a `refines` string, the registry resolves it to a `ConceptId`:

- **Local reference** (e.g., `ContractClause` or `legal.contracts.ContractClause`): resolved within the same package by matching against concept refs or bare concept codes.
- **Cross-package reference** (e.g., `dep_alias->domain.ConceptCode`): the alias is looked up in the package's `dependency_aliases` map to find the target package address, then the concept is resolved in the target package.

If the `refines` target cannot be resolved (unknown alias, missing concept), the registry MUST log a warning and leave the `refines` field as `null`. Unresolvable refinement targets MUST NOT prevent the concept from appearing in the graph.

### Step 3: Build Pipe Nodes

For every pipe in the index, the registry creates a `PipeNode` with resolved concept identities for all inputs and the output:

```json
{
  "package_address": "github.com/acme/legal-tools",
  "pipe_code": "extract_clause",
  "pipe_type": "PipeLLM",
  "domain_code": "legal.contracts",
  "description": "Extract a specific clause from a contract document",
  "is_exported": true,
  "input_concept_ids": {
    "source": {
      "package_address": "github.com/acme/legal-tools",
      "concept_ref": "legal.contracts.ContractDocument"
    }
  },
  "output_concept_id": {
    "package_address": "github.com/acme/legal-tools",
    "concept_ref": "legal.contracts.ContractClause"
  }
}
```

Concept resolution for pipe inputs and outputs follows the same rules as refinement resolution: native concepts, local references, domain-qualified references, and cross-package references are all supported.

If a pipe's output concept or any input concept cannot be resolved, the registry MUST exclude the entire pipe from the graph. Pipes with unresolvable concepts MUST NOT create dangling references.

### Step 4: Build Refinement Edges

For each concept node whose `refines` field is non-null, the registry creates a `REFINEMENT` edge:

```json
{
  "kind": "refinement",
  "source_concept_id": {
    "package_address": "github.com/acme/legal-tools",
    "concept_ref": "legal.contracts.NonCompeteClause"
  },
  "target_concept_id": {
    "package_address": "github.com/acme/legal-tools",
    "concept_ref": "legal.contracts.ContractClause"
  }
}
```

The source is the more specific concept; the target is the more general concept it refines.

### Step 5: Build Data Flow Edges

A data flow edge connects two pipes when the output of one can satisfy an input of the other. Compatibility is determined by the refinement hierarchy:

> A pipe's output concept is compatible with another pipe's input concept if the output concept is exactly the input concept, OR the output concept is a refinement (descendant) of the input concept.

The registry walks up the refinement chain from each pipe's output concept, collecting all ancestor node keys (cycle-safe). For each pipe's input, it looks up compatible producers from this reverse index.

```json
{
  "kind": "data_flow",
  "source_pipe_key": "github.com/acme/legal-tools::extract_pages",
  "target_pipe_key": "github.com/acme/legal-tools::extract_clause",
  "input_param": "source"
}
```

Self-loops (a pipe feeding into itself) are excluded.

## Index Refresh

A registry MUST support at least one mechanism for keeping the index current:

- **Manual trigger** — an API call or administrative action that re-indexes a specific package address.
- **Polling** — periodic re-crawl of known package addresses, comparing the latest version tag against the indexed version.
- **Webhook** — a Git hosting webhook (e.g., GitHub push event) that triggers re-indexing when a new tag is pushed.

A registry SHOULD expose the index freshness for each package (e.g., `indexed_at` timestamp) so that clients can assess staleness.

## Error Handling

Indexing errors are non-fatal at the individual package and bundle level:

| Error | Behavior |
|-------|----------|
| `METHODS.toml` missing or invalid | Skip the package. Log a warning. |
| Individual `.mthds` file fails to parse | Skip the bundle. Index remaining bundles. Log a warning. |
| Concept `refines` target unresolvable | Set `refines` to null. Log a warning. |
| Pipe input/output concept unresolvable | Exclude the pipe from the graph. Log a warning. |
| Git clone fails | Skip the package. Log a warning. |

A registry MUST NOT stop its indexing run because of errors in individual packages.

## See Also

- [The Registry](registry.md) — API endpoints for querying the index.
- [Registry Search](registry-search.md) — how the index and graph power type-aware queries.
- [The Know-How Graph](../know-how-graph/index.md) — conceptual overview of the typed network.
- [The Manifest](manifest.md) — the `METHODS.toml` fields that the registry parses.
