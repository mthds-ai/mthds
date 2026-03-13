---
description: "Discover MTHDS operator pipes: PipeLLM, PipeFunc, PipeImgGen, PipeExtract, PipeSearch, and PipeCompose for single-step AI transformations."
---

# Pipes — Operators

Pipes are typed transformations — the actions in MTHDS. Each pipe has a typed signature: it declares what concepts it accepts as input and what concept it produces as output.

MTHDS defines two categories of pipes:

- **Operators** — pipes that perform a single transformation (this page).
- **Controllers** — pipes that orchestrate other pipes (next page).

## Common Fields

All pipe types share these base fields:

| Field | Required | Description |
|-------|----------|-------------|
| `type` | Yes | The pipe type (e.g., `"PipeLLM"`, `"PipeSequence"`). |
| `description` | Yes | Human-readable description of what this pipe does. |
| `inputs` | No | Input declarations. Keys are input names (`snake_case`), values are concept references. |
| `output` | Yes | The output concept reference. |

**Pipe codes** are the keys in `[pipe.<pipe_code>]` tables. They must be `snake_case`, matching `[a-z][a-z0-9_]*`.

**Concept references in inputs and output** support an optional multiplicity suffix:

| Syntax | Meaning |
|--------|---------|
| `ConceptName` | A single instance. |
| `ConceptName[]` | A variable-length list. |
| `ConceptName[N]` | A fixed-length list of exactly N items (N ≥ 1). |

See [Multiplicity](multiplicity.md) for a detailed guide on when and how to use each form.

## PipeLLM

Generates output by invoking a large language model with a prompt.

```toml
[pipe.analyze_cv]
type = "PipeLLM"
description = "Analyze a CV to extract key professional information"
output = "CVAnalysis"
model = "$writing-factual"
system_prompt = """
You are an expert HR analyst specializing in CV evaluation.
"""
prompt = """
Analyze the following CV and extract the candidate's key professional information.

@cv_pages
"""

[pipe.analyze_cv.inputs]
cv_pages = "Page"
```

**What this does:** Takes a `Page` input, sends it to an LLM with the given prompt and system prompt, and produces a `CVAnalysis` output.

**Key fields:**

| Field | Required | Description |
|-------|----------|-------------|
| `prompt` | No | The LLM prompt template. Supports Jinja2 syntax and `@variable` / `$variable` shorthand. |
| `system_prompt` | No | System prompt for the LLM. Falls back to the bundle-level `system_prompt` if omitted. |
| `model` | No | Model identifier, model reference (see [Model References](model-references.md)), or an inline settings table (see [Inline Settings](model-references.md#inline-settings)). |
| `model_to_structure` | No | Model used for structuring the LLM output into the declared concept. Accepts the same forms as `model`. |
| `structuring_method` | No | How the output is structured: `"direct"` or `"preliminary_text"`. |

**Prompt template syntax:**

All three syntaxes below compile to the same Jinja2 template under the hood. The shorthands exist to improve readability:

- `{{ variable_name }}` — standard Jinja2 variable substitution.
- `@variable_name` — shorthand designed for **block-level insertion** of an input's full content. Use `@` when the variable stands on its own line or represents a large block of text.
- `$variable_name` — shorthand designed for **inline substitution** within a sentence. Use `$` when the variable is embedded in surrounding text.
- `@?variable_name` — shorthand for **conditional insertion**. Renders the variable only if it is truthy (non-empty, non-null). Use `@?` for optional inputs that may or may not be provided.

For example:

```toml
prompt = """
Summarize the following article about $topic:

@article_text

@?additional_context

Keep the summary under 3 sentences.
"""
```

Here, `$topic` is inline (part of the sentence), `@article_text` is block-level (inserted as a standalone block), and `@?additional_context` is conditionally inserted — it only appears if the variable has a value. All three conventions aid readability — they are not enforced by the runtime.

Dotted paths are supported: `{{ doc_request.document_type }}`, `@doc_request.priority`.

For the full reference on shorthand syntax, template categories, and available filters, see [PipeCompose — Template Mode](#template-mode) below.

Every variable referenced in the prompt must correspond to a declared input, and every declared input must be referenced in the prompt or system prompt. Unused inputs are rejected.

### Image Inputs

PipeLLM supports vision language models that process both text and images. Declare image inputs in the `inputs` field — they are passed to the model alongside the text prompt.

```toml
[pipe.describe_image]
type        = "PipeLLM"
description = "Describe an image"
inputs      = { image = "Image" }
output      = "VisualDescription"
prompt      = "Describe the provided image in great detail: $image"
```

Image variables must be tagged with `@` or `$` in the prompt, just like text variables.

**Sub-attribute access with dot notation:** When an input is a structured concept that contains an image field, use dotted paths to reach the image:

```toml
[pipe.analyze_page_view]
type        = "PipeLLM"
description = "Analyze the visual layout of a page"
inputs      = { "page_content.page_view" = "Image" }
output      = "LayoutAnalysis"
prompt      = """
Analyze the visual layout and design elements of this page: $page_content.page_view
Focus on typography, spacing, and overall composition.
"""
```

**Multiple images:** List each image as a separate input:

```toml
[pipe.compare_images]
type        = "PipeLLM"
description = "Compare two images"
inputs      = { first_image = "Image", second_image = "Image" }
output      = "ImageComparison"
prompt      = "Compare these two images and describe their similarities and differences: $first_image and $second_image"
```

### Document Inputs

PipeLLM supports documents (PDFs, etc.) as inputs. Documents are passed to the model alongside the text prompt.

```toml
[pipe.summarize_document]
type        = "PipeLLM"
description = "Summarize a document"
inputs      = { document = "Document" }
output      = "DocumentSummary"
prompt      = "Summarize the key points from this document: @document"
```

Document variables must be tagged with `@` or `$`, just like text and image variables.

**Multiple documents:**

```toml
[pipe.compare_documents]
type        = "PipeLLM"
description = "Compare two documents"
inputs      = { first_doc = "Document", second_doc = "Document" }
output      = "DocumentComparison"
prompt      = "Compare these two documents and describe their similarities and differences: $first_doc and $second_doc"
```

Text, image, and document inputs can be freely combined in the same pipe.

### Structuring Method

The `structuring_method` field controls how PipeLLM produces structured output (when the output concept has a `structure` table):

- `"direct"` — the model generates JSON conforming to the output schema in a single call. This is the fastest option and works well when the output structure is straightforward (few fields, simple types) and the model reliably produces well-formed JSON.
- `"preliminary_text"` — a two-step process: the model first generates free-form text reasoning through the problem, then a second call extracts and structures the information into the target schema. Use this mode when the output structure is complex (many fields, nested concepts, or nuanced extraction) or when the model struggles to produce correct JSON in a single pass.

When `structuring_method` is omitted, the runtime chooses a default. In general, start with the default and switch to `"preliminary_text"` if you observe structuring errors or degraded output quality on complex schemas.

**More PipeLLM examples:**

Image input with structured output:

```toml
[concept.TableRow]
description = "A single row of data from a table"

[concept.TableRow.structure]
cells = { type = "list", item_type = "text", description = "Cell values in order" }

[concept.TableData]
description = "Structured data extracted from a table image"

[concept.TableData.structure]
headers = { type = "list", item_type = "text", description = "Column headers" }
rows    = { type = "list", item_type = "concept", item_concept_ref = "TableRow", description = "Table rows" }

[pipe.extract_table_from_image]
type        = "PipeLLM"
description = "Extract table data from an image"
inputs      = { image = "Image" }
output      = "TableData"
prompt      = "Extract the table data from this image and return the headers and rows: $image"
```

Combining text and document inputs:

```toml
[pipe.analyze_with_context]
type        = "PipeLLM"
description = "Analyze a document with additional context"
inputs      = { context = "Text", reference_doc = "Document" }
output      = "ContextualAnalysis"
prompt      = """
Given this context: $context

Analyze the document and explain how it relates to the context: $reference_doc
"""
```

## PipeFunc

Calls a registered Python function.

```toml
[pipe.capitalize_text]
type          = "PipeFunc"
description   = "Capitalize the input text"
inputs        = { text = "Text" }
output        = "Text"
function_name = "my_package.text_utils.capitalize"
```

**What this does:** Passes the `Text` input to the Python function `my_package.text_utils.capitalize` and returns the result as `Text`.

**Key fields:**

| Field | Required | Description |
|-------|----------|-------------|
| `function_name` | Yes | The fully-qualified name of the Python function to call. |

PipeFunc bridges MTHDS with custom code. The function must be registered in the runtime.

## PipeImgGen

Generates images using an image generation model.

```toml
[pipe.generate_portrait]
type        = "PipeImgGen"
description = "Generate a portrait image from a description"
inputs      = { description = "Text" }
output      = "Image"
prompt      = "A professional portrait: $description"
model       = "$gen-image-testing"
```

**What this does:** Takes a `Text` description, sends it to an image generation model, and produces an `Image` output.

**Key fields:**

| Field | Required | Description |
|-------|----------|-------------|
| `prompt` | Yes | The image generation prompt. Supports Jinja2 and `$variable` shorthand. |
| `negative_prompt` | No | Concepts to avoid in generation. |
| `model` | No | Model identifier, model reference (see [Model References](model-references.md)), or an inline settings table (see [Inline Settings](model-references.md#inline-settings)). |
| `aspect_ratio` | No | Desired aspect ratio. Values: `square`, `landscape_4_3`, `landscape_3_2`, `landscape_16_9`, `landscape_21_9`, `portrait_3_4`, `portrait_2_3`, `portrait_9_16`, `portrait_9_21`. |
| `is_raw` | No | Whether to use raw mode (less post-processing). |
| `seed` | No | Random seed for reproducibility. Integer value, or `"auto"` to let the model randomize it. |
| `background` | No | Background setting. Values: `transparent`, `opaque`, `auto`. |
| `output_format` | No | Image output format. Values: `png`, `jpeg`, `webp`. |

## PipeExtract

Extracts structured content from documents (e.g., PDF pages).

```toml
[pipe.extract_cv]
type        = "PipeExtract"
description = "Extract text content from a CV PDF document"
inputs      = { cv_pdf = "Document" }
output      = "Page[]"
model       = "@default-text-from-pdf"
```

**What this does:** Takes a `Document` input and extracts its content as a variable-length list of `Page` objects.

**Key fields:**

| Field | Required | Description |
|-------|----------|-------------|
| `model` | No | Model identifier, model reference (see [Model References](model-references.md)), or an inline settings table (see [Inline Settings](model-references.md#inline-settings)). |
| `max_page_images` | No | Maximum number of page images to process. |
| `page_image_captions` | No | Whether to generate captions for page images. |
| `page_views` | No | Whether to generate page views. |
| `page_views_dpi` | No | DPI for page view rendering. |

**Constraints:** PipeExtract requires exactly one input (typically `Document` or a concept refining it) and the output must be `"Page[]"`.

## PipeSearch

Searches the web using a search provider and returns structured results with an answer and source citations.

```toml
[pipe.search_topic]
type        = "PipeSearch"
description = "Search the web for information about a topic"
inputs      = { topic = "Text" }
output      = "SearchResult"
model       = "$standard"
prompt      = "What's the latest news on $topic?"
```

**What this does:** Takes a `Text` input, sends a search query to a web search provider, and produces a `SearchResult` output containing a synthesized answer and a list of sources.

**Key fields:**

| Field | Required | Description |
|-------|----------|-------------|
| `prompt` | Yes | The search query template. Supports Jinja2 syntax and `$variable` shorthand. |
| `model` | No | Model identifier, model reference (see [Model References](model-references.md)), or an inline settings table (see [Inline Settings](model-references.md#inline-settings)). |
| `from_date` | No | Start date filter in ISO 8601 format (YYYY-MM-DD). Only return results from this date onwards. |
| `to_date` | No | End date filter in ISO 8601 format (YYYY-MM-DD). Only return results up to this date. |
| `include_domains` | No | Restrict search to these domains only (e.g., `["reuters.com", "bbc.com"]`). |
| `exclude_domains` | No | Exclude results from these domains. |

**Constraints:** The output must be `SearchResult` or a concept that refines `SearchResult`.

## PipeCompose

Composes output by assembling data from working memory. PipeCompose has two modes: **template mode** and **construct mode**. Exactly one must be used.

### Template Mode

Uses a Jinja2 template to produce text output:

```toml
[pipe.format_report]
type        = "PipeCompose"
description = "Format analysis results into a report"
inputs      = { analysis = "CVAnalysis", candidate_name = "Text" }
output      = "Text"
template    = """
# Report for $candidate_name

@analysis.summary

Skills: $analysis.skills
"""
```

The `template` field can be a plain string (as above) or a table with additional options:

```toml
[pipe.format_report.template]
template = "# Report for $candidate_name"
category = "markdown"

[pipe.format_report.template.templating_style]
tag_style   = "xml"
text_format = "markdown"
```

#### Template Shorthand Syntax

MTHDS templates support three shorthand patterns that are preprocessed into Jinja2 before rendering. Raw Jinja2 (`{{ }}`, `{% %}`) is always available alongside the shorthands.

| Shorthand | Jinja2 Expansion | Purpose |
|-----------|-----------------|---------|
| `$variable` | `{{ variable|format() }}` | **Inline substitution** — embed a value within a sentence. |
| `@variable` | `{{ variable|tag("variable") }}` | **Block insertion** — insert content as a standalone, tagged block. |
| `@?variable` | `{% if variable %}{{ variable|tag("variable") }}{% endif %}` | **Conditional insertion** — render only if the variable is truthy. |

**Notes:**

- **Dotted paths** are supported with all three patterns: `$user.name`, `@doc.summary`, `@?extra.notes`.
- **Trailing dots** are treated as punctuation, not part of the path: `$amount.` expands to `{{ amount|format() }}.`
- **Dollar amounts** like `$100` or `$1,000` are **not** matched — the character after `$` must be a letter or underscore.
- **Raw Jinja2** is always available: `{{ variable_name }}`, `{% for item in items %}`, etc.

**Example combining all three patterns:**

```toml
[pipe.compose_prompt]
type        = "PipeCompose"
description = "Build an LLM prompt from structured inputs"
inputs      = { topic = "Text", context = "Text", guidelines = "Text" }
output      = "Text"
template    = """
Write an article about $topic.

@context

@?guidelines
"""
```

Here, `$topic` is inlined into the sentence, `@context` is inserted as a tagged block, and `@?guidelines` appears only if the variable has a value.

#### Template Categories

The `category` field determines which Jinja2 filters are registered and how the template environment is configured.

| Category | Use When | Autoescape | Trim Blocks | Available Filters |
|----------|----------|:----------:|:-----------:|-------------------|
| `basic` | General-purpose text composition | No | No | `format`, `tag` |
| `expression` | Simple expression evaluation | No | No | *(none)* |
| `html` | Generating HTML content | Yes | Yes | `format`, `tag`, `escape_script_tag` |
| `markdown` | Generating Markdown content | No | Yes | `format`, `tag`, `escape_script_tag` |
| `mermaid` | Generating Mermaid diagrams | No | No | *(none)* |
| `llm_prompt` | Composing prompts for LLMs | No | No | `format`, `tag`, `with_images` |
| `img_gen_prompt` | Composing prompts for image generation | No | No | `format`, `tag`, `with_images` |

**Guidance:** Use `basic` for most templates. Use `html` when generating web content (autoescape prevents XSS). Use `llm_prompt` when composing prompts that may include image references.

#### Available Filters

Filters transform variable content during rendering. The `$` and `@` shorthands apply `format()` and `tag()` automatically — you only need to call filters explicitly when using raw Jinja2 syntax.

| Filter | Syntax | Description | Categories |
|--------|--------|-------------|------------|
| `format` | `{{ var|format(text_format?) }}` | Formats a value as text. Optional `text_format` parameter: `plain`, `markdown`, `html`, `json`. Uses the context default if omitted. Applied automatically by `$`. | basic, html, markdown, llm_prompt, img_gen_prompt |
| `tag` | `{{ var|tag(tag_name?) }}` | Wraps content in tags based on the template's `tag_style`. The tag name defaults to the variable name. Applied automatically by `@` and `@?`. | basic, html, markdown, llm_prompt, img_gen_prompt |
| `escape_script_tag` | `{{ var|escape_script_tag() }}` | Escapes `</script>` tags to prevent injection. | html, markdown |
| `with_images` | `{{ var|with_images() }}` | Extracts nested images from structured content and returns text with `[Image N]` placeholders. | llm_prompt, img_gen_prompt |

#### Template Context

All declared inputs are available as variables in the template. The optional `extra_context` field (table form only) injects additional static variables:

```toml
[pipe.format_report.template]
template = "Version: $version — Report for $candidate_name"
category = "basic"

[pipe.format_report.template.extra_context]
version = "2.0"
```

Every variable referenced in the template must correspond to a declared input or an `extra_context` key.

**`category` values:** `basic`, `expression`, `html`, `markdown`, `mermaid`, `llm_prompt`, `img_gen_prompt`.

The optional `templating_style` table controls output formatting with `tag_style` (`no_tag`, `ticks`, `xml`, `square_brackets`) and `text_format` (`plain`, `markdown`, `html`, `json`). See the [specification](../spec/mthds-format.md#templating-style) for details.

### Construct Mode

Composes structured output field-by-field from working memory:

```toml
[pipe.compose_interview_sheet]
type        = "PipeCompose"
description = "Compose the final interview sheet"
inputs      = { match_analysis = "MatchAnalysis", interview_questions = "InterviewQuestion[]" }
output      = "InterviewSheet"

[pipe.compose_interview_sheet.construct]
overall_match_score  = { from = "match_analysis.overall_match_score" }
matching_skills      = { from = "match_analysis.matching_skills" }
missing_skills       = { from = "match_analysis.missing_skills" }
questions            = { from = "interview_questions" }
```

Each field in the `construct` table defines how a field of the output concept is composed:

| Value form | Method | Description |
|------------|--------|-------------|
| Literal (`string`, `integer`, `float`, `boolean`, `array`) | Fixed | The field value is the literal. |
| `{ from = "path" }` | Variable reference | The field value comes from a variable in working memory. |
| `{ from = "path", list_to_dict_keyed_by = "attr" }` | Variable reference with transform | Converts a list to a dict keyed by the named attribute. |
| `{ template = "..." }` | Template | The field value is rendered from a Jinja2 template string. |
| Nested table (no `from` or `template` key) | Nested construct | The field is recursively composed. |

**Constraint:** PipeCompose output must be a single concept — multiplicity (`[]` or `[N]`) is not allowed.

## See Also

- [Specification: Pipe Definitions](../spec/mthds-format.md#pipe-definitions) — normative reference for all pipe types and validation rules.
- [Pipes — Controllers](pipes-controllers.md) — orchestrating multiple pipes.
