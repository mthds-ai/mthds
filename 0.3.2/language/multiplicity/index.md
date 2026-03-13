# Multiplicity

Multiplicity defines how many items a pipe accepts as input or produces as output. It is expressed with bracket notation on concept references and is fundamental to building methods that handle both single items and collections.

## Philosophy: Concepts Are Always Singular

Concepts are always defined in the singular form. Define `Keyword`, not `Keywords`. Define `Invoice`, not `Invoices`.

This is not just a naming convention — it is a design principle. A concept describes a semantic entity: what something *is*. The number of items is a circumstantial detail of the method, not part of the concept's identity:

- A pipe that extracts keywords might find 3 or 30 — each is still a `Keyword`.
- A pipe that generates product ideas might produce 5 or 10 — each remains a `ProductIdea`.

By keeping concepts singular and expressing quantity through multiplicity, MTHDS maintains a clean separation between semantics (what) and cardinality (how many).

## Output Multiplicity

Output multiplicity controls how many items a pipe produces. It is specified using bracket notation in the `output` field.

### Single Output (default)

When no brackets are used, the pipe produces exactly one item:

```toml
[pipe.summarize]
type        = "PipeLLM"
description = "Create a summary of the document"
inputs      = { document = "Text" }
output      = "Summary"
prompt      = "Summarize this document concisely: @document"
```

### Variable Output (`[]`)

Empty brackets let the model decide how many items to produce:

```toml
[pipe.extract_line_items]
type        = "PipeLLM"
description = "Extract all line items from an invoice"
inputs      = { invoice_text = "Text" }
output      = "LineItem[]"
prompt      = """
Extract all line items from this invoice:

@invoice_text

For each line item, extract the description, quantity, unit price, and total amount.
"""
```

The pipe extracts however many line items appear in the invoice — 2 for a simple receipt, 50 for a detailed purchase order.

**Common use cases:**

- Extract entities from text (unknown count in advance)
- List all items that match criteria
- Identify all occurrences of a pattern

### Fixed Output (`[N]`)

A number in brackets produces an exact count:

```toml
[pipe.generate_headline_options]
type        = "PipeLLM"
description = "Generate headline alternatives"
inputs      = { article_text = "Text" }
output      = "Headline[5]"
prompt      = """
Read this article:

@article_text

Generate 5 different headline options for this article. Make each one unique and compelling.
"""
```

**Common use cases:**

- Generate N alternatives for A/B testing
- Create a fixed set of options for user selection
- Produce a specific number of variations for comparison

### The `nb_output` Field

In a `PipeSequence` step, the `nb_output` field provides an alternative to bracket notation. It overrides the output multiplicity declared on the called pipe for that particular step invocation:

```toml
[pipe.generate_email_variants]
type        = "PipeSequence"
description = "Generate subject lines for an email"
inputs      = { email_body = "EmailContent" }
output      = "SubjectLine[]"
steps = [
    { pipe = "generate_subject_lines", nb_output = 3, result = "subject_lines" },
]
```

Here, `generate_subject_lines` may declare `output = "SubjectLine"` (singular), but `nb_output = 3` on the step tells the runtime to produce 3 items for this invocation. The `$_nb_output` variable is automatically available in the called pipe's prompt and reflects this value.

## Input Multiplicity

Input multiplicity specifies whether a pipe expects a single item or a list. It uses the same bracket notation, applied to concept references in the `inputs` field.

### Single Input (default)

No brackets — the pipe expects exactly one item:

```toml
inputs = { report = "Report" }
```

### Variable Input (`[]`)

Empty brackets — the pipe expects a list of indeterminate length:

```toml
[pipe.summarize_all_documents]
type        = "PipeLLM"
description = "Create a unified summary of multiple documents"
inputs      = { documents = "Document[]" }
output      = "Summary"
prompt      = """
Analyze all of these documents:

@documents

Create a single unified summary that captures the key points across all documents.
"""
```

### Fixed Input (`[N]`)

A number in brackets — the pipe expects exactly that many items:

```toml
[pipe.compare_two_images]
type        = "PipeLLM"
description = "Compare exactly two images side by side"
inputs      = { images = "Image[2]" }
output      = "Comparison"
prompt      = """
Compare these two images in detail:

@images

Describe their similarities, differences, and relative strengths.
"""
```

## Practical Use Cases

### Batch Processing with Variable Input

Process an unknown number of invoices, extracting structured data from each:

```toml
[pipe.extract_single_invoice]
type        = "PipeLLM"
description = "Extract data from one invoice"
inputs      = { invoice_image = "InvoiceImage" }
output      = "InvoiceData"
prompt      = "Extract all fields from this invoice: @invoice_image"

[pipe.process_invoice_batch]
type        = "PipeSequence"
description = "Process multiple invoices"
inputs      = { invoice_images = "InvoiceImage[]" }
output      = "InvoiceData[]"
steps = [
    { pipe = "extract_single_invoice", batch_over = "invoice_images", batch_as = "invoice_image", result = "all_invoice_data" }
]
```

### Fixed Alternatives for Comparison

Generate exactly 3 subject line variations for A/B testing:

```toml
[pipe.generate_subject_lines]
type        = "PipeLLM"
description = "Generate 3 subject line options"
inputs      = { email_body = "EmailContent" }
output      = "SubjectLine[3]"
prompt      = """
Email content:
@email_body

Generate 3 compelling subject lines for this email.
Each should use a different persuasion technique.
"""
```

### Entity Extraction with Unknown Count

Extract all company names mentioned in a document:

```toml
[pipe.extract_companies]
type        = "PipeLLM"
description = "Extract all company names from an article"
inputs      = { article = "Article" }
output      = "CompanyName[]"
prompt      = """
Read this article:

@article

Extract all company and organization names mentioned in the article.
Only include entities that are explicitly named.
"""
```

## Best Practices

**When to use variable output (`[]`):**

- The number of outputs depends on the content being analyzed
- You are extracting or identifying items (entities, keywords, issues)
- The count is not known until after processing

**When to use fixed output (`[N]`):**

- You need a specific number for downstream processes
- You are generating alternatives for comparison or selection
- External requirements dictate a fixed count

**When to use variable input (`[]`):**

- The pipe should handle batches of unknown size
- You are aggregating or summarizing multiple items
- You want maximum flexibility in how the pipe is called

**When to use fixed input (`[N]`):**

- The operation inherently requires a specific count (e.g., comparison of 2 items)
- The prompt logic depends on an exact number of inputs

## See Also

- [Pipes — Operators](pipes-operators.md) — multiplicity syntax in the Common Fields table.
- [Pipes — Controllers](pipes-controllers.md) — how `PipeBatch` and inline batching interact with list inputs.
- [Specification: Pipe Definitions](../spec/mthds-format.md#pipe-definitions) — normative reference for multiplicity syntax.
