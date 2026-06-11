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
| `GET` | `/models` | The model deck this runner can route to: presets, aliases, waterfalls. Optional `?type=` filter (`llm` · `extract` · `img_gen` · `search`). |
| `GET` | `/version` | Always public. Protocol and implementation versions — the handshake clients use for feature detection. |

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

The 200 response is a `RunResult`: `pipeline_run_id`, `state`, `created_at`, `finished_at`, `main_stuff_name`, and `pipe_output` — the method's serialized output working memory, with the main output named by `main_stuff_name`.

The protocol sets no time limit on `/execute`; deployments cap it at their proxy layer. For long-running methods prefer `/start`. Implementations **MAY** answer `202 + StartAck` with a `Location` header pointing at an implementation-defined status resource when they cannot hold the connection open ([RFC 9110](https://www.rfc-editor.org/rfc/rfc9110#section-15.3.3) asynchronous pattern). Simple runners never emit 202; clients that cannot handle it should use `/start`.

## Starting a method asynchronously

`POST /start` accepts a `StartRequest` — a `RunRequest` plus one optional field:

- `pipeline_run_id` — a client-supplied run identifier for correlation or idempotency. The server generates one when absent. Implementations **MAY** decline client-supplied values, but **MUST** then reject the request with a 422 problem — never silently ignore it. The `pipeline_run_id` in the `StartAck` response is always authoritative.

The response is `202 + StartAck {pipeline_run_id, state, created_at}`.

### No run store, no completion channel

The protocol mandates no run store, and it defines **no completion channel for `/start`**: how a caller learns that an asynchronous run finished — webhooks, polling routes, anything else — is implementation-defined and outside the protocol (see [Extension policy](#extension-policy)). A bare runner is not required to answer "what happened to run X?" after the fact. Clients written against the protocol alone must rely on `/execute`'s response.

## Run states

`RunState` is a closed enum: `STARTED`, `RUNNING`, `COMPLETED`, `FAILED`, `CANCELLED`, `ERROR`.

## Validating a bundle

`POST /validate` takes `mthds_contents` (always an array, even for a single file) and an optional `allow_signatures` flag (default `false` — strict; when `true`, the validation sweep tolerates unimplemented pipe signatures by minting a mock). A valid bundle returns 200 with structural artifacts: the parsed `blueprint`, the method's `graph_spec`, and per-pipe `pipe_structures`. An invalid bundle is a 422 problem.

## Discovery

`GET /models` returns the runner's model deck — the models it can route to, their aliases, and routing waterfalls, optionally filtered by category.

`GET /version` is always public (no auth), and returns:

```json
{
  "protocol_version": "0.1.0",
  "implementation": "example-runner",
  "implementation_version": "2.3.0",
  "runtime_version": "1.8.1"
}
```

Clients use `/version` as the handshake: it identifies the implementation and lets clients detect vendor extensions before relying on them.

## Extension policy

Implementations may extend the surface — extra routes, extra optional request properties — but **must not change the meaning or shape of the protocol routes**. A client written against the MTHDS Protocol runs unmodified against any compliant runner; a vendor's superset may accept more, but never diverges on the surface defined here.

## Conformance

An implementation claiming conformance states it as: *implements MTHDS Protocol v0.1*. Conformance means: the five routes exist with the request/response shapes of [`mthds-protocol.openapi.yaml`](openapi/mthds-protocol.openapi.yaml), errors are RFC 7807 problems, `/version` is public, and a declined client `pipeline_run_id` is rejected with 422 rather than ignored.

## Route reference

Everything below is rendered at build time from the normative OpenAPI document — do not edit it by hand; edit [`mthds-protocol.openapi.yaml`](openapi/mthds-protocol.openapi.yaml).

[OAD(./openapi/mthds-protocol.openapi.yaml)]
