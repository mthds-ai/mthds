# Changelog

## [Unreleased]

### Changed

- **Updated the bundled MTHDS JSON Schema to pipelex v0.41.0.** The schema is generated from the pipelex blueprint models and gitignored there, so drift never shows up in a PR — this copy had fallen behind. Concept structure field types gain `datetime` and `time`: a `.mthds` declaring either was **valid at runtime but rejected by this copy**, which is the user-visible half of the drift. Copied from the released `pipelex` v0.41.0 tree rather than fetched via `make update-schema`, because the release chain it pulls from (S3 `mthds_schema_latest.json` → `mthds.ai`) is still serving **v0.27.0** — the refresh target would have pulled a schema fourteen releases older than what was already committed here. Republishing that object is a separate manual, outward-facing step and is not done here.

### Added

- **Native Concept Definitions (breaking):** New specification (`spec/native-concepts.md`) pinning the normative blueprint form of every native concept per standard version — fields, types, and descriptions are now standard-owned and version-pinned. Implementations MUST materialize natives by lookup into the pinned set, never by reflection over their own runtime types; this is what makes library-crate fingerprints byte-agree across implementations. Breaking definition changes carried by the pinned set: `native.Image` flattens its nested size object into paired optional `width`/`height` integer fields, and `native.Date` declares real structure (`date` required, `time` optional) instead of being structureless.
- **Native concept `Time`:** A time of day, optionally with a UTC offset (`native.Time`). `Time` joins the reserved native concept codes — a bundle can no longer declare its own `Time` concept (breaking for bundles that did).
- **Field types `datetime` and `time`:** The concept structure language gains a documented `datetime` field type (a point in time — already accepted by the reference implementation but missing from the field-type table) and a new `time` field type (a time of day, optionally with a UTC offset), completing the temporal triple alongside `date`. Both `time` and `native.Time` ship in the reference implementation in lockstep with this spec change.
- **Library Crate Format:** New specification (`spec/library-crate.md`) for the normalized library crate — the flat, fully-qualified, self-contained, fingerprinted snapshot a library resolves into. Covers the three units (bundle / library / pipe) and the resolution rule, closure assembly from working bundles plus the local method cache, the normalization pass (merge, fully qualify every reference, flatten refinement, expand and version-pin natives, materialize defaults and multiplicity, promote string-described concepts, built only from a valid library), the semantic-hash fingerprint definition, the JSON and TOML encodings, and the sufficiency guarantee.
- **Optionality in the language:** Documented first-class `?` / `!` presence markers, recorded absences, liftable pipes, guarded template requirements, and optionality validation diagnostics.
- **Native concepts `YesNo` and `Date`:** Documented first-class yes/no and date outputs, including their content fields and native concept references.

### Changed

- **Library crate native materialization:** Normalization step 4 is re-pointed from implementation-derived structural definitions to a verbatim copy of the pinned Native Concept Definitions for the crate's `mthds_version` — materialization is a lookup, not a computation. The specification-status callout now reflects the reference implementation's current conformance (steps 1–4 and 6, both encodings, full-scope fingerprint), leaving defaults/multiplicity materialization and cross-package fold-in as the remaining forward contract.
- **PipeSignature authoring:** Contract-only pipe signatures now omit `type`; `type = "PipeSignature"` is no longer author-facing syntax.
- **PipeParallel output model:** `PipeParallel` now always combines branch results into its declared `output`, which must be `Composite` or a structured concept matching branch `result` names. The old `combined_output` field is removed; `add_each_output` only exposes branch outputs individually.
- **Bundled MTHDS schema:** Updated the committed schema to pipelex `v0.38.0`, including `PipeSignatureBlueprint`, `PipeType`, image-size schema additions, nullable `ImgGenSetting.is_moderated`, required concrete pipe type tags, and removal of `PipeParallelBlueprint.combined_output`.

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
