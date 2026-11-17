# Registry Indexing

A registry builds its index by crawling Git-hosted packages and parsing their manifests and bundles into `PackageIndexEntry` records. This page specifies the indexing pipeline.

## Indexing Pipeline

The indexing pipeline transforms a package address into a `PackageIndexEntry`:

```
address → git clone → parse METHODS.toml → scan .mthds files → PackageIndexEntry
```

### Step 1: Clone the Repository

The registry resolves the package address to a Git clone URL per the [distribution rules](distribution.md#clone-url-derivation): the hostname and first two path segments name the repository, prefixed with `https://` and suffixed with `.git`.

```
github.com/acme/legal-tools → https://github.com/acme/legal-tools.git
```

The registry MUST use `git ls-remote --tags` to enumerate available version tags before cloning. Only tags that parse as valid [semantic versions](version-resolution.md) are considered. Both `v`-prefixed (e.g., `v1.0.0`) and bare (e.g., `1.0.0`) tags are recognized.

The registry clones at the **latest stable version tag** using `git clone --depth 1 --branch {tag}`.

!!! note "Crawl-at-latest is not resolution"
    The registry indexes the *newest* published state so that discovery reflects what a package has become — the opposite selection rule from [version resolution](version-resolution.md), which picks the *minimum* version satisfying the declared floors. The two rules serve different questions: "what is this package now?" (index) versus "what did dependents ask for?" (resolution). A registry surfaces the gap between them as a freshness signal (`latest_version` beside a consumer's resolved version), never by influencing resolution — the registry is [off the install path](registry.md#role-in-the-ecosystem).

### Step 2: Parse the Manifest

The registry reads `METHODS.toml` from the package root (for a library repository, one entry per contained package, each located by [manifest identity](distribution.md#locating-a-package-inside-a-clone)). This provides:

| Field | Type | Description |
|-------|------|-------------|
| `address` | `string` | Package address (e.g., `github.com/acme/legal-tools`). |
| `name` | `string` | The package name. |
| `display_name` | `string \| null` | Human-friendly label, when present. |
| `version` | `string` | Semantic version (e.g., `1.2.0`). |
| `main_pipe` | `string \| null` | The package's entry-point pipe, when declared. |
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

The `concept_ref` is always `{domain_code}.{concept_code}`. The `refines` field is the raw string from the bundle.

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

The `is_exported` flag reflects the package's export surface: a pipe is exported when it appears in the manifest's `[exports]` for its domain, or when it is auto-exported as a `main_pipe` (see [Exports & Visibility](exports-visibility.md)).

!!! warning "Open question: the no-exports default at the index edge"
    Historically, indexers have treated a package with no `[exports]` section as all-public, while the manifest's own default is pipes-private (only auto-exported main pipes are visible). Which default the index should present for an exports-less manifest is an open question of the standard — deliberately recorded here rather than silently decided by an implementation.

### Step 4: Assemble the Index Entry

The registry assembles a `PackageIndexEntry` from the parsed manifest and scanned bundles — the full field set is specified in [The Registry: The Index Entry](registry.md#the-index-entry):

```json
{
  "address": "github.com/acme/legal-tools",
  "name": "legal_tools",
  "display_name": "Legal Tools",
  "version": "1.2.0",
  "main_pipe": "analyze_nda",
  "description": "Contract analysis and clause extraction methods",
  "authors": ["Acme Legal Team"],
  "license": "Apache-2.0",
  "domains": [
    { "domain_code": "legal.contracts", "description": "Contract processing domain" }
  ],
  "concepts": [ "..." ],
  "pipes": [ "..." ],
  "dependencies": ["github.com/mthds/document-processing"],
  "dependency_aliases": { "doc_processing": "github.com/mthds/document-processing" },
  "indexed_at": "2026-08-20T08:00:00Z"
}
```

The `dependencies` list contains raw addresses. The `dependency_aliases` map aliases to addresses, so a package page can render the dependency graph as authored.

Domains are sorted alphabetically by `domain_code`. Parse errors in individual bundles are logged as warnings — a single broken bundle MUST NOT prevent the rest of the package from being indexed.

### Step 5: Validate (Optional)

A registry MAY validate the indexed package — run the standard's [validation rules](../implementers/validation-rules.md) over the manifest and bundles, optionally exercising its entry pipe — and attach the verdict to the entry as a validation record naming the validated version. See [Validation Badges](registry.md#validation-badges).

## The Package Index

The `PackageIndex` is the collection of all `PackageIndexEntry` records, keyed by address:

```json
{
  "entries": {
    "github.com/acme/legal-tools": { "...": "..." },
    "github.com/mthds/document-processing": { "...": "..." }
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

Building a typed graph over the index — refinement edges, data-flow edges, chain queries — is a [future direction](future-directions.md), not part of the specified indexing pipeline.

## Index Refresh

A registry MUST support at least one mechanism for keeping the index current:

- **Manual trigger** — an API call or administrative action that re-indexes a specific package address.
- **Polling** — periodic re-crawl of known package addresses, comparing the latest version tag against the indexed version.
- **Webhook** — a Git hosting webhook (e.g., GitHub push event) that triggers re-indexing when a new tag is pushed.

A registry SHOULD expose the index freshness for each package (the `indexed_at` timestamp) so that clients can assess staleness.

## Error Handling

Indexing errors are non-fatal at the individual package and bundle level:

| Error | Behavior |
|-------|----------|
| `METHODS.toml` missing or invalid | Skip the package. Log a warning. |
| Individual `.mthds` file fails to parse | Skip the bundle. Index remaining bundles. Log a warning. |
| Git clone fails | Skip the package. Log a warning. |

A registry MUST NOT stop its indexing run because of errors in individual packages.

## See Also

- [The Registry](registry.md) — API endpoints for querying the index.
- [Future Directions](future-directions.md) — typed search, graph construction, signed manifests, and proxy chains.
- [Distribution](distribution.md) — clone URL derivation and package location.
- [The Manifest](manifest.md) — the `METHODS.toml` fields that the registry parses.
