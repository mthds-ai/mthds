# MTHDS JSON Schema

The MTHDS standard includes a machine-readable JSON Schema that describes the structure of `.mthds` files. Tools and editors can use this schema for validation, autocompletion, and documentation.

## What It Covers

The schema defines the complete structure of an `.mthds` bundle:

- **Header fields**: `domain`, `description`, `system_prompt`, `main_pipe`.
- **Concept definitions**: both simple (string) and structured forms, including `structure` fields, `refines`, and all field types (`text`, `integer`, `number`, `boolean`, `date`, `list`, `dict`, `concept`, `choices`).
- **Pipe definitions**: all nine pipe types with their specific fields — `PipeLLM`, `PipeFunc`, `PipeImgGen`, `PipeExtract`, `PipeCompose`, `PipeSequence`, `PipeParallel`, `PipeCondition`, `PipeBatch`.
- **Sub-pipe blueprints**: the `steps`, `branches`, `outcomes`, and `construct` structures used by controllers and PipeCompose.

## Where to Find It

The schema is located at `pipelex/language/mthds_schema.json` in the Pipelex repository. It is auto-generated from the MTHDS data model to ensure it stays in sync with the implementation.

## How to Use It

### With the VS Code Extension

The VS Code extension can use the schema for autocompletion and inline validation. Configure it via `pipelex.schema.associations` in your VS Code settings:

```json
{
  "pipelex.schema.associations": {
    ".*\\.mthds$": "path/to/mthds_schema.json"
  }
}
```

### With Other Editors

Any editor that supports JSON Schema for TOML can use the MTHDS schema. Configure your editor's TOML language server to associate `.mthds` files with the schema.

### For Tooling

The schema can be used programmatically for:

- Building custom validators for `.mthds` files.
- Generating documentation from the schema structure.
- Implementing autocompletion in non-VS Code editors.

For detailed guidance on building editor support, see [For Implementers: Building Editor Support](../implementers/editor-support.md).
