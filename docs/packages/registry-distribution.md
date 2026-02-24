---
description: "Registry distribution protocol for MTHDS — proxy chains, signed manifests, social signals, and multi-tier deployment."
---

# Registry Distribution Protocol

This page specifies how registries participate in the package distribution chain — acting as proxies, verifying package integrity, surfacing community signals, and supporting multi-tier deployment from local development to community-wide distribution.

## Proxy Chain

A client can be configured with an ordered list of registry URLs, analogous to Go's `GOPROXY` protocol. When resolving a package, the client queries registries in order:

```
MTHDS_REGISTRY=https://registry.example.com,https://community.mthds.ai,direct
```

| Entry | Behavior |
|-------|----------|
| A registry URL | Query the registry's `/v1/packages/{address}` endpoint. If the package is found, use it. If not (404), try the next entry. |
| `direct` | Bypass registries and fetch directly from the Git repository at the package address. |

The special value `direct` as the final entry ensures that packages not indexed by any registry can still be fetched from source. If `direct` is not present and no registry returns the package, resolution fails.

### Proxy Mode

A registry MAY operate in proxy mode, where it does not maintain its own index but forwards requests to an upstream registry and caches the results. A proxy registry:

- MUST forward the original request path and query parameters.
- MUST cache successful responses for a configurable duration.
- MUST forward `404 Not Found` without caching (the upstream may index the package later).
- SHOULD pass through the upstream's `Retry-After` headers on `429` responses.

### Mirror Mode

A registry MAY operate in mirror mode, where it maintains a full copy of another registry's index. A mirror registry:

- MUST periodically synchronize with the upstream registry.
- MUST serve requests from its local copy without forwarding.
- SHOULD expose a `last_synced_at` timestamp so clients can assess freshness.

## Signed Manifests

To ensure package integrity, a registry MAY require or serve **signed manifests**. A signed manifest binds the `METHODS.toml` content to a cryptographic signature.

### Signature Format

A signature is a detached JSON object:

```json
{
  "manifest_sha256": "a1b2c3d4e5f6...",
  "address": "github.com/acme/legal-tools",
  "version": "1.2.0",
  "signed_at": "2026-01-15T10:30:00Z",
  "signer": "acme-ci-bot",
  "algorithm": "ed25519",
  "public_key_id": "key-2026-01",
  "signature": "base64-encoded-signature..."
}
```

| Field | Description |
|-------|-------------|
| `manifest_sha256` | SHA-256 hash of the raw `METHODS.toml` file content. |
| `address` | Package address, matching the manifest. |
| `version` | Package version, matching the manifest. |
| `signed_at` | ISO 8601 timestamp of when the signature was created. |
| `signer` | Identifier of the signing entity (human or automation). |
| `algorithm` | Signature algorithm. MUST be `ed25519`. |
| `public_key_id` | Identifier for the public key used, for key rotation. |
| `signature` | Base64-encoded Ed25519 signature over the canonical representation of the preceding fields. |

### Verification

When verifying a signed manifest:

1. Compute the SHA-256 hash of the `METHODS.toml` file content.
2. Compare it against `manifest_sha256`.
3. Reconstruct the canonical signing payload (all fields except `signature`, serialized as sorted-key JSON with no whitespace).
4. Verify the Ed25519 signature against the payload using the public key identified by `public_key_id`.

A client SHOULD verify signatures when available. A client MUST NOT treat an unsigned package as verified.

### Trust Store

Public keys are stored in a trust store. A compliant runtime SHOULD support trust stores at two levels:

| Level | Location | Purpose |
|-------|----------|---------|
| **System** | `~/.mthds/trust/` | Keys trusted for all projects. |
| **Project** | `.mthds/trust/` in the project root | Keys trusted for this project only. |

Each key file is named `{public_key_id}.pub` and contains the raw Ed25519 public key in base64 encoding.

## Social Signals

A registry MAY track and expose social signals to help users evaluate packages:

| Signal | Description |
|--------|-------------|
| `install_count` | Number of times the package has been fetched through this registry. |
| `star_count` | Number of users who have starred the package. |
| `endorsed_by` | List of known organizations or users who endorse the package. |
| `last_updated` | Timestamp of the latest indexed version. |
| `indexed_at` | Timestamp of when the registry last crawled the package. |

Social signals are informational. They MUST NOT affect search ranking in type-compatible queries (which are purely type-driven). A registry MAY use social signals to influence text search ranking.

### Social Signals Endpoint

```
GET /v1/packages/{address}/signals
```

**Response:**

```json
{
  "address": "github.com/acme/legal-tools",
  "install_count": 1247,
  "star_count": 42,
  "endorsed_by": ["mthds-foundation"],
  "last_updated": "2026-01-15T10:30:00Z",
  "indexed_at": "2026-02-01T08:00:00Z"
}
```

## Multi-Tier Deployment

Registries support the same deployment tiers described in [Distribution](distribution.md):

### Local Tier

No registry involved. The CLI operates on the current project and its local cache (`~/.mthds/packages/`). Search and graph queries run against a locally-built index.

### Project Tier

A project team runs an internal registry indexing their shared packages. The registry URL is configured in the project's `.mthds/config.toml`:

```toml
[registry]
urls = ["https://registry.internal.acme.com"]
```

### Organization Tier

An organization runs a registry that acts as a proxy to the community registry, adding organization-specific packages and governance policies:

```
MTHDS_REGISTRY=https://registry.internal.acme.com,https://community.mthds.ai,direct
```

The internal registry can:

- Index private packages not available on the community registry.
- Enforce approval policies before indexing external packages.
- Cache community packages for air-gapped environments.

### Community Tier

A public registry indexes open-source packages from public Git repositories. Anyone can notify the registry of a new package address. The registry crawls and indexes it.

## Configuration

Registry URLs are resolved in this order of precedence:

1. **Environment variable**: `MTHDS_REGISTRY` (comma-separated list).
2. **Project config**: `.mthds/config.toml` `[registry].urls` array.
3. **User config**: `~/.mthds/config.toml` `[registry].urls` array.
4. **Default**: `direct` (no registry, fetch from Git directly).

## See Also

- [The Registry](registry.md) — API endpoints and schemas.
- [Registry Indexing](registry-indexing.md) — how registries build the index.
- [Distribution](distribution.md) — the federated storage model that registries build upon.
- [Version Resolution](version-resolution.md) — how version constraints are resolved.
