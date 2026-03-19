# Concepts

Concepts are typed data declarations. They define the vocabulary of a domain — the kinds of data that pipes accept as input and produce as output.

## Simple Concepts

The simplest form of concept declaration uses a flat `[concept]` table. Each key is a concept code, and the value is a description string:

```toml
[concept]
ContractClause = "A clause extracted from a legal contract"
UserProfile    = "A user's profile information"
```

These concepts exist as named types. They have no internal structure — they are semantic labels that give meaning to data flowing through pipes.

**Naming rule:** Concept codes must be `PascalCase`, matching the pattern `[A-Z][a-zA-Z0-9]*`. Examples: `ContractClause`, `UserProfile`, `CVAnalysis`.

### Naming Guidelines

Beyond the PascalCase rule, follow these principles for clear, reusable concept names:

**1. Define what it is, not what it's for.**

```toml
[concept]
# Avoid — includes usage context
TextToSummarize = "Text that needs to be summarized"

# Prefer — defines the essence
Article = "A written composition on a specific topic"
```

A concept should describe the nature of the data, not the role it plays in a particular pipe.

**2. Use singular forms.**

```toml
[concept]
# Avoid — plural form
Invoices = "Commercial documents from sellers"

# Prefer — singular form
Invoice = "A commercial document issued by a seller to a buyer"
```

Concepts are always singular. Use [multiplicity](multiplicity.md) to express quantity.

**3. Avoid unnecessary adjectives.**

```toml
[concept]
# Avoid — includes subjective qualifier
LongArticle = "A lengthy written composition"

# Prefer — neutral description
Article = "A written composition on a specific topic"
```

Keep concept names factual and neutral. Qualitative distinctions belong in the pipe logic, not in the concept name.

## Structured Concepts

When a concept needs internal structure — specific fields with types — use a `[concept.<ConceptCode>]` sub-table:

```toml
[concept.LineItem]
description = "A single line item in an invoice"

[concept.LineItem.structure]
product_name = { type = "text", description = "Name of the product", required = true }
quantity     = { type = "integer", description = "Quantity ordered", required = true }
unit_price   = { type = "number", description = "Price per unit", required = true }
```

The `structure` table defines the fields of the concept. Each field has a type and a description.

Both simple and structured forms can coexist in the same bundle:

```toml
[concept]
ContractClause = "A clause extracted from a legal contract"

[concept.LineItem]
description = "A single line item in an invoice"

[concept.LineItem.structure]
product_name = { type = "text", description = "Name of the product", required = true }
quantity     = { type = "integer", description = "Quantity ordered", required = true }
unit_price   = { type = "number", description = "Price per unit", required = true }
```

## Concept Blueprint Fields

When using the structured form `[concept.<ConceptCode>]`:

| Field | Required | Description |
|-------|----------|-------------|
| `description` | Yes | Human-readable description of the concept. |
| `structure` | No | Field definitions. If a string, it is a shorthand description (equivalent to a simple declaration). If a table, each key is a field name mapped to a field blueprint. |
| `refines` | No | A concept reference indicating specialization of another concept. |

`refines` and `structure` cannot both be present on the same concept. A concept either refines another concept or defines its own structure, not both.

## Field Types

Each field in a concept's `structure` is defined by a field blueprint. The `type` field determines the kind of data:

| Type | Description | Example `default_value` |
|------|-------------|------------------------|
| `text` | A string value. | `"hello"` |
| `integer` | A whole number. | `42` |
| `number` | A numeric value (integer or floating-point). | `3.14` |
| `boolean` | A true/false value. | `true` |
| `date` | A date value. | *(datetime)* |
| `list` | An ordered collection. Use `item_type` to specify element type. | `["a", "b"]` |
| `dict` | A key-value mapping. Requires `key_type` and `value_type`. | *(table)* |
| `concept` | A reference to another concept. Requires `concept_ref`. Cannot have a `default_value`. | *(not allowed)* |

When `type` is omitted and `choices` is provided, the field becomes an enumeration — its value must be one of the listed strings.

## Field Blueprint Reference

The complete set of attributes available on each field in a concept's `structure`:

| Attribute | Required | Description |
|-----------|----------|-------------|
| `description` | Yes | Human-readable description. |
| `type` | Conditional | The field type (see table above). Required unless `choices` is provided. |
| `required` | No | Whether the field is required. Default: `false`. |
| `default_value` | No | Default value, must match the declared type. |
| `choices` | No | Fixed set of allowed string values. When set, `type` must be omitted. |
| `key_type` | Conditional | Key type for `dict` fields. Required when `type = "dict"`. |
| `value_type` | Conditional | Value type for `dict` fields. Required when `type = "dict"`. |
| `item_type` | No | Item type for `list` fields. When `"concept"`, requires `item_concept_ref`. |
| `concept_ref` | Conditional | Concept reference for `concept`-typed fields. Required when `type = "concept"`. |
| `item_concept_ref` | Conditional | Concept reference for list items when `item_type = "concept"`. |

## A Complete Example

This concept demonstrates every field type:

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

## Concept Refinement

Refinement establishes a specialization relationship between concepts. A refined concept inherits the semantic meaning of its parent and can be used anywhere the parent is expected.

```toml
[concept.NonCompeteClause]
description = "A non-compete clause in an employment contract"
refines     = "ContractClause"
```

`NonCompeteClause` is a specialization of `ContractClause`. Any pipe that accepts `ContractClause` also accepts `NonCompeteClause`.

!!! note "Type Compatibility — Substitutability"
    Refined concepts are **substitutable** for their parent. If a pipe declares `inputs = { clause = "ContractClause" }`, you can pass a `NonCompeteClause` (or any other concept that refines `ContractClause`) as the `clause` input. This follows the standard subtyping rule: a specialized type is always valid where the general type is expected.

The `refines` field accepts three forms of concept reference:

- **Bare code:** `"ContractClause"` — resolved within the current bundle's domain.
- **Domain-qualified:** `"legal.ContractClause"` — resolved within the current package.
- **Cross-package:** `"acme_legal->legal.contracts.NonDisclosureAgreement"` — resolved from a dependency.

Cross-package refinement is how you build on another package's vocabulary without merging namespaces. See [Namespace Resolution](namespace-resolution.md) for the full resolution rules.

## When to Refine vs. When to Create a New Concept

Choosing between refinement and a new concept depends on the semantic relationship and whether you need custom structure.

**Refine** when the new concept is genuinely a specialized version of an existing one and the parent's structure is sufficient:

```toml
[concept.Invoice]
description = "A commercial document issued by a seller to a buyer"
refines = "Document"

[concept.VIPCustomer]
description = "A high-value customer with special privileges"
refines = "Customer"
```

Refinement is the right choice when you want substitutability — an `Invoice` can be used wherever a `Document` is expected.

**Create a new concept** when the data needs its own structure, or when it does not naturally fit as a subtype of any existing concept:

```toml
[concept.InvoiceData]
description = "Extracted data from an invoice"

[concept.InvoiceData.structure]
invoice_number = { type = "text", description = "Invoice identifier", required = true }
total_amount   = { type = "number", description = "Total amount due" }
line_items     = { type = "list", item_type = "concept", item_concept_ref = "LineItem", description = "Invoice line items" }
```

!!! tip "Don't over-refine"
    Avoid creating refinements for distinctions that belong in processing logic rather than in the type system. For example, `SmallInvoice` and `LargeInvoice` are better handled as a single `Invoice` concept with the pipe deciding how to process different amounts.

## Native Concepts

MTHDS provides a set of built-in concepts that are always available in every bundle without declaration. They belong to the reserved `native` domain.

| Code | Description |
|------|-------------|
| `Dynamic` | A dynamically-typed value. |
| `Text` | A text string. |
| `Image` | An image (binary). |
| `Document` | A document (e.g., PDF, web page). |
| `Html` | HTML content. |
| `TextAndImages` | Combined text and image content. |
| `Number` | A numeric value. |
| `ImgGenPrompt` | A prompt for image generation. |
| `Page` | A single page extracted from a document. |
| `JSON` | A JSON value. |
| `SearchResult` | A web search result with answer and sources. |
| `Anything` | Accepts any type. |

Native concepts can be referenced by bare code (`Text`, `Image`) or by qualified reference (`native.Text`, `native.Image`). Bare native codes always take priority during name resolution.

A bundle cannot declare a concept with the same code as a native concept. For example, defining `[concept] Text = "My custom text"` is an error.

### Native Concept Fields

The most commonly used native concepts have the following fields. These are the fields you can reference in prompts via dot notation (e.g., `$page_content.page_view`).

**Text** — a single `text` field containing the string value.

**Image** — `url` (location of the image), `source_prompt` (the prompt used to generate it, if applicable), `caption` (descriptive text), `base_64` (base64-encoded image data, alternative to URL).

**Document** — `url` (location of the document file or web page), `mime_type` (e.g., `"application/pdf"`), `title` (optional display name), `snippet` (optional text excerpt).

**Number** — a single `number` field (integer or floating-point).

**TextAndImages** — `text` (the text content), `images` (a list of images associated with the text).

**Page** — `text_and_images` (the extracted text and embedded images from the page), `page_view` (a screenshot or rendering of the entire page as an image).

**SearchResult** — `answer` (the synthesized answer text), `sources` (a list of source citations, each a Document with `title`, `url`, and `snippet`).

**JSON** — a single `json_obj` field containing the JSON object.

## See Also

- [Specification: Concept Definitions](../spec/mthds-format.md#concept-definitions) — normative reference for all concept fields and validation rules.
- [Pipes — Operators](pipes-operators.md) — how concepts are used as pipe inputs and outputs.
- [Native Concepts table](../spec/mthds-format.md#native-concepts) — full list with qualified references.
