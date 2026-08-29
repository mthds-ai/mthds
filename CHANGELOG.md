# Changelog

## [Unreleased]

### Changed

- **The package system is rewritten to the decided design.** The packaging corpus — manifest, lock, resolution, crate, distribution, and registry pages — now describes one coherent, committed system instead of a mix of live rules, withdrawn plans, and speculative ambition.
- **`[dependencies]` is committed design (manifest spec, dependencies pages, guides):** The "not yet implemented / removed from the standard" banners are gone. Dependency declaration — aliases, addresses, version constraints, `path` overrides — is specified as the contract implementations are brought into conformance with, under the same forward-contract convention the library crate spec already uses, with honest status notes where implementation has not landed.
- **Version resolution commits to Minimum Version Selection, with constraints read as floors:** A compliant implementation MUST use MVS; a declared constraint states the minimum a dependent is known to work with, and a newly published version is never adopted until some manifest raises a floor to it. The `update`-vs-MVS contradiction is resolved: `update` raises the floors in `METHODS.toml` to latest and re-locks (re-resolution alone never moves a version), and `add` records the added dependency's latest version as the floor.
- **`methods.lock` becomes a verification record with semantic identity (breaking):** Each entry now pins `version`, the byte `hash` (unchanged algorithm), a new `fingerprint` (the library-crate semantic fingerprint of the dependency's resolved content), the `source` clone URL (now consistently carrying its `.git` suffix), and the resolved `commit` SHA. The spec states the derivable-lock semantics — under MVS the lock is regenerable from manifests plus fetched sources, the `go.sum` relationship — and keeps install-time byte-hash verification as a hard failure.
- **The library crate specifies its multi-package keyspace — host-relative `::` address keys:** Host-package entries keep bare qualified keys; dependency-contributed entries are keyed by package address (`github.com/acme/legal-tools::legal.ContractClause`), for concepts, pipes, and domains alike. Cross-package `alias->` references rewrite to the address-qualified key, so consumer-local aliases never leak into the canonical form. Every already-realized single-package crate fingerprint is preserved by construction; the fold-in pass that applies the keyspace remains forward contract.
- **`name` is required and the directory-match rule is deleted (breaking):** Every package states its snake_case `name`; the manifest is the identity, the directory name carries no meaning, and cache layout is a tool concern. `name` also participates in locating a package inside a library repository.
- **`main_pipe` is auto-exported — the MUST-be-listed clause is deleted:** The single rule everywhere is that a `main_pipe` (manifest or bundle header) is exported by virtue of being `main_pipe`, in addition to `[exports]`.
- **Cross-package visibility is a validation-time diagnosis:** A reference to a dependency's non-exported pipe is a validation error naming the dependency's export surface — never a silent load-time omission. The implementers' checking algorithm and both validation checklists now state it.
- **Distribution specifies the versioned reference and package location:** The reference grammar is `<address>[@<tag>]` — bare address means the default branch HEAD, `@vX.Y.Z` the repository at that tag; the clone URL derives from the hostname plus the first two path segments; a package inside a clone is located by manifest identity (`address`, or `address + "/" + name` in a library repository), never by directory path, with a loud error listing candidates on a miss. The two caches and their bridge are specified: install populates the project-local method cache from the global `~/.mthds/packages/{address}/{version}/` cache, lock-pinned and hash-verified. A note records that what a runtime executes from fetched content is runtime policy it may restrict loudly.
- **The registry spec is re-scoped to the honest surface:** Index, package pages, text search, validation badges tied to a validated version, and freshness signals — with the index schema gaining `name`, `display_name`, and `main_pipe` — and a stated design guarantee that the registry is off the install path. The indexing page distinguishes crawl-at-latest-stable from resolution's minimum selection, and flags (without deciding) the open edge between the indexer's historic all-public default and the manifest's pipes-private default.
- **Drift sweep across the corpus:** Every manifest example now carries the required `name`; the create-package guide embraces kebab-case directories; the overlapping package-validation checklists in the namespace spec and the implementers' reference now agree; "three-tier" refers only to the reference syntax; the CLI reference's package group is `mthds package`, documenting the live manifest commands and the committed dependency lifecycle instead of the retired `mthds pkg` group; the discover-methods guide describes registry-based discovery; the roadmap names the actually-open items (`[dependencies]` implementation, crate fold-in); the manifest spec's meta description no longer advertises model configuration it never contained; and the "what is MTHDS" pitch states the package system's status honestly.

### Added

- **Future Directions** (`packages/future-directions.md`): New page preserving the package ecosystem's ambitions — typed signature search, the Know-How Graph's query surface, Ed25519-signed manifests with a trust store, and registry proxy/mirror chains — explicitly as non-normative directions, each compatible with the registry-off-the-install-path invariant.

### Removed

- **`packages/registry-search.md` and `packages/registry-distribution.md`:** Their honest content (text search, package signals) moved into the registry overview; the speculative content (typed search semantics, graph queries, signed manifests, proxy chains) moved to the Future Directions page.

## [v0.9.0] - 2026-08-26

### Added

- **Pipe I/O Contracts** (`spec/pipe-io-contracts.md`): New specification for the per-pipe map of declared input and output slots, stating each slot's concept reference, presence, multiplicity, and JSON schema. A plural slot's schema is an array wrapper carrying `minItems`/`maxItems` exactly on the fixed arm, so a stock validator enforces a declared count; concept identity is read from `concept_ref`, never sniffed out of the schema.
- **Input-Form Descriptor** (`spec/input-form-descriptor.md`): New specification for the ordered presentation view of a method's inputs — the artifact a renderer turns into a fill-in form with no schema heuristics, no hardcoded native table, and no description matching. Field kinds are assigned by ordered tables rather than inference, with a mandatory `unknown` escape hatch, and `gating` is kept deliberately distinct from `required`.
- **Intent Hints** (`spec/intent-hints.md`): New specification for an optional, non-normative presentation intent layer. A `hints` table attaches to a concept, a structure field, or a pipe input slot, with one defined key `intent` over a closed vocabulary (`prose`, `label`, `rating`, `quantity`). Execution and validation never read hints, and consumers that ignore them stay correct.
- **Library Crate Format** (`spec/library-crate.md`): New specification for the flat, fully-qualified, self-contained, fingerprinted snapshot a library resolves into — closure assembly, the normalization pass, the semantic-hash fingerprint, both encodings, and the sufficiency guarantee.
- **Native Concept Definitions** (`spec/native-concepts.md`): New specification pinning the normative blueprint form of every native concept per standard version. Implementations MUST materialize natives by lookup into the pinned set, never by reflection over their own runtime types — which is what makes crate fingerprints byte-agree across implementations.
- **Optionality** (`language/optionality.md`): Documented first-class presence markers for pipe inputs and outputs (`?` optional, `!` forced), recorded absences, liftable pipes, guarded template requirements, and the matching diagnostics.
- **Native concepts `YesNo`, `Date`, `Time` and `Composite`:** All four now appear in the documented native set. `Time` (a time of day, optionally with a UTC offset) is new to the standard and joins the reserved native codes — **breaking** for a bundle that declared its own `Time`. The other three already existed and gained the documentation they were missing.
- **Field types `datetime` and `time`:** The concept structure language gains `datetime` (a point in time, already accepted by the reference implementation but absent from the field-type table) and `time` (a time of day), completing the temporal triple alongside `date`.
- **Expanded input slot form:** An input slot may now be written as a table, `name = { concept = "Ref", hints = { ... } }`, to carry intent hints and future per-slot authoring fields. The string form is unchanged and exactly equivalent to a `concept`-only table.
- **Contract-only pipe signatures:** A `[pipe.*]` section may declare inputs and outputs with no implementation by omitting `type`.

### Changed

- **`native.Image`, `native.Date`, `native.Html` (breaking):** `Image` flattens its nested size object into paired optional `width`/`height` integers; `Date` declares real structure (`date` required, `time` optional) instead of being structureless; `Html` makes `css_class` optional, leaving `inner_html` as its only required field — the requirement was a modeling accident that forced every generating pipe to invent a class name for content needing no wrapper.
- **PipeParallel output model:** Branch results are now always combined into the pipe's declared `output`, which must be `Composite` or a structured concept whose fields match the branch `result` names. `combined_output` is removed; `add_each_output` only exposes branch outputs individually.
- **`Concept[1]` is a single value:** The multiplicity suffix table read `[N]` as a fixed-length list for N ≥ 1, making `Concept[1]` a one-item list on paper while every artifact reporting multiplicity treats it as a plain single value. `[N]` is now a list for N ≥ 2, `[1]` is a way of writing `Concept`, and `[0]` is invalid — so a fixed count on any wire is always greater than one.
- **Structure-field validation:** A field blueprint's keys are a closed set, so a hopeful key (`minimum`, `examples`, `unit`, …) is rejected rather than validating green and being silently dropped. A field MUST NOT declare both `required = true` and `default_value` — two contradictory instructions on one field. The long-accepted bare-string field form (`summary = "A one-line summary"`) is now documented.
- **Library crate normalization:** Native materialization is transitively closed — a crate carries exactly the least native set covering every native the library references and the references inside the pinned definitions themselves, since both a missing and a padded entry are wrong for a hashed member. Corrected the merged-keyspace and schema-scope claims: two packages may declare the same domain, so a bare `domain_path.Code` key is not a global identity, and a crate document is not an instance of `mthds_schema.json`.
- **HTTP runner protocol:** The validate response's `is_valid: true` arm SHOULD carry `pipe_io_contracts` and `input_form`. Base fields are unchanged and a conformant runner may omit both; what is fixed is that a runner reporting them reports those shapes under those names.
- **Bundled MTHDS schema:** Updated the committed `mthds_schema.json` to pipelex `v0.41.0` — `PipeSignatureBlueprint`, image-size additions, removal of `PipeParallelBlueprint.combined_output`, and the `datetime` and `time` field types. That last pair is the user-visible half: a `.mthds` declaring either was valid at runtime but rejected by this copy.
- **Bare pipe references (clarification):** Namespace Resolution now explains why no-fall-through is load-bearing — bare references are exempt from the export visibility check precisely because they cannot leave their own domain, so a resolver falling through to other domains would make `[exports]` unenforceable. The rule itself is unchanged.

### Removed

- **`type = "PipeSignature"`:** No longer author-facing syntax. A contract-only signature omits `type` instead.

## [v0.8.0] - 2026-06-22

### Removed

- **Native concept `ImgGenPrompt` (breaking):** Dropped `ImgGenPrompt` from the built-in native concepts. It was structurally identical to `Text` — a built-in concept with no distinct content payload — and `PipeImgGen` never depended on it. **Migration:** replace `ImgGenPrompt` (or `refines = "ImgGenPrompt"`) with `Text` in any `.mthds` bundle.

### Changed

- **PipeImgGen documentation:** Clarified the input model across the language reference and the normative spec. `PipeImgGen` carries a required `prompt` string template (plus an optional `negative_prompt`) and injects its declared `inputs` into that template — `Text` inputs via `$variable`/Jinja2 interpolation, and `Image` inputs (single or list) as reference images rendered to `[Image N]` tokens for image-to-image and editing workflows — rather than consuming a dedicated prompt concept. Added reference-image examples. The `negative_prompt` is a full template like `prompt`: its variables are subject to the same validation (every referenced variable must be a declared input) and the same `$`/`@` shorthand preprocessing.

### Fixed

- **Native-concept lists:** Completed and aligned the inline native-concept lists in the validation rules, namespace resolution, and registry indexing references — they were missing `SearchResult`. All native-concept lists across the docs now share one canonical order (`Dynamic`, `Text`, `Image`, `Document`, `Html`, `TextAndImages`, `Number`, `YesNo`, `Date`, `Page`, `JSON`, `SearchResult`, `Anything`, `Composite`).

## [v0.7.0] - 2026-06-17

### Added

- **Docs analytics:** Add Vercel Web Analytics to the documentation site — a deferred `/_vercel/insights/script.js` snippet that is suppressed on the 404 page (like the existing PostHog snippet) and 404s harmlessly under local `mkdocs serve`.
- **OpenAPI schemas:** Add `ValidationResult`, `InvalidValidationReport`, and `ValidationError` schemas to the normative OpenAPI document to model the new `/validate` diagnostic response.

### Changed

- **Protocol version:** Bump the MTHDS Protocol OpenAPI document version from `0.1.0` to `0.6.0`.
- **`/validate` endpoint:** Redesign as a pure diagnostic endpoint that always returns `200 OK` for a successfully evaluated bundle, whether valid or invalid. The response is a discriminated union (`ValidationResult`) keyed on a mandatory `is_valid` boolean:
    - `is_valid: true` — requires runnability facts (`is_runnable` and `pending_signatures`); implementations may append custom artifacts (e.g. `pipe_io_contracts` in the Pipelex reference implementation).
    - `is_valid: false` — carries `is_runnable: false` and a non-empty `validation_errors` array of structured diagnostics (each with at least a `category` and a `message`).
- **422 semantics:** On `/validate`, a `422 Unprocessable Entity` now strictly indicates a request-shape problem (e.g. malformed JSON) or transport failure — never an invalid bundle. `/execute` and `/start` still return 422 for a bad bundle.
- **Documentation:** Update `protocol.md` and `runtime.md` to explain the new `/validate` behavior and distinguish validation failures from runnability facts; update `CLAUDE.md` to reflect the analytics setup.

## [v0.6.0] - 2026-06-11

- Add the **MTHDS Protocol** — the minimal HTTP contract every MTHDS runner implements: `POST /execute`, `POST /start`, `POST /validate`, `GET /models`, `GET /version`. Normative OpenAPI document at `docs/spec/openapi/mthds-protocol.openapi.yaml` (v0.1.0), prose specification page at `docs/spec/protocol.md`. Paths are version-agnostic (the version segment belongs to the server base URL); errors are RFC 7807 problems; `/start` takes the same `RunRequest` body as `/execute`; `/execute` 200 answers with `RunResultExecute` (`pipeline_run_id` + `pipe_output`, both required — a completed run has output); `/start` 202 (and the optional `/execute` 202 degrade) answers with `RunResultStart` (`pipeline_run_id` only). No run store in the protocol; completion delivery is implementation-defined. The protocol defines base request/response fields only — anything an implementation adds or returns on top (a client-supplied run identifier, run states, timestamps) is an extension.
- The protocol page embeds a rendered route reference — every protocol route with its parameters, request bodies, and response schemas, generated at build time from the normative OpenAPI document via the `neoteroi.mkdocsoad` plugin.
- Add "Exposing a Runner over HTTP" section to the implementers runtime guide.
- Add `make spec-check` (OpenAPI validation, wired into `docs-check`).

## [v0.5.0] - 2026-05-12

- Add `PipeStructure` operator: turns `Text` (or a concept refining `Text`) into a structured concept — typically via an LLM call. Accepts a single input and an optional `model` reference; supports multiplicity on the output.
- Clarify `structuring_method = "preliminary_text"` on `PipeLLM` as a runtime directive — the standard does not prescribe HOW a runtime implements it. The reference runtime expands the pipe at load time into a `PipeSequence` of `PipeLLM` (producing `Text`) and `PipeStructure` (producing the declared output).
- Document `PipeStructure` across the language reference, normative spec, validation rules, runtime guide, model references, and JSON schema pages.
- Document `render_js` and `include_raw_html` on `PipeExtract` (boolean optional flags for web-page extraction: JS rendering and raw-HTML inclusion).
- Document `xhigh` value on `LLMSetting.reasoning_effort` (sits between `high` and `max`, maps to provider-specific xhigh values where supported).

## [v0.4.1] - 2026-03-30

- Fix README links to point to versioned `/latest/` docs URLs
- Update agent skills reference to agent plugins with correct repo URL
- Change `plxt` install instruction from `pip` to `uv tool install`

## [v0.4.0] - 2026-03-29

- Expand Document concept and PipeExtract operator to support web page URLs alongside file paths
- Add PipeExtract web page extraction example
- Define SearchResult sources: a list of source citations, each a Document with `title`, `url`, and `snippet`
- Add `title` and `snippet` fields to Document native concept docs
- Migrate docs deployment from GitHub Pages to Vercel with versioned routing and redirects
- Add `/know-how-graph/` redirect to `/latest/`
- Inject `<base>` tags for versioned directory roots to fix asset loading
- Add docs version pruning script for cleaning up old deployed versions
- Add Lighthouse performance baseline and comparison scripts

## [v0.3.8] - 2026-03-19

- Enrich root index.html with real content for AI agents and scrapers (browsers still redirect instantly)
- Copy llms.txt and llms-full.txt to domain root for AI agent discovery
- Add llms.txt paths to robots.txt allowlist

## [v0.3.7] - 2026-03-17

- Refine robots.txt to block specific paths (/0., /pre-release/, /404.html) instead of broad disallow
- Add multi-size favicon support (32, 128, 180, 192px) with Apple Touch Icon and Android/PWA sizes
- Support multi-version deletion in docs-delete make target

## [v0.3.6] - 2026-03-17

- Add visible H1 heading and emphasize key terms on index page
- Add Pipelex reference runtime line to site footer

## [v0.3.5] - 2026-03-16

- Fix sitemap.xml double-path bug (`/latest/latest/page/`) by setting `site_url` to bare domain
- Add root-level `sitemap.xml` generation for Google crawling (rewritten from versioned copy)
- Fix `robots.txt` to allow `/sitemap.xml` and point `Sitemap:` to root copy
- Override `site_meta` block in `main.html` to hardcode `/latest/` canonical URLs
- Suppress OG tags, JSON-LD, and analytics on 404 page

## [v0.3.4] - 2026-03-15

- Fix sitemap URLs to include `/latest/` prefix (was generating broken URLs without version path)
- Add conditional `og:type` (website on homepage, article on all other pages), `og:site_name`, and `og:locale` meta tags
- Restructure JSON-LD: WebSite schema on homepage only, TechArticle on article pages only
- Replace indexable `404.md` page with proper MkDocs 404 override (`noindex`, canonical, visible content)
- Style root 404 fallback with grayscale palette and dark mode support
- Improve on-site search tokenization for hyphenated and dotted identifiers

## [v0.3.3] - 2026-03-13

- Improve root redirect page styling for better appearance during redirect
- Add runtime requirement note to first-method getting-started guide

## [v0.3.2] - 2026-03-13

- Document PipeCompose template mode: shorthand syntax (`$`, `@`, `@?`), template categories, available filters, and template context
- Add `@?` conditional insertion pattern to PipeLLM prompt syntax reference
- Add normative shorthand expansion rules to the specification
- Add preprocessor guidance and filter-per-category table to implementers runtime docs

## [v0.3.1] - 2026-03-09

- Expand language docs: file naming conventions, bundle-level system prompt, refinement vs. new concept guidance, and structuring_method details
- Fix docs quality issues: nb_output example, cross-references, concept headers, and item_type

## [v0.3.0] - 2026-03-04

- Add OpenGraph and Twitter Card meta tags to mike redirect template for social link previews
- Add mike plugin configuration with custom redirect template

## [v0.2.1] - 2026-03-03

- Add PipeSearch operator to JSON Schema

## [v0.2.0] - 2026-03-03

- Add documentation for PipeSearch operator

## [v0.1.4] - 2026-03-02

### Changed

- **Method names: strict snake_case** — the `name` field specification updated from kebab-case to snake_case (pattern `[a-z][a-z0-9_]*`). Directory name must match the `name` field exactly — no conversion needed.
- Updated CLI I/O contract examples to use snake_case method names.

## [v0.1.3] - 2026-02-26

- Add PostHog analytics to docs site
- Add Hub link to navigation

## [v0.1.2] - 2026-02-26

- Update homepage with overview content

## [v0.1.1] - 2026-02-25

- Change favicon and logo

## [v0.1.0] - 2026-02-22

- Add hosted JSON Schema and document inline model settings and enum values
- Add update-schema make target to download latest JSON Schema from S3

## [v0.0.4] - 2026-02-20

- Added github release workflow
- Fix deploy doc workflow

## [v0.0.3] - 2026-02-20

- Renamed Home section first page to Overview
- Quieted check-uv and env targets for operational commands
- Refined project description
- Added /release skill and gitignore .skill artifacts

## [v0.0.2] - 2026-02-19

- Polished documentation

## [v0.0.1] - 2026-02-10

- Initial release
