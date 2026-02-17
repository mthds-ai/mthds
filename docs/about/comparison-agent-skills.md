---
description: "Compare MTHDS with Agent Skills: differences in type systems, packaging, discoverability, and approaches to AI method definitions."
---

# Comparison with Agent Skills

Both MTHDS and [Agent Skills](https://agentskills.io/) address the problem of defining and discovering AI capabilities. They take fundamentally different approaches, reflecting different design goals.

## Scope Comparison

| Dimension | Agent Skills | MTHDS |
|-----------|-------------|-------|
| **Format** | JSON or YAML manifest describing a skill | TOML-based language with concepts, pipes, domains |
| **Type system** | Text descriptions for inputs/outputs | Typed signatures with concept refinement |
| **Composition** | No built-in composition model | Controllers (sequence, parallel, condition, batch) |
| **Package system** | No dependencies or versioning | Full package system with manifest, lock file, dependencies |
| **Discovery** | Text-based search (name, description, tags) | Typed search ("I have X, I need Y") + text search |
| **Distribution** | Hosted registry or skill files | Git-native, federated (decentralized storage, centralized discovery) |
| **CLI** | No CLI | Full `mthds` CLI with package management |

## What Agent Skills Does Well

Agent Skills is deliberately minimal. A skill is a manifest file that describes what an AI capability does in natural language. This makes it:

- **Simple to adopt.** Writing a skill manifest requires no new syntax — it is standard JSON/YAML.
- **Runtime-agnostic.** Any AI framework can consume a skill manifest.
- **Easy to discover.** Text descriptions are searchable by keywords, tags, and categories.

The simplicity is a feature. Agent Skills serves the use case of "tell me what capabilities exist" without prescribing how they are implemented or composed.

## What MTHDS Adds

MTHDS targets a different use case: defining, composing, and distributing AI methods with type safety.

- **Typed signatures** enable semantic discovery that text descriptions cannot support. "Find pipes that accept `Document` and produce `NonCompeteClause`" is a precise query with a precise answer.
- **Built-in composition** means multi-step methods are defined in the same file as the individual steps. A PipeSequence that extracts, analyzes, and summarizes is a single method, not an external orchestration.
- **A real package system** with versioned dependencies, lock files, and visibility controls makes methods reusable across teams and organizations.

## Design Parallels

Despite different approaches, the two standards share design principles:

- **Progressive disclosure.** Agent Skills' tiered skill hosting (built-in → user-created → community) parallels MTHDS's progressive enhancement (single file → package → ecosystem).
- **Skills as files.** Both standards treat capabilities as human-readable text files, not database entries or API registrations.
- **Federated distribution.** Both favor decentralized storage with centralized discovery.

## When to Use Which

- Use **Agent Skills** when you need a lightweight manifest that describes what an AI capability does, for use with frameworks that support the Agent Skills standard.
- Use **MTHDS** when you need typed composition, versioned dependencies, and type-safe discovery across packages.

The two standards are not mutually exclusive. A package's `main_pipe` could be exposed as an Agent Skill for frameworks that consume that format.
