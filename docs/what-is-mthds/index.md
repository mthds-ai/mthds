---
description: "Learn what MTHDS is: a typed language for declaring AI methods as concepts and pipes in readable, version-controllable text files — giving agents structured methods they can discover and execute."
---

# What is MTHDS?

MTHDS (pronounced "methods") is an open standard for AI methods. It defines a typed language for describing what an AI should do — the data it works with, the transformations it performs, and how those transformations compose together — in plain text files that humans and machines can read.

An AI method in MTHDS is not code in the traditional sense. It is a declaration: "given this kind of input, produce that kind of output, using this approach." An agent or runner decides how to execute it. The method author decides what it means.

## Why a New Standard?

Current approaches to AI workflows each solve part of the problem but leave significant gaps:

**Code** (Python, frameworks) provides full control, typed outputs, and testability. But the business logic that matters — the actual extraction, analysis, or reasoning steps — is buried in infrastructure code. Domain experts cannot read or iterate on it.

**Natural-language instructions** (prompts, skills) are the opposite: easy to write and human-readable. But they carry no typed outputs, no validation, and no guaranteed output structure. The agent reinterprets them at every invocation.

**Automation platforms** (Zapier, Make, n8n) connect APIs through visual, GUI-based editors designed for deterministic workflows — not for AI. AI capabilities were bolted on after the fact. Their interfaces are built for human point-and-click editing, not for agents to read or compose programmatically. And when workflows require multi-step cognitive work — extraction, analysis, synthesis — these platforms lack the conceptual typing system to validate what flows between steps.

MTHDS provides the missing combination: a declarative language that is typed enough to validate, structured enough to compose, and readable enough for domain experts to understand. The method separates *what* a workflow does from *how* it is executed, analogous to how SQL separates data queries from storage engines.

## Agents as First-Class Participants

MTHDS gives agents the ability to discover, compose, and execute structured AI methods. But agents are not limited to execution. Because `.mthds` files are plain text with typed structure, agents can also *build* new methods, *modify* existing ones, and *extend* the ecosystem. An agent can search the Know-How Graph for methods by typed signature ("I have a `Document`, I need a `NonCompeteClause`"), compose them into multi-step workflows, create new methods that fill gaps in the graph, and execute them with validated data flow. Methods are artifacts agents can create, not just consume.

The language reads close to natural language and is designed to transcribe business logic. ***Concepts*** like `ContractClause`, `CandidateProfile`, or `Joke` carry business meaning directly — they are not programming abstractions but representations of real domain knowledge. A ***Pipe*** that declares `inputs = { doc = "ContractClause" }` and `output = "NonCompeteClause"` reads as a business statement, not as code. Domain experts can read and understand `.mthds` files without programming skills, making methods a shared artifact between technical and non-technical teams.

## The Two Pillars

MTHDS has two complementary halves, designed so you can start with one and add the other when you need it.

### Pillar 1 — The Language

The `.mthds` file format. Everything you need to define typed data and AI transformations in a single file.

A `.mthds` file is a valid [TOML](https://toml.io/) document with structure and meaning layered on top. If you know TOML, you already know the syntax. Inside a file, you define:

- **Concepts** — typed data declarations. A concept is a named type that describes a kind of data: a `ContractClause`, a `CandidateProfile`, a `Joke`. Concepts can have internal structure (fields with types like `text`, `integer`, `boolean`, `list`, `number`, `date`, `dict`, and `concept`) or they can be simple semantic labels. Concepts can refine other concepts — `NonCompeteClause` refines `ContractClause`, meaning it can be used anywhere a `ContractClause` is expected.

- **Pipes** — typed transformations. A pipe declares its inputs (concepts), its output (a concept), and its type — what kind of work it does. MTHDS defines five **operators** (PipeLLM for language model generation, PipeFunc for Python functions, PipeImgGen for image generation, PipeExtract for document extraction, PipeCompose for templating and assembly) and four **controllers** (PipeSequence for sequential steps, PipeParallel for concurrent branches, PipeCondition for conditional routing, PipeBatch for mapping over lists).

- **Domains** — namespaces that organize concepts and pipes. A domain like `legal.contracts` tells you what a bundle is about and prevents naming collisions between unrelated definitions.

A single `.mthds` file — called a **bundle** — works on its own. No manifest, no package, no configuration. This is the starting point for learning and prototyping.

[:octicons-arrow-right-24: Learn the Language](../language/bundles.md)

### Pillar 2 — The Package System

The infrastructure for distributing and composing methods at scale.

When a standalone bundle is not enough — when you want to share methods, depend on other people's work, or control which methods are public — you add a `METHODS.toml` manifest. This turns a directory of bundles into a **package**: a distributable unit with a globally unique address, semantic versioning, declared dependencies, and explicit exports.

Packages are stored in Git repositories. The package address (e.g., `github.com/acme/legal-tools`) doubles as the fetch location — no upload step, no proprietary hosting. A lock file (`methods.lock`) pins exact versions with SHA-256 integrity hashes for reproducible builds.

Cross-package references use the `->` syntax: `scoring_lib->scoring.compute_weighted_score` reads as "from the `scoring_lib` dependency, get `compute_weighted_score` in the `scoring` domain." The separator was chosen for readability by non-technical audiences — arrows are intuitive, visually distinct from dots, and universally understood.

[:octicons-arrow-right-24: The Package System](../packages/structure.md)

## Core Concepts at a Glance

| Term | What it is | Analogy |
|------|-----------|---------|
| **Concept** | A typed data declaration — the kinds of data that flow through pipes. | A form with typed fields. |
| **Pipe** | A typed transformation — declares inputs, output, and what kind of work it does. | A processing step in a workflow. |
| **Domain** | A namespace that groups related concepts and pipes. | A folder that organizes related definitions. |
| **Bundle** | A single `.mthds` file. The authoring unit. | A source file. |
| **Package** | A directory with a `METHODS.toml` manifest and one or more bundles. The distribution unit. | A versioned library. |

## A Concrete Example

Here is a complete, working `.mthds` file:

```toml
domain      = "joke_generation"
description = "Generating one-liner jokes from topics"
main_pipe   = "generate_jokes_from_topics"

[concept.Topic]
description = "A subject or theme that can be used as the basis for a joke."
refines     = "Text"

[concept.Joke]
description = "A humorous one-liner intended to make people laugh."
refines     = "Text"

[pipe.generate_jokes_from_topics]
type        = "PipeSequence"
description = "Generate 3 joke topics and create a joke for each"
output      = "Joke[]"
steps = [
    { pipe = "generate_topics", result = "topics" },
    { pipe = "batch_generate_jokes", result = "jokes" },
]

[pipe.generate_topics]
type        = "PipeLLM"
description = "Generate 3 distinct topics suitable for jokes"
output      = "Topic[3]"
prompt      = "Generate 3 distinct and varied topics for crafting one-liner jokes."

[pipe.batch_generate_jokes]
type             = "PipeBatch"
description      = "Generate a joke for each topic"
inputs           = { topics = "Topic[]" }
output           = "Joke[]"
branch_pipe_code = "generate_joke"
input_list_name  = "topics"
input_item_name  = "topic"

[pipe.generate_joke]
type        = "PipeLLM"
description = "Write a clever one-liner joke about the given topic"
inputs      = { topic = "Topic" }
output      = "Joke"
prompt      = "Write a clever one-liner joke about $topic. Be concise and witty."
```

This file defines two concepts (`Topic` and `Joke`, both refining the built-in `Text` type) and four pipes: a sequence that generates topics and then batch-processes them into jokes. It works as a standalone file — save it, point a runner at it, and it runs.

## Progressive Enhancement

MTHDS is designed so you can start simple and add complexity only when you need it:

1. **Single file** — a `.mthds` bundle works on its own. No configuration, no manifest, no dependencies. Define concepts and pipes, and run them.

2. **Package** — add a `METHODS.toml` manifest to get a globally unique identity, version number, and visibility controls. Pipes become private by default; you choose what to export.

3. **Dependencies** — add a `[dependencies]` section to compose with other packages. Reference their concepts and pipes using the `->` syntax.

4. **Ecosystem** — publish packages to Git repositories. Registry indexes crawl and index them, enabling search by domain, by concept, or by typed pipe signature. The **Know-How Graph** — a typed network of AI methods — lets you ask "I have a `Document`, I need a `NonCompeteClause`" and find the pipes (or chains of pipes) that get you there.

Each layer builds on the previous one without breaking it. A standalone bundle that works today continues to work unchanged inside a package.

## What Makes MTHDS Different

MTHDS differs from other approaches to describing AI capabilities in three ways:

- **Typed signatures.** Every pipe declares the concepts it accepts and produces. This enables semantic discovery ("I have X, I need Y") and compile-time validation of data flow — something text-based descriptions cannot provide.

- **Composition built in.** Controllers (sequence, parallel, condition, batch) are part of the language, not an external orchestration layer. Multi-step methods are defined in the same file as the individual steps.

- **A real package system.** Versioned dependencies, lock files, visibility controls, cross-package references — the same infrastructure that makes code ecosystems work, applied to AI methods.

## Where to Go Next

- **Method authors**: Start with [The Language](../language/bundles.md) to learn bundles, concepts, pipes, and domains. Then move to [The Package System](../packages/structure.md) when you are ready to distribute.

- **Runner implementers**: Start with the [Specification](../spec/mthds-format.md) for the normative reference on file formats, validation rules, and resolution algorithms.

- **Everyone**: [Write Your First Method](../getting-started/first-method.md) walks you through creating a working `.mthds` file step by step.
