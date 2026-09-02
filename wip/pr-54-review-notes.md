# PR #54 review notes — deferred items

Deferred findings from the review-agent triage of [PR #54](https://github.com/mthds-ai/mthds/pull/54) (`feature/Codegen`). Everything else surfaced in that pass was fixed in the PR itself.

## How package identity is carried in the merged keyspace

> **Resolved 2026-08-27.** The owner decision was taken in the packaging interview (workspace `docs/package/interview.md`, round 2.2): **host-relative `::` keys**, exactly as recommended below — dependency-contributed entries keyed by package address, host entries bare, existing single-package fingerprints preserved. Adopted into `docs/spec/library-crate.md` (§1 Merge, §2 Fully Qualify) by the package-spec rewrite. The analysis below is kept as the record of why.

**Where:** `docs/spec/library-crate.md` §1 Merge and §2 Fully Qualify Every Reference.

**Reporters:** greptile-apps (P1) and cubic-dev-ai (P2), both on the same underlying issue.

**The issue.** As originally written, §1 claimed "the merged keyspace is global and collision-free" and §2 said a cross-package `alias->domain.Code` reference is rewritten to "the canonical qualified ref of the target in the merged keyspace", dropping the `->` alias. But the standard explicitly permits the collision those sentences assume away:

- `docs/spec/namespace-resolution.md:143` — "Two packages MAY declare the same domain name (e.g., both declare `domain = "recruitment"`). Their concepts and pipes are completely independent — there is no merging of namespaces across packages."
- The Conflict Rules table on the same page, final row — "Different packages | Same domain and same concept/pipe code | **No conflict — package isolation**."
- Restated at `docs/implementers/package-loading.md:97` ("The isolation boundary is the package, not the domain") and `docs/language/domains.md:78`.

So two independently-valid dependencies both declaring `recruitment.CandidateProfile` is a *sanctioned* configuration. Once the alias is dropped, a bare `domain_path.Code` key cannot tell the two apart: they collapse onto one key, producing either a spurious duplicate-key rejection or a silent resolution to the wrong definition. The old §1 text even cited the Conflict Rules table as its authority — a citation that lands on the row saying the opposite.

**What was fixed in the PR.** Only the contradiction. §1 and §2 no longer assert a false guarantee: they now state that MTHDS permits the same domain across packages, that a bare `domain_path.Code` key is therefore not a global identity, and that the key form is part of cross-package closure fold-in, which the document does not yet specify (it is already listed as unrealized forward contract in §Specification Status). The design below is deliberately **not** adopted yet.

**Why deferred.** Choosing the key form is a normative design decision with wide blast radius — it is baked into the `fingerprint`, into both encodings, and into every third-party consumer that reads a crate. It deserves an explicit owner decision rather than a PR-review pass, especially since cross-package fold-in is not implemented yet and nothing is currently broken by the silence.

**Recommendation.** Key dependency-contributed entries by **package address**, host entries by bare qualified ref:

```
host entry        →  scoring.WeightedScore
dependency entry  →  github.com/acme/legal-tools::legal.contracts.ContractClause
```

Supporting evidence, all already in the standard:

- `::` is the established separator and address-prefixing the established identity scheme — `docs/packages/registry-indexing.md:169` uses `{package_address}::{concept_ref}`, as does `docs/packages/registry-search.md:173`. `__native__` is the existing precedent for a synthetic address.
- The address is globally unique by definition (`docs/spec/manifest-format.md:28`, `:39`).
- It must be the **address, not the alias**. An alias is a key in the consuming package's `[dependencies]` (`docs/spec/namespace-resolution.md:100`), so it is consumer-local: two consumers of one dependency may name it differently, and an alias-keyed crate would give semantically identical libraries different fingerprints, breaking the canonicality guarantee.

**Host-relative rather than uniform prefixing**, for two reasons:

1. A standalone bundle has **no package address** — "No package address (not distributable)" (`docs/spec/manifest-format.md:247`) — so a uniform scheme has nothing to prefix host entries with.
2. Host-relative leaves already-realized single-package crates and their fingerprints byte-identical (§Specification Status records steps 1–4 and 6 as shipped).

Adopting it also needs a TOML clause: an address-qualified key contains `/` and `::` as well as dots, so it is likewise one quoted key (`["concepts"."github.com/acme/legal-tools::legal.contracts.ContractClause"]`), never a dotted path.

**Open question for the owner:** adopt host-relative `::` keys as above, or give the host a synthetic address (on the `__native__` precedent) so every key is uniformly prefixed? The synthetic-address option is more regular but changes every existing key and breaks the fingerprints of already-realized single-package crates.

## `native.Image` positivity constraint is enforced but not pinned

**Where:** `docs/spec/native-concepts.md` §native.Image.

**Reporter:** none — found while verifying a cubic-dev-ai comment about the `width`/`height` pairing.

**The issue.** The reference implementation constrains both pixel dimensions to be positive (`gt=0` on `width` and `height` in `pipelex/pipelex/core/stuffs/image_content.py`), alongside the both-or-neither model validator. The pinned definition on this page declares only `type = "integer"`. So a constraint the reference implementation enforces is invisible in the normative definition — the same class of gap as the pairing, but unlike the pairing it is not even stated in prose.

The PR added a sentence clarifying that the pairing constrains values rather than the blueprint, and that a validating runtime is what enforces it. Positivity is arguably covered by that same sentence's logic, but it is nowhere written down.

**Why deferred.** It is a judgment call about what the pinned set is *for*. If the pinned definitions are the complete normative contract, positivity belongs in them — but the structure language has no minimum-value form, so expressing it means either a language addition or a description reword, and per this page's own rule (line 9) any reworded description is a standard change requiring a version bump and churning every fingerprint. If instead the pinned set is deliberately the *structural* surface with semantics stated beside it, then positivity should simply be documented in prose like the pairing is.

**Recommendation.** Decide the convention once and apply it to the whole page, rather than patching `Image` alone. The page already carries several prose-only semantics beyond the structure language — the `url` value domains, `Date`'s "never an invented midnight and never reads numeric epoch input", the structureless-by-design note — so a single paragraph stating that a definition's `structure` is its machine-checkable surface and not its whole contract would cover all of them, and would let `Image` positivity be added as ordinary prose with no fingerprint impact.

**Open question for the owner:** should the pinned set carry only what the structure language can express (with semantics documented beside it), or should the structure language grow constraint forms (minimum, cross-field co-presence) so the crate becomes sufficient for full instance validation as well as type projection?
