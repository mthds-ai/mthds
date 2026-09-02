# Package specification — open questions

Standards decisions surfaced by the review-agent triage of [PR #62](https://github.com/mthds-ai/mthds/pull/62) (`release/v0.10.0`), the release that rewrote the packaging corpus to the decided design. Each one is real and verified against the documents; each defers because closing it means **deciding what the standard should say**, not transcribing a decision already taken. Everything else that pass surfaced was fixed in the PR itself.

None of these is a regression introduced by that release unless the entry says so.

## Manifest `main_pipe` does not identify a pipe unambiguously

**Where:** `docs/spec/manifest-format.md:132` (the `main_pipe` value rule), with `docs/spec/namespace-resolution.md:358` (Manifest Validation rule 6).

**Reporters:** the Codex PR bot (P1), corroborated independently by cubic and by Codex's own reviewer run locally.

**The issue.** Three facts combine into a gap:

1. `docs/spec/manifest-format.md:132` — the value "MUST be a valid `snake_case` pipe code (matching `[a-z][a-z0-9_]*`)". That pattern excludes `.`, so a domain-qualified value such as `legal.contracts.analyze_nda` is *syntactically invalid*. Restated at `manifest-format.md:35` and mirrored at `docs/packages/manifest.md:101`.
2. `docs/spec/namespace-resolution.md:159` — "Different domains (same package) | Same concept or pipe code | No conflict — different namespaces." Only same-domain collisions are errors.
3. Manifest Validation rule 6 (`docs/spec/namespace-resolution.md:358`) requires only that the value be a well-formed pipe code — not that it exist, and not that it resolve uniquely.

So a package declaring both `legal.analyze` and `scoring.analyze` with `main_pipe = "analyze"` is a valid manifest, and two conformant runtimes may auto-export and execute different pipes. cubic added the second half: validation cannot even reject a `main_pipe` that names no pipe at all, so an invalid manifest passes and fails only when invoked.

Corroborating that the mapping was never specified: the implementer algorithm indexes main pipes from bundles only — `docs/implementers/package-loading.md:87` (`main_pipes: (alias, domain) -> pipe code`) and `:112` (`main_pipes = build_main_pipe_index(bundles)`). A manifest-level main pipe has no slot in that domain-keyed index.

**Correcting the reporter, because it changes the framing.** The bot attributed the ambiguity to this release removing the requirement that `main_pipe` appear in a domain-specific `[exports]` table. That is not right. The old rule (`git show origin/main:docs/spec/manifest-format.md:130`, "The referenced pipe MUST be declared in the `[exports]` section") narrowed the candidate set to exported pipes but guaranteed no uniqueness either — nothing forbade `[exports.legal]` and `[exports.scoring]` both listing `analyze`. **The ambiguity pre-dates the release**, which only widens the candidate set from exported pipes to all pipes in the package.

**Why deferred.** The options are not equivalent and each has its own blast radius:

- permit a domain-qualified `main_pipe` — relaxes the `snake_case`-only pattern at three spec sites plus the committed JSON schema;
- require the code to resolve uniquely across the package's domains — rejects packages that are legal today;
- define the manifest `main_pipe` as a pointer to a bundle main pipe — narrowest, but changes what the field means.

**Blocked on this decision**, and deliberately left untouched by the PR-review pass: `docs/language/namespace-resolution.md:84` and its normative twin `docs/spec/namespace-resolution.md:122` (intra-package cross-domain visibility, "or is the `main_pipe` of a bundle in `legal.contracts`"), and `docs/implementers/package-loading.md:112`'s `build_main_pipe_index(bundles)`. Guide and specification agree at all three; none can name a manifest main pipe until this question is settled, because such a pipe has no domain.

## The project-local method cache is keyed by a name that is not globally unique

**Where:** `docs/spec/library-crate.md:45` (normative), mirrored at `docs/packages/distribution.md:70`.

**Reporter:** Codex's reviewer, run locally against the PR diff. No PR bot raised it.

**The issue.** `docs/spec/library-crate.md:45` specifies the project-local method cache as `.mthds/methods/<name>/`, "keyed by dependency name", and `docs/packages/distribution.md:72` — new in this release — has install materialize **every locked dependency, transitively**, into it. But `name` is not a global key: `docs/spec/manifest-format.md:28` reserves "globally unique package identifier" for the `address`, and the constraints on `name` (`manifest-format.md:66-70`) are only `snake_case`, 2–25 characters. Nothing forbids `github.com/acme/tools/documents` and `github.com/mthds/methods/documents` from both carrying `name = "documents"`, and the lock covers all transitive remote dependencies (`docs/spec/lock-format.md:78`). One would overwrite the other.

Reading `<name>` as the *alias* instead does not help: `docs/spec/namespace-resolution.md:359` makes aliases unique only per manifest, and the flat cache holds transitive dependencies that have no alias in the consuming manifest at all.

**Why deferred, and why it is nonetheless worth deciding.** Two things keep it below a release-PR bar. `docs/spec/manifest-format.md:72` explicitly carves the question out of the standard — "Where a fetched or cached copy of a package lives on disk is a tool concern, not part of the standard" — so `<name>` is arguably illustrative rather than a normative path template, although `docs/spec/library-crate.md:41` does make the *directory* normative while leaving the leaf undecided. And the scheme pre-dates the release: `origin/main` carries `library-crate.md:45` verbatim.

What makes it worth an owner's attention is the asymmetry the release itself created. This same release decided the analogous question for the crate keyspace, and decided it *against* names and aliases — `docs/spec/library-crate.md:82`: "The prefix is the **address, never the alias**… The full address is globally unique by definition… so address-keyed entries are collision-free across any closure." The disk cache is now the one place in the corpus still keyed by a non-global name.

**Options.** An address-derived leaf (`.mthds/methods/github.com/mthds/methods/documents/` — unambiguous, ugly); or a short name plus a scan-by-manifest-identity rule mirroring `docs/packages/distribution.md:47-52` ("Directory names carry no meaning… scans the clone for `METHODS.toml` files"); or a non-deciding normative sentence that states only the requirement — each locked package address occupies its own directory, and a tool MUST NOT let two distinct addresses share one — and leaves the scheme to tools. Even the last is a new normative sentence, so it belongs to the owner.

## Whether version ranges should be legal under Minimum Version Selection

**Where:** `docs/spec/manifest-format.md:190-206` (the constraint grammar) against `docs/spec/namespace-resolution.md:164-169` (the MVS algorithm).

**Reporter:** surfaced while verifying the determinism over-claim that the release fixed; no reviewer raised it directly.

**The issue.** MTHDS keeps the full range vocabulary — caret, tilde, wildcard, `<`, `>`, `<=`, `!=`, `==`, and compound constraints — and that table was not touched by the release. The normative algorithm is availability-dependent as a MUST: "List all available versions (from VCS tags) … Select the minimum version that satisfies all constraints simultaneously." Under a range, publishing a previously-absent *lower* matching tag therefore changes the answer for an unchanged manifest: `^1.0.0` with `1.1.0` and `1.2.0` available resolves `1.1.0`; a later backport of `1.0.3` re-resolves to `1.0.3`, a downgrade nobody asked for.

Go's MVS has no ranges precisely so that selection is availability-independent. MTHDS instead hedges around the seam in three separate places — `docs/spec/manifest-format.md:208`, `docs/spec/namespace-resolution.md:173`, `docs/packages/version-resolution.md:22` — each qualifying max-of-floors with "for plain floor constraints". That triple hedge is the standard noticing the gap without closing it.

The release corrected the *prose* that over-claimed determinism on the back of this. It did not, and should not have, decided the underlying question.

**Options.** Restrict the grammar to plain floors, so max-of-floors becomes the general rule and selection is genuinely time-invariant; or keep ranges and document the backport-downgrade case explicitly, so the seam is stated rather than hedged.

## Elsewhere

- **The integrity hash's digest input is not injective.** Raised by cubic locally, verified, and filed in the workspace ledger rather than here, because closing it obligates `mthds-python` and `mthds-js` to change in lockstep — their maintainers will not read this repo's `wip/`. Filed as **L-260902-99a2a6** (owner `mthds`, type `decision`); the short form is that `docs/spec/lock-format.md:60-70` concatenates each relative path with its file bytes with no separator or length prefix, so path `a` with contents `bc` and path `ab` with contents `c` hash identically.

- **A mild wording tension around the clone cache key, no action requested.** `docs/packages/distribution.md:63` (new in this release) calls the resolved commit "the honest key for **any** clone cache", while `docs/packages/distribution.md:69` and `docs/spec/namespace-resolution.md:214` key the global VCS cache by `{version}`. The tension is slight — a "clone cache" retains `.git` whereas VCS-cache entries have it removed, and line 63 is advisory — but these are the two sentences to reconcile if the install-by-commit question below is ever revisited.

- **Rejected: "install must check out the locked `commit`."** Codex's local reviewer observed correctly that the Verification procedure (`docs/spec/lock-format.md:91-96`) never fetches or checks out `commit`, and that fetching clones by tag. But it assumed a purpose the specification does not assign: three independent sites define `commit` as *provenance* — `docs/spec/lock-format.md:56`, `docs/packages/distribution.md:63`, `docs/packages/lock-file.md:45`. And the behaviour is fail-safe: on a re-pointed tag, install fetches the new tree, the byte hash diverges from the lock, and step 4 rejects the install as a hard failure. Nothing unpinned is ever installed. Checking out the pinned commit silently instead would hide a re-pointed tag from the consumer — a different design, not obviously a better one. Recorded here so a later round does not re-raise it.

- **`PipeLLM.templating_style` semantics beyond its shape.** The release documented the field in `docs/spec/mthds-format.md` from what the committed schema and the existing Templating Style section establish. Two things remain unstated anywhere in this repo and were deliberately not invented: whether the bare-string form (`templating_style = "xml"`) is exact shorthand for `{ tag_style = "xml" }` taking the default `text_format = "plain"`, and whether the style governs `system_prompt` as well as `prompt` and how it interacts with a PipeCompose template's own style. Both need a check against the `pipelex` v0.55.0 runtime before the prose can sharpen.
