---
description: "Reference for METHODS.toml — the MTHDS package manifest that declares identity, version, dependencies, and exports."
---

# The Manifest

`METHODS.toml` is the package manifest — the identity card and dependency declaration for a package. It is a TOML file at the root of the package directory.

## A First Look

```toml
[package]
name          = "nda-analyzer"
address       = "github.com/acme/legal-tools"
display_name  = "Nda Analyzer"
version       = "0.3.0"
description   = "Legal document analysis and contract review methods."
authors       = ["ACME Legal Tech <legal@acme.com>"]
license       = "MIT"
mthds_version = ">=1.0.0"
main_pipe     = "analyze_nda"

[exports.legal]
pipes = ["classify_document"]

[exports.legal.contracts]
pipes = ["extract_clause", "analyze_nda", "compare_contracts"]

[exports.scoring]
pipes = ["compute_weighted_score"]
```

This manifest declares a method called `nda-analyzer` hosted at `github.com/acme/legal-tools`, version `0.3.0`. It exports specific pipes from three domains and designates `analyze_nda` as its main entry point.

## The `[package]` Section

The `[package]` section defines the package's identity:

| Field | Required | Description |
|-------|----------|-------------|
| `name` | Yes | The name of the method. Must be `kebab-case` (matching `[a-z][a-z0-9]*(-[a-z0-9]+)*`), max 25 characters. |
| `address` | Yes | Globally unique identifier. Must follow the hostname/path pattern (e.g., `github.com/org/repo`). |
| `display_name` | No | Human-friendly label for CLI output and registry listings. Cosmetic only — never used as an identifier. Max 128 characters. |
| `version` | Yes | [Semantic version](https://semver.org/) (`MAJOR.MINOR.PATCH`, with optional pre-release and build metadata). |
| `description` | Yes | Human-readable summary of the package's purpose. Must not be empty. |
| `authors` | No | List of author identifiers (e.g., `"Name <email>"`). Default: empty list. |
| `license` | No | [SPDX license identifier](https://spdx.org/licenses/) (e.g., `"MIT"`, `"Apache-2.0"`). |
| `mthds_version` | No | MTHDS standard version constraint. The current standard version is `1.0.0`. |
| `main_pipe` | No | The package's entry-point pipe. Must reference a pipe declared in the `[exports]` section. See [Main Pipe](#main-pipe) below. |

## Package Addresses

The address is the globally unique identifier for a package. It doubles as the fetch location for distribution (see [Distribution](distribution.md)).

Addresses follow a hostname/path pattern:

```
github.com/acme/legal-tools
github.com/mthds/document-processing
gitlab.com/company/internal-methods
```

The address must start with a hostname (containing at least one dot), followed by a `/`, followed by one or more path segments.

Invalid addresses:

```
legal-tools               # No hostname
acme/legal-tools          # No dot in hostname
```

## Version Format

The `version` field must conform to [Semantic Versioning 2.0.0](https://semver.org/):

```
MAJOR.MINOR.PATCH[-pre-release][+build-metadata]
```

Examples: `1.0.0`, `0.3.0`, `2.1.3-beta.1`, `1.0.0-rc.1+build.42`

## Main Pipe

The `main_pipe` field designates the package's primary entry point — the pipe that runs when a user invokes the package by slug or address:

```bash
mthds run method nda-analyzer
mthds run method github.com/acme/legal-tools
```

Both commands above execute the pipe referenced by `main_pipe`.

The value is a `snake_case` pipe code that **must** match a pipe declared in the `[exports]` section:

```toml
main_pipe = "analyze_nda"
```

**Validation rules:**

- The value MUST be a valid `snake_case` pipe code (matching `[a-z][a-z0-9_]*`).
- The referenced pipe **must** be declared in the `[exports]` section. A manifest that sets `main_pipe` to a pipe not present in exports is invalid.
- The field is optional. Packages without a `main_pipe` can still be used as libraries — consumers import specific pipes by their qualified names.

## The `[dependencies]` Section

> **Not yet implemented.** Dependencies between packages are planned but not yet supported.

Dependencies are covered in detail on the [Dependencies](dependencies.md) page.

## The `[exports]` Section

Exports are covered in detail on the [Exports & Visibility](exports-visibility.md) page.

## See Also

- [Specification: METHODS.toml Manifest Format](../spec/manifest-format.md) — normative reference for all fields and validation rules.
- [Dependencies](dependencies.md) — how to declare and manage dependencies.
- [Exports & Visibility](exports-visibility.md) — how to control which pipes are public.
