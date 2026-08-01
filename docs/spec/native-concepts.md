---
description: "Normative, version-pinned definitions of the MTHDS native concepts — the exact blueprint form every implementation materializes, hashes, and projects."
---

# Native Concept Definitions

Native concepts are the built-in vocabulary of the MTHDS standard: always available in every bundle, never declared by authors. This page pins their **normative definitions** — the exact blueprint form of each native concept, expressed in the same structure language authors use for their own concepts (see [Concept Structure Fields](./mthds-format.md#concept-structure-fields)).

These definitions are **pinned per MTHDS standard version**. The set below is normative for MTHDS `1.0.0`. Any change to a definition — a field added, a type changed, a description reworded — is a change to the standard and requires a version bump. An implementation MUST NOT derive these definitions from its own runtime types (reflection over internal classes makes one implementation's quirks the de-facto standard); it materializes them by **lookup into this pinned set**, selected by the standard version it implements.

Three consequences follow:

- **Crate materialization is a copy, not a computation.** When a [library crate](./library-crate.md) expands native concepts ([normalization step 4](./library-crate.md#4-expand-native-concepts)), each referenced native is materialized into `concepts` as the `native.<Code>` concept object equivalent to its definition below. The crate's `mthds_version` records which pinned set was used.
- **Fingerprints byte-agree across implementations.** Because the materialized form derives from this page rather than from any implementation's internals, two independent implementations normalizing the same library produce the same materialized natives — and therefore the same [fingerprint](./library-crate.md#fingerprint). Every part of a definition participates in the hash, including field `description` strings.
- **Some definitions reference other definitions.** `native.TextAndImages` references `native.Text` and `native.Image`; `native.Page` references `native.TextAndImages` and `native.Image`; `native.SearchResult` references `native.Document`. Every other definition in the pinned set is a leaf, and the graph is acyclic, so materializing a native into a crate pulls in at most two further hops and always terminates. A crate MUST carry that whole transitive closure — materializing `native.Page` without `native.TextAndImages`, `native.Image`, and `native.Text` produces a crate that is not closed ([normalization step 4](./library-crate.md#4-expand-native-concepts)).

## Reading the Definitions

Each definition is written in authored TOML form. In a crate, the same definition appears as the JSON concept object keyed `native.<Code>`: the `description`, and the `structure` table with one field blueprint per field, exactly as pinned — field order preserved, `required` explicit only where `true` (the default is `false`). Materialized natives carry no `source` field: they originate from this page, not from a file in the closure. The preserved field order governs the crate's *emitted encodings*; the [fingerprint](./library-crate.md#fingerprint) is computed separately over the canonicalized (key-sorted) hash payload, per the crate spec's canonicalization rules.

Three natives are **structureless by design**: their shape is intentionally open, so they carry a `description` and no `structure`. A consumer treats them per the [sufficiency guarantee](./library-crate.md#sufficiency-guarantee): surface the openness (an opaque, pass-through type), never invent a shape.

One reserved marker: `value_type = "Any"` on a `dict` field declares the value type **unspecified** — the values are arbitrary; a consumer surfaces this as declared imprecision (e.g. `dict[str, Any]` with a caveat), never as a guessed value shape.

## The Pinned Set (MTHDS 1.0.0)

### native.Dynamic

Structureless by design — a dynamically-typed value whose shape is determined at runtime.

```toml
[concept.Dynamic]
description = "A dynamic concept"
```

### native.Text

```toml
[concept.Text]
description = "A text"

[concept.Text.structure]
text = { type = "text", required = true, description = "The text" }
```

### native.Image

```toml
[concept.Image]
description = "An image"

[concept.Image.structure]
url = { type = "text", required = true, description = "The image URL: a storage URI, an HTTP(S) URL, or a base64 data URL" }
public_url = { type = "text", description = "The public URL of the image" }
source_prompt = { type = "text", description = "The source prompt of the image" }
source_negative_prompt = { type = "text", description = "The source negative prompt of the image" }
caption = { type = "text", description = "The caption of the image" }
mime_type = { type = "text", description = "The MIME type of the image" }
width = { type = "integer", description = "The width of the image, in pixels" }
height = { type = "integer", description = "The height of the image, in pixels" }
filename = { type = "text", description = "The original filename of the image" }
```

`width` and `height` are each optional but paired: a compliant value carries both or neither. The pairing constrains values, not the blueprint — the structure language has no cross-field form, so a consumer projecting this definition emits two independently optional integers, and a validating runtime is what enforces the pairing.

### native.Document

```toml
[concept.Document]
description = "A document"

[concept.Document.structure]
url = { type = "text", required = true, description = "The document URL: a storage URI, an HTTP(S) URL, or a base64 data URL" }
public_url = { type = "text", description = "The public HTTPS URL of the document" }
mime_type = { type = "text", description = "The MIME type of the document" }
filename = { type = "text", description = "The original filename of the document" }
title = { type = "text", description = "The title of the document or source" }
snippet = { type = "text", description = "A text snippet or excerpt from the document" }
```

### native.Html

```toml
[concept.Html]
description = "HTML content"

[concept.Html.structure]
inner_html = { type = "text", required = true, description = "The inner HTML of the content" }
css_class = { type = "text", required = true, description = "The CSS class of the content" }
```

### native.TextAndImages

```toml
[concept.TextAndImages]
description = "A text and an image"

[concept.TextAndImages.structure]
text = { type = "concept", concept_ref = "native.Text", description = "A text content" }
images = { type = "list", item_type = "concept", item_concept_ref = "native.Image", description = "A list of images that were extracted from the text" }
raw_html = { type = "text", description = "The raw HTML of the fetched page, if requested" }
```

### native.Number

```toml
[concept.Number]
description = "A number"

[concept.Number.structure]
number = { type = "number", required = true, description = "The number" }
```

### native.YesNo

```toml
[concept.YesNo]
description = "The answer to a yes/no question"

[concept.YesNo.structure]
yes_no = { type = "boolean", required = true, description = "Whether the answer is yes (true) or no (false)." }
```

### native.Date

```toml
[concept.Date]
description = "A calendar date, optionally with a time of day — as precise as its source states."

[concept.Date.structure]
date = { type = "date", required = true, description = "The calendar date, in ISO 8601 (e.g. 2026-07-07). Always required." }
time = { type = "time", description = "The time of day, in ISO 8601 (e.g. 15:40:00, or 15:40:00+02:00 with a UTC offset). Include it only when the source states a time — never invent a time. Keep the UTC offset exactly when the source states one." }
```

A `Date` is as precise as its source: the `time` field is present only when the source states a time of day, and its UTC offset is kept exactly when the source states one. A `Date` never carries an invented midnight and never reads numeric epoch input.

### native.Time

```toml
[concept.Time]
description = "A time of day, optionally with a UTC offset — as precise as its source states."

[concept.Time.structure]
time = { type = "time", required = true, description = "The time of day, in ISO 8601 (e.g. 15:40:00, or 15:40:00+02:00 with a UTC offset)." }
```

### native.Page

```toml
[concept.Page]
description = "The content of a page of a document, comprising text and linked images and an optional page view image"

[concept.Page.structure]
text_and_images = { type = "concept", concept_ref = "native.TextAndImages", required = true, description = "The text and images content extracted from the page" }
page_view = { type = "concept", concept_ref = "native.Image", description = "The screenshot of the page" }
```

### native.JSON

```toml
[concept.JSON]
description = "A JSON object"

[concept.JSON.structure]
json_obj = { type = "dict", key_type = "text", value_type = "Any", required = true, description = "The JSON object" }
```

### native.SearchResult

```toml
[concept.SearchResult]
description = "A search result with answer and sources"

[concept.SearchResult.structure]
answer = { type = "text", required = true, description = "The answer to the search query" }
sources = { type = "list", item_type = "concept", item_concept_ref = "native.Document", required = true, description = "The source documents supporting the answer" }
```

### native.Anything

Structureless by design — accepts any type.

```toml
[concept.Anything]
description = "Anything"
```

### native.Composite

Structureless by design — a named composition of contents whose field names are chosen at combination time (e.g. by a `PipeParallel`'s branch result names).

```toml
[concept.Composite]
description = "A named composition of contents"
```

## See Also

- [.mthds File Format — Native Concepts](./mthds-format.md#native-concepts) — how natives are referenced from bundles and the reservation rules.
- [Library Crate Format — Expand Native Concepts](./library-crate.md#4-expand-native-concepts) — how these definitions are materialized into a normalized crate.
- [Concept Structure Fields](./mthds-format.md#concept-structure-fields) — the structure language the definitions are written in.
