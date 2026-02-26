# .mthds File Format

The `.mthds` file is a TOML document that defines typed data (concepts) and typed transformations (pipes) within a single domain. This page is the normative reference for every field, validation rule, and structural constraint of the format.

## File Encoding and Syntax

A `.mthds` file MUST be a valid TOML document encoded in UTF-8. The file extension MUST be `.mthds`. Parsers MUST reject files that are not valid TOML before any MTHDS-specific validation occurs.

## Top-Level Structure

A `.mthds` file is called a **bundle**. It consists of:

1. **Header fields** — top-level key-value pairs that identify the bundle.
2. **Concept definitions** — a `[concept]` table and/or `[concept.<ConceptCode>]` sub-tables.
3. **Pipe definitions** — `[pipe.<pipe_code>]` sub-tables.

All three sections are optional in the TOML sense (an empty `.mthds` file is valid TOML), but a useful bundle will contain at least one concept or one pipe.

## Header Fields

Header fields appear at the top level of the TOML document, before any `[concept]` or `[pipe]` tables.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `domain` | string | Yes | The domain this bundle belongs to. Determines the namespace for all concepts and pipes defined in this file. |
| `description` | string | No | A human-readable description of what this bundle provides. |
| `system_prompt` | string | No | A default system prompt applied to all `PipeLLM` pipes in this bundle that do not define their own `system_prompt`. |
| `main_pipe` | string | No | The pipe code of the bundle's primary entry point. If set, this pipe is auto-exported when the bundle is part of a package. |

**Validation rules:**

- `domain` MUST be a valid domain code (see [Domain Naming Rules](#domain-naming-rules)).
- `main_pipe`, if present, MUST be a valid pipe code (`snake_case`) and MUST reference a pipe defined in this bundle.

**Example:**

```toml
domain      = "legal.contracts"
description = "Contract analysis methods for legal documents"
main_pipe   = "extract_clause"
```

## Domain Naming Rules

Domain codes define the namespace for all concepts and pipes in a bundle.

**Syntax:**

- A domain code is one or more `snake_case` segments separated by `.` (dot).
- Each segment MUST match the pattern `[a-z][a-z0-9_]*`.
- Domains MAY be hierarchical: `legal`, `legal.contracts`, `legal.contracts.shareholder`.

**Reserved domains:**

The following domain names are reserved and MUST NOT be used as the first segment of any user-defined domain:

- `native` — built-in concept types
- `mthds` — reserved for the MTHDS standard
- `pipelex` — reserved for the reference implementation

A compliant implementation MUST reject bundles that declare a domain starting with a reserved segment (e.g., `native.custom` is invalid).

**Recommendations:**

- Depth SHOULD be 1–3 levels.
- Each segment SHOULD be 1–4 words.

## Concept Definitions

Concepts are typed data declarations. They define the vocabulary of a domain — the kinds of data that pipes accept and produce.

### Simple Concept Declarations

The simplest form of concept declaration uses a flat `[concept]` table where each key is a concept code and the value is a description string:

```toml
[concept]
ContractClause = "A clause extracted from a legal contract"
UserProfile    = "A user's profile information"
```

This form declares concepts with no structure and no refinement. They exist as named types.

### Structured Concept Declarations

A concept with fields uses a `[concept.<ConceptCode>]` sub-table:

```toml
[concept.LineItem]
description = "A single line item in an invoice"

[concept.LineItem.structure]
product_name = { type = "text", description = "Name of the product", required = true }
quantity     = { type = "integer", description = "Quantity ordered", required = true }
unit_price   = { type = "number", description = "Price per unit", required = true }
```

Both forms MAY coexist in the same bundle. A bundle MAY mix simple declarations in `[concept]` with structured declarations as `[concept.<Code>]` sub-tables.

### Concept Blueprint Fields

When using the structured form `[concept.<ConceptCode>]`, the following fields are available:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `description` | string | Yes | Human-readable description of the concept. |
| `structure` | table or string | No | Field definitions for the concept. If a string, it is a shorthand description (equivalent to a simple declaration). If a table, each key is a field name mapped to a field blueprint. |
| `refines` | string | No | A concept reference indicating that this concept is a specialization of another concept. |

**Validation rules:**

- `refines` and `structure` MUST NOT both be present on the same concept. A concept either refines another concept or defines its own structure, not both.
- `refines`, if present, MUST be a valid concept reference: either a bare concept code (`PascalCase`) or a domain-qualified reference (`domain.ConceptCode`). Cross-package references (`alias->domain.ConceptCode`) are also valid.
- Concept codes MUST be `PascalCase`, matching the pattern `[A-Z][a-zA-Z0-9]*`.
- Concept codes MUST NOT collide with native concept codes (see [Native Concepts](#native-concepts)).

### Concept Refinement

Refinement establishes a specialization relationship between concepts. A concept that refines another inherits its semantic meaning and can be used anywhere the parent concept is expected.

```toml
[concept.NonCompeteClause]
description = "A non-compete clause in an employment contract"
refines     = "ContractClause"
```

The `refines` field accepts:

- A bare concept code: `"ContractClause"` — resolved within the current bundle's domain.
- A domain-qualified reference: `"legal.ContractClause"` — resolved within the current package.
- A cross-package reference: `"acme_legal->legal.contracts.NonDisclosureAgreement"` — resolved from a dependency.

### Concept Structure Fields

When `structure` is a table, each key is a field name and each value is a field blueprint. Field names MUST NOT start with an underscore (`_`), as these are reserved for internal use. Field names MUST NOT collide with reserved field names (Pydantic model attributes and internal metadata fields).

#### Field Blueprint

Each field in a concept structure is defined by a field blueprint:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `description` | string | Yes | Human-readable description of the field. |
| `type` | string | Conditional | The field type. Required unless `choices` is provided. |
| `required` | boolean | No | Whether the field is required. Default: `false`. |
| `default_value` | any | No | Default value for the field. Must match the declared type. |
| `choices` | array of strings | No | Fixed set of allowed string values. When `choices` is set, `type` MUST be omitted (the type is implicitly an enum of the given choices). |
| `key_type` | string | Conditional | Key type for `dict` fields. Required when `type = "dict"`. |
| `value_type` | string | Conditional | Value type for `dict` fields. Required when `type = "dict"`. |
| `item_type` | string | No | Item type for `list` fields. When set to `"concept"`, `item_concept_ref` is required. |
| `concept_ref` | string | Conditional | Concept reference for `concept`-typed fields. Required when `type = "concept"`. |
| `item_concept_ref` | string | Conditional | Concept reference for list items when `item_type = "concept"`. |

#### Field Types

The `type` field accepts the following values:

| Type | Description | `default_value` type |
|------|-------------|---------------------|
| `text` | A string value. | `string` |
| `integer` | A whole number. | `integer` |
| `number` | A numeric value (integer or floating-point). | `integer` or `float` |
| `boolean` | A true/false value. | `boolean` |
| `date` | A date value. | `datetime` |
| `list` | An ordered collection. Use `item_type` to specify element type. | `array` |
| `dict` | A key-value mapping. Requires `key_type` and `value_type`. | `table` |
| `concept` | A reference to another concept. Requires `concept_ref`. Cannot have `default_value`. | *(not allowed)* |

When `type` is omitted and `choices` is provided, the field is an enumeration field. The value MUST be one of the strings in the `choices` array.

**Validation rules for field types:**

- `type = "dict"`: `key_type` and `value_type` MUST both be non-empty.
- `type = "concept"`: `concept_ref` MUST be set. `default_value` MUST NOT be set.
- `type = "list"` with `item_type = "concept"`: `item_concept_ref` MUST be set.
- `item_concept_ref` MUST NOT be set unless `item_type = "concept"`.
- `concept_ref` MUST NOT be set unless `type = "concept"`.
- If `choices` is provided and `type` is omitted, `default_value` (if present) MUST be one of the values in `choices`.
- If both `type` and `default_value` are set, the runtime type of `default_value` MUST match the declared `type`.

**Example — concept with all field types:**

```toml
[concept.CandidateProfile]
description = "A candidate's profile for job matching"

[concept.CandidateProfile.structure]
full_name        = { type = "text", description = "Full name", required = true }
years_experience = { type = "integer", description = "Years of professional experience" }
gpa              = { type = "number", description = "Grade point average" }
is_active        = { type = "boolean", description = "Whether actively looking", default_value = true }
graduation_date  = { type = "date", description = "Date of graduation" }
skills           = { type = "list", item_type = "text", description = "List of skills" }
metadata         = { type = "dict", key_type = "text", value_type = "text", description = "Additional metadata" }
seniority_level  = { description = "Seniority level", choices = ["junior", "mid", "senior", "lead"] }
address          = { type = "concept", concept_ref = "Address", description = "Home address" }
references       = { type = "list", item_type = "concept", item_concept_ref = "ContactInfo", description = "Professional references" }
```

## Native Concepts

Native concepts are built-in types that are always available in every bundle without declaration. They belong to the reserved `native` domain.

| Code | Qualified Reference | Description |
|------|-------------------|-------------|
| `Dynamic` | `native.Dynamic` | A dynamically-typed value. |
| `Text` | `native.Text` | A text string. |
| `Image` | `native.Image` | An image (binary). |
| `Document` | `native.Document` | A document (e.g., PDF). |
| `Html` | `native.Html` | HTML content. |
| `TextAndImages` | `native.TextAndImages` | Combined text and image content. |
| `Number` | `native.Number` | A numeric value. |
| `ImgGenPrompt` | `native.ImgGenPrompt` | A prompt for image generation. |
| `Page` | `native.Page` | A single page extracted from a document. |
| `JSON` | `native.JSON` | A JSON value. |
| `Anything` | `native.Anything` | Accepts any type. |

Native concepts MAY be referenced by bare code (`Text`, `Image`) or by qualified reference (`native.Text`, `native.Image`). Bare native concept codes always take priority during resolution.

A bundle MUST NOT declare a concept with the same code as a native concept. A compliant implementation MUST reject such declarations.

## Pipe Definitions

Pipes are typed transformations. Each pipe has a typed signature: it declares what concepts it accepts as input and what concept it produces as output.

### Common Pipe Fields

All pipe types share these base fields:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `type` | string | Yes | The pipe type. Determines which category and additional fields are available. |
| `description` | string | Yes | Human-readable description of what this pipe does. |
| `inputs` | table | No | Input declarations. Keys are input names (`snake_case`), values are concept references with optional multiplicity. |
| `output` | string | Yes | The output concept reference with optional multiplicity. |

**Pipe codes:**

- Pipe codes are the keys in `[pipe.<pipe_code>]` tables.
- Pipe codes MUST be `snake_case`, matching the pattern `[a-z][a-z0-9_]*`.

**Input names:**

- Input names MUST be `snake_case`.
- Dotted input names are allowed for nested field access (e.g., `my_input.field_name`), where each segment MUST be `snake_case`.

**Concept references in inputs and output:**

Concept references in `inputs` and `output` support an optional multiplicity suffix:

| Syntax | Meaning |
|--------|---------|
| `ConceptName` | A single instance. |
| `ConceptName[]` | A variable-length list (runtime determines count). |
| `ConceptName[N]` | A fixed-length list of exactly N items (N ≥ 1). |

Concept references MAY be bare codes (`Text`), domain-qualified (`legal.ContractClause`), or cross-package qualified (`alias->domain.ConceptCode`).

**Example:**

```toml
[pipe.analyze_contract]
type        = "PipeLLM"
description = "Analyze a legal contract and extract key clauses"
output      = "ContractClause[5]"

[pipe.analyze_contract.inputs]
contract_text = "Text"
```

### Pipe Types

MTHDS defines nine pipe types in two categories:

**Operators** — pipes that perform a single transformation:

| Type | Value | Description |
|------|-------|-------------|
| PipeLLM | `"PipeLLM"` | Generates output using a large language model. |
| PipeFunc | `"PipeFunc"` | Calls a registered Python function. |
| PipeImgGen | `"PipeImgGen"` | Generates images using an image generation model. |
| PipeExtract | `"PipeExtract"` | Extracts structured content from documents. |
| PipeCompose | `"PipeCompose"` | Composes output from templates or constructs. |

**Controllers** — pipes that orchestrate other pipes:

| Type | Value | Description |
|------|-------|-------------|
| PipeSequence | `"PipeSequence"` | Executes a series of pipes in order. |
| PipeParallel | `"PipeParallel"` | Executes pipes concurrently. |
| PipeCondition | `"PipeCondition"` | Routes execution based on a condition. |
| PipeBatch | `"PipeBatch"` | Maps a pipe over each item in a list. |

## Operator: PipeLLM

Generates output by invoking a large language model with a prompt.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `type` | `"PipeLLM"` | Yes | — |
| `description` | string | Yes | — |
| `inputs` | table | No | — |
| `output` | string | Yes | — |
| `prompt` | string | No | The LLM prompt template. Supports Jinja2 syntax and the `@variable` / `$variable` shorthand. |
| `system_prompt` | string | No | System prompt for the LLM. If omitted, the bundle-level `system_prompt` is used (if any). |
| `model` | string or table | No | Model identifier, model reference (see [Model References](../language/model-references.md)), or an inline [LLM settings](#inline-llm-settings) table. |
| `model_to_structure` | string or table | No | Model used for structuring the LLM output into the declared concept. Accepts the same forms as `model`. |
| `structuring_method` | string | No | How the output is structured. Values: `"direct"`, `"preliminary_text"`. |

**Prompt template syntax:**

- `{{ variable_name }}` — standard Jinja2 variable substitution.
- `@variable_name` — shorthand, preprocessed to Jinja2 syntax.
- `$variable_name` — shorthand, preprocessed to Jinja2 syntax.
- Dotted paths are supported: `{{ doc_request.document_type }}`, `@doc_request.priority`.

**Validation rules:**

- Every variable referenced in `prompt` and `system_prompt` MUST correspond to a declared input (by root name). Internal variables starting with `_` and the special names `preliminary_text` and `place_holder` are excluded from this check.
- Every declared input MUST be referenced by at least one variable in `prompt` or `system_prompt`. Unused inputs are rejected.

**Example:**

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

### Inline LLM Settings

When the `model` field is a table instead of a string, it defines inline model settings using the `LLMSetting` structure:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `model` | string | Yes | The model handle (e.g., `"claude-4.5-sonnet"`). |
| `temperature` | number | Yes | Sampling temperature. Range: 0–1. |
| `max_tokens` | integer, `"auto"`, or null | No | Maximum tokens for the response. `"auto"` lets the model choose. |
| `image_detail` | string | No | Image detail level for vision inputs. Values: `high`, `low`, `auto`. |
| `prompting_target` | string | No | Target provider for prompt formatting. Values: `openai`, `anthropic`, `mistral`, `gemini`, `fal`. |
| `reasoning_effort` | string | No | Level of reasoning effort. Values: `none`, `minimal`, `low`, `medium`, `high`, `max`. |
| `reasoning_budget` | integer | No | Token budget for reasoning. Must be > 0. |
| `description` | string | No | Human-readable description of this model configuration. |

**Validation rules:**

- `reasoning_effort` and `reasoning_budget` MUST NOT both be set on the same inline LLM settings table.

**Example — inline LLM settings:**

```toml
[pipe.analyze_cv]
type = "PipeLLM"
description = "Analyze a CV"
output = "CVAnalysis"
prompt = "Analyze: @cv_pages"
model = { model = "claude-4.5-sonnet", temperature = 0.1, max_tokens = 4096 }

[pipe.analyze_cv.inputs]
cv_pages = "Page"
```

## Operator: PipeFunc

Calls a registered Python function.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `type` | `"PipeFunc"` | Yes | — |
| `description` | string | Yes | — |
| `inputs` | table | No | — |
| `output` | string | Yes | — |
| `function_name` | string | Yes | The fully-qualified name of the Python function to call. |

**Example:**

```toml
[pipe.capitalize_text]
type          = "PipeFunc"
description   = "Capitalize the input text"
inputs        = { text = "Text" }
output        = "Text"
function_name = "my_package.text_utils.capitalize"
```

## Operator: PipeImgGen

Generates images using an image generation model.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `type` | `"PipeImgGen"` | Yes | — |
| `description` | string | Yes | — |
| `inputs` | table | No | — |
| `output` | string | Yes | — |
| `prompt` | string | Yes | The image generation prompt. Supports Jinja2 and `$variable` shorthand. |
| `negative_prompt` | string | No | A negative prompt (concepts to avoid in generation). |
| `model` | string or table | No | Model identifier, model reference (see [Model References](../language/model-references.md)), or an inline [image generation settings](#inline-image-generation-settings) table. |
| `aspect_ratio` | string | No | Desired aspect ratio. Values: `square`, `landscape_4_3`, `landscape_3_2`, `landscape_16_9`, `landscape_21_9`, `portrait_3_4`, `portrait_2_3`, `portrait_9_16`, `portrait_9_21`. |
| `is_raw` | boolean | No | Whether to use raw mode (less post-processing). |
| `seed` | integer or `"auto"` | No | Random seed for reproducibility. `"auto"` lets the model choose. |
| `background` | string | No | Background setting. Values: `transparent`, `opaque`, `auto`. |
| `output_format` | string | No | Image output format. Values: `png`, `jpeg`, `webp`. |

**Validation rules:**

- Every variable referenced in `prompt` MUST correspond to a declared input.

**Example:**

```toml
[pipe.generate_portrait]
type        = "PipeImgGen"
description = "Generate a portrait image from a description"
inputs      = { description = "Text" }
output      = "Image"
prompt      = "A professional portrait: $description"
model       = "$gen-image-testing"
```

### Inline Image Generation Settings

When the `model` field is a table instead of a string, it defines inline model settings using the `ImgGenSetting` structure:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `model` | string | Yes | The model handle. |
| `quality` | string | No | Image quality. Values: `low`, `medium`, `high`. |
| `nb_steps` | integer | No | Number of generation steps. Must be > 0. |
| `guidance_scale` | number | No | Guidance scale for generation. Must be > 0. |
| `is_moderated` | boolean | No | Whether to apply content moderation. Default: `false`. |
| `safety_tolerance` | integer | No | Safety tolerance level. Range: 1–6. |
| `description` | string | No | Human-readable description of this model configuration. |

**Validation rules:**

- `quality` and `nb_steps` MUST NOT both be set on the same inline image generation settings table.

**Example — inline image generation settings:**

```toml
[pipe.generate_portrait]
type        = "PipeImgGen"
description = "Generate a portrait image"
inputs      = { description = "Text" }
output      = "Image"
prompt       = "A professional portrait: $description"
aspect_ratio = "portrait_3_4"
model        = { model = "flux-pro", quality = "high" }
```

## Operator: PipeExtract

Extracts structured content from documents (e.g., PDF pages).

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `type` | `"PipeExtract"` | Yes | — |
| `description` | string | Yes | — |
| `inputs` | table | Yes | MUST contain exactly one input. |
| `output` | string | Yes | MUST be `"Page[]"`. |
| `model` | string or table | No | Model identifier, model reference (see [Model References](../language/model-references.md)), or an inline [extract settings](#inline-extract-settings) table. |
| `max_page_images` | integer | No | Maximum number of page images to process. |
| `page_image_captions` | boolean | No | Whether to generate captions for page images. |
| `page_views` | boolean | No | Whether to generate page views. |
| `page_views_dpi` | integer | No | DPI for page view rendering. |

**Validation rules:**

- `inputs` MUST contain exactly one entry. The input concept SHOULD be `Document` or a concept that refines `Document` or `Image`.
- `output` MUST be `"Page[]"` (a variable-length list of `Page`).

**Example:**

```toml
[pipe.extract_cv]
type        = "PipeExtract"
description = "Extract text content from a CV PDF document"
inputs      = { cv_pdf = "Document" }
output      = "Page[]"
model       = "@default-text-from-pdf"
```

### Inline Extract Settings

When the `model` field is a table instead of a string, it defines inline model settings using the `ExtractSetting` structure:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `model` | string | Yes | The model handle. |
| `max_nb_images` | integer | No | Maximum number of images to extract. Must be >= 0. |
| `image_min_size` | integer | No | Minimum image size in pixels. Must be >= 0. |
| `description` | string | No | Human-readable description of this model configuration. |

**Example — inline extract settings:**

```toml
[pipe.extract_cv]
type        = "PipeExtract"
description = "Extract text content from a CV PDF document"
inputs      = { cv_pdf = "Document" }
output      = "Page[]"
model       = { model = "gpt-4.1", max_nb_images = 10, image_min_size = 100 }
```

## Operator: PipeCompose

Composes output by assembling data from working memory using either a template or a construct. Exactly one of `template` or `construct` MUST be provided.

### Template Mode

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `type` | `"PipeCompose"` | Yes | — |
| `description` | string | Yes | — |
| `inputs` | table | No | — |
| `output` | string | Yes | MUST be a single concept (no multiplicity). |
| `template` | string or table | Yes (if no `construct`) | A Jinja2 template string, or a template blueprint table with `template`, `category`, `templating_style`, and `extra_context` fields. |

When `template` is a string, it is a Jinja2 template rendered with the input variables. When `template` is a table, it MUST contain a `template` field (string) and a `category` field, and MAY contain `templating_style` and `extra_context`.

**Template blueprint fields (table form):**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `template` | string | Yes | The Jinja2 template string. |
| `category` | string | Yes | Template category. Values: `basic`, `expression`, `html`, `markdown`, `mermaid`, `llm_prompt`, `img_gen_prompt`. |
| `templating_style` | table | No | Rendering style configuration. See [Templating Style](#templating-style) below. |
| `extra_context` | table | No | Additional context variables for template rendering. |

#### Templating Style

The `templating_style` field controls how template output is formatted, particularly useful for templates that produce prompts for different LLM providers.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `tag_style` | string | Yes | How variables are tagged in output. Values: `no_tag`, `ticks`, `xml`, `square_brackets`. |
| `text_format` | string | No | Output text format. Values: `plain`, `markdown`, `html`, `json`. Default: `plain`. |

**Validation rules (template mode):**

- Every variable referenced in the template MUST correspond to a declared input.
- `output` MUST NOT use multiplicity brackets (`[]` or `[N]`).

### Construct Mode

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `type` | `"PipeCompose"` | Yes | — |
| `description` | string | Yes | — |
| `inputs` | table | No | — |
| `output` | string | Yes | MUST be a single concept (no multiplicity). |
| `construct` | table | Yes (if no `template`) | A field-by-field composition blueprint. |

The `construct` table defines how each field of the output concept is composed. Each key is a field name, and the value defines the composition method:

| Value form | Method | Description |
|------------|--------|-------------|
| Literal (`string`, `integer`, `float`, `boolean`, `array`) | Fixed | The field value is the literal. |
| `{ from = "path" }` | Variable reference | The field value comes from a variable in working memory. `path` is a dotted path (e.g., `"match_analysis.score"`). |
| `{ from = "path", list_to_dict_keyed_by = "attr" }` | Variable reference with transform | Converts a list to a dict keyed by the named attribute. |
| `{ template = "..." }` | Template | The field value is rendered from a Jinja2 template string. |
| Nested table (no `from` or `template` key) | Nested construct | The field is recursively composed from a nested construct. |

**Validation rules (construct mode):**

- The root variable of every `from` path and every template variable MUST correspond to a declared input.
- `from` and `template` are mutually exclusive within a single field definition.

**Example — construct mode:**

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

## Controller: PipeSequence

Executes a series of sub-pipes in order. The output of each step is added to working memory and can be consumed by subsequent steps.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `type` | `"PipeSequence"` | Yes | — |
| `description` | string | Yes | — |
| `inputs` | table | No | — |
| `output` | string | Yes | — |
| `steps` | array of tables | Yes | Ordered list of sub-pipe invocations. MUST contain at least one step. |

Each step is a **sub-pipe blueprint**:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `pipe` | string | Yes | Pipe reference (bare, domain-qualified, or package-qualified). |
| `result` | string | No | Name under which the step's output is stored in working memory. |
| `nb_output` | integer | No | Expected number of output items. Mutually exclusive with `multiple_output`. |
| `multiple_output` | boolean | No | Whether to expect multiple output items. Mutually exclusive with `nb_output`. |
| `batch_over` | string | No | Working memory variable to iterate over (inline batch). Requires `batch_as`. |
| `batch_as` | string | No | Name for each item during inline batch iteration. Requires `batch_over`. |

**Validation rules:**

- `steps` MUST contain at least one entry.
- `nb_output` and `multiple_output` MUST NOT both be set on the same step.
- `batch_over` and `batch_as` MUST either both be present or both be absent.
- `batch_over` and `batch_as` MUST NOT be the same value.

**Example:**

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

## Controller: PipeParallel

Executes multiple sub-pipes concurrently. Each branch operates independently.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `type` | `"PipeParallel"` | Yes | — |
| `description` | string | Yes | — |
| `inputs` | table | No | — |
| `output` | string | Yes | — |
| `branches` | array of tables | Yes | List of sub-pipe invocations to execute concurrently. |
| `add_each_output` | boolean | No | If `true`, each branch's output is individually added to working memory under its `result` name. Default: `false`. |
| `combined_output` | string | No | Concept reference for a combined output that merges all branch results. |

**Validation rules:**

- At least one of `add_each_output` or `combined_output` MUST be set (otherwise the pipe produces no output).
- `combined_output`, if present, MUST be a valid concept reference.
- Each branch follows the same sub-pipe blueprint format as `PipeSequence` steps.

**Example:**

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

## Controller: PipeCondition

Routes execution to different pipes based on an evaluated condition.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `type` | `"PipeCondition"` | Yes | — |
| `description` | string | Yes | — |
| `inputs` | table | No | — |
| `output` | string | Yes | — |
| `expression_template` | string | Conditional | A Jinja2 template that evaluates to a string matching an outcome key. Exactly one of `expression_template` or `expression` MUST be provided. |
| `expression` | string | Conditional | A static expression string. Exactly one of `expression_template` or `expression` MUST be provided. |
| `outcomes` | table | Yes | Maps outcome strings to pipe references. MUST have at least one entry. |
| `default_outcome` | string | Yes | The pipe reference (or special outcome) to use when no outcome key matches. |
| `add_alias_from_expression_to` | string | No | If set, stores the evaluated expression value in working memory under this name. |

**Special outcomes:**

Certain string values in `outcomes` values and `default_outcome` have special meaning and are not treated as pipe references:

| Value | Meaning |
|-------|---------|
| `"fail"` | Abort execution with an error. |
| `"continue"` | Skip this branch and continue without executing a sub-pipe. |

**Example:**

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

## Controller: PipeBatch

Maps a single pipe over each item in a list input, producing a list output.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `type` | `"PipeBatch"` | Yes | — |
| `description` | string | Yes | — |
| `inputs` | table | Yes | MUST include an entry whose name matches `input_list_name`. |
| `output` | string | Yes | — |
| `branch_pipe_code` | string | Yes | The pipe reference to invoke for each item. |
| `input_list_name` | string | Yes | The name of the input that contains the list to iterate over. |
| `input_item_name` | string | Yes | The name under which each individual item is passed to the branch pipe. |

**Validation rules:**

- `input_list_name` MUST exist as a key in `inputs`.
- `input_item_name` MUST NOT be empty.
- `input_item_name` MUST NOT equal `input_list_name`.
- `input_item_name` MUST NOT equal any key in `inputs`.

**Example:**

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

## Pipe Reference Syntax

Every location in a `.mthds` file that references another pipe supports three forms:

| Form | Syntax | Example | Resolution |
|------|--------|---------|------------|
| Bare | `pipe_code` | `"extract_clause"` | Resolved within the current bundle and its domain. |
| Domain-qualified | `domain.pipe_code` | `"legal.contracts.extract_clause"` | Resolved within the named domain of the current package. |
| Package-qualified | `alias->domain.pipe_code` | `"docproc->extraction.extract_text"` | Resolved in the named domain of the dependency identified by the alias. |

Pipe references appear in:

- `steps[].pipe` (PipeSequence)
- `branches[].pipe` (PipeParallel)
- `outcomes` values (PipeCondition)
- `default_outcome` (PipeCondition)
- `branch_pipe_code` (PipeBatch)

Pipe *definitions* (the `[pipe.<pipe_code>]` table keys) are always bare `snake_case` names. Namespacing applies only to pipe *references*.

## Concept Reference Syntax

Every location that references a concept supports three forms, symmetric with pipe references:

| Form | Syntax | Example | Resolution |
|------|--------|---------|------------|
| Bare | `ConceptCode` | `"ContractClause"` | Resolved in order: native concepts → current bundle → same domain. |
| Domain-qualified | `domain.ConceptCode` | `"legal.contracts.NonCompeteClause"` | Resolved within the named domain of the current package. |
| Package-qualified | `alias->domain.ConceptCode` | `"acme->legal.ContractClause"` | Resolved in the named domain of the dependency identified by the alias. |

The disambiguation between concepts and pipes in a domain-qualified reference relies on casing:

- `snake_case` final segment → pipe code
- `PascalCase` final segment → concept code

Concept references appear in:

- `inputs` values
- `output`
- `refines`
- `concept_ref` and `item_concept_ref` in structure field blueprints
- `combined_output` (PipeParallel)

## Complete Bundle Example

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
