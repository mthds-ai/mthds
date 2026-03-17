---
description: "MTHDS is an open standard for defining, packaging, and sharing AI methods — giving agents the ability to discover and execute structured, composable AI workflows."
---

# MTHDS: the language of executable AI methods

**TLDR**

MTHDS is a declarative language for defining **AI methods**: discrete, reusable units of cognitive work like extraction, analysis, synthesis, generation. It is built on TOML and introduces two primitives: **concepts** (semantically typed data named after real domain things) and **pipes** (deterministic orchestration steps with explicit typed inputs and outputs). Pipes can invoke LLMs, VLMs, OCR, and image generation models, with built-in *structured generation*.

The typing is **conceptual**: `NonCompeteClause` is a refinement of `ContractClause`, meaning pipes compose wherever types are compatible, without manual glue code, because the types carry *business meaning* rather than just structure.

Methods are **executable and composable** like Unix tools: a method can be saved as a CLI command, combined with others using standard Unix pipes, or invoked directly by Claude Code. Methods can also be published as packages, used as templates to customize, or called as components from other methods. Teams can share some methods openly and keep their secret sauce private.

The standard ships with a **Claude Code plugin** that lets Claude write, modify, and compose methods on your behalf. This makes MTHDS **agent-first by design**: a domain expert who can describe what they need in plain language can have Claude author the method, which then runs consistently, is testable, and lives in version control.

Where agent skills handle open-ended tasks, methods handle the parts that benefit from being **explicit, versioned, and validated**. And unlike skills, methods are *executable outside the scope of an agent entirely*.

- Hub: [mthds.sh](https://mthds.sh)
- Spec: [github.com/mthds-ai/mthds](https://github.com/mthds-ai/mthds)
- Reference implementation: [github.com/Pipelex/pipelex](https://github.com/Pipelex/pipelex)
- Agent skills: [github.com/mthds-ai/skills](https://github.com/mthds-ai/skills)
- VS Code extension: [go.pipelex.com/vscode](https://go.pipelex.com/vscode)

<div class="grid cards" markdown>

-   **Learn the Language**

    Concepts, pipes, domains — everything you need to write `.mthds` files.

    [:octicons-arrow-right-24: The Language](language/bundles.md)

-   **Read the Specification**

    The normative reference for file formats, validation rules, and resolution algorithms.

    [:octicons-arrow-right-24: Specification](spec/mthds-format.md)

-   **Get Started**

    Set up your editor and write your first method in a few steps.

    [:octicons-arrow-right-24: Write Your First Method](getting-started/first-method.md)

</div>
