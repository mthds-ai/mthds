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

## Package Commands (`mthds pkg`)

Package commands manage the full lifecycle of MTHDS packages: initialization, dependencies, distribution, and discovery.

### `mthds pkg init`

Initialize a `METHODS.toml` package manifest from `.mthds` files in the current directory.

**Usage:**

```
mthds pkg init [--force]
```

**Options:**

| Option | Short | Description |
|--------|-------|-------------|
| `--force` | `-f` | Overwrite an existing `METHODS.toml`. |

The command scans all `.mthds` files recursively, extracts domain and pipe information, and generates a skeleton `METHODS.toml` with a placeholder address and auto-populated exports. Edit the generated file to set the correct address and refine exports.

**Example:**

```bash
mthds pkg init
# Created METHODS.toml with:
#   Domains: 2
#   Total pipes: 7
#   Bundles scanned: 3
#
# Edit METHODS.toml to set the correct address and configure exports.
```

---

### `mthds pkg list`

Display the package manifest for the current directory.

**Usage:**

```
mthds pkg list
```

Walks up from the current directory to find a `METHODS.toml` and displays its contents: package identity, dependencies, and exports.

---

### `mthds pkg add`

Add a dependency to `METHODS.toml`.

**Usage:**

```
mthds pkg add <address> [--alias NAME] [--version CONSTRAINT] [--path LOCAL_PATH]
```

**Arguments:**

| Argument | Description |
|----------|-------------|
| `address` | Package address (e.g., `github.com/mthds/document-processing`). |

**Options:**

| Option | Short | Description |
|--------|-------|-------------|
| `--alias` | `-a` | Dependency alias. Auto-derived from the last path segment if not provided. |
| `--version` | `-v` | Version constraint. Default: `0.1.0`. |
| `--path` | `-p` | Local filesystem path to the dependency (for development). |

**Examples:**

```bash
# Add a remote dependency (alias auto-derived as "document_processing")
mthds pkg add github.com/mthds/document-processing --version "^1.0.0"

# Add with a custom alias
mthds pkg add github.com/acme/legal-tools --alias acme_legal --version "^0.3.0"

# Add a local development dependency
mthds pkg add github.com/team/scoring --path ../scoring-lib --version "^0.5.0"
```

---

### `mthds pkg lock`

Resolve dependencies and generate `methods.lock`.

**Usage:**

```
mthds pkg lock
```

Reads the `[dependencies]` section of `METHODS.toml`, resolves all versions (including transitive dependencies), and writes the lock file. The lock file records exact versions and SHA-256 integrity hashes for reproducible builds.

---

### `mthds pkg install`

Fetch and cache all dependencies from `methods.lock`.

**Usage:**

```
mthds pkg install
```

For each entry in the lock file, checks the local cache (`~/.mthds/packages/`). Missing packages are fetched via Git. After fetching, integrity hashes are verified against the lock file.

---

### `mthds pkg update`

Re-resolve dependencies to latest compatible versions and update `methods.lock`.

**Usage:**

```
mthds pkg update
```

Performs a fresh resolution of all dependencies (ignoring the existing lock file), writes the updated lock file, and displays a diff showing added, removed, and updated packages.

---

### `mthds pkg index`

Build and display the local package index.

**Usage:**

```
mthds pkg index [--cache]
```

**Options:**

| Option | Short | Description |
|--------|-------|-------------|
| `--cache` | `-c` | Index cached packages instead of the current project. |

Displays a summary table showing each package's address, version, description, and counts of domains, concepts, and pipes.

---

### `mthds pkg search`

Search the package index for concepts and pipes.

**Usage:**

```
mthds pkg search <query> [options]
mthds pkg search --accepts <concept> [--produces <concept>]
```

**Arguments:**

| Argument | Description |
|----------|-------------|
| `query` | Search term (case-insensitive substring match). Optional if using `--accepts` or `--produces`. |

**Options:**

| Option | Short | Description |
|--------|-------|-------------|
| `--domain` | `-d` | Filter results to a specific domain. |
| `--concept` | | Show only matching concepts. |
| `--pipe` | | Show only matching pipes. |
| `--cache` | `-c` | Search cached packages instead of the current project. |
| `--accepts` | | Find pipes that accept this concept (type-compatible search). |
| `--produces` | | Find pipes that produce this concept (type-compatible search). |

**Examples:**

```bash
# Text search for concepts and pipes
mthds pkg search "contract"

# Search only pipes in a specific domain
mthds pkg search "extract" --pipe --domain legal.contracts

# Type-compatible search: "What can I do with a Document?"
mthds pkg search --accepts Document

# Type-compatible search: "What produces a NonCompeteClause?"
mthds pkg search --produces NonCompeteClause

# Combined: "What transforms Text into ScoreResult?"
mthds pkg search --accepts Text --produces ScoreResult
```

Type-compatible search uses the [Know-How Graph](../know-how-graph/index.md) to find pipes by their typed signatures. It understands concept refinement: searching for pipes that accept `Text` also finds pipes that accept `NonCompeteClause` (since `NonCompeteClause` refines `Text`).

---

### `mthds pkg inspect`

Display detailed information about a package.

**Usage:**

```
mthds pkg inspect <address> [--cache]
```

**Arguments:**

| Argument | Description |
|----------|-------------|
| `address` | Package address to inspect. |

**Options:**

| Option | Short | Description |
|--------|-------|-------------|
| `--cache` | `-c` | Look in the package cache instead of the current project. |

Displays the package's metadata, domains, concepts (with structure fields and refinement), and pipe signatures (with inputs, outputs, and export status).

**Example:**

```bash
mthds pkg inspect github.com/acme/legal-tools
```

---

### `mthds pkg graph`

Query the Know-How Graph for concept and pipe relationships.

**Usage:**

```
mthds pkg graph --from <concept_id> [--to <concept_id>] [options]
mthds pkg graph --check <pipe_key_a>,<pipe_key_b>
```

**Options:**

| Option | Short | Description |
|--------|-------|-------------|
| `--from` | `-f` | Concept ID — find pipes that accept it. Format: `package_address::concept_ref`. |
| `--to` | `-t` | Concept ID — find pipes that produce it. |
| `--check` | | Two pipe keys comma-separated — check if the output of the first is compatible with an input of the second. |
| `--max-depth` | `-m` | Maximum chain depth when using `--from` and `--to` together. Default: `3`. |
| `--compose` | | Show an MTHDS composition template for discovered chains. Requires both `--from` and `--to`. |
| `--cache` | `-c` | Use cached packages instead of the current project. |

**Examples:**

```bash
# Find all pipes that accept a specific concept
mthds pkg graph --from "__native__::native.Document"

# Find all pipes that produce a specific concept
mthds pkg graph --to "github.com/acme/legal-tools::legal.contracts.NonCompeteClause"

# Find chains from Document to NonCompeteClause (auto-composition)
mthds pkg graph \
  --from "__native__::native.Document" \
  --to "github.com/acme/legal-tools::legal.contracts.NonCompeteClause"

# Same query, but generate an MTHDS snippet for the chain
mthds pkg graph \
  --from "__native__::native.Document" \
  --to "github.com/acme/legal-tools::legal.contracts.NonCompeteClause" \
  --compose

# Check if two pipes are compatible (can be chained)
mthds pkg graph --check "github.com/acme/legal-tools::extract_pages,github.com/acme/legal-tools::analyze_content"
```

When both `--from` and `--to` are provided, the command searches for multi-step pipe chains through the graph, up to `--max-depth` hops. With `--compose`, it generates a ready-to-use MTHDS `PipeSequence` snippet for each discovered chain.

---

### `mthds pkg publish`

Validate that a package is ready for distribution.

**Usage:**

```
mthds pkg publish [--tag]
```

**Options:**

| Option | Description |
|--------|-------------|
| `--tag` | Create a local git tag `v{version}` if validation passes. |

Runs 15 validation checks across seven categories:

| Category | Checks |
|----------|--------|
| **Manifest** | `METHODS.toml` exists and parses; required fields are valid; `mthds_version` constraint is parseable and satisfiable. |
| **Manifest completeness** | Authors and license are present (warnings if missing). |
| **Bundles** | At least one `.mthds` file exists; all bundles parse without error. |
| **Exports** | Every exported pipe actually exists in the scanned bundles. |
| **Visibility** | Cross-domain pipe references respect export rules. |
| **Dependencies** | No wildcard (`*`) version constraints (warning). |
| **Lock file** | `methods.lock` exists and includes all remote dependencies; parses without error. |
| **Git** | Working directory is clean; version tag does not already exist. |

Errors block publishing. Warnings are advisory. With `--tag`, the command creates a `v{version}` git tag locally if all checks pass.

**Example:**

```bash
# Validate readiness
mthds pkg publish

# Validate and create a git tag
mthds pkg publish --tag
```
