---
description: "Understand the directory layout of an MTHDS package: bundles, manifest, domains, and the know-how graph."
---

# Package Structure

A **package** is the distribution unit of MTHDS. It is a directory that contains a manifest (`METHODS.toml`) and one or more bundles (`.mthds` files).

## A Minimal Package

```
my_tool/
├── METHODS.toml
└── main.mthds
```

This is the smallest distributable package: one manifest, one bundle. The manifest gives the package an identity — an address, a version, a description — turning a standalone bundle into something that other packages can depend on.

## A Full Package

```
legal_tools/
├── METHODS.toml
├── methods.lock
├── general_legal.mthds
├── contract_analysis.mthds
├── shareholder_agreements.mthds
├── scoring.mthds
├── README.md
└── LICENSE
```

This package has multiple bundles, each declaring its own domain (`legal`, `legal.contracts`, `legal.contracts.shareholder`, `scoring`). The `methods.lock` file records exact dependency versions for reproducible builds.

## Directory Layout Rules

- `METHODS.toml` must be at the directory root.
- `methods.lock` must be alongside `METHODS.toml` at the root.
- `.mthds` files can be at the root or in subdirectories. A compliant runtime discovers all `.mthds` files recursively.
- A single directory should contain one package.

## Standalone Bundles (No Package)

A `.mthds` file works without a package manifest. When used standalone:

- All pipes are treated as public (no visibility restrictions).
- No dependencies are available beyond [native concepts](../language/concepts.md#native-concepts).
- The bundle is not distributable (no package address).

This preserves the "single file = working method" experience for learning, prototyping, and simple projects. When you need distribution, add a `METHODS.toml` — the rest of this section shows how.

## Progressive Enhancement

The package system follows a progressive enhancement principle:

1. **Single file** — a `.mthds` bundle works on its own. No configuration, no manifest.
2. **Package** — add a `METHODS.toml` to get exports, visibility, and a globally unique identity.
3. **Dependencies** — add `[dependencies]` to compose with other packages.
4. **Ecosystem** — publish, search, and discover through the Know-How Graph.

Each layer adds capability without breaking the previous one.

## Manifest Discovery

When loading a `.mthds` bundle, a compliant runtime discovers the manifest by walking up the directory tree:

1. Check the bundle's directory for `METHODS.toml`.
2. If not found, move to the parent directory.
3. Stop when `METHODS.toml` is found, a `.git` directory is encountered, or the filesystem root is reached.
4. If no manifest is found, the bundle is treated as a standalone bundle.

## See Also

- [Specification: Package Directory Structure](../spec/manifest-format.md#package-directory-structure) — normative reference for layout rules.
- [The Manifest](manifest.md) — what goes inside `METHODS.toml`.
