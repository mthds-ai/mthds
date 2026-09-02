---
description: "Reference for the mthds CLI — commands for validating bundles, running pipes, and managing the full package lifecycle."
---

# CLI Reference

The `mthds` CLI is the official command-line tool for working with MTHDS packages. It covers validation, execution, and the full package management lifecycle.

## Core Commands

### `mthds validate`

Validate `.mthds` files, individual pipes, or an entire project.

**Usage:**

```
mthds validate <target>
mthds validate --bundle <file.mthds>
mthds validate --bundle <file.mthds> --pipe <pipe_code>
mthds validate --all
```

**Arguments:**

| Argument | Description |
|----------|-------------|
| `target` | A pipe code or a bundle file path (`.mthds`). Auto-detected based on file extension. |

**Options:**

| Option | Short | Description |
|--------|-------|-------------|
| `--pipe` | | Pipe code to validate. Optional when using `--bundle`. |
| `--bundle` | | Bundle file path (`.mthds`). Validates all pipes in the bundle. |
| `--all` | `-a` | Validate all pipes in all loaded libraries. |
| `--library-dir` | `-L` | Directory to search for `.mthds` files. Can be specified multiple times. |

**Examples:**

```bash
# Validate a single pipe by code
mthds validate extract_clause

# Validate a bundle file
mthds validate contract_analysis.mthds

# Validate a specific pipe within a bundle
mthds validate --bundle contract_analysis.mthds --pipe extract_clause

# Validate all pipes in the project
mthds validate --all
```

---

### `mthds run`

Execute a method. Loads the bundle, resolves dependencies, and runs the specified pipe.

**Usage:**

```
mthds run <target>
mthds run --bundle <file.mthds>
mthds run --bundle <file.mthds> --pipe <pipe_code>
mthds run <directory/>
```

**Arguments:**

| Argument | Description |
|----------|-------------|
| `target` | A pipe code, a bundle file path (`.mthds`), or a pipeline directory. Auto-detected. |

**Options:**

| Option | Short | Description |
|--------|-------|-------------|
| `--pipe` | | Pipe code to run. If omitted when using `--bundle`, runs the bundle's `main_pipe`. |
| `--bundle` | | Bundle file path (`.mthds`). |
| `--inputs` | `-i` | Path to a JSON file with input data. |
| `--output-dir` | `-o` | Base directory for all outputs. Default: `results`. |
| `--dry-run` | | Run in dry mode (no actual inference calls). |
| `--library-dir` | `-L` | Directory to search for `.mthds` files. Can be specified multiple times. |

**Examples:**

```bash
# Run a bundle's main pipe
mthds run joke_generation.mthds

# Run a specific pipe within a bundle
mthds run --bundle contract_analysis.mthds --pipe extract_clause

# Run with input data
mthds run extract_clause --inputs data.json

# Run a pipeline directory (auto-detects bundle and inputs)
mthds run pipeline_01/

# Dry run (no inference calls)
mthds run joke_generation.mthds --dry-run
```

When a directory is provided as the target, `mthds run` auto-detects the `.mthds` bundle file and an optional `inputs.json` file within it.

---

## Package Commands (`mthds package`)

Package commands manage the lifecycle of MTHDS packages: manifest creation, inspection, validation, and the dependency lifecycle.

### `mthds package init`

Create a `METHODS.toml` package manifest in the current directory.

**Usage:**

```
mthds package init [--force]
```

**Options:**

| Option | Short | Description |
|--------|-------|-------------|
| `--force` | `-f` | Overwrite an existing `METHODS.toml`. |

The command generates a skeleton `METHODS.toml`. Edit the generated file to set the package `name`, the correct `address`, and your `[exports]` surface (see [Create a Package](../guides/create-package.md)).

---

### `mthds package list`

Display the package manifest for the current directory.

**Usage:**

```
mthds package list
```

Walks up from the current directory to find a `METHODS.toml` and displays its contents: package identity, dependencies, and exports.

---

### `mthds package validate`

Validate the package manifest.

**Usage:**

```
mthds package validate
```

Checks the manifest against the [validation rules](../implementers/validation-rules.md#stage-6-manifest-validation): identity fields, dependency declarations, and the `[exports]` surface.

---

## Dependency Lifecycle Commands

!!! note "Implementation status"
    The dependency lifecycle commands below are committed design; see the [normative status note](../spec/manifest-format.md#the-dependencies-section) for how conformance is asserted as implementations land.

### `mthds package add`

Add a dependency to `METHODS.toml`, recording its latest version as the floor, then re-lock.

**Usage:**

```
mthds package add <address> [--alias NAME] [--version CONSTRAINT] [--path LOCAL_PATH]
```

**Arguments:**

| Argument | Description |
|----------|-------------|
| `address` | Package address (e.g., `github.com/mthds/document-processing`). |

**Options:**

| Option | Short | Description |
|--------|-------|-------------|
| `--alias` | `-a` | Dependency alias. Auto-derived from the last path segment if not provided. |
| `--version` | `-v` | Version constraint. Defaults to the latest available version, recorded as the floor. |
| `--path` | `-p` | Local filesystem path to the dependency (for development). |

**Examples:**

```bash
# Add a remote dependency (alias auto-derived as "document_processing")
mthds package add github.com/mthds/document-processing --version "^1.0.0"

# Add with a custom alias
mthds package add github.com/acme/legal-tools --alias acme_legal --version "^0.3.0"

# Add a local development dependency
mthds package add github.com/team/scoring --path ../scoring-lib --version "^0.5.0"
```

---

### `mthds package lock`

Resolve dependencies and generate `methods.lock`.

**Usage:**

```
mthds package lock
```

Reads the `[dependencies]` section of `METHODS.toml`, resolves all versions with [Minimum Version Selection](../packages/version-resolution.md) (including transitive dependencies), and writes the lock file: exact versions, byte hashes, crate fingerprints, sources, and commits. Because resolution is deterministic from the manifests, re-running `lock` against unchanged manifests reproduces the same file.

---

### `mthds package install`

Fetch and verify all dependencies pinned by `methods.lock`.

**Usage:**

```
mthds package install
```

For each entry in the lock file, checks the global cache (`~/.mthds/packages/`), fetches what is missing via Git, verifies the byte hash against the lock (a mismatch is a hard failure), and materializes each dependency into the project-local cache (see [Distribution: The Two Caches](../packages/distribution.md#the-two-caches)).

---

### `mthds package update`

Raise the dependency floors in `METHODS.toml` to the latest available versions, then re-lock.

**Usage:**

```
mthds package update
```

Under MVS, nothing upgrades on its own — updating is a deliberate manifest edit. The command raises the floors, writes the updated lock file, and displays what moved (see [Adding and Updating](../packages/version-resolution.md#adding-and-updating-deliberate-adoption)).
