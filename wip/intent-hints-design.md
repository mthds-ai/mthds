# Intent hints — the H1 language design session

**Status:** design session run 2026-08-22, milestone H1 of the workspace input-form roadmap (`../wip/devx/input-form-roadmap.md`, Track H). The output is the normative spec page [`docs/spec/intent-hints.md`](../docs/spec/intent-hints.md) plus the structural additions to [`docs/spec/mthds-format.md`](../docs/spec/mthds-format.md) and [`docs/spec/library-crate.md`](../docs/spec/library-crate.md). Acceptance happens through the standard's process: this branch becomes the PR; H1 closes when it merges. Inputs read: the adopted direction (`../wip/devx/input-form-projection.md`, Layer 3), the frozen descriptor spec (`../docs/specs/mthds-input-form-descriptor.md`, "The reserved hint slot"), and the S1 language-side ceiling (`pipelex` branch `feature/Input-semantics`, `wip/input-semantics/findings.md` §B).

Two constraints were contracted before this session and were not reopened: hints are **non-normative** (execution and validation never read them; no hint changes a verdict, a gating rule, or a payload contract), and **consumers that ignore hints stay correct** (no hint means the deriver's defaults apply; a hint refines presentation, never enables it).

## The split of S1 §B — semantics versus intent

The session's first job was to split the language-side ceiling into what needs a *semantic* home in the language and what belongs to the *hint* layer. The result is stark, and it is the session's most important finding: **almost everything the language cannot express today is semantic; only rendering intent belongs in `hints`.** The hint layer is deliberately tiny because the discipline demands it — a range, a unit, an example serves validation, documentation, and agent tool-calling at once, and smuggling any of them in as a "UI hint" would strand them in a layer only renderers read.

| §B entry | Disposition | Where it belongs |
|---|---|---|
| Numeric ranges (`minimum`/`maximum`/exclusive bounds) | semantic | structure-field keys; the schema vocabulary is already proven engine-side (the direction doc's slider example) |
| String constraints (length bounds, pattern) | semantic | structure-field keys |
| Examples (field, concept, slot level) | semantic | an `examples` slot; the descriptor already reserves the wire side |
| Units | semantic | a unit is meaning — it changes documentation, agent tool-calling, and any conversion, not just the control |
| Per-input-slot description | semantic | the expanded input-slot form this design introduces is deliberately shaped to receive a `description` key later (see decision 4) |
| Per-slot defaults and examples | semantic | same future home |
| Non-string choices | semantic | `choices` typing |
| Choice labels and per-choice descriptions | semantic | display content serves docs and agent tool-calling, not only forms |
| Inner type of nested lists | semantic | list typing |
| Multiple refinement | semantic | type system |
| Refine-and-extend | semantic | type system |
| Defaults on concept-typed fields | ceiling kept | the rejection is arguably correct; unchanged |
| Rendering intent (prose vs label, rating, quantity, …) | **intent** | the `hints` layer — the only §B entry that lands there |

The semantic column is not designed here. It is the upstream worklist for the language's semantic growth (S2 covers the engine-side half; the language-side syntax for these is its own future session). This session only made sure the hint layer cannot become their accidental home.

## Decisions

1. **One defined hint key, `intent`, with a closed vocabulary: `prose`, `label`, `rating`, `quantity`.** Each word names what a value *is*, never how to draw it. `prose`/`label` replace the worst proven guess in the field (prose-versus-label decided by nesting depth and a `maxLength > 120` magic number); `rating`/`quantity` are the intent half of the direction doc's slider example — the bounds are semantic, the "this number is a judgment / an amount" is intent.

2. **`choice` is dropped from the vocabulary, deliberately.** The direction doc listed it as an example, but everything `choice` would signal is already a semantic fact: the `choices` field. A hint that duplicates a semantic fact violates "semantics first, hints second" — and radio-versus-dropdown scale decisions are widget territory a renderer derives from the choice count. Recorded as a rejected candidate, not a deferred one.

3. **Three authoring sites, two attachment levels.** Concept-level knowledge travels with the concept and has two sites: the concept itself (`hints` beside `description`/`refines`/`structure`) and each structure field (`hints` in the field blueprint). Slot-level override has one site: the pipe input slot, via the new expanded slot form. A concept's hints describe the concept's own presentation as a value; they never distribute to its fields — each field is its own site.

4. **The expanded input-slot form: `name = { concept = "RefString", hints = { … } }`.** The string form stays unchanged and is exactly equivalent to a table carrying only `concept`; the `concept` key carries the full existing slot grammar (ref + multiplicity + presence marker). This is the smallest syntax that gives slots an attachment point — and it is deliberately the future home for the *semantic* per-slot keys (`description`, later defaults/examples), so the language never needs a second slot syntax. Unknown keys in the slot table are rejected (normal language strictness); only hint *content* is lenient. The expanded form is inputs-only; `output` stays a string, because concept-level hints already cover result presentation.

5. **Precedence is one rule, key by key: the site wins over the concept; along a refinement chain, the nearer declaration wins.** Stated once in the spec, used everywhere. On plural sites (a `[]`/`[N]` slot, a list-typed field), an applicable word refines each item's presentation — list-ness itself is semantic.

6. **Strict shape, lenient content.** The `hints` table's shape (a flat map of string keys to string values) is validated like any other blueprint member — loud at author time, which is the answer to §B's silent-failure asymmetry (E7). Its *content* (unknown keys, unknown words, words on inapplicable sites) MUST NOT be rejected, SHOULD warn, and well-formed unknown entries are preserved into the crate. The reconciliation with "no hint changes a verdict": the two governing rules bind the *meaning* of hints, not the well-formedness of the bundle — a malformed `hints` member is not a hint, it is a structural error like `description = 42`.

7. **The flatness invariant makes growth non-breaking.** Future standard versions may add keys and words but will never change the shape (flat string → string). That is what lets an implementation validate shape strictly while staying lenient about content it does not know: a bundle authored against a newer standard never fails an older implementation's shape check because of its hints. Vocabulary is pinned per standard version, like native concept definitions; additions are minor versions.

8. **Crate travel: hints ride the blueprint objects and are fingerprinted.** Normalization materializes each concept's *effective* hints (the refinement-chain merge, so consumers never chain-walk for hints — same principle as effective structure) and removes empty hint tables; a slot carrying no hints normalizes exactly as before hints existed, so hint-free libraries keep their fingerprints. Hints are inside the hashed members, hence inside the fingerprint — a hint edit is a semantic change to the method's presentation, and two crates differing only in hints are distinct artifacts (same precedent as domain `description`, which is fingerprinted because it surfaces in documentation).

9. **Pinned native definitions carry no hints in this version.** A refinement of a native (`Prompt refines native.Text` with `hints = { intent = "prose" }`) is the natural way to make a reusable hinted text concept.

## Deferred vocabulary candidates

Recorded so the next vocabulary session starts from the reasoning, not from scratch:

| Candidate | Why deferred |
|---|---|
| `code` | Real intent (a template or snippet is not prose), but no recorded guessing-pain behind it yet; v1 admits only words with proven pain. |
| `secret` | Sensitivity is arguably semantic — if it should affect logging or storage, it must not be a hint. Needs the semantic question answered first. |
| `identifier` | Overlaps `label`; unclear it changes a presentation decision. |
| `url`, `email`, and friends | These are semantic string formats (`format` territory in the constraint work), not intent. |

## What H2 needs from this design

The engine milestone (H2, in `pipelex`) implements the round trip. The implementation surface this design implies:

- Parse `hints` on the concept blueprint (extras are forbidden there today — a new field), on the structure-field blueprint (extras are silently ignored there today — a new field; the E7 strictness fix is separate work), and the expanded input-slot form (today slot values are ref strings only; the rejected-table fixture flips to an accepted shape with exactly `concept` + `hints`).
- Shape errors are validation errors; unknown hint keys/words produce warnings on the diagnostics channel and are preserved.
- Crate normalization: effective-hints materialization on concepts, empty-table removal, hint-free output byte-identical to today.
- The input-form descriptor's reserved `hints` slot gets populated with each site's effective hints, and the no-hint defaults are promoted from heuristics to specified rules (already H2's mandate).
- `mthds_schema.json` regeneration and the schema-sync propagation to the downstream copies; the workspace conformance pair for the descriptor's hint slot.

## Follow-ups after acceptance

- On merge, notify H2 through the workspace `wip/inbox/` (per the roadmap's execution protocol) and record the H1 checkpoint in `wip/devx/input-form-roadmap.md` with the landing SHA.
- The Language section of this site (`docs/language/concepts.md`, the pipes pages) should present hints example-led once the spec is accepted — kept out of this PR so the normative proposal stays reviewable on its own.
- The workspace descriptor spec's "reserved hint slot" section can then link to the accepted `spec/intent-hints.md` page as the vocabulary owner.
