# MTHDS

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Docs](https://img.shields.io/badge/docs-mthds.ai-blue)](https://mthds.ai/)

An open standard for defining, packaging, and distributing AI methods — typed descriptions of what an AI should do, with what inputs, and what outputs it produces.

## Quick Example

A `.mthds` bundle is a plain-text TOML file that defines typed data (concepts) and transformations (pipes):

```toml
domain      = "summarization"
description = "Text summarization methods"
main_pipe   = "summarize"

[concept]
Summary = "A concise summary of a longer text"

[pipe.summarize]
type        = "PipeLLM"
description = "Summarize the input text in 2-3 sentences"
inputs      = { text = "Text" }
output      = "Summary"
prompt      = """
Summarize the following text in 2-3 concise sentences. Focus on the key points.

@text
"""
```

This bundle works on its own — no manifest, no package, no dependencies.

## The Standard

MTHDS has two pillars:

- **The Language** — Define typed data and transformations in `.mthds` bundles. Plain text, version-controllable, readable by anyone on the team. A single bundle works on its own, no setup required.
- **The Package System** — Give your methods an identity, declare dependencies, control visibility, and share them across projects and organizations.

## Getting Started

- [Write Your First Method](https://mthds.ai/getting-started/first-method/) — Create a working bundle from scratch
- [Learn the Language](https://mthds.ai/language/bundles/) — Concepts, pipes, domains, and namespace resolution
- [Editor Support](https://mthds.ai/tooling/editor-support/) — VS Code / Cursor extension for syntax highlighting, validation, and autocomplete
- [Full Documentation](https://mthds.ai/)

## Contributing

This repository hosts the MTHDS specification and documentation site. Contributions include new content, fixes, structure improvements, and style tweaks.

### Requirements

- Python >= 3.10
- [uv](https://docs.astral.sh/uv/) >= 0.7.2

### Local Setup

```bash
git clone https://github.com/mthds-ai/mthds.git
cd mthds
make install
make docs
```

This serves the documentation site locally at `http://127.0.0.1:8000`.

See [CONTRIBUTING.md](CONTRIBUTING.md) for the full contribution guide.

## License

[MIT](LICENSE) — Copyright (c) 2026 Evotis S.A.S.

---

Maintained by [Pipelex](https://pipelex.com).
