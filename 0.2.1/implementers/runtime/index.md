# Building a Runtime

This page describes how to build a runtime that loads, validates, and executes MTHDS bundles and packages. The specification defines *what* must hold; this page describes *how* the reference implementation achieves it, as guidance for alternative implementations.

## High-Level Architecture

A compliant MTHDS runtime has four main subsystems:

1. **Parser** — reads `.mthds` TOML files into an in-memory bundle model.
2. **Loader** — discovers manifests, resolves dependencies, assembles a library of bundles.
3. **Validator** — checks all structural, naming, reference, and visibility rules.
4. **Executor** — runs pipes by dispatching to operator backends (LLM, function, image generation, extraction, composition) and orchestrating controllers.

The first three are specified by the standard; the fourth is implementation-specific (the standard defines *what* a pipe does, not *how*).

## Parsing .mthds Files

A `.mthds` file is valid TOML. Parse it with any compliant TOML parser, then validate the resulting structure against the MTHDS data model.

**Recommended approach:**

1. Parse the TOML into a generic dictionary.
2. Extract header fields (`domain`, `description`, `system_prompt`, `main_pipe`).
3. Extract the `concept` table — a mix of simple declarations (string values) and structured declarations (sub-tables with `description`, `structure`, `refines`).
4. Extract `pipe` sub-tables. Each pipe has a `type` field that determines the discriminated union variant (one of the supported pipe types).
5. Validate all fields against the rules in the [Specification](../spec/mthds-format.md).

The reference implementation uses Pydantic's discriminated union on the `type` field to dispatch pipe parsing:

```
PipeBlueprintUnion = PipeFuncBlueprint
                   | PipeImgGenBlueprint
                   | PipeComposeBlueprint
                   | PipeLLMBlueprint
                   | PipeExtractBlueprint
                   | PipeSearchBlueprint
                   | PipeBatchBlueprint
                   | PipeConditionBlueprint
                   | PipeParallelBlueprint
                   | PipeSequenceBlueprint
```

This means an invalid `type` value is rejected at parse time, before any field-level validation occurs.

## Manifest Discovery

When loading a bundle, the runtime must locate the package manifest (`METHODS.toml`) by walking up the directory tree:

```
function find_manifest(bundle_path):
    current = parent_directory(bundle_path)
    while true:
        if "METHODS.toml" exists in current:
            return parse_manifest(current / "METHODS.toml")
        if ".git" directory exists in current:
            return null  // stop at repository boundary
        parent = parent_directory(current)
        if parent == current:
            return null  // filesystem root
        current = parent
```

If no manifest is found, the bundle is treated as a standalone bundle: all pipes are public, no dependencies are available beyond native concepts, and the bundle is not distributable.

## Loading a Package

Loading a package involves these steps in order:

1. **Parse the manifest** — read `METHODS.toml` and validate all fields (address, version, dependencies, exports). Reject immediately on any parse or validation error.
2. **Discover bundles** — recursively find all `.mthds` files under the package root.
3. **Parse all bundles** — parse each `.mthds` file into a bundle blueprint. Collect parse errors.
4. **Resolve dependencies** — for each dependency in the manifest:
    - If it has a `path` field, resolve from the local filesystem (non-transitive).
    - If it is remote, resolve via VCS (transitive, with cycle detection and diamond handling).
5. **Build the library** — assemble all parsed bundles (local and dependency) into a library structure indexed by domain and package.
6. **Validate references** — check that all concept and pipe references resolve correctly, following the [Namespace Resolution Rules](../spec/namespace-resolution.md).
7. **Validate visibility** — check that cross-domain and cross-package pipe references respect export rules.

## Working Memory

Controllers orchestrate pipes through **working memory** — a key-value store that accumulates results as a pipeline executes.

When a `PipeSequence` runs, each step's output is stored under its `result` name. Subsequent steps can consume any previously stored value. The final step's output (or the value matching the sequence's `output` concept) becomes the sequence's output.

Working memory is scoped to a pipeline execution. Each top-level `mthds run` invocation starts with a fresh working memory containing only the declared inputs.

## Concept Refinement at Runtime

Concept refinement establishes a type-compatibility relationship. When a pipe declares `inputs = { doc = "ContractClause" }`, any concept that refines `ContractClause` (directly or transitively) is an acceptable input.

A runtime must build and query a refinement graph:

```
function is_compatible(actual_concept, expected_concept):
    if actual_concept == expected_concept:
        return true
    if actual_concept is a native concept and expected_concept == "Anything":
        return true
    parent = refinement_parent(actual_concept)
    if parent is null:
        return false
    return is_compatible(parent, expected_concept)
```

The refinement graph is built during loading by following `refines` fields across all loaded concepts (including cross-package refinements).

## Output Validation

A compliant runtime validates the output of every pipe against the declared output concept's structure at every intermediate step — not just at the method level. This ensures that errors surface at the step that produces incorrect output, not downstream where the symptoms are harder to trace.

**Recommended approach:**

1. After a pipe produces output, resolve the output concept's definition (including its `structure` fields if any).
2. Validate the produced data against the concept's type and field constraints — required fields, field types (`text`, `integer`, `boolean`, `list`, `dict`, `number`, `date`, `concept`), and any `choices` enums.
3. If validation fails, report the error with the pipe code and step index, and halt execution of the current pipeline.

Validation libraries such as Pydantic (Python) or Zod (TypeScript) are natural fits for implementing these checks. Beyond mapping MTHDS concept structures to schema definitions, these libraries also support custom validation logic — expressed in Python or TypeScript — that goes beyond what the MTHDS standard defines.

## Model References

MTHDS defines several forms of model reference (`$` preset, `@` alias, `~` waterfall, and bare handle) that method authors use in the `model` field of `PipeLLM`, `PipeImgGen`, `PipeExtract`, and `PipeSearch`. See [Model References](../language/model-references.md) for the full description and examples.

A runtime must resolve each form to a concrete model configuration. The recommended approach:

1. **Parse the prefix** — inspect the first character of the `model` string to determine the reference kind (`$`, `@`, `~`, or no prefix).
2. **Look up in a registry** — resolve the name (after stripping the prefix) against the appropriate registry:
    - `$` → preset registry (returns a model handle plus parameters such as temperature, max tokens, quality).
    - `@` → alias registry (returns a model handle).
    - `~` → waterfall registry (returns an ordered list of model handles to try in sequence).
    - No prefix → treat the string as a direct model handle.
3. **Return the model configuration** — pass the resolved handle (and any associated parameters) to the operator backend.

A compliant runtime may implement model references differently — or not at all, treating the `model` field as a direct model identifier. The standard requires only that the field be a string.

## Template Blueprint (Advanced PipeCompose)

When the `template` field of a `PipeCompose` pipe is a table (rather than a plain string), it is a **template blueprint** with additional rendering options:

| Field | Type | Description |
|-------|------|-------------|
| `template` | string | The Jinja2 template source. Required. |
| `category` | string | Determines which Jinja2 filters and rendering rules apply. Values: `basic`, `expression`, `html`, `markdown`, `mermaid`, `llm_prompt`, `img_gen_prompt`. |
| `templating_style` | object or null | Controls tag style and text formatting during rendering. |
| `extra_context` | object or null | Additional variables injected into the template rendering context beyond the pipe's declared inputs. |

The `category` field influences which Jinja2 filters are available. For example, `html` templates get HTML-specific filters, while `llm_prompt` templates get prompt-specific filters. The reference implementation registers different filter sets per category.

A compliant runtime must support the plain string form of `template`. The table form with `category`, `templating_style`, and `extra_context` is an advanced feature that implementations may support progressively.
