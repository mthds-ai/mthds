---
description: "Formal specification of MTHDS intent hints — optional, non-normative presentation intent attached to concepts, structure fields, and pipe input slots."
---

# Intent Hints

Intent hints let a bundle author state what a value *is* to the person providing or reading it — so any consumer rendering the method (a fill-in form, a result view, a documentation page) can present it well without guessing.

```toml
[concept.Instructions]
description = "Steering instructions for how the work should be done"
refines     = "native.Text"
hints       = { intent = "prose" }
```

A hint names **intent, never a widget**. `prose` says the value is flowing natural language; it does not say `textarea`. Intent survives design systems and decades; widget names do not — the same lesson HTML's input types encode, where `type="tel"` names what the value is and each platform decides what that means for presentation.

Hints are strictly optional and strictly presentational. Everything a value *is* structurally — its type, its structure, its allowed choices, its presence, its multiplicity — belongs to the semantic layer of the language, and hints never carry any of it.

## Specification Status

This document specifies a forward contract: no implementation realizes it yet. It follows the same convention as the not-yet-implemented sections of the [Library Crate Format](./library-crate.md#specification-status) — implementations are brought into conformance with this document, and conformance is asserted as each piece lands.

## The Two Governing Rules

Every hint, present and future, is bound by two rules:

1. **Hints are non-normative.** An implementation MUST NOT consult hints when executing a pipe, validating a payload, deciding whether an input blocks a run, or producing any verdict about a bundle, library, or method. The presence, absence, or content of any well-formed hint MUST NOT change any of those outcomes.
2. **Consumers that ignore hints stay correct.** Every site is presentable with no hint: absence means the consumer's own defaults apply, derived from the semantic layer. A hint refines a presentation the semantics already determine; it MUST NOT be the only source of any fact a consumer needs.

A corollary the vocabulary below obeys, and every future addition MUST obey: **a hint never carries a semantic fact.** A bound, a unit, an example, a description, a set of allowed values — anything that changes what a value *is* — belongs to the language's semantic surface, where it serves validation, documentation, and tool-calling at once, not only rendering.

## The `hints` Table

A hint attachment is a TOML table named `hints`:

```toml
hints = { intent = "prose" }
```

**Shape rules (strict):**

- `hints` MUST be a table.
- Every value in the table MUST be a string.
- A `hints` member violating this shape is a structural error in the bundle, exactly like any other field-type violation.

**Content rules (lenient):**

- This version of the standard defines one key: `intent`, whose value is a word from the [vocabulary below](#the-intent-vocabulary).
- An unknown key, or an unknown `intent` word, MUST NOT be rejected. A validating implementation SHOULD report it as a warning. Well-formed unknown entries MUST be preserved when producing a [library crate](./library-crate.md).
- An empty `hints` table is equivalent to no `hints` at all.

The split is deliberate, and the two governing rules explain it: they bind the *meaning* of hints, not the well-formedness of the bundle. A malformed `hints` member is not a hint — it is broken structure, and it fails loudly at author time. A well-formed hint an implementation does not recognize is content from a newer vocabulary, and it passes through untouched.

**The flatness invariant:** the `hints` table is, and will remain, a flat map of string keys to string values. Future versions of the standard MAY define new keys and new intent words; they will not change the shape. This is what lets an implementation validate the shape strictly while staying lenient about content it does not know — a bundle authored against a newer standard version never fails an older implementation's shape check because of its hints.

## The Intent Vocabulary

The `intent` key takes one word from a closed vocabulary, pinned per standard version like the [native concept definitions](./native-concepts.md). This version defines:

| `intent` | Applies to | Declares |
|----------|------------|----------|
| `prose` | text-valued sites | The value is flowing natural language — sentences meant to be written and read as running text. |
| `label` | text-valued sites | The value is a short designation — a name, a title, a heading; a few words on a single line. |
| `rating` | number-valued sites | The value is a subjective score on a scale — a judgment, not a measurement. |
| `quantity` | number-valued sites | The value is an amount of something — a count or a measured magnitude. |

**Applicability:**

- A **text-valued site** is a structure field with `type = "text"`; a concept that is `native.Text` or whose refinement chain reaches `native.Text`; a structure field with `type = "concept"` whose `concept_ref` names such a concept; or an input slot whose concept is such a concept.
- A **number-valued site** is a structure field with `type = "integer"` or `type = "number"`; a concept that is `native.Number` or whose refinement chain reaches `native.Number`; a structure field with `type = "concept"` whose `concept_ref` names such a concept; or an input slot whose concept is such a concept.
- On a **plural site** — an input slot with `[]` or `[N]` multiplicity, or a structure field with `type = "list"` — applicability is judged against the item: the slot's concept, the field's `item_type`, or the concept its `item_concept_ref` names when `item_type = "concept"`. An applicable word refines the presentation of each item. The collection's own presentation follows from its semantics.
- An intent word attached to a site it does not apply to has no defined meaning: a consumer ignores it, and a validating implementation SHOULD report it as a warning, never as an error.

How a consumer honors a word is the consumer's decision, and this specification deliberately names no controls. A consumer might give `prose` room to write, keep `label` to a single line, and present a `rating` against its bounds where the semantic layer provides them — or do none of that and remain conformant.

## Attachment Sites

Hints attach at three sites, forming two levels: **concept-level** knowledge that travels with the concept wherever it is used, and a **slot-level** override local to one pipe input.

### On a Concept

The concept blueprint accepts an optional `hints` field beside `description`, `structure`, and `refines` (see [Concept Blueprint Fields](./mthds-format.md#concept-blueprint-fields)):

```toml
[concept.Instructions]
description = "Steering instructions for how the work should be done"
refines     = "native.Text"
hints       = { intent = "prose" }
```

A concept's hints apply wherever the concept is presented — as an input slot's value, as a structure field's referenced concept, as a list item, or in a rendered result. They describe the concept's own presentation as a value; they never distribute to the concept's structure fields, each of which is its own site.

A refining concept inherits its base's hints along the refinement chain, a nearer declaration winning key by key. The pinned native concept definitions carry no hints in this version of the standard; a refinement of a native is the natural way to author a reusable hinted concept.

### On a Structure Field

Each field blueprint accepts an optional `hints` key (see [Field Blueprint](./mthds-format.md#field-blueprint)):

```toml
[concept.CandidateProfile.structure]
full_name = { type = "text", description = "Full name", required = true, hints = { intent = "label" } }
bio       = { type = "text", description = "Short biography", hints = { intent = "prose" } }
```

### On a Pipe Input Slot

An input slot declared in the expanded form accepts an optional `hints` key (see [Input slot declarations](./mthds-format.md#pipe-definitions)):

```toml
[pipe.summarize]
type        = "PipeLLM"
description = "Summarize a contract, following optional steering instructions"
output      = "Summary"

[pipe.summarize.inputs]
contract     = "legal.Contract"
instructions = { concept = "Text?", hints = { intent = "prose" } }
```

Slot-level hints exist on inputs only. Result presentation is served by concept-level hints on the output concept.

## Precedence and Inheritance

The effective hints of a site are assembled **key by key** from at most two layers:

1. the hints of the concept that types the site — where a refining concept inherits its base's hints along the refinement chain, a nearer declaration winning key by key;
2. the site's own hints — a structure field's `hints`, or an input slot's `hints` in the expanded form.

The site layer wins, key by key. A key absent at every layer is absent, and the consumer's defaults apply.

A key declared at a farther layer can be **overridden** at a nearer one, but not **cleared**: there is no syntax to unset an inherited key. An empty `hints` table is equivalent to no hints and so inherits everything; an empty string is an unknown word, not a clearing mark. A refinement or site that wants a different presentation names the intent it wants. Should a later version of the standard define a clearing mark, it is a vocabulary addition under [Vocabulary Growth and Versioning](#vocabulary-growth-and-versioning).

```toml
[concept.Summary]
description = "A summary of the source material"
refines     = "native.Text"
hints       = { intent = "prose" }

[pipe.make_tagline]
type        = "PipeLLM"
description = "Condense a summary into a one-line tagline"
output      = "Text"

[pipe.make_tagline.inputs]
summary = { concept = "Summary", hints = { intent = "label" } }
```

`Summary` is prose everywhere it appears — except in `make_tagline`, whose slot declares that *this use* of a summary is a one-liner. The slot's `label` overrides the concept's `prose` for that site only.

## Hints in the Library Crate

Hints ride the concept and pipe objects of the [normalized library crate](./library-crate.md) — they are blueprint content like any other. Normalization gives them their canonical form in two steps:

- Each concept carries its **effective hints** — the key-by-key merge along its refinement chain — assembled when refinement is flattened (see [Flatten Refinement](./library-crate.md#3-flatten-refinement)), the same pass that gives a flattened concept its complete effective field set. A consumer reads a concept's hints without walking the chain, which after that step no longer exists.
- Empty `hints` tables are removed when defaults and multiplicity are materialized (see [Materialize Defaults and Multiplicity](./library-crate.md#5-materialize-defaults-and-multiplicity)). A slot, field, or concept carrying no hints normalizes exactly as it did before hints existed, so a library that authors no hints keeps its fingerprint.

Hints live inside the crate's hashed members and are therefore part of its [fingerprint](./library-crate.md#fingerprint): a hint edit is a change to the method's authored presentation, and two crates differing only in hints are distinct artifacts — the same reasoning that fingerprints a domain's `description`.

## Vocabulary Growth and Versioning

- The vocabulary and the set of defined keys are pinned per standard version. Additions are minor versions of the standard.
- A word, once defined, is never reused with a different meaning. Removing a word is a major version.
- The content-leniency rule above is what makes growth non-breaking in practice: an implementation built against this version warns on, preserves, and otherwise ignores words and keys from a later one.

## Non-Goals

- **No widget vocabulary.** `textarea`, `slider`, `dropdown`, and their kin are not, and will never be, hint values.
- **No layout or styling.** Field order is authored input order — a semantic fact. Sizing, grouping, and theming belong to consumers.
- **No validation semantics.** A hint never participates in any verdict; the semantic layer alone decides what a valid payload is.
- **No per-consumer targeting.** A hint states intent once, for every consumer; there is no syntax to address a hint to one kind of surface.
