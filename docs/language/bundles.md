---
description: "Learn how MTHDS bundles organize concepts and pipes into .mthds files — the basic building block of the standard."
---

# Bundles

A **bundle** is a single `.mthds` file. It is the authoring unit of MTHDS — the place where you define typed data and typed transformations.

## A First Look

```toml
domain      = "legal.contracts"
description = "Contract analysis methods for legal documents"
main_pipe   = "extract_clause"

[concept]
ContractClause = "A clause extracted from a legal contract"

[pipe.extract_clause]
type        = "PipeLLM"
description = "Extract the key clause from a contract"
inputs      = { contract_text = "Text" }
output      = "ContractClause"
prompt      = "Extract the key clause from the following contract: @contract_text"
```

This is a complete, valid `.mthds` file. It defines one concept, one pipe, and works on its own — no manifest, no package, no dependencies needed.

## What This Does

The file declares a **domain** (`legal.contracts`), a **concept** (`ContractClause`), and a **pipe** (`extract_clause`) that uses an LLM to transform `Text` into a `ContractClause`. The `main_pipe` header marks `extract_clause` as the bundle's primary entry point.

## File Format

A `.mthds` file is a valid [TOML](https://toml.io/) document encoded in UTF-8. The `.mthds` extension is required. If you know TOML, you already know the syntax — MTHDS adds structure and meaning on top of it.

## Bundle Structure

Every bundle has up to three sections:

1. **Header fields** — top-level key-value pairs that identify the bundle.
2. **Concept definitions** — typed data declarations in `[concept]` tables.
3. **Pipe definitions** — typed transformations in `[pipe.<pipe_code>]` tables.

All three are optional in the TOML sense, but a useful bundle will contain at least one concept or one pipe.

## Header Fields

Header fields appear at the top of the file, before any `[concept]` or `[pipe]` tables.

| Field | Required | Description |
|-------|----------|-------------|
| `domain` | Yes | The domain this bundle belongs to. Determines the namespace for all concepts and pipes defined in this file. |
| `description` | No | A human-readable description of what this bundle provides. |
| `system_prompt` | No | A default system prompt applied to all `PipeLLM` pipes in this bundle that do not define their own. When a PipeLLM pipe omits its own `system_prompt`, it inherits the bundle-level value. A pipe that defines its own `system_prompt` overrides the bundle default. |
| `main_pipe` | No | The pipe code of the bundle's primary entry point. Auto-exported when the bundle is part of a package. |

The `domain` field is the only required header. It assigns a namespace to everything in the file — more on this in [Domains](domains.md).

The `main_pipe` field, if present, must be a valid `snake_case` pipe code and must reference a pipe defined in the same bundle.

## Standalone Bundles

A `.mthds` file works on its own, without a package manifest. When used standalone:

- All pipes are treated as public (no visibility restrictions).
- No dependencies are available beyond native concepts.
- The bundle is not distributable (no package address).

This makes `.mthds` files ideal for learning, prototyping, and simple projects. When you need distribution, add a `METHODS.toml` manifest — see [The Package System](../packages/structure.md).
