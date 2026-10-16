---
description: "The MTHDS Protocol — the minimal HTTP contract every MTHDS runner implements: execute, start, validate, models, version, the optional blob routes, and the problem document every error is."
---

# HTTP Runner Protocol

The MTHDS Protocol is the minimal HTTP contract every MTHDS runner implements. Any server that serves its five required routes with the shapes defined here is an MTHDS-compliant runner, and a runner that keeps a blob store also serves the optional blob routes. A runner is just a runner: it executes methods, validates bundles, and reports what models it can route to and what version it is. It keeps no run store and owns no user, billing, or catalog concepts.

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

The first five routes are required of every runner. The last two are served by a runner whose `/version` declares `blob_store: true`, and `PUT /blobs/{sha256}` only by one that stores uploaded bytes itself rather than pointing its senders at another upload target.

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

The protocol sets no time limit on `/execute`; deployments cap it at their proxy layer. For long-running methods prefer `/start`. Implementations **MAY** answer `202 + RunResultStart` (just the run id, no output yet) with a `Location` header pointing at an implementation-defined status resource when they cannot hold the connection open ([RFC 9110](https://www.rfc-editor.org/rfc/rfc9110#section-15.3.3) asynchronous pattern). Simple runners never emit 202; clients that cannot handle it should use `/start`.

### Method files

A request's `files` map holds every file of the method's tree under its [tree path](./method-tree.md#tree-paths): its bundles, its manifest when it has one, and every other file a step may read or that travels with the method, such as a Python module, a template, an image or a `requirements.txt`. Each value is a [file entry](./method-tree.md#the-file-entry) in one of three forms:

- **a string**, the file's text, whose bytes are its UTF-8 encoding;
- **`{ "base64": "…" }`**, any bytes, in standard padded Base64, canonical, with its pad bits zero;
- **`{ "sha256": "…", "size": … }`**, bytes the runner already holds in its blob store, named by their SHA-256 in lowercase hexadecimal and their length, a JSON integer written without a fraction or an exponent.

The map must form a tree. A runner refuses with a `422` naming the offending path a map in which:

- a key is not a tree path, such as a key not already in NFC, which a runner refuses rather than normalize, or names a file the membership rule could never admit, such as a dotfile;
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

The protocol mandates no run store, and it defines **no completion channel for `/start`**: how a caller learns that an asynchronous run finished — webhooks, polling routes, anything else — is implementation-defined and outside the protocol (see [Extension policy](#extension-policy)). A bare runner is not required to answer "what happened to run X?" after the fact. Clients written against the protocol alone must rely on `/execute`'s response.

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

## Discovery

`GET /models` returns the runner's model deck — the models it can route to (`{name, type}` entries), optionally filtered by category. Implementations may add their own routing metadata (aliases, fallback chains, anything else) as additional properties.

`GET /version` is always public (no auth). It returns `protocol_version` (required), an optional `runner_version`, and an optional `blob_store` flag, which is `true` for a runner that keeps a blob store and serves the [blob routes](#sending-files-by-hash), and `false` or absent for one that does not — implementations may add their own identification on top:

```json
{
  "protocol_version": "2.0.0",
  "runner_version": "2.3.0",
  "blob_store": true
}
```

Clients use `/version` as the handshake: it reports the protocol and runner versions and whether the runner takes files by hash, and any additional properties let clients detect vendor extensions before relying on them.

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

The RFC's optional `instance` member is not part of the core: a runner may send it, and a client written against the protocol does not read it.

**The code decides.** Every problem carries exactly one code from a registry, and its domain, its retry verdict, its next step, its title and its HTTP status are properties of that code. The wire carries them so that a reader needs no lookup, but a runner never sets them independently of the code: two cases that need different verdicts are two codes. A client branches on `code`, and on `domain`, `retry` and `next_step.kind` when it handles several codes alike. It never parses `title`, `detail` or `next_step.detail`, which are written for a person, so every fact they state is also a member: the typed facts in `params`, the place in `location`. No member of a problem carries the content of a run's inputs or outputs.

### Codes

A code is lowercase and dotted, each segment matching `[a-z][a-z0-9_]*`. A core code is bare, exactly a family and a name, such as `input.missing` or `request.blobs_missing`. A code belongs to the core when any conforming runner or client could raise it, independently of hosting, billing or a vendor's components. The MTHDS core registry lists the core codes and gives each its title, domain, retry verdict, steps, parameters and HTTP status. A code's **family** is the code without its last segment, so `request.blobs_missing` belongs to the family `request`.

**Extension codes.** Every other code starts with a prefix its owner registers, followed by a family and a name: `<prefix>.<family>.<name>`, such as `acme.billing.credit_exhausted`. A prefix is one segment of the same form, it is never the name of a core family, and it belongs to one owner, who alone adds codes under it. What the protocol leaves to implementations, such as billing or a catalog of saved methods, is coded under the implementation's own prefix.

**Declaring a prefix.** An owner declares an extension prefix in two steps:

1. It publishes a registry of its own codes, in the format of the core registry, that names the prefix and the base URL its codes' pages are published under, and declares for each code everything the core registry declares for a core code.
2. It registers the prefix with the standard, through the [contribution process](../about/contributing.md), as an entry of the core registry's list of extension prefixes naming the prefix, its owner and that base URL. A registered prefix is never reassigned to another owner.

A runner emits a code under a prefix only once the prefix is registered and the code is in its owner's registry.

### The `type` URI

`type` is derived from the code and its owner's base URL: the base URL, a slash, then the whole code. The core's base URL is `https://mthds.ai/errors`, so the core code `input.missing` has the type `https://mthds.ai/errors/input.missing`. An extension code is joined, its prefix included, to the base URL its prefix is registered with: under a prefix registered with `https://errors.acme.example`, the code `acme.billing.credit_exhausted` has the type `https://errors.acme.example/acme.billing.credit_exhausted`. The page at a type URI says what the code means and what to do about it. Because `type` and `code` name the same thing one to one, a client branches on `code` and never takes a code apart from `type`.

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
- `outcome_unknown`: the operation may already have taken effect, such as a request whose connection dropped after the runner received it. A client never repeats such an operation automatically; it follows the next step to learn the outcome first.

On a run's own problem the operation is the run, so `yes` means that a new run with the same inputs may succeed.

### Next steps

`next_step` tells the reader what to do next, as a `kind` from a closed list and a `detail` sentence:

| Kind | What the reader does |
|---|---|
| `retry` | Repeats the operation. |
| `wait` | Waits, then checks again later. |
| `read_run` | Reads the run to learn its outcome. |
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

Because every problem carries its own domain, verdict and step, a client whose registry lags a runner's still reads a new code correctly by these rules. A tool that checks a runner, such as a conformance harness, checks the emitter rules and stays free to reject an unknown value.

## Extension policy

Implementations may extend the surface — extra routes, extra optional request properties, extra response properties — but **must not change the meaning or shape of the protocol routes**. Both sides of the wire are extension-open: request bodies accept implementation-defined args, and the protocol's response schemas declare only the base fields (`additionalProperties` allowed). A client written against the MTHDS Protocol runs unmodified against any compliant runner; a vendor's superset may accept and return more, but never diverges on the surface defined here.

## Conformance

An implementation claiming conformance states it as: *implements MTHDS Protocol v2.0*. Conformance means: the five required routes exist with the request/response shapes of [`mthds-protocol.openapi.yaml`](openapi/mthds-protocol.openapi.yaml), every error is an RFC 9457 problem document carrying the core members, with a registered code, `/version` is public, and a runner that declares `blob_store: true` serves `POST /blobs/missing` and resolves hash entries from its blob store.

The protocol number moves under its own rule — a new route, a new optional field or a new [model category](#model-categories) is a minor bump, a changed shape or meaning is a major one — independently of the standard version. The recommended extension fields above are not such an addition: they are shaped by their own specification pages and ride a report that is extension-open by policy, so naming one moves no protocol number. See [Versioning](./versioning.md#the-protocol-version).

## Route reference

Everything below is rendered at build time from the normative OpenAPI document — do not edit it by hand; edit [`mthds-protocol.openapi.yaml`](openapi/mthds-protocol.openapi.yaml).

[OAD(./openapi/mthds-protocol.openapi.yaml)]
