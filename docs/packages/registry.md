---
description: "Specification of the MTHDS registry — the HTTP index that powers package discovery, package pages, validation badges, and freshness signals."
---

# The Registry

!!! note "Implementation status"
    An early beta of the MTHDS registry is available at [mthds.sh](https://mthds.sh). This page specifies the index surface a registry serves; more ambitious registry capabilities — typed signature search, graph queries, signed manifests, proxy chains — are preserved as [future directions](future-directions.md) and are not part of the specified system.

A **registry** is an HTTP service that indexes MTHDS packages and exposes them for discovery. Registries do not host package source code — they index metadata from Git-hosted packages and serve it through a structured API.

## Role in the Ecosystem

The [distribution model](distribution.md) separates storage from discovery:

- **Storage** remains decentralized — packages live in Git repositories controlled by their authors.
- **Discovery** is centralized per registry — a registry crawls known package addresses, builds an index, and serves queries over HTTP.

**The registry is off the install path — a design guarantee.** [Version resolution](version-resolution.md) is deterministic from manifests alone and packages are fetched straight from their repositories, so bare Git access suffices to resolve, lock, and install. A registry adds discovery, social proof, and freshness signals on top; it is never load-bearing infrastructure for running or installing a method.

Multiple registries can coexist, each with its own crawl set and policies.

## API Versioning

All endpoints are prefixed with `/v1/`. The version number increments only for breaking changes. Non-breaking additions (new optional fields, new endpoints) do not require a version bump.

```
https://registry.example.com/v1/packages
```

## The Index Entry

The unit a registry serves is the `PackageIndexEntry` — the parsed identity, contents, and signals of one package at its indexed version:

| Field | Type | Description |
|-------|------|-------------|
| `address` | string | The package address (see [The Manifest](manifest.md)). |
| `name` | string | The package's `name` from the manifest. |
| `display_name` | string or null | The human-friendly label from the manifest, when present. |
| `version` | string | The indexed version (the latest stable tag at crawl time). |
| `main_pipe` | string or null | The package's entry-point pipe, when declared. |
| `description` | string | The manifest description. |
| `authors` | list of strings | Package authors. |
| `license` | string or null | SPDX license identifier. |
| `domains` | list of domain entries | The domains the package's bundles declare. |
| `concepts` | list of concept entries | The concepts the package declares (see [Registry Indexing](registry-indexing.md)). |
| `pipes` | list of pipe signatures | The pipes the package declares, with export status. |
| `dependencies` | list of addresses | The addresses the package depends on. |
| `dependency_aliases` | map of alias to address | The package's declared dependency aliases. |
| `validation` | validation record or null | The registry's validation verdict for this indexed version, when the registry validates (see [Validation Badges](#validation-badges)). |
| `indexed_at` | timestamp | When the registry last crawled the package. |

## Endpoints

### List Packages

```
GET /v1/packages?offset=0&limit=20
```

Returns a paginated list of indexed packages. Each item carries the identity subset of the index entry:

```json
{
  "items": [
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
      ]
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

Returns the full `PackageIndexEntry` for a single package — the data behind a package page: identity, entry point, domains, concepts, pipe signatures with export status, dependencies, validation, and freshness.

### Text Search

```
GET /v1/search?q=contract&type=concept&domain=legal.contracts&offset=0&limit=20
```

**Query parameters:**

| Parameter | Required | Description |
|-----------|----------|-------------|
| `q` | Yes | Search term. Case-insensitive substring match against package names, concept codes, pipe codes, descriptions, and domain codes. |
| `type` | No | Filter by entity type: `concept`, `pipe`, or omit for both. |
| `domain` | No | Filter results to a specific domain code. |
| `offset` | No | Pagination offset. Default: `0`. |
| `limit` | No | Page size. Default: `20`. Maximum: `100`. |

Each result names the entity, its kind, its package address, and its description, so a client can present a hit and link to the package page.

Search by *typed signature* — "find pipes that accept this concept and produce that one" — is a [future direction](future-directions.md), not part of the specified surface.

### Package Signals

```
GET /v1/packages/{address}/signals
```

Returns the social and freshness signals for a package:

```json
{
  "address": "github.com/acme/legal-tools",
  "install_count": 1247,
  "star_count": 42,
  "latest_version": "1.4.0",
  "last_updated": "2026-08-15T10:30:00Z",
  "indexed_at": "2026-08-20T08:00:00Z"
}
```

| Signal | Description |
|--------|-------------|
| `install_count` | Number of installs the registry has observed. |
| `star_count` | Number of users who have starred the package. |
| `latest_version` | The newest published version the registry has seen — beside a consumer's resolved version, this is the freshness signal that prompts a deliberate [update](version-resolution.md#adding-and-updating-deliberate-adoption). |
| `last_updated` | Timestamp of the latest indexed version. |
| `indexed_at` | When the registry last crawled the package. |

Social signals are informational and MAY influence text search ranking. A registry SHOULD expose `indexed_at` so clients can assess staleness.

## Validation Badges

A registry MAY validate the packages it indexes — loading each package and checking it against the standard's [validation rules](../implementers/validation-rules.md), optionally exercising its entry pipe — and surface the verdict as a **validation badge** on the package page. When it does:

- The validation record MUST name the version (and SHOULD name the commit) it validated, so the badge is a statement about a specific published state, never a floating claim.
- A failed validation MUST be distinguishable from an unvalidated package.

Because installs reproduce the resolved closure deterministically (MVS + the lock), a badge earned by a validated version remains honest for every consumer who installs that version.

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
| `429` | `rate_limited` | Too many requests. |
| `500` | `internal_error` | Unexpected server error. |

## Content Type

All responses use `Content-Type: application/json; charset=utf-8`. A registry MUST return JSON for all API endpoints. A registry MUST set the `Content-Type` header on every response.

## See Also

- [Registry Indexing](registry-indexing.md) — how registries crawl and index packages.
- [Future Directions](future-directions.md) — typed search, the Know-How Graph, signed manifests, and proxy chains.
- [Distribution](distribution.md) — the federated model that registries build upon.
