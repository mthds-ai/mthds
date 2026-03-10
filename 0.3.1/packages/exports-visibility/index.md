# Exports & Visibility

When a bundle is part of a package, not every pipe needs to be visible to consumers. The `[exports]` section of `METHODS.toml` controls which pipes are part of the public API.

## Default Visibility Rules

Three rules govern visibility:

- **Concepts are always public.** Concepts are vocabulary — they are always accessible from outside the package.
- **Pipes are private by default.** A pipe not listed in `[exports]` is an implementation detail, invisible to consumers.
- **`main_pipe` must be exported.** If a package declares a `main_pipe`, that pipe MUST appear in the `[exports]` section.

## Declaring Exports

The `[exports]` section uses nested TOML tables that mirror the domain hierarchy. The domain path maps directly to the TOML table path:

```toml
[exports.legal]
pipes = ["classify_document"]

[exports.legal.contracts]
pipes = ["extract_clause", "analyze_nda", "compare_contracts"]

[exports.scoring]
pipes = ["compute_weighted_score"]
```

Each table contains a `pipes` list — the pipe codes that are public from that domain. A domain can have both a `pipes` list and sub-domain tables (e.g., `[exports.legal]` with `pipes` and `[exports.legal.contracts]`).

## How Visibility Works in Practice

Consider a package with two domains and this manifest:

```toml
[exports.scoring]
pipes = ["compute_weighted_score"]
```

**Bundles in the `scoring` domain** can reference any pipe within `scoring` freely — same-domain references are always allowed.

**Bundles in other domains** (say, `analysis`) can reference `scoring.compute_weighted_score` because it is exported. They cannot reference `scoring.internal_helper` because it is not in the exports list.

**External packages** that depend on this package follow the same rule: only exported pipes are accessible via [cross-package references](cross-package-references.md).

## Intra-Package Visibility Summary

| Reference type | Allowed? |
|---------------|----------|
| Bare references (same bundle or same domain) | Always |
| Cross-domain references to exported pipes | Yes |
| Cross-domain references to non-exported pipes | No — visibility error |

## Standalone Bundles

When no manifest is present (standalone bundle), all pipes are treated as public. Visibility restrictions only apply when a `METHODS.toml` exists.

## Reserved Domains in Exports

Domain paths in `[exports]` must not start with a reserved domain segment (`native`, `mthds`, `pipelex`). A manifest with `[exports.native]` or `[exports.pipelex.utils]` is invalid.

## See Also

- [Specification: The `[exports]` Section](../spec/manifest-format.md#the-exports-section) — normative reference.
- [Namespace Resolution](../language/namespace-resolution.md) — how visibility interacts with reference resolution.
