# The Registry

A **registry** is an HTTP service that indexes MTHDS packages and exposes them for discovery. Registries do not host package source code — they index metadata from Git-hosted packages and serve it through a structured API.

## Role in the Ecosystem

The [distribution model](distribution.md) separates storage from discovery:

- **Storage** remains decentralized — packages live in Git repositories controlled by their authors.
- **Discovery** is centralized per registry — a registry crawls known package addresses, builds an index, constructs the [Know-How Graph](../know-how-graph/index.md), and serves queries over HTTP.

Multiple registries can coexist. A client can query several registries in order (analogous to Go's `GOPROXY` chain), falling back from one to the next.

## API Versioning

All endpoints are prefixed with `/v1/`. The version number increments only for breaking changes. Non-breaking additions (new optional fields, new endpoints) do not require a version bump.

```
https://registry.example.com/v1/packages
```

## Endpoints

### List Packages

```
GET /v1/packages?offset=0&limit=20
```

Returns a paginated list of indexed packages.

**Response:**

```json
{
  "items": [
    {
      "address": "github.com/acme/legal-tools",
      "version": "1.2.0",
      "description": "Contract analysis and clause extraction methods",
      "authors": ["Acme Legal Team"],
      "license": "Apache-2.0",
      "domains": [
        { "domain_code": "legal.contracts", "description": "Contract processing domain" }
      ],
      "concept_count": 5,
      "pipe_count": 8,
      "dependency_count": 2
    }
  ],
  "total": 47,
  "offset": 0,
  "limit": 20
}
```

### Get Package Detail

```
GET /v1/packages/{address}
```

The `{address}` path parameter is the full package address, URL-encoded where necessary (e.g., `github.com%2Facme%2Flegal-tools`).

Returns the full `PackageIndexEntry` for a single package.

**Response:**

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
  "concepts": [
    {
      "concept_code": "ContractClause",
      "domain_code": "legal.contracts",
      "concept_ref": "legal.contracts.ContractClause",
      "description": "A single clause extracted from a contract",
      "refines": "native.Text",
      "structure_fields": ["clause_type", "text", "section_number"]
    }
  ],
  "pipes": [
    {
      "pipe_code": "extract_clause",
      "pipe_type": "PipeLLM",
      "domain_code": "legal.contracts",
      "description": "Extract a specific clause from a contract document",
      "input_specs": { "source": "ContractDocument" },
      "output_spec": "ContractClause",
      "is_exported": true
    }
  ],
  "dependencies": ["github.com/mthds/document-processing"],
  "dependency_aliases": { "doc_processing": "github.com/mthds/document-processing" }
}
```

### Text Search

```
GET /v1/search?q=contract&type=concept&domain=legal.contracts&offset=0&limit=20
```

**Query parameters:**

| Parameter | Required | Description |
|-----------|----------|-------------|
| `q` | Yes | Search term. Case-insensitive substring match against concept codes, pipe codes, descriptions, and domain codes. |
| `type` | No | Filter by entity type: `concept`, `pipe`, or omit for both. |
| `domain` | No | Filter results to a specific domain code. |
| `offset` | No | Pagination offset. Default: `0`. |
| `limit` | No | Page size. Default: `20`. Maximum: `100`. |

**Response:**

```json
{
  "items": [
    {
      "kind": "concept",
      "package_address": "github.com/acme/legal-tools",
      "concept_code": "ContractClause",
      "domain_code": "legal.contracts",
      "description": "A single clause extracted from a contract",
      "refines": "native.Text"
    },
    {
      "kind": "pipe",
      "package_address": "github.com/acme/legal-tools",
      "pipe_code": "extract_clause",
      "pipe_type": "PipeLLM",
      "domain_code": "legal.contracts",
      "description": "Extract a specific clause from a contract document",
      "input_specs": { "source": "ContractDocument" },
      "output_spec": "ContractClause",
      "is_exported": true
    }
  ],
  "total": 2,
  "offset": 0,
  "limit": 20
}
```

### Type-Compatible Search

```
GET /v1/search/typed?accepts=Document&produces=ContractClause
```

Finds pipes by their typed signatures, using the [Know-How Graph](../know-how-graph/index.md) to resolve concept compatibility through refinement chains.

**Query parameters:**

| Parameter | Required | Description |
|-----------|----------|-------------|
| `accepts` | No | Concept code or reference. Finds pipes that accept this concept as input (including concepts that this one refines). |
| `produces` | No | Concept code or reference. Finds pipes that produce this concept as output (including concepts that refine this one). |
| `offset` | No | Pagination offset. Default: `0`. |
| `limit` | No | Page size. Default: `20`. Maximum: `100`. |

At least one of `accepts` or `produces` MUST be provided.

**Response:**

```json
{
  "items": [
    {
      "package_address": "github.com/acme/legal-tools",
      "pipe_code": "extract_clause",
      "pipe_type": "PipeLLM",
      "domain_code": "legal.contracts",
      "description": "Extract a specific clause from a contract document",
      "input_specs": { "source": "ContractDocument" },
      "output_spec": "ContractClause",
      "is_exported": true
    }
  ],
  "total": 1,
  "offset": 0,
  "limit": 20
}
```

### Graph Chain Query

```
GET /v1/graph/chains?from={concept_id}&to={concept_id}&max_depth=3
```

Finds multi-step pipe chains that transform one concept into another, using BFS traversal of the Know-How Graph.

**Query parameters:**

| Parameter | Required | Description |
|-----------|----------|-------------|
| `from` | Yes | Source concept ID in `package_address::concept_ref` format (e.g., `__native__::native.Document`). |
| `to` | Yes | Target concept ID in `package_address::concept_ref` format. |
| `max_depth` | No | Maximum number of pipes in a chain. Default: `3`. |

**Response:**

```json
{
  "chains": [
    {
      "steps": [
        {
          "pipe_key": "github.com/acme/legal-tools::extract_pages",
          "pipe_code": "extract_pages",
          "package_address": "github.com/acme/legal-tools",
          "input_specs": { "source": "Document" },
          "output_spec": "PageContent"
        },
        {
          "pipe_key": "github.com/acme/legal-tools::extract_clause",
          "pipe_code": "extract_clause",
          "package_address": "github.com/acme/legal-tools",
          "input_specs": { "source": "PageContent" },
          "output_spec": "ContractClause"
        }
      ]
    }
  ],
  "from": "__native__::native.Document",
  "to": "github.com/acme/legal-tools::legal.contracts.ContractClause"
}
```

Chains are sorted shortest-first. If no chain exists within `max_depth`, the `chains` array is empty.

### Compatibility Check

```
GET /v1/graph/compatibility?source={pipe_key}&target={pipe_key}
```

Checks whether the output of one pipe is type-compatible with an input of another.

**Query parameters:**

| Parameter | Required | Description |
|-----------|----------|-------------|
| `source` | Yes | Source pipe key in `package_address::pipe_code` format. |
| `target` | Yes | Target pipe key in `package_address::pipe_code` format. |

**Response:**

```json
{
  "compatible": true,
  "compatible_params": ["source"],
  "source_output": "ContractClause",
  "target_inputs": { "source": "Text", "context": "AnalysisContext" }
}
```

The `compatible_params` array lists the target pipe's input parameter names that can accept the source pipe's output. An empty array means the pipes are incompatible.

## Pagination

All list endpoints use offset-based pagination:

| Field | Description |
|-------|-------------|
| `offset` | Number of items to skip. Default: `0`. |
| `limit` | Maximum items per page. Default: `20`. Maximum: `100`. |
| `total` | Total number of matching items (returned in every response). |

A registry MUST return a `total` field in paginated responses. Clients SHOULD use `total` to determine whether more pages exist.

## Authentication

A registry MAY require authentication. When authentication is required:

- The registry MUST accept a Bearer token in the `Authorization` header.
- The registry MUST return `401 Unauthorized` for requests that require authentication but lack a valid token.
- The registry MUST return `403 Forbidden` for requests with a valid token that lacks the required scope.

```
Authorization: Bearer <token>
```

Token provisioning is outside the scope of this specification. Registries may use API keys, OAuth tokens, or any scheme that produces a Bearer token.

## Rate Limiting

A registry SHOULD enforce rate limits to ensure fair use. When rate-limited:

- The registry MUST return `429 Too Many Requests`.
- The registry SHOULD include a `Retry-After` header with the number of seconds to wait.

## Error Format

All error responses use a consistent JSON format:

```json
{
  "error": {
    "code": "not_found",
    "message": "Package 'github.com/acme/unknown' is not indexed by this registry."
  }
}
```

**Standard error codes:**

| HTTP Status | Error Code | Description |
|-------------|------------|-------------|
| `400` | `bad_request` | Malformed query parameters or missing required fields. |
| `401` | `unauthorized` | Missing or invalid authentication token. |
| `403` | `forbidden` | Valid token but insufficient permissions. |
| `404` | `not_found` | Package or resource not found in the index. |
| `422` | `invalid_concept` | Concept ID format is invalid or concept not found in the graph. |
| `429` | `rate_limited` | Too many requests. |
| `500` | `internal_error` | Unexpected server error. |

## Content Type

All responses use `Content-Type: application/json; charset=utf-8`. A registry MUST return JSON for all API endpoints. A registry MUST set the `Content-Type` header on every response.

## See Also

- [Registry Indexing](registry-indexing.md) — how registries crawl and index packages.
- [Registry Search](registry-search.md) — type-aware search semantics and graph query rules.
- [Registry Distribution Protocol](registry-distribution.md) — proxy chains, signed manifests, and multi-tier deployment.
- [Distribution](distribution.md) — the federated model that registries build upon.
- [The Know-How Graph](../know-how-graph/index.md) — the typed network that powers registry search.
