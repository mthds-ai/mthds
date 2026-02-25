---
description: "Use plxt to format and lint .mthds and TOML files — ensure consistent style and catch errors across your MTHDS project."
---

# Formatting & Linting

`plxt` is the CLI tool for formatting and linting `.mthds` and `.toml` files. It ensures consistent style across MTHDS projects.

## Installation

`plxt` is distributed as a standalone binary. Install it from the [`pipelex-tools` PyPI package](https://pypi.org/project/pipelex-tools/) (`pip install pipelex-tools`), or use the bundled version included with the [VS Code extension](https://marketplace.visualstudio.com/items?itemName=pipelex.pipelex).

## Formatting

Format `.mthds` and `.toml` files in place:

```bash
# Format all .mthds and .toml files in the current directory (recursive)
plxt format .

# Format a single file
plxt format contract_analysis.mthds

# Format and see what changed (check mode — exits non-zero if changes needed)
plxt format --check .
```

The `plxt format` command (also available as `plxt fmt`) aligns entries, normalizes whitespace, and ensures consistent TOML style. Files are modified in place.

## Linting

Lint `.mthds` and `.toml` files for structural issues:

```bash
# Lint all files in the current directory
plxt lint .

# Lint a single file
plxt lint contract_analysis.mthds
```

The `plxt lint` command checks for TOML structural issues and reports errors.

## Configuration

`plxt` reads its configuration from a `.pipelex/plxt.toml` file in the project root or a parent directory. This file controls formatting rules (alignment, column width, trailing commas, etc.) and can define per-file-type overrides.

A basic configuration:

```toml
[formatting]
align_entries      = true
column_width       = 100
trailing_newline   = true
array_trailing_comma = true
```

For the full list of configuration options, see the Pipelex documentation.

## Editor Integration

When the VS Code extension is installed, `plxt` formatting runs automatically on save. The extension uses the same formatting engine, so files formatted via CLI and editor produce identical results.
