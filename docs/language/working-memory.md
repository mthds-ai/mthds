---
description: "Understand working memory — the data-flow mechanism that connects pipes in a pipeline run."
---

# Working Memory

Working memory is the mechanism that enables data flow between pipes. It acts as a temporary store that exists for the duration of a single pipeline run.

## How Data Flows Between Pipes

When pipes are composed inside a controller (such as `PipeSequence`), the output of each pipe needs to reach subsequent pipes. Working memory handles this.

```toml
[pipe.description_to_tagline]
type = "PipeSequence"
description = "From product description to tagline and keywords"
inputs = { description = "ProductDescription" }
output = "Keyword[]"
steps = [
    { pipe = "generate_tagline", result = "tagline" },
    { pipe = "extract_keywords", result = "keywords" },
]
```

How does `extract_keywords` access the output of `generate_tagline`? Through working memory:

1. When `generate_tagline` completes, its output is stored in working memory under the name specified by `result` — here, `"tagline"`.
2. `extract_keywords` declares `tagline` in its `inputs`. The runtime matches the input name to the working memory entry and passes the data in.

This name-matching mechanism chains pipes together into a flow of typed data.

## Lifecycle

Working memory follows a simple lifecycle within a pipeline run:

1. **Creation** — Working memory is initialized when the pipeline run starts.
2. **Population** — The caller's inputs are placed into working memory before the first pipe executes.
3. **Updates** — After each pipe completes, its output is stored under the name given by the `result` field.
4. **Access** — Any subsequent pipe can consume data from working memory by declaring a matching name in its `inputs`.
5. **Disposal** — Working memory is cleared when the pipeline run completes.

## Best Practices

- **Use meaningful names.** Choose descriptive `result` values so the pipeline reads like a narrative: `result = "candidate_skills"` is clearer than `result = "data"`.
- **Declare clear contracts.** Each pipe's `inputs` field explicitly states what it needs from working memory. This makes dependencies visible at a glance.
- **Fail fast.** If a required input is missing from working memory, a compliant runtime rejects the run before the pipe executes, producing a clear error rather than a silent failure.

## See Also

- [Pipes — Controllers](pipes-controllers.md) — how PipeSequence, PipeParallel, and PipeBatch use working memory.
- [Putting It All Together](putting-it-all-together.md) — a complete bundle walkthrough showing working memory in action.
