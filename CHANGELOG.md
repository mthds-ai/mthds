# Changelog

## [Unreleased]

**Next release: v8.0.1 · MTHDS standard 8.0.1 · MTHDS Protocol 2.0.1**

### Changed

- **A files map's collision and entry checks read only the keys it has not refused** (`spec/method-tree.md`, `spec/protocol.md`, `spec/openapi/mthds-protocol.openapi.yaml`, `spec/openapi/mthds-error-registry.yaml`, `implementers/validation-rules.md`): the File Entry section, the protocol's method files section, its OpenAPI document and the core registry's `request.blobs_missing` entry now say that the collision check reads only the keys that are tree paths the membership rule could admit, reading a key given twice once, and that the entry checks, an entry's form, its validity within that form and whether the receiver holds the bytes a hash entry names, read the entries of those keys alone, the bytes being checked last, so `request.blobs_missing` answers only a map that breaks no other rule. A key refused as not a tree path, or as a name the membership rule could never admit, therefore collides with nothing and never has its entry checked, so a map holding `inputs.json` beside `Inputs.json`, or holding `inputs.json` with a malformed entry or a hash entry the runner lacks, is refused naming `inputs.json` for its name alone, never as a collision, for its entry or with `request.blobs_missing`, and a sender never uploads blobs for a map that would be refused anyway, while which maps are accepted and which are refused is unchanged. This clarification moves the protocol to `2.0.1`.
- **The site's development Python is pinned in `.python-version`** (`.python-version`, `make install`, the documentation workflows): the repository names the interpreter it builds the site on, `3.13`, in a `.python-version` at its root, which the Makefile and the documentation workflows read instead of each naming a version, so the next `make install` moves an environment built on another Python to the pin, and `PYTHON_VERSION=<version> make install` builds it on another one.
- **Problem titles in plain words** (`spec/error-registry.md`, `spec/openapi/mthds-error-registry.yaml`, `spec/protocol.md`): the core registry now says who a title is written for, any reader of the code, someone following a run of a method they did not write included, and the titles and `other` steps of the codes a run can raise say what happened in plain words rather than in the language's terms, so `pipe.output_invalid` is titled "A step's result does not have the structure the method declares" where it read "A pipe's output does not fit its concept". The codes of the `method` family that describe a fault in the method as written keep naming the language's constructs, and no code, domain, retry verdict, step kind or parameter changes.

## [v8.0.0] - 2026-10-18

**MTHDS standard 8.0.0 · MTHDS Protocol 2.0.0**

### Highlights

**Every error is a problem document a program can act on.** A runner answers every error, and a CLI writes every failure, as an RFC 9457 problem document carrying a registry `code`, the `domain` of who must act, a `retry` verdict and a `next_step`, so a client branches on `code` rather than on a status or a message, and the protocol moves to `2.0.0`. **The core error registry is part of the standard.** It declares every core code with its meaning, parameters and steps, is published as a JSON snapshot with each release, and gives each code a page at `https://mthds.ai/errors/<code>`. **A lost answer can be recovered.** A runner that keeps a run store serves reads of a run's status and results and honours an `Idempotency-Key`, so a client repeats a request instead of starting a second run.

### Added

- **Suggested fixes** (`spec/protocol.md`, `spec/openapi/mthds-protocol.openapi.yaml`): an error item may carry `suggested_fix`, a semantic patch over a bundle rather than a text diff: a `fix_code`, a `description`, a `safety` of `safe` or `unsafe`, an optional `file`, and a list of `ops` discriminated on `kind` (`set_key`, `ensure_table`, `delete_key`, `delete_table`, `rename_table_key`, `move_key`, `remap_value`), each addressing a table by its TOML key path. A deletion, a rename, a move or a remap whose target is absent is skipped, while `ensure_table` creates its absent table and `set_key` its absent key, each skipped when the table that would hold its target is absent, so a fix that needs a missing table puts an `ensure_table` before it. An operation that would overwrite a key or a table other than its own target, such as a rename or a move onto a key its destination table already holds, is a conflict that changes nothing, as is a `set_key` whose key holds a table or an `ensure_table` whose path names a value other than a table, while `set_key` replaces a scalar or array value and `remap_value` rewrites its value by design. An applier that meets an operation kind it does not know applies none of the fix, which still validates against the reader-side catch-all `UnknownFixOp`.
- **The core error registry** (`spec/error-registry.md`, `spec/openapi/mthds-error-registry.yaml`, `spec/openapi/mthds-error-registry.schema.json`, `spec/openapi/mthds-error-registry.json`, `spec/versioning.md`, `about/contributing.md`): the MTHDS core registry lists every core code, the `client.` family of failures a client detects itself and the catch-all `runtime.unexpected` among them, and declares for each its title, domain, retry verdict, HTTP status, the templates of its detail and of its two steps, its typed parameters, and what it means and what to do, while a JSON Schema refuses an entry with a member missing. Its JSON snapshot is published with every release of the standard, in the repository at the release's tag and as an asset of the release, and a consumer vendors that file. It lists the registered extension prefixes, `pipelex` among them, the contributing guide says how to register another, and a change to the registry moves the standard version.
- **A page for every error code** (`errors/`): each core code has a page at the URL its problem's `type` names, `https://mthds.ai/errors/<code>`, which resolves to the page of the current standard and says what the code means, who acts, what to do, and its steps, parameters and templates, and an index lists every code by family.
- **Run reads and idempotency keys** (`spec/protocol.md`, `spec/openapi/mthds-protocol.openapi.yaml`, `spec/versioning.md`): a runner that keeps a run store declares `run_store: true` in `GET /version`, serves `GET /runs/{pipeline_run_id}/status`, which answers a run's `status` (`pending`, `running`, `completed`, `failed`) and its problem as `error` once it has failed, and `GET /runs/{pipeline_run_id}/results`, which answers a completed run with the body `/execute` answers with and any other run with `run.not_finished`, `run.failed`, carrying the run's own problem as the new core member `run_error`, or `run.results_not_stored`, and honours an `Idempotency-Key` header on `/execute` and `/start`. The runner holds each key for at least 24 hours after the first request under it: the same request repeated under a key it holds runs at most once and is answered from the first execution, a different request under it is refused with `request.idempotency_conflict`, and one arriving while the first is still being handled with `request.idempotency_key_in_use`. A repeat on `/execute` whose run has ended, when the runner kept neither the first answer nor the run's output, is answered with `run.answer_not_kept`, and the client reads the run's status instead. So a client whose answer was lost sends the request again under its key within those 24 hours, against a runner declaring `run_store: true`, instead of starting a second run, and past them, where the protocol promises nothing about a repeat, it reads the run when it knows its `pipeline_run_id` or treats the outcome as unknown. The protocol still requires no run store.

### Changed

- **Run inputs files are out of the method tree (Breaking)** (`spec/method-tree.md`, `spec/protocol.md`, `spec/openapi/mthds-protocol.openapi.yaml`, `spec/cli-io-contract.md`): the membership rule keeps a file named `inputs.json` or `inputs.toml` out of every tree at any depth, so a run's inputs written into a method's folder never travel with the method, and a receiver refuses a map of file entries holding such a key. A method ships example inputs under any other name, and a tree that held such a file has a new digest.
- **Errors are RFC 9457 problem documents carrying the MTHDS core members (Breaking)** (`spec/protocol.md`, `spec/openapi/mthds-protocol.openapi.yaml`, `spec/versioning.md`): every error a runner answers is an RFC 9457 `application/problem+json` document, where the protocol named RFC 7807, and carries beside `type`, `title`, `status` and `detail` a registry `code`, the `domain` of who must act (`input`, `method`, `account`, `operator`, `runtime`), a `retry` verdict (`no`, `yes`, `outcome_unknown`) with an optional `retry_after`, a `next_step` whose `kind` is one of a closed list of steps and whose `detail` is a sentence, the code's typed `params`, a `location`, one item per fault in `errors`, and the `pipeline_run_id` when a run exists, while the protocol no longer declares `instance`. Core codes are bare, every other code starts with a prefix its owner registers with the standard, `type` is derived from the code (`https://mthds.ai/errors/<code>` for the core), and a reader that meets a code, a domain or a step kind it does not know falls back on the code's family, then on `runtime` and `report`. A runner now emits these members on every error and a client branches on `code`, and the protocol moves to `2.0.0`.
- **`/validate` reports its faults as problem items (Breaking)** (`spec/protocol.md`, `spec/openapi/mthds-protocol.openapi.yaml`): the invalid verdict's `validation_errors`, whose items carried a `category` and a `message`, is now `errors`, a non-empty list of problem items each carrying its own `code`, `detail`, `params` and `location` and optionally `suggestions` and `suggested_fix`, and either arm may carry `warnings` in the same item schema. The verdict is still a `200` discriminated on `is_valid`, and an unset member is left out rather than written as `null` on every arm, warnings included. A client reads `errors` and each item's `code` where it read `validation_errors` and `category`.
- **`missing_blobs` moves into `params` (Breaking)** (`spec/protocol.md`, `spec/openapi/mthds-protocol.openapi.yaml`): a `422` refusing hash entries the runner does not hold is coded `request.blobs_missing` and lists the hashes in `params.missing_blobs` rather than in a top-level `missing_blobs` member. A sender reads `params.missing_blobs`, which the OpenAPI document's `ProblemParams` types as a list of lowercase SHA-256 hashes, uploads each blob listed to a runner that keeps a blob store or sends those files inline to one that keeps none, and sends the request again.
- **The validation names are registry codes (Breaking)** (`spec/mthds-format.md`, `language/optionality.md`, `implementers/validation-rules.md`, `spec/namespace-resolution.md`): `binding_step_invalid` is now `method.binding_step_invalid`, `binding_path_unresolved` is `method.field_path_unresolved`, `invalid_input_name` is `method.identifier_invalid` and `optional_marker_invalid` is `method.optional_marker_invalid`. The optionality diagnostics `optional_not_handled`, `optional_output_required`, `optional_input_unguarded` and `optional_branch_required_field` are one code, `method.optional_unhandled`, whose `site` parameter says where the absent value escapes, and a step carrying neither `pipe` nor `from` is `method.schema_violation`.
- **A CLI's error is the protocol's problem document (Breaking)** (`spec/cli-io-contract.md`, `spec/versioning.md`): a method that fails on the command line writes on stderr the problem document of the protocol version that its release of the standard names, without its `status` member, in place of the envelope of `error: true`, `error_type`, `message`, `hint`, `error_domain` and `retryable`, so a program reads `code`, `domain`, `retry`, `next_step` and `location` where it read `error_type`, `error_domain`, `retryable` and `hint`, and never branches on the exit code. A CLI read by a person or an agent may write a rendering of the problem, such as Markdown, while every CLI that runs a method writes the JSON form under `--error-format json`. A downstream method whose declared inputs the upstream's working memory cannot satisfy fails with an `input.missing` problem naming the input, where it raised an error listing what the upstream held and what the downstream expected, and when it cannot satisfy several inputs, the problem names the first in authored input order and its `errors` lists every one in that order.
- **A failed output validation is a `pipe.output_invalid` problem (Breaking)** (`implementers/runtime.md`): a runtime whose validation of a pipe's output against its declared concept fails reports a `pipe.output_invalid` problem whose `location.pipe` is the failing pipe's code and whose `location.path` lists the pipe codes from the run's main pipe down to it, where it reported the pipe code and the step index in a form of its own.
- **Documentation versions served on mthds.ai**: this release stops serving `7.0.0`, so links into that version no longer resolve and should point at `/latest/`. The site serves `8.0.0`, which `/latest/` also serves, and `7.0.1`, and keeps both numbered directories out of search indexes, so that only `/latest/` is indexed.

## [v7.0.1] - 2026-10-16

**MTHDS standard 7.0.1 · MTHDS Protocol 1.0.0**

### Changed

- **The bundled MTHDS schema does not check every `function_name` segment yet** (`mthds_schema.json`): the published schema, generated by pipelex v0.87.0, rejects nothing this standard allows, but it still accepts a `function_name` segment that is not a Python identifier or is a Python keyword, and one that NFKC normalization would change, such as one holding the ligature `ﬁ`, all of which this standard rejects. A later release of this site publishes the schema of the pipelex release that checks them.
- **Documentation versions served on mthds.ai**: this release stops serving `6.0.0`, so links into that version no longer resolve and should point at `/latest/`. The site serves `7.0.1`, which `/latest/` also serves, and `7.0.0`, and keeps both numbered directories out of search indexes, so that only `/latest/` is indexed.

### Fixed

- **The bundled MTHDS schema describes `function_name` as an import path (Breaking)** (`mthds_schema.json`): the published schema is now the one generated by pipelex v0.87.0, which describes a `PipeFunc`'s `function_name` as the function's import path from the root of the method tree and refuses one with no dot, such as `capitalize`, or with an empty segment, so a tool validating against it now flags a name it used to accept. This closes the first part of the gap the v7.0.0 entry names. The schema also describes a PipeDocGen's `template_file` as a path relative to the bundle's file that names a file inside the method tree, written with forward slashes.

## [v7.0.0] - 2026-10-15

**MTHDS standard 7.0.0 · MTHDS Protocol 1.0.0**

### Highlights

**A method is the tree of files under its root, and it travels whole.** A new specification page defines which files belong to a method beside its bundles, among them its Python modules, templates, images and `requirements.txt`, and how they are named, referenced and digested. A `PipeFunc` now names a function of that tree by its import path, the run and validate routes carry the whole tree as `files`, sending a file the runner already holds by its hash, and the lock records each package's tree digest. Because a `function_name` with no dot, a request carrying `mthds_contents` and a lock carrying `hash` are no longer valid, the standard moves to `7.0.0`, and **the protocol moves to `1.0.0`**.

### Added

- **The method tree** (`spec/method-tree.md`): a new specification page defines a method as the tree of files under its root, so its Python modules, templates, images, `requirements.txt` and `README.md` travel with its bundles. A file belongs unless a path segment starts with a dot, it lies in a `__pycache__`, `node_modules`, Python virtual environment, nested repository (a directory below the root holding any entry named `.git`) or nested package (a directory below the root holding its own `METHODS.toml`, which travels as a tree of its own), or the tree's own `.gitignore` files or the manifest's `exclude` ignore it, and a symbolic link, like a `.gitignore` file whose bytes are not UTF-8, is an error; the page also defines tree paths, file references resolved inside the tree with `..` allowed, the tree digest with its `LC_ALL=C` and `sha256sum` reference pipeline, and the file entry that carries a file as text, as `{ "base64" }` or as `{ "sha256", "size" }`. Two tree paths whose Unicode full case foldings are equal, such as `straße.txt` and `STRASSE.txt`, never share a tree; patterns and file references are normalized to NFC before they are used, a reference resolving to the root, with or without a trailing `/`, is refused as not in the tree, and a URL in a template with a scheme, an authority or no path is not a file reference; and a map of file entries refuses a key not already in NFC, a key given twice inside an entry object, Base64 whose pad bits are not zero and a `size` written `13.0`.
- **`[package] exclude`** (`spec/manifest-format.md`): a manifest may list patterns in `.gitignore` syntax naming files to keep out of the method tree without keeping them out of git.
- **`requirements.txt`** (`spec/method-tree.md`): a method declares the third-party Python packages its functions import in a `requirements.txt` at its root, one PEP 508 requirement per line, with no URL, option or include, and a runtime that cannot satisfy it should refuse the method when it loads, naming the packages.
- **The blob routes** (`spec/protocol.md`): a runner that keeps a blob store declares `blob_store: true` in `GET /version` and serves `POST /blobs/missing`, which answers which of a sender's blobs it lacks and where to upload each, and a runner that stores the bytes itself serves `PUT /blobs/{sha256}` as that upload target, so an unchanged method is sent by hash and uploads nothing.

### Changed

- **Run and validate requests carry the method's files (Breaking)** (`spec/protocol.md`, `spec/openapi/mthds-protocol.openapi.yaml`): `POST /execute`, `POST /start` and `POST /validate` take `files`, a map from tree path to file entry holding the method's whole tree, in place of `mthds_contents`, and a request without `pipe_code` starts at the manifest's `main_pipe` or the one `main_pipe` its bundles declare rather than at the first bundle's. A hash entry the runner does not hold is a `422` whose `missing_blobs` lists the hashes; a client sends `{ "main.mthds": "<contents>" }` where it sent `["<contents>"]`, and the protocol moves to `1.0.0`.
- **`function_name` is an import path (Breaking)** (`spec/mthds-format.md`): a `PipeFunc` names its function by its Python import path from the root of the method tree, normalized to NFC and split at its last dot into a module of the tree and the function's name, so a name with no dot, which named a function registered with the runtime, is rejected, and so is a segment that NFKC normalization would change, such as one holding the ligature `ﬁ`, since Python would import another file than the tree holds. An author moves the function into a module of the method's folder and writes, for example, `function_name = "funcs.text_utils.capitalize"`.
- **The root of a `.mthds` file named alone (Breaking)** (`spec/method-tree.md`, `spec/manifest-format.md`): a bundle or a directory handed over is rooted at the nearest directory holding `METHODS.toml`, found by Manifest Discovery, which now stops at an entry named `.git` of any kind, a submodule's or a worktree's file and a symbolic link included; with none, a directory is its own root and a bundle named alone is a tree of that one file, so a file reference from it to a file beside it is refused. An author runs the method's directory instead, or adds a `METHODS.toml`.
- **The lock records tree digests (Breaking)** (`spec/lock-format.md`): a locked entry's `hash` is now `digest`, the tree digest of the fetched package, replacing a byte hash that concatenated paths and contents with no separator and so could give two different directories one hash. A lock carrying `hash` is refused when parsed, with a message that `lock` regenerates it, and no old hash is ever verified.
- **A fetched package is read from its commit (Breaking)** (`packages/distribution.md`, `spec/namespace-resolution.md`): a fetched package's tree is read from the resolved commit's git objects as stored, with no checkout filter, line-ending conversion or `export-ignore` applied, and filtered by the membership rule with that commit's own `.gitignore` files, so its digest is the same on every machine and a file committed despite a pattern that matches it is out of the package. The global cache holds each package's tree and nothing else, and a reader takes a cached copy's files as the tree, as written, without applying the membership rule again.
- **The bundled MTHDS schema does not describe `function_name` as an import path yet** (`mthds_schema.json`): the published schema is still the one generated by pipelex v0.82.0, which predates this release's PipeFunc change and accepts any string as `function_name`, described as the name of the function to call. It rejects nothing this standard now allows, but it still accepts a `function_name` with no dot, such as `capitalize`, a segment that is not a Python identifier or is a Python keyword, and a segment that NFKC normalization would change, such as one holding the ligature `ﬁ`, all of which this standard rejects. A later release of this site publishes the schema of the pipelex release that implements the change.
- **Documentation versions served on mthds.ai**: this release retires no version, so every link into `6.0.0` keeps resolving. The site serves `7.0.0`, which `/latest/` also serves, and `6.0.0`, and keeps the numbered `7.0.0` directory out of search indexes as it does `6.0.0`, so that only `/latest/` is indexed.

## [v6.0.0] - 2026-10-11

**MTHDS standard 6.0.0 · MTHDS Protocol 0.7.0**

### Changed

- **Stored names are plain input names (Breaking)** (`spec/mthds-format.md`): every name under which a step stores a value in working memory, namely a pipe step's or a PipeParallel branch's `result`, the `batch_as` of a step or a branch, and a PipeBatch's `input_item_name`, must now take the form of a plain input name matching `[a-z][a-z0-9_]*`, as a binding step's `result` already did, and a name in any other form, such as `Pages` or `a.b`, is rejected as `invalid_input_name`. An author renames such a name to a plain one, such as `pages`, along with every input, binding path, `batch_over` and PipeParallel output field that reads it.
- **The bundled MTHDS schema checks stored names (Breaking)** (`mthds_schema.json`): the published schema now refuses a stored name that is not a plain input name matching `[a-z][a-z0-9_]*`, namely a PipeSequence step's or a PipeParallel branch's `result` and `batch_as`, and a PipeBatch's `input_item_name`, where it refused only the reserved `_bound_` prefix before, so a tool validating against it now flags a name such as `result = "Pages"` or `batch_as = "a.b"` that it used to accept. The schema has carried this rule since pipelex v0.80.0.
- **The bundled MTHDS schema describes the new PipeJudge (Breaking)** (`mthds_schema.json`): the published schema, now the one generated by pipelex v0.82.0, carries the PipeJudge of standard 5.0.0, which closes the gap the v5.0.0 entry names. It requires `prompt`, the evidence template, beside exactly one of `question` and `questions`, and requires both `yes` and `no` in a `criteria` table, so a PipeJudge with no `prompt`, one that wrote its question in `prompt` alone, and a `criteria` table declaring one side no longer validate. It accepts a rating level written as a table of `label` and `description` (`JudgeRatingLevel`), every level of one scale carrying a label or none of them, and the multi form's `questions`, a table of at least one question keyed by name whose values are closed `JudgeQuestionBlueprint` tables of a required `question` and optional `options`, `levels`, `criteria` and `threshold`, those four fields being refused on the pipe itself beside `questions`. It does not enforce the value rules the standard sets on those fields yet, on the pipe or on each of its `questions`: it still accepts `options` beside `levels`, `criteria` or `threshold` beside either, fewer than two options or levels, empty option keys, levels and criteria, a level table carrying neither `label` nor `description`, and a `threshold` outside the open interval from 0 to 1, all of which the standard rejects. A later release of this site publishes the schema of the pipelex release that enforces them.
- **Documentation versions served on mthds.ai**: the site no longer serves any version older than `6.0.0`, the first built with the cookie consent banner, through a new `[tool.mthds.docs] floor` in `pyproject.toml` that retires every published version below it, the release before the current one included. This release stops serving `5.0.0`, `4.0.0` and the formerly pinned `0.10.0`, so links into those versions no longer resolve and should point at `/latest/`. The site serves `6.0.0` alone.

### Fixed

- **Analytics on mthds.ai wait for consent**: the site asks for consent before loading PostHog and before fetching the repository's star and fork counts from GitHub, with no purpose ticked in advance, and clears what PostHog stored in the browser when consent is refused or withdrawn. Its footer links the privacy policy and a "Cookie settings" link that reopens the choice.

## [v5.0.0] - 2026-10-09

**MTHDS standard 5.0.0 · MTHDS Protocol 0.7.0**

### Highlights

**A PipeJudge judges the evidence its prompt presents, and can ask several questions about it at once.** `prompt` is now the evidence template, written like a PipeLLM's prompt, and the closed question is always written in `question`, or as several `questions` whose verdicts fill one structured output. Rating levels may carry labels, which the `Rating` native reports, so the native set is re-pinned at `5.0.0`. Because a PipeJudge written for 4.0.0 is no longer valid, the standard moves to `5.0.0`, and the protocol stays at `0.7.0`.

### Added

- **Several questions in one PipeJudge** (`spec/mthds-format.md`): a PipeJudge may set `questions`, a table keyed by question name, instead of `question`, and each question carries its own `options`, `levels`, `criteria` and `threshold`. Every question is answered independently over the same evidence, and the output is a structured concept whose fields are exactly the question names, each declared as the verdict native of its question's kind or a concept that refines it.
- **Refusals** (`spec/mthds-format.md`): a judging model may refuse a question, and a refusal never becomes a verdict. With `question`, a refused question fails the run; with `questions`, it leaves its field absent when the field is optional and fails the run when the field is required.
- **Labelled rating levels and `Rating.label` (Breaking)** (`spec/native-concepts.md`, `spec/mthds-format.md`): a rating level may be a table carrying a `label`, a `description` or both, the labels of a scale being all present or all absent and distinct, and the `Rating` native gains an optional `label` holding the label of the selected level, copied from the declaration. The native set is re-pinned at 5.0.0, so a crate normalized at 5.0.0 materializes the new `Rating` and gets a new fingerprint.

### Changed

- **PipeJudge judges an evidence prompt (Breaking)** (`spec/mthds-format.md`): `prompt` is now a required template presenting the evidence, and the question is always written in `question`, which `prompt` no longer stands for. The judging model sees only what the templates read, so every declared input must be read by `prompt` or by a question and an unread input is rejected, as on the other inference operators; an image or a document the prompt reads is presented with it, and a question may read neither. A PipeJudge written for 4.0.0 adds a `prompt` that presents its inputs, such as `prompt = "@message"`, and one that spelled its question `prompt` renames that field `question`.
- **Yes/no criteria declare both answers (Breaking)** (`spec/mthds-format.md`): a `criteria` table now carries both `yes` and `no`, each non-empty, and a table declaring one side is rejected. An author who knows only when the answer is no writes the yes side as its complement.
- **The bundled MTHDS schema does not describe the new PipeJudge yet** (`mthds_schema.json`): the published schema is still the one generated by pipelex v0.75.0, which predates this release's PipeJudge changes. It rejects a `prompt` set beside `question`, a `questions` table and a rating level written as a table, all of which this standard allows, and it still accepts a PipeJudge with no `prompt`, a `prompt` standing in for the question, and `criteria` declaring only one side, all of which this standard rejects. A later release of this site publishes the schema of the pipelex release that implements these changes.
- **Documentation versions served on mthds.ai**: this release stops serving `3.0.0`, so links into that version no longer resolve and should point at `/latest/`. The site serves `5.0.0`, `4.0.0` and the pinned `0.10.0`.

### Fixed

- **What the hosted schema describes** (`tooling/json-schema.md`): the JSON Schema page no longer says that the hosted `mthds_schema.json` always matches the latest standard. It now says that the schema is generated by the reference implementation, so it can lag a release of the standard that changes the language, and that the changelog entry of such a release names the changes the hosted schema does not describe yet.

## [v4.0.0] - 2026-10-06

**MTHDS standard 4.0.0 · MTHDS Protocol 0.7.0**

### Highlights

**A pipe's inputs name whole concepts, and a sequence binds the fields its steps read.** An input name is a plain name on every pipe, so a dotted input such as `"page.page_view" = "Image"` is refused, and a PipeSequence gains the binding step, which copies the value at a path into working memory under a new name, its concept derived from the declared structure the path walks. A dotted `batch_over` becomes a binding followed by a batch. Because a bundle that declared a dotted input is no longer valid, the standard moves to `4.0.0`; the native set stays pinned at `3.0.0`, and the protocol stays at `0.7.0`.

### Added

- **The binding step** (`spec/mthds-format.md`): a PipeSequence step is now either a pipe step or a binding step, `{ from = "invoice.total", result = "total_amount" }`, which stores a deep copy of the value at a path in working memory under a new name, its concept derived before any run from the declared structure the path walks. A path crossing a list maps over every item and flattens into one list, a path reaching nothing records an absence under the optionality model rather than failing, and a bare name such as `from = "departure_board"` binds a renamed copy. A PipeParallel branch stays a pipe step, and a compliant implementation reports a malformed binding step, or one placed in a branch, as `binding_step_invalid`, and a path the declared structures cannot walk as `binding_path_unresolved`.

### Changed

- **Dotted `batch_over` (Breaking)** (`spec/mthds-format.md`): a dotted `batch_over` such as `catalog.pages` is now defined as a binding of that path followed by a batch over the bound list, so it derives its concept, crosses lists and records absences exactly as a binding step does. A dotted `batch_over` that breaks the binding step's path grammar, or that sits on a PipeParallel branch, since a branch cannot bind, is now rejected as `binding_step_invalid`, and one whose path derives a single value is rejected before any run. An author writes the path as field names separated by single dots, points the batch at a path that crosses a list, and binds the field a branch needs in the calling sequence, in a step before the PipeParallel step, so that the branch's plain `batch_over` names the bound list. Names starting with `_bound_` are reserved for the private names an implementation binds a dotted `batch_over` under, so a pipe step's or branch's `result`, `batch_as` or plain `batch_over`, or a PipeBatch's `input_item_name`, taking that prefix is now rejected as `invalid_input_name`, and an author renames it.
- **The bundled MTHDS schema (Breaking)** (`mthds_schema.json`): a PipeSequence step is now either a pipe step or a binding step, the binding step being a closed table of `from`, which follows the path grammar, and `result`, a plain input name; a PipeParallel branch is a pipe step whose `batch_over` carries no dot; a sequence step's dotted `batch_over` follows the path grammar; and every `inputs` table, like a PipeBatch's `input_list_name`, accepts only plain input names matching `[a-z][a-z0-9_]*`. The schema also refuses the reserved `_bound_` prefix on the fields the specification reserves it on, and it now carries the PipeJudge blueprint, which the previous copy predated, and the PipeDocGen blueprint, which this specification does not define yet. This copy is the schema generated by pipelex v0.75.0, the release that carries these changes.
- **Documentation versions served on mthds.ai**: this release stops serving `2.1.1`, the last version left on the 2.x line, so links into that version no longer resolve and should point at `/latest/`. The site serves `4.0.0`, `3.0.0` and the pinned `0.10.0`.

### Removed

- **Dotted input names (Breaking)** (`spec/mthds-format.md`): an input name is a plain `snake_case` name on every pipe, so a dotted key such as `"page.page_view" = "Image"` is rejected as `invalid_input_name`, and so is a dotted `input_list_name` on a PipeBatch; every operator now matches a template variable to a declared input by its root alone. Every operator that handles a value according to its concept now handles a template variable according to the concept its path reaches through the root's declared concept, so PipeLLM attaches `@page.page_view` on `page = "Page"` as an image and PipeImgGen injects it as a reference image. A bundle that declared a dotted input declares the root with its whole concept instead and reads the field through it in the template (`page = "Page"`, read as `@page.page_view`), or has the calling sequence hand the field over under a plain name with a binding step.

## [v3.0.0] - 2026-10-04

**MTHDS standard 3.0.0 · MTHDS Protocol 0.7.0**

### Highlights

**A method can ask a model for a verdict, and get its uncertainty back with it.** `PipeJudge` puts one closed question to a judging model and returns a `YesNo`, `Choice` or `Rating`, the native set being re-pinned at 3.0.0 to carry those verdicts. **The protocol moves to `0.7.0`** to list the models that serve it under a new `judgment` category, and a client reading a model list now keeps going when it meets a category it does not recognize.

### Added

- **PipeJudge** (`spec/mthds-format.md`): a new operator asks a judging model one closed question about its inputs — yes or no, one key out of its `options`, or one index into its `levels` — and returns the verdict as a `YesNo`, `Choice` or `Rating` carrying whatever uncertainty the model reports, with an optional `threshold` deciding a yes. Its template field is `question`, with `prompt` read as a synonym, and its inputs reach the model by name as the material to judge, so unlike the other inference operators it does not reject an input its question never references.
- **The verdict natives `Choice` and `Rating`, and `YesNo`'s `probability` (Breaking)** (`spec/native-concepts.md`): the native set is re-pinned at 3.0.0, adding `Choice` (a required `choice`, optional `confidence` and `probabilities`) and `Rating` (a required `level`, optional `confidence`, `probabilities` and `position`), and an optional `probability` on `YesNo`. A bundle declaring its own `Choice` or `Rating` concept must rename it, since native codes are reserved, and a crate normalized at 3.0.0 materializes the new `YesNo` and so gets a new fingerprint. The input-form descriptor keeps `YesNo` a `boolean`, the output-form descriptor now states a `YesNo` as an `object` carrying `yes_no` and `probability`, and both state `Choice` and `Rating` as `object`s.
- **The `judgment` model category (Breaking)** (`spec/protocol.md`): `GET /models` lists a model that serves `PipeJudge` under the category `judgment`, and its `?type=` filter accepts the value; a client that checks a deck entry's `type` against the previous closed set fails on such an entry until it follows the reader rule below. The protocol page now defines a model category as a settings family of the language, with a table giving each category's settings family and the pipes that name its models, and the protocol adds a category in its next minor version whenever the standard adds a settings family.

### Changed

- **A client accepts a model category it does not recognize (Breaking)** (`spec/protocol.md`): a client reading a model list must not fail it because an entry carries a category it does not recognize; it keeps that entry with its raw value or leaves it out. A runner still emits only the protocol's categories, reports a vendor's own model family under an extension property, and answers an undefined `?type=` value with a `422`. `spec/versioning.md` now counts a new value of an enumerated response field as a minor protocol change, so this release's `judgment` category moves the protocol to `0.7.0` rather than to `1.0.0`.
- **PipeImgGen, PipeSearch and PipeCompose reject a declared input they never read (Breaking)** (`spec/mthds-format.md`): as for PipeLLM, every declared input must be referenced by the fields that read the pipe's inputs — `prompt` or `negative_prompt` for PipeImgGen, `prompt` for PipeSearch, the template for PipeCompose, and in construct mode every `from` path and field template, nested constructs included — and an optional input is not exempt. A new section, Inputs Read Through Templates, states when a template variable reads an input, including a dotted input name. A bundle declaring an input one of these pipes never reads must reference it or remove it from `inputs`.
- **Documentation versions served on mthds.ai**: this release stops serving `2.1.0`, so links into that version no longer resolve and should point at `/latest/`. The site serves `3.0.0`, `2.1.1` and the pinned `0.10.0`.

## [v2.1.1] - 2026-09-19

**MTHDS standard 2.1.1 · MTHDS Protocol 0.6.0**

### Changed

- **Documentation versions served on mthds.ai**: the site now serves the current standard, the release before it and each version pinned under `[tool.mthds.docs] retain` in `pyproject.toml` — today `0.10.0`, the last 0.x standard — and every deploy retires the rest, while `make docs-retention` prints what the next deploy would keep and retire. This release stops serving `2.0.0`, `0.9.0`, `0.8.0`, `0.7.0`, `0.6.0`, `0.5.0`, `0.4.1`, `0.4.0` and the unlisted `0.1.2` directory, so links into those versions no longer resolve and should point at `/latest/`.

## [v2.1.0] - 2026-09-19

**MTHDS standard 2.1.0 · MTHDS Protocol 0.6.0**

### Highlights

**A stuff has one shape wherever it travels, and the standard now says so.** Every surface that carries a value — the CLI's `--inputs` and stdin, the `--with-memory` envelope, a runner's `pipe_output`, a file written from a working memory — spells it `{"concept": "<key>", "content": …}`, where the key is the string the library crate files the concept under. The concept's definition stays in the library and never travels beside the value it describes.

### Changed

- **A stuff's `concept` on the wire is its crate key (Breaking)** (`spec/cli-io-contract.md`): the CLI I/O Contract now states the shape a stuff takes wherever it travels — `--inputs`, stdin, the `--with-memory` envelope, a runner's `pipe_output` and any file written from a working memory — as `{"concept": "<key>", "content": …}`, `concept` being the string the library crate keys the concept under: `<domain>.<Code>` for the method's own and native concepts, `<package_address>::<domain>.<Code>` for a dependency's. The concept's definition belongs to the library and never travels beside a stuff. A runtime must emit that string and must not emit an object in its place; on input it may also accept a package-qualified reference, a bare code or a bare value as a convenience. The `--with-memory` example, which showed `concept` as an object, now agrees with the rule, and the protocol page says the same of `pipe_output`.
- **Versioning** (`spec/versioning.md`): the CLI I/O contract joins what the standard version governs, with the reading that a wire rule leaving every authored document valid is a MINOR change marked breaking for implementations; and the shape of a stuff inside the protocol's inputs and `pipe_output` is the standard's, so a change to it moves no protocol number.

### Fixed

- **The `RunRequest` example on the protocol page** (`spec/protocol.md`): its `Document` input named the concept by its bare code and gave the content a `file_path` field the native concept does not have. It now reads `native.Document` with a `url`, the concept's one required field.

## [v2.0.0] - 2026-09-14

**MTHDS standard 2.0.0 · MTHDS Protocol 0.6.0**

### Highlights

**The standard version and the specification's release version are now one number, cut at `2.0.0`.** The breaking changes shipped in `v0.8.0`, `v0.9.0` and `v0.10.0` were made while the standard still read `1.0.0`; this release accounts for them with a major cut, writes down the rule every later release follows, and adds a check that keeps every stated copy of the two numbers in agreement. **A pipe's output gets a presentation descriptor of its own**, the counterpart of the input-form descriptor, so a result can be shown or typed without schema heuristics.

### Added

- **Versioning** (`spec/versioning.md`): New specification page defining how MTHDS is versioned — the standard version, which covers the language, the native set and the manifest, lock, crate and namespace formats, and the protocol version, which covers the HTTP runner contract alone and moves independently. It states what bumps each and where each is written, that a recommended extension field on the validate response does not move the protocol version, and that every changelog heading from `v2.0.0` onward names the standard and protocol versions of its release.
- **A version-consistency check** (`make version-check`): every written copy of the standard and protocol versions — the versioning page, the manifest specification and guides with the `mthds_version` constraints in their example manifests, the roadmap, the agent guide, the OpenAPI document, the protocol page and the changelog's topmost heading — must agree, or the check names each disagreeing site and fails. It runs in `make docs-check` on every documentation pull request and in the `changelog-check` and `version-check` release gates; the versions at which the native set and the intent vocabulary are pinned are excluded, since each lags the current version by design.
- **Output-Form Descriptor** (`spec/output-form-descriptor.md`): New specification for the presentation view of what a pipe resolves to — one field descriptor per pipe, stating its output's kind, nesting and constraints, so that showing a result or generating a type for it needs no schema heuristics. It reuses the input-form descriptor's field descriptor and states only what an output position changes: no `presence` and no `gating`, the fixed node name `output`, `required` always `true` with possible absence left to the contract's `optional`, and the plural wrap that makes a `Concept[]` output a `list` node whose `item` is the element. Pipe I/O Contracts, the Input-Form Descriptor, the Library Crate Format and the `.mthds` File Format now point at it.
- **`output_form` on the validate response**: a recommended extension field, on the same terms as `pipe_io_contracts` and `input_form` — a runner reporting it uses this shape under this name, and a runner omitting it is still conformant. No base field and no route changes, so the protocol version does not move.

### Changed

- **The standard version is the specification's release version, cut at `2.0.0` (Breaking)**: the specification's release, its changelog heading and `MTHDS_STANDARD_VERSION` in every implementation are one number, so an implementation of this release reports `2.0.0`. The version moves forwards rather than down to the `0.x` line, so a manifest constraint of `>=1.0.0` stays satisfiable; a crate stamped `1.0.0` predates native-set pinning, and re-normalizing it restamps it at the set pinned in `2.0.0`.
- **Pinned sets are identified by the version in which they last changed**: an implementation of standard version `V` materializes the native set, and resolves the intent vocabulary, of the greatest pinned version less than or equal to `V`, so implementations on different patch or minor versions still byte-agree on materialized natives and on crate fingerprints. The intent vocabulary, which named itself only as "this version", is now pinned at `2.0.0`.
- **The protocol version is reconciled at `0.6.0`**: the conformance statement in `spec/protocol.md` said v0.1 beside a `0.6.0` example, and now agrees with the OpenAPI document and the shipped client libraries. The protocol page states the protocol's own bump rule.
- **`mthds_version` examples require `>=2.0.0`** in the manifest specification, the manifest guide and the package-creation guide, so a package created by following the documentation declares the standard it was written against.

### Fixed

- **The reference runner's license on the runtime page**: `implementers/runtime.md` called `pipelex-api` MIT. It now says the runner is source-available under the Elastic License 2.0, and that the license is the implementation's alone: the standard and its OpenAPI document stay MIT, and any runtime may implement the protocol under its own terms.
- **The version-check workflow passes pull requests into `main` that are not releases**: `exit 0` in its branch-detection step ended that step rather than the job, so a non-release pull request went on to compare `pyproject.toml` against an empty release version and failed.
- **Archived 2.x documentation versions are kept out of search indexes**: the root `robots.txt` and the `noindex` headers matched `/0.` only, so `/2.0.0/` would have been indexed as a duplicate of `/latest/`. Both lists now cover each major release line.

## [v0.10.0] - 2026-09-02

### Added

- **Future Directions** (`packages/future-directions.md`): New page preserving the package ecosystem's ambitions — typed signature search, the Know-How Graph, signed manifests, and registry proxy/mirror chains — explicitly as non-normative directions, kept distinct from the specified system.
- **Schema updates for pipelex v0.55.0:** `docs/mthds_schema.json` gains the `hints` members on concepts and structure fields, the `InputSlotBlueprint` (the expanded input slot form), and `PipeLLMBlueprint.templating_style`. The pipe-level `templating_style` is now documented in the `.mthds` file format specification, in both its accepted forms.

### Changed

- **The package system specification is rewritten to the decided design.** The packaging corpus — manifest, lock, resolution, crate, distribution, and registry pages — now describes one coherent, committed system rather than a mix of live rules and speculative plans.
- **The package management CLI group is renamed** from `mthds pkg` to `mthds package` (breaking).
- **Manifest (`METHODS.toml`) rules (breaking):** `name` is strictly required and serves as the package identity (the directory-name-match rule is deleted), and `main_pipe` is auto-exported rather than requiring an explicit `[exports]` entry.
- **Version resolution commits to Minimum Version Selection (breaking):** Constraints are read strictly as floors. `update` raises floors to the latest available versions and re-locks; `add` records the added dependency's latest version as the new floor.
- **Lock file semantics:** `methods.lock` is specified as a regenerable verification record with semantic identity. Entries pin a semantic `fingerprint`, the resolved `commit` SHA, and a `source` clone URL that consistently carries its `.git` suffix.
- **Library crate keyspace:** The multi-package keyspace uses host-relative `::` address keys. Dependency-contributed entries are keyed by package address (`github.com/acme/legal-tools::legal.ContractClause`), so no two packages can collide.
- **Cross-package visibility:** A reference to a dependency's non-exported pipe is diagnosed as a validation error naming the export surface, instead of being silently omitted at load time.
- **Distribution and caching:** The versioned reference grammar (`<address>[@<tag>]`) is formalized, along with the two-cache system — the global VCS cache and the project-local method cache.
- **The registry specification is re-scoped** to its implemented surface: index, package pages, text search, validation badges, and freshness signals.

### Fixed

- **The VCS fetching algorithm derives the clone URL from the repository segments.** The implementer guide told implementations to prepend `https://` and append `.git` to the whole package address, which produces a nonexistent URL for a package in a library repository; it now follows the Clone URL Derivation rule and uses the hostname plus the first two path segments.
- **`LLMSetting.prompting_target` is gone from the language and format documentation.** The field was removed from a schema whose `LLMSetting` is closed, so the pages that still advertised it described input the schema rejects.
- **The export surface in the language guide includes manifest main pipes.** A pipe made public solely by `[package].main_pipe` was public per the specification and private per the guide.
- **The determinism and regeneration guarantees state their real precondition.** Resolution and lock regeneration were described as holding under an "unchanged published tag set" and "regardless of when you run the resolver"; both are conditioned on which version tags exist *and* which commits they point at, since tags may be added, deleted or re-pointed. The lock file is regenerable and still the record of what was fetched — not "regenerable rather than load-bearing".
- **The documentation build is gated on the pull requests that carry the work.** `docs-check` now triggers on pull requests targeting `dev` as well as `main`, and `CHANGELOG.md`, `CODE_OF_CONDUCT.md` and `LICENSE` join the path filters, so an edit to any snippet-included repo-root file triggers the strict build.

### Removed

- **Deprecated schema fields:** `LLMSetting.prompting_target` and its `PromptingTarget` definition are gone from the MTHDS schema, having already been dropped from the language.
- **Speculative registry pages:** `packages/registry-search.md` and `packages/registry-distribution.md` are removed; their implemented content merged into the registry overview and their speculative content moved to Future Directions.
- **Speculative registry CLI commands:** `search`, `graph`, `inspect` and `index` are removed from the CLI reference, which now documents only the live manifest and dependency lifecycle.

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
