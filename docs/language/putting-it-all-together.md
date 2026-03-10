---
description: "A complete MTHDS bundle walkthrough showing how concepts, operators, and controllers compose into a working AI method."
---

# Putting It All Together

Before moving on to domains and namespace resolution, here is a complete bundle that uses both operators and controllers. It shows how concepts, pipes, and [working memory](working-memory.md) flow together.

```toml
domain      = "joke_generation"
description = "Generating one-liner jokes from topics"
main_pipe   = "generate_jokes_from_topics"

[concept.Topic]
description = "A subject or theme that can be used as the basis for a joke."
refines     = "Text"

[concept.Joke]
description = "A humorous one-liner intended to make people laugh."
refines     = "Text"

[pipe.generate_jokes_from_topics]
type        = "PipeSequence"
description = "Generate 3 joke topics and create a joke for each"
output      = "Joke[]"
steps = [
    { pipe = "generate_topics", result = "topics" },
    { pipe = "batch_generate_jokes", result = "jokes" },
]

[pipe.generate_topics]
type   = "PipeLLM"
description = "Generate 3 distinct topics suitable for jokes"
output = "Topic[3]"
prompt = "Generate 3 distinct and varied topics for crafting one-liner jokes."

[pipe.batch_generate_jokes]
type             = "PipeBatch"
description      = "Generate a joke for each topic"
inputs           = { topics = "Topic[]" }
output           = "Joke[]"
branch_pipe_code = "generate_joke"
input_list_name  = "topics"
input_item_name  = "topic"

[pipe.generate_joke]
type        = "PipeLLM"
description = "Write a clever one-liner joke about the given topic"
inputs      = { topic = "Topic" }
output      = "Joke"
prompt      = "Write a clever one-liner joke about $topic. Be concise and witty."
```

## How It Works

1. `generate_jokes_from_topics` is a `PipeSequence` — the entry point.
2. Step 1 calls `generate_topics`, a `PipeLLM` that produces exactly 3 `Topic` items (`Topic[3]`). The result is stored in working memory as `topics`.
3. Step 2 calls `batch_generate_jokes`, a `PipeBatch` that iterates over `topics`. For each `Topic`, it invokes `generate_joke`.
4. `generate_joke` is a `PipeLLM` that takes one `topic` and produces one `Joke`.
5. The batch collects all jokes into `Joke[]`, which becomes the final output.

The concepts (`Topic` and `Joke`) both refine the native `Text` concept. The pipes — a sequence, a batch, and LLM operators — work together through working memory.
