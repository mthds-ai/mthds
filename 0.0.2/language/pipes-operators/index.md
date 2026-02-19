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
| `model` | No | Model identifier or model reference (see [Model References](model-references.md)). |
| `model_to_structure` | No | Model used for structuring the LLM output into the declared concept. |
| `structuring_method` | No | How the output is structured: `"direct"` or `"preliminary_text"`. |

**Prompt template syntax:**

- `{{ variable_name }}` — standard Jinja2 variable substitution.
- `@variable_name` — shorthand, preprocessed to Jinja2 syntax.
- `$variable_name` — shorthand, preprocessed to Jinja2 syntax.
- Dotted paths are supported: `{{ doc_request.document_type }}`, `@doc_request.priority`.

Every variable referenced in the prompt must correspond to a declared input, and every declared input must be referenced in the prompt or system prompt. Unused inputs are rejected.

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
| `model` | No | Model identifier or model reference (see [Model References](model-references.md)). |
| `aspect_ratio` | No | Desired aspect ratio for the generated image. |
| `seed` | No | Random seed for reproducibility. `"auto"` lets the model choose. |
| `output_format` | No | Image output format (e.g., `"png"`, `"jpeg"`). |

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
| `model` | No | Model identifier or model reference (see [Model References](model-references.md)). |
| `max_page_images` | No | Maximum number of page images to process. |
| `page_image_captions` | No | Whether to generate captions for page images. |
| `page_views` | No | Whether to generate page views. |
| `page_views_dpi` | No | DPI for page view rendering. |

**Constraints:** PipeExtract requires exactly one input (typically `Document` or a concept refining it) and the output must be `"Page[]"`.

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
# Report for {{ candidate_name }}

{{ analysis.summary }}

Skills: {{ analysis.skills }}
"""
```

The `template` field can be a plain string (as above) or a table with additional options:

```toml
[pipe.format_report.template]
template        = "# Report for {{ candidate_name }}"
category        = "basic"
templating_style = "default"
```

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
