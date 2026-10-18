# HTTP Runner Protocol

The MTHDS Protocol is the minimal HTTP contract every MTHDS runner implements. Any server that serves its five required routes with the shapes defined here is an MTHDS-compliant runner. A runner that keeps a blob store also serves the optional blob routes, and one that keeps a run store also serves the optional run reads and honours idempotency keys. A runner is just a runner: it executes methods, validates bundles, and reports what models it can route to and what version it is. The protocol requires no run store of it, and it owns no user, billing, or catalog concepts.

The normative artifact is the OpenAPI document: [`mthds-protocol.openapi.yaml`](openapi/mthds-protocol.openapi.yaml). This page walks through it in prose, then renders it route by route — every parameter, request body, and response schema — in the [route reference](#route-reference) below. Where prose and YAML disagree, the YAML wins.

## The routes

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/execute` | Execute a method synchronously; the full output comes back in the response. |
| `POST` | `/start` | Start a method asynchronously; returns its `pipeline_run_id` immediately (202). Completion delivery is implementation-defined. |
| `POST` | `/validate` | Parse, validate, and dry-run an MTHDS bundle. |
| `GET` | `/models` | The models this runner can route to. Optional `?type=` filter on the [model category](#model-categories) (`llm` · `extract` · `img_gen` · `search` · `judgment`). |
| `GET` | `/version` | Always public. Protocol and runner versions — the handshake clients use for feature detection. |
| `POST` | `/blobs/missing` | Optional, served by a runner that keeps a [blob store](#sending-files-by-hash). Which of the listed blobs the runner lacks, and where to upload each. |
| `PUT` | `/blobs/{sha256}` | Optional. Uploads one blob's bytes to a runner that stores them itself. |
| `GET` | `/runs/{pipeline_run_id}/status` | Optional, served by a runner that keeps a [run store](#reading-a-run-and-idempotency-keys). A run's status, and its problem once it has failed. |
| `GET` | `/runs/{pipeline_run_id}/results` | Optional. A completed run's output, as `/execute` answers it. |

The first five routes are required of every runner. The blob routes are served by a runner whose `/version` declares `blob_store: true`, and `PUT /blobs/{sha256}` only by one that stores uploaded bytes itself rather than pointing its senders at another upload target. The run reads are served by a runner whose `/version` declares `run_store: true`, which also honours an `Idempotency-Key` header on `/execute` and `/start`.

Every error is a problem document of [RFC 9457](https://www.rfc-editor.org/rfc/rfc9457), served as `application/problem+json`, that carries the MTHDS core members described under [Errors](#errors). Auth is implementation-defined: a bearer-token slot is reserved, and anonymous access is allowed for self-hosted runners.

## Base URL and versioning

Protocol paths are version-agnostic. The version segment belongs to the server base URL, chosen by the implementation:

```
http://localhost:8081/v1/execute
https://api.example.com/v1/execute
```

The protocol itself is versioned by this standard (`protocol_version` in `/version`), on its own cadence and independently of the [standard version](./versioning.md); each implementation versions its own mount point. A client written against the protocol composes `{base_url}/{path}` and never inspects the base URL's structure.

## Executing a method

`POST /execute` is blocking: the response carries the method's full output. The request body is a `RunRequest`:

```json
{
  "pipe_code": "analyze_contract",
  "files": {
    "METHODS.toml": "[package]\nname = \"contract_review\"\n...",
    "contracts.mthds": "domain = \"legal\"\n...",
    "templates/report.html": "<html>...",
    "templates/logo.png": { "base64": "iVBORw0KGgo..." }
  },
  "inputs": {
    "contract": { "concept": "native.Document", "content": { "url": "..." } }
  }
}
```

`files` carries the method: its whole [method tree](./method-tree.md), as a map from tree path to file entry (see [Method files](#method-files) below). At least one of `pipe_code` / `files` is required, and `pipe_code` alone names a pipe the runner already holds. When `files` is given without `pipe_code`, the run starts at the manifest's `main_pipe` when the tree holds a `METHODS.toml` at its root, or else, in a method with no manifest, at the one `main_pipe` its bundles declare. A tree whose manifest declares no `main_pipe`, or with no manifest whose bundles declare none or several, is refused with a `422` naming its bundles by their tree paths. Optional fields: `output_name`, `output_multiplicity`, `dynamic_output_concept_ref`. Each input is a stuff in the wire form the [CLI I/O Contract](./cli-io-contract.md#stuffs-on-the-wire) defines: `concept` names the concept by its crate key, as a string, and `content` is its value.

The 200 response is a `RunResultExecute` — the completed run, holding two base fields: `pipeline_run_id` (mandatory, server-generated and authoritative) and `pipe_output` (the method's serialized output; always present — a completed run has output, either a value or an explicit absence document). Anything more an implementation returns — a run state, timestamps, output naming, anything else — is an extension field (see [Extension policy](#extension-policy)), declared and documented by that implementation.

`pipe_output` is a working memory of stuffs in the same wire form as the inputs, and it carries references only: a concept's definition never travels in a working memory. A client that needs the structure behind a `concept` resolves the key against the library crate, or reads it from the `pipe_io_contracts` a validating runner reports. The stuff's shape is the standard's, not the protocol's: the OpenAPI document types an input's `concept` as a string and leaves `pipe_output` an open object, the CLI I/O Contract fixes what its entries look like, and a change to that shape moves the [standard version](./versioning.md#the-protocol-version) and no protocol number — the way the recommended extension fields of the validate report are shaped by their own pages.

The protocol sets no time limit on `/execute`; deployments cap it at their proxy layer. For long-running methods prefer `/start`. Implementations **MAY** answer `202 + RunResultStart` (just the run id, no output yet) with a `Location` header pointing at an implementation-defined status resource when they cannot hold the connection open ([RFC 9110](https://www.rfc-editor.org/rfc/rfc9110#section-15.3.3) asynchronous pattern). A runner that keeps a run store points it at the run's [status read](#get-runspipeline_run_idstatus) and keeps the run's output for its results read. Simple runners never emit 202; clients that cannot handle it should use `/start`.

### Method files

A request's `files` map holds every file of the method's tree under its [tree path](./method-tree.md#tree-paths): its bundles, its manifest when it has one, and every other file a step may read or that travels with the method, such as a Python module, a template, an image or a `requirements.txt`. Each value is a [file entry](./method-tree.md#the-file-entry) in one of three forms:

- **a string**, the file's text, whose bytes are its UTF-8 encoding;
- **`{ "base64": "…" }`**, any bytes, in standard padded Base64, canonical, with its pad bits zero;
- **`{ "sha256": "…", "size": … }`**, bytes the runner already holds in its blob store, named by their SHA-256 in lowercase hexadecimal and their length, a JSON integer written without a fraction or an exponent.

The map must form a tree. A runner refuses with a `422` naming the offending path a map in which:

- a key is not a tree path, such as a key not already in NFC, which a runner refuses rather than normalize, or names a file the membership rule could never admit, such as a dotfile or a run's inputs file, named `inputs.json` or `inputs.toml` at any depth;
- one path is given twice, as written or once its JSON escapes are decoded, or an entry object gives one of its own keys twice;
- two paths [collide](./method-tree.md#tree-paths), or one collides with a directory of another, under the Unicode full case folding the method tree defines, such as `readme.md` beside `README.md`, `STRASSE.txt` beside `straße.txt`, or `Templates` beside `templates/letter.html`;
- an entry is malformed, such as Base64 whose pad bits are not zero, or a `size` written `13.0`.

A hash entry resolves only in the runner's own blob store, and only when the runner holds those bytes at the stated size. A runner without a blob store, or one that does not hold every hash a request names, answers with a `422` problem coded `request.blobs_missing`, whose `params.missing_blobs` lists, in lowercase hexadecimal, each hash it does not hold, so a sender learns in one answer which files to supply:

```json
{
  "type": "https://mthds.ai/errors/request.blobs_missing",
  "title": "The runner does not hold some files sent by hash",
  "status": 422,
  "detail": "This runner does not hold a file the request sends by hash.",
  "code": "request.blobs_missing",
  "domain": "input",
  "retry": "no",
  "next_step": {
    "kind": "change_input",
    "detail": "Upload each listed blob, or send its file inline if this runner keeps no blob store, then send the request again."
  },
  "params": {
    "missing_blobs": ["3e9b68b71cc667168399f0bccfb64b2d16314cdc0ed78fac4819aba0dda121a0"]
  }
}
```

Supplying the listed files and sending the request again is a change to the request, so the step is `change_input`. A sender uploads each listed blob to a runner that keeps a blob store, as [Sending files by hash](#sending-files-by-hash) describes, and sends each listed file inline to a runner whose `GET /version` does not declare `blob_store: true`, since such a runner serves no upload route. The tree's files are the method's own: a file a caller supplies for one run is an input, never an entry of `files`.

A runner reads a method only from the files it is sent. A [file reference](./method-tree.md#file-references) resolves in the tree's set of paths and a hash in the blob store, so no request names a path on the runner's own disk. Each implementation bounds a file's size, the tree's file count and its total size, and the total of the inline entries, and refuses a tree past one of them with a problem naming the limit.

## Starting a method asynchronously

`POST /start` accepts the same `RunRequest` body as `/execute` — the protocol declares no start-only request fields. Anything an implementation accepts on top (a client-supplied run identifier, anything else) is an extension arg (see [Extension policy](#extension-policy)), defined and documented by that implementation.

The response is `202 + RunResultStart` — just the authoritative server-generated `pipeline_run_id` (plus any implementation extension fields). A started run has no output yet.

### No run store, no completion channel

The protocol mandates no run store, and it defines **no completion channel for `/start`**: nothing tells a caller that an asynchronous run has finished, and a channel that does, such as a webhook, is implementation-defined and outside the protocol (see [Extension policy](#extension-policy)). A bare runner is not required to answer "what happened to run X?" after the fact. A runner that keeps a run store answers it through the optional [run reads](#reading-a-run-and-idempotency-keys), which a caller polls, and declares so with `run_store: true` in `GET /version`. A client that must work against every runner relies on `/execute`'s response, and relies on `/start` only once `GET /version` has declared a run store or the implementation documents a channel of its own.

## Validating a bundle

`POST /validate` takes `files`, the method's tree as `/execute` takes it (see [Method files](#method-files)), and an optional `allow_signatures` flag (default `false` — strict; when `true`, the validation sweep tolerates unimplemented pipe signatures by minting a mock). A validating runner judges the whole tree: every bundle, and every file a bundle names by file reference or by a `PipeFunc`'s import path.

`/validate` is a **diagnostic endpoint**: its job is to return a *verdict* about the submitted bundle, and every verdict it can produce — valid or invalid — rides a **200**, discriminated in the body on the mandatory `is_valid` field.

- **`is_valid: true`** — the bundle is valid. The protocol declares the `is_valid` discriminant plus the runnability facts (`is_runnable`, and `pending_signatures` — refs of pipes still declared as unimplemented signatures); implementations MAY include their own artifacts (parsed structures, graphs, anything else) as additional properties.
- **`is_valid: false`** — the bundle is invalid. The body carries `errors[]`, a non-empty list of [problem items](#itemized-errors), one per fault, each with its own `code`, `detail`, `params` and `location` and optionally `suggestions` and a [`suggested_fix`](#suggested-fixes), plus `is_runnable: false` and an optional `message`. The structural artifacts of a valid report are absent.

Either arm may carry `warnings[]`: advisory findings in the same item schema, which never make a bundle invalid. On every arm a member with no value is left out rather than written as `null`, in the items of `warnings` as in those of `errors`. An item carries no verdict of its own: `is_valid` is the verdict, and a reader that needs an item's domain reads it from the item's code.

**Three recommended extension fields.** The protocol's base fields stay exactly as listed above, but three artifacts are common enough — and useful enough to a client that has just learned a bundle is valid — that the standard names them and fixes their shapes rather than letting each implementation invent its own. On the `is_valid: true` arm, an implementation SHOULD report them under these names: **`pipe_io_contracts`**, the per-pipe input and output contracts, whose shape is defined by [Pipe I/O Contracts](./pipe-io-contracts.md); **`input_form`**, the per-pipe ordered presentation view of a method's inputs, whose shape is defined by [Input-Form Descriptor](./input-form-descriptor.md); and **`output_form`**, the per-pipe presentation view of what each pipe resolves to, whose shape is defined by [Output-Form Descriptor](./output-form-descriptor.md). All three derive from the validated library, so none can appear on the `is_valid: false` arm — there is no library to derive from when loading or wiring failed. They remain *extension* fields in the sense of the [extension policy](#extension-policy): a conformant runner may omit them, and a client written against the base fields alone is unaffected. What the standard fixes is that a runner reporting them reports **these shapes** under **these names**. How a caller *asks* for them — always on, an opt-in request token, a separate route — is implementation-defined; all three artifacts are equally derivable offline from a resolved library, and the protocol carriage is one way to obtain them, not what they are.

A client pattern-matches `is_valid` to learn the verdict — it never inspects a status code or catches an exception body. Non-2xx is reserved for the cases where **no verdict could be produced**: a malformed request body is a `422` problem, auth a `401`/`403`, a server fault a `5xx`. So a non-2xx on `/validate` always means "the endpoint could not produce a verdict," never "your bundle is bad" — which keeps expected validation failures out of the 4xx error budget and never editorializes a verdict into a spurious retry. Signatures are never an error: an unimplemented signature reached during validation is a *runnability fact* (`is_runnable: false` + `pending_signatures`), not a validation failure, and `allow_signatures` only affects the dry-run sweep, not the verdict.

## Sending files by hash

A runner MAY keep a **blob store**: bytes keyed by their SHA-256, written once and never changed. A runner that keeps one declares `blob_store: true` in `GET /version` and serves `POST /blobs/missing`, so a sender uploads each file at most once and then sends the method's tree by hash. A second run of an unchanged method uploads nothing, and editing one template uploads one file.

1. The sender lists the method's tree and computes each file's SHA-256 and the [tree digest](./method-tree.md#the-tree-digest).
2. It asks `POST /blobs/missing` which of those blobs the runner lacks.
3. It uploads each missing blob as the answer says.
4. It sends the run, or the validation, with a hash entry for each file it chose to send by hash.

A sender chooses per file between an inline entry and a hash entry, and may mix both in one request; neither form is second-class.

### `POST /blobs/missing`

The request lists blobs by hash and size, each `size` a JSON integer written without a fraction or an exponent, as in a hash entry, and may name the tree they make up:

```json
{
  "digest": "sha256:801fca61b41566e46d3fb1923e323590da7a539fd3e7af7455e7cba3934d4674",
  "blobs": [
    { "sha256": "af12591480ada38cf107d1a76bc5e2e111ad4c7ec5f3a2a63d058f5f5ab6b91c", "size": 12 },
    { "sha256": "3e9b68b71cc667168399f0bccfb64b2d16314cdc0ed78fac4819aba0dda121a0", "size": 13 }
  ]
}
```

The `200` answer lists every blob of the request the runner does not hold, each with its `size`, a JSON integer written in the same way, and where to upload it:

```json
{
  "missing": [
    {
      "sha256": "3e9b68b71cc667168399f0bccfb64b2d16314cdc0ed78fac4819aba0dda121a0",
      "size": 13,
      "upload": {
        "method": "PUT",
        "url": "https://runner.example.com/v1/blobs/3e9b68b71cc667168399f0bccfb64b2d16314cdc0ed78fac4819aba0dda121a0",
        "headers": { "content-type": "application/octet-stream" }
      }
    }
  ]
}
```

To upload a missing blob, the sender sends the blob's bytes as the whole body of a request with the given `method` to the given `url`, carrying exactly the given `headers`. The upload target is the runner's to choose: its own `PUT /blobs/{sha256}`, or any other address that stores the bytes where the runner reads its blobs. A blob the runner holds is left out of `missing`, and an empty `missing` means the sender has nothing to upload.

The optional `digest` names the tree the listed blobs make up. A runner that keeps a record of the trees it has held in full MAY answer with an empty `missing` when it holds the tree that digest names, which makes the check for an unchanged method one lookup however many files it has. It records a tree only after checking that it holds every file the tree's listing names, and never takes an uploaded blob as such a record, since anyone can upload bytes that happen to form a listing.

A request naming one hash twice with different sizes is a `422`, and so is a blob past the runner's limits, refused before anything is uploaded with a problem naming the limit. Which callers share a blob store is the runner's policy: a hash entry resolves only in the store the runner keeps for its caller, and a runner serving several tenants SHOULD keep each one's blobs apart, so that holding a hash never tells one tenant what another has stored.

### `PUT /blobs/{sha256}`

The upload target of a runner that stores bytes itself. The body is the blob's bytes and nothing else. The runner computes their SHA-256 and refuses with a `422` a body whose hash differs from the one in the path. A blob is written once and never changed, so uploading bytes the runner already holds succeeds without changing anything; either way the answer is a `204`.

## Reading a run and idempotency keys

A runner MAY keep a **run store**: a record of the runs it has started, kept by their `pipeline_run_id`. A runner that keeps one declares `run_store: true` in `GET /version`, serves the two run reads below, and honours an idempotency key on `/execute` and `/start`. A runner that declares no run store serves neither read and ignores the key. Like the blob routes, this section is optional: the protocol requires no run store, and a runner without one is conformant.

A caller starts a run under an idempotency key of its choosing:

```http
POST /start
Idempotency-Key: 0b6e3c0e-5d0a-4f3e-8a57-9a1f4c2d7e11
Content-Type: application/json

{ "pipe_code": "analyze_contract", "files": { "contracts.mthds": "domain = \"legal\"\n..." }, "inputs": { "contract": { "concept": "native.Document", "content": { "url": "..." } } } }
```

If the `202` answer is lost, the caller sends the same request again under the same key within 24 hours of the first, the least time a runner [keeps a key](#idempotency-keys), and the runner answers with the run the first request started rather than starting a second one. The caller then polls the run's status and reads its output once it has completed:

```http
GET /runs/8c1f6a52-3d1e-4b7a-9f0e-2a5c7d9e4b10/status
GET /runs/8c1f6a52-3d1e-4b7a-9f0e-2a5c7d9e4b10/results
```

### The run store

A runner that keeps a run store records every run it starts, through `/execute` and `/start` alike, under the `pipeline_run_id` it answered with, together with the run's status and, once the run has failed, its problem. It keeps the output of every completed run whose output did not travel in an answer, that is a run started by `/start` and one that `/execute` answered with a `202`, so that the results read can serve it. It may also keep the output of a run whose `/execute` answer carried it. How long it keeps a run is its own policy, and a run it no longer holds reads as one it never held.

A run is read by the caller that started it, or by whoever else the runner's policy lets read it. A runner answers an id naming a run the caller may not read exactly as it answers an id naming no run, so that an id never tells a caller about a run it cannot read.

### `GET /runs/{pipeline_run_id}/status`

The status read answers `200` with the run's `pipeline_run_id`, its `status`, and its `error` once it has failed:

```json
{
  "pipeline_run_id": "8c1f6a52-3d1e-4b7a-9f0e-2a5c7d9e4b10",
  "status": "failed",
  "error": {
    "type": "https://mthds.ai/errors/pipe.output_multiplicity",
    "title": "A pipe's output does not have the declared multiplicity",
    "detail": "Pipe 'extract_clauses' produced a list, but its output 'clause' is declared as a single item.",
    "code": "pipe.output_multiplicity",
    "domain": "method",
    "retry": "no",
    "next_step": {
      "kind": "change_method",
      "detail": "Declare the output 'clause' as a list, or make pipe 'extract_clauses' produce a single item."
    },
    "params": { "pipe": "extract_clauses", "output": "clause", "declared": "single", "produced": "list" },
    "location": { "pipe": "extract_clauses", "path": ["review_contract", "extract_clauses"] },
    "pipeline_run_id": "8c1f6a52-3d1e-4b7a-9f0e-2a5c7d9e4b10"
  }
}
```

A run's `status` is one of:

| Status | Ended | Meaning |
|---|---|---|
| `pending` | no | The runner accepted the run and has not begun executing it. |
| `running` | no | The run is executing. |
| `completed` | yes | The run ended with its output, which the results read serves. |
| `failed` | yes | The run ended without output. `error` holds its problem, whose code says why, such as `run.cancelled` for a run its caller cancelled or `run.timed_out` for one that passed its time limit. |

`error` is the run's own problem, as the run's record keeps it: a problem document without `status`, since it is not the body of a response. It is present exactly when `status` is `failed`. The status read does not fail because the run failed: its `200` answers a question about the run, and the run's problem rides inside it. A runner that can no longer learn how a run ended, such as when whatever executed it vanished without reporting, ends it `failed` with the problem `run.lost`, whose retry is `yes`, since a new run may succeed.

A run ends `completed` or `failed`, and the statuses of a run that has ended are closed: a later protocol version may add a status only for a run that has not ended. So a runner MUST NOT emit a status this page does not list, and a client that meets a status it does not know reads the run as not ended and reads it again later. A runner may set a `Retry-After` header on the `200` of a run that has not ended, to say when to read it again.

### `GET /runs/{pipeline_run_id}/results`

The results read answers a completed run with a `200` whose body is the one `/execute` answers with, a `RunResultExecute` holding the run's `pipeline_run_id` and its `pipe_output`, so a client that started a run with `/start` reads the same output it would have read from `/execute`. Any other run is answered with a problem: `run.not_finished` before the run has ended, `run.failed` once it has ended without output, and `run.results_not_stored` for a completed run whose output travelled in `/execute`'s answer and was not kept. A read of a failed run's results carries the run's own problem as its `run_error` member, beside the read's own code:

```json
{
  "type": "https://mthds.ai/errors/run.failed",
  "title": "The run did not succeed",
  "status": 409,
  "detail": "Run '8c1f6a52-3d1e-4b7a-9f0e-2a5c7d9e4b10' ended without output, so it has no results.",
  "code": "run.failed",
  "domain": "runtime",
  "retry": "no",
  "next_step": {
    "kind": "read_run",
    "detail": "Read the run's own problem in run_error to learn why it failed."
  },
  "params": { "pipeline_run_id": "8c1f6a52-3d1e-4b7a-9f0e-2a5c7d9e4b10", "run_status": "failed" },
  "pipeline_run_id": "8c1f6a52-3d1e-4b7a-9f0e-2a5c7d9e4b10",
  "run_error": {
    "type": "https://mthds.ai/errors/run.timed_out",
    "title": "The run passed its time limit",
    "detail": "The run did not end within this runner's run time limit.",
    "code": "run.timed_out",
    "domain": "method",
    "retry": "no",
    "next_step": { "kind": "change_method", "detail": "Make the method do less work in one run." },
    "params": { "timeout": 3600 },
    "pipeline_run_id": "8c1f6a52-3d1e-4b7a-9f0e-2a5c7d9e4b10"
  }
}
```

A problem about a run is not the problem of the read that returned it. Reading the results again changes nothing, so the read's `retry` is `no`, and the run's own problem, in `run_error`, says who must act and whether a new run may succeed.

### Idempotency keys

A client sending `/execute` or `/start` may name the request with an `Idempotency-Key` header: a string of 1 to 255 visible ASCII characters, from `!` to `~`, that the client chooses and never uses for another request, such as a UUID. A runner that declares `run_store: true` then runs the request at most once while it holds the key: a repeat of it under the same key, from the same caller, is answered from that one execution. A client whose answer was lost, or whose request may or may not have reached the runner, sends the request again under its key within the period below and learns the outcome without starting a second run. A client SHOULD send a key on every request that starts a run, since only a request that carried one can be repeated safely. A runner that honours keys refuses a key outside that form with a `422` coded `request.invalid`.

A runner keeps each key per caller, so that two callers' keys never meet, and for at least 24 hours after the first request under it, with what it needs to answer a repeat: a fingerprint of the request, the run the request started, and the answer it gave when it keeps that answer. A request under a key the runner no longer holds is a first request. So every promise this section makes about a repeat holds within that period: a repeat that reaches the runner within 24 hours of the first request under its key is answered as described below, and past them the protocol promises nothing, since a runner that has let the key go takes the repeat as a first request and may start a second run. A client that cannot repeat a request within the period does not repeat it to learn its outcome: it reads the run when it knows the run's `pipeline_run_id`, and otherwise treats the outcome as unknown and never repeats the request automatically.

A repeat is the **same request** when it goes to the same route with a body of the same JSON value, whatever the order of its members and its whitespace. A request under a held key that is not the same request is refused with `request.idempotency_conflict`, whether the first request is still running or has ended: a key names one request, and a different request takes a new key. The same request under a held key is answered as follows:

- **While the first request is still being handled and has started no run**, with `request.idempotency_key_in_use`, carrying `retry_after` when the runner knows how long to wait. The client sends the same request again, unchanged, after waiting.
- **On `/start`, once the first request has started its run**, with the first answer, a `202 + RunResultStart` naming that run. Nothing starts again.
- **On `/execute`, once the first request has started its run**, with the first answer when the runner can give it again from what it kept of the answer or of the run: the same `200` and output, or the same problem. While the run has not ended, the runner answers with a `202 + RunResultStart` naming the run, with a `Location` header pointing at its status read, the asynchronous answer `/execute` may already give. Once the run has ended and the runner kept neither its answer nor its output, it answers with `run.answer_not_kept`, and the client reads the run's status to learn how it ended.
- **When the first request was refused before it started a run**, as a first request: a refusal takes no effect, so it leaves the key free.

The key changes nothing else about a request. A run's id is still the runner's, and a request without a key is never deduplicated. A runner that honours the key on a route of its own, beyond `/execute` and `/start`, answers a repeat whose answer it never gives twice, such as one that hands out a secret, with `request.already_executed`, and the client reads what the first request created rather than sending it again. A runner that keeps no run store ignores the header, so that a repeat under the key would start a second run: a client repeats a request under its key only against a runner whose `GET /version` declares `run_store: true`.

This is what the next step of a problem whose `retry` is `outcome_unknown` rests on. Against a runner that keeps a run store, the client learns the outcome by reading the run whose `pipeline_run_id` the problem carries or, when no answer named the run, by sending the request again under the same idempotency key within 24 hours of the first request under it, which answers with the run the first request started and never starts a second. Past that period a repeat may start a second run, so a client that knows no run to read leaves the outcome unknown.

The protocol defines no route that changes a run. A runner that offers one, such as a route that cancels a run, answers a change asked of a run that has already ended with `run.already_ended`.

### The codes of the run reads and idempotency keys

Every code in the table below is a core code that the run reads and idempotency keys introduce. Each code's title, parameters and documentation are the core registry's, and each code in the table declares the same step for its actor and for any other reader. The other codes this section names, such as `request.invalid`, `run.cancelled` and `run.timed_out`, are core codes it does not introduce, whose values are the core registry's.

| Code | Answered | Status | Domain | Retry | Step |
|---|---|---|---|---|---|
| `run.not_found` | By either read, when the id names no run the caller can read. | 404 | `input` | `no` | `change_input` |
| `run.not_finished` | By the results read, before the run has ended, with `retry_after` when known. | 409 | `runtime` | `yes` | `wait` |
| `run.failed` | By the results read, once the run has ended without output, with the run's problem in `run_error`. | 409 | `runtime` | `no` | `read_run` |
| `run.results_not_stored` | By the results read, for a completed run whose output travelled in `/execute`'s answer and was not kept. | 404 | `input` | `no` | `read_run` |
| `run.lost` | As a failed run's own problem, when the runner can no longer learn how the run ended. Its status is the one `/execute` answers it with. | 500 | `runtime` | `yes` | `retry` |
| `run.answer_not_kept` | By `/execute`, to the same request under a held key, once the run has ended and the runner kept neither its answer nor its output. | 409 | `input` | `no` | `read_run` |
| `run.already_ended` | By a runner's own route that changes a run, such as a cancellation, once the run has ended. | 409 | `input` | `no` | `read_run` |
| `request.idempotency_conflict` | To a request under a held key that is not the same request. | 409 | `input` | `no` | `change_input` |
| `request.idempotency_key_in_use` | To the same request under a held key, while the first request is still being handled and has started no run, with `retry_after` when known. | 409 | `runtime` | `yes` | `wait` |
| `request.already_executed` | To a repeat under a held key, on a runner's own route whose answer is never given twice. | 409 | `input` | `no` | `read_run` |

## Discovery

`GET /models` returns the runner's model deck — the models it can route to (`{name, type}` entries), optionally filtered by category. Implementations may add their own routing metadata (aliases, fallback chains, anything else) as additional properties.

`GET /version` is always public (no auth). It returns `protocol_version` (required), an optional `runner_version`, an optional `blob_store` flag, which is `true` for a runner that keeps a blob store and serves the [blob routes](#sending-files-by-hash), and `false` or absent for one that does not, and an optional `run_store` flag, which is `true` for a runner that keeps a run store, serves the [run reads](#reading-a-run-and-idempotency-keys) and honours idempotency keys, and `false` or absent for one that does not — implementations may add their own identification on top:

```json
{
  "protocol_version": "2.0.0",
  "runner_version": "2.3.0",
  "blob_store": true,
  "run_store": true
}
```

Clients use `/version` as the handshake: it reports the protocol and runner versions, whether the runner takes files by hash and whether it can be asked about a run after the fact, and any additional properties let clients detect vendor extensions before relying on them.

### Model categories

A deck entry's `type` is its model category. A category is a settings family of the language: it names the inline settings structure a model serves, and so the pipes whose `model` field can name that model.

| Category | Settings family | Pipes that name a model of it |
|---|---|---|
| `llm` | [`LLMSetting`](./mthds-format.md#inline-llm-settings) | `PipeLLM`, `PipeStructure` |
| `extract` | [`ExtractSetting`](./mthds-format.md#inline-extract-settings) | `PipeExtract` |
| `img_gen` | [`ImgGenSetting`](./mthds-format.md#inline-image-generation-settings) | `PipeImgGen` |
| `search` | [`SearchSetting`](./mthds-format.md#inline-search-settings) | `PipeSearch` |
| `judgment` | [`JudgmentSetting`](./mthds-format.md#inline-judgment-settings) | `PipeJudge` |

The category follows the settings family, not the operator: `PipeStructure` takes `LLMSetting`, so its models are listed under `llm`. When the standard adds a settings family, the protocol adds its category in its next minor version.

The two sides of the wire carry different obligations:

- **A runner emits only the protocol's categories.** A runner MUST NOT put a value the protocol does not define in a deck entry's `type`, and MUST NOT accept one on the `?type=` filter, which answers it with a `422`. A model of a family the protocol does not define — a vendor's own operator — is reported, if at all, under an extension property of the runner's choosing, never under an invented category and never as an entry of `models` without one.
- **A client accepts any category.** A client reading a model list MUST NOT fail it because an entry carries a category it does not recognize; it keeps that entry with its raw value or leaves it out.

The `enum` on a deck entry's `type` in the OpenAPI document is the emitter's contract, the set a runner may report. A client that derives its types or its validation from that document widens the field to any string, as the reader rule requires.

The reader rule is what makes a new category a minor change: a client written against one protocol version keeps working when a runner of a later minor version reports a category the client has never heard of. It governs a client *reading* a list on purpose. A tool that checks a runner, such as a conformance harness, is checking the emitter rule and stays free to reject an unknown value. In the other direction, a client that filters on a category its runner's protocol version does not define gets a `422`, and learns from `GET /version` which protocol version the runner implements.

## Errors

Every error a runner answers is a problem document of [RFC 9457](https://www.rfc-editor.org/rfc/rfc9457), served as `application/problem+json`, carrying the MTHDS core members beside the RFC's own. A run that failed, as the caller of `/execute` reads it:

```json
{
  "type": "https://mthds.ai/errors/pipe.output_multiplicity",
  "title": "A pipe's output does not have the declared multiplicity",
  "status": 422,
  "detail": "Pipe 'extract_clauses' produced a list, but its output 'clause' is declared as a single item.",
  "code": "pipe.output_multiplicity",
  "domain": "method",
  "retry": "no",
  "next_step": {
    "kind": "change_method",
    "detail": "Declare the output 'clause' as a list, or make pipe 'extract_clauses' produce a single item."
  },
  "params": { "pipe": "extract_clauses", "output": "clause", "declared": "single", "produced": "list" },
  "location": { "pipe": "extract_clauses", "path": ["review_contract", "extract_clauses"] },
  "pipeline_run_id": "8c1f6a52-3d1e-4b7a-9f0e-2a5c7d9e4b10"
}
```

The first four members are the RFC's, and the rest are the MTHDS core's:

| Member | Present | Meaning |
|---|---|---|
| `type` | always | The code's documentation page, derived from the code (see [The `type` URI](#the-type-uri)). |
| `title` | always | The code's short title, the same for every occurrence of the code. |
| `status` | on an HTTP response | The HTTP status of the response the problem is the body of. A runner sets it on every response; a problem kept elsewhere, such as in a run's record, leaves it out. |
| `detail` | always | This occurrence, in one or two sentences a person can read. |
| `code` | always | The registry [code](#codes): what happened. |
| `domain` | always | [Who must act](#domain-who-must-act). |
| `retry` | always | Whether [repeating the operation](#retry) that produced the problem can succeed. |
| `retry_after` | when known | Seconds to wait before repeating it, beside a `retry` of `yes`. |
| `next_step` | always | What the reader should do [next](#next-steps): a `kind` from a closed list and a `detail` sentence. |
| `params` | when the code declares parameters | The typed facts the problem's sentences were written from. |
| `location` | when the error has a place | Where in the method, the request or the run. |
| `errors` | when the problem has several faults | One [item](#itemized-errors) per fault. |
| `pipeline_run_id` | when a run exists | The run the error belongs to, as `/execute` and `/start` name it. |
| `run_error` | on a read of a failed run's results | The run's own problem, nested, as the [results read](#get-runspipeline_run_idresults) describes. |

The RFC's optional `instance` member is not part of the core: a runner may send it, and a client written against the protocol does not read it.

**The code decides.** Every problem carries exactly one code from a registry, and its domain, its retry verdict, its next step, its title and its HTTP status are properties of that code. The wire carries them so that a reader needs no lookup, but a runner never sets them independently of the code: two cases that need different verdicts are two codes. A client branches on `code`, and on `domain`, `retry` and `next_step.kind` when it handles several codes alike. It never parses `title`, `detail` or `next_step.detail`, which are written for a person, so every fact they state is also a member: the typed facts in `params`, the place in `location`. No member of a problem carries the content of a run's inputs or outputs.

### Codes

A code is lowercase and dotted, each segment matching `[a-z][a-z0-9_]*`. A core code is bare, exactly a family and a name, such as `input.missing` or `request.blobs_missing`. A code belongs to the core when any conforming runner or client could raise it, independently of hosting, billing or a vendor's components. The [MTHDS core registry](error-registry.md) lists the core codes and gives each its title, domain, retry verdict, steps, parameters and HTTP status. A code's **family** is the code without its last segment, so `request.blobs_missing` belongs to the family `request`.

**Extension codes.** Every other code starts with a prefix its owner registers, followed by a family and a name: `<prefix>.<family>.<name>`, such as `acme.billing.credit_exhausted`. A prefix is one segment of the same form, it is never the name of a core family, and it belongs to one owner, who alone adds codes under it. What the protocol leaves to implementations, such as billing or a catalog of saved methods, is coded under the implementation's own prefix.

**Declaring a prefix.** An owner declares an extension prefix in two steps:

1. It publishes a registry of its own codes, in the [format of the core registry](error-registry.md), that names the prefix and the base URL its codes' pages are published under, and declares for each code everything the core registry declares for a core code.
2. It registers the prefix with the standard, through the [contribution process](../about/contributing.md#register-an-error-code-prefix), as an entry of the core registry's list of extension prefixes naming the prefix, its owner and that base URL. A registered prefix is never reassigned to another owner.

A runner emits a code under a prefix only once the prefix is registered and the code is in its owner's registry.

### The `type` URI

`type` is derived from the code and its owner's base URL: the base URL, a slash, then the whole code. The core's base URL is `https://mthds.ai/errors`, so the core code `input.missing` has the type `https://mthds.ai/errors/input.missing`. An extension code is joined, its prefix included, to the base URL its prefix is registered with: under a prefix registered with `https://errors.acme.example`, the code `acme.billing.credit_exhausted` has the type `https://errors.acme.example/acme.billing.credit_exhausted`. The page at a type URI says what the code means and what to do about it, and the [Error Codes](../errors/index.md) page lists every core code's. Because `type` and `code` name the same thing one to one, a client branches on `code` and never takes a code apart from `type`.

### Domain: who must act

The domain answers the first question a reader has: can I fix this myself, and if not, who can. Its list is closed:

| Domain | Who acts | Examples |
|---|---|---|
| `input` | The caller, by changing the request or its inputs | A required input is missing; an input is not the declared concept; a request body is malformed; the runner does not hold a file sent by hash. |
| `method` | The method's author, by changing the method | The method does not validate; a pipe's output has the wrong multiplicity at run time; the method names a model that exists nowhere. |
| `account` | The account's owner | A refused credential; a missing permission; an exhausted quota. |
| `operator` | Whoever runs the runtime | The method names a model that exists, but this runner serves no backend for it; a misconfigured server. |
| `runtime` | Nobody beforehand: wait, retry or report | A provider outage; a timeout; a model's structured output that did not match its schema; a fault of the runtime itself. |

A case whose actor depends on where something came from is two codes: a URL the runner refuses to fetch is the caller's when an input named it and the method's author's when the method did.

### Retry

`retry` says whether repeating the operation that produced the problem can succeed, and its list is closed:

- `no`: repeating it fails the same way.
- `yes`: repeating it may succeed, after `retry_after` seconds when that member is given.
- `outcome_unknown`: the operation may already have taken effect, such as a request whose connection dropped after the runner received it. A client never repeats such an operation automatically; it follows the next step to learn the outcome first. Against a runner that keeps a run store, that step reads the run, or sends the request again under the same idempotency key within 24 hours of the first request under it, which then never runs it twice ([Idempotency keys](#idempotency-keys)). Past those 24 hours a repeat may start a second run, so a client that knows no run to read leaves the outcome unknown.

On a run's own problem the operation is the run, so `yes` means that a new run with the same inputs may succeed.

### Next steps

`next_step` tells the reader what to do next, as a `kind` from a closed list and a `detail` sentence:

| Kind | What the reader does |
|---|---|
| `retry` | Repeats the operation. |
| `wait` | Waits, then checks again later. |
| `read_run` | Reads the run to learn its outcome, such as through the [status read](#get-runspipeline_run_idstatus) of a runner that keeps a run store. |
| `refresh` | Fetches the latest state, such as a fresh credential, and applies the change again. |
| `change_input` | Changes the request or its inputs, which includes supplying the files a runner lacks, by uploading them or by sending them inline, and sending the request again. |
| `change_method` | Changes the method. |
| `change_model` | Chooses another model. |
| `check_credentials` | Checks the credential the request sent. |
| `request_access` | Asks for the permission the operation needs. |
| `check_account` | Checks the account's credit, plan or quotas. |
| `fix_configuration` | Fixes the runtime's configuration. |
| `upgrade` | Upgrades the client or the runtime. |
| `contact_owner` | Contacts the owner of the method or of the account. |
| `report` | Reports the problem, with the identifiers it carries. |

A step is aimed at whoever reads the problem, not at the domain's actor. Each code declares a step for its actor and one for any other reader: a caller who runs a method someone else owns reads `contact_owner` where the method's author would read `change_method`, and a member of an account who cannot change it reads `contact_owner` where its owner would read `check_account`. There is no unknown step: every code declares its steps, and the catch-all code, for a fault no other code describes, says `report`.

### Parameters and location

`params` holds the typed facts the problem's sentences were written from, such as the pipe, the output and the two multiplicities in the example above, so that a client acts on data rather than on prose. Each code declares its parameters and their types in its registry, and `params` is present when the code declares any. A parameter holds an identifier, a number or an enumerated value, or, where its code declares so, the caller's own text, such as a parser's finding about the caller's method; it never holds the content of a run's inputs or outputs.

`location` says where the error happened. Every member is optional:

| Member | Meaning |
|---|---|
| `pipe` | The failing pipe's code. |
| `path` | The pipe codes from the run's main pipe down to the failing one. |
| `input` | The name of the input the error concerns. |
| `field` | A dotted path inside an input or a request body. |
| `item` | The index of the batch item that failed, counted from 0. |
| `attempt` | The attempt that failed, counted from 1. |
| `file` | The [tree path](./method-tree.md#tree-paths) of the method's file the error is in. |
| `line` | The line in `file`, counted from 1. |
| `column` | The column in `line`, counted from 1. |

The location of a run's problem is its root fault's, so it names the pipe that failed rather than the controller around it.

### Itemized errors

A problem with several faults, such as a method that does not validate, carries one item per fault in `errors`, and the errors and warnings of a [validate verdict](#validating-a-bundle) are items of the same schema:

```json
{
  "code": "method.input_unused",
  "detail": "Pipe 'summarize' declares the input 'draft' but never reads it.",
  "params": { "pipe": "summarize", "variables": ["draft"] },
  "location": { "pipe": "summarize", "file": "contracts.mthds", "line": 12, "column": 1 },
  "suggested_fix": {
    "fix_code": "remove-unused-input",
    "description": "Remove the input 'draft' from pipe 'summarize'.",
    "safety": "unsafe",
    "ops": [
      { "kind": "delete_key", "table_path": ["pipe", "summarize", "inputs"], "key": "draft" }
    ]
  }
}
```

| Member | Present | Meaning |
|---|---|---|
| `code` | always | The fault's code. |
| `detail` | always | This fault, in one or two sentences a person can read. |
| `params` | when the code declares parameters | The fault's typed facts. |
| `location` | when the fault has a place | Where the fault is. |
| `suggestions` | optional | The names a near miss most likely meant, the likeliest first. |
| `suggested_fix` | optional | A [semantic patch](#suggested-fixes) that fixes the fault. |

An item carries no verdict of its own: the problem or the verdict that holds it does, and a reader that needs an item's domain reads it from the item's code.

### Suggested fixes

A `suggested_fix` is a semantic patch over a bundle: a list of operations addressed by TOML key path, never a text diff. Its members are `fix_code`, the implementation's kebab-case name for the rule that produced it; `description`, one sentence saying what it does; `safety`; `file`, the tree path of the bundle it patches, which defaults to the file the item's `location` names; and `ops`, a non-empty list of operations discriminated on `kind`.

`safety` is `safe` for a fix that may be applied without asking anyone, and `unsafe` for a likely correction that a person or an agent confirms before it is applied.

Every operation names a table by `table_path`, the table's key path from the document root, each segment one key as written, and empty for the root table:

| Kind | Members | Effect |
|---|---|---|
| `set_key` | `table_path`, `key`, `value` | Writes `key = value` in the table, creating the key when the table does not hold it and replacing a scalar or array value it holds; when the key holds a table, the operation is a conflict and changes nothing. The value is a TOML scalar or an inline table of scalars. |
| `ensure_table` | `table_path` | Creates the table at `table_path` when it is absent and the table above it exists, and leaves an existing one untouched. |
| `delete_key` | `table_path`, `key` | Removes `key` from the table. |
| `delete_table` | `table_path` | Removes the table at `table_path`, every part of it included. |
| `rename_table_key` | `table_path`, `key`, `new_key` | Renames `key` to `new_key` within the table, keeping its value and its position. |
| `move_key` | `table_path`, `key`, `new_table_path`, `new_key` | Moves `key`, with its whole value, into the table at `new_table_path` under `new_key`, creating the destination tables that do not exist. |
| `remap_value` | `table_path`, `key`, `mapping` | Rewrites the string value of `key` through `mapping`, from an old value to its new one, and does nothing when the value is not a key of the mapping. It rewrites its own target by design, which is never a conflict. |

For `ensure_table` and `delete_table`, `table_path` names the table acted on rather than the table holding a key, so it is never empty, and the root table is never removed.

The operations apply in order, each to the document the previous one left. What an operation does with an absent target depends on its kind. A deletion, a rename, a move or a remap whose target is absent, such as a key to delete or the table holding it, is skipped. `ensure_table` creates its table when it is absent, and `set_key` creates its key when the table does not hold it. Each needs the table that would hold its target: a `set_key` whose table is absent, or an `ensure_table` whose parent table is absent, is skipped, so a fix that writes into a table that may be missing puts an `ensure_table` before the operations that need it, one for each level that may be missing, the outermost first. An operation already in the state it would produce, such as an `ensure_table` whose table exists or a `set_key` whose key already holds its value, is skipped too. One that could only proceed by overwriting a key or a table other than its own target, such as a rename or a move onto a key its destination table already holds, is a conflict and changes nothing. Rewriting its own target is no conflict: `set_key` replaces a scalar or array value its key holds, and `remap_value` rewrites its value by design. A `set_key` whose key holds a table is a conflict all the same, and so is an `ensure_table` whose `table_path` names a value other than a table; neither changes anything. An applier reports skips and conflicts rather than forcing the change. The operations are the contract, and any diff an applier shows from them is presentation.

### Readers and emitters

The problem document is closed for emitters and open for readers:

- **A runner emits only what is registered.** Every code it emits is in a registry, the core's or that of a registered prefix, and every value it puts in `domain`, `retry`, `next_step.kind`, a fix's `safety` or an operation's `kind` is one this page lists. The enums of the OpenAPI document are the emitter's contract.
- **A reader accepts what it does not know.** Every schema of the problem document, its items, locations, steps, fixes and operations included, accepts members it does not declare, and a reader ignores a member it does not know, as RFC 9457 requires. A client that derives its types or its validation from the OpenAPI document widens each of these enums to any string, as it does for [model categories](#model-categories). An operation's `kind` selects a variant of a union rather than a value of an enum, so the OpenAPI document gives `FixOp` a reader-side catch-all, `UnknownFixOp`, an object whose `kind` is a string none of the listed kinds, which no runner emits: an operation of a kind the reader does not know still validates, and so do its fix, its item and the problem or verdict holding them. `FixOp` is a plain `oneOf` matched on `kind`, each listed operation fixing it to one value, with no discriminator object, since a discriminator rejects a value its mapping does not name. Such a client keeps that variant rather than closing the union on the kinds this page lists.
- **A reader falls back on the family.** A reader that meets a code, a domain or a step kind it does not know reads it by the code's family, as it reads the codes of that family it knows, and when it knows nothing of the family either, it reads the domain as `runtime` and the step as `report`. A `retry` it does not know reads as `no`, so that nothing is repeated on a guess. An applier that meets an operation kind it does not know applies none of that fix, and a `safety` it does not know reads as `unsafe`.
- **An unset member is absent.** A member with no value is left out, never written as `null`, in a problem, in its items and locations, and in a validate verdict's errors and warnings alike.

Because every problem carries its own domain, verdict and step, a client whose registry lags a runner's still reads a problem with a new code correctly by these rules. An item carries only its code, so that guarantee does not reach an item whose code the client does not know, such as an item of a validate verdict, which no problem holds: the client reads such an item by the code's family, and when it knows nothing of the family either, as `runtime` and `report`, which need not be the domain and step its code declares. A tool that checks a runner, such as a conformance harness, checks the emitter rules and stays free to reject an unknown value.

## Extension policy

Implementations may extend the surface — extra routes, extra optional request properties, extra response properties — but **must not change the meaning or shape of the protocol routes**. Both sides of the wire are extension-open: request bodies accept implementation-defined args, and the protocol's response schemas declare only the base fields (`additionalProperties` allowed). A client written against the MTHDS Protocol runs unmodified against any compliant runner; a vendor's superset may accept and return more, but never diverges on the surface defined here.

## Conformance

An implementation claiming conformance states it as: *implements MTHDS Protocol v2.0*. Conformance means: the five required routes exist with the request/response shapes of [`mthds-protocol.openapi.yaml`](openapi/mthds-protocol.openapi.yaml), every error is an RFC 9457 problem document carrying the core members, with a registered code, `/version` is public, a runner that declares `blob_store: true` serves `POST /blobs/missing` and resolves hash entries from its blob store, and a runner that declares `run_store: true` serves both run reads and honours an idempotency key on `/execute` and `/start` as [Reading a run and idempotency keys](#reading-a-run-and-idempotency-keys) describes.

The protocol number moves under its own rule — a new route, a new optional field or a new [model category](#model-categories) is a minor bump, a changed shape or meaning is a major one — independently of the standard version. The recommended extension fields above are not such an addition: they are shaped by their own specification pages and ride a report that is extension-open by policy, so naming one moves no protocol number. See [Versioning](./versioning.md#the-protocol-version).

## Route reference

Everything below is rendered at build time from the normative OpenAPI document — do not edit it by hand; edit [`mthds-protocol.openapi.yaml`](openapi/mthds-protocol.openapi.yaml).

<!--
This Markdown has been generated by essentials-openapi
https://github.com/Neoteroi/essentials-openapi

Most likely, it is not desirable to edit this file by hand!
-->


## Servers

<table>
    <thead>
        <tr>
            <th>Description</th>
            <th>URL</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td>Example — a self-hosted runner. The version segment belongs to the server base URL; protocol paths are version-agnostic.</td>
            <td>
                <a href="http://localhost:8081/v1" target="_blank" rel="noopener noreferrer">http://localhost:8081/v1</a>
            </td>
        </tr>
        <tr>
            <td>Example — a hosted, protocol-compliant superset.</td>
            <td>
                <a href="https://api.example.com/v1" target="_blank" rel="noopener noreferrer">https://api.example.com/v1</a>
            </td>
        </tr>
    </tbody>
</table>

## <span class="api-tag">run</span>


<hr class="operation-separator" />

### <span class="http-post">POST</span> /execute
Execute a method synchronously and return its full output.

??? note "Description"
    Blocking. The protocol sets no time limit; deployments cap it at their proxy layer. For long-running methods prefer /start. Implementations MAY return 202 + RunResultStart (id only) with a Location header pointing at an implementation-defined status resource when they cannot hold the connection open for the full execution (RFC 9110 asynchronous pattern); clients that cannot handle 202 should use /start instead. A runner whose /version declares run_store true points Location at the run's status read, keeps the run's output for its results read, and honours the Idempotency-Key header: the same request repeated under a held key is answered with the first answer when the runner can give it again, with a 202 naming the run while the run has not ended, and with a 409 coded run.answer_not_kept once it has ended and the runner kept neither its answer nor its output.



**Input parameters**

<table>
    <thead>
        <tr>
            <th>Parameter</th>
            <th>In</th>
            <th>Type</th>
            <th>Default</th>
            <th>Nullable</th>
            <th>Description</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td class="parameter-name"><code>bearer</code></td>
            <td>header</td>
            <td>string</td>
            <td>N/A</td>
            <td>No</td>
            <td>Token semantics are implementation-defined.</td>
        </tr>
        <tr>
            <td class="parameter-name"><code>Idempotency-Key</code></td>
            <td>header</td>
            <td>string</td>
            <td></td>
            <td>No</td>
            <td>Names the request, so that a runner whose /version declares run_store true runs it at most once while it holds the key: a string of visible ASCII characters the client chooses and never uses for another request, such as a UUID. The runner keeps each key per caller, for at least 24 hours after the first request under it, and takes a request under a key it no longer holds as a first request, so the protocol promises nothing about a repeat past those 24 hours: a client that cannot repeat within them reads the run when it knows its pipeline_run_id, and otherwise treats the outcome as unknown and never repeats automatically. The same request, the same route with a body of the same JSON value whatever the order of its members and its whitespace, repeated under a held key is answered from the first execution: a 409 coded request.idempotency_key_in_use while the first request is still being handled and has started no run, the first answer once it has started its run, and as a first request when the first was refused before it started a run, which leaves the key free. A different request under a held key is a 409 coded request.idempotency_conflict. A key outside this form is a 422 coded request.invalid. A runner that keeps no run store ignores the header, so a client repeats a request under its key only against a runner that declares run_store true.
</td>
        </tr>
    </tbody>
</table>
<p class="request-body-title"><strong>Request body</strong></p>



=== "application/json"
    
    
    ```json
    {
        "pipe_code": "string",
        "files": null,
        "inputs": {},
        "output_name": "string",
        "output_multiplicity": null,
        "dynamic_output_concept_ref": "string"
    }
    ```
    <span class="small-note">⚠️</span>&nbsp;<em class="small-note warning">This example has been generated automatically from the schema and it is not accurate. Refer to the schema for more information.</em>

    

    ??? hint "Schema of the request body"
        ```json
        {
            "type": "object",
            "description": "At least one of pipe_code / files is required (enforced by the anyOf rule below). If files is provided without pipe_code, the run starts at the manifest's main_pipe when the tree holds a METHODS.toml at its root, or else, in a method with no manifest, at the one main_pipe its bundles declare; a tree whose manifest declares none, or with no manifest whose bundles declare none or several, is a 422 naming its bundles by their tree paths. Extension-open: implementations MAY accept extra top-level properties (extension args).\n",
            "additionalProperties": true,
            "anyOf": [
                {
                    "required": [
                        "pipe_code"
                    ],
                    "properties": {
                        "pipe_code": {
                            "type": "string",
                            "minLength": 1
                        }
                    }
                },
                {
                    "required": [
                        "files"
                    ],
                    "properties": {
                        "files": {
                            "$ref": "#/components/schemas/MethodFiles"
                        }
                    }
                }
            ],
            "properties": {
                "pipe_code": {
                    "type": [
                        "string",
                        "null"
                    ],
                    "description": "Code of the pipe to execute (a pipe the runner already holds, or one defined in a bundle of files)."
                },
                "files": {
                    "description": "The method to load, as its whole method tree. Implementations bound a file's size, the tree's file count and total size, and the total of the inline entries.",
                    "anyOf": [
                        {
                            "$ref": "#/components/schemas/MethodFiles"
                        },
                        {
                            "type": "null"
                        }
                    ]
                },
                "inputs": {
                    "type": [
                        "object",
                        "null"
                    ],
                    "description": "Method inputs: map of input name to { concept, content }. Content shapes follow the concept's structure; content validation is deliberately loose here and strict inside the runtime.",
                    "additionalProperties": {
                        "type": "object",
                        "required": [
                            "concept",
                            "content"
                        ],
                        "properties": {
                            "concept": {
                                "type": "string"
                            },
                            "content": {}
                        }
                    }
                },
                "output_name": {
                    "type": [
                        "string",
                        "null"
                    ],
                    "description": "Name of the output slot to return as the main output."
                },
                "output_multiplicity": {
                    "oneOf": [
                        {
                            "type": "boolean"
                        },
                        {
                            "type": "integer"
                        },
                        {
                            "type": "null"
                        }
                    ],
                    "description": "Output multiplicity override (false/true or an explicit count)."
                },
                "dynamic_output_concept_ref": {
                    "type": [
                        "string",
                        "null"
                    ],
                    "description": "Override for the dynamic output concept reference."
                }
            }
        }
        ```

<p class="responses-title"><strong>Responses</strong></p>


=== "200 OK"
    
    === "application/json"
        
        
        ```json
        {
            "pipeline_run_id": "string",
            "pipe_output": {}
        }
        ```
        <span class="small-note">⚠️</span>&nbsp;<em class="small-note warning">This example has been generated automatically from the schema and it is not accurate. Refer to the schema for more information.</em>
        
        

        ??? hint "Schema of the response body"
            ```json
            {
                "type": "object",
                "description": "POST /execute 200 — the completed run, and the 200 of the results read of a runner that keeps a run store, which answers a completed run with the body /execute answers with. Two base fields: the server-generated authoritative pipeline_run_id and the method's pipe_output (always present — a completed run has output, either a value or an explicit absence document). Extension-open: anything more an implementation returns (a run state, timestamps, output naming) is an extension on top.\n",
                "additionalProperties": true,
                "required": [
                    "pipeline_run_id",
                    "pipe_output"
                ],
                "properties": {
                    "pipeline_run_id": {
                        "type": "string",
                        "description": "The run identifier — server-generated and authoritative."
                    },
                    "pipe_output": {
                        "description": "The method's serialized output (working memory of serialized stuffs).",
                        "type": "object"
                    }
                }
            }
            ```
    
    
=== "202 Accepted"
    
    === "application/json"
        
        
        ```json
        {
            "pipeline_run_id": "string"
        }
        ```
        <span class="small-note">⚠️</span>&nbsp;<em class="small-note warning">This example has been generated automatically from the schema and it is not accurate. Refer to the schema for more information.</em>
        
        

        ??? hint "Schema of the response body"
            ```json
            {
                "type": "object",
                "description": "POST /start 202 (and the optional /execute 202 degrade) — the started run's authoritative pipeline_run_id, nothing else. A started run has no output yet. A runner that keeps a run store serves it through the results read once the run has completed; any other way it is delivered (callbacks, anything else) is implementation-defined and outside the protocol. Extension-open.\n",
                "additionalProperties": true,
                "required": [
                    "pipeline_run_id"
                ],
                "properties": {
                    "pipeline_run_id": {
                        "type": "string",
                        "description": "The run identifier — server-generated and authoritative."
                    }
                }
            }
            ```
    
    

    **Response headers**

    | Name | Description | Schema |
    | --- | --- | --- |
    | `Location` | Implementation-defined status resource for this run, or its status read on a runner that keeps a run store. |<span class="string-type">string</span> |

    
=== "409 Conflict"
    <div class="common-response"><p>Refer to the common response description: <a href="#idempotencyproblem" class="ref-link">IdempotencyProblem</a>.</p></div>
=== "422 Unprocessable Content"
    <div class="common-response"><p>Refer to the common response description: <a href="#validationproblem" class="ref-link">ValidationProblem</a>.</p></div>
=== "Other responses"
    <div class="common-response"><p>Refer to the common response description: <a href="#problem" class="ref-link">Problem</a>.</p></div>


<hr class="operation-separator" />

### <span class="http-post">POST</span> /start
Start a method asynchronously; returns its pipeline_run_id immediately.

??? note "Description"
    Asynchronous. Returns 202 + RunResultStart immediately (pipeline_run_id only). The protocol defines no completion channel: a runner whose /version declares run_store true serves the run reads, which a caller polls, and any channel that tells a caller a run has finished (callbacks, anything else) is implementation-defined and outside the protocol. The returned pipeline_run_id is always authoritative (server-generated). A runner that keeps a run store honours the Idempotency-Key header: the same request repeated under a held key is answered with the first 202, naming the run the first request started, and starts nothing.



**Input parameters**

<table>
    <thead>
        <tr>
            <th>Parameter</th>
            <th>In</th>
            <th>Type</th>
            <th>Default</th>
            <th>Nullable</th>
            <th>Description</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td class="parameter-name"><code>bearer</code></td>
            <td>header</td>
            <td>string</td>
            <td>N/A</td>
            <td>No</td>
            <td>Token semantics are implementation-defined.</td>
        </tr>
        <tr>
            <td class="parameter-name"><code>Idempotency-Key</code></td>
            <td>header</td>
            <td>string</td>
            <td></td>
            <td>No</td>
            <td>Names the request, so that a runner whose /version declares run_store true runs it at most once while it holds the key: a string of visible ASCII characters the client chooses and never uses for another request, such as a UUID. The runner keeps each key per caller, for at least 24 hours after the first request under it, and takes a request under a key it no longer holds as a first request, so the protocol promises nothing about a repeat past those 24 hours: a client that cannot repeat within them reads the run when it knows its pipeline_run_id, and otherwise treats the outcome as unknown and never repeats automatically. The same request, the same route with a body of the same JSON value whatever the order of its members and its whitespace, repeated under a held key is answered from the first execution: a 409 coded request.idempotency_key_in_use while the first request is still being handled and has started no run, the first answer once it has started its run, and as a first request when the first was refused before it started a run, which leaves the key free. A different request under a held key is a 409 coded request.idempotency_conflict. A key outside this form is a 422 coded request.invalid. A runner that keeps no run store ignores the header, so a client repeats a request under its key only against a runner that declares run_store true.
</td>
        </tr>
    </tbody>
</table>
<p class="request-body-title"><strong>Request body</strong></p>



=== "application/json"
    
    
    ```json
    {
        "pipe_code": "string",
        "files": null,
        "inputs": {},
        "output_name": "string",
        "output_multiplicity": null,
        "dynamic_output_concept_ref": "string"
    }
    ```
    <span class="small-note">⚠️</span>&nbsp;<em class="small-note warning">This example has been generated automatically from the schema and it is not accurate. Refer to the schema for more information.</em>

    

    ??? hint "Schema of the request body"
        ```json
        {
            "type": "object",
            "description": "At least one of pipe_code / files is required (enforced by the anyOf rule below). If files is provided without pipe_code, the run starts at the manifest's main_pipe when the tree holds a METHODS.toml at its root, or else, in a method with no manifest, at the one main_pipe its bundles declare; a tree whose manifest declares none, or with no manifest whose bundles declare none or several, is a 422 naming its bundles by their tree paths. Extension-open: implementations MAY accept extra top-level properties (extension args).\n",
            "additionalProperties": true,
            "anyOf": [
                {
                    "required": [
                        "pipe_code"
                    ],
                    "properties": {
                        "pipe_code": {
                            "type": "string",
                            "minLength": 1
                        }
                    }
                },
                {
                    "required": [
                        "files"
                    ],
                    "properties": {
                        "files": {
                            "$ref": "#/components/schemas/MethodFiles"
                        }
                    }
                }
            ],
            "properties": {
                "pipe_code": {
                    "type": [
                        "string",
                        "null"
                    ],
                    "description": "Code of the pipe to execute (a pipe the runner already holds, or one defined in a bundle of files)."
                },
                "files": {
                    "description": "The method to load, as its whole method tree. Implementations bound a file's size, the tree's file count and total size, and the total of the inline entries.",
                    "anyOf": [
                        {
                            "$ref": "#/components/schemas/MethodFiles"
                        },
                        {
                            "type": "null"
                        }
                    ]
                },
                "inputs": {
                    "type": [
                        "object",
                        "null"
                    ],
                    "description": "Method inputs: map of input name to { concept, content }. Content shapes follow the concept's structure; content validation is deliberately loose here and strict inside the runtime.",
                    "additionalProperties": {
                        "type": "object",
                        "required": [
                            "concept",
                            "content"
                        ],
                        "properties": {
                            "concept": {
                                "type": "string"
                            },
                            "content": {}
                        }
                    }
                },
                "output_name": {
                    "type": [
                        "string",
                        "null"
                    ],
                    "description": "Name of the output slot to return as the main output."
                },
                "output_multiplicity": {
                    "oneOf": [
                        {
                            "type": "boolean"
                        },
                        {
                            "type": "integer"
                        },
                        {
                            "type": "null"
                        }
                    ],
                    "description": "Output multiplicity override (false/true or an explicit count)."
                },
                "dynamic_output_concept_ref": {
                    "type": [
                        "string",
                        "null"
                    ],
                    "description": "Override for the dynamic output concept reference."
                }
            }
        }
        ```

<p class="responses-title"><strong>Responses</strong></p>


=== "202 Accepted"
    
    === "application/json"
        
        
        ```json
        {
            "pipeline_run_id": "string"
        }
        ```
        <span class="small-note">⚠️</span>&nbsp;<em class="small-note warning">This example has been generated automatically from the schema and it is not accurate. Refer to the schema for more information.</em>
        
        

        ??? hint "Schema of the response body"
            ```json
            {
                "type": "object",
                "description": "POST /start 202 (and the optional /execute 202 degrade) — the started run's authoritative pipeline_run_id, nothing else. A started run has no output yet. A runner that keeps a run store serves it through the results read once the run has completed; any other way it is delivered (callbacks, anything else) is implementation-defined and outside the protocol. Extension-open.\n",
                "additionalProperties": true,
                "required": [
                    "pipeline_run_id"
                ],
                "properties": {
                    "pipeline_run_id": {
                        "type": "string",
                        "description": "The run identifier — server-generated and authoritative."
                    }
                }
            }
            ```
    
    
=== "409 Conflict"
    <div class="common-response"><p>Refer to the common response description: <a href="#idempotencyproblem" class="ref-link">IdempotencyProblem</a>.</p></div>
=== "422 Unprocessable Content"
    <div class="common-response"><p>Refer to the common response description: <a href="#validationproblem" class="ref-link">ValidationProblem</a>.</p></div>
=== "Other responses"
    <div class="common-response"><p>Refer to the common response description: <a href="#problem" class="ref-link">Problem</a>.</p></div>



## <span class="api-tag">validate</span>


<hr class="operation-separator" />

### <span class="http-post">POST</span> /validate
Parse, validate, and dry-run an MTHDS bundle.

??? note "Description"
    Diagnostic endpoint. Every verdict the validator can produce — valid or invalid — rides a 200, discriminated in the body on is_valid. Non-2xx is reserved for the cases where no verdict could be produced (a malformed request body, auth, a server fault), so a 422 here is a request-shape problem, never "the bundle is invalid".



**Input parameters**

<table>
    <thead>
        <tr>
            <th>Parameter</th>
            <th>In</th>
            <th>Type</th>
            <th>Default</th>
            <th>Nullable</th>
            <th>Description</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td class="parameter-name"><code>bearer</code></td>
            <td>header</td>
            <td>string</td>
            <td>N/A</td>
            <td>No</td>
            <td>Token semantics are implementation-defined.</td>
        </tr>
    </tbody>
</table>
<p class="request-body-title"><strong>Request body</strong></p>



=== "application/json"
    
    
    ```json
    {
        "files": {},
        "allow_signatures": true
    }
    ```
    <span class="small-note">⚠️</span>&nbsp;<em class="small-note warning">This example has been generated automatically from the schema and it is not accurate. Refer to the schema for more information.</em>

    

    ??? hint "Schema of the request body"
        ```json
        {
            "type": "object",
            "required": [
                "files"
            ],
            "properties": {
                "files": {
                    "$ref": "#/components/schemas/MethodFiles",
                    "description": "The method to validate, as its whole method tree; the runner judges every bundle and every file a bundle names."
                },
                "allow_signatures": {
                    "type": "boolean",
                    "default": false,
                    "description": "When true, the validation sweep tolerates unimplemented pipe signatures (signatures dry-run by minting a mock). Strict by default."
                }
            }
        }
        ```

<p class="responses-title"><strong>Responses</strong></p>


=== "200 OK"
    
    === "application/json"
        
        

        ??? hint "Schema of the response body"
            ```json
            {
                "description": "The 200 response of POST /validate — a produced verdict discriminated on the mandatory is_valid field. A client pattern-matches is_valid to learn the verdict; it never inspects a status code or catches an exception body. Non-2xx is a no-verdict condition (a request-shape problem, auth, a server fault), never an invalid bundle.\n",
                "oneOf": [
                    {
                        "$ref": "#/components/schemas/ValidationReport"
                    },
                    {
                        "$ref": "#/components/schemas/InvalidValidationReport"
                    }
                ]
            }
            ```
    
    
=== "422 Unprocessable Content"
    <div class="common-response"><p>Refer to the common response description: <a href="#validationproblem" class="ref-link">ValidationProblem</a>.</p></div>
=== "Other responses"
    <div class="common-response"><p>Refer to the common response description: <a href="#problem" class="ref-link">Problem</a>.</p></div>



## <span class="api-tag">discovery</span>


<hr class="operation-separator" />

### <span class="http-get">GET</span> /models
The model deck available on this runner.

**Input parameters**

<table>
    <thead>
        <tr>
            <th>Parameter</th>
            <th>In</th>
            <th>Type</th>
            <th>Default</th>
            <th>Nullable</th>
            <th>Description</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td class="parameter-name"><code>bearer</code></td>
            <td>header</td>
            <td>string</td>
            <td>N/A</td>
            <td>No</td>
            <td>Token semantics are implementation-defined.</td>
        </tr>
        <tr>
            <td class="parameter-name"><code>type</code></td>
            <td>query</td>
            <td>string</td>
            <td></td>
            <td>No</td>
            <td>Filter the deck by model category. A value outside the enum is a 422: a runner MUST NOT accept a category the protocol does not define, so a category that a later protocol version adds is a 422 from a runner of an earlier one.
</td>
        </tr>
    </tbody>
</table><p class="responses-title"><strong>Responses</strong></p>


=== "200 OK"
    
    === "application/json"
        
        
        ```json
        {
            "models": [
                {
                    "name": "string",
                    "type": "llm"
                }
            ]
        }
        ```
        <span class="small-note">⚠️</span>&nbsp;<em class="small-note warning">This example has been generated automatically from the schema and it is not accurate. Refer to the schema for more information.</em>
        
        

        ??? hint "Schema of the response body"
            ```json
            {
                "type": "object",
                "description": "The models this runner can route to. Implementations MAY add their own routing metadata (aliases, fallback chains, anything else) as additional properties — on the deck and on each model entry. A model of a family the protocol does not define, such as a vendor's own operator, is reported, if at all, under an extension property of the runner's choosing, never under an invented category and never as an entry of models without one.\n",
                "additionalProperties": true,
                "properties": {
                    "models": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "additionalProperties": true,
                            "properties": {
                                "name": {
                                    "type": "string"
                                },
                                "type": {
                                    "type": "string",
                                    "enum": [
                                        "llm",
                                        "extract",
                                        "img_gen",
                                        "search",
                                        "judgment"
                                    ],
                                    "description": "The model's category: the inline settings family of the language that the model serves, and so the pipes that can name it, as the table under \"Model categories\" on the protocol page states. A runner MUST NOT emit a value outside this enum. A client reading a model list MUST NOT fail it because an entry carries a category it does not recognize; it keeps that entry with its raw value or leaves it out. The enum is the emitter's contract: a client that derives its types or its validation from this document widens this field to any string.\n"
                                }
                            }
                        }
                    }
                }
            }
            ```
    
    
=== "422 Unprocessable Content"
    <div class="common-response"><p>Refer to the common response description: <a href="#validationproblem" class="ref-link">ValidationProblem</a>.</p></div>
=== "Other responses"
    <div class="common-response"><p>Refer to the common response description: <a href="#problem" class="ref-link">Problem</a>.</p></div>


<hr class="operation-separator" />

### <span class="http-get">GET</span> /version
Protocol and runner versions.<p class="responses-title"><strong>Responses</strong></p>


=== "200 OK"
    
    === "application/json"
        
        
        ```json
        {
            "protocol_version": "string",
            "runner_version": "string",
            "blob_store": true,
            "run_store": true
        }
        ```
        <span class="small-note">⚠️</span>&nbsp;<em class="small-note warning">This example has been generated automatically from the schema and it is not accurate. Refer to the schema for more information.</em>
        
        

        ??? hint "Schema of the response body"
            ```json
            {
                "type": "object",
                "description": "The handshake. The protocol defines protocol_version (required) plus an optional runner_version and the optional blob_store and run_store flags; implementations MAY add their own identification (a name, an underlying runtime version, anything else) as additional properties.\n",
                "required": [
                    "protocol_version"
                ],
                "additionalProperties": true,
                "properties": {
                    "protocol_version": {
                        "type": "string",
                        "description": "MTHDS Protocol version implemented."
                    },
                    "runner_version": {
                        "type": [
                            "string",
                            "null"
                        ],
                        "description": "Version of the runner serving this protocol (optional)."
                    },
                    "blob_store": {
                        "type": "boolean",
                        "default": false,
                        "description": "True when the runner keeps a blob store: it serves POST /blobs/missing and resolves hash entries in a files map. False or absent when it does not, in which case it answers any hash entry with a 422 coded request.blobs_missing, listing the hashes in params.missing_blobs, and serves no upload route, so a sender sends those files inline instead.\n"
                    },
                    "run_store": {
                        "type": "boolean",
                        "default": false,
                        "description": "True when the runner keeps a run store: it records every run it starts, serves GET /runs/{pipeline_run_id}/status and GET /runs/{pipeline_run_id}/results, and honours the Idempotency-Key header on /execute and /start. False or absent when it does not, in which case it serves neither read and ignores the header, so a client neither reads a run after the fact nor repeats a request under its key.\n"
                    }
                }
            }
            ```
    
    
=== "Other responses"
    <div class="common-response"><p>Refer to the common response description: <a href="#problem" class="ref-link">Problem</a>.</p></div>



## <span class="api-tag">blobs</span>


<hr class="operation-separator" />

### <span class="http-post">POST</span> /blobs/missing
Which of these blobs the runner lacks, and where to upload each.

??? note "Description"
    OPTIONAL — served by a runner whose /version declares blob_store true. The answer lists every blob of the request the runner does not hold, each with an upload target; a blob it holds is left out, and an empty list means there is nothing to upload. The optional digest names the tree the blobs make up: a runner that records the trees it has held in full, recording one only after checking it holds every file the tree's listing names and never taking an uploaded blob as such a record, MAY answer an empty list when it holds the tree that digest names. A hash given twice with different sizes, or a blob past the runner's limits, is a 422, refused before anything is uploaded.



**Input parameters**

<table>
    <thead>
        <tr>
            <th>Parameter</th>
            <th>In</th>
            <th>Type</th>
            <th>Default</th>
            <th>Nullable</th>
            <th>Description</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td class="parameter-name"><code>bearer</code></td>
            <td>header</td>
            <td>string</td>
            <td>N/A</td>
            <td>No</td>
            <td>Token semantics are implementation-defined.</td>
        </tr>
    </tbody>
</table>
<p class="request-body-title"><strong>Request body</strong></p>



=== "application/json"
    
    
    ```json
    {
        "blobs": [
            {
                "sha256": "string",
                "size": 0
            }
        ],
        "digest": "string"
    }
    ```
    <span class="small-note">⚠️</span>&nbsp;<em class="small-note warning">This example has been generated automatically from the schema and it is not accurate. Refer to the schema for more information.</em>

    

    ??? hint "Schema of the request body"
        ```json
        {
            "type": "object",
            "description": "The blobs a sender is about to send by hash, and optionally the tree they make up.",
            "required": [
                "blobs"
            ],
            "additionalProperties": true,
            "properties": {
                "blobs": {
                    "type": "array",
                    "items": {
                        "$ref": "#/components/schemas/BlobRef"
                    },
                    "description": "The blobs to check, each hash listed once."
                },
                "digest": {
                    "type": "string",
                    "pattern": "^sha256:[0-9a-f]{64}$",
                    "description": "The tree digest of the method tree the blobs make up (optional)."
                }
            }
        }
        ```

<p class="responses-title"><strong>Responses</strong></p>


=== "200 OK"
    
    === "application/json"
        
        
        ```json
        {
            "missing": [
                {
                    "sha256": "string",
                    "size": 0,
                    "upload": {
                        "method": "string",
                        "url": "string",
                        "headers": {}
                    }
                }
            ]
        }
        ```
        <span class="small-note">⚠️</span>&nbsp;<em class="small-note warning">This example has been generated automatically from the schema and it is not accurate. Refer to the schema for more information.</em>
        
        

        ??? hint "Schema of the response body"
            ```json
            {
                "type": "object",
                "description": "The blobs of the request the runner does not hold. Extension-open.",
                "required": [
                    "missing"
                ],
                "additionalProperties": true,
                "properties": {
                    "missing": {
                        "type": "array",
                        "items": {
                            "$ref": "#/components/schemas/MissingBlob"
                        }
                    }
                }
            }
            ```
    
    
=== "422 Unprocessable Content"
    <div class="common-response"><p>Refer to the common response description: <a href="#validationproblem" class="ref-link">ValidationProblem</a>.</p></div>
=== "Other responses"
    <div class="common-response"><p>Refer to the common response description: <a href="#problem" class="ref-link">Problem</a>.</p></div>


<hr class="operation-separator" />

### <span class="http-put">PUT</span> /blobs/<span class="route-param">{sha256}</span>
Upload one blob's bytes to a runner that stores them itself.

??? note "Description"
    OPTIONAL — served by a runner that keeps a blob store and stores uploaded bytes itself, as the upload target its POST /blobs/missing answers name. The body is the blob's bytes and nothing else. A body whose SHA-256 differs from the path is a 422. A blob is written once and never changed, so uploading bytes the runner already holds succeeds without changing anything.



**Input parameters**

<table>
    <thead>
        <tr>
            <th>Parameter</th>
            <th>In</th>
            <th>Type</th>
            <th>Default</th>
            <th>Nullable</th>
            <th>Description</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td class="parameter-name"><code>bearer</code></td>
            <td>header</td>
            <td>string</td>
            <td>N/A</td>
            <td>No</td>
            <td>Token semantics are implementation-defined.</td>
        </tr>
        <tr>
            <td class="parameter-name"><code>sha256</code></td>
            <td>path</td>
            <td>string</td>
            <td></td>
            <td>No</td>
            <td>The SHA-256 of the body, in lowercase hexadecimal.</td>
        </tr>
    </tbody>
</table>
<p class="request-body-title"><strong>Request body</strong></p>



=== "application/octet-stream"
    
    
    ```json
    "TG9yZW0gaXBzdW0gZG9sb3Igc2l0IGFtZXQ="
    ```
    <span class="small-note">⚠️</span>&nbsp;<em class="small-note warning">This example has been generated automatically from the schema and it is not accurate. Refer to the schema for more information.</em>

    

    ??? hint "Schema of the request body"
        ```json
        {
            "type": "string",
            "format": "binary"
        }
        ```

<p class="responses-title"><strong>Responses</strong></p>


=== "204 No Content"
=== "422 Unprocessable Content"
    <div class="common-response"><p>Refer to the common response description: <a href="#validationproblem" class="ref-link">ValidationProblem</a>.</p></div>
=== "Other responses"
    <div class="common-response"><p>Refer to the common response description: <a href="#problem" class="ref-link">Problem</a>.</p></div>



## <span class="api-tag">runs</span>


<hr class="operation-separator" />

### <span class="http-get">GET</span> /runs/<span class="route-param">{pipeline_run_id}</span>/status
A run's status, and its problem once it has failed.

??? note "Description"
    OPTIONAL — served by a runner whose /version declares run_store true. Answers 200 for every run the caller can read, whatever became of it: a failed run's problem rides inside the answer as error rather than failing the read. A runner may set Retry-After on the 200 of a run that has not ended, to say when to read it again. An id naming no run the caller can read, a run the caller may not read included, is a 404 coded run.not_found.



**Input parameters**

<table>
    <thead>
        <tr>
            <th>Parameter</th>
            <th>In</th>
            <th>Type</th>
            <th>Default</th>
            <th>Nullable</th>
            <th>Description</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td class="parameter-name"><code>bearer</code></td>
            <td>header</td>
            <td>string</td>
            <td>N/A</td>
            <td>No</td>
            <td>Token semantics are implementation-defined.</td>
        </tr>
        <tr>
            <td class="parameter-name"><code>pipeline_run_id</code></td>
            <td>path</td>
            <td>string</td>
            <td></td>
            <td>No</td>
            <td>The run's identifier, as /execute or /start answered it.</td>
        </tr>
    </tbody>
</table><p class="responses-title"><strong>Responses</strong></p>


=== "200 OK"
    
    === "application/json"
        
        
        ```json
        {
            "pipeline_run_id": "string",
            "status": "pending",
            "error": {
                "type": "string",
                "title": "string",
                "status": 0,
                "detail": "string",
                "code": "string",
                "domain": "input",
                "retry": "no",
                "retry_after": 10.12,
                "next_step": {
                    "kind": "retry",
                    "detail": "string"
                },
                "params": {
                    "missing_blobs": [
                        "string"
                    ]
                },
                "location": {
                    "pipe": "string",
                    "path": [
                        "string"
                    ],
                    "input": "string",
                    "field": "string",
                    "item": 0,
                    "attempt": 0,
                    "file": "string",
                    "line": 0,
                    "column": 0
                },
                "errors": [
                    {
                        "code": null,
                        "detail": "string",
                        "params": null,
                        "location": null,
                        "suggestions": [
                            "string"
                        ],
                        "suggested_fix": {
                            "fix_code": "string",
                            "description": "string",
                            "safety": "safe",
                            "file": "string",
                            "ops": [
                                null
                            ]
                        }
                    }
                ],
                "pipeline_run_id": "string",
                "run_error": null
            }
        }
        ```
        <span class="small-note">⚠️</span>&nbsp;<em class="small-note warning">This example has been generated automatically from the schema and it is not accurate. Refer to the schema for more information.</em>
        
        

        ??? hint "Schema of the response body"
            ```json
            {
                "type": "object",
                "description": "The 200 of the status read of a runner that keeps a run store: the run's id, its status, and its problem once it has failed. Extension-open; an unset member is left out, never written as null.\n",
                "required": [
                    "pipeline_run_id",
                    "status"
                ],
                "additionalProperties": true,
                "properties": {
                    "pipeline_run_id": {
                        "type": "string",
                        "description": "The run identifier, as /execute or /start answered it."
                    },
                    "status": {
                        "$ref": "#/components/schemas/RunStatus"
                    },
                    "error": {
                        "$ref": "#/components/schemas/Problem",
                        "description": "The run's own problem, as the run's record keeps it, without status since it is not the body of a response. Present exactly when status is failed; its code says why the run ended without output, such as run.cancelled, run.timed_out or run.lost.\n"
                    }
                }
            }
            ```
    
    

    **Response headers**

    | Name | Description | Schema |
    | --- | --- | --- |
    | `Retry-After` | Seconds to wait before reading a run that has not ended again (optional). |<span class="integer-type">integer</span> |

    
=== "404 Not Found"
    <div class="common-response"><p>Refer to the common response description: <a href="#runnotfoundproblem" class="ref-link">RunNotFoundProblem</a>.</p></div>
=== "Other responses"
    <div class="common-response"><p>Refer to the common response description: <a href="#problem" class="ref-link">Problem</a>.</p></div>


<hr class="operation-separator" />

### <span class="http-get">GET</span> /runs/<span class="route-param">{pipeline_run_id}</span>/results
A completed run's output, as /execute answers it.

??? note "Description"
    OPTIONAL — served by a runner whose /version declares run_store true. A completed run is answered with a 200 whose body is the one /execute answers with, its pipeline_run_id and its pipe_output. Any other run is a problem: a 409 coded run.not_finished before the run has ended, a 409 coded run.failed, carrying the run's own problem as run_error, once it has ended without output, and a 404 coded run.results_not_stored for a completed run whose output travelled in /execute's answer and was not kept. An id naming no run the caller can read is a 404 coded run.not_found.



**Input parameters**

<table>
    <thead>
        <tr>
            <th>Parameter</th>
            <th>In</th>
            <th>Type</th>
            <th>Default</th>
            <th>Nullable</th>
            <th>Description</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td class="parameter-name"><code>bearer</code></td>
            <td>header</td>
            <td>string</td>
            <td>N/A</td>
            <td>No</td>
            <td>Token semantics are implementation-defined.</td>
        </tr>
        <tr>
            <td class="parameter-name"><code>pipeline_run_id</code></td>
            <td>path</td>
            <td>string</td>
            <td></td>
            <td>No</td>
            <td>The run's identifier, as /execute or /start answered it.</td>
        </tr>
    </tbody>
</table><p class="responses-title"><strong>Responses</strong></p>


=== "200 OK"
    
    === "application/json"
        
        
        ```json
        {
            "pipeline_run_id": "string",
            "pipe_output": {}
        }
        ```
        <span class="small-note">⚠️</span>&nbsp;<em class="small-note warning">This example has been generated automatically from the schema and it is not accurate. Refer to the schema for more information.</em>
        
        

        ??? hint "Schema of the response body"
            ```json
            {
                "type": "object",
                "description": "POST /execute 200 — the completed run, and the 200 of the results read of a runner that keeps a run store, which answers a completed run with the body /execute answers with. Two base fields: the server-generated authoritative pipeline_run_id and the method's pipe_output (always present — a completed run has output, either a value or an explicit absence document). Extension-open: anything more an implementation returns (a run state, timestamps, output naming) is an extension on top.\n",
                "additionalProperties": true,
                "required": [
                    "pipeline_run_id",
                    "pipe_output"
                ],
                "properties": {
                    "pipeline_run_id": {
                        "type": "string",
                        "description": "The run identifier — server-generated and authoritative."
                    },
                    "pipe_output": {
                        "description": "The method's serialized output (working memory of serialized stuffs).",
                        "type": "object"
                    }
                }
            }
            ```
    
    
=== "404 Not Found"
    
    === "application/problem+json"
        
        

        ??? hint "Schema of the response body"
            ```json
            {
                "allOf": [
                    {
                        "$ref": "#/components/schemas/Problem"
                    },
                    {
                        "required": [
                            "status"
                        ]
                    }
                ]
            }
            ```
    
    
=== "409 Conflict"
    
    === "application/problem+json"
        
        

        ??? hint "Schema of the response body"
            ```json
            {
                "allOf": [
                    {
                        "$ref": "#/components/schemas/Problem"
                    },
                    {
                        "required": [
                            "status"
                        ]
                    }
                ]
            }
            ```
    
    
=== "Other responses"
    <div class="common-response"><p>Refer to the common response description: <a href="#problem" class="ref-link">Problem</a>.</p></div>




---
## Schemas


### Base64FileEntry

<table>
    <thead>
        <tr>
            <th>Name</th>
            <th>Type</th>
            <th>Description</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td><code>base64</code></td>
            <td><span class="string-type">string</span></td>
            <td></td>
        </tr>
    </tbody>
</table>



### BlobRef

<table>
    <thead>
        <tr>
            <th>Name</th>
            <th>Type</th>
            <th>Description</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td><code>sha256</code></td>
            <td><span class="string-type">string</span></td>
            <td></td>
        </tr>
        <tr>
            <td><code>size</code></td>
            <td><span class="integer-type">integer</span></td>
            <td>The length of the bytes, a JSON integer written without a fraction or an exponent. A size written 13.0 is refused, although JSON Schema's integer type admits it.
</td>
        </tr>
    </tbody>
</table>



### DeleteKeyOp

<table>
    <thead>
        <tr>
            <th>Name</th>
            <th>Type</th>
            <th>Description</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td><code>key</code></td>
            <td><span class="string-type">string</span></td>
            <td></td>
        </tr>
        <tr>
            <td><code>kind</code></td>
            <td><span class="string-type">string</span></td>
            <td></td>
        </tr>
        <tr>
            <td><code>table_path</code></td>
            <td><a href="#tablepath" class="ref-link">TablePath</a></td>
            <td></td>
        </tr>
    </tbody>
</table>



### DeleteTableOp

<table>
    <thead>
        <tr>
            <th>Name</th>
            <th>Type</th>
            <th>Description</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td><code>kind</code></td>
            <td><span class="string-type">string</span></td>
            <td></td>
        </tr>
        <tr>
            <td><code>table_path</code></td>
            <td>Array&lt;<span class="string-type">string</span>&gt;</td>
            <td>The key path of the table itself, from the document root.</td>
        </tr>
    </tbody>
</table>



### EnsureTableOp

<table>
    <thead>
        <tr>
            <th>Name</th>
            <th>Type</th>
            <th>Description</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td><code>kind</code></td>
            <td><span class="string-type">string</span></td>
            <td></td>
        </tr>
        <tr>
            <td><code>table_path</code></td>
            <td>Array&lt;<span class="string-type">string</span>&gt;</td>
            <td>The key path of the table itself, from the document root.</td>
        </tr>
    </tbody>
</table>



### FileEntry
<span>Type: </span>



### FixOp
<span>Type: </span>



### HashFileEntry

<table>
    <thead>
        <tr>
            <th>Name</th>
            <th>Type</th>
            <th>Description</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td><code>sha256</code></td>
            <td><span class="string-type">string</span></td>
            <td>The SHA-256 of the bytes</td>
        </tr>
        <tr>
            <td><code>size</code></td>
            <td><span class="integer-type">integer</span></td>
            <td>The length of the bytes, a JSON integer written without a fraction or an exponent. A size written 13.0 is refused, although JSON Schema's integer type admits it.
</td>
        </tr>
    </tbody>
</table>



### InvalidValidationReport

<table>
    <thead>
        <tr>
            <th>Name</th>
            <th>Type</th>
            <th>Description</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td><code>errors</code></td>
            <td>Array&lt;<a href="#problemitem" class="ref-link">ProblemItem</a>&gt;</td>
            <td>One problem item per fault, each with its own code, detail, params and location — non-empty on every invalid verdict. An unset member of an item is left out, never written as null.
</td>
        </tr>
        <tr>
            <td><code>is_runnable</code></td>
            <td><span class="boolean-type">boolean</span></td>
            <td>An invalid bundle is never runnable.</td>
        </tr>
        <tr>
            <td><code>is_valid</code></td>
            <td><span class="boolean-type">boolean</span></td>
            <td>Discriminant — the bundle is invalid.</td>
        </tr>
        <tr>
            <td><code>message</code></td>
            <td><span class="string-type">string</span></td>
            <td>Human-readable summary of the verdict.</td>
        </tr>
        <tr>
            <td><code>pending_signatures</code></td>
            <td>Array&lt;<span class="string-type">string</span>&gt;</td>
            <td>Outstanding signatures (best-effort; empty when no library could be assembled).</td>
        </tr>
        <tr>
            <td><code>warnings</code></td>
            <td>Array&lt;<a href="#problemitem" class="ref-link">ProblemItem</a>&gt;</td>
            <td>Advisory findings in the same item schema, which do not make the verdict invalid. Absent or empty when there are none.
</td>
        </tr>
    </tbody>
</table>



### MethodFiles




### MissingBlob

<table>
    <thead>
        <tr>
            <th>Name</th>
            <th>Type</th>
            <th>Description</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td><code>sha256</code></td>
            <td><span class="string-type">string</span></td>
            <td></td>
        </tr>
        <tr>
            <td><code>size</code></td>
            <td><span class="integer-type">integer</span></td>
            <td>The length of the bytes, a JSON integer written without a fraction or an exponent. A size written 13.0 is refused, although JSON Schema's integer type admits it.
</td>
        </tr>
        <tr>
            <td><code>upload</code></td>
            <td><a href="#uploadtarget" class="ref-link">UploadTarget</a></td>
            <td></td>
        </tr>
    </tbody>
</table>



### MissingBlobsRequest

<table>
    <thead>
        <tr>
            <th>Name</th>
            <th>Type</th>
            <th>Description</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td><code>blobs</code></td>
            <td>Array&lt;<a href="#blobref" class="ref-link">BlobRef</a>&gt;</td>
            <td>The blobs to check, each hash listed once.</td>
        </tr>
        <tr>
            <td><code>digest</code></td>
            <td><span class="string-type">string</span></td>
            <td>The tree digest of the method tree the blobs make up (optional).</td>
        </tr>
    </tbody>
</table>



### MissingBlobsResult

<table>
    <thead>
        <tr>
            <th>Name</th>
            <th>Type</th>
            <th>Description</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td><code>missing</code></td>
            <td>Array&lt;<a href="#missingblob" class="ref-link">MissingBlob</a>&gt;</td>
            <td></td>
        </tr>
    </tbody>
</table>



### ModelDeck

<table>
    <thead>
        <tr>
            <th>Name</th>
            <th>Type</th>
            <th>Description</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td><code>models</code></td>
            <td>Array&lt;<em>Properties: </em><code>name, type</code>&gt;</td>
            <td></td>
        </tr>
    </tbody>
</table>



### MoveKeyOp

<table>
    <thead>
        <tr>
            <th>Name</th>
            <th>Type</th>
            <th>Description</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td><code>key</code></td>
            <td><span class="string-type">string</span></td>
            <td></td>
        </tr>
        <tr>
            <td><code>kind</code></td>
            <td><span class="string-type">string</span></td>
            <td></td>
        </tr>
        <tr>
            <td><code>new_key</code></td>
            <td><span class="string-type">string</span></td>
            <td></td>
        </tr>
        <tr>
            <td><code>new_table_path</code></td>
            <td><a href="#tablepath" class="ref-link">TablePath</a></td>
            <td></td>
        </tr>
        <tr>
            <td><code>table_path</code></td>
            <td><a href="#tablepath" class="ref-link">TablePath</a></td>
            <td></td>
        </tr>
    </tbody>
</table>



### NextStep

<table>
    <thead>
        <tr>
            <th>Name</th>
            <th>Type</th>
            <th>Description</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td><code>detail</code></td>
            <td><span class="string-type">string</span></td>
            <td>The step, in one sentence a person can read.</td>
        </tr>
        <tr>
            <td><code>kind</code></td>
            <td><a href="#stepkind" class="ref-link">StepKind</a></td>
            <td></td>
        </tr>
    </tbody>
</table>



### Problem

<table>
    <thead>
        <tr>
            <th>Name</th>
            <th>Type</th>
            <th>Description</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td><code>code</code></td>
            <td><a href="#problemcode" class="ref-link">ProblemCode</a></td>
            <td></td>
        </tr>
        <tr>
            <td><code>detail</code></td>
            <td><span class="string-type">string</span></td>
            <td>This occurrence, in one or two sentences a person can read. A client never parses it: every fact it states is in params or location.
</td>
        </tr>
        <tr>
            <td><code>domain</code></td>
            <td><a href="#problemdomain" class="ref-link">ProblemDomain</a></td>
            <td></td>
        </tr>
        <tr>
            <td><code>errors</code></td>
            <td>Array&lt;<a href="#problemitem" class="ref-link">ProblemItem</a>&gt;</td>
            <td>One item per fault, for a problem with several, such as a method that does not validate. Absent when the problem has a single fault.
</td>
        </tr>
        <tr>
            <td><code>location</code></td>
            <td><a href="#problemlocation" class="ref-link">ProblemLocation</a></td>
            <td></td>
        </tr>
        <tr>
            <td><code>next_step</code></td>
            <td><a href="#nextstep" class="ref-link">NextStep</a></td>
            <td></td>
        </tr>
        <tr>
            <td><code>params</code></td>
            <td><a href="#problemparams" class="ref-link">ProblemParams</a></td>
            <td></td>
        </tr>
        <tr>
            <td><code>pipeline_run_id</code></td>
            <td><span class="string-type">string</span></td>
            <td>The run the error belongs to, as /execute and /start name it. Present when a run exists.
</td>
        </tr>
        <tr>
            <td><code>retry</code></td>
            <td><a href="#retryverdict" class="ref-link">RetryVerdict</a></td>
            <td></td>
        </tr>
        <tr>
            <td><code>retry_after</code></td>
            <td><span class="number-type">number</span></td>
            <td>Seconds to wait before repeating the operation, when known. Set only beside a retry of yes.
</td>
        </tr>
        <tr>
            <td><code>run_error</code></td>
            <td><a href="#problem" class="ref-link">Problem</a></td>
            <td>The run's own problem, nested, on the problem coded run.failed that the results read of a runner keeping a run store answers for a run that ended without output. It is the problem the run's record keeps, without status, and it says why the run failed, while the problem holding it is about the read. Absent on every other problem.
</td>
        </tr>
        <tr>
            <td><code>status</code></td>
            <td><span class="integer-type">integer</span></td>
            <td>The HTTP status of the response this problem is the body of. A runner sets it on every response, so the problem responses of this document require it; a problem kept elsewhere, such as in a run's record, leaves it out.
</td>
        </tr>
        <tr>
            <td><code>title</code></td>
            <td><span class="string-type">string</span></td>
            <td>The code's short title, the same for every occurrence of the code.</td>
        </tr>
        <tr>
            <td><code>type</code></td>
            <td><span class="string-type">string</span>(<span class="uri-format format">uri</span>)</td>
            <td>The code's documentation page, derived from the code and its owner's base URL: https://mthds.ai/errors/<code> for a core code, and for an extension code the base URL its prefix is registered with, a slash and the whole code. It names what code names, one to one; a client branches on code.
</td>
        </tr>
    </tbody>
</table>



### ProblemCode
<span>Type: </span><span class="string-type">string</span>



### ProblemDomain
<span>Type: </span><span class="string-type">string</span>



### ProblemItem

<table>
    <thead>
        <tr>
            <th>Name</th>
            <th>Type</th>
            <th>Description</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td><code>code</code></td>
            <td><a href="#problemcode" class="ref-link">ProblemCode</a></td>
            <td></td>
        </tr>
        <tr>
            <td><code>detail</code></td>
            <td><span class="string-type">string</span></td>
            <td>This fault, in one or two sentences a person can read.</td>
        </tr>
        <tr>
            <td><code>location</code></td>
            <td><a href="#problemlocation" class="ref-link">ProblemLocation</a></td>
            <td></td>
        </tr>
        <tr>
            <td><code>params</code></td>
            <td><a href="#problemparams" class="ref-link">ProblemParams</a></td>
            <td></td>
        </tr>
        <tr>
            <td><code>suggested_fix</code></td>
            <td><a href="#suggestedfix" class="ref-link">SuggestedFix</a></td>
            <td></td>
        </tr>
        <tr>
            <td><code>suggestions</code></td>
            <td>Array&lt;<span class="string-type">string</span>&gt;</td>
            <td>The names a near miss most likely meant, the likeliest first.</td>
        </tr>
    </tbody>
</table>



### ProblemLocation

<table>
    <thead>
        <tr>
            <th>Name</th>
            <th>Type</th>
            <th>Description</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td><code>attempt</code></td>
            <td><span class="integer-type">integer</span></td>
            <td>The attempt that failed, counted from 1.</td>
        </tr>
        <tr>
            <td><code>column</code></td>
            <td><span class="integer-type">integer</span></td>
            <td>The column in line, counted from 1.</td>
        </tr>
        <tr>
            <td><code>field</code></td>
            <td><span class="string-type">string</span></td>
            <td>A dotted path inside an input or a request body.</td>
        </tr>
        <tr>
            <td><code>file</code></td>
            <td><span class="string-type">string</span></td>
            <td>The tree path of the method's file the error is in.</td>
        </tr>
        <tr>
            <td><code>input</code></td>
            <td><span class="string-type">string</span></td>
            <td>The name of the input the error concerns.</td>
        </tr>
        <tr>
            <td><code>item</code></td>
            <td><span class="integer-type">integer</span></td>
            <td>The index of the batch item that failed, counted from 0.</td>
        </tr>
        <tr>
            <td><code>line</code></td>
            <td><span class="integer-type">integer</span></td>
            <td>The line in file, counted from 1.</td>
        </tr>
        <tr>
            <td><code>path</code></td>
            <td>Array&lt;<span class="string-type">string</span>&gt;</td>
            <td>The pipe codes from the run's main pipe down to the failing one.</td>
        </tr>
        <tr>
            <td><code>pipe</code></td>
            <td><span class="string-type">string</span></td>
            <td>The failing pipe's code.</td>
        </tr>
    </tbody>
</table>



### ProblemParams

<table>
    <thead>
        <tr>
            <th>Name</th>
            <th>Type</th>
            <th>Description</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td><code>missing_blobs</code></td>
            <td>Array&lt;<span class="string-type">string</span>&gt;</td>
            <td>Carried by the protocol's own refusal of hash entries, request.blobs_missing: every hash of the request the runner does not hold, in lowercase hexadecimal.
</td>
        </tr>
    </tbody>
</table>



### RemapValueOp

<table>
    <thead>
        <tr>
            <th>Name</th>
            <th>Type</th>
            <th>Description</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td><code>key</code></td>
            <td><span class="string-type">string</span></td>
            <td></td>
        </tr>
        <tr>
            <td><code>kind</code></td>
            <td><span class="string-type">string</span></td>
            <td></td>
        </tr>
        <tr>
            <td><code>mapping</code></td>
            <td></td>
            <td></td>
        </tr>
        <tr>
            <td><code>table_path</code></td>
            <td><a href="#tablepath" class="ref-link">TablePath</a></td>
            <td></td>
        </tr>
    </tbody>
</table>



### RenameTableKeyOp

<table>
    <thead>
        <tr>
            <th>Name</th>
            <th>Type</th>
            <th>Description</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td><code>key</code></td>
            <td><span class="string-type">string</span></td>
            <td></td>
        </tr>
        <tr>
            <td><code>kind</code></td>
            <td><span class="string-type">string</span></td>
            <td></td>
        </tr>
        <tr>
            <td><code>new_key</code></td>
            <td><span class="string-type">string</span></td>
            <td></td>
        </tr>
        <tr>
            <td><code>table_path</code></td>
            <td><a href="#tablepath" class="ref-link">TablePath</a></td>
            <td></td>
        </tr>
    </tbody>
</table>



### RetryVerdict
<span>Type: </span><span class="string-type">string</span>



### RunRead

<table>
    <thead>
        <tr>
            <th>Name</th>
            <th>Type</th>
            <th>Description</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td><code>error</code></td>
            <td><a href="#problem" class="ref-link">Problem</a></td>
            <td>The run's own problem, as the run's record keeps it, without status since it is not the body of a response. Present exactly when status is failed; its code says why the run ended without output, such as run.cancelled, run.timed_out or run.lost.
</td>
        </tr>
        <tr>
            <td><code>pipeline_run_id</code></td>
            <td><span class="string-type">string</span></td>
            <td>The run identifier, as /execute or /start answered it.</td>
        </tr>
        <tr>
            <td><code>status</code></td>
            <td><a href="#runstatus" class="ref-link">RunStatus</a></td>
            <td></td>
        </tr>
    </tbody>
</table>



### RunRequest

<table>
    <thead>
        <tr>
            <th>Name</th>
            <th>Type</th>
            <th>Description</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td><code>dynamic_output_concept_ref</code></td>
            <td><span class="string-type">string</span> &#124; <span class="null-type">null</span></td>
            <td>Override for the dynamic output concept reference.</td>
        </tr>
        <tr>
            <td><code>files</code></td>
            <td></td>
            <td>The method to load, as its whole method tree. Implementations bound a file's size, the tree's file count and total size, and the total of the inline entries.</td>
        </tr>
        <tr>
            <td><code>inputs</code></td>
            <td></td>
            <td>Method inputs: map of input name to { concept, content }. Content shapes follow the concept's structure; content validation is deliberately loose here and strict inside the runtime.</td>
        </tr>
        <tr>
            <td><code>output_multiplicity</code></td>
            <td></td>
            <td>Output multiplicity override (false/true or an explicit count).</td>
        </tr>
        <tr>
            <td><code>output_name</code></td>
            <td><span class="string-type">string</span> &#124; <span class="null-type">null</span></td>
            <td>Name of the output slot to return as the main output.</td>
        </tr>
        <tr>
            <td><code>pipe_code</code></td>
            <td><span class="string-type">string</span> &#124; <span class="null-type">null</span></td>
            <td>Code of the pipe to execute (a pipe the runner already holds, or one defined in a bundle of files).</td>
        </tr>
    </tbody>
</table>



### RunResultExecute

<table>
    <thead>
        <tr>
            <th>Name</th>
            <th>Type</th>
            <th>Description</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td><code>pipe_output</code></td>
            <td></td>
            <td>The method's serialized output (working memory of serialized stuffs).</td>
        </tr>
        <tr>
            <td><code>pipeline_run_id</code></td>
            <td><span class="string-type">string</span></td>
            <td>The run identifier — server-generated and authoritative.</td>
        </tr>
    </tbody>
</table>



### RunResultStart

<table>
    <thead>
        <tr>
            <th>Name</th>
            <th>Type</th>
            <th>Description</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td><code>pipeline_run_id</code></td>
            <td><span class="string-type">string</span></td>
            <td>The run identifier — server-generated and authoritative.</td>
        </tr>
    </tbody>
</table>



### RunStatus
<span>Type: </span><span class="string-type">string</span>



### SetKeyOp

<table>
    <thead>
        <tr>
            <th>Name</th>
            <th>Type</th>
            <th>Description</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td><code>key</code></td>
            <td><span class="string-type">string</span></td>
            <td></td>
        </tr>
        <tr>
            <td><code>kind</code></td>
            <td><span class="string-type">string</span></td>
            <td></td>
        </tr>
        <tr>
            <td><code>table_path</code></td>
            <td><a href="#tablepath" class="ref-link">TablePath</a></td>
            <td></td>
        </tr>
        <tr>
            <td><code>value</code></td>
            <td><a href="#tomlvalue" class="ref-link">TomlValue</a></td>
            <td></td>
        </tr>
    </tbody>
</table>



### StepKind
<span>Type: </span><span class="string-type">string</span>



### SuggestedFix

<table>
    <thead>
        <tr>
            <th>Name</th>
            <th>Type</th>
            <th>Description</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td><code>description</code></td>
            <td><span class="string-type">string</span></td>
            <td>What the fix does, in one sentence a person can read.</td>
        </tr>
        <tr>
            <td><code>file</code></td>
            <td><span class="string-type">string</span></td>
            <td>The tree path of the bundle the operations patch. When absent, they patch the file the item's location names.
</td>
        </tr>
        <tr>
            <td><code>fix_code</code></td>
            <td><span class="string-type">string</span></td>
            <td>The implementation's kebab-case name for the rule that produced the fix, such as match-sequence-output.</td>
        </tr>
        <tr>
            <td><code>ops</code></td>
            <td>Array&lt;<a href="#fixop" class="ref-link">FixOp</a>&gt;</td>
            <td></td>
        </tr>
        <tr>
            <td><code>safety</code></td>
            <td><span class="string-type">string</span></td>
            <td>safe: the fix may be applied without asking anyone. unsafe: a likely correction that a person or an agent confirms before it is applied. A reader that meets a value it does not know reads it as unsafe.
</td>
        </tr>
    </tbody>
</table>



### TablePath
<span>Type: </span>Array&lt;<span class="string-type">string</span>&gt;



### TomlValue
<span>Type: </span>



### UnknownFixOp

<table>
    <thead>
        <tr>
            <th>Name</th>
            <th>Type</th>
            <th>Description</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td><code>kind</code></td>
            <td><span class="string-type">string</span></td>
            <td></td>
        </tr>
    </tbody>
</table>



### UploadTarget

<table>
    <thead>
        <tr>
            <th>Name</th>
            <th>Type</th>
            <th>Description</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td><code>headers</code></td>
            <td></td>
            <td>The headers to send, exactly.</td>
        </tr>
        <tr>
            <td><code>method</code></td>
            <td><span class="string-type">string</span></td>
            <td>The HTTP method, such as PUT.</td>
        </tr>
        <tr>
            <td><code>url</code></td>
            <td><span class="string-type">string</span>(<span class="uri-format format">uri</span>)</td>
            <td></td>
        </tr>
    </tbody>
</table>



### ValidateRequest

<table>
    <thead>
        <tr>
            <th>Name</th>
            <th>Type</th>
            <th>Description</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td><code>allow_signatures</code></td>
            <td><span class="boolean-type">boolean</span></td>
            <td>When true, the validation sweep tolerates unimplemented pipe signatures (signatures dry-run by minting a mock). Strict by default.</td>
        </tr>
        <tr>
            <td><code>files</code></td>
            <td><a href="#methodfiles" class="ref-link">MethodFiles</a></td>
            <td>The method to validate, as its whole method tree; the runner judges every bundle and every file a bundle names.</td>
        </tr>
    </tbody>
</table>



### ValidationReport

<table>
    <thead>
        <tr>
            <th>Name</th>
            <th>Type</th>
            <th>Description</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td><code>is_runnable</code></td>
            <td><span class="boolean-type">boolean</span></td>
            <td>Whether the validated library is complete enough to run — false when pipe signatures remain unimplemented (a runnability fact, not an error).
</td>
        </tr>
        <tr>
            <td><code>is_valid</code></td>
            <td><span class="boolean-type">boolean</span></td>
            <td>Discriminant — the bundle is valid.</td>
        </tr>
        <tr>
            <td><code>pending_signatures</code></td>
            <td>Array&lt;<span class="string-type">string</span>&gt;</td>
            <td>Refs of pipes still declared as unimplemented signatures.</td>
        </tr>
        <tr>
            <td><code>warnings</code></td>
            <td>Array&lt;<a href="#problemitem" class="ref-link">ProblemItem</a>&gt;</td>
            <td>Advisory findings, one problem item each, which never make the bundle invalid. Absent or empty when there are none. An unset member of an item is left out, never written as null, as in errors.
</td>
        </tr>
    </tbody>
</table>



### ValidationResult
<span>Type: </span>



### VersionInfo

<table>
    <thead>
        <tr>
            <th>Name</th>
            <th>Type</th>
            <th>Description</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td><code>blob_store</code></td>
            <td><span class="boolean-type">boolean</span></td>
            <td>True when the runner keeps a blob store: it serves POST /blobs/missing and resolves hash entries in a files map. False or absent when it does not, in which case it answers any hash entry with a 422 coded request.blobs_missing, listing the hashes in params.missing_blobs, and serves no upload route, so a sender sends those files inline instead.
</td>
        </tr>
        <tr>
            <td><code>protocol_version</code></td>
            <td><span class="string-type">string</span></td>
            <td>MTHDS Protocol version implemented.</td>
        </tr>
        <tr>
            <td><code>run_store</code></td>
            <td><span class="boolean-type">boolean</span></td>
            <td>True when the runner keeps a run store: it records every run it starts, serves GET /runs/{pipeline_run_id}/status and GET /runs/{pipeline_run_id}/results, and honours the Idempotency-Key header on /execute and /start. False or absent when it does not, in which case it serves neither read and ignores the header, so a client neither reads a run after the fact nor repeats a request under its key.
</td>
        </tr>
        <tr>
            <td><code>runner_version</code></td>
            <td><span class="string-type">string</span> &#124; <span class="null-type">null</span></td>
            <td>Version of the runner serving this protocol (optional).</td>
        </tr>
    </tbody>
</table>



## Common responses

This section describes common responses that are reused across operations.



### Problem
An RFC 9457 problem document carrying the MTHDS core members. As the body of an HTTP response it always carries status, which the shared Problem schema leaves optional for a problem kept elsewhere, such as in a run's record.


<p class="message-separator"></p>

=== "application/problem+json"
    
    

    ??? hint "Schema of the response body"
        ```json
        {
            "allOf": [
                {
                    "$ref": "#/components/schemas/Problem"
                },
                {
                    "required": [
                        "status"
                    ]
                }
            ]
        }
        ```






### ValidationProblem
A 422 problem document. On /execute and /start a method that does not validate also lands here, one item per fault in errors; on /validate an invalid method is a 200 verdict, so there a 422 is about the request alone. A request whose files map is not a tree is a 422 naming the offending path, and a request naming a hash entry the runner does not hold, or any hash entry when it keeps no blob store, is a 422 coded request.blobs_missing whose params.missing_blobs lists each such hash. Like every problem response, it always carries status.


<p class="message-separator"></p>

=== "application/problem+json"
    
    

    ??? hint "Schema of the response body"
        ```json
        {
            "allOf": [
                {
                    "$ref": "#/components/schemas/Problem"
                },
                {
                    "required": [
                        "status"
                    ]
                }
            ]
        }
        ```






### IdempotencyProblem
A 409 problem about the request's Idempotency-Key, answered only by a runner whose /version declares run_store true: request.idempotency_conflict for a different request under a held key; request.idempotency_key_in_use for the same request while the first one is still being handled and has started no run, with retry_after when the runner knows how long to wait; and, on /execute, run.answer_not_kept for the same request once its run has ended and the runner kept neither its answer nor its output. Like every problem response, it always carries status.


<p class="message-separator"></p>

=== "application/problem+json"
    
    

    ??? hint "Schema of the response body"
        ```json
        {
            "allOf": [
                {
                    "$ref": "#/components/schemas/Problem"
                },
                {
                    "required": [
                        "status"
                    ]
                }
            ]
        }
        ```






### RunNotFoundProblem
A 404 problem coded run.not_found: the id names no run the caller can read. A runner answers an id naming a run the caller may not read exactly as one naming no run, so an id never tells a caller about a run it cannot read. Like every problem response, it always carries status.


<p class="message-separator"></p>

=== "application/problem+json"
    
    

    ??? hint "Schema of the response body"
        ```json
        {
            "allOf": [
                {
                    "$ref": "#/components/schemas/Problem"
                },
                {
                    "required": [
                        "status"
                    ]
                }
            ]
        }
        ```






## Common parameters

This section describes common parameters that are reused across operations.



### IdempotencyKey

<table>
    <thead>
        <tr>
            <th>Name</th>
            <th>In</th>
            <th>Type</th>
            <th>Default</th>
            <th>Nullable</th>
            <th>Description</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td class="parameter-name"><code>Idempotency-Key</code></td>
            <td>header</td>
            <td>string</td>
            <td></td>
            <td>No</td>
            <td></td>
        </tr>
    </tbody>
</table>



### PipelineRunId

<table>
    <thead>
        <tr>
            <th>Name</th>
            <th>In</th>
            <th>Type</th>
            <th>Default</th>
            <th>Nullable</th>
            <th>Description</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td class="parameter-name"><code>pipeline_run_id</code></td>
            <td>path</td>
            <td>string</td>
            <td></td>
            <td>No</td>
            <td></td>
        </tr>
    </tbody>
</table>



## Security schemes

<table>
    <thead>
        <tr>
            <th>Name</th>
            <th>Type</th>
            <th>Scheme</th>
            <th>Description</th>
        </tr>
    </thead>
    <tbody>
        
        <tr>
            <td>bearer</td>
            <td>http</td>
            <td>bearer</td>
            <td>Token semantics are implementation-defined.</td>
        </tr>
        
    </tbody>
</table>

## Tags

| Name      | Description                                                                                                                                                                                                                                                                                                                                                                          |
| --------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| run       | Execute methods, synchronously or asynchronously.                                                                                                                                                                                                                                                                                                                                    |
| validate  | Static + dry-run validation of MTHDS bundles.                                                                                                                                                                                                                                                                                                                                        |
| discovery | What this runner is and what it can route to.                                                                                                                                                                                                                                                                                                                                        |
| blobs     | Optional. A runner whose /version declares blob_store true keeps a blob store (bytes keyed by their SHA-256, written once, never changed), so a sender uploads a file at most once and then sends it by hash.
                                                                                                                                                                       |
| runs      | Optional. A runner whose /version declares run_store true keeps a run store (a record of the runs it has started, by their pipeline_run_id), so a caller reads a run's status and its results after the fact, and it honours an Idempotency-Key header on /execute and /start, so a request repeated under its key within 24 hours of the first request under it runs at most once.
 |


