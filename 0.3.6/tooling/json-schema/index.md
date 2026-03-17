# MTHDS JSON Schema

The MTHDS standard includes a machine-readable JSON Schema that describes the structure of `.mthds` files. Tools and editors can use this schema for validation, autocompletion, and documentation.

## What It Covers

The schema defines the complete structure of an `.mthds` bundle:

- **Header fields**: `domain`, `description`, `system_prompt`, `main_pipe`.
- **Concept definitions**: both simple (string) and structured forms, including `structure` fields, `refines`, and all field types (`text`, `integer`, `number`, `boolean`, `date`, `list`, `dict`, `concept`) and the `choices` enum mechanism.
- **Pipe definitions**: all pipe types with their specific fields — `PipeLLM`, `PipeFunc`, `PipeImgGen`, `PipeExtract`, `PipeSearch`, `PipeCompose`, `PipeSequence`, `PipeParallel`, `PipeCondition`, `PipeBatch`.
- **Sub-pipe blueprints**: the `steps`, `branches`, `outcomes`, and `construct` structures used by controllers and PipeCompose.
- **Inline model settings**: the `LLMSetting`, `ImgGenSetting`, `ExtractSetting`, and `SearchSetting` objects that can be used in place of string model references.

## Schema Version

The schema is auto-generated from the MTHDS bundle data model. The current version is noted in the schema's `$comment` field. The hosted schema always corresponds to the latest released version of the MTHDS standard.

## Where to Find It

The schema is distributed with the tools that use it:

- **VS Code extension** — the Pipelex extension bundles the schema and uses it for autocompletion and inline validation.
- **`plxt` CLI** — the `plxt` binary includes the schema for local validation.
- **`pipelex-tools` PyPI package** — the schema is included in the Python distribution.

The schema is also hosted at a stable URL for direct use by editors and other tooling:

**Hosted URL:** [`https://mthds.ai/mthds_schema.json`](https://mthds.ai/mthds_schema.json)

## How to Use It

### With the VS Code Extension

The Pipelex VS Code extension includes the schema and uses it automatically for autocompletion and inline validation of `.mthds` files. No configuration is required.

### With Other Editors

Any editor that supports JSON Schema for TOML can use the MTHDS schema. Configure your editor's TOML language server to associate `.mthds` files with the schema URL `https://mthds.ai/mthds_schema.json`.

### For Tooling

The schema can be used programmatically for:

- Building custom validators for `.mthds` files.
- Generating documentation from the schema structure.
- Implementing autocompletion in non-VS Code editors.

For detailed guidance on building editor support, see [For Implementers: Building Editor Support](../implementers/editor-support.md).
