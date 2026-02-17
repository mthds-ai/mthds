---
description: "Guide to turning standalone .mthds bundles into a distributable MTHDS package with a manifest and exports."
---

# Create a Package

This guide walks you through turning a standalone bundle into a distributable MTHDS package.

## What You Start With

You have one or more `.mthds` files that work on their own:

```
my-methods/
├── summarizer.mthds
└── classifier.mthds
```

## Step 1: Initialize the Manifest

Run `mthds pkg init` from the package directory:

```bash
cd my-methods
mthds pkg init
```

This scans all `.mthds` files, extracts domains and pipe names, and generates a `METHODS.toml` skeleton:

```toml
[package]
address     = "example.com/yourorg/my_methods"
version     = "0.1.0"
description = "Package generated from 2 .mthds file(s)"

[exports.summarization]
pipes = ["summarize"]

[exports.classification]
pipes = ["classify_document"]
```

## Step 2: Set the Package Address

Edit the `address` field to your actual repository location:

```toml
[package]
address     = "github.com/yourorg/my-methods"
version     = "0.1.0"
description = "Text summarization and document classification methods"
```

The address must start with a hostname (containing at least one dot), followed by a path. It doubles as the fetch location when other packages depend on yours.

## Step 3: Configure Exports

Review the `[exports]` section. The generated manifest exports all pipes found during scanning. Narrow it down to your public API:

```toml
[exports.summarization]
pipes = ["summarize"]

[exports.classification]
pipes = ["classify_document"]
```

Pipes not listed in `[exports]` are private — they are implementation details invisible to consumers. Pipes declared as `main_pipe` in a bundle header are auto-exported regardless of whether they appear here.

Concepts are always public — they do not need to be listed.

## Step 4: Add Metadata

Add optional but recommended fields:

```toml
[package]
address       = "github.com/yourorg/my-methods"
version       = "0.1.0"
description   = "Text summarization and document classification methods"
authors       = ["Your Name <you@example.com>"]
license       = "MIT"
mthds_version = ">=1.0.0"
```

## Step 5: Validate

Verify your package is well-formed:

```bash
mthds validate --all
```

This validates all pipes across all bundles in the package, checking concept references, pipe references, and visibility rules.

## The Result

Your package directory now looks like:

```
my-methods/
├── METHODS.toml
├── summarizer.mthds
└── classifier.mthds
```

You have a distributable package with a globally unique address, versioned identity, and controlled exports. Other packages can now depend on it.

## See Also

- [The Manifest](../packages/manifest.md) — full reference for `METHODS.toml` fields.
- [Exports & Visibility](../packages/exports-visibility.md) — how visibility rules work.
- [Use Dependencies](use-dependencies.md) — how to depend on other packages.
