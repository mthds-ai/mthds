---
description: "The MTHDS Protocol — the minimal HTTP contract every MTHDS runner implements: execute, start, validate, models, version."
---

# HTTP Runner Protocol

The MTHDS Protocol is the minimal HTTP contract every MTHDS runner implements. Any server that serves these five routes with the shapes defined here is an MTHDS-compliant runner. A runner is just a runner: it executes methods, validates bundles, and reports what models it can route to and what version it is. It keeps no run store and owns no user, billing, or catalog concepts.

The normative artifact is the OpenAPI document: [`mthds-protocol.openapi.yaml`](openapi/mthds-protocol.openapi.yaml). This page walks through it in prose, then renders it route by route — every parameter, request body, and response schema — in the [route reference](#route-reference) below. Where prose and YAML disagree, the YAML wins.

## The five routes

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/execute` | Execute a method synchronously; the full output comes back in the response. |
| `POST` | `/start` | Start a method asynchronously; returns its `pipeline_run_id` immediately (202). Completion delivery is implementation-defined. |
| `POST` | `/validate` | Parse, validate, and dry-run an MTHDS bundle. |
| `GET` | `/models` | The models this runner can route to. Optional `?type=` filter (`llm` · `extract` · `img_gen` · `search`). |
| `GET` | `/version` | Always public. Protocol and runner versions — the handshake clients use for feature detection. |

All errors are [RFC 7807](https://www.rfc-editor.org/rfc/rfc7807) `application/problem+json` documents. Auth is implementation-defined: a bearer-token slot is reserved, and anonymous access is allowed for self-hosted runners.

## Base URL and versioning

Protocol paths are version-agnostic. The version segment belongs to the server base URL, chosen by the implementation:

```
http://localhost:8081/v1/execute
https://api.example.com/v1/execute
```

The protocol itself is versioned by this standard (`protocol_version` in `/version`); each implementation versions its own mount point. A client written against the protocol composes `{base_url}/{path}` and never inspects the base URL's structure.

## Executing a method

`POST /execute` is blocking: the response carries the method's full output. The request body is a `RunRequest`:

```json
{
  "pipe_code": "analyze_contract",
  "mthds_contents": ["domain = \"legal\"\n..."],
  "inputs": {
    "contract": { "concept": "Document", "content": { "file_path": "..." } }
  }
}
```

At least one of `pipe_code` / `mthds_contents` is required. If `mthds_contents` is provided without `pipe_code`, the first bundle must declare a `main_pipe`. Optional fields: `output_name`, `output_multiplicity`, `dynamic_output_concept_ref`.

The 200 response is a `RunResultExecute` — the completed run, holding two base fields: `pipeline_run_id` (mandatory, server-generated and authoritative) and `pipe_output` (the method's serialized output; always present — a completed run has output). Anything more an implementation returns — a run state, timestamps, output naming, anything else — is an extension field (see [Extension policy](#extension-policy)), declared and documented by that implementation.

The protocol sets no time limit on `/execute`; deployments cap it at their proxy layer. For long-running methods prefer `/start`. Implementations **MAY** answer `202 + RunResultStart` (just the run id, no output yet) with a `Location` header pointing at an implementation-defined status resource when they cannot hold the connection open ([RFC 9110](https://www.rfc-editor.org/rfc/rfc9110#section-15.3.3) asynchronous pattern). Simple runners never emit 202; clients that cannot handle it should use `/start`.

## Starting a method asynchronously

`POST /start` accepts the same `RunRequest` body as `/execute` — the protocol declares no start-only request fields. Anything an implementation accepts on top (a client-supplied run identifier, anything else) is an extension arg (see [Extension policy](#extension-policy)), defined and documented by that implementation.

The response is `202 + RunResultStart` — just the authoritative server-generated `pipeline_run_id` (plus any implementation extension fields). A started run has no output yet.

### No run store, no completion channel

The protocol mandates no run store, and it defines **no completion channel for `/start`**: how a caller learns that an asynchronous run finished — webhooks, polling routes, anything else — is implementation-defined and outside the protocol (see [Extension policy](#extension-policy)). A bare runner is not required to answer "what happened to run X?" after the fact. Clients written against the protocol alone must rely on `/execute`'s response.

## Validating a bundle

`POST /validate` takes `mthds_contents` (always an array, even for a single file) and an optional `allow_signatures` flag (default `false` — strict; when `true`, the validation sweep tolerates unimplemented pipe signatures by minting a mock).

`/validate` is a **diagnostic endpoint**: its job is to return a *verdict* about the submitted bundle, and every verdict it can produce — valid or invalid — rides a **200**, discriminated in the body on the mandatory `is_valid` field.

- **`is_valid: true`** — the bundle is valid. The protocol declares the `is_valid` discriminant plus the runnability facts (`is_runnable`, and `pending_signatures` — refs of pipes still declared as unimplemented signatures); implementations MAY include their own artifacts (parsed structures, graphs, anything else) as additional properties.
- **`is_valid: false`** — the bundle is invalid. The body carries `validation_errors[]` (a non-empty list of structured diagnostics, each at least a `category` and a `message`) plus `is_runnable: false` and an optional `message`. The structural artifacts of a valid report are absent.

A client pattern-matches `is_valid` to learn the verdict — it never inspects a status code or catches an exception body. Non-2xx is reserved for the cases where **no verdict could be produced**: a malformed request body is a `422` problem, auth a `401`/`403`, a server fault a `5xx`. So a non-2xx on `/validate` always means "the endpoint could not produce a verdict," never "your bundle is bad" — which keeps expected validation failures out of the 4xx error budget and never editorializes a verdict into a spurious retry. Signatures are never an error: an unimplemented signature reached during validation is a *runnability fact* (`is_runnable: false` + `pending_signatures`), not a validation failure, and `allow_signatures` only affects the dry-run sweep, not the verdict.

## Discovery

`GET /models` returns the runner's model deck — the models it can route to (`{name, type}` entries), optionally filtered by category. Implementations may add their own routing metadata (aliases, fallback chains, anything else) as additional properties.

`GET /version` is always public (no auth). It returns `protocol_version` (required) and an optional `runner_version` — implementations may add their own identification on top:

```json
{
  "protocol_version": "0.6.0",
  "runner_version": "2.3.0"
}
```

Clients use `/version` as the handshake: it reports the protocol and runner versions, and any additional properties let clients detect vendor extensions before relying on them.

## Extension policy

Implementations may extend the surface — extra routes, extra optional request properties, extra response properties — but **must not change the meaning or shape of the protocol routes**. Both sides of the wire are extension-open: request bodies accept implementation-defined args, and the protocol's response schemas declare only the base fields (`additionalProperties` allowed). A client written against the MTHDS Protocol runs unmodified against any compliant runner; a vendor's superset may accept and return more, but never diverges on the surface defined here.

## Conformance

An implementation claiming conformance states it as: *implements MTHDS Protocol v0.1*. Conformance means: the five routes exist with the request/response shapes of [`mthds-protocol.openapi.yaml`](openapi/mthds-protocol.openapi.yaml), errors are RFC 7807 problems, and `/version` is public.

## Route reference

Everything below is rendered at build time from the normative OpenAPI document — do not edit it by hand; edit [`mthds-protocol.openapi.yaml`](openapi/mthds-protocol.openapi.yaml).

[OAD(./openapi/mthds-protocol.openapi.yaml)]
