---
description: "Set up the MTHDS VS Code extension for syntax highlighting, semantic tokens, formatting, and validation of .mthds files."
---

# Editor Support

The MTHDS editor extension for VS Code and Cursor provides syntax highlighting, semantic tokens, formatting, and validation for `.mthds` files. It is the recommended way to work with MTHDS.

## Installation

Install the **Pipelex** extension from the VS Code Marketplace:

1. Open VS Code or Cursor.
2. Go to Extensions (`Ctrl+Shift+X` / `Cmd+Shift+X`).
3. Search for **Pipelex**.
4. Click **Install**.

The extension activates automatically for `.mthds` files.

## Features

### Syntax Highlighting

The extension provides a full TextMate grammar for `.mthds` files, built on top of TOML highlighting. It recognizes MTHDS-specific constructs: pipe sections, concept sections, prompt templates, Jinja2 variables (`{{ }}`, `@variable`, `$variable`), and HTML content embedded in prompts.

Markdown code blocks tagged as `mthds` or `toml` also receive syntax highlighting when the extension is active.

### Semantic Tokens

Beyond TextMate grammar-based highlighting, the extension provides 7 semantic token types that distinguish MTHDS-specific elements:

| Token type | Applies to | Visual hint |
|------------|-----------|-------------|
| `mthdsConcept` | Concept names (e.g., `ContractClause`, `Text`) | Type color |
| `mthdsPipeType` | Pipe type values (e.g., `PipeLLM`, `PipeSequence`) | Type color, bold |
| `mthdsDataVariable` | Data variables in prompts | Variable color |
| `mthdsPipeName` | Pipe names in references | Function color |
| `mthdsPipeSection` | Pipe section headers (`[pipe.my_pipe]`) | Keyword color, bold |
| `mthdsConceptSection` | Concept section headers (`[concept.MyConcept]`) | Keyword color, bold |
| `mthdsModelRef` | Model field references (`$preset`, `@alias`) | Variable color, bold |

Semantic tokens are enabled by default. To toggle them:

- `pipelex.mthds.semanticTokens` — MTHDS-specific semantic tokens.
- `pipelex.syntax.semanticTokens` — TOML table/array key tokens.

### Formatting

The extension includes a built-in formatter for `.mthds` and `.toml` files. It uses the same engine as the `plxt` CLI (see [Formatting & Linting](formatting-linting.md)). Format on save works out of the box.

Formatting options are configurable in VS Code settings under `pipelex.formatter.*` (e.g., `alignEntries`, `columnWidth`, `trailingNewline`).

### Schema Validation

The extension supports JSON Schema-based validation and completion for TOML files. When the MTHDS JSON Schema is configured (see [MTHDS JSON Schema](json-schema.md)), the editor provides:

- Autocomplete suggestions for field names and values.
- Inline validation errors for invalid fields or types.
- Hover documentation for known fields.

Schema support is enabled by default (`pipelex.schema.enabled`).

### Additional Commands

The extension contributes several commands accessible via the Command Palette:

| Command | Description |
|---------|-------------|
| **TOML: Copy as JSON** | Copy selected TOML as JSON. |
| **TOML: Copy as TOML** | Copy selected text as TOML. |
| **TOML: Paste as JSON** | Paste clipboard content as JSON. |
| **TOML: Paste as TOML** | Paste clipboard content as TOML. |
| **TOML: Select Schema** | Choose a JSON Schema for the current TOML file. |
