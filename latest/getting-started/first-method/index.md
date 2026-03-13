# Write Your First Method

This guide walks you through creating a working `.mthds` file from scratch. By the end, you will have a method that generates a short summary from a text input.

## Prerequisites

- A text editor with MTHDS support. Install the [VS Code extension](../tooling/editor-support.md) for the best experience.
- The `plxt` CLI installed for formatting (see [Formatting & Linting](../tooling/formatting-linting.md)).
- The `mthds` CLI installed for validation.

## Step 1: Create a `.mthds` File

Create a new file called `summarizer.mthds` and add a domain header:

```toml
domain      = "summarization"
description = "Text summarization methods"
```

Every bundle starts with a `domain` — a namespace for the concepts and pipes you will define. The domain name uses `snake_case` segments separated by dots.

## Step 2: Define a Concept

Add a concept to describe the kind of data your method produces:

```toml
domain      = "summarization"
description = "Text summarization methods"

[concept]
Summary = "A concise summary of a longer text"
```

This declares a simple concept called `Summary`. It has no internal structure — it is a semantic label that gives meaning to the data your pipe produces.

Concept codes use `PascalCase` (e.g., `Summary`, `ContractClause`, `CandidateProfile`).

## Step 3: Define a Pipe

Add a pipe that takes text input and produces a summary:

```toml
domain      = "summarization"
description = "Text summarization methods"
main_pipe   = "summarize"

[concept]
Summary = "A concise summary of a longer text"

[pipe.summarize]
type        = "PipeLLM"
description = "Summarize the input text in 2-3 sentences"
inputs      = { text = "Text" }
output      = "Summary"
prompt      = """
Summarize the following text in 2-3 concise sentences. Focus on the key points.

@text
"""
```

Here is what each field does:

- `type = "PipeLLM"` — this pipe uses a large language model to generate output.
- `inputs = { text = "Text" }` — the pipe accepts one input called `text`, of the native `Text` type.
- `output = "Summary"` — the pipe produces a `Summary` concept.
- `prompt` — the LLM prompt template. `@text` is shorthand for `{{ text }}`, injecting the input variable.

The `main_pipe = "summarize"` header marks this pipe as the bundle's primary entry point.

## Step 4: Format Your File

Run the formatter to ensure consistent style:

```bash
plxt fmt summarizer.mthds
```

The formatter aligns entries, normalizes whitespace, and ensures your file follows MTHDS style conventions.

## Step 5: Validate

Validate your bundle:

```bash
mthds validate summarizer.mthds
```

If everything is correct, you will see a success message. If there are errors — a misspelled concept reference, an unused input, a missing required field — the validator reports them with specific messages.

## The Complete File

```toml
domain      = "summarization"
description = "Text summarization methods"
main_pipe   = "summarize"

[concept]
Summary = "A concise summary of a longer text"

[pipe.summarize]
type        = "PipeLLM"
description = "Summarize the input text in 2-3 sentences"
inputs      = { text = "Text" }
output      = "Summary"
prompt      = """
Summarize the following text in 2-3 concise sentences. Focus on the key points.

@text
"""
```

This file works as a standalone bundle — no manifest, no package, no dependencies. To run it:

```bash
mthds run summarizer.mthds
```

## File Naming Conventions

When organizing `.mthds` files in a project:

- Use `snake_case` for file names: `invoice_processing.mthds`, `cv_analysis.mthds`.
- Match the file name to the bundle's domain when practical. A bundle with `domain = "invoice_processing"` lives naturally in `invoice_processing.mthds`.
- Use the `.mthds` extension — it is required by the toolchain for validation and formatting.

## Next Steps

- Add more concepts and pipes to your bundle. See [The Language](../language/bundles.md) for the full set of pipe types and concept features.
- When you are ready to distribute your methods, see [Create a Package](../guides/create-package.md).
