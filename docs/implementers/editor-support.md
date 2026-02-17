---
description: "Build editor support for .mthds files — TextMate grammars, semantic tokens, schema validation, and formatting integration."
---

# Building Editor Support

This page describes how to build editor support for `.mthds` files — syntax highlighting, semantic tokens, schema validation, and formatting.

## TextMate Grammar

The primary mechanism for syntax highlighting is a TextMate grammar layered on top of TOML. The grammar recognizes MTHDS-specific constructs within the TOML structure.

**Scope hierarchy:**

The base scope is `source.mthds` (extending `source.toml`). Key MTHDS-specific scopes include:

- `meta.pipe-section.mthds` — `[pipe.<name>]` table headers
- `meta.concept-section.mthds` — `[concept.<name>]` table headers
- `entity.name.type.mthds` — concept codes in `PascalCase`
- `entity.name.function.mthds` — pipe codes in references
- `string.template.mthds` — prompt template strings
- `variable.other.jinja.mthds` — Jinja2 variables (`{{ }}`, `@var`, `$var`)

**Key patterns to recognize:**

1. **Pipe sections** — table headers matching `[pipe.<snake_case>]` or `[pipe.<snake_case>.<subfield>]`.
2. **Concept sections** — table headers matching `[concept.<PascalCase>]` or `[concept.<PascalCase>.structure]`.
3. **Pipe type values** — string values that match the nine pipe type names (`PipeLLM`, `PipeFunc`, etc.) in the `type` field of pipe sections.
4. **Prompt templates** — multi-line strings containing Jinja2 syntax and `@variable` / `$variable` shorthand.
5. **Cross-package references** — strings containing `->` (the arrow separator for package-qualified references).
6. **Model references** — string values with `$` or `@` prefixes in the `model` field.

**Implementation approach:**

The reference implementation's TextMate grammar is structured as a set of injection grammars that layer on top of the TOML base grammar. This allows TOML syntax to remain correct while MTHDS-specific constructs receive additional semantic coloring.

## Semantic Token Types

Beyond TextMate grammar-based highlighting, an LSP-aware extension can provide semantic tokens for more precise highlighting. The reference implementation defines 7 MTHDS-specific semantic token types:

| Token Type | Description | Applied To |
|------------|-------------|------------|
| `mthdsConcept` | Concept names | `ContractClause`, `Text`, `Image`, concept references in `inputs`, `output`, `refines` |
| `mthdsPipeType` | Pipe type values | `PipeLLM`, `PipeSequence`, etc. in the `type` field |
| `mthdsDataVariable` | Data variables in prompts | `@variable_name`, `$variable_name`, `{{ variable }}` |
| `mthdsPipeName` | Pipe names in references | Pipe codes in `steps[].pipe`, `branch_pipe_code`, `outcomes`, etc. |
| `mthdsPipeSection` | Pipe section headers | The entire `[pipe.my_pipe]` header |
| `mthdsConceptSection` | Concept section headers | The entire `[concept.MyConcept]` header |
| `mthdsModelRef` | Model field references | Values in the `model` field (e.g., `$writing-factual`, `@default-text-from-pdf`) |

**Detection algorithm for semantic tokens:**

The semantic token provider parses the TOML document and walks the AST to identify MTHDS-specific elements. For each token, it determines the type based on:

1. **Context** — is this value inside a `[pipe.*]` section or a `[concept.*]` section?
2. **Field name** — is this the `type` field, the `model` field, a prompt field, an `inputs`/`output` field?
3. **Value pattern** — does the value match `PascalCase` (concept), `snake_case` (pipe), or have a `$`/`@` prefix (model ref)?

## Using the MTHDS JSON Schema

The MTHDS JSON Schema (`mthds_schema.json`) provides machine-readable validation for `.mthds` files. It is a standard JSON Schema document that describes the complete bundle structure.

**What the schema covers:**

- Header fields (`domain`, `description`, `system_prompt`, `main_pipe`)
- Concept definitions (simple and structured forms)
- All nine pipe types with their specific fields
- Sub-pipe blueprints (`steps`, `branches`, `outcomes`, `construct`)
- Field types and their constraints

**How to use it:**

1. **For validation** — feed the parsed TOML (as JSON) through a JSON Schema validator. This catches structural errors (wrong field types, missing required fields) without implementing MTHDS-specific validation logic.
2. **For autocompletion** — use the schema's `properties` and `enum` values to suggest field names and valid values.
3. **For hover documentation** — use the schema's `description` fields to show documentation on hover.

**Generating the schema:**

The reference implementation auto-generates the schema from the Pydantic data model (`PipelexBundleBlueprint`) using the `pipelex-dev generate-mthds-schema` command. This ensures the schema stays in sync with the implementation. Alternative implementations can use the published schema directly.

**Configuring schema association:**

In the `plxt.toml` configuration, associate `.mthds` files with the schema:

```toml
[[rule]]
include = ["**/*.mthds"]

[rule.schema]
path = "path/to/mthds_schema.json"
```

## LSP Integration Points

The reference implementation includes an LSP server, available standalone via `plxt lsp stdio`. It is built on a fork of [taplo](https://github.com/tamasfe/taplo), extended with MTHDS-specific semantic tokens, validation, and navigation. It currently provides formatting, document symbols, folding, semantic tokens, schema-based validation and completion, and basic within-bundle go-to-definition. The LSP is bundled with the [`pipelex-tools`](https://pypi.org/project/pipelex-tools/) CLI and with the Pipelex VS Code extension ([source](https://github.com/Pipelex/vscode-pipelex), [Marketplace](https://marketplace.visualstudio.com/items?itemName=pipelex.pipelex), [Open VSX](https://open-vsx.org/extension/Pipelex/pipelex)).

The following integration points describe the full scope of MTHDS-aware language server capabilities. Each bullet notes the current coverage in the reference implementation:

- **Diagnostics** — run validation (Stages 2–7 from the [Validation Rules](validation-rules.md) page) and report errors as LSP diagnostics. *(Reference implementation: schema-level validation only.)*
- **Completion** — suggest pipe type names, native concept codes, field type names, concept codes from the current bundle, and pipe codes for references. *(Reference implementation: schema-based suggestions for field names and values.)*
- **Hover** — show concept descriptions, pipe signatures, and field documentation. *(Reference implementation: schema-based field documentation.)*
- **Go to Definition** — navigate from a concept/pipe reference to its definition (may span files for domain-qualified or cross-package references). *(Reference implementation: within-bundle navigation only.)*
- **Find References** — find all usages of a concept or pipe across bundles. *(Not yet implemented in the reference implementation.)*
- **Rename** — rename a concept or pipe code across all references in the package. *(Not yet implemented in the reference implementation.)*

## See Also

- [Tooling: Editor Support](../tooling/editor-support.md) — user-facing editor documentation.
- [Tooling: MTHDS JSON Schema](../tooling/json-schema.md) — user-facing schema documentation.
