---
description: "Formal rules for resolving bare, domain-qualified, and package-qualified references in MTHDS bundles and packages."
---

# Namespace Resolution Rules

This page defines the formal rules for resolving references to concepts and pipes across bundles, domains, and packages.

## Reference Syntax Overview

All references to concepts and pipes in MTHDS follow a uniform three-tier syntax:

| Tier | Syntax | Example (concept) | Example (pipe) |
|------|--------|--------------------|----------------|
| Bare | `name` | `ContractClause` | `extract_clause` |
| Domain-qualified | `domain_path.name` | `legal.contracts.NonCompeteClause` | `legal.contracts.extract_clause` |
| Package-qualified | `alias->domain_path.name` | `acme->legal.ContractClause` | `docproc->extraction.extract_text` |

## Parsing Rules

### Splitting Cross-Package References

If the reference string contains `->`, it is a cross-package reference. The string is split on the first `->`:

- Left part: the package alias.
- Right part: the remainder (a domain-qualified or bare reference).

The alias MUST be `snake_case`. The remainder is parsed as a domain-qualified or bare reference.

### Splitting Domain-Qualified References

For the remainder (or the entire string if no `->` is present), the reference is parsed by splitting on the **last `.`** (dot):

- Left part: the domain path.
- Right part: the local code (concept code or pipe code).

If no `.` is present, the reference is a bare name with no domain qualification.

**Examples:**

| Reference | Domain Path | Local Code | Type |
|-----------|-------------|------------|------|
| `extract_clause` | *(none)* | `extract_clause` | Bare pipe |
| `NonCompeteClause` | *(none)* | `NonCompeteClause` | Bare concept |
| `scoring.compute_score` | `scoring` | `compute_score` | Domain-qualified pipe |
| `legal.contracts.NonCompeteClause` | `legal.contracts` | `NonCompeteClause` | Domain-qualified concept |
| `docproc->extraction.extract_text` | `extraction` (in package `docproc`) | `extract_text` | Package-qualified pipe |

### Disambiguation: Concept vs. Pipe

When parsing a domain-qualified reference, the casing of the local code (the segment after the last `.`) determines whether it is a concept or a pipe:

- `PascalCase` (`[A-Z][a-zA-Z0-9]*`) → concept code.
- `snake_case` (`[a-z][a-z0-9_]*`) → pipe code.

This disambiguation is unambiguous because concept codes and pipe codes follow mutually exclusive casing conventions.

## Domain Path Validation

Each segment of a domain path MUST be `snake_case`:

- Match pattern: `[a-z][a-z0-9_]*`
- Segments are separated by `.`
- No leading, trailing, or consecutive dots

## Resolution Order for Bare Concept References

When resolving a bare concept code (no domain qualifier, no package prefix):

1. **Native concepts** — check if the code matches a native concept code (`Text`, `Image`, `Document`, `Html`, `TextAndImages`, `Number`, `ImgGenPrompt`, `Page`, `JSON`, `Dynamic`, `Anything`). Native concepts always take priority.
2. **Current bundle** — check concepts declared in the same `.mthds` file.
3. **Same domain, other bundles** — if the bundle is part of a package, check concepts in other bundles that declare the same domain.
4. **Error** — if not found in any of the above, the reference is invalid.

Bare concept references do NOT fall through to other domains or other packages.

## Resolution Order for Bare Pipe References

When resolving a bare pipe code (no domain qualifier, no package prefix):

1. **Current bundle** — check pipes declared in the same `.mthds` file.
2. **Same domain, other bundles** — if the bundle is part of a package, check pipes in other bundles that declare the same domain.
3. **Error** — if not found, the reference is invalid.

Bare pipe references do NOT fall through to other domains or other packages.

## Resolution of Domain-Qualified References

When resolving `domain_path.name` (no package prefix):

1. Look in the named domain within the **current package**.
2. If not found: **error**. Domain-qualified references do not fall through to dependencies.

This applies to both concept and pipe references.

## Resolution of Package-Qualified References

When resolving `alias->domain_path.name`:

1. Identify the dependency by the alias. The alias MUST match a key in the `[dependencies]` section of the consuming package's `METHODS.toml`.
2. Look in the named domain of the **resolved dependency package**.
3. If not found: **error**.

**Visibility constraints for cross-package pipe references:**

- The referenced pipe MUST be exported by the dependency package (listed in its `[exports]` section or declared as `main_pipe` in its bundle header).
- If the pipe is not exported, the reference is a visibility error.

**Visibility for cross-package concept references:**

- Concepts are always public. No visibility check is needed for cross-package concept references.

## Visibility Rules (Intra-Package)

Within a package that has a `METHODS.toml` manifest:

- **Same-domain references** — always allowed. A pipe in domain `legal.contracts` can reference any other pipe in `legal.contracts` without restriction.
- **Cross-domain references** (within the same package) — the target pipe MUST be exported. A pipe in domain `scoring` referencing `legal.contracts.extract_clause` requires that `extract_clause` is listed in `[exports.legal.contracts]` (or is the `main_pipe` of a bundle in `legal.contracts`).
- **Bare references** — always allowed at the visibility level (they resolve within the same domain).

When no manifest is present (standalone bundle), all pipes are treated as public.

## Reserved Domains

The following domain names are reserved at the first segment level:

| Domain | Owner | Purpose |
|--------|-------|---------|
| `native` | MTHDS standard | Built-in concept types. |
| `mthds` | MTHDS standard | Reserved for future standard extensions. |
| `pipelex` | Reference implementation | Reserved for the reference implementation. |

**Enforcement points:**

- A compliant implementation MUST reject `METHODS.toml` exports that use a reserved domain path.
- A compliant implementation MUST reject bundles that declare a domain starting with a reserved segment when the bundle is part of a package.
- A compliant implementation MUST reject packages at publish time if any bundle uses a reserved domain.

The `native` domain is the only reserved domain with active semantics: it serves as the namespace for native concepts (`native.Text`, `native.Image`, etc.).

## Package Namespace Isolation

Two packages MAY declare the same domain name (e.g., both declare `domain = "recruitment"`). Their concepts and pipes are completely independent — there is no merging of namespaces across packages.

Within a single package, bundles that share the same domain DO merge their namespace. Concept or pipe code collisions within the same package and same domain are errors.

## Conflict Rules

| Scope | Conflict type | Result |
|-------|--------------|--------|
| Same bundle | Duplicate concept code | TOML parse error (duplicate key). |
| Same bundle | Duplicate pipe code | TOML parse error (duplicate key). |
| Same domain, different bundles (same package) | Duplicate concept code | Error at load time. |
| Same domain, different bundles (same package) | Duplicate pipe code | Error at load time. |
| Different domains (same package) | Same concept or pipe code | No conflict — different namespaces. |
| Different packages | Same domain and same concept/pipe code | No conflict — package isolation. |

## Version Resolution Strategy

When resolving dependency versions, a compliant implementation SHOULD use **Minimum Version Selection** (MVS), following Go's approach:

1. Collect all version constraints for a given package address from all dependents (direct and transitive).
2. List all available versions (from VCS tags).
3. Sort versions in ascending order.
4. Select the **minimum** version that satisfies **all** constraints simultaneously.

If no version satisfies all constraints, the resolution fails with an error.

**Properties of MVS:**

- **Deterministic** — the same set of constraints always produces the same result.
- **Reproducible** — no dependency on a "latest" query or timestamp.
- **Simple** — no backtracking solver needed.

## Transitive Dependency Resolution

Dependencies are resolved transitively with the following rules:

- **Remote dependencies** are resolved recursively. If Package A depends on Package B, and Package B depends on Package C, then Package C is also resolved.
- **Local path dependencies** are resolved at the root level only. They are NOT resolved transitively.
- **Cycle detection** — if a dependency is encountered while it is already on the resolution stack, the resolver MUST report a cycle error.
- **Diamond dependencies** — when the same package address is required by multiple dependents with different version constraints, MVS selects the minimum version satisfying all constraints simultaneously.

## Fetching Remote Dependencies

Package addresses map to Git clone URLs by the following rule:

1. Prepend `https://`.
2. Append `.git` (if not already present).

For example: `github.com/acme/legal-tools` → `https://github.com/acme/legal-tools.git`

The resolution chain for fetching a dependency is:

1. **Local path** — if the dependency has a `path` field in `METHODS.toml`, resolve from the local filesystem.
2. **Local cache** — check `~/.mthds/packages/{address}/{version}/` for a cached copy.
3. **VCS fetch** — clone the repository at the resolved version tag using `git clone --depth 1 --branch {tag}`.

Version tags in the remote repository MAY use a `v` prefix (e.g., `v1.0.0`). The prefix is stripped during version parsing.

## Cache Layout

The default package cache is located at `~/.mthds/packages/`. Cached packages are stored at:

```
~/.mthds/packages/{address}/{version}/
```

For example:

```
~/.mthds/packages/github.com/acme/legal-tools/1.0.0/
```

The `.git` directory is removed from cached copies.

## Cross-Package Reference Examples

The following examples illustrate the complete reference resolution for cross-package scenarios.

**Setup:** Package A depends on Package B with alias `scoring_lib`.

Package B (`METHODS.toml`):

```toml
[package]
address = "github.com/mthds/scoring-lib"
version = "0.5.0"
description = "Scoring utilities"

[exports.scoring]
pipes = ["compute_weighted_score"]
```

Package B (`scoring.mthds`):

```toml
domain    = "scoring"
main_pipe = "compute_weighted_score"

[concept.ScoreResult]
description = "A weighted score result"

[pipe.compute_weighted_score]
type        = "PipeLLM"
description = "Compute a weighted score"
inputs      = { item = "Text" }
output      = "ScoreResult"
prompt      = "Compute a weighted score for: $item"

[pipe.internal_helper]
type        = "PipeLLM"
description = "Internal helper (not exported)"
inputs      = { data = "Text" }
output      = "Text"
prompt      = "Process: $data"
```

Package A (`analysis.mthds`):

```toml
domain = "analysis"

[pipe.analyze_item]
type        = "PipeSequence"
description = "Analyze using scoring dependency"
inputs      = { item = "Text" }
output      = "Text"
steps = [
    { pipe = "scoring_lib->scoring.compute_weighted_score", result = "score" },
    { pipe = "summarize", result = "summary" },
]
```

**Resolution of `scoring_lib->scoring.compute_weighted_score`:**

1. `->` detected — split into alias `scoring_lib` and remainder `scoring.compute_weighted_score`.
2. Look up `scoring_lib` in Package A's `[dependencies]` — found, resolves to `github.com/mthds/scoring-lib`.
3. Parse remainder: split on last `.` → domain `scoring`, pipe code `compute_weighted_score`.
4. Look in domain `scoring` of the resolved Package B — pipe found.
5. Visibility check: `compute_weighted_score` is in `[exports.scoring]` pipes — accessible.
6. Resolution succeeds.

**If Package A tried `scoring_lib->scoring.internal_helper`:**

1. Steps 1–4 as above — pipe `internal_helper` is found in Package B's `scoring` domain.
2. Visibility check: `internal_helper` is NOT in `[exports.scoring]` and is NOT `main_pipe` — **visibility error**.

**Cross-package concept reference:**

```toml
[concept.DetailedScore]
description = "An extended score with additional analysis"
refines     = "scoring_lib->scoring.ScoreResult"
```

This refines `ScoreResult` from Package B. Concepts are always public, so no visibility check is needed.

## Validation Rule Summary

This section consolidates the validation rules scattered throughout this specification into a single reference.

### Bundle-Level Validation

1. The file MUST be valid TOML.
2. `domain` MUST be present and MUST be a valid domain code.
3. `main_pipe`, if present, MUST be `snake_case` and MUST reference a pipe defined in the same bundle.
4. Concept codes MUST be `PascalCase`.
5. Concept codes MUST NOT match any native concept code.
6. Pipe codes MUST be `snake_case`.
7. `refines` and `structure` MUST NOT both be set on the same concept.
8. Local concept references (bare or same-domain) MUST resolve to a declared concept in the bundle or a native concept.
9. Same-domain pipe references MUST resolve to a declared pipe in the bundle.
10. Cross-package references (`->` syntax) are deferred to package-level validation.

### Concept Structure Field Validation

1. `description` MUST be present on every field.
2. If `type` is omitted, `choices` MUST be non-empty.
3. `type = "dict"` requires both `key_type` and `value_type`.
4. `type = "concept"` requires `concept_ref` and forbids `default_value`.
5. `type = "list"` with `item_type = "concept"` requires `item_concept_ref`.
6. `concept_ref` MUST NOT be set unless `type = "concept"`.
7. `item_concept_ref` MUST NOT be set unless `item_type = "concept"`.
8. `default_value` type MUST match the declared `type`.
9. If `choices` is set and `default_value` is present, `default_value` MUST be in `choices`.
10. Field names MUST NOT start with `_`.

### Pipe Validation (Type-Specific)

1. **PipeLLM**: All prompt variables MUST have matching inputs. All inputs MUST be used.
2. **PipeFunc**: `function_name` MUST be present.
3. **PipeImgGen**: `prompt` MUST be present. All prompt variables MUST have matching inputs.
4. **PipeExtract**: Exactly one input MUST be declared. `output` MUST be `"Page[]"`.
5. **PipeCompose**: Exactly one of `template` or `construct` MUST be present. Output MUST NOT use multiplicity.
6. **PipeSequence**: `steps` MUST have at least one entry.
7. **PipeParallel**: At least one of `add_each_output` or `combined_output` MUST be set.
8. **PipeCondition**: Exactly one of `expression_template` or `expression` MUST be present. `outcomes` MUST have at least one entry.
9. **PipeBatch**: `input_list_name` MUST be in `inputs`. `input_item_name` MUST NOT equal `input_list_name` or any `inputs` key.

### Package-Level Validation

1. `[package]` section MUST be present in `METHODS.toml`.
2. `address` MUST match the hostname/path pattern.
3. `version` MUST be valid semver.
4. `description` MUST NOT be empty.
5. All dependency aliases MUST be unique.
6. All dependency aliases MUST be `snake_case`.
7. All dependency addresses MUST match the hostname/path pattern.
8. All dependency version constraints MUST be valid.
9. Domain paths in `[exports]` MUST NOT use reserved domains.
10. All pipe codes in `[exports]` MUST be valid `snake_case`.
11. Cross-package references MUST reference known dependency aliases.
12. Cross-package pipe references MUST target exported pipes.
13. Bundles MUST NOT use reserved domains as their first segment.

### Lock File Validation

1. Each entry's `version` MUST be valid semver.
2. Each entry's `hash` MUST match `sha256:[0-9a-f]{64}`.
3. Each entry's `source` MUST start with `https://`.

## Summary: Reference Resolution Flowchart

Given a reference string `R`:

```
1. Does R contain "->"?
   YES → Split into (alias, remainder).
         Look up alias in [dependencies].
         Parse remainder as domain-qualified or bare ref.
         Resolve in the dependency's namespace.
         For pipes: check export visibility.
   NO  → Continue to step 2.

2. Does R contain "."?
   YES → Split on last "." into (domain_path, local_code).
         Resolve in domain_path within current package.
   NO  → R is a bare name. Continue to step 3.

3. Is R a concept code (PascalCase)?
   YES → Check native concepts → current bundle → same domain.
   NO  → R is a pipe code (snake_case).
         Check current bundle → same domain.

4. Not found? → Error.
```
