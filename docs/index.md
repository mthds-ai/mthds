---
description: "MTHDS is an open standard for defining, packaging, and sharing AI methods — giving agents the ability to discover and execute structured, composable AI workflows."
---

# Home

MTHDS is an open standard for defining, packaging, and distributing AI methods. It provides a typed language for describing what an AI should do, with what inputs, and what outputs to produce — all in plain-text files that humans and machines can read alike.

The language reads close to natural language and is designed to transcribe business logic. ***Concepts*** carry business meaning directly — `ContractClause`, `CandidateProfile`, `Joke` — and ***Pipes*** read as declarative intent: "given this input, produce that output." Domain experts can read a `.mthds` file without programming skills.

The standard has two pillars. **The Language** lets you define typed data and transformations in `.mthds` files — plain text, version-controllable, readable by anyone on the team. A single file works on its own, no setup required. **The Package System** adds distribution: give your methods an identity, declare dependencies, control visibility, and share them across projects and organizations.

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
