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

This package has multiple bundles, each declaring its own domain (`legal`, `legal.contracts`, `legal.contracts.shareholder`, `scoring`). The `methods.lock` file records exact dependency versions for verifiable installs.

## Method Files

A package is its folder. Every file under the folder that holds `METHODS.toml` belongs to the method and travels with it, whatever it is for:

```
invoice_letters/
├── METHODS.toml
├── letters.mthds
├── requirements.txt
├── funcs/
│   └── totals.py
├── templates/
│   ├── letter.html
│   └── logo.png
├── README.md
├── .gitignore
└── .venv/
```

Here the bundle, the Python module a `PipeFunc` step calls, the template and the logo it shows, the `requirements.txt` that declares the Python packages `totals.py` imports, and the `README.md` all travel together. There is no list of files to maintain: drop a file into the folder and it is part of the method.

A few files stay out on their own, so that a method never carries what it should not:

- **Anything whose name starts with a dot**, at any depth: `.git/`, `.venv/`, `.env`, `.gitignore` and the `.mthds/` folder where installed dependencies live.
- **The defaults**: `__pycache__/`, `node_modules/`, any Python virtual environment whatever its name, any repository nested inside the folder, any other package nested inside it, meaning a subfolder holding its own `METHODS.toml`, which travels as a package of its own, and a run's inputs file at the top of the folder, `inputs.json` or `inputs.toml`, so the data of a run you start from the folder never travels as part of the method. Example inputs you want to ship go in a subfolder, such as `examples/inputs.json`, where they travel like any other file.
- **Whatever the folder's own `.gitignore` files ignore**, read exactly as git reads them, so what travels is what git would publish.
- **Whatever the manifest's [`exclude`](manifest.md#exclude) patterns name**, for files you want out of the method but still in git.

A step names another file by its path from the bundle that uses it, such as `templates/letter.html`, or `../shared/logo.png` from a template one folder down, and that path is looked up among the method's files, never on the disk of whoever runs it. A symbolic link inside the folder is refused rather than followed. The [Method Tree](../spec/method-tree.md) specification states every rule exactly, along with the tree digest that identifies a method by its files.

## The Three Artifacts

Three artifacts carry a package through its life, and each answers a different question:

- **`METHODS.toml`** — the [manifest](manifest.md) — resolves *which files* make up the package and what its identity is.
- **`methods.lock`** — the [lock file](lock-file.md) — pins *which versions* of its remote dependencies it resolves to.
- **The [library crate](../spec/library-crate.md)** — the resolution artifact — captures *what the resolved files mean*: the flat, fully-qualified, fingerprinted snapshot the whole library resolves into. It is derived and recomputable, never authored.

## Directory Layout Rules

- `METHODS.toml` must be at the directory root.
- `methods.lock` must be alongside `METHODS.toml` at the root.
- `.mthds` files can be at the root or in subdirectories. A compliant runtime loads every `.mthds` file among the method's files, and only those.
- A single directory should contain one package.
- The directory name is not part of the package's identity — the manifest `name` is. A kebab-case repository holding a snake_case-named package is perfectly fine.

## Standalone Bundles (No Package)

A `.mthds` file works without a package manifest. When used standalone:

- All pipes are treated as public (no visibility restrictions).
- No dependencies are available beyond [native concepts](../language/concepts.md#native-concepts).
- The bundle is not distributable (no package address).

This preserves the "single file = working method" experience for learning, prototyping, and simple projects. When you need distribution, add a `METHODS.toml` — the rest of this section shows how.

A bundle named on its own carries nothing else with it: its method is that one file. A step that names a template or a Python module beside it is refused until you hand over the folder instead, which makes the folder the method, or add a `METHODS.toml` to it.

## Progressive Enhancement

The package system follows a progressive enhancement principle:

1. **Single file** — a `.mthds` bundle works on its own. No configuration, no manifest.
2. **Package** — add a `METHODS.toml` to get exports, visibility, and a globally unique identity.
3. **Dependencies** — add `[dependencies]` to compose with other packages.
4. **Ecosystem** — publish by pushing a tag; [registries](registry.md) index, search, and surface what you published. At the horizon, the [Know-How Graph](../know-how-graph/index.md) makes discovery typed.

Each layer adds capability without breaking the previous one.

## Manifest Discovery

When loading a `.mthds` bundle, a compliant runtime discovers the manifest by walking up the directory tree:

1. Check the bundle's directory for `METHODS.toml`.
2. If not found, move to the parent directory.
3. Stop when `METHODS.toml` is found, an entry named `.git` of any kind is encountered (a directory, a file or a symbolic link), or the filesystem root is reached.
4. If no manifest is found, the bundle is treated as a standalone bundle.

The folder where the manifest is found is the root of the method's files, so handing over a bundle or a subfolder of a package hands over the whole package.

## See Also

- [Specification: Package Directory Structure](../spec/manifest-format.md#package-directory-structure) — normative reference for layout rules.
- [Specification: Method Tree](../spec/method-tree.md) — normative reference for which files make up a method and how they are named.
- [The Manifest](manifest.md) — what goes inside `METHODS.toml`.
- [Specification: Library Crate Format](../spec/library-crate.md) — the resolution artifact a package's library resolves into.
