---
description: "Use the -> syntax to reference pipes and concepts from other MTHDS packages in your bundles."
---

# Cross-Package References

When your bundle needs a pipe or concept from another package, you use a **cross-package reference** — the `->` syntax that reaches into a dependency.

## The `->` Syntax

```toml
steps = [
    { pipe = "scoring_lib->scoring.compute_weighted_score", result = "score" },
]
```

This reference reads as: "from the package aliased as `scoring_lib`, get the pipe `compute_weighted_score` in the `scoring` domain."

The `->` separator was chosen for readability. It reads as natural language — "from scoring_lib, get..." — and is visually distinct from the `.` used for domain paths.

## Anatomy of a Cross-Package Reference

```
scoring_lib -> scoring.compute_weighted_score
  alias     ↑     domain   pipe code
         separator
```

1. **Alias** — the `snake_case` key from `[dependencies]` in `METHODS.toml`.
2. **`->`** — the cross-package separator.
3. **Domain-qualified name** — parsed by splitting on the last `.`: domain path `scoring`, pipe code `compute_weighted_score`.

## Referencing Pipes

Cross-package pipe references appear in all the same locations as domain-qualified pipe references:

- `steps[].pipe` in PipeSequence
- `branches[].pipe` in PipeParallel
- `outcomes` values in PipeCondition
- `default_outcome` in PipeCondition
- `branch_pipe_code` in PipeBatch

```toml
[pipe.full_analysis]
type        = "PipeSequence"
description = "Run external scoring and local summary"
inputs      = { item = "Text" }
output      = "Text"
steps = [
    { pipe = "scoring_lib->scoring.compute_weighted_score", result = "score" },
    { pipe = "summarize_score", result = "summary" },
]
```

**Visibility constraint:** The referenced pipe must be exported by the dependency package — listed in its `[exports]` section or declared as `main_pipe` in one of its bundles.

## Referencing Concepts

Cross-package concept references work the same way, appearing in `inputs`, `output`, `refines`, `concept_ref`, `item_concept_ref`, and `combined_output`:

```toml
[concept.DetailedScore]
description = "An extended score with additional analysis"
refines     = "scoring_lib->scoring.ScoreResult"
```

**Concepts are always public.** No visibility check is needed for cross-package concept references.

## A Complete Example

**Setup:** Package A depends on Package B with alias `scoring_lib`.

Package B's manifest:

```toml
[package]
address     = "github.com/mthds/scoring-lib"
version     = "0.5.0"
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

**What works:**

- `scoring_lib->scoring.compute_weighted_score` resolves because `compute_weighted_score` is exported.
- `scoring_lib->scoring.ScoreResult` (concept reference) resolves because concepts are always public.

**What fails:**

- `scoring_lib->scoring.internal_helper` — visibility error: `internal_helper` is not in `[exports.scoring]` and is not `main_pipe`.

## See Also

- [Specification: Namespace Resolution Rules](../spec/namespace-resolution.md) — formal resolution algorithm.
- [Namespace Resolution](../language/namespace-resolution.md) — the three tiers of reference resolution.
- [Exports & Visibility](exports-visibility.md) — how exports control what is accessible.
