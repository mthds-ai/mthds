---
description: "Formal specification of the input-form descriptor — the per-pipe, ordered presentation view of a method's inputs a renderer turns into a fill-in form with no heuristics."
---

# Input-Form Descriptor

The **input-form descriptor** is a presentation view of a method's inputs: for each pipe, an ordered list of field descriptors that a renderer turns into a fill-in form with no schema heuristics, no hardcoded native-concept table, and no description matching.

```json
{
  "legal.summarize_contract": {
    "fields": [
      {
        "kind": "document",
        "name": "contract",
        "concept_ref": "legal.Contract",
        "refines": ["native.Document"],
        "description": "The contract to summarize",
        "required": true,
        "presence": "plain",
        "gating": true
      },
      {
        "kind": "prose",
        "name": "instructions",
        "concept_ref": "native.Text",
        "description": "Optional steering instructions",
        "required": false,
        "presence": "optional",
        "gating": false
      }
    ]
  }
}
```

A renderer reading that descriptor knows to offer a file control for `contract` because the descriptor **says** the concept refines `native.Document` — not because it recognized a `url` property in a schema, and not because the description contained the word "document". That is the whole point of the artifact: every fact a form needs is stated, so the guessing that a JSON Schema forces on a renderer stops being necessary.

The descriptor exists because a schema is a lossy projection of a method's inputs. Projecting a concept onto JSON Schema destroys concept identity, the refinement chain, the authored presence marker, a fixed item count, and the measured meaning of a default — and a renderer that needs those back can only re-infer them, imprecisely and differently in every consumer. The descriptor states them instead, deriving from the same resolved library the schema does, so the two cannot disagree.

The descriptor is a **recommended extension field** of the [HTTP Runner Protocol](./protocol.md#validating-a-bundle)'s validate response, where it rides the field name `input_form`. It is equally derivable offline from a resolved library, with no server involved; how a caller *asks* a particular implementation for it is that implementation's decision, and outside this standard.

## Specification Status

This document specifies an artifact implementations already produce, and makes it standard-owned so that independent implementations agree on it by conformance rather than by imitation. Where a rule below names behavior an implementation has not yet realized, it is the forward contract that implementation is brought into conformance with — the same convention [Library Crate Format](./library-crate.md#specification-status) uses.

Two slots are shaped now and filled by the language later. `examples` and the text and numeric constraint slots are on the wire because the descriptor's shape should settle once: an implementation may already hold such facts about a concept's payload, and the language will grow the authoring side without reopening the wire. A producer that has nothing to put in them omits them.

Until the language defines how such a fact is *authored*, these are the one part of the artifact whose content is a producer's own, and the standard says so rather than pretending otherwise: two conforming implementations agree on every language-derived slot and may differ on whether they fill these. A consumer reads them as advisory enrichment and never as a fact it depends on, and the [comparability guarantee](#derivation-requirements) below is stated over the language-derived slots.

## The Per-Pipe Descriptor

The artifact is a map from **namespaced pipe reference** to one descriptor object, over the **same key set as [pipe I/O contracts](./pipe-io-contracts.md#the-map)** — the descriptor is per pipe input, and that map's key space is its natural address. Keys are fully-qualified `pipe_ref`s (`domain_path.pipe_code`).

Each entry is an object with one member: `fields`, an **ordered list holding one field descriptor per declared input slot, in authored input order**.

Order is why the descriptor is a sibling artifact rather than a decoration inside each contract's input entry. A form is ordered; the contract's `inputs` map deliberately contracts no order. The list carries the order as a fact, and the contract stays byte-stable whatever a renderer asks for.

A pipe with no inputs maps to `{"fields": []}`. An empty form is a valid form, not an omitted entry.

## Field Descriptors

A field descriptor is a **recursive object, discriminated on `kind`**: one node per rendered field. An `object` node recurses through `fields`, a `list` node through `item`.

The vocabulary is field *kinds* and semantic slots — bounds, choices, defaults — and never control names. How a renderer maps a kind to a control is the renderer's decision, and this document deliberately names no controls.

### Common Slots

Every field descriptor carries:

| Slot | Type | Presence | Meaning |
|---|---|---|---|
| `kind` | string | always | The field kind, from the [closed union](#field-kinds) below. |
| `name` | string | on every node except a `list`'s `item` | The identifier as authored — the input slot name on a top-level field, the structure field name on a nested one. A `list`'s `item` has no authored name and carries **no `name` member** at all: the index labels items, and a sentinel would be a value two producers could pick differently. |
| `title` | string | optional | Human label. A renderer falls back to `name`. A generated or internal type name is not a title and MUST NOT be reported as one. |
| `concept_ref` | string | on every concept-typed node | The fully-qualified concept reference the node carries (`native.Document`, `legal.Invoice`). Present on every top-level field and on every nested node that is concept-typed. This is the fact whose absence forces consumers into hardcoded native-reference tables. |
| `refines` | list of strings | on concept-typed nodes with a refinement chain | The concept's [refinement](./mthds-format.md#concept-refinement) chain, immediate parent first, walked to its end (`["legal.BaseClause", "native.Text"]`, `["native.Document"]`). Absent when the concept refines nothing. "Does this refine `native.X`?" is a membership test on this list — a stated fact, never shape sniffing. |
| `description` | string | optional | Helper text, from the authored concept or field description. |
| `required` | boolean | always | On a **top-level** field: the caller must supply the slot, derived as `presence != "optional"`. On a **nested** field: the field must be present within its concept's payload. The two levels are independent facts and never interact. `required` drives layout — a required field always shows, an optional one may collapse; whether the *user* must put content in before the run may start is the separate `gating` fact. |
| `presence` | `"optional"` \| `"plain"` \| `"force"` | top-level fields only | The authored [presence marker](./pipe-io-contracts.md#presence) on the pipe's input slot, three-valued so that `!` is not flattened away. Nested fields carry no `presence`: presence is a pipe-slot fact. |
| `gating` | boolean | top-level fields only | The declared [gating fact](#gating) — the run cannot start until the caller provides content for this slot. |
| `default_value` | any | optional | The value applied when the caller omits the field. Absent unless a default was authored; the `null` that a schema projection attaches to every optional field is an emission artifact and MUST NOT be reported as a `default_value`. A descriptor never carries both `required: true` and a `default_value` — the pair is two contradictory instructions on one field and is rejected at validation — so a defaulted field always reports `required: false`. |
| `examples` | list | optional | Example values for the field. |
| `hints` | object | optional | The node's effective [intent hints](#intent-hints-on-a-descriptor), a flat map of string to string. |

A slot that does not apply to a node is **absent**, never `null`. Applicable falsy values (`required: false`, `integer: false`) are stated.

#### Gating

`gating` is the single answer to "must the user put something in before the run may start", and a renderer blocks the run on exactly the top-level descriptors whose `gating` is `true` (a nested field gates through its parent).

It is stated rather than left to a consumer to re-derive, because it is **not** the same question as `required`:

| Slot | `required` | `gating` | Why |
|---|---|---|---|
| `Concept`, `Concept!` | `true` | `true` | The method demands a value. |
| `Concept?` | `false` | `false` | The method states the slot may be omitted. |
| `Concept[]` | `true` | `false` | The empty list is a legitimate value, and the language cannot declare "at least one item". |
| `Concept[N]`, N ≥ 2 | `true` | `true` | A list whose empty form the method has explicitly ruled out. |

The rule is `presence != "optional"` and not (`kind == "list"` without `item_count`). The variable-list row is the one that makes the two facts distinct: such a slot is required — a caller must send the property — yet a renderer submitting `[]` for it has satisfied the method, so blocking the run there would demand something the method never asked for. Stating `gating` on the wire is what lets a later language-level minimum change the answer without touching a single renderer.

### Field Kinds

`kind` is a **closed union**. This version of the standard defines:

| Kind | The value is | Additional slots |
|---|---|---|
| `text` | a short single-line string | `min_length`, `max_length`, `pattern`, `format` — all optional |
| `prose` | flowing free text | the same as `text` |
| `date` | a calendar date, or a point in time | `datetime` (boolean) — **required**: `true` when the value carries a time of day, `false` for a bare calendar date |
| `number` | an integer or a floating-point number | `integer` (boolean) — **required**; `minimum`, `maximum`, `exclusive_minimum`, `exclusive_maximum` — all optional |
| `boolean` | true or false | — |
| `enum` | one of a fixed set of values | `choices` (list) — **required**, and always a list **even for a single choice**, so that no consumer has to read a single-value form |
| `document` | a document supplied as a file or a URL | — |
| `image` | an image, which a renderer may preview | — |
| `object` | a structured concept | `fields` (list of field descriptors) — **required**; the concept's resolved payload fields, in declared order |
| `list` | an array of one element type | `item` (field descriptor) — **required**; `item_count` (integer) — optional, present exactly on a fixed `[N]` slot, where `N` is always at least 2 |
| `unknown` | not honestly describable as any of the above | — |

`document` and `image` carry no accept-list and no upload affordance: *what the value is* rides `concept_ref` and `refines`, and how a renderer offers a file is the renderer's decision.

`unknown` is the **escape hatch, and it is mandatory rather than optional**: a producer that cannot map a node honestly MUST report `unknown` rather than guess a kind. A renderer then falls back to raw entry against the slot's [`json_schema`](./pipe-io-contracts.md#the-input-schema). A derivation is total — every node gets a descriptor — and `unknown` is what makes totality truthful.

The constraint slots (`min_length`, `max_length`, `pattern`, `format` on the text kinds; the four numeric bounds on `number`) are stated where a producer holds them. `format` is an open string set carrying schema formats the `date` kind does not absorb (`time`, `uri`, …).

### Kind Assignment

Kind is decided from **stated facts** — a concept's identity, its refinement chain, its resolved structure — and never by sniffing a schema's shape or matching a description. A concept refining `native.Document` is `kind: "document"` because it says so, not because its payload happens to hold a `url` property.

**A concept-typed node** takes its kind from what the concept resolves to. The rows below are tried **in order, and the first one that matches decides**:

| The concept | Kind |
|---|---|
| is a native | the native's kind, from the table below |
| has a refinement chain that reaches a native | that native's kind |
| declares a `structure` table — its own, or one inherited along the refinement chain | `object`, whose `fields` are the effective field set in declared order |
| resolves to no structure — a [string-described concept](./library-crate.md#6-promote-string-described-concepts), one declaring neither `structure` nor `refines`, or one whose refinement chain reaches such a concept | `prose` |
| resolves to none of the above, or is not present in the library | `unknown` |

**The order is the rule, not a formatting accident.** Most natives declare a structure of their own — `native.Document` is a `url`, a `mime_type`, a `filename` — so a table that asked about structure first would put every native and every native-backed concept on the `object` arm and never reach the native rows at all. `legal.Contract refines native.Document` is `kind: "document"`, not an `object` of `url` and `mime_type`, and it is the ordering that says so.

The chain is walked rather than the concept read alone because the language keeps [`refines` and `structure` mutually exclusive](./mthds-format.md#concept-definitions): a refining concept never carries a structure of its own, so inheritance along the chain is the only way one reaches the `object` arm — and a chain that reaches a native reaches it *through* that native's structure, which is exactly the case the native rows catch first.

A concept that resolves to no structure is text-valued, per the language's own rule that [a description-only concept is text](./intent-hints.md#the-intent-vocabulary) — and the chain clause matters: `Foo refines Bar` where `Bar` is description-only resolves to no structure just as `Bar` does, so it is `prose` and not the `unknown` a literal reading of the concept alone would give. That fact reaches the wire as `kind: "prose"` and **never as a fabricated refinement link**: the language states description-only text-valuedness as an arm of its own, not as refinement of `native.Text`, and a producer inventing that link would be reporting ancestry no one authored — precisely what the [derivation requirement](#derivation-requirements) below forbids. A consumer asking "is this text-valued?" reads `kind`; `refines` answers the different question "what does this specialize?", and on a structureless concept the honest answer is nothing.

**A native concept** maps by identity, over the [pinned definitions](./native-concepts.md):

| Native | Kind | Additional slots |
|---|---|---|
| `Text`, `Html` | `prose` | — |
| `Number` | `number` | `integer: false` |
| `YesNo` | `boolean` | — |
| `Date` | `date` | `datetime: false` |
| `Time` | `text` | `format: "time"` |
| `Document` | `document` | — |
| `Image` | `image` | — |
| `Page`, `TextAndImages`, `SearchResult` | `object` | `fields` from the pinned definition |
| `Dynamic`, `JSON`, `Anything`, `Composite` | `unknown` | — |

**A structure field** maps from its declared [field type](./mthds-format.md#field-types) — except that a field carrying `choices` is an `enum`, which the language already guarantees by requiring `type` to be omitted there:

| Field | Kind | Additional slots |
|---|---|---|
| `choices` present | `enum` | `choices`, verbatim |
| `type = "text"` | `text` | — |
| `type = "integer"` | `number` | `integer: true` |
| `type = "number"` | `number` | `integer: false` |
| `type = "boolean"` | `boolean` | — |
| `type = "date"` | `date` | `datetime: false` |
| `type = "datetime"` | `date` | `datetime: true` |
| `type = "time"` | `text` | `format: "time"` |
| `type = "list"` | `list` | `item`, derived from `item_type` and `item_concept_ref` |
| `type = "concept"` | the referenced concept's node | as that node carries |
| `type = "dict"` | `unknown` | — |
| the [shorthand string form](./mthds-format.md#concept-structure-fields) | `text` | `required: true` |

`dict` is `unknown` rather than a kind of its own because the language's dict declares a key type and a value type, not a set of fields, and a form built from that would be guessing at entries the method never named.

### Structured Multiplicity

Plurality is a stated fact and is never re-derived from a schema's `type: "array"`:

- An input slot authored `Concept[]` is a `list` field whose `item` describes the concept, with **no** `item_count`.
- An input slot authored `Concept[N]`, N ≥ 2, is a `list` field with `item_count: N` — the fixed count as a structured fact.
- A nested structure field of `list` type is likewise a `list` node, its `item` derived from `item_type` and, where that is `"concept"`, `item_concept_ref`. A field that declares no `item_type`, or whose element type the field blueprint cannot express (a list of lists, a list of dicts), is still a `list` node — the plurality is stated — carrying `item` with `kind: "unknown"`.
- `Concept[1]` is **single** — one item, no list framing — exactly as in [pipe I/O contracts](./pipe-io-contracts.md#multiplicity-and-item-count), so a stated `item_count` is always greater than one.

`item_count` is **absent** when it does not apply. The [contract](./pipe-io-contracts.md#multiplicity-and-item-count) makes the opposite choice and carries the slot as `null` off the fixed arm; the two artifacts differ deliberately, and each states its own rule so that neither is guessed from the other.

On a `list` node, `concept_ref` and `refines` name the **element** concept — the authored reference with its multiplicity suffix stripped, exactly as the contract reports it — and the `item` descriptor carries the same `concept_ref`. The list node is where a renderer reads the slot's identity; the item is what it renders once per entry.

## Intent Hints on a Descriptor

Every field descriptor carries an optional `hints` object: the node's **effective** [intent hints](./intent-hints.md), a flat map of string to string.

The value is the final key-by-key merge the language defines — along the concept's refinement chain, nearer declaration winning, and then the site layer (a structure field's or an input slot's own `hints`) over the concept layer — so a consumer reads one map and walks nothing. Everything well-formed rides it, unknown keys and unknown words included: content leniency is the language's rule, and a descriptor preserves content for consumers that know more than this version does.

On a **plural node** the merged hints appear on the `list` node *and* on its `item`, mirroring the `concept_ref` duplication: applicability is judged per item, and a renderer reading either node finds the same answer.

A node with **no effective hints has no `hints` member**, so a hint-free method's descriptor is byte-identical to what it would have been before hints existed.

An applicable `intent` word is an **input to kind assignment, never a second answer competing with it**. On a text-valued node, an effective `intent = "prose"` yields `kind: "prose"` and `intent = "label"` yields `kind: "text"`. An absent, unknown, or inapplicable word leaves the kind that [kind assignment](#kind-assignment) already decided. `rating` and `quantity` never change a kind — both describe a `number`, and this version's union has no finer kind — and ride the slot for the renderer.

Applicability is judged exactly as [Intent Hints](./intent-hints.md#the-intent-vocabulary) defines it, which is narrower than a kind: a `prose` node reached through `native.Html` and a `text` node carrying `format: "time"` are neither text-valued nor number-valued, so no word of this version applies to them.

The language's two governing rules bind the slot, and neither is weakened by the descriptor carrying it: hints are **non-normative** — no hint changes a verdict, the gating rule, or the payload contract — and a **renderer that ignores hints stays correct**, because the kind assignment above is complete without them.

## Strictness

Every object this document defines — a per-pipe descriptor, a field descriptor — is a **closed shape**. A producer MUST NOT emit a member this version of the standard does not define, and a consumer MAY reject one. An unrecognized member is version drift, and catching it where a payload is parsed is more useful than discovering it three layers later.

The `hints` map is the deliberate exception, and it is an exception in *content*, not in shape: its shape is fixed — a flat map of string to string — while unknown keys and unknown words inside it are carried through, exactly as the [language's leniency rule](./intent-hints.md#the-hints-table) requires.

This strictness is the opposite of the [protocol's extension policy](./protocol.md#extension-policy), which keeps the validate *report* extension-open: an implementation may add fields to the report — that is how this artifact reached the report in the first place — but it may not add members inside the artifact and still call it an input-form descriptor. The report is the envelope and grows; the artifact is the view and does not. Growth happens through the standard, as a minor version.

## Derivation Requirements

- **Derived from the resolved library, never from a projected schema.** Deriving the descriptor *from* a JSON Schema would re-import every loss the descriptor exists to end. The descriptor and the contract's `json_schema` are two projections of one library, which is why they cannot disagree.
- **The refinement chain needs pre-flattening facts.** `refines` reports the chain as authored, and the crate's [normalization step 3](./library-crate.md#3-flatten-refinement) deliberately flattens in-crate structured refinement away. A producer therefore derives the descriptor from the closure *before* that flattening — fully qualified and native-materialized, with its `refines` links intact. A producer holding only a normalized crate derives every other slot unchanged and reports the `refines` link normalization retains — the terminal `native.<Code>` link, where the chain reaches one, which is what the membership test consumers run on `refines` depends on. It MUST NOT reconstruct intermediate links it does not hold.
- **Deterministic.** The same library yields the same descriptor: field order is authored order, and no content depends on the environment or on the request.
- **One derivation, every surface.** An implementation that reports the descriptor from more than one path MUST derive it through one shared derivation, so the artifact cannot differ by which backend answered.
- **Same projection from every engine.** The derivation is mechanism-free — nothing in it requires a network, a model, or a server — so two independent implementations derive the same descriptor from the same library, and their outputs are comparable as values. The [slots the language does not yet author](#specification-status) are the stated exception: comparability is asserted over the slots this version derives from the library.

## Non-Goals

- **No widget vocabulary.** Kinds and hints name intent; `textarea`, `slider`, and `dropdown` never appear on this wire.
- **No validation semantics.** The descriptor never becomes something a machine consumer must read to validate a payload — [`json_schema`](./pipe-io-contracts.md#the-input-schema) keeps that job. A caller ignoring the descriptor entirely loses no fact it needs.
- **No layout or styling.** Field order is the authored order, not a layout. Grouping, sizing, and theming belong to consumers.
- **No committed artifacts.** The descriptor is derived on demand. Nothing is generated into a consumer's repository, stamped, or locked.
- **No result presentation.** The descriptor describes a method's *inputs*. Presenting what a run produced is a separate concern this artifact does not address.

## Relationship to Other Specifications

- [.mthds File Format](./mthds-format.md) defines the input slots, concepts, and structure fields the descriptor projects.
- [Library Crate Format](./library-crate.md) defines the resolved library the descriptor derives from — the authority on refinement, presence, multiplicity, and defaults.
- [Pipe I/O Contracts](./pipe-io-contracts.md) is the machine contract over the same pipes, keyed by the same `pipe_ref` set, and carries the `json_schema` the `unknown` kind falls back to.
- [Intent Hints](./intent-hints.md) owns the hint vocabulary the `hints` slot carries; this page defines only how the effective merge reaches the wire.
- [Native Concept Definitions](./native-concepts.md) pins the native concepts the kind-assignment table maps.
- [HTTP Runner Protocol](./protocol.md#validating-a-bundle) carries the artifact as a recommended extension field of the validate response.
