---
description: "MTHDS is an open standard for defining, packaging, and sharing AI methods — giving agents the ability to discover and execute structured, composable AI workflows."
---

# Home

MTHDS is an open standard for defining, packaging, and distributing AI methods. It gives agents a typed, knowledge-based language for structured AI methods — a way to describe what an AI should do, with what inputs, producing what outputs, in files that humans and machines can read.

The language reads close to natural language. Concepts carry business meaning directly — `ContractClause`, `CandidateProfile`, `Joke` — and pipes read as declarative intent: "given this input, produce that output." Domain experts can read a `.mthds` file without programming experience. Business knowledge is not buried in code — it is the language.

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
