# Pipe I/O Contracts

A **pipe I/O contract** states, for one pipe, exactly what a caller must supply and what the pipe resolves to: for each declared input, the concept it expects, whether it may be omitted, how many items it takes, and the JSON Schema its content must satisfy; for the output, the concept it produces and how many items that is.

```json
{
  "legal.summarize_contract": {
    "inputs": {
      "contract": {
        "concept_ref": "legal.Contract",
        "presence": "plain",
        "multiplicity": "single",
        "item_count": null,
        "json_schema": { "type": "object", "properties": { "url": { "type": "string" }, "mime_type": { "type": "string" } }, "required": ["url"] }
      },
      "instructions": {
        "concept_ref": "native.Text",
        "presence": "optional",
        "multiplicity": "single",
        "item_count": null,
        "json_schema": { "type": "object", "properties": { "text": { "type": "string" } }, "required": ["text"] }
      }
    },
    "output": {
      "concept_ref": "legal.Summary",
      "multiplicity": "single",
      "item_count": null,
      "optional": false
    }
  }
}
```

The contract is a projection of the library, not a second declaration of it. Everything it states is already in the `.mthds` source — `summarize_contract` declares `contract = "legal.Contract"` and `instructions = "Text?"`, and `legal.Contract` refines `native.Document` — and the contract makes it explicit, fully qualified, and machine-readable in one place, so a caller assembling a payload, a tool registry building a function signature, and a form renderer choosing controls all read one artifact rather than three interpretations of the source.

Pipe I/O contracts are a **recommended extension field** of the [HTTP Runner Protocol](./protocol.md#validating-a-bundle)'s validate response, where they ride the field name `pipe_io_contracts`. They are equally derivable offline from a resolved library, with no server involved; the protocol carriage is one way to obtain them, not what they are.

## Specification Status

This document specifies an artifact implementations already produce. What it adds is **ownership**: until now the shape was defined only by its producers, and this page makes it standard-owned so that independent implementations agree on it by conformance rather than by imitation. Where a rule below names behavior an implementation has not yet realized, it is the forward contract that implementation is brought into conformance with — the same convention [Library Crate Format](./library-crate.md#specification-status) uses. The `json_schema` slot's *content* — how a concept projects onto JSON Schema — is not fixed by this document beyond the rules in [The input schema](#the-input-schema); that projection follows the concept model of [.mthds File Format](./mthds-format.md#concept-definitions).

## The Map

The artifact is a map from **namespaced pipe reference** to one contract object:

- Keys are fully-qualified `pipe_ref`s (`domain_path.pipe_code`), the same identity convention the [library crate](./library-crate.md#crate-structure) keys pipes by. A bare or same-domain-implicit key MUST NOT appear.
- Every pipe in the resolved library has an entry, including a [contract-only pipe signature](./mthds-format.md#contract-only-pipe-signatures) — a signature's declared contract is exactly what it exists to state, and a consumer building against a method still under construction reads it like any other.
- A pipe with no declared inputs carries `"inputs": {}`. An empty input map is a stated fact, never an omitted member.

Each entry is an object with two members, both required: `inputs` (a map from input name to an [input contract](#the-input-contract)) and `output` (one [output contract](#the-output-contract)).

The `inputs` member is a **map, and deliberately contracts no order**. Where an ordered view of a pipe's inputs is needed — a form, a rendered signature — that order is stated by the [input-form descriptor](./input-form-descriptor.md), which is keyed by the same `pipe_ref` set.

## The Input Contract

One entry per declared input slot, keyed by the authored input name (including a [dotted name](./mthds-format.md#input-names)).

| Member | Type | Required | Meaning |
|--------|------|----------|---------|
| `concept_ref` | string | Yes | The fully-qualified concept the slot expects, **with any multiplicity suffix stripped** — a `Concept[]` slot names `Concept`. Plurality is stated by `multiplicity`, never by this member. |
| `presence` | `"plain"` \| `"optional"` \| `"force"` | Yes | The authored [presence marker](#presence), verbatim. |
| `multiplicity` | `"single"` \| `"variable"` \| `"fixed"` | Yes | How many items the slot takes (see [Multiplicity and item count](#multiplicity-and-item-count)). |
| `item_count` | integer or `null` | Yes | The exact item count, non-`null` exactly when `multiplicity` is `"fixed"`. |
| `json_schema` | object | Yes | The JSON Schema the slot's content must satisfy (see [The input schema](#the-input-schema)). |

### Presence

`presence` carries the authored marker as written, and is **three-valued** so that `!` survives:

| `presence` | Authored as | Means |
|------------|-------------|-------|
| `"plain"` | no marker | The caller must supply the slot. |
| `"optional"` | `?` | The caller may omit the slot; the pipe handles the absence itself. |
| `"force"` | `!` | The caller must supply the slot, and the author has asserted so explicitly. |

`plain` and `force` are the same requirement on the caller and differ only in what the author asserted. The distinction is kept on the wire because it is a fact lint and graph surfaces read, and a producer flattening it to a boolean destroys it for every consumer at once. A consumer that only needs "may this be absent?" answers it as `presence == "optional"`, and is well advised to answer it in exactly one place: that is what keeps a marker a later version of the standard adds from meaning one thing on one of its surfaces and something else on another.

The vocabulary is the [crate's materialized presence](./library-crate.md#5-materialize-defaults-and-multiplicity): normalization makes each slot's marker explicit, and this artifact reports it.

Because [markers may not be combined with multiplicity](./mthds-format.md#concept-references-in-inputs-and-output), a slot whose `multiplicity` is `"variable"` or `"fixed"` always reports `presence: "plain"`.

### Multiplicity and item count

`multiplicity` and `item_count` are a **pair**, and they are read together:

| Authored | `multiplicity` | `item_count` |
|----------|----------------|--------------|
| `Concept` | `"single"` | `null` |
| `Concept[]` | `"variable"` | `null` |
| `Concept[N]`, N ≥ 2 | `"fixed"` | `N` |
| `Concept[1]` | `"single"` | `null` |

`Concept[1]` is **single** — one item, no list framing — because [the language says so](./mthds-format.md#concept-references-in-inputs-and-output), not because this artifact chose to collapse it: a count of one is a way of writing `Concept`, so a `"fixed"` count on this wire is always greater than one and a `[1]` slot's `json_schema` is the element schema with no array wrapper. The crate's [normalization step 5](./library-crate.md#5-materialize-defaults-and-multiplicity) materializes the same rule; this artifact reports it rather than re-deriving it.

`item_count` is **always on the wire**, `null` off the fixed arm. The [input-form descriptor](./input-form-descriptor.md#structured-multiplicity) makes the opposite choice and omits the slot entirely when it does not apply; the two artifacts differ deliberately, and each states its own rule so that neither is guessed from the other.

### The input schema

`json_schema` is a JSON Schema document describing the slot's **content** — what the caller puts in the slot, not the slot's envelope. Two rules bind it; everything else about the projection follows the concept model and the producer's chosen schema dialect.

**A plural slot's schema is an array wrapper.** When `multiplicity` is `"variable"` or `"fixed"`, the schema is `{"type": "array", "items": <the element schema>}` — the element schema being exactly what the same concept would carry at `"single"`. On the **fixed** arm, and only there, the wrapper additionally carries `minItems` and `maxItems`, both equal to `item_count`:

```json
{
  "concept_ref": "legal.Clause",
  "presence": "plain",
  "multiplicity": "fixed",
  "item_count": 3,
  "json_schema": {
    "type": "array",
    "items": { "type": "object", "properties": { "text": { "type": "string" } }, "required": ["text"] },
    "minItems": 3,
    "maxItems": 3
  }
}
```

Stating the count as schema keywords rather than only as `item_count` is what lets an unmodified JSON Schema validator enforce it: a consumer checking a payload runs the schema and gets the count checked for free, without restating a number the contract already carries. A `"variable"` slot carries neither keyword — the language cannot declare a minimum on a variable list, so an empty array is a conforming value.

**Concept identity is read from `concept_ref`, never from the schema.** A producer MAY carry the concept's identity or description inside the schema document (as `title`, `description`, or a dialect-specific annotation), and consumers MUST NOT depend on it: `concept_ref` is the authoritative statement, and a consumer sniffing identity out of schema shape or annotations is doing exactly what this artifact exists to make unnecessary.

## The Output Contract

One object per pipe, describing what the pipe resolves to.

| Member | Type | Required | Meaning |
|--------|------|----------|---------|
| `concept_ref` | string | Yes | The fully-qualified concept the pipe produces, multiplicity suffix stripped. |
| `multiplicity` | `"single"` \| `"variable"` \| `"fixed"` | Yes | How many items the pipe resolves to; the same three values and the same `[1]`-is-single rule as an input. |
| `item_count` | integer or `null` | Yes | The exact item count, non-`null` exactly when `multiplicity` is `"fixed"`. |
| `optional` | boolean | Yes | `true` when the output is declared optional (`?`): the pipe may resolve it as a recorded absence instead of a value. |

**The two sides are deliberately asymmetric, and this is the one thing to know about the output contract.** An input carries a three-valued `presence`; an output carries a two-valued boolean. That is not a lag in one half of the artifact — it is the language: [`!` MUST NOT appear on `output`](./mthds-format.md#concept-references-in-inputs-and-output), because a force marker is a use-site assertion about an input. With no third state to carry, a three-valued output slot would have an arm nothing can ever produce.

`optional: true` means a **successful** run may leave the output absent — a recorded absence, per [Optionality](../language/optionality.md#runtime-behavior) — not that the run may fail. No output member carries a schema: an output contract states identity and shape-of-plurality, and the payload a run actually produces is the run's own result.

## Strictness

Every object this document defines — a contract entry, an input contract, an output contract — is a **closed shape**. A producer MUST NOT emit a member this version of the standard does not define, and a consumer MAY reject one. An unrecognized member is version drift, and catching it where a payload is parsed is more useful than discovering it three layers later.

This is the deliberate opposite of the [protocol's extension policy](./protocol.md#extension-policy), which keeps the validate *report* extension-open: an implementation may add fields to the report — that is how this artifact reached the report in the first place — but it may not add members inside the artifact and still call it a pipe I/O contract. The report is the envelope and grows; the artifact is the contract and does not.

Growth happens through the standard: a new member is a minor version, and an implementation built against this version may refuse a payload from a later one rather than silently discard what it does not understand.

## Derivation Requirements

- **Derived from the resolved library.** Every fact the contract states is authored: the concept references, the presence markers, the multiplicity. A [normalized library crate](./library-crate.md) is a sufficient input — it is fully qualified, natives are materialized, and presence and multiplicity are explicit — so a consumer holding a crate can derive the contracts with a JSON parser and nothing else, exactly as the [sufficiency guarantee](./library-crate.md#sufficiency-guarantee) promises.
- **Deterministic.** The same library yields the same contracts. Nothing in the artifact depends on the environment, the request, or the order bundles were loaded in.
- **One derivation, every surface.** An implementation that reports contracts from more than one path — an in-process validation and a remote worker, say — MUST derive them through one shared derivation, so the artifact cannot differ by which backend answered.

## Non-Goals

- **Not a payload validator's replacement.** The contract *carries* the schema; it does not restate what the schema says. A machine consumer validates a payload with `json_schema` and an ordinary JSON Schema validator.
- **No presentation.** Field order, labels, controls, and grouping are not here. That is the [input-form descriptor](./input-form-descriptor.md)'s job, and it exists so that this artifact stays byte-stable whatever a renderer needs.
- **No execution semantics.** What a pipe *does* with an absent optional input, how a controller behaves under absence, and what a run costs are outside this artifact.
- **No run state.** A contract describes a pipe, not an invocation.

## Relationship to Other Specifications

- [.mthds File Format](./mthds-format.md) defines the `inputs` and `output` declarations this artifact projects, including the multiplicity-and-presence suffix grammar.
- [Library Crate Format](./library-crate.md) defines the resolved library the contracts derive from, and the normalization that makes presence and multiplicity explicit.
- [Input-Form Descriptor](./input-form-descriptor.md) is the presentation view over the same pipes, keyed by the same `pipe_ref` set, and reads `json_schema` from here for its `unknown` escape hatch.
- [HTTP Runner Protocol](./protocol.md#validating-a-bundle) carries the artifact as a recommended extension field of the validate response.
- [Optionality](../language/optionality.md) and [Multiplicity](../language/multiplicity.md) are the language-level pages behind `presence` and `multiplicity`.
