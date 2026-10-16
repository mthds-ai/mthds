---
description: "The MTHDS error registry format — one entry per error code, declaring its title, domain, retry verdict, steps, typed parameters, templates and HTTP status — the core registry published with the standard, and the extension prefixes it lists."
---

# Error Registry

Every problem a runner answers with carries exactly one code from a registry, and the code decides its title, its domain, its retry verdict, its steps and its HTTP status ([Errors](protocol.md#errors)). The **MTHDS core registry** lists the core codes. It is data, authored once, from which everything else is derived: the snapshot clients vendor, the [page of each code](../errors/index.md) at the URL its `type` names, and the checks that keep the protocol's examples in line with it.

This is the core registry's entry for `request.blobs_missing`, the protocol's refusal of a file sent by a hash the runner does not hold:

```yaml
--8<-- "docs/spec/openapi/mthds-error-registry.yaml:blobs_missing"
```

A runner that meets this case answers with a problem whose `code`, `title`, `domain`, `retry` and `status` are the entry's, whose `next_step` is one of the entry's two steps, and whose `params` holds the entry's typed parameters:

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
    "missing_blobs": ["9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08"]
  }
}
```

The format described here is the same for the core registry and for the registry an owner of an [extension prefix](#extension-prefixes) publishes for its own codes.

## The Files

The core registry lives beside the protocol's OpenAPI document, in three files:

| File | What it is |
|---|---|
| [`mthds-error-registry.yaml`](openapi/mthds-error-registry.yaml) | The registry as it is authored. It is the single source of every other form. |
| [`mthds-error-registry.json`](openapi/mthds-error-registry.json) | The snapshot: the same data as JSON, which a client or a runtime vendors. It is generated from the YAML and never edited by hand. |
| [`mthds-error-registry.schema.json`](openapi/mthds-error-registry.schema.json) | The JSON Schema of the format. It refuses an entry with a member missing, so no code is ever left without a domain, a verdict or a step. |

The snapshot is published with every release of the standard, at addresses that do not move:

- In the standard's repository, as `docs/spec/openapi/mthds-error-registry.json` at the release's tag, `v<version>`.
- As an asset of the release itself, at `https://github.com/mthds-ai/mthds/releases/download/v<version>/mthds-error-registry.json`.
- On this site, at `https://mthds.ai/latest/spec/openapi/mthds-error-registry.json` for the current standard, and under a version's own directory for each version the site still serves. The site retires older versions, so a consumer that pins a version reads it from the release or the tag.

A consumer that vendors the snapshot records the version it copied, which the snapshot states in its `version` member, and copies it again when it follows a newer standard.

## The Document

A registry document has these members:

| Member | Required | Meaning |
|---|---|---|
| `version` | yes | The version of the release the registry is published with. The core registry's is the standard version. |
| `base_url` | yes | The base URL the pages of the registry's codes are published under, an `https` URL with no trailing slash. The core's is `https://mthds.ai/errors`. |
| `extension_prefixes` | core only | The registered [extension prefixes](#extension-prefixes), each with its owner and base URL. |
| `prefix` | extension only | The registered prefix every code of an extension registry starts with. |
| `families` | yes | The families the registry's codes belong to, each with what its codes are about, in the order the pages present them. |
| `codes` | yes | One entry per code. |

A code's family is the code without its last segment. A core code is exactly two segments, a family and a name, such as `input.missing`; an extension code is three, the prefix, a family and a name, such as `acme.billing.credit_exhausted`, and its family, `acme.billing`, starts with the prefix. Every code belongs to a declared family, and every declared family has at least one code.

## An Entry

Every entry declares every member below except `status`, which only some entries carry, and `see`, which is optional:

| Member | Meaning |
|---|---|
| `code` | The code, unique in the registry. |
| `title` | The code's short title, the same for every occurrence of the code. |
| `domain` | [Who must act](protocol.md#domain-who-must-act): one of `input`, `method`, `account`, `operator` and `runtime`. |
| `retry` | Whether [repeating the operation](protocol.md#retry) can succeed: one of `no`, `yes` and `outcome_unknown`. |
| `raised_as` | How the code reaches a reader, described [below](#how-a-code-reaches-a-reader). |
| `status` | The HTTP status of a response the code is the body of. It is present exactly when `raised_as` is `problem`. |
| `detail` | The template of the problem's `detail`, which describes this occurrence. |
| `steps` | Two [next steps](protocol.md#next-steps), each a `kind` from the protocol's closed list and the template of its `detail` sentence: `actor`, for the domain's actor, and `other`, for any other reader. |
| `params` | The code's [parameters](#parameters) by name, in the order its page lists them. It is empty for a code that declares none. |
| `meaning` | What the code means, as its page says it. |
| `what_to_do` | What to do about it, as its page says it. |
| `see` | The pages of the specification that define the situation the code names, each a `title` and an `href` from the documentation's root. |

The closed lists of `domain`, `retry` and the step kinds are those of the protocol's OpenAPI document, and they change only with it.

A problem carries the step aimed at whoever reads it. A runtime that knows its reader is the domain's actor, such as the method's author validating their own method, sends the `actor` step; one that does not, such as a runner serving a caller who runs someone else's method, sends the `other` step. The catch-all code, `runtime.unexpected`, which names a fault no other code describes, has the verdict `no` and the step `report` for both readers.

### How a Code Reaches a Reader

`raised_as` says where a reader meets the code:

- `problem`: as a problem document, the body of an HTTP response or kept in a run's record, so the entry has a `status`. A code kept only in a run's record carries the status the run's synchronous execution would answer with.
- `warning`: only as an item of a validate verdict's `warnings`, which never makes a method invalid, so the entry has no `status`.
- `client`: detected by a client itself, such as a runner it cannot reach, and never received as a response body, so the entry has no `status`. A client builds the problem for such an error itself, so that its own callers read every error alike.

An entry raised as a problem may also be met as an [item](protocol.md#itemized-errors) of another problem's `errors` or of a validate verdict, where it carries its code, its detail, its parameters and its location, and may carry suggestions and a suggested fix, but no member its code decides: no `type`, `title`, `status`, `domain`, `retry`, `retry_after` or `next_step`, which the problem or the verdict holding it carries.

## Parameters

A parameter is a typed fact that the code's sentences are written from, so that a reader acts on data rather than on prose. Each declares a `type` and a `description`, and the types are these:

| Type | Holds | JSON Schema of the value |
|---|---|---|
| `identifier` | A name, a code or an id, such as a pipe code, a concept, a model or a run id. | `{"type": "string"}` |
| `integer` | A whole number. | `{"type": "integer"}` |
| `seconds` | A number of seconds, never negative. | `{"type": "number", "minimum": 0}` |
| `bytes` | A size in bytes, never negative. | `{"type": "integer", "minimum": 0}` |
| `sha256` | A SHA-256 hash in lowercase hexadecimal. | `{"type": "string", "pattern": "^[0-9a-f]{64}$"}` |
| `enum` | One of the values the parameter lists in `values`. | `{"type": "string", "enum": [...]}` |
| `caller_text` | The caller's own text, capped, such as a parser's finding about the caller's method. Text that can quote a run's inputs or outputs, such as the message of an exception a method's function raised, is never one. | `{"type": "string"}` |
| `list` | A list of values of the scalar type `items` declares. | `{"type": "array", "items": ...}` |

No parameter holds the content of a run's inputs or outputs. The OpenAPI document's `ProblemParams` types the parameters a client relies on by shape, such as `missing_blobs`, and those types are the registry's.

Two flags qualify a parameter:

- `optional: true` marks a fact that an occurrence of the code may lack, such as the run id of a run a client may never have learned. Every other parameter is present on every occurrence, so a reader may rely on it.
- `operator_only: true` marks a fact of the runtime's own configuration, such as which component is misconfigured, that only whoever runs the runtime may read. An implementation leaves it out of every problem it answers to a caller and keeps it for its operator, in its logs for instance.

## Templates

`detail` and each step's `detail` are templates: a sentence or two naming parameters as `{name}`. An emitter fills each placeholder with the occurrence's value of that parameter, writing a list as its items joined by a comma and a space; a literal brace is written twice. A template names only the parameters its code declares, never an optional one, which may be absent, and an operator-only one only in the `actor` step of a code whose domain is `operator`, the one sentence that only whoever runs the runtime reads.

A template is the registry's wording of the sentence, and every fact it states is also a parameter, since no reader parses `detail`. An implementation that words the sentence otherwise, or writes it in another language, states the same facts and no others.

## Extension Prefixes

A code that is not a core code starts with a prefix its owner registers ([Extension codes](protocol.md#codes)). The core registry's `extension_prefixes` lists each registered prefix with three members:

| Member | Meaning |
|---|---|
| `prefix` | The prefix, one segment that is not the name of a core family. |
| `owner` | Who owns the prefix, and alone adds codes under it. |
| `base_url` | The base URL its codes' pages are published under. |

A prefix is registered through the [contribution process](../about/contributing.md#register-an-error-code-prefix), by adding its entry to the core registry, and a registered prefix is never reassigned to another owner. Its owner publishes a registry of its own codes in this format, with `prefix` in place of `extension_prefixes`, which the [schema](openapi/mthds-error-registry.schema.json) checks like the core's, and publishes each code's page at its type URI.

## The Type URI and the Pages

A code's `type` is its registry's base URL, a slash, then the whole code, so the core code `input.missing` has the type `https://mthds.ai/errors/input.missing`. That address resolves to the page of the code in the current standard, served under a directory for its family, `https://mthds.ai/latest/errors/<family>/<name>/`, such as `https://mthds.ai/latest/errors/input/missing/`, and each version the site serves keeps its own copy under its directory. A code's page gives every member of its entry: what it means, what to do, who acts, its verdict and status, its steps, its parameters and its templates.

The pages are generated from the registry when the site is built, so they never differ from it. The [Error Codes](../errors/index.md) page lists every core code by family.

## Checks

The standard's repository checks the core registry on every change. It refuses a registry that the schema refuses or that holds a key twice, a code given twice, a family that is undeclared or unused, a prefix given twice or named like a core family, a template naming a parameter its reader may not see, and a `see` reference to a page the documentation does not hold. It also refuses closed lists that differ from the OpenAPI document's, a parameter that `ProblemParams` types otherwise, a problem example in the documentation that uses a core code the registry does not declare or disagrees with its code's entry, in a member the code decides, a status its entry does not have, its step's kind, or a parameter undeclared, mistyped or missing, and a snapshot that is not the registry's.

## Versioning

The core registry is part of the standard, and its `version` is the standard version it is published with. A new code, family or prefix is an addition; a changed domain, verdict, step kind, status or parameter type changes what a runtime emits, and a reworded title or template does not. [Versioning](versioning.md#the-core-error-registry) says which change moves which part of the number.
