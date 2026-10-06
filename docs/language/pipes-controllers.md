---
description: "Orchestrate multi-step AI workflows with MTHDS controller pipes: PipeSequence, PipeBatch, PipeCondition, and PipeParallel."
---

# Pipes — Controllers

Controllers are pipes that orchestrate other pipes. They do not perform transformations themselves — they arrange when and how operator pipes (and other controllers) execute.

## PipeSequence

Executes a series of steps in order. A pipe step runs a pipe and adds its output to [working memory](working-memory.md), and a [binding step](#binding-steps) stores a deep copy of the value at a path in working memory under its `result` name. Subsequent steps can consume every value stored this way.

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

A step is either a **pipe step**, which runs a pipe, or a [binding step](#binding-steps), which binds a value already in working memory to a new name.

**Pipe step fields:**

| Field | Required | Description |
|-------|----------|-------------|
| `pipe` | Yes | Pipe reference (bare, domain-qualified, or package-qualified). |
| `result` | No | Name under which the step's output is stored in working memory. |
| `nb_output` | No | Expected number of output items. Mutually exclusive with `multiple_output`. |
| `multiple_output` | No | Whether to expect multiple output items. Mutually exclusive with `nb_output`. |
| `batch_over` | No | Working memory variable to iterate over (inline batch). Requires `batch_as`. A dotted path such as `catalog.pages` binds that field first, then iterates over it. |
| `batch_as` | No | Name for each item during inline batch iteration. Requires `batch_over`. |

A sequence must contain at least one step.

Inline batching (`batch_over` / `batch_as`) allows iterating over a list within a sequence step, without needing a dedicated `PipeBatch`. Both must be provided together, and they must not have the same value. `batch_over` may be a dotted path, such as `catalog.pages`: that is a binding of the path followed by a batch over the bound list, so it follows every rule of the binding step described below.

### Binding Steps

A binding step takes the value at a path in working memory and stores it under a new name, so that the next steps can read one field of a larger value without a pipe written to extract it:

```toml
[pipe.review_invoice]
type        = "PipeSequence"
description = "Decide whether an invoice needs a manager's approval"
inputs      = { invoice = "Invoice" }
output      = "YesNo"
steps = [
    { from = "invoice.total", result = "total_amount" },
    { pipe = "judge_large_amount", result = "needs_approval" },
]
```

**What this does:** The first step takes the `total` field of `invoice` and stores it in working memory as `total_amount`. `judge_large_amount` declares `total_amount = "Number"` among its inputs, so it receives the amount alone, not the whole invoice. The judge's signature names a whole concept, and the sequence, which knows what `invoice` holds, picks the field at the call site.

A binding step has exactly two fields, both required: `from`, the path to bind, and `result`, the name to store it under. The path starts with a name in working memory and continues with zero or more field names, separated by dots. It carries no subscripts or expressions: anything computed is a pipe's job. The `result` must be a plain name in lowercase `snake_case`, such as `total_amount`, and never a dotted path, because a binding step stores its value only for a later step to read, and an input reads a stored value only under a plain name. Every step carries exactly one of `pipe` and `from`: `pipe` makes it a pipe step and `from` a binding step, and a step with both or with neither is rejected. A binding step carries none of a pipe step's other fields.

**The result's concept is derived from the structure the path walks**, before anything runs. `invoice.total` is a `Number` because `Invoice` declares `total` as a number, and `page.page_view` is an `Image` because the native `Page` declares `page_view` as one. A text field gives a `Text`, a boolean a `YesNo`, a date a `Date`, and a field holding a concept gives that concept. A path naming a field that does not exist is rejected, and the error lists the fields that do.

**Lists map and flatten.** When the path crosses a list, the rest of the path is applied to every item, items that hold nothing are dropped, and lists inside lists are flattened into one. Over a list of pages, `pages.page_view` gives a list of images, which a later step can batch over:

```toml
steps = [
    { pipe = "extract_pages", result = "pages" },
    { from = "pages.page_view", result = "page_views" },
    { pipe = "describe_view", batch_over = "page_views", batch_as = "page_view", result = "descriptions" },
]
```

**The value is a copy**, taken when the step runs. The whole value at the path is copied, so a bound image keeps every field it has, and a later step that changes or replaces `invoice` does not change `total_amount`.

**A bare name renames.** `{ from = "departure_board", result = "board" }` binds a copy of the whole value under a new name, with the same concept and multiplicity. This is how a sequence hands a value to a pipe whose input has another name.

**Absence.** A binding step whose root is absent is skipped, and one whose path reaches nothing records an absence rather than failing. See [Optionality](optionality.md#absence-through-a-binding-step).

Binding steps belong to `PipeSequence` only, because only a sequence has an order. A `PipeParallel` branch always runs a pipe: bind the value in a sequence step before the parallel.

The full rules, including how each field type maps to a concept and every reason a path is refused, are in the [specification](../spec/mthds-format.md#binding-steps).

## PipeParallel

Executes multiple pipes concurrently. Each branch operates independently, then the branch results are combined into the pipe's declared `output`.

```toml
[pipe.extract_documents]
type        = "PipeParallel"
description = "Extract text from both CV and job offer concurrently"
inputs      = { cv_pdf = "Document", job_offer_pdf = "Document" }
output      = "Composite"
add_each_output = true
branches = [
    { pipe = "extract_cv", result = "cv_pages" },
    { pipe = "extract_job_offer", result = "job_offer_pages" },
]
```

**What this does:** Runs `extract_cv` and `extract_job_offer` at the same time, then combines the two branch results into the main `Composite` output. With `add_each_output = true`, each branch's output is also stored individually in working memory under its `result` name.

**Key fields:**

| Field | Required | Description |
|-------|----------|-------------|
| `branches` | Yes | List of pipe steps to execute concurrently. A branch cannot be a [binding step](#binding-steps), nor carry a dotted `batch_over`, which binds before it batches. |
| `output` | Yes | Combined output concept. Must be `Composite` or a structured concept whose fields match branch `result` names. Multiplicity is not allowed. |
| `add_each_output` | No | If `true`, each branch's output is also stored individually. Default: `false`. |

The combined `output` is always the pipe's main output. `add_each_output` is only for exposing branch outputs to downstream pipes by their individual `result` names.

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
| `input_list_name` | Yes | The name of the input that contains the list to iterate over. Must be a plain input name and must exist as a key in `inputs`. |
| `input_item_name` | Yes | The name under which each individual item is passed to the branch pipe. |

**Constraints:**

- `input_list_name` must be a plain input name, never a dotted path such as `catalog.pages` (see [Input names](../spec/mthds-format.md#input-names)). To map a pipe over a list held in a field, declare the list itself as the PipeBatch's input (`pages = "Page[]"`, with `input_list_name = "pages"`), and let the calling [PipeSequence](#pipesequence) hand the field over under that name.
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
