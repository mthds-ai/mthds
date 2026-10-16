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

All errors are [RFC 7807](https://www.rfc-editor.org/rfc/rfc7807) `application/problem+json` documents. Auth is implementation-defined: a bearer-token slot is reserved, and anonymous access is allowed for self-hosted runners.

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

A hash entry resolves only in the runner's own blob store, and only when the runner holds those bytes at the stated size. A runner without a blob store, or one that does not hold every hash a request names, answers with a `422` problem whose `missing_blobs` member lists, in lowercase hexadecimal, each hash it does not hold, so a sender learns in one answer what to upload. The tree's files are the method's own: a file a caller supplies for one run is an input, never an entry of `files`.

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
- **`is_valid: false`** — the bundle is invalid. The body carries `validation_errors[]` (a non-empty list of structured diagnostics, each at least a `category` and a `message`) plus `is_runnable: false` and an optional `message`. The structural artifacts of a valid report are absent.

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
  "protocol_version": "1.0.0",
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

## Extension policy

Implementations may extend the surface — extra routes, extra optional request properties, extra response properties — but **must not change the meaning or shape of the protocol routes**. Both sides of the wire are extension-open: request bodies accept implementation-defined args, and the protocol's response schemas declare only the base fields (`additionalProperties` allowed). A client written against the MTHDS Protocol runs unmodified against any compliant runner; a vendor's superset may accept and return more, but never diverges on the surface defined here.

## Conformance

An implementation claiming conformance states it as: *implements MTHDS Protocol v1.0*. Conformance means: the five required routes exist with the request/response shapes of [`mthds-protocol.openapi.yaml`](openapi/mthds-protocol.openapi.yaml), errors are RFC 7807 problems, `/version` is public, and a runner that declares `blob_store: true` serves `POST /blobs/missing` and resolves hash entries from its blob store.

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
    Blocking. The protocol sets no time limit; deployments cap it at their proxy layer. For long-running methods prefer /start. Implementations MAY return 202 + RunResultStart (id only) with a Location header pointing at an implementation-defined status resource when they cannot hold the connection open for the full execution (RFC 9110 asynchronous pattern); clients that cannot handle 202 should use /start instead.



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
                "description": "POST /execute 200 — the completed run. Two base fields: the server-generated authoritative pipeline_run_id and the method's pipe_output (always present — a completed run has output, either a value or an explicit absence document). Extension-open: anything more an implementation returns (a run state, timestamps, output naming) is an extension on top.\n",
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
                "description": "POST /start 202 (and the optional /execute 202 degrade) — the started run's authoritative pipeline_run_id, nothing else. A started run has no output yet; how it is delivered later (polling, callbacks, anything else) is implementation-defined and outside the protocol. Extension-open.\n",
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
    | `Location` | Implementation-defined status resource for this run. |<span class="string-type">string</span> |

    
=== "422 Unprocessable Content"
    <div class="common-response"><p>Refer to the common response description: <a href="#validationproblem" class="ref-link">ValidationProblem</a>.</p></div>
=== "Other responses"
    <div class="common-response"><p>Refer to the common response description: <a href="#problem" class="ref-link">Problem</a>.</p></div>


<hr class="operation-separator" />

### <span class="http-post">POST</span> /start
Start a method asynchronously; returns its pipeline_run_id immediately.

??? note "Description"
    Asynchronous. Returns 202 + RunResultStart immediately (pipeline_run_id only); the runner keeps no run store, and how completion is later delivered (callbacks, polling, anything else) is implementation-defined and outside the protocol. The returned pipeline_run_id is always authoritative (server-generated).



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
                "description": "POST /start 202 (and the optional /execute 202 degrade) — the started run's authoritative pipeline_run_id, nothing else. A started run has no output yet; how it is delivered later (polling, callbacks, anything else) is implementation-defined and outside the protocol. Extension-open.\n",
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
            "blob_store": true
        }
        ```
        <span class="small-note">⚠️</span>&nbsp;<em class="small-note warning">This example has been generated automatically from the schema and it is not accurate. Refer to the schema for more information.</em>
        
        

        ??? hint "Schema of the response body"
            ```json
            {
                "type": "object",
                "description": "The handshake. The protocol defines protocol_version (required) plus an optional runner_version and an optional blob_store flag; implementations MAY add their own identification (a name, an underlying runtime version, anything else) as additional properties.\n",
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
                        "description": "True when the runner keeps a blob store: it serves POST /blobs/missing and resolves hash entries in a files map. False or absent when it does not, in which case it answers any hash entry with a 422 listing missing_blobs.\n"
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



### FileEntry
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
            <td><code>validation_errors</code></td>
            <td>Array&lt;<a href="#validationerror" class="ref-link">ValidationError</a>&gt;</td>
            <td>Per-error diagnostics — non-empty on every invalid verdict.</td>
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
            <td><code>detail</code></td>
            <td><span class="string-type">string</span></td>
            <td></td>
        </tr>
        <tr>
            <td><code>instance</code></td>
            <td><span class="string-type">string</span></td>
            <td></td>
        </tr>
        <tr>
            <td><code>missing_blobs</code></td>
            <td>Array&lt;<span class="string-type">string</span>&gt;</td>
            <td>On a 422 refusing hash entries, every hash of the request the runner does not hold, in lowercase hexadecimal, so a sender learns in one answer what to upload.
</td>
        </tr>
        <tr>
            <td><code>status</code></td>
            <td><span class="integer-type">integer</span></td>
            <td></td>
        </tr>
        <tr>
            <td><code>title</code></td>
            <td><span class="string-type">string</span></td>
            <td></td>
        </tr>
        <tr>
            <td><code>type</code></td>
            <td><span class="string-type">string</span>(<span class="uri-format format">uri</span>)</td>
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



### ValidationError

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
            <td><code>category</code></td>
            <td><span class="string-type">string</span></td>
            <td>Implementation-defined diagnostic category.</td>
        </tr>
        <tr>
            <td><code>message</code></td>
            <td><span class="string-type">string</span></td>
            <td></td>
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
            <td>True when the runner keeps a blob store: it serves POST /blobs/missing and resolves hash entries in a files map. False or absent when it does not, in which case it answers any hash entry with a 422 listing missing_blobs.
</td>
        </tr>
        <tr>
            <td><code>protocol_version</code></td>
            <td><span class="string-type">string</span></td>
            <td>MTHDS Protocol version implemented.</td>
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
RFC 7807 problem document.

<p class="message-separator"></p>

=== "application/problem+json"
    
    
    ```json
    {
        "type": "string",
        "title": "string",
        "status": 0,
        "detail": "string",
        "instance": "string",
        "missing_blobs": [
            "string"
        ]
    }
    ```
    <span class="small-note">⚠️</span>&nbsp;<em class="small-note warning">This example has been generated automatically from the schema and it is not accurate. Refer to the schema for more information.</em>

    

    ??? hint "Schema of the response body"
        ```json
        {
            "type": "object",
            "description": "RFC 7807.",
            "properties": {
                "type": {
                    "type": "string",
                    "format": "uri"
                },
                "title": {
                    "type": "string"
                },
                "status": {
                    "type": "integer"
                },
                "detail": {
                    "type": "string"
                },
                "instance": {
                    "type": "string"
                },
                "missing_blobs": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "pattern": "^[0-9a-f]{64}$"
                    },
                    "description": "On a 422 refusing hash entries, every hash of the request the runner does not hold, in lowercase hexadecimal, so a sender learns in one answer what to upload.\n"
                }
            }
        }
        ```






### ValidationProblem
The request failed validation (RFC 7807). On /execute and /start a bad bundle also lands here; on /validate an invalid bundle is a 200 verdict, so there a 422 is request-shape only. A request whose files map is not a tree is a 422 naming the offending path, and a request naming a hash entry the runner does not hold, or any hash entry when it keeps no blob store, is a 422 whose missing_blobs member lists each such hash.


<p class="message-separator"></p>

=== "application/problem+json"
    
    
    ```json
    {
        "type": "string",
        "title": "string",
        "status": 0,
        "detail": "string",
        "instance": "string",
        "missing_blobs": [
            "string"
        ]
    }
    ```
    <span class="small-note">⚠️</span>&nbsp;<em class="small-note warning">This example has been generated automatically from the schema and it is not accurate. Refer to the schema for more information.</em>

    

    ??? hint "Schema of the response body"
        ```json
        {
            "type": "object",
            "description": "RFC 7807.",
            "properties": {
                "type": {
                    "type": "string",
                    "format": "uri"
                },
                "title": {
                    "type": "string"
                },
                "status": {
                    "type": "integer"
                },
                "detail": {
                    "type": "string"
                },
                "instance": {
                    "type": "string"
                },
                "missing_blobs": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "pattern": "^[0-9a-f]{64}$"
                    },
                    "description": "On a 422 refusing hash entries, every hash of the request the runner does not hold, in lowercase hexadecimal, so a sender learns in one answer what to upload.\n"
                }
            }
        }
        ```






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

| Name      | Description                                                                                                                                                                                                    |
| --------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| run       | Execute methods, synchronously or asynchronously.                                                                                                                                                              |
| validate  | Static + dry-run validation of MTHDS bundles.                                                                                                                                                                  |
| discovery | What this runner is and what it can route to.                                                                                                                                                                  |
| blobs     | Optional. A runner whose /version declares blob_store true keeps a blob store (bytes keyed by their SHA-256, written once, never changed), so a sender uploads a file at most once and then sends it by hash.
 |


