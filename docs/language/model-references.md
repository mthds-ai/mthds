---
description: "Specify which AI model a pipe uses with MTHDS model references — direct, aliased, class-based, and waterfall resolution."
---

# Model References

Model references tell pipes which AI model to use. Every `PipeLLM`, `PipeImgGen`, and `PipeExtract` accepts an optional `model` field — a string that identifies the model and, depending on its prefix, how that model is configured.

## At a Glance

MTHDS defines four forms of model reference, distinguished by a single-character prefix:

| Prefix | Kind | Example | Purpose |
|--------|------|---------|---------|
| `@` | Alias | `@best-claude` | Simple name-to-model-handle mapping. |
| `$` | Preset | `$writing-factual` | Model handle bundled with parameters (temperature, quality, etc.). |
| `~` | Waterfall | `~fallback-chain` | Ordered fallback list for resilience. |
| *(none)* | Handle | `claude-4.5-sonnet` | Direct model identifier. |

All four forms apply uniformly to all pipe types that accept a `model` field — there is no prefix reserved for a specific operator.

## Aliases (`@`)

An alias maps a short, memorable name to a specific model handle.

```toml
[pipe.extract_cv]
type        = "PipeExtract"
description = "Extract text content from a CV PDF document"
inputs      = { cv_pdf = "Document" }
output      = "Page[]"
model       = "@default-text-from-pdf"
```

An alias is a pure name-to-handle mapping. Use aliases when you want a readable name but have no need to override model parameters.

## Presets (`$`)

A preset bundles a model handle with extra parameters, letting method authors express *how* a model should behave without hardcoding provider-specific tuning. A preset can reference an alias as its underlying handle.

```toml
[pipe.analyze_cv]
type        = "PipeLLM"
description = "Analyze a CV to extract key professional information"
output      = "CVAnalysis"
model       = "$writing-factual"
prompt      = "Analyze the following CV: @cv_pages"

[pipe.analyze_cv.inputs]
cv_pages = "Page"
```

The `$writing-factual` preset might resolve to a specific model handle with a low temperature and deterministic sampling — but the bundle author does not need to know those details. Presets decouple *intent* ("factual writing") from *implementation* ("claude-4.6-opus at temperature 0.1"). A preset can also carry parameters like `reasoning_effort` — for instance, a `$deep-analysis` preset might set `reasoning_effort = "high"` to enable extended reasoning.

## Waterfalls (`~`)

A waterfall defines an ordered fallback list of model handles. The runtime tries each model in sequence until one succeeds, providing resilience against model unavailability.

```toml
[pipe.generate_summary]
type        = "PipeLLM"
description = "Generate a summary with fallback models"
output      = "Text"
model       = "~summary-fallback"
prompt      = "Summarize the following: @document"

[pipe.generate_summary.inputs]
document = "Text"
```

The `~summary-fallback` waterfall might try a primary model first, then fall back to a secondary model if the primary is unavailable. This is useful for production methods that must remain operational even when a specific model provider has an outage.

## Handles (bare string)

A bare string — no prefix — is a direct model handle. The runtime resolves it to a concrete model without any indirection.

```toml
[pipe.generate_portrait]
type        = "PipeImgGen"
description = "Generate a portrait image from a description"
inputs      = { description = "Text" }
output      = "Image"
prompt      = "A professional portrait: $description"
model       = "nano-banana-pro"
```

Handles are the simplest form. They are convenient for quick experiments but couple the bundle to a specific model identifier.

## Which Pipes Use Model References

Three operator pipe types accept the `model` field:

| Pipe Type | Typical Use |
|-----------|-------------|
| `PipeLLM` | Large language model invocation. |
| `PipeImgGen` | Image generation. |
| `PipeExtract` | Document extraction (e.g., PDF to pages). |

All four reference forms (`$`, `@`, `~`, bare) work identically across all three pipe types.

## Choosing a Reference Type

- **Use an alias (`@`)** when you want a readable, stable name for a model handle but do not need to override parameters.
- **Use a preset (`$`)** when the model needs specific parameters (temperature, quality, token limits). Presets express intent without hardcoding provider details.
- **Use a waterfall (`~`)** when resilience matters — production methods that must survive model outages benefit from ordered fallbacks.
- **Use a bare handle** for quick prototyping or when the exact model identifier is known and no indirection is needed.

!!! note "Runtime compliance"
    The MTHDS standard requires only that the `model` field be a string. The prefix convention (`$`, `@`, `~`) is a standard pattern that runtimes are expected to support, but a compliant runtime may implement model references differently — for example, treating all model strings as direct identifiers.

## See Also

- [Pipes — Operators](pipes-operators.md) — the pipe types that use model references.
- [Specification: Pipe Definitions](../spec/mthds-format.md#pipe-definitions) — normative reference for all pipe fields.
- [Building a Runtime: Model References](../implementers/runtime.md#model-references) — how runtimes resolve model reference strings.
