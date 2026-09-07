---
description: "Formal specification of the output-form descriptor — the per-pipe presentation view of what a pipe resolves to, described with the same node vocabulary as the input form."
---

# Output-Form Descriptor

The **output-form descriptor** is a presentation view of what a pipe *resolves to*: for each pipe, one field descriptor stating the kind, the nesting and the constraints of its single output, so that rendering a result, registering a tool signature with a return type, or projecting a typed structure for it needs no schema heuristics.

```json
{
  "legal.summarize_contract": {
    "field": {
      "kind": "object",
      "name": "output",
      "concept_ref": "legal.Summary",
      "description": "A summary of a contract",
      "required": true,
      "fields": [
        { "kind": "text", "name": "headline", "description": "One line, no more", "required": true },
        { "kind": "prose", "name": "body", "description": "The summary itself", "required": true },
        { "kind": "number", "name": "risk_score", "description": "How risky, 0 to 1", "required": false, "integer": false }
      ]
    }
  }
}
```

The descriptor is the twin of the [input-form descriptor](./input-form-descriptor.md), and exists for the same reason. [Pipe I/O contracts](./pipe-io-contracts.md#the-output-contract) state what a pipe's output *is* — its concept, how many items it is, whether a successful run may leave it absent — but a consumer that wants to show that result, or to generate a type for it, needs the facts a schema projection destroys: concept identity, the refinement chain, the resolved structure in declared order, a fixed item count. The input side already states them. This artifact states them for the other half of the contract.

**An output is a concept reference exactly like an input is.** That is the whole design, and it is why this page defines almost nothing of its own: the same concepts, the same structures, the same field kinds, the same nesting, and therefore the same node vocabulary. There is no second node union and no second `kind` enum, so there is no second place for kinds to drift.

The descriptor is a **recommended extension field** of the [HTTP Runner Protocol](./protocol.md#validating-a-bundle)'s validate response, where it rides the field name `output_form`. It is equally derivable offline from a resolved library, with no server involved; how a caller *asks* a particular implementation for it is that implementation's decision, and outside this standard.

## Specification Status

This document specifies an artifact implementations already produce, and makes it standard-owned so that independent implementations agree on it by conformance rather than by imitation. Where a rule below names behavior an implementation has not yet realized, it is the forward contract that implementation is brought into conformance with — the same convention [Library Crate Format](./library-crate.md#specification-status) uses.

The node vocabulary is not restated here. Every rule the [Input-Form Descriptor](./input-form-descriptor.md) states about a field descriptor — its slots, its closed kind union, its kind assignment, its recursion, its hints, its strictness, its derivation — binds this artifact unchanged, including the slots that page shapes now and the language fills later. What this page states is the handful of facts that differ, and every one of them is a fact about the *position* a node sits in rather than about the concept it describes.

## The Per-Pipe Descriptor

The artifact is a map from **namespaced pipe reference** to one descriptor object, over the **same key set as [pipe I/O contracts](./pipe-io-contracts.md#the-map) and the [input-form descriptor](./input-form-descriptor.md#the-per-pipe-descriptor)**. Keys are fully-qualified `pipe_ref`s (`domain_path.pipe_code`), and every pipe in the resolved library has an entry — a [contract-only pipe signature](./mthds-format.md#contract-only-pipe-signatures) included, since a signature's declared output is exactly what it exists to state.

Each entry is an object with one member: `field`, the descriptor of what the pipe resolves to.

**One `field`, not a `fields` list.** That is the one shape difference from the input-form descriptor, and it follows from the language rather than from taste: a pipe has exactly one output where it may declare many inputs. A list of one would invite a consumer to loop and a producer to wonder what a second entry means. It is also why this artifact states no order: an input form is ordered and the order is a fact worth carrying, while one output has none.

## The Output Node

`field` is a **field descriptor exactly as [Field Descriptors](./input-form-descriptor.md#field-descriptors) defines one**: a recursive object discriminated on `kind` over that page's [closed union](./input-form-descriptor.md#field-kinds), carrying that page's [common slots](./input-form-descriptor.md#common-slots), assigned by that page's [kind-assignment](./input-form-descriptor.md#kind-assignment) rules, recursing through `fields` on an `object` node and through `item` on a `list` node. A consumer narrows an output node on `kind` with the same exhaustiveness it uses for an input node, and the closed union covers this artifact too.

The derivation is likewise total: an output a producer cannot map honestly reports `kind: "unknown"`, and a consumer reading one treats the payload as opaque rather than trusting a shape no stated fact supports.

What differs is only the **slot facts** — what a node's position states rather than what its concept does.

### No presence, no gating

An output node carries **neither `presence` nor `gating`** — not at the top, and not at any depth. A producer MUST NOT emit either, and a consumer MAY reject a descriptor that does.

Both are facts of an *input slot*, and an output has none:

- `presence` is the authored marker, and [`!` MUST NOT appear on an `output`](./mthds-format.md#concept-references-in-inputs-and-output): a force marker is a use-site assertion about an input. The one marker an output does take, `?`, is stated by the contract's [`optional`](./pipe-io-contracts.md#the-output-contract), which is where a consumer reads it.
- `gating` asks whether the run may start. Nothing waits on a result.

The absence is stated rather than left implicit because the node type is shared with the input side, where both slots are optional precisely so that a node belonging to no slot can exist at all — not so that a producer may fill them in with something plausible.

### The node's name is `output`

An input's name is authored by the method; an output has none to author. The node carries one anyway, because `name` is what separates a named node from the nameless one a `list`'s `item` holds, and this standard fixes its value rather than leaving each producer to pick a sentinel: **a producer states the string `output`**.

It is an **address, not a label**, and nothing displays it. A result is labelled by its concept and a list entry by its index, exactly as the input side already rules for [list items](./input-form-descriptor.md#common-slots). A consumer MUST NOT report it as an authored name. The `item` of a plural output carries no `name` member at all, by the same structural rule as an input's.

### `required` is always `true`

The output node states `required: true`.

On a top-level input field, `required` is derived as `presence != "optional"`; an output has no presence to derive it from, and the question that slot answers — must the caller supply this — has no output analogue. Whether a successful run may leave the output absent is the contract's `optional`, and a consumer reading absence off `required` is reading the wrong artifact.

One consequence follows from the input page's rule that a descriptor never carries `required: true` beside a `default_value`: the output node carries no `default_value`. Nothing defaults a result.

Nested fields inside the output's payload are unaffected and keep the ordinary nested meaning — the field must be present within its concept's payload, and an optional one reports `required: false`, exactly as it does under an input.

## Plurality Is on the Descriptor, Never on the Concept

`concept_ref` names the **element** concept, with any multiplicity suffix stripped, on both sides of the contract — a `Concept[]` output names `Concept`. Plurality therefore cannot be read off the concept, and the descriptor states it structurally:

- A **single** output is the element node directly. `Concept[1]` is single, [as the language reads it](./mthds-format.md#concept-references-in-inputs-and-output), so it too is described with no list framing.
- A **plural** output is a `list` node whose `item` is the element node. On the list node, `concept_ref`, `refines`, `description` and `hints` are the element's, and the `item` carries the same `concept_ref` — the same duplication the [input side states](./input-form-descriptor.md#structured-multiplicity), for the same reason: the list node is where a consumer reads the output's identity, and the item is what it renders once per entry.
- A **fixed-count** output additionally carries `item_count: N`, always at least 2, and equal to the [contract's `item_count`](./pipe-io-contracts.md#multiplicity-and-item-count) for the same pipe. Off the fixed arm the slot is **absent**, where the contract carries `null` instead; the two artifacts differ deliberately, and each states its own rule so that neither is guessed from the other.

```json
{
  "legal.extract_clauses": {
    "field": {
      "kind": "list",
      "name": "output",
      "concept_ref": "legal.Clause",
      "description": "One clause of a contract",
      "required": true,
      "item": {
        "kind": "object",
        "concept_ref": "legal.Clause",
        "description": "One clause of a contract",
        "required": true,
        "fields": [
          { "kind": "text", "name": "heading", "description": "The clause heading", "required": true },
          { "kind": "prose", "name": "text", "description": "The clause body", "required": true }
        ]
      }
    }
  }
}
```

A producer performs the wrap by reading the pipe's output multiplicity — the same authored fact the contract reports as `multiplicity`. **This is the one place producing this artifact is work rather than reuse, and it fails silently when skipped**: a `Concept[]` output described as its element states one item where a run produces many, and every consumer then shows one. A consumer never sees the wrap as work: it reads `kind: "list"` and never consults the contract for plurality.

## Intent Hints on an Output Node

Every node carries the same optional `hints` object the [input-form descriptor](./input-form-descriptor.md#intent-hints-on-a-descriptor) defines, under the same rules: the effective merge as one flat map of string to string, an applicable `intent` word feeding kind assignment rather than competing with it, the merged map riding both a plural node and its `item`, no `hints` member at all when there are none, and the language's two governing rules unweakened — hints are non-normative, and a consumer that ignores them stays correct.

One layer of that merge is simply absent here. [Slot-level hints exist on inputs only](./intent-hints.md#on-a-pipe-input-slot) — the language serves result presentation through concept-level hints on the output concept — so an output node's effective hints are the concept layer alone: the concept's own hints merged along its refinement chain, nearer declaration winning. There is no site layer to win over it.

## Reading It With the Contract

The descriptor states what the output **is**. The [output contract](./pipe-io-contracts.md#the-output-contract) states its identity, how many items it is, and whether a successful run may leave it absent. Neither is sufficient alone, and the two are keyed by the same `pipe_ref` so that a consumer holding both never has to match them up: identity and plurality are stated in both places and agree by derivation, and everything a consumer needs in order to *present* the result is stated only here.

## Strictness

Every object this document defines — a per-pipe descriptor, and the field descriptor it carries — is a **closed shape**. A producer MUST NOT emit a member this version of the standard does not define, and a consumer MAY reject one. An unrecognized member is version drift, and catching it where a payload is parsed is more useful than discovering it three layers later.

The `hints` map is the same deliberate exception it is on the input side, and it is an exception in *content*, not in shape.

This strictness is the opposite of the [protocol's extension policy](./protocol.md#extension-policy), which keeps the validate *report* extension-open: an implementation may add fields to the report — that is how this artifact reached the report in the first place — but it may not add members inside the artifact and still call it an output-form descriptor. The report is the envelope and grows; the artifact is the view and does not. Growth happens through the standard, as a minor version.

## Derivation Requirements

The [input-form descriptor's derivation requirements](./input-form-descriptor.md#derivation-requirements) bind this artifact unchanged: derived from the resolved library and never from a projected schema, with the `refines` chain read from pre-flattening facts; deterministic; one derivation across every surface an implementation reports from; and the same projection from every engine, so that two independent implementations produce comparable values.

Two more are this artifact's own:

- **The output node is derived as a concept, not as a slot.** An output belongs to no slot, so a producer derives it exactly as it derives a nested concept-typed node — the code path the input side already runs for every nested field — and then performs the [plural wrap](#plurality-is-on-the-descriptor-never-on-the-concept). Nothing about an output justifies a second derivation, and an implementation that writes one has given kinds a second place to drift.
- **One key set with the sibling artifacts.** An implementation reporting this descriptor beside pipe I/O contracts or the input-form descriptor derives all of them over the same pipes, so their key sets are equal by construction rather than by coincidence.

## Non-Goals

- **No widget vocabulary.** Kinds and hints name intent; `textarea`, `slider`, and `dropdown` never appear on this wire.
- **No run state.** The descriptor describes what a pipe resolves to, derived from the library — not what a run produced. It is the same before a run, after a successful one, and after a failed one, and it names no run.
- **No delivery semantics.** How a result reaches a caller — a synchronous response, an asynchronous one, a stored artifact, a URL — belongs to the [protocol](./protocol.md) and to the runtime.
- **No validation semantics.** A machine consumer never has to read the descriptor to judge a payload; that is what [pipe I/O contracts](./pipe-io-contracts.md) are for. A caller ignoring the descriptor entirely loses no fact it needs.
- **No layout or styling.** Grouping, sizing, and theming belong to consumers.
- **No committed artifacts.** The descriptor is derived on demand. Nothing is generated into a consumer's repository, stamped, or locked.

## Relationship to Other Specifications

- [Input-Form Descriptor](./input-form-descriptor.md) is the twin over the inputs and the owner of the node vocabulary this artifact reuses: its field descriptor, its kinds, its kind assignment, its strictness and its derivation requirements are this page's too.
- [Pipe I/O Contracts](./pipe-io-contracts.md) is the machine contract over the same pipes, keyed by the same `pipe_ref` set, and states the output's identity, multiplicity and optionality.
- [.mthds File Format](./mthds-format.md) defines the `output` declaration this artifact projects, including the multiplicity suffix grammar and the rule that a force marker may not appear on an output.
- [Library Crate Format](./library-crate.md) defines the resolved library the descriptor derives from.
- [Intent Hints](./intent-hints.md) owns the hint vocabulary and the rule that slot-level hints exist on inputs only.
- [Native Concept Definitions](./native-concepts.md) pins the native concepts the kind-assignment table maps.
- [HTTP Runner Protocol](./protocol.md#validating-a-bundle) carries the artifact as a recommended extension field of the validate response.
