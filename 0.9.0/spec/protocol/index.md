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

The 200 response is a `RunResultExecute` — the completed run, holding two base fields: `pipeline_run_id` (mandatory, server-generated and authoritative) and `pipe_output` (the method's serialized output; always present — a completed run has output, either a value or an explicit absence document). Anything more an implementation returns — a run state, timestamps, output naming, anything else — is an extension field (see [Extension policy](#extension-policy)), declared and documented by that implementation.

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

**Two recommended extension fields.** The protocol's base fields stay exactly as listed above, but two artifacts are common enough — and useful enough to a client that has just learned a bundle is valid — that the standard names them and fixes their shapes rather than letting each implementation invent its own. On the `is_valid: true` arm, an implementation SHOULD report them under these names: **`pipe_io_contracts`**, the per-pipe input and output contracts, whose shape is defined by [Pipe I/O Contracts](./pipe-io-contracts.md); and **`input_form`**, the per-pipe ordered presentation view of a method's inputs, whose shape is defined by [Input-Form Descriptor](./input-form-descriptor.md). Both derive from the validated library, so neither can appear on the `is_valid: false` arm — there is no library to derive from when loading or wiring failed. They remain *extension* fields in the sense of the [extension policy](#extension-policy): a conformant runner may omit them, and a client written against the base fields alone is unaffected. What the standard fixes is that a runner reporting them reports **these shapes** under **these names**. How a caller *asks* for them — always on, an opt-in request token, a separate route — is implementation-defined; both artifacts are equally derivable offline from a resolved library, and the protocol carriage is one way to obtain them, not what they are.

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
        "mthds_contents": [
            "string"
        ],
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
            "description": "At least one of pipe_code / mthds_contents is required (enforced by the anyOf rule below). If mthds_contents is provided without pipe_code, the first bundle must declare a main_pipe. Extension-open: implementations MAY accept extra top-level properties (extension args).\n",
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
                        "mthds_contents"
                    ],
                    "properties": {
                        "mthds_contents": {
                            "type": "array",
                            "minItems": 1
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
                    "description": "Code of the pipe to execute (a pipe already registered, or one defined in mthds_contents)."
                },
                "mthds_contents": {
                    "type": [
                        "array",
                        "null"
                    ],
                    "minItems": 1,
                    "items": {
                        "type": "string"
                    },
                    "description": "MTHDS bundle contents to load (always an array, even for a single file; never empty). Implementations bound count and per-file size."
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
        "mthds_contents": [
            "string"
        ],
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
            "description": "At least one of pipe_code / mthds_contents is required (enforced by the anyOf rule below). If mthds_contents is provided without pipe_code, the first bundle must declare a main_pipe. Extension-open: implementations MAY accept extra top-level properties (extension args).\n",
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
                        "mthds_contents"
                    ],
                    "properties": {
                        "mthds_contents": {
                            "type": "array",
                            "minItems": 1
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
                    "description": "Code of the pipe to execute (a pipe already registered, or one defined in mthds_contents)."
                },
                "mthds_contents": {
                    "type": [
                        "array",
                        "null"
                    ],
                    "minItems": 1,
                    "items": {
                        "type": "string"
                    },
                    "description": "MTHDS bundle contents to load (always an array, even for a single file; never empty). Implementations bound count and per-file size."
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
        "mthds_contents": [
            "string"
        ],
        "allow_signatures": true
    }
    ```
    <span class="small-note">⚠️</span>&nbsp;<em class="small-note warning">This example has been generated automatically from the schema and it is not accurate. Refer to the schema for more information.</em>

    

    ??? hint "Schema of the request body"
        ```json
        {
            "type": "object",
            "required": [
                "mthds_contents"
            ],
            "properties": {
                "mthds_contents": {
                    "type": "array",
                    "minItems": 1,
                    "items": {
                        "type": "string"
                    },
                    "description": "MTHDS contents to load (always an array, even for a single file)."
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
            <td>Filter the deck by model category.</td>
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
                "description": "The models this runner can route to. Implementations MAY add their own routing metadata (aliases, fallback chains, anything else) as additional properties — on the deck and on each model entry.\n",
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
                                        "search"
                                    ]
                                }
                            }
                        }
                    }
                }
            }
            ```
    
    
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
            "runner_version": "string"
        }
        ```
        <span class="small-note">⚠️</span>&nbsp;<em class="small-note warning">This example has been generated automatically from the schema and it is not accurate. Refer to the schema for more information.</em>
        
        

        ??? hint "Schema of the response body"
            ```json
            {
                "type": "object",
                "description": "The handshake. The protocol defines protocol_version (required) plus an optional runner_version; implementations MAY add their own identification (a name, an underlying runtime version, anything else) as additional properties.\n",
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
                    }
                }
            }
            ```
    
    
=== "Other responses"
    <div class="common-response"><p>Refer to the common response description: <a href="#problem" class="ref-link">Problem</a>.</p></div>




---
## Schemas


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
            <td><code>inputs</code></td>
            <td></td>
            <td>Method inputs: map of input name to { concept, content }. Content shapes follow the concept's structure; content validation is deliberately loose here and strict inside the runtime.</td>
        </tr>
        <tr>
            <td><code>mthds_contents</code></td>
            <td>Array&lt;<span class="string-type">string</span>&gt;</td>
            <td>MTHDS bundle contents to load (always an array, even for a single file; never empty). Implementations bound count and per-file size.</td>
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
            <td>Code of the pipe to execute (a pipe already registered, or one defined in mthds_contents).</td>
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
            <td><code>mthds_contents</code></td>
            <td>Array&lt;<span class="string-type">string</span>&gt;</td>
            <td>MTHDS contents to load (always an array, even for a single file).</td>
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
        "instance": "string"
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
                }
            }
        }
        ```






### ValidationProblem
The request failed validation (RFC 7807). On /execute and /start a bad bundle also lands here; on /validate an invalid bundle is a 200 verdict, so there a 422 is request-shape only.


<p class="message-separator"></p>

=== "application/problem+json"
    
    
    ```json
    {
        "type": "string",
        "title": "string",
        "status": 0,
        "detail": "string",
        "instance": "string"
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

| Name      | Description                                       |
| --------- | ------------------------------------------------- |
| run       | Execute methods, synchronously or asynchronously. |
| validate  | Static + dry-run validation of MTHDS bundles.     |
| discovery | What this runner is and what it can route to.     |


