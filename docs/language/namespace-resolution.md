---
description: "Learn how MTHDS resolves bare, domain-qualified, and package-qualified references to concepts and pipes across bundles."
---

# Namespace Resolution

When a pipe references a concept or another pipe, MTHDS resolves that reference through a well-defined set of rules. Understanding these rules is essential for working with multi-bundle packages and cross-package dependencies.

## Three Forms of Reference

Every reference to a concept or pipe uses one of three forms:

| Form | Syntax | Example |
|------|--------|---------|
| **Bare** | `name` | `ContractClause`, `extract_clause` |
| **Domain-qualified** | `domain_path.name` | `legal.contracts.NonCompeteClause`, `scoring.compute_score` |
| **Package-qualified** | `alias->domain_path.name` | `acme->legal.ContractClause`, `docproc->extraction.extract_text` |

## How References Are Parsed

**Cross-package references** (`->` syntax): The string is split on the first `->`. The left part is the package alias, the right part is parsed as a domain-qualified or bare reference.

**Domain-qualified references** (`.` syntax): The string is split on the **last `.`**. The left part is the domain path, the right part is the local code (concept code or pipe code).

**Disambiguation** between concepts and pipes in a domain-qualified reference relies on casing:

- `snake_case` final segment → pipe code (e.g., `scoring.compute_score`)
- `PascalCase` final segment → concept code (e.g., `scoring.WeightedScore`)

This is unambiguous because concept codes and pipe codes follow mutually exclusive casing conventions.

## Resolution Order for Bare References

### Bare Concept References

When resolving a bare concept code like `ContractClause`:

1. **Native concepts** — check if it matches a native concept code (`Text`, `Image`, etc.). Native concepts always take priority.
2. **Current bundle** — check concepts declared in the same `.mthds` file.
3. **Same domain, other bundles** — if the bundle is part of a package, check concepts in other bundles that declare the same domain.
4. **Error** — if not found in any of the above.

Bare concept references do not fall through to other domains or other packages.

### Bare Pipe References

When resolving a bare pipe code like `extract_clause`:

1. **Current bundle** — check pipes declared in the same `.mthds` file.
2. **Same domain, other bundles** — if the bundle is part of a package, check pipes in other bundles that declare the same domain.
3. **Error** — if not found.

Bare pipe references do not fall through to other domains or other packages.

## Resolution of Domain-Qualified References

When resolving `domain_path.name` (e.g., `legal.contracts.extract_clause`):

1. Look in the named domain within the **current package**.
2. If not found: **error**.

Domain-qualified references are explicit about which domain to look in. They do not fall through to dependencies.

## Resolution of Package-Qualified References

When resolving `alias->domain_path.name` (e.g., `docproc->extraction.extract_text`):

1. Identify the dependency by the alias. The alias must match a key in the `[dependencies]` section of the consuming package's `METHODS.toml`.
2. Look in the named domain of the **resolved dependency package**.
3. If not found: **error**.

**Visibility rules for cross-package pipe references:**

- The referenced pipe must be exported by the dependency package (listed in its `[exports]` section or declared as `main_pipe` in a bundle header).
- If the pipe is not exported, the reference fails with a visibility error.

**Concepts are always public.** No visibility check is needed for cross-package concept references.

## Visibility Within a Package

When a package has a `METHODS.toml` manifest:

- **Same-domain references** — always allowed. A pipe in `legal.contracts` can reference any other pipe in `legal.contracts`.
- **Cross-domain references** (within the same package) — the target pipe must be exported. A pipe in `scoring` referencing `legal.contracts.extract_clause` requires that `extract_clause` is listed in `[exports.legal.contracts]` or is the `main_pipe` of a bundle in that domain.
- **Bare references** — always allowed (they resolve within the same domain).

When no manifest is present (standalone bundle), all pipes are treated as public.

## A Concrete Example

Package A depends on Package B with alias `scoring_lib`.

Package B's manifest (`METHODS.toml`):

```toml
[package]
address = "github.com/mthds/scoring-lib"
version = "0.5.0"
description = "Scoring utilities"

[exports.scoring]
pipes = ["compute_weighted_score"]
```

Package B's bundle (`scoring.mthds`):

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

Package A's bundle (`analysis.mthds`):

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
2. Look up `scoring_lib` in Package A's `[dependencies]` — found.
3. Parse remainder: split on last `.` → domain `scoring`, pipe code `compute_weighted_score`.
4. Look in domain `scoring` of Package B — pipe found.
5. Visibility check: `compute_weighted_score` is in `[exports.scoring]` — accessible.
6. Resolution succeeds.

**If Package A tried `scoring_lib->scoring.internal_helper`:**

Steps 1–4 would succeed (the pipe exists), but the visibility check would fail — `internal_helper` is not in `[exports.scoring]` and is not `main_pipe`. This is a visibility error.

**Cross-package concept references** work the same way but skip the visibility check, since concepts are always public:

```toml
[concept.DetailedScore]
description = "An extended score with additional analysis"
refines     = "scoring_lib->scoring.ScoreResult"
```

## Resolution Flowchart

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

## See Also

- [Specification: Namespace Resolution Rules](../spec/namespace-resolution.md) — the normative, formal definition of all resolution rules.
- [Domains](domains.md) — how domains organize concepts and pipes.
- [The Package System: Exports & Visibility](../packages/exports-visibility.md) — how packages control what they expose.
