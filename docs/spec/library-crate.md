---
description: "Formal specification of the normalized library crate — the flat, fully-qualified, self-contained, fingerprinted snapshot a consumer resolves an MTHDS library into, in normal form."
---

# Library Crate Format

The **library crate** is the resolution artifact of the MTHDS standard: the flat, fully-qualified, self-contained snapshot that a whole library resolves into. Where `METHODS.toml` resolves *which files* make up a package and `methods.lock` pins *which versions* of its remote dependencies, the library crate captures *what the resolved files mean* — every concept, pipe, and domain, merged across all bundles and keyed by qualified reference.

A crate exists in one of two forms:

- **Authored form** — the concise, elided, multi-bundle style people and agents *write*: smart defaults, bare references, refinement, string-described concepts, spread across sibling bundles.
- **Normalized form** — the closure assembled and made fully explicit, optimized for machines *consuming* methods. This document specifies the **normalized library crate**.

The normalized library crate is not a new format. It is MTHDS content — the same blueprint model every validator, runner, and loader already operates on — carrying a guarantee: **closed** (needs nothing outside itself), **canonical** (byte-reproducible), and **valid** (built only from a library that passed validation). That guarantee is what lets a consumer with only a JSON or TOML parser emit correct types, render a correct form, or register a correct tool — with no MTHDS frontend, no namespace resolver, and no hardcoded knowledge of native concepts.

## Specification Status

This document specifies the **target** normal form and its guarantees. A reference implementation now realizes most of it: the [normalization pass](#normalization-pass) steps 1–4 and 6 (merge, in-body reference qualification, refinement flattening, native materialization from the pinned definitions, string-concept promotion), both [encodings](#encodings), and the fingerprint over the [full scope](#scope) — for a closure drawn from a single package. Step 5 ([defaults and multiplicity materialization](#5-materialize-defaults-and-multiplicity)), the effective-hints assembly in step 3 (added with [Intent Hints](./intent-hints.md), itself a forward contract), the [canonicalization](#canonicalization) rule that absent members are omitted rather than hashed as `null`, and the application of cross-package closure fold-in are not yet applied — the fold-in's merged keyspace and reference-rewriting rules are now specified below (see [Merge](#1-merge)), and the pass that applies them is forward contract. Where a section below describes behavior a reference implementation has not yet realized, it is the **forward contract** that implementation is brought into conformance with — the same convention [METHODS.toml Manifest Format](./manifest-format.md#the-dependencies-section) uses to spec the `[dependencies]` section. Conformance is asserted against this document as each piece lands.

## The Three Units: Bundle, Library, Pipe

MTHDS methods are deliberately *not* one-file-one-method. A pipe's sub-pipes and the concepts it references are spread across sibling bundles, and cross-package references pull in whole other methods. A single bundle is therefore not self-contained and is the wrong unit to resolve. The standard distinguishes three units precisely:

| Unit | What it is | Grounded in |
|------|------------|-------------|
| **bundle** | one authored `.mthds` file — a domain's concepts and pipes | a bundle blueprint (see [.mthds File Format](./mthds-format.md)) |
| **library** | the resolved *closure* across all needed bundles (working files + local method cache), flat and fully qualified | package loading (see [Package Loading](../implementers/package-loading.md)) |
| **pipe** | one runnable entry point, selected by qualified `pipe_ref`, defaulting to a package's `main_pipe` | the execution path |

The resolution rule that follows: **resolve a library; project types over its concept set; project runnable artifacts per pipe.** A person who "has a method" has a runnable *pipe* (usually a package's exported entry pipe); the *library* is the closure that pipe was resolved within; the *bundle* is just a file inside it.

The normalized library crate is the serialized form of the **library** unit.

## Closure Assembly

The library closure is assembled from two sources:

1. **Working bundles** — the `.mthds` files being resolved (the current package's own bundles).
2. **The local method cache** — dependency methods vendored on disk under `.mthds/methods/<name>/`, each a package directory (`METHODS.toml` + one or more `.mthds` bundles).

A compliant implementation discovers the local method cache by walking up from each working bundle's directory toward the filesystem root, collecting every `.mthds/methods/` directory it finds (the same ancestor-walk used for manifest discovery in [METHODS.toml Manifest Format](./manifest-format.md#manifest-discovery)). Cross-package references (`alias->domain_path.name`) resolve against the cached dependency identified by the alias, following [Namespace Resolution Rules](./namespace-resolution.md#resolution-of-package-qualified-references).

> **Two caches, one deterministic read.** There are two distinct dependency caches, and closure assembly reads only the first:
>
> - the **project-local method cache** — `.mthds/methods/<name>/`, keyed by dependency name, vendored inside the consuming project and discovered by the ancestor-walk above. This is the cache closure assembly resolves against.
> - the **global VCS cache** — `~/.mthds/packages/{address}/{version}/`, keyed by address and resolved version, described in [Namespace Resolution: Cache Layout](./namespace-resolution.md#cache-layout) and [Package Loading: VCS Fetching](../implementers/package-loading.md#vcs-fetching).
>
> A cross-package reference's *logical identity* is its package address (e.g. `github.com/mthds/document-processing`); its *physical resolution* in scope for this specification is the vendored copy in the project-local cache. Populating that cache from a remote address over the network — fetching into the global VCS cache and materializing it project-local, lock-pinned to a commit — is the **install step**, specified in [Distribution: The Two Caches](../packages/distribution.md#the-two-caches); it slots in *before* closure assembly. Nothing in this specification depends on how the project-local cache was populated; resolution reads from disk and is fully deterministic.

The closure is the transitive union of the working bundles and every dependency bundle reachable through cross-package references, indexed by domain and package exactly as described in [Package Loading: Library Assembly](../implementers/package-loading.md#library-assembly). Namespace isolation between packages is preserved during assembly; the normalization pass below flattens the result into a single qualified keyspace.

## Crate Structure

A normalized library crate is an object with the following members. The same logical structure is shared by both encodings (JSON and TOML); the field names are neutral and carry no implementation-brand prefix.

| Member | Type | Required | Description |
|--------|------|----------|-------------|
| `mthds_version` | string | Yes | The MTHDS standard version the crate was normalized against, so native expansion (below) is self-describing. |
| `concepts` | map of qualified concept ref → concept object | Yes | Every concept in the closure, keyed by its crate key: the fully-qualified `concept_ref` (`domain_path.ConceptCode`) for host entries, address-prefixed (`package_address::domain_path.ConceptCode`) for dependency-contributed entries (see [Merge](#1-merge)). Includes materialized `native.<Code>` entries for every native concept referenced, and for every native those pinned definitions themselves reference (see [step 4](#4-expand-native-concepts)). |
| `pipes` | map of qualified pipe ref → pipe object | Yes | Every pipe in the closure, keyed by its crate key: the fully-qualified `pipe_ref` (`domain_path.pipe_code`) for host entries, address-prefixed for dependency-contributed entries. |
| `domains` | map of domain code → domain object | Yes | Domain metadata (`description`, `system_prompt`, `main_pipe`) keyed by domain code for host domains, address-prefixed (`package_address::domain_path`) for dependency-contributed domains. |
| `source_map` | map of qualified ref → source path | No | Provenance: `concept_ref` or `pipe_ref` → the source file it came from, for error tracing. Excluded from the fingerprint. |
| `fingerprint` | string | Yes | Lowercase SHA-256 hex digest of the normalized content (see [Fingerprint](#fingerprint)). |

- Domain — and, for dependency-contributed entries, package identity — is encoded in the **keys**, not in a structural container: `scoring.WeightedScore`, `scoring.compute_score`, `github.com/acme/legal-tools::legal.ContractClause`. There is no per-domain or per-package nesting of concepts or pipes.
- Concept and pipe objects are the standard blueprint shapes defined by the published MTHDS schema (`mthds_schema.json`) — a normalized crate's concept and pipe objects contain no members outside that blueprint model. The schema describes an authored `.mthds` *file*, not a crate: the crate envelope above (`mthds_version`, `concepts`, `pipes`, `domains`, `source_map`, `fingerprint`) is defined by this section, and a crate document is not itself an instance of that schema.
- **Provenance is dual and both parts are non-semantic.** The top-level `source_map` is the primary trace. Additionally, a concept, pipe, or domain object MAY carry an inline `source` field (from the blueprint model). Both are provenance — an inline `source` and its `source_map` entry name the same origin file — and **both are excluded from the fingerprint** (see [Fingerprint](#fingerprint)).

## Normalization Pass

Normalization transforms an authored, multi-bundle library into the closed, canonical, explicit form. A compliant producer MUST apply every step below; a consumer MAY rely on every step having been applied.

Normalization is defined **only over a valid library** — a library that has passed validation (structural, reference, and visibility checks per [Namespace Resolution Rules](./namespace-resolution.md#validation-rule-summary)). Producing a normalized crate from an invalid library is undefined. Because the crate is emitted only downstream of a passing validation, **the artifact carries the validation verdict implicitly**: possessing a normalized crate is evidence the library was valid at the time it was produced.

### 1. Merge

All bundles in the closure are merged into a single flat namespace. Each concept and pipe is keyed by its crate key. Within a package, same-domain bundles merge into one namespace.

Across packages there is no such merge. MTHDS permits two packages to declare the same domain, and their concepts and pipes remain completely independent (see [Namespace Resolution: Package Namespace Isolation](./namespace-resolution.md#package-namespace-isolation)) — so a bare `domain_path.Code` key is not a global identity, and two dependencies that each declare `recruitment.CandidateProfile` are two distinct definitions, not one. Package identity is therefore carried in the merged keyspace by **host-relative address keys**:

- Entries contributed by the **host package** — the package (or standalone bundle set) the closure is being resolved for — are keyed by bare fully-qualified reference: `scoring.WeightedScore`, `scoring.compute_score`.
- Entries contributed by a **dependency** (direct or transitive) are keyed by that dependency's package address, joined with `::`: `github.com/acme/legal-tools::legal.contracts.ContractClause`, `github.com/mthds/scoring-lib::scoring.compute_weighted_score`. The address is the manifest `address` of the package that declares the entry.
- The same host-relative rule applies to the `domains` map: a dependency-contributed domain is keyed `package_address::domain_path`, so two packages declaring the same domain keep distinct metadata.

The prefix is the **address, never the alias**. An alias is a key in the *consuming* package's `[dependencies]` (see [Namespace Resolution: Resolution of Package-Qualified References](./namespace-resolution.md#resolution-of-package-qualified-references)), so it is local to one consumer: two consumers of one dependency may alias it differently, and an alias-keyed crate would give semantically identical libraries different fingerprints. The address is globally unique by definition ([METHODS.toml Manifest Format](./manifest-format.md#address-format)), so address-keyed entries are collision-free across any closure — two dependencies declaring `recruitment.CandidateProfile` hold two distinct keys, one per address.

The scheme is **host-relative** — the host's own entries carry no prefix — for two reasons. A standalone bundle set has no package address (see [Manifest Format: Standalone Bundles](./manifest-format.md#standalone-bundles-no-manifest)), so a uniform prefixing scheme would have nothing to prefix host entries with. And host-relative keying leaves every crate resolved from a single-package closure — the realized case — byte-identical to what this specification always produced, preserving its [fingerprint](#fingerprint).

Domain metadata for a given domain code is merged per field with two rules: an **omitted** field defers to whichever same-domain bundle declared it (order-independent — the outcome does not depend on load order); a genuine **conflict** (two bundles declare different non-empty values for the same field) resolves to the established (first-declared) value and a warning is emitted. Duplicate crate keys contributed by a **single** package are collisions, not merges, and are rejected per [Namespace Resolution: Conflict Rules](./namespace-resolution.md#conflict-rules). The same domain and code declared by two *different* packages is not a collision — the address prefix keeps the keys distinct.

### 2. Fully Qualify Every Reference

Every reference is rewritten to its fully-qualified canonical form — **not only the map keys, but every reference in the body**:

- concept map keys and pipe map keys → `domain_path.Code`;
- each pipe's `inputs` concept references and `output` concept reference;
- each pipe step's `pipe` reference (in `PipeSequence`, `PipeParallel`, `PipeCondition` outcomes, `PipeBatch`, etc.);
- each concept's `refines` target;
- each structure field's `concept_ref` and `item_concept_ref`.

Every reference is rewritten to the **crate key** of its target, per the host-relative scheme of [Merge](#1-merge). A reference to a host-contributed definition — bare (`ContractClause`), same-domain, or domain-qualified — resolves to the bare qualified form, `domain_path.ConceptCode`. A reference to a dependency-contributed definition resolves to the address-prefixed form: the host's `alias->domain.Code` resolves through `[dependencies]` to the dependency's address and rewrites to `package_address::domain_path.Code`, and a reference *inside* a dependency's own bundles (bare, same-domain, or qualified in its source) rewrites to that same address-prefixed key — the two spellings of one target converge on one key. The `->` alias syntax does not survive normalization: an alias is a key in the *consuming* package's `[dependencies]` (see [Namespace Resolution: Resolution of Package-Qualified References](./namespace-resolution.md#resolution-of-package-qualified-references)), so it is local to one consumer and cannot serve as a canonical identity; the address can, and does. Special pipe outcomes (`fail`, `continue`) are not references and are left as-is.

After this step, no bare, same-domain-implicit, or `->`-qualified reference remains anywhere in the crate: every reference is a crate key, resolvable by direct lookup.

### 3. Flatten Refinement

Concept refinement (`refines`) over an **in-crate structured base** is flattened into effective structures. A refining concept's normalized structure is its **complete effective field set** — the fields inherited from its refinement base(s) together with its own — so a consumer never has to walk a refinement chain to know a concept's full shape. Once flattened, such a concept carries a materialized `structure` and no `refines` (the two are mutually exclusive in the concept object model); the base's provenance survives in the source map, not on the flattened concept.

A concept whose refinement chain bottoms out at a **native** is the exception: it retains its `refines: native.<Code>` link rather than inlining the native's fields. The native is materialized into the crate as its own `native.<Code>` concept by [step 4](#4-expand-native-concepts), so the base is already resolvable in-crate without chain-walking — and keeping the link (rather than flattening) is what preserves the native's identity, so a consumer projecting the concept renders it as extending the native (e.g. a `Text`-refining concept remains a text type) instead of a bare structure that has lost its native base. Sufficiency is satisfied either way: the base is present in the crate.

Flattening is also where a concept's **effective hints** are assembled. While the chain is walked, the concept's own `hints` are merged key by key with those inherited from each base, a nearer declaration winning (see [Intent Hints: Precedence and Inheritance](./intent-hints.md#precedence-and-inheritance)), and the merged table is what the normalized concept carries. This applies to every refining concept whose bases are resolvable in-crate — one flattened to a bare structure and one retaining a `refines` link alike — because the chain is walked here and nowhere later: after this step a consumer reads a concept's hints exactly as it reads its complete effective field set, without walking anything. A merge that yields nothing leaves the concept without a `hints` member.

### 4. Expand Native Concepts

References to native concepts (`Dynamic`, `Text`, `Image`, `Document`, `Html`, `TextAndImages`, `Number`, `YesNo`, `Date`, `Time`, `Page`, `JSON`, `SearchResult`, `Anything`, `Composite`) are rewritten to their canonical `native.<Code>` qualified form, and for every native concept a crate references, its definition is **materialized into `concepts`** as a `native.<Code>` entry — the same concept-object shape as any other concept. A consumer therefore needs no hardcoded native-concept table: every native a crate uses is present in the crate itself.

Materialization is a **lookup, not a computation**: each materialized entry is the [pinned normative definition](./native-concepts.md) of that native for the crate's `mthds_version`, copied verbatim. An implementation MUST NOT derive the materialized form from its own runtime types — pinning is what makes two independent implementations byte-agree on materialized natives, and therefore on the [fingerprint](#fingerprint). The `mthds_version` member records which pinned set was used, so a consumer can confirm it understands the definitions; it is a version stamp, not a lookup key the consumer must resolve externally.

The materialized set is **transitively closed**. A native's pinned definition may itself reference other natives through a structure field's `concept_ref` or `item_concept_ref`, and those natives are materialized too. A producer MUST materialize exactly the least set of natives that contains every native the library references and is closed under the references appearing in the pinned definitions themselves — no more, no less. The reference graph over the pinned set is finite and acyclic, so that closure is reached in finitely many steps and is uniquely determined by the library and the crate's `mthds_version`.

Both halves of that rule are load-bearing. Omitting a transitively-referenced native leaves a materialized concept pointing at a `native.<Code>` absent from `concepts` — a crate carrying `native.Page` without `native.TextAndImages` and `native.Image` is not closed, and [sufficiency](#sufficiency-guarantee) fails for exactly the consumer this format exists for: the one with no native table to fall back on. Materializing *beyond* the closure is equally non-conforming, because `concepts` is hashed: a producer that padded a crate with unreferenced natives would compute a different [fingerprint](#fingerprint) for the same library. Pinning fixes what each materialized entry *contains*; this rule fixes which entries are *present*. Both are required for two independent implementations to byte-agree.

### 5. Materialize Defaults and Multiplicity

Elided authoring conveniences are made explicit:

- field default values become explicit on each structure field;
- multiplicity — list markers (`Concept[]`) and presence markers (optional `?`, required `!`) — becomes explicit on each field and on each pipe input/output, rather than implied by shorthand. A fixed count of exactly one materializes as **single**, per the language's [`[1]`-is-single rule](./mthds-format.md#concept-references-in-inputs-and-output), so a materialized fixed count is always greater than one;
- empty `hints` tables are removed, absent hints are an absent member (never `null`, never an empty table), and a hint-free input slot normalizes exactly as the string form does, whichever form authored it — so a slot, field, or concept carrying no hints normalizes exactly as it did before hints existed, and a library that authors no hints keeps its [fingerprint](#fingerprint). A hinted slot is carried in the expanded form, `hints` beside the slot's concept reference, its multiplicity and presence materialized exactly as a string-form slot's are; a field's or slot's `hints` are carried as authored, the site-over-concept merge being the consumer's (see [Intent Hints: Hints in the Library Crate](./intent-hints.md#hints-in-the-library-crate)). (A concept's effective hints are assembled earlier, in [step 3](#3-flatten-refinement), where the refinement chain is walked.)

### 6. Promote String-Described Concepts

A concept written in string-shorthand form (`Foo = "a short description"`) is promoted to the explicit concept object with that string as its `description` and no `structure` or `refines`. The promoted concept is **structureless**; a consumer treats an absent structure as declared imprecision to surface (see [Sufficiency](#sufficiency-guarantee)), never as a shape to invent.

## Fingerprint

Every normalized library crate carries a deterministic `fingerprint`: the lowercase SHA-256 hex digest of its normalized content. Because the digest is computed over normalized *meaning* rather than authored bytes, reformatting or commenting a `.mthds` file never changes the fingerprint, while changing a method's effective type surface, prompt, or entry point always does. The fingerprint is the crate's semantic identity: two crates with the same fingerprint are semantically identical.

The host-relative keyspace keeps the fingerprint canonical in both directions. A crate resolved from a single-package closure carries only bare keys — exactly the keys this specification always produced — so realized single-package fingerprints are unchanged by the multi-package extension. A multi-package crate hashes address-prefixed keys for its dependency-contributed entries, so two consumers that alias one dependency differently still produce byte-identical crates, and identical fingerprints, for identical resolved content.

### Scope

The fingerprint is computed over exactly three members: `concepts`, `pipes`, and `domains`.

- Each domain contributes its `code`, `description`, `system_prompt`, and `main_pipe`. `system_prompt` and `main_pipe` affect execution semantics and the default runnable entry point; `description` surfaces in generated documentation — all three are meaning.
- The top-level `source_map`, any per-object `source`, and the `mthds_version` stamp are **excluded**: the first two are provenance (file locations) that would make the fingerprint unstable under relocation, and the version's semantic effect is already captured in the materialized native definitions inside `concepts` (a version that changes a native's shape changes that hashed concept; a pure version bump that changes nothing does not change the digest).
- The `fingerprint` member itself is excluded (it cannot hash itself).

### Canonicalization

To make independent implementations byte-agree on the digest, the hashed payload MUST be canonicalized as follows:

1. Build a payload object `{ "concepts": …, "pipes": …, "domains": … }` where each member is the corresponding map with its per-object `source` removed and with every member that has no value omitted — an absent optional member is absent from the payload, never emitted as `null`, so that a producer before and after a new optional member exists still byte-agrees on unchanged content.
2. Serialize the payload as JSON per **RFC 8785 (JSON Canonicalization Scheme, JCS)**, which fully fixes the byte form: keys sorted lexicographically at every level, no whitespace between tokens (a `,` and `:` with no surrounding space), minimal string escaping with non-ASCII emitted as literal UTF-8, and numbers in the JCS canonical number form. Deferring to JCS verbatim is what guarantees two independent producers emit byte-identical output for identical content.
3. Encode the serialized string as UTF-8 and compute its SHA-256 digest.
4. Format the digest as a 64-character lowercase hexadecimal string.

Map entries MUST be sorted by key (qualified ref / domain code) before serialization, and every nested object's keys MUST be sorted, so the digest is independent of authoring order and load order.

## Encodings

The normalized library crate has two canonical encodings of the same blueprint model. Both MUST round-trip to an identical logical crate and MUST yield the same `fingerprint`.

### JSON

The machine-native encoding. A crate serialized as JSON is a single object with the members defined in [Crate Structure](#crate-structure); its concept and pipe objects follow the blueprint shapes of the published MTHDS schema (`mthds_schema.json`), while the crate envelope itself is defined by this document rather than by that schema. JSON is the encoding third-party generators consume as emitter input.

### TOML

The human-diffable encoding, meant to be committed so that a semantic diff of two crates reads cleanly. A crate serialized as TOML is a valid TOML document that a validator or runner can load directly as a bundle set — a normalized crate is a distinct document shape from an authored bundle (one flat, fully-qualified, multi-domain document versus one `domain`-headed file per bundle), so "loadable as a bundle set" requires the loader to accept the crate's flat qualified keyspace; that loader accommodation is part of realizing this encoding, not an authored-bundle equivalence.

Because crate keys are dotted qualified refs (`scoring.WeightedScore`) — and, for dependency-contributed entries, contain `/` and `::` as well (`github.com/acme/legal-tools::legal.ContractClause`) — each key **MUST be quoted** as a single TOML key (`["concepts"."scoring.WeightedScore"]`, `["concepts"."github.com/acme/legal-tools::legal.ContractClause"]`), never written as an unquoted dotted path (which TOML would parse as nested tables) — the same rule [methods.lock Format](./lock-format.md#structure) applies to its dotted package-address keys.

### Canonical Serialization

For a given encoding, a compliant producer MUST emit crates deterministically so that version control diffs are minimal and independent implementations agree byte-for-byte:

- map entries (`concepts`, `pipes`, `domains`, `source_map`) sorted by key;
- object members emitted in a fixed, schema-defined order;
- dotted qualified refs quoted as single keys (see [TOML](#toml) above);
- no encoding-specific ambiguity (e.g. consistent string quoting, no trailing insignificant whitespace).

The `fingerprint` is a property of the *logical* crate (computed via the JSON canonicalization above), not of a particular encoding's bytes, so both encodings of one crate carry the same fingerprint.

## Sufficiency Guarantee

The defining property of the normalized library crate is **sufficiency**, stated here as a testable contract:

> Given only a JSON or TOML parser and a single normalized library crate — with **no** MTHDS loader, **no** namespace resolver, and **no** hardcoded table of native concepts — a consumer can, for any concept in the crate's concept set, emit a correct type; for any pipe, render a correct input form and register a correct tool.

This holds because normalization has already done every job that would otherwise require a frontend: references are fully qualified (no resolver needed), structured refinement is flattened and native-backed refinement resolves via the crate's own materialized `native.<Code>` entry — a single guaranteed in-crate lookup, never a multi-hop chain to walk, natives are expanded to a transitively closed set and version-pinned (no native table needed, and no materialized native points outside the crate), defaults and multiplicity are explicit (no shorthand to interpret), and string-described concepts are promoted (no dual concept representation to handle). Where the source is genuinely imprecise — a concept with no structure, a list with no item type, a dict whose `value_type` is the reserved `"Any"` marker — the crate preserves that imprecision explicitly, so a consumer can *surface* it (a caveat, a TODO) rather than guess a shape.

Sufficiency is the same property that makes a crate portable to a remote worker with no access to the original files, and portable to a third-party code generator with no MTHDS frontend. They are one requirement, met once.

The two halves of that promise have standard-owned artifacts of their own, so a consumer need not re-derive them: [Pipe I/O Contracts](./pipe-io-contracts.md) states, per pipe, the concept, presence, multiplicity and JSON Schema of every input and the concept and multiplicity of the output — what "register a correct tool" needs; and the [Input-Form Descriptor](./input-form-descriptor.md) states the ordered, kind-discriminated presentation view of the same inputs — what "render a correct input form" needs. Both are projections of a resolved library and are derivable from a crate with a JSON parser and nothing else, which is sufficiency demonstrated rather than asserted. The one place a normalized crate is a lossy input is the descriptor's `refines` chain, which needs the refinement links [step 3](#3-flatten-refinement) deliberately flattens; the descriptor page states what a crate-only producer reports there.

## Relationship to Other Formats

- [.mthds File Format](./mthds-format.md) defines the bundle — the authored unit a crate is assembled from.
- [METHODS.toml Manifest Format](./manifest-format.md) resolves *which files* form a package; the crate captures *what they mean* once resolved.
- [methods.lock Format](./lock-format.md) pins *which versions* of remote dependencies a package resolves to; it is an input to closure assembly, not part of the crate.
- [Namespace Resolution Rules](./namespace-resolution.md) define the reference-resolution semantics the normalization pass applies.
- [Package Loading](../implementers/package-loading.md) details the dependency resolution and library assembly the closure is built by.
- [Distribution](../packages/distribution.md) specifies how dependency sources are fetched, cached, and installed before closure assembly reads them.
- [Pipe I/O Contracts](./pipe-io-contracts.md) and the [Input-Form Descriptor](./input-form-descriptor.md) are the two standard-owned projections of a resolved library — the machine contract and the presentation view of a pipe's inputs.
