---
description: "Complete specification of the .mthds file format — TOML sections for concepts, pipes, domains, and metadata."
---

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
| `hints` | table | No | Optional [intent hints](./intent-hints.md) for the concept — non-normative presentation intent that applies wherever the concept is presented. |

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

A field's value is either a **field blueprint table** or a **bare string**, which is shorthand for a required text field: `summary = "A one-line summary"` declares exactly what `summary = { type = "text", required = true, description = "A one-line summary" }` declares. The shorthand carries a description and nothing else, so a field needing any other key is written as a table.

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
| `hints` | table | No | Optional [intent hints](./intent-hints.md) for the field — non-normative presentation intent. |

The keys of a field blueprint are a **closed set**, exactly like an [input slot table](#input-slot-declarations)'s. A key this table does not define MUST be rejected — a hopeful key (`minimum`, `examples`, `unit`, …) that validated green would be silently dropped, and an author would have no way to learn the field never carried what they wrote.

#### Field Types

The `type` field accepts the following values:

| Type | Description | `default_value` type |
|------|-------------|---------------------|
| `text` | A string value. | `string` |
| `integer` | A whole number. | `integer` |
| `number` | A numeric value (integer or floating-point). | `integer` or `float` |
| `boolean` | A true/false value. | `boolean` |
| `date` | A calendar date value. | `datetime` |
| `datetime` | A date with a time of day (a point in time). | `datetime` |
| `time` | A time of day, optionally with a UTC offset. | `time` |
| `list` | An ordered collection. Use `item_type` to specify element type. | `array` |
| `dict` | A key-value mapping. Requires `key_type` and `value_type`. | `table` |
| `concept` | A reference to another concept. Requires `concept_ref`. Cannot have `default_value`. | *(not allowed)* |

When `type` is omitted and `choices` is provided, the field is an enumeration field. The value MUST be one of the strings in the `choices` array.

**Validation rules for field types:**

- `type = "dict"`: `key_type` and `value_type` MUST both be non-empty.
- `value_type = "Any"` is a **reserved marker** declaring the dict's value type unspecified: the values are arbitrary, and a consumer surfaces the field as declared imprecision (e.g. `dict[str, Any]` with a caveat), never as a guessed value shape. It appears primarily in materialized [native concept definitions](./native-concepts.md); authors SHOULD declare a concrete value type instead.
- `type = "concept"`: `concept_ref` MUST be set. `default_value` MUST NOT be set.
- `type = "list"` with `item_type = "concept"`: `item_concept_ref` MUST be set.
- `item_concept_ref` MUST NOT be set unless `item_type = "concept"`.
- `concept_ref` MUST NOT be set unless `type = "concept"`.
- If `choices` is provided and `type` is omitted, `default_value` (if present) MUST be one of the values in `choices`.
- If both `type` and `default_value` are set, the runtime type of `default_value` MUST match the declared `type`.
- A field MUST NOT declare both `required = true` and `default_value`. A default means "applied when the caller omits the field", which makes absence legal; `required` means "must be present". The pair is two contradictory instructions on one field, and it fails validation rather than resolving to whichever the implementation happens to check first.

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
last_seen_at     = { type = "datetime", description = "Last activity timestamp" }
preferred_slot   = { type = "time", description = "Preferred interview time of day" }
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
| `Document` | `native.Document` | A document (e.g., PDF, web page). |
| `Html` | `native.Html` | HTML content. |
| `TextAndImages` | `native.TextAndImages` | Combined text and image content. |
| `Number` | `native.Number` | A numeric value. |
| `YesNo` | `native.YesNo` | The answer to a yes/no question. |
| `Choice` | `native.Choice` | One option picked out of a declared set. |
| `Rating` | `native.Rating` | A position on an ordered scale of described levels. |
| `Date` | `native.Date` | A calendar date, optionally with a time of day. |
| `Time` | `native.Time` | A time of day, optionally with a UTC offset. |
| `Page` | `native.Page` | A single page extracted from a document. |
| `JSON` | `native.JSON` | A JSON value. |
| `SearchResult` | `native.SearchResult` | A web search result with answer and sources. |
| `Anything` | `native.Anything` | Accepts any type. |
| `Composite` | `native.Composite` | A named composition of contents. |

Native concepts MAY be referenced by bare code (`Text`, `Image`) or by qualified reference (`native.Text`, `native.Image`). Bare native concept codes always take priority during resolution.

A bundle MUST NOT declare a concept with the same code as a native concept. A compliant implementation MUST reject such declarations.

Each native concept's exact blueprint form — its fields, their types, and their descriptions — is pinned per standard version in [Native Concept Definitions](./native-concepts.md). Implementations MUST use the pinned definitions verbatim (no reflection over internal runtime types) wherever a native's structural definition is needed, such as [library crate materialization](./library-crate.md#4-expand-native-concepts).

## Pipe Definitions

Pipes are typed transformations. Each pipe has a typed signature: it declares what concepts it accepts as input and what concept it produces as output.

### Common Pipe Fields

Concrete pipe types share these base fields:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `type` | string | Yes for concrete pipes | The pipe type. Determines which category and additional fields are available. Omitted only for contract-only `PipeSignature` declarations. |
| `description` | string | Yes | Human-readable description of what this pipe does. |
| `inputs` | table | No | Input declarations. Keys are input names (`snake_case`), values are input slot declarations (see [Input slot declarations](#input-slot-declarations)). |
| `output` | string | Yes | The output concept reference with optional multiplicity. |

**Pipe codes:**

- Pipe codes are the keys in `[pipe.<pipe_code>]` tables.
- Pipe codes MUST be `snake_case`, matching the pattern `[a-z][a-z0-9_]*`.

**Input names:**
{ #input-names }

- Input names MUST be `snake_case`.
- Dotted input names are allowed for nested field access (e.g., `my_input.field_name`), where each segment MUST be `snake_case`. A dotted input name MUST be written as a single quoted TOML key (`"my_input.field_name" = "Text"`), never as an unquoted dotted path: TOML parses the latter as nested tables, which the [expanded slot form](#input-slot-declarations) would misread as a slot table.

**Concept references in inputs and output:**
{ #concept-references-in-inputs-and-output }

Concept references in `inputs` and `output` support an optional multiplicity suffix and, for pipe declarations only, a presence marker:

| Syntax | Meaning |
|--------|---------|
| `ConceptName` | A single instance. |
| `ConceptName[]` | A variable-length list (runtime determines count). |
| `ConceptName[N]` | A fixed-length list of exactly N items (N ≥ 2). |
| `ConceptName[1]` | A single instance — the same slot as `ConceptName`, with the count written out. Not a one-item list. |
| `ConceptName?` | Optional single value. The slot may resolve as a recorded absence. |
| `ConceptName!` | Forced single input. If the slot is absent at run time, the run fails loudly. Inputs only. |

The **bracketed count** MUST be at least 1: `ConceptName[0]` is invalid, because a fixed count of zero declares a slot that can hold nothing. A count of exactly one is **single throughout the standard** — `ConceptName[1]` is a way of writing `ConceptName`, never a one-element list — so nothing downstream wraps such a value in an array, and a fixed count reported on any wire is always greater than one. Every artifact that carries multiplicity states the same rule: the [library crate](./library-crate.md#5-materialize-defaults-and-multiplicity) materializes it, and [pipe I/O contracts](./pipe-io-contracts.md#multiplicity-and-item-count), the [input-form descriptor](./input-form-descriptor.md#structured-multiplicity) and the [output-form descriptor](./output-form-descriptor.md#plurality-is-on-the-descriptor-never-on-the-concept) report it.

Concept references MAY be bare codes (`Text`), domain-qualified (`legal.ContractClause`), or cross-package qualified (`alias->domain.ConceptCode`).

Presence markers have these constraints:

- Markers apply only to pipe `inputs` and `output`, not concept definitions, `refines`, or structure fields.
- Markers MUST NOT be combined with multiplicity. `Concept[]?`, `Concept[N]?`, `Concept[]!`, and `Concept[N]!` are invalid because plural slots use an empty list when no items are produced.
- `!` MUST NOT appear on `output`. A force marker is an input-side assertion.

**Input slot declarations:**
{ #input-slot-declarations }

Each value in `inputs` declares one input slot, in one of two forms. The **string form** is a concept reference with optional multiplicity and presence marker, as specified above. The **expanded form** is a table:

```toml
[pipe.summarize]
type        = "PipeLLM"
description = "Summarize a contract, following optional steering instructions"
output      = "Summary"

[pipe.summarize.inputs]
contract     = "legal.Contract"
instructions = { concept = "Text?", hints = { intent = "prose" } }
```

Rules for the expanded form:

- `concept` (string) is required and carries exactly the same grammar as the string form — a concept reference with optional multiplicity and optional presence marker. `x = "S"` and `x = { concept = "S" }` are equivalent.
- `hints` (table) is optional and attaches [intent hints](./intent-hints.md) to the slot.
- No other keys are defined in this version of the standard. An unknown key in an input slot table MUST be rejected. (The form is deliberately shaped so that future versions can add per-slot authoring fields — such as a slot description — without a second syntax.)
- The expanded form applies to `inputs` only. `output` is always a string.

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

MTHDS defines pipe types in two categories:

**Operators** — pipes that perform a single transformation:

| Type | Value | Description |
|------|-------|-------------|
| PipeLLM | `"PipeLLM"` | Generates output using a large language model. |
| PipeStructure | `"PipeStructure"` | Turns text into a structured concept using a large language model. |
| PipeFunc | `"PipeFunc"` | Calls a registered Python function. |
| PipeImgGen | `"PipeImgGen"` | Generates images using an image generation model. |
| PipeExtract | `"PipeExtract"` | Extracts structured content from documents. |
| PipeSearch | `"PipeSearch"` | Searches the web and returns structured results. |
| PipeJudge | `"PipeJudge"` | Asks a judging model a closed question about its inputs and returns a verdict. |
| PipeCompose | `"PipeCompose"` | Composes output from templates or constructs. |

**Controllers** — pipes that orchestrate other pipes:

| Type | Value | Description |
|------|-------|-------------|
| PipeSequence | `"PipeSequence"` | Executes a series of pipes in order. |
| PipeParallel | `"PipeParallel"` | Executes pipes concurrently. |
| PipeCondition | `"PipeCondition"` | Routes execution based on a condition. |
| PipeBatch | `"PipeBatch"` | Maps a pipe over each item in a list. |

### Contract-Only Pipe Signatures

A `[pipe.<pipe_code>]` section with no `type` is a `PipeSignature` when it contains only contract fields:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `description` | string | Yes | Human-readable description of the intended pipe. |
| `inputs` | table | No | Input declarations, in either [input slot form](#input-slot-declarations) — the string form, or the expanded form with `hints`. |
| `output` | string | Yes | Output concept reference. Multiplicity and `?` are supported. |
| `signature_for` | string | No | Optional hint naming the concrete pipe type expected later, such as `"PipeLLM"`. |

`PipeSignature` is not a pipe type value. Authors MUST NOT write `type = "PipeSignature"`. A typeless pipe section that contains implementation fields such as `prompt`, `steps`, `branches`, or `model` is invalid because concrete implementations must declare their `type`.

**Example:**

```toml
[pipe.summarize_doc]
description   = "Summarize a source document"
inputs        = { document = "Document" }
output        = "Text"
signature_for = "PipeLLM"
```

### Inputs Read Through Templates

PipeLLM, PipeImgGen, PipeSearch and PipeCompose read their inputs through templates, and the validation rules of each operator name the fields that do the reading. For these four operators the input rule runs in both directions: every variable those fields reference MUST correspond to a declared input, apart from the names the operator's own rules exclude, and every declared input MUST be read by at least one of them. A declared input that no such field reads is rejected.

A template variable reads an input when the variable's dotted path is the input's name, or begins with the input's name followed by a dot:

- `$deal.customer_name` reads the input `deal`.
- A [dotted input name](#input-names) such as `"page.page_view"` is read by `@page.page_view` or `{{ page.page_view.text }}`, but not by `@page` alone. PipeImgGen, PipeSearch and PipeCompose match every variable they read against a declared input by its root, so on these operators the root `page` MUST be declared as well.
- An optional (`?`) input is not exempt. A conditional reference such as `@?note` or `{% if note %}…{% endif %}` reads it.

PipeJudge is not among these operators. Its inputs reach the model as the named material the question is asked about, not through its `question` template, so a declared input it never references is still read (see [Operator: PipeJudge](#operator-pipejudge)).

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
| `structuring_method` | string | No | Directive controlling how the output is structured. Values: `"direct"` (single LLM call producing JSON) or `"preliminary_text"` (the runtime first produces text, then structures it as a second step). The standard does not prescribe HOW the runtime implements `"preliminary_text"`. |
| `templating_style` | string or table | No | How the pipe's inputs are tagged and formatted when interpolated into the prompt. Either a tag style string (`no_tag`, `ticks`, `xml`, `square_brackets`) or a [templating style](#templating-style) table carrying `tag_style` and `text_format`. If omitted, the runtime default applies. |

**Prompt template syntax:**

- `{{ variable_name }}` — standard Jinja2 variable substitution.
- `@variable_name` — shorthand, preprocessed to Jinja2 syntax.
- `$variable_name` — shorthand, preprocessed to Jinja2 syntax.
- Dotted paths are supported: `{{ doc_request.document_type }}`, `@doc_request.priority`.

**Validation rules:**

- Every variable referenced in `prompt` and `system_prompt` MUST correspond to a declared input (by root name). Internal variables starting with `_` and the special names `preliminary_text` and `place_holder` are excluded from this check.
- Every declared input MUST be referenced by at least one variable in `prompt` or `system_prompt`. Unused inputs are rejected (see [Inputs Read Through Templates](#inputs-read-through-templates)).

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
| `reasoning_effort` | string | No | Level of reasoning effort. Values: `none`, `minimal`, `low`, `medium`, `high`, `xhigh`, `max`. `xhigh` sits between `high` and `max` and maps to provider-specific xhigh values where supported. |
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

## Operator: PipeStructure

Turns text into a structured concept matching the declared output schema. The standard does not prescribe how a runtime achieves this; a typical implementation uses an LLM call.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `type` | `"PipeStructure"` | Yes | — |
| `description` | string | Yes | — |
| `inputs` | table | Yes | MUST contain exactly one entry. |
| `output` | string | Yes | The target structured concept reference, with optional multiplicity. MUST NOT be `Text` or a concept that refines `Text`. |
| `model` | string or table | No | Model identifier, model reference (see [Model References](../language/model-references.md)), or an inline [LLM settings](#inline-llm-settings) table. |

**Validation rules:**

- `inputs` MUST contain exactly one entry. The single input concept MUST be `Text` or a concept that refines `Text`.
- `output` MUST NOT be `Text` and MUST NOT be a concept that refines `Text`.
- `output` MAY use multiplicity (`Foo`, `Foo[]`, `Foo[N]`).
- `PipeStructure` MUST NOT accept image or document inputs. Use an upstream extraction step to produce text first.

**Example:**

```toml
[pipe.structure_review]
type        = "PipeStructure"
description = "Turn a free-form review into a RestaurantReview"
inputs      = { review_text = "Text" }
output      = "RestaurantReview"
```

**Example — with an explicit structuring model:**

```toml
[pipe.structure_review_premium]
type        = "PipeStructure"
description = "Use a stronger model for tricky structurings"
inputs      = { review_text = "Text" }
output      = "RestaurantReview"
model       = "@default-premium"
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

Generates images using an image generation model. The pipe carries a required `prompt` string template (and an optional `negative_prompt` template); it does not take a dedicated prompt concept as input. Declared `inputs` are injected into the `prompt` at runtime: `Text` inputs are interpolated into the prompt text, while `Image` inputs (a single image or a list) are referenced in the prompt and injected as reference images — each becomes an `[Image N]` token in the rendered text and is passed to the generator alongside it, enabling image-to-image, reference-image, and image-editing generation.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `type` | `"PipeImgGen"` | Yes | — |
| `description` | string | Yes | — |
| `inputs` | table | No | — |
| `output` | string | Yes | — |
| `prompt` | string | Yes | The image generation prompt template. Supports Jinja2 and `$variable` shorthand; declared inputs are injected into it. |
| `negative_prompt` | string | No | An optional prompt template describing what to avoid in the generated image. |
| `model` | string or table | No | Model identifier, model reference (see [Model References](../language/model-references.md)), or an inline [image generation settings](#inline-image-generation-settings) table. |
| `aspect_ratio` | string | No | Desired aspect ratio. Values: `square`, `landscape_4_3`, `landscape_3_2`, `landscape_16_9`, `landscape_21_9`, `portrait_3_4`, `portrait_2_3`, `portrait_9_16`, `portrait_9_21`. |
| `is_raw` | boolean | No | Whether to use raw mode (less post-processing). |
| `seed` | integer or `"auto"` | No | Random seed for reproducibility. `"auto"` lets the model choose. |
| `background` | string | No | Background setting. Values: `transparent`, `opaque`, `auto`. |
| `output_format` | string | No | Image output format. Values: `png`, `jpeg`, `webp`. |

**Validation rules:**

- Every variable referenced in `prompt` or `negative_prompt` MUST correspond to a declared input.
- Every declared input MUST be referenced by at least one variable in `prompt` or `negative_prompt`. Unused inputs are rejected (see [Inputs Read Through Templates](#inputs-read-through-templates)).
- `output` MUST resolve to an `Image`-compatible concept.
- Any input referenced as a reference image in the `prompt` or `negative_prompt` MUST resolve to an `Image`-compatible concept (single or list).

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

**Example with a reference image (image-to-image):**

```toml
[pipe.restyle_photo]
type        = "PipeImgGen"
description = "Restyle a source photo following a textual instruction"
inputs      = { source = "Image", instruction = "Text" }
output      = "Image"
prompt      = "Restyle this image: $source. $instruction"
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

Extracts structured content from documents (e.g., PDF, web pages).

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
| `render_js` | boolean | No | Web-page extraction only: render JavaScript before fetching the page content. Honored by backends that support headless rendering. Default: `false`. |
| `include_raw_html` | boolean | No | Web-page extraction only: include the fetched HTML in each extracted `Page`'s `raw_html` field. Default: `false`. |

**Validation rules:**

- `inputs` MUST contain exactly one entry. The input concept SHOULD be `Document` or a concept that refines `Document` or `Image`.
- `output` MUST be `"Page[]"` (a variable-length list of `Page`).
- When the document URL is a web page, PipeExtract fetches and extracts the page content. `render_js` and `include_raw_html` apply only to this case; backends that target local documents (PDFs, images) MAY ignore them.

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

## Operator: PipeSearch

Searches the web using a search provider and returns structured results.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `type` | `"PipeSearch"` | Yes | — |
| `description` | string | Yes | — |
| `inputs` | table | No | — |
| `output` | string | Yes | MUST be `SearchResult` or a concept that refines `SearchResult`. |
| `prompt` | string | Yes | The search query template. Supports Jinja2 syntax and the `@variable` / `$variable` shorthand. |
| `model` | string or table | No | Model identifier, model reference (see [Model References](../language/model-references.md)), or an inline [search settings](#inline-search-settings) table. |
| `from_date` | string | No | Start date filter in ISO 8601 format (YYYY-MM-DD). Only return results from this date onwards. |
| `to_date` | string | No | End date filter in ISO 8601 format (YYYY-MM-DD). Only return results up to this date. |
| `include_domains` | array of strings | No | Restrict search to these domains only (e.g., `["reuters.com", "bbc.com"]`). |
| `exclude_domains` | array of strings | No | Exclude results from these domains. |

**Validation rules:**

- Every variable referenced in `prompt` MUST correspond to a declared input.
- Every declared input MUST be referenced by at least one variable in `prompt`. Unused inputs are rejected (see [Inputs Read Through Templates](#inputs-read-through-templates)).
- `output` MUST be `SearchResult` or a concept that refines `SearchResult`.

**Example:**

```toml
[pipe.search_topic]
type        = "PipeSearch"
description = "Search the web for information about a topic"
inputs      = { topic = "Text" }
output      = "SearchResult"
model       = "$standard"
prompt      = "What is $topic?"
```

**Example — with date and domain filters:**

```toml
[pipe.search_recent_from_sources]
type            = "PipeSearch"
description     = "Search specific sources for recent news"
inputs          = { topic = "Text" }
output          = "SearchResult"
model           = "$standard"
prompt          = "What are the latest developments about $topic?"
from_date       = "2026-01-01"
include_domains = ["reuters.com", "apnews.com", "bbc.com"]
```

### Inline Search Settings

When the `model` field is a table instead of a string, it defines inline model settings using the `SearchSetting` structure:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `model` | string | Yes | The model handle. |
| `include_images` | boolean | No | Whether to include images in results. Default: `false`. |
| `include_inline_citations` | boolean | No | Whether to include inline citations. Default: `true`. |
| `max_results` | integer or null | No | Maximum number of results. Must be ≥ 1. |
| `description` | string | No | Human-readable description of this model configuration. |

**Example — inline search settings:**

```toml
[pipe.deep_search]
type        = "PipeSearch"
description = "Deep research on a topic"
inputs      = { topic = "Text" }
output      = "SearchResult"
prompt      = "What are the main details about $topic?"
model       = { model = "linkup-deep", include_images = false }
```

## Operator: PipeJudge

Asks a judging model one closed question about its inputs and returns the verdict with whatever uncertainty the model reports: a yes or a no, one option out of a declared set, or one level on a declared scale.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `type` | `"PipeJudge"` | Yes | — |
| `description` | string | Yes | — |
| `inputs` | table | No | The material the question is asked about. |
| `output` | string | Yes | MUST agree with the question's kind: `YesNo`, `Choice` or `Rating`, or a concept that refines it. |
| `question` | string | Yes (if no `prompt`) | The question template. Supports Jinja2 syntax and the `@variable` / `$variable` shorthand. |
| `prompt` | string | Yes (if no `question`) | A synonym of `question`, read exactly as it. |
| `model` | string or table | No | Model identifier, model reference (see [Model References](../language/model-references.md)), or an inline [judgment settings](#inline-judgment-settings) table. |
| `options` | table | No | The options of a choice question: each key is an option, each value describes it. |
| `levels` | array of strings | No | The levels of a rating question, from lowest to highest, each describing a situation. |
| `criteria` | table | No | What a yes and a no mean, for a yes/no question: optional `yes` and `no` descriptions. |
| `threshold` | number | No | For a yes/no question, the probability of yes at or above which the verdict is yes. |

**The question's kind** is decided by which of `options` and `levels` the pipe declares, never by a separate field:

| The pipe declares | Kind | `output` MUST be |
|-------------------|------|------------------|
| neither `options` nor `levels` | yes/no | `YesNo` or a concept that refines it |
| `options` | choice | `Choice` or a concept that refines it |
| `levels` | rating | `Rating` or a concept that refines it |

**`prompt` is a synonym of `question`.** Every other inference operator calls its template `prompt`, so a PipeJudge MAY spell the field `prompt` instead, and an implementation MUST read it exactly as `question`. Exactly one of the two MUST be set: a pipe setting both is rejected, and the rejection names `question`. A tool that writes a PipeJudge MUST write `question`.

**The inputs are the material, not the question.** Every declared input is presented to the judging model by name, beside the question and separate from it, so the model judges the material rather than a paraphrase of it. An implementation SHOULD present the material as one object with one member per declared input, keyed by the input's name. An optional input that resolves as a recorded absence is left out of the material. The question MAY also reference an input, which suits a short parameter (`"Is the message about $topic?"`), and such an input is still part of the material.

**Validation rules:**

- Exactly one of `question` and `prompt` MUST be set.
- Every variable referenced in `question` MUST correspond to a declared input. A declared input need not be referenced.
- `options` and `levels` MUST NOT both be set.
- `options`, when set, MUST hold at least two options. Each key MUST be a non-empty string, and each value a string; an empty string is an option with no description.
- `levels`, when set, MUST hold at least two levels, each a non-empty string. A level's position in the array is its index, counted from `0`.
- `criteria` and `threshold` MUST NOT be set beside `options` or `levels`.
- `criteria`, when set, MUST be a table whose keys are among `yes` and `no`, each a string. Any other key MUST be rejected.
- `threshold`, when set, MUST be a number strictly between `0` and `1`.
- `output` MUST agree with the question's kind, per the table above, and MUST NOT carry a multiplicity suffix: a PipeJudge produces one verdict. To judge each item of a list, map the PipeJudge over it with a [PipeBatch](#controller-pipebatch).

**The verdict.** The output is a [verdict native](./native-concepts.md#verdict-natives) whose required member is always set, and whose uncertainty members are set only when the judging model reports them:

- A yes/no question produces a `YesNo`. When the model reports a probability of yes, `probability` carries it.
- A choice question produces a `Choice` whose `choice` is one of the keys of `options`, and whose `probabilities`, when present, are keyed by those same keys.
- A rating question produces a `Rating` whose `level` is an index into `levels`, and whose `probabilities`, when present, are keyed by those indices written as text.

An implementation MUST NOT synthesize an uncertainty member the model did not report — no `probability` of `1` read off a bare yes, no `confidence` invented for a model that has none.

**The threshold.** When a yes/no question's model reports a probability, `yes_no` is `true` exactly when that probability is at or above `threshold`, and the default threshold is `0.5`. When the model reports no probability, the threshold has nothing to apply to and the model's own verdict stands; when the pipe declares a `threshold`, an implementation SHOULD warn that it was not applied.

Because a `Choice`'s `choice` is a plain string, a [PipeCondition](#controller-pipecondition) routes on it directly, with one outcome per option key.

**Example — a yes/no question:**

```toml
[pipe.judge_is_urgent]
type        = "PipeJudge"
description = "Decide whether a message is urgent"
inputs      = { message = "Text" }
output      = "YesNo"
question    = "Is the message urgent?"
threshold   = 0.8

[pipe.judge_is_urgent.criteria]
yes = "The sender needs an answer today, or something stops working without one"
no  = "The message can wait for the next working day"
```

**Example — a choice question:**

```toml
[pipe.route_ticket]
type        = "PipeJudge"
description = "Pick the team that should handle a ticket"
inputs      = { ticket = "Ticket" }
output      = "Choice"
question    = "Which team should handle the ticket?"

[pipe.route_ticket.options]
returns  = "Exchanges, refunds, wrong or damaged items"
shipping = "Delivery status, delays, lost packages"
billing  = "Charges, invoices, payment problems"
other    = "None of the above"
```

**Example — a rating question:**

```toml
[pipe.rate_severity]
type        = "PipeJudge"
description = "Rate how severe a reported issue is"
inputs      = { report = "BugReport" }
output      = "Rating"
question    = "How severe is the reported issue?"
levels      = [
  "Cosmetic; no impact on functionality",
  "Broken or degraded feature, but a workaround exists",
  "Blocking issue; no workaround exists",
]
```

### Inline Judgment Settings

When the `model` field is a table instead of a string, it defines inline model settings using the `JudgmentSetting` structure:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `model` | string | Yes | The model handle. |
| `description` | string | No | Human-readable description of this model configuration. |

**Example — inline judgment settings:**

```toml
[pipe.judge_is_spam]
type        = "PipeJudge"
description = "Decide whether an email is spam"
inputs      = { email = "Text" }
output      = "YesNo"
question    = "Is the email unsolicited bulk advertising?"
model       = { model = "verdict-small", description = "A fast model for screening" }
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

**Template shorthand syntax:**

MTHDS defines three shorthand patterns that a compliant preprocessor MUST expand before Jinja2 rendering:

| Pattern | Expansion | Description |
|---------|-----------|-------------|
| `$name` | `{{ name|format() }}` | Inline substitution with formatting. |
| `@name` | `{{ name|tag("name") }}` | Block insertion with tagging. |
| `@?name` | `{% if name %}{{ name|tag("name") }}{% endif %}` | Conditional block insertion (renders only if truthy). |

**Rules:**

- A shorthand pattern MUST NOT match when the character immediately following `$`, `@`, or `@?` is a digit (`0`–`9`). This prevents dollar amounts (e.g., `$100`) and version-like strings (e.g., `@2.0`) from being treated as variables.
- Dotted paths are supported: `$user.name`, `@doc.summary`, `@?extra.notes`. Each segment of the dotted path MUST be a valid identifier.
- When a matched name ends with a `.` (dot), the preprocessor MUST strip the trailing dot from the variable name and place it after the expanded expression (treating it as sentence punctuation).
- Raw Jinja2 syntax (`{{ }}`, `{% %}`) MUST always be accepted alongside the shorthands.

These shorthands apply to the `template` field of PipeCompose, the `prompt` and `system_prompt` fields of PipeLLM, the `prompt` and `negative_prompt` fields of PipeImgGen, the `prompt` field of PipeSearch, and the `question` field of PipeJudge (or `prompt`, its synonym). See [Pipes — Operators: Template Mode](../language/pipes-operators.md#template-mode) for the full reference on categories and filters.

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
- Every declared input MUST be referenced by at least one variable in the template. Unused inputs are rejected (see [Inputs Read Through Templates](#inputs-read-through-templates)).
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
- Every declared input MUST be referenced by at least one `from` path or by at least one variable in a field template, nested constructs included. Unused inputs are rejected (see [Inputs Read Through Templates](#inputs-read-through-templates)).
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

Executes a series of steps in order. A step either runs a pipe or binds a value already in working memory to a new name, and what each step stores in working memory can be consumed by the steps after it.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `type` | `"PipeSequence"` | Yes | — |
| `description` | string | Yes | — |
| `inputs` | table | No | — |
| `output` | string | Yes | — |
| `steps` | array of tables | Yes | Ordered list of steps, each a pipe step or a binding step. MUST contain at least one step. |

Each step is either a **pipe step**, which runs a pipe, or a **binding step**, which binds the value at a path in working memory to a new name (see [Binding Steps](#binding-steps)). A step carrying `pipe` is a pipe step, and a step carrying `from` is a binding step. Each shape is a closed table: a pipe step carries no `from`, and a binding step carries no field of a pipe step other than `result`.

**Pipe step:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `pipe` | string | Yes | Pipe reference (bare, domain-qualified, or package-qualified). |
| `result` | string | No | Name under which the step's output is stored in working memory. |
| `nb_output` | integer | No | Expected number of output items. Mutually exclusive with `multiple_output`. |
| `multiple_output` | boolean | No | Whether to expect multiple output items. Mutually exclusive with `nb_output`. |
| `batch_over` | string | No | Working memory variable to iterate over (inline batch). Requires `batch_as`. A dotted path such as `catalog.pages` is a binding followed by a batch: the path is bound by the rules of a binding step, and the step iterates over the bound list (see [Dotted `batch_over`](#dotted-batch_over)). |
| `batch_as` | string | No | Name for each item during inline batch iteration. Requires `batch_over`. |

**Binding step:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `from` | string | Yes | The path to bind: a name in working memory, followed by zero or more field names, separated by dots (see [Path Grammar](#path-grammar)). |
| `result` | string | Yes | Name under which the bound value is stored in working memory, to be read by a later step's input or as the root of a later binding. It MUST be a plain [input name](#input-names), a `snake_case` identifier matching `[a-z][a-z0-9_]*` and so never dotted. |

**Validation rules:**

- `steps` MUST contain at least one entry.
- `nb_output` and `multiple_output` MUST NOT both be set on the same step.
- `batch_over` and `batch_as` MUST either both be present or both be absent.
- `batch_over` and `batch_as` MUST NOT be the same value.
- A dotted `batch_over` MUST follow the [path grammar](#path-grammar), or the step is rejected as `binding_step_invalid`, and its walk MUST derive a list (see [Dotted `batch_over`](#dotted-batch_over)).
- A step MUST carry exactly one of `pipe` and `from`. A step carrying both is rejected as `binding_step_invalid`. A step carrying neither, such as `{ result = "x" }`, is neither a pipe step nor a binding step, and the schema rejects it with no error name of its own.
- A binding step MUST carry `result`, and MUST NOT carry `nb_output`, `multiple_output`, `batch_over` or `batch_as`, or the step is rejected as `binding_step_invalid`.
- A binding step's `result` MUST be a plain input name, matching `[a-z][a-z0-9_]*`, or the step is rejected as `binding_step_invalid`.
- A binding step's `from` MUST follow the [path grammar](#path-grammar), or the step is rejected as `binding_step_invalid`, and its path MUST be walkable through the declared structures, or the step is rejected as `binding_path_unresolved` (see [The Concept of the Result](#the-concept-of-the-result)).

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

### Binding Steps

A binding step binds the value at a path in working memory to a new name, so that the steps after it can read one field of a larger value, or the same value under another name, without a pipe written to do it:

```toml
[concept.Invoice]
description = "An invoice received from a supplier"

[concept.Invoice.structure]
supplier_name = { type = "text", description = "The supplier's name", required = true }
total         = { type = "number", description = "The total amount due", required = true }

[pipe.review_invoice]
type        = "PipeSequence"
description = "Decide whether an invoice needs a manager's approval"
inputs      = { invoice = "Invoice" }
output      = "YesNo"
steps = [
    { from = "invoice.total", result = "total_amount" },
    { pipe = "judge_large_amount", result = "needs_approval" },
]

[pipe.judge_large_amount]
type        = "PipeJudge"
description = "Decide whether an amount needs a manager's approval"
inputs      = { total_amount = "Number" }
output      = "YesNo"
question    = "Is an invoice total of $total_amount large enough to need a manager's approval?"
```

The first step binds the invoice's `total` field under the name `total_amount`, as a `Number`, and the judge declares exactly that input. The judge's signature names a whole concept, and the sequence, which knows the invoice's concept, picks the field at the call site. Because a PipeJudge presents its inputs whole to the judging model, the model receives the amount and nothing else of the invoice.

Binding steps live in a PipeSequence's `steps` only. A binding orders a value before the steps that read it, and only a sequence has an order: a [PipeParallel](#controller-pipeparallel) branch is always a pipe step, and a value its branches need is bound by a sequence step before the parallel. PipeCondition and PipeBatch have no steps.

#### Path Grammar

`from` is a path. Its first segment, the root, names a value in working memory: an input of the sequence or the `result` of an earlier step. Each following segment, zero or more, names a field of the value the path has reached. Segments are separated by single dots, and each segment MUST be an identifier: a letter followed by letters, digits and underscores, matching `[A-Za-z][A-Za-z0-9_]*`. A segment therefore never starts with an underscore, which marks private names. Subscripts (`lines[0]`), expressions and whitespace are not part of the grammar: a path names fields, and anything computed is a pipe's job. A `from` that breaks the grammar is rejected as `binding_step_invalid`.

A path with no dot is a bare name, which binds a renamed copy of the whole value (see [A Bare Name Binds a Renamed Copy](#a-bare-name-binds-a-renamed-copy)).

#### The Concept of the Result

The result's concept is derived statically, before any run, by walking the path through declared structures. The walk starts from the root's concept and multiplicity as the sequence knows them at the binding step, which are those of the latest value stored under the root's name before that step, in step order:

- When one or more earlier steps stored a value under the root's name, the root takes the concept and multiplicity of the most recent of them, whether that is a pipe step's output (a list when the step batches or asks for several outputs), the result of a branch of a PipeParallel step with `add_each_output`, or the result of an earlier binding step.
- Only when no earlier step stored a value under that name does the root take the concept and multiplicity that the sequence's own `inputs` declare for it.

A step that stores its result under the name of a sequence input therefore replaces that input for every later binding step, which walks from the concept of the replacement, not from the one the input declares. The walk then reads one segment at a time, finding the field the segment names in the structure of the concept it stands on:

| The segment names a field declared as | The walk continues into, or the result is |
|---|---|
| `type = "concept"`, `concept_ref = X` | `X`, whose structure the next segment walks |
| `type = "list"`, `item_type = "concept"`, `item_concept_ref = X` | `X`, crossing a list (see [Lists Map and Flatten](#lists-map-and-flatten)) |
| `type = "text"`, or `choices` | `native.Text`, a leaf |
| `type = "number"` or `type = "integer"` | `native.Number`, a leaf |
| `type = "boolean"` | `native.YesNo`, a leaf |
| `type = "date"` or `type = "datetime"` | `native.Date`, a leaf, since a `Date` carries a calendar date with an optional time of day |
| `type = "time"` | `native.Time`, a leaf |
| `type = "list"` with any other `item_type` | the native concept that `item_type` gives by the rows above, a leaf, crossing a list |
| `type = "dict"` | `native.JSON`, a leaf |

The walk reads only the concept references the structures declare. A field the table above calls a leaf holds a plain value, which has no fields of its own, so the walk always ends on it, whatever native concept it derives. A native concept reached through a concept reference is walked through its [pinned definition](./native-concepts.md), so `page.page_view` is a `native.Image` and `page.page_view.caption` is a `native.Text`. The exceptions are the natives whose pinned definition is a single field holding the value itself, which are leaves wherever the walk reaches them. A concept that [refines](#concept-refinement) another is walked through the structure it inherits. The walk never infers a concept from the shape of a value: several concepts can share one structure, and only the declaration says which of them a field holds.

**A native that holds its value in a single field is a leaf wherever it is reached.** A native concept whose pinned definition is a single field holding the value itself, rather than a part of it, is a leaf for the walk, and so is any concept that refines one: a path never enters it. In the pinned set, these natives are `Text`, whose field is `text`, `Number`, whose field is `number`, `Time`, whose field is `time`, and `JSON`, whose field is `json_obj`. How the walk reached the concept makes no difference: a field declared `type = "number"` and a field declared `type = "concept"` with `concept_ref = "native.Number"` both derive `native.Number`, and both end the walk. A path may end on such a concept, but no segment may follow it: `from = "note.text"`, over a `note` holding a `Text`, is rejected as `binding_path_unresolved`, and so is `from = "invoice.total.number"` over the invoice above, whether `Invoice` declares `total` as a number field or as a reference to `native.Number`. Every other native that has a structure, such as `YesNo`, `Date`, `Image` or `Page`, carries several fields and is walked through its pinned definition when a concept reference leads to it.

When the walk crosses no list, the result is a single value of the concept the walk ends on. When it crosses at least one list, the result is a variable-length list of that concept, `X[]`. A bare name has no segment to walk, and its result takes the root's concept and multiplicity unchanged. A step that reads the result is checked against the derived concept and multiplicity exactly as it would be against a pipe's output, and a binding step that ends the sequence is checked against the sequence's `output` the same way.

The walk refuses the path, and the step is rejected as `binding_path_unresolved`, when:

- a segment names no field of the structure it walks;
- a segment follows a leaf: a field the table above calls a leaf, or, however the walk reached it, a native whose pinned definition is a single field holding the value itself, such as `Text`, `Number`, `Time` or `JSON`, or any concept that refines one of them;
- a segment follows a `dict` field, or a `list` field with no `item_type`;
- a segment walks a concept that has no structure, which is any concept declared with neither a `structure` nor `refines`, any of the [structureless natives](./native-concepts.md#reading-the-definitions) `Dynamic`, `Anything` and `Composite`, and any concept that refines one of them;
- the path ends on a `list` field with no `item_type`, whose items have no concept to derive.

The diagnostic names the segment that failed and lists the fields that were available at that point, so that a typo can be repaired from the message alone.

#### Lists Map and Flatten

When the walk crosses a list, whether the root is a list or a field along the path is one, the rest of the path is applied to every item. Every list crossed is flattened into one, so the result is always a single list, never a list of lists. Wherever a segment holds nothing, on one item or on a single value before the first list is reached, that part of the path contributes no items: such items are dropped, the way a PipeBatch drops absent branch results. An empty list is a valid result, and a list result is never absent.

- `pages.page_view`, over `pages` holding `Page[]`, gives `Image[]`, one image per page that has a page view.
- `order.lines.amount`, where `lines` is a list of `OrderLine` and each line declares a number field `amount`, gives `Number[]`.
- `shipments.parcels`, over `shipments` holding `Shipment[]` whose `parcels` field is a list of `Parcel`, gives one flat `Parcel[]`.

#### Absence

A binding step introduces no new kind of absence: like a pipe's output under the [optionality model](../language/optionality.md#runtime-behavior), a single result is either a value or a recorded absence, and a list result is never absent.

- **The root is absent.** The root is read like a plain input, so the binding step lifts the way a pipe with an absent plain input does: a single result is recorded as a skipped absence, with provenance pointing to the root's absence. A list result is an empty list instead, since a plural slot is never absent.
- **The path reaches nothing.** When the result is a single value and a segment holds nothing, at the leaf or at any segment before it (`invoice.scan.url` on an invoice with no `scan`), the result is a recorded absence whose provenance names the segment that held nothing. This is not an error. When the result is a list, the [list rule](#lists-map-and-flatten) applies instead.
- **Statically,** a single result may be absent when its root may be absent, judged from the same latest value stored under the root's name that gives the root its concept (see [The Concept of the Result](#the-concept-of-the-result)), or when its path walks a field that may hold nothing, meaning one that is not `required` and has no `default_value`. Structure fields default to `required = false`, so most single-value bindings may be absent unless the concept marks the field required, which is correct, since the data may lack the field. A list result is never considered maybe-absent.

What follows is the existing machinery: a step reading the result through a plain input lifts when it is absent, a step reading it through an optional (`?`) input runs and guards the read, and a sequence whose output can be absent MUST declare its output `?`.

#### The Value Is a Copy

The result is a new value holding a deep copy of the value at the path, taken when the step runs. It is never an alias of the root: a later step that stores a new value under the root's name, or anything that changes the root's content, leaves the bound value as it was, and a change to the bound value leaves the root as it was. The whole value at the path is copied, every field of a concept included, never field by field, so a bound `Image` keeps its `caption` and every other field it holds.

A leaf holding a plain value is stored as its derived native concept, with the value in that concept's pinned field: a text field's string becomes a `Text` whose `text` is the string, a number or an integer becomes a `Number`, a boolean a `YesNo`, a date a `Date`, a datetime a `Date` carrying both its date and its time of day, a time a `Time`, and a dict a `JSON`. The new value has its own identity, and the binding step is its producer wherever an implementation records which step produced a value.

#### A Bare Name Binds a Renamed Copy

A path with no field segment binds a deep copy of the whole value under a new name, with the same concept and multiplicity:

```toml
steps = [
    { from = "departure_board", result = "board" },
    { pipe = "announce_delays", result = "announcement" },
]
```

Working memory matches a pipe's inputs by name, so this is how a sequence hands a value to a pipe whose input has another name: here `announce_delays` declares `board`, and the sequence holds the value as `departure_board`.

#### Dotted `batch_over`

A pipe step whose `batch_over` is a dotted path is a binding followed by a batch. `{ pipe = "describe_view", batch_over = "pages.page_view", batch_as = "page_view" }` behaves exactly as a binding step of `pages.page_view` under a private name that no other step can read, followed by the same pipe step with `batch_over` naming that private name. The path follows every rule of a binding step. Its root takes the concept and multiplicity of the latest value stored under its name before the step, in step order, and those the sequence's `inputs` declare only when no earlier step stored that name (see [The Concept of the Result](#the-concept-of-the-result)). Its concept is derived by the same walk, it maps and flattens across lists, so a dotted path over a list of catalogs iterates over the pages of all of them, and it lifts and records absences the same way.

A dotted `batch_over` MUST bind a list: its walk MUST cross at least one list, whether the root is a list, a field along the path is one, or the path ends on a list field. A dotted `batch_over` whose walk derives a single value, such as `batch_over = "invoice.supplier_name"` over the invoice above, is rejected before any run, and an implementation reports it the way it reports a `batch_over` naming a value that is not a list. A dotted `batch_over` that breaks the [path grammar](#path-grammar), such as `a..b` or `pages[0].x`, is rejected as `binding_step_invalid`, as a binding step's `from` would be.

A dotted `batch_over` binds, and only a sequence's steps can bind, so a [PipeParallel](#controller-pipeparallel) branch MUST NOT carry one: a branch whose `batch_over` is a dotted path is rejected as `binding_step_invalid`, which the schema catches, exactly as a binding step placed in a branch is. A plain `batch_over` on a branch is unaffected. A branch that needs to iterate over a list held in a field gets it from the calling sequence, which binds the field in a step before the PipeParallel step, so that the branch's plain `batch_over` names the bound list.

#### Validation Surface

A compliant implementation SHOULD report a binding step's own faults under these names:

| Error | Fault | Caught by |
|-------|-------|-----------|
| `binding_step_invalid` | A step carrying both `pipe` and `from`; a binding step lacking `result` or carrying `nb_output`, `multiple_output`, `batch_over` or `batch_as`; a binding step whose `result` is not a plain input name matching `[a-z][a-z0-9_]*`; a `from` that breaks the [path grammar](#path-grammar); a dotted `batch_over` that breaks the path grammar; a binding step in a PipeParallel's `branches`; a dotted `batch_over` in a PipeParallel's `branches`. | The schema. |
| `binding_path_unresolved` | A path the declared structures cannot walk, under the refusals listed in [The Concept of the Result](#the-concept-of-the-result). | Validation of the bundle, which reads the concepts' structures, before any run. |

A binding step can also cause faults that are not its own, and an implementation reports each of them the way it reports the same fault caused by a pipe step: a root that is neither an input of the sequence nor stored by an earlier step, whose diagnostic asks for the concept whose structure holds the path; a step that reads the result through an input declaring a concept or multiplicity incompatible with the ones the binding derives; a binding step ending the sequence whose derived concept or multiplicity does not match the sequence's declared `output`; and a dotted `batch_over` whose walk derives a single value, which is reported as a `batch_over` naming a value that is not a list. A maybe-absent result escaping a sequence whose output is not `?` is `optional_not_handled`, as [Optionality](../language/optionality.md#validation-surface) defines it.

## Controller: PipeParallel

Executes multiple sub-pipes concurrently. Each branch operates independently, then the branch results are combined into the pipe's declared `output`.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `type` | `"PipeParallel"` | Yes | — |
| `description` | string | Yes | — |
| `inputs` | table | No | — |
| `output` | string | Yes | Combined output concept. MUST be `Composite` or a structured concept whose fields match branch `result` names. MUST NOT use multiplicity. |
| `branches` | array of tables | Yes | List of pipe steps to execute concurrently. |
| `add_each_output` | boolean | No | If `true`, each branch's output is individually added to working memory under its `result` name. Default: `false`. |

**Validation rules:**

- `branches` MUST contain at least one entry.
- `output` MUST be `Composite` or a structured concept.
- `output` MUST NOT use multiplicity brackets (`[]` or `[N]`).
- For structured output, required fields MUST be produced by matching branch `result` names and branch output concepts MUST be compatible with the corresponding fields.
- `add_each_output` controls only whether branch results are also exposed individually in working memory. It does not control the main output.
- Each branch is a pipe step, in the format of a [PipeSequence](#controller-pipesequence) pipe step. A branch MUST NOT be a binding step: a branch carrying `from` is rejected as `binding_step_invalid`, and a value the branches need is bound by a sequence step before the parallel.
- A branch MUST NOT carry a dotted `batch_over`, which is a binding followed by a batch (see [Dotted `batch_over`](#dotted-batch_over)): such a branch is rejected as `binding_step_invalid`, while a plain `batch_over` on a branch is unaffected.

**Example:**

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

- `inputs` values — the string form, or the `concept` key of the [expanded form](#input-slot-declarations)
- `output`
- `refines`
- `concept_ref` and `item_concept_ref` in structure field blueprints

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
