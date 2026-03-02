# Pipes — Controllers

Controllers are pipes that orchestrate other pipes. They do not perform transformations themselves — they arrange when and how operator pipes (and other controllers) execute.

## PipeSequence

Executes a series of pipes in order. Each step's output is added to working memory, where subsequent steps can consume it.

```toml
[pipe.process_document]
type        = "PipeSequence"
description = "Full document processing pipeline"
inputs      = { document = "Document" }
output      = "AnalysisResult"
steps = [
    { pipe = "extract_pages", result = "pages" },
    { pipe = "analyze_content", result = "analysis" },
    { pipe = "generate_summary", result = "summary" },
]
```

**What this does:** Runs `extract_pages` first, stores its output as `pages` in working memory. Then runs `analyze_content` (which can use `pages`), stores the result as `analysis`. Finally runs `generate_summary`, producing the final `AnalysisResult`.

**Step fields:**

| Field | Required | Description |
|-------|----------|-------------|
| `pipe` | Yes | Pipe reference (bare, domain-qualified, or package-qualified). |
| `result` | No | Name under which the step's output is stored in working memory. |
| `nb_output` | No | Expected number of output items. Mutually exclusive with `multiple_output`. |
| `multiple_output` | No | Whether to expect multiple output items. Mutually exclusive with `nb_output`. |
| `batch_over` | No | Working memory variable to iterate over (inline batch). Requires `batch_as`. |
| `batch_as` | No | Name for each item during inline batch iteration. Requires `batch_over`. |

A sequence must contain at least one step.

Inline batching (`batch_over` / `batch_as`) allows iterating over a list within a sequence step, without needing a dedicated `PipeBatch`. Both must be provided together, and they must not have the same value.

## PipeParallel

Executes multiple pipes concurrently. Each branch operates independently.

```toml
[pipe.extract_documents]
type        = "PipeParallel"
description = "Extract text from both CV and job offer concurrently"
inputs      = { cv_pdf = "Document", job_offer_pdf = "Document" }
output      = "Page[]"
add_each_output = true
branches = [
    { pipe = "extract_cv", result = "cv_pages" },
    { pipe = "extract_job_offer", result = "job_offer_pages" },
]
```

**What this does:** Runs `extract_cv` and `extract_job_offer` at the same time. With `add_each_output = true`, each branch's output is individually stored in working memory under its `result` name.

**Key fields:**

| Field | Required | Description |
|-------|----------|-------------|
| `branches` | Yes | List of sub-pipe invocations to execute concurrently. |
| `add_each_output` | No | If `true`, each branch's output is stored individually. Default: `false`. |
| `combined_output` | No | Concept reference for a combined output that merges all branch results. |

At least one of `add_each_output` or `combined_output` must be set — otherwise the pipe produces no usable output.

## PipeCondition

Routes execution to different pipes based on an evaluated condition.

```toml
[pipe.route_by_document_type]
type                = "PipeCondition"
description         = "Route processing based on document type"
inputs              = { doc_request = "DocumentRequest" }
output              = "Text"
expression_template = "{{ doc_request.document_type }}"
default_outcome     = "continue"

[pipe.route_by_document_type.outcomes]
technical = "process_technical"
business  = "process_business"
legal     = "process_legal"
```

**What this does:** Evaluates `doc_request.document_type` and routes to the matching pipe. If the document type is `"technical"`, it runs `process_technical`. If no outcome matches, `"continue"` means execution proceeds without running a sub-pipe.

**Key fields:**

| Field | Required | Description |
|-------|----------|-------------|
| `expression_template` | Conditional | A Jinja2 template that evaluates to a string matching an outcome key. Exactly one of `expression_template` or `expression` is required. |
| `expression` | Conditional | A static expression string. Exactly one of `expression_template` or `expression` is required. |
| `outcomes` | Yes | Maps outcome strings to pipe references. Must have at least one entry. |
| `default_outcome` | Yes | The pipe reference (or special outcome) to use when no outcome key matches. |
| `add_alias_from_expression_to` | No | If set, stores the evaluated expression value in working memory under this name. |

**Special outcomes:** Two string values have special meaning and are not treated as pipe references:

- `"fail"` — abort execution with an error.
- `"continue"` — skip this branch and continue without executing a sub-pipe.

## PipeBatch

Maps a single pipe over each item in a list input, producing a list output.

```toml
[pipe.batch_generate_jokes]
type             = "PipeBatch"
description      = "Generate a joke for each topic"
inputs           = { topics = "Topic[]" }
output           = "Joke[]"
branch_pipe_code = "generate_joke"
input_list_name  = "topics"
input_item_name  = "topic"
```

**What this does:** Takes a list of `Topic` items and runs `generate_joke` on each one, producing a list of `Joke` outputs.

**Key fields:**

| Field | Required | Description |
|-------|----------|-------------|
| `branch_pipe_code` | Yes | The pipe reference to invoke for each item. |
| `input_list_name` | Yes | The name of the input that contains the list to iterate over. Must exist as a key in `inputs`. |
| `input_item_name` | Yes | The name under which each individual item is passed to the branch pipe. |

**Constraints:**

- `input_item_name` must not equal `input_list_name`.
- `input_item_name` must not equal any key in `inputs`.

A naming tip: use the plural for the list and its singular form for the item (e.g., list `"topics"` → item `"topic"`).

## Pipe Reference Syntax in Controllers

Every location in a controller that references another pipe supports three forms:

| Form | Syntax | Example |
|------|--------|---------|
| Bare | `pipe_code` | `"extract_clause"` |
| Domain-qualified | `domain.pipe_code` | `"legal.contracts.extract_clause"` |
| Package-qualified | `alias->domain.pipe_code` | `"docproc->extraction.extract_text"` |

These references appear in:

- `steps[].pipe` (PipeSequence)
- `branches[].pipe` (PipeParallel)
- `outcomes` values (PipeCondition)
- `default_outcome` (PipeCondition)
- `branch_pipe_code` (PipeBatch)

Pipe *definitions* (the `[pipe.<pipe_code>]` table keys) are always bare `snake_case` names. Namespacing applies only to pipe *references*.

## See Also

- [Specification: Controller Definitions](../spec/mthds-format.md#controller-pipesequence) — normative reference for all controller types and validation rules.
- [Pipes — Operators](pipes-operators.md) — the individual transformations that controllers orchestrate.
