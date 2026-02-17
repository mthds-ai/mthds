---
description: "Normative specification of the METHODS.toml manifest — package identity, dependencies, exports, and model configuration."
---

# METHODS.toml Manifest Format

The `METHODS.toml` file is the package manifest — the identity card and dependency declaration for an MTHDS package. It MUST be named exactly `METHODS.toml` and MUST be located at the root of the package directory.

## File Encoding and Syntax

`METHODS.toml` MUST be a valid TOML document encoded in UTF-8.

## Top-Level Sections

A `METHODS.toml` file contains up to three top-level sections:

| Section | Required | Description |
|---------|----------|-------------|
| `[package]` | Yes | Package identity and metadata. |
| `[dependencies]` | No | Dependencies on other MTHDS packages. |
| `[exports]` | No | Visibility declarations for pipes. |

## The `[package]` Section

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `address` | string | Yes | Globally unique package identifier. MUST follow the hostname/path pattern. |
| `display_name` | string | No | Human-friendly display label. When provided, MUST NOT be empty or whitespace-only, MUST NOT exceed 128 characters, and MUST NOT contain Unicode control characters (category Cc). Leading and trailing whitespace is stripped. |
| `version` | string | Yes | Package version. MUST be valid [semantic versioning](https://semver.org/) (`MAJOR.MINOR.PATCH`, with optional pre-release and build metadata). |
| `description` | string | Yes | Human-readable summary of the package's purpose. MUST NOT be empty. |
| `authors` | array of strings | No | List of author identifiers (e.g., `"Name <email>"`). Default: empty list. |
| `license` | string | No | SPDX license identifier (e.g., `"MIT"`, `"Apache-2.0"`). |
| `mthds_version` | string | No | MTHDS standard version constraint. If set, MUST be a valid version constraint. |

### Address Format

The package address is the globally unique identifier for the package. It doubles as the fetch location for VCS-based distribution.

**Pattern:** `^[a-zA-Z0-9._-]+\.[a-zA-Z0-9._-]+/[a-zA-Z0-9._/-]+$`

In plain language: the address MUST start with a hostname (containing at least one dot), followed by a `/`, followed by one or more path segments.

**Examples of valid addresses:**

```
github.com/acme/legal-tools
github.com/mthds/document-processing
gitlab.com/company/internal-methods
```

**Examples of invalid addresses:**

```
legal-tools                     # No hostname
acme/legal-tools                # No dot in hostname
```

### Display Name

The optional `display_name` field provides a human-friendly label for the package. It appears in CLI output, registry listings, and error messages. It is cosmetic only — the `address` remains the sole canonical identifier.

**Constraints:**

- MUST NOT be empty or whitespace-only when provided.
- MUST NOT exceed 128 characters (after leading/trailing whitespace is stripped).
- MUST NOT contain Unicode control characters (Unicode general category `Cc`).
- Emojis and other Unicode characters are allowed.
- Leading and trailing whitespace is stripped by a compliant implementation.

**Example:**

```toml
[package]
address      = "github.com/acme/legal-tools"
display_name = "Legal Tools"
```

### Version Format

The `version` field MUST conform to [Semantic Versioning 2.0.0](https://semver.org/):

```
MAJOR.MINOR.PATCH[-pre-release][+build-metadata]
```

**Examples:** `1.0.0`, `0.3.0`, `2.1.3-beta.1`, `1.0.0-rc.1+build.42`

### mthds_version Constraints

The `mthds_version` field, if present, declares which versions of the MTHDS standard this package is compatible with. It uses version constraint syntax (see [Version Constraint Syntax](#version-constraint-syntax)).

The current MTHDS standard version is `1.0.0`.

## The `[dependencies]` Section

Each entry in `[dependencies]` declares a dependency on another MTHDS package. The key is the **alias** — a `snake_case` identifier used in cross-package references (`->` syntax).

```toml
[dependencies]
docproc     = { address = "github.com/mthds/document-processing", version = "^1.0.0" }
scoring_lib = { address = "github.com/mthds/scoring-lib", version = "^0.5.0" }
```

### Dependency Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `address` | string | Yes | The dependency's package address. MUST follow the hostname/path pattern. |
| `version` | string | Yes | Version constraint for the dependency (see [Version Constraint Syntax](#version-constraint-syntax)). |
| `path` | string | No | Local filesystem path to the dependency, resolved relative to the manifest directory. For development-time workflows. |

### Alias Rules

- The alias (the TOML key) MUST be `snake_case`, matching `[a-z][a-z0-9_]*`.
- All aliases within a single `[dependencies]` section MUST be unique.
- The alias is used in cross-package references: `alias->domain.name`.

### The `path` Field

When `path` is set, the dependency is resolved from the local filesystem instead of being fetched via VCS. This supports development-time workflows where packages are co-located on disk, similar to Cargo's `path` dependencies or Go's `replace` directives.

- The path is resolved relative to the directory containing `METHODS.toml`.
- Local path dependencies are NOT resolved transitively — only the root package's local paths are honored.
- Local path dependencies are excluded from the lock file.

**Example:**

```toml
[dependencies]
scoring = { address = "github.com/mthds/scoring-lib", version = "^0.5.0", path = "../scoring-lib" }
```

### Version Constraint Syntax

Version constraints specify which versions of a dependency are acceptable.

| Form | Syntax | Example | Meaning |
|------|--------|---------|---------|
| Exact | `MAJOR.MINOR.PATCH` | `1.0.0` | Exactly this version. |
| Caret | `^MAJOR.MINOR.PATCH` | `^1.0.0` | Compatible release (same major version). |
| Tilde | `~MAJOR.MINOR.PATCH` | `~1.0.0` | Approximately compatible (same major.minor). |
| Greater-or-equal | `>=MAJOR.MINOR.PATCH` | `>=1.0.0` | This version or newer. |
| Less-than | `<MAJOR.MINOR.PATCH` | `<2.0.0` | Older than this version. |
| Greater | `>MAJOR.MINOR.PATCH` | `>1.0.0` | Newer than this version. |
| Less-or-equal | `<=MAJOR.MINOR.PATCH` | `<=2.0.0` | This version or older. |
| Equal | `==MAJOR.MINOR.PATCH` | `==1.0.0` | Exactly this version. |
| Not-equal | `!=MAJOR.MINOR.PATCH` | `!=1.0.0` | Any version except this one. |
| Compound | constraint `, ` constraint | `>=1.0.0, <2.0.0` | Both constraints must be satisfied. |
| Wildcard | `*`, `MAJOR.*`, `MAJOR.MINOR.*` | `1.*` | Any version matching the prefix. |

Partial versions are allowed: `1.0` is equivalent to `1.0.*`.

## The `[exports]` Section

The `[exports]` section controls which pipes are visible to consumers of the package.

**Default visibility rules:**

- **Concepts are always public.** Concepts are vocabulary — they are always accessible from outside the package.
- **Pipes are private by default.** A pipe not listed in `[exports]` is an implementation detail, invisible to consumers.
- **`main_pipe` is auto-exported.** If a bundle declares a `main_pipe`, that pipe is automatically part of the public API, regardless of whether it appears in `[exports]`.

### Exports Table Structure

The `[exports]` section uses nested TOML tables that mirror the domain hierarchy. The domain path maps directly to the TOML table path:

```toml
[exports.legal]
pipes = ["classify_document"]

[exports.legal.contracts]
pipes = ["extract_clause", "analyze_nda", "compare_contracts"]

[exports.scoring]
pipes = ["compute_weighted_score"]
```

Each leaf table contains:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `pipes` | array of strings | Yes | Pipe codes that are public from this domain. Each entry MUST be a valid pipe code (`snake_case`). |

**Validation rules:**

- Domain paths in `[exports]` MUST be valid domain codes.
- Domain paths in `[exports]` MUST NOT start with a reserved domain segment (`native`, `mthds`, `pipelex`).
- A domain MAY have both a `pipes` list and sub-domain tables (e.g., `[exports.legal]` with `pipes` AND `[exports.legal.contracts]`).

### Standalone Bundles (No Manifest)

A `.mthds` file without a `METHODS.toml` manifest is a standalone bundle. It behaves as an implicit local package with:

- No dependencies (beyond native concepts).
- All pipes treated as public (no visibility restrictions).
- No package address (not distributable).

This preserves the "single file = working method" experience for learning, prototyping, and simple projects.

## Package Directory Structure

A package is a directory containing a `METHODS.toml` manifest and one or more `.mthds` bundle files. The directory layout follows a progressive enhancement principle — start minimal, add structure as needed.

**Minimal package:**

```
my-tool/
├── METHODS.toml
└── main.mthds
```

**Full package:**

```
legal-tools/
├── METHODS.toml
├── methods.lock
├── general_legal.mthds
├── contract_analysis.mthds
├── shareholder_agreements.mthds
├── scoring.mthds
├── README.md
└── LICENSE
```

**Rules:**

- `METHODS.toml` MUST be at the directory root.
- `methods.lock` MUST be at the directory root, alongside `METHODS.toml`.
- `.mthds` files MAY be at the root or in subdirectories. A compliant implementation MUST discover all `.mthds` files recursively.
- A single directory SHOULD contain one package. Multiple packages in subdirectories with distinct addresses are possible but outside the scope of this specification.

## Manifest Discovery

When loading a `.mthds` bundle, a compliant implementation SHOULD discover the manifest by walking up from the bundle file's directory:

1. Check the current directory for `METHODS.toml`.
2. If not found, move to the parent directory.
3. Stop when `METHODS.toml` is found, a `.git` directory is encountered, or the filesystem root is reached.
4. If no manifest is found, the bundle is treated as a standalone bundle (no package).

## Complete Manifest Example

```toml
[package]
address       = "github.com/acme/legal-tools"
display_name  = "Legal Tools"
version       = "0.3.0"
description   = "Legal document analysis and contract review methods."
authors       = ["ACME Legal Tech <legal@acme.com>"]
license       = "MIT"
mthds_version = ">=1.0.0"

[dependencies]
docproc     = { address = "github.com/mthds/document-processing", version = "^1.0.0" }
scoring_lib = { address = "github.com/mthds/scoring-lib", version = "^0.5.0" }

[exports.legal]
pipes = ["classify_document"]

[exports.legal.contracts]
pipes = ["extract_clause", "analyze_nda", "compare_contracts"]

[exports.scoring]
pipes = ["compute_weighted_score"]
```
