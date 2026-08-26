# PR #57 review notes — deferred items

Deferred findings from the review-agent triage of [PR #57](https://github.com/mthds-ai/mthds/pull/57) (`feature/Input-form`). Everything else surfaced in that pass was fixed in the PR itself.

## The normative OpenAPI document does not declare the two recommended extension fields

**Where:** `docs/spec/openapi/mthds-protocol.openapi.yaml`, the `ValidationReport` schema — prompted by the paragraph this PR added at `docs/spec/protocol.md:73`.

**Reporter:** greptile-apps (P1).

**The issue.** This PR makes the HTTP Runner Protocol recommend that a validate response's `is_valid: true` arm carry `pipe_io_contracts` and `input_form`, whose shapes the two new specification pages define. Neither name appears in the OpenAPI document. Greptile's premise is correct and worth conceding rather than waving away: `protocol.md:9` says "The normative artifact is the OpenAPI document… Where prose and YAML disagree, the YAML wins", and `protocol.md:98` defines conformance as the five routes having "the request/response shapes of `mthds-protocol.openapi.yaml`". The document is hand-maintained in this repo — no codegen, no sync from elsewhere — so adding to it would be legitimate. And this is the first time the prose names a response field the YAML does not declare; before this PR the YAML lagged the prose on nothing.

**Why deferred.** Four reasons, none of which is "it does not matter":

1. **There is no prose/YAML disagreement, so the precedence rule never fires.** `ValidationReport` carries `additionalProperties: true`, and `protocol.md:94` states the design deliberately — "the protocol's response schemas declare only the base fields". The new paragraph opens by affirming the base fields are unchanged. A client reading only the YAML correctly concludes that extensions are unconstrained there, which is true. What the YAML omits is a SHOULD-level recommendation — a category it has never carried.

2. **The "undeclared means untyped" consequence is already owned, and not by this document.** Typed clients here do not generate from the OpenAPI: the program's Stage 2 gives `mthds-js` a `src/protocol/` module and `mthds-python` pydantic models with `extra="forbid"`, and Stage 3 types the SDK field by importing those, not by codegen. That work is sequenced in ledger items across four repos, blocked on this PR.

3. **Freezing the shapes now inverts the program's own sequencing.** The gate immediately after this PR is Checkpoint 1, whose whole point is that it is the last cheap moment to change a slot name. Encoding both shapes into the normative contract before that ratification is exactly the "a type never leads the page that defines it" rule the program set for itself.

4. **A faithful declaration is not a review-sized edit, and a loose one would be worse than silence.** Both pages declare closed shapes (`pipe-io-contracts.md:143`, `input-form-descriptor.md:211`) over a recursive union of eleven `kind` values with per-kind required slots, a three-valued `presence`, and a content-lenient `hints` map. Declaring `pipe_io_contracts: {type: object}` would satisfy "discoverable" while actively misstating the strictness rule. Doing it properly is a `$ref`-heavy recursive schema — and its most load-bearing member is deliberately unpinned: `L-260826-8bd4b8` records that `json_schema`'s dialect and the concept-to-schema projection are not fixed by this version. Writing a normative machine schema around a knowingly unspecified centre bakes in the ambiguity.

There is repo precedent for this exact class of deferral: `wip/intent-hints-design.md:76` already records that the OpenAPI defines no advisory-warnings member for the hints spec's SHOULD-warn rules and calls it its own follow-up. And `library-crate.md` — a full normative artifact format — has no machine-readable counterpart in this repo at all. The house pattern is that prose pages own artifact shapes while the YAML owns the HTTP surface.

**Recommendation.** Do it once Checkpoint 1 ratifies the slot names, and preferably when that file is next opened anyway — there is already an opportunistic item queued against it, `L-260826-11f836` (swap the three single-value `enum: [x]` to `const: x`). Be clear about what the edit is, though: it is deliberately the loose declaration reason 4 argues against, so it is worth taking only if the open question below is answered *yes, a discoverable name is worth having on its own*. It buys that name and nothing more — it states nothing true about either shape, and a reader who takes `type: object` for the whole story reads the strictness rule backwards. On those terms, the smallest edit is two properties under `ValidationReport.properties`, neither in `required`:

```yaml
pipe_io_contracts:
  type: object
  description: >-
    Recommended extension field (SHOULD) — per-pipe input/output contracts.
    Shape defined by the Pipe I/O Contracts specification, not by this document.
input_form:
  type: object
  description: >-
    Recommended extension field (SHOULD) — per-pipe ordered presentation view.
    Shape defined by the Input-Form Descriptor specification, not by this document.
```

**One thing that edit must not forget:** it makes the sentence at `protocol.md:94` ("the protocol's response schemas declare only the base fields") inaccurate, so the two move together. That buys discoverability only — full typing stays with the Stage 2 protocol packages, which is where the plan already puts it.

**Open question for the owner:** is discoverability-without-shape worth having at all, or should the YAML stay silent until the two shapes are pinned tightly enough to declare faithfully? The thread on the PR is left open for that call.

## The intent-hints follow-up bullet describes a divergence that does not exist

**Where:** `wip/intent-hints-design.md:75`, the third bullet under "Follow-ups after acceptance". Predates the review rounds — it arrived with the branch's first commit, `c8832e7`.

**Reporter:** cubic-dev-ai (P3, confidence 6). [Thread on PR #57](https://github.com/mthds-ai/mthds/pull/57#discussion_r3864869240).

**The issue.** The bullet reads: "The hints spec treats a description-only concept (neither `structure` nor `refines`) as text-valued, as the reference implementation does (it refines `native.Text` at run time); Library Crate step 6 still promotes the string-shorthand form to a 'structureless' concept with no `refines`. Aligning step 6 with that reading is a follow-up on the crate spec." Cubic is right that there is nothing to align, and every citation checks out:

- `docs/spec/intent-hints.md:70` already makes a concept "that declares neither `structure` nor `refines`" text-valued, in the applicability list itself.
- `docs/spec/input-form-descriptor.md:145` states that this text-valuedness reaches the wire "as `kind: \"prose\"` and **never as a fabricated refinement link**", because "the language states description-only text-valuedness as an arm of its own, not as refinement of `native.Text`, and a producer inventing that link would be reporting ancestry no one authored — precisely what the derivation requirement below forbids".
- `docs/spec/library-crate.md:125` (step 6) promotes the string-shorthand form to a **structureless** concept with no `refines`, which is that rule correctly applied — not a divergence from it.

So the crate spec is already saying the right thing, and the "alignment" the bullet gestures at — giving the promoted concept a `refines native.Text` — is the one move a normative page explicitly forbids. The bullet also aims at the wrong repo: the fabricated `refines native.Text` link is the *reference implementation's* run-time behaviour, and dropping it is already filed as ledger item `L-260826-0ed8dd` (owner `pipelex`).

**Why deferred.** It is a pre-existing inaccuracy in a work-in-progress design note rather than a regression this PR's review rounds introduced, and it blocks no merge — which puts it below the bar a second review round applies. It is real, though, and left alone it is the kind of follow-up someone eventually acts on.

**Recommendation.** Rewrite the bullet, or drop it. If rewritten, it should say the opposite of what it says now: Library Crate step 6 is correct as written, the descriptor forbids the `refines native.Text` link, and the outstanding work is on the implementation side under `L-260826-0ed8dd` — nothing is owed by the crate spec.
