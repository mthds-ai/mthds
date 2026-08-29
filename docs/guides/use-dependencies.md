---
description: "Add dependencies on other MTHDS packages and use their concepts and pipes in your bundles with cross-package references."
---

# Use Dependencies

This guide shows how to add dependencies on other MTHDS packages and use their concepts and pipes in your bundles.

!!! note "Implementation status"
    The dependency lifecycle commands shown here are committed design; see the [normative status note](../spec/manifest-format.md#the-dependencies-section) for how conformance is asserted as implementations land.

## Step 1: Add a Dependency

Use `mthds package add` to add a dependency to your `METHODS.toml`:

```bash
mthds package add github.com/mthds/document-processing --version "^1.0.0"
```

This adds an entry to the `[dependencies]` section:

```toml
[dependencies]
document_processing = { address = "github.com/mthds/document-processing", version = "^1.0.0" }
```

The alias (`document_processing`) is auto-derived from the last segment of the address. To choose a shorter alias:

```bash
mthds package add github.com/mthds/document-processing --alias docproc --version "^1.0.0"
```

```toml
[dependencies]
docproc = { address = "github.com/mthds/document-processing", version = "^1.0.0" }
```

## Step 2: Resolve and Lock

Generate the lock file to pin exact versions:

```bash
mthds package lock
```

Then install the dependencies into the local cache:

```bash
mthds package install
```

## Step 3: Use Cross-Package References

In your `.mthds` files, reference the dependency's concepts and pipes using the `->` syntax:

```toml
domain = "analysis"

[pipe.analyze_document]
type        = "PipeSequence"
description = "Extract pages from a document and analyze them"
inputs      = { document = "Document" }
output      = "AnalysisResult"
steps = [
    { pipe = "docproc->extraction.extract_text", result = "pages" },
    { pipe = "process_pages", result = "analysis" },
]
```

The reference `docproc->extraction.extract_text` reads as: "from the package aliased as `docproc`, get the pipe `extract_text` in the `extraction` domain."

Cross-package concept references work the same way:

```toml
[concept.DetailedPage]
description = "An enriched page with additional metadata"
refines     = "docproc->extraction.ExtractedPage"
```

## Step 4: Validate

```bash
mthds validate --all
```

Validation checks that:

- The alias `docproc` exists in `[dependencies]`.
- The pipe `extract_text` exists in the `extraction` domain of the resolved dependency.
- The pipe is exported by the dependency (listed in its `[exports]` or declared as `main_pipe`).

## Using Local Path Dependencies

During development, you can point a dependency to a local directory instead of fetching it remotely:

```bash
mthds package add github.com/mthds/document-processing --path ../document-processing --version "^1.0.0"
```

```toml
[dependencies]
docproc = { address = "github.com/mthds/document-processing", version = "^1.0.0", path = "../document-processing" }
```

Local path dependencies are resolved from the filesystem at load time. They are not resolved transitively and are excluded from the lock file.

## Updating Dependencies

Under [Minimum Version Selection](../packages/version-resolution.md), re-resolving never moves a version on its own — your floors decide. To move forward:

```bash
mthds package update
```

This raises the floors in `METHODS.toml` to the latest available versions, re-locks, and shows what moved. Adding a dependency (`mthds package add`) records its latest version as the floor, so a fresh `add` always gets you the newest release.

## See Also

- [Dependencies](../packages/dependencies.md) — full reference for dependency fields and version constraints.
- [Cross-Package References](../packages/cross-package-references.md) — the `->` syntax explained.
- [Version Resolution](../packages/version-resolution.md) — how Minimum Version Selection works.
