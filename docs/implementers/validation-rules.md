---
description: "Complete validation checklist for MTHDS implementers — ordered by stage from TOML parsing through cross-package resolution."
---

# Validation Rules

This page consolidates all validation rules from the [Specification](../spec/mthds-format.md) into an ordered checklist for implementers. Rules are grouped by the stage at which they should be enforced.

## Stage 1: TOML Parsing

Before any MTHDS-specific validation, the file must be valid TOML.

- The file MUST be valid UTF-8-encoded TOML.
- A `.mthds` file MUST have the `.mthds` extension.
- `METHODS.toml` MUST be named exactly `METHODS.toml`.
- `methods.lock` MUST be named exactly `methods.lock`.

## Stage 2: Bundle Structural Validation

After parsing TOML into a dictionary, validate the bundle structure:

1. `domain` MUST be present.
2. `domain` MUST be a valid domain code: one or more `snake_case` segments (`[a-z][a-z0-9_]*`) separated by `.`.
3. `main_pipe`, if present, MUST be `snake_case` and MUST reference a pipe defined in the same bundle.
4. Concept codes MUST be `PascalCase` (`[A-Z][a-zA-Z0-9]*`).
5. Concept codes MUST NOT match any native concept code (`Dynamic`, `Text`, `Image`, `Document`, `Html`, `TextAndImages`, `Number`, `YesNo`, `Date`, `Time`, `Page`, `JSON`, `SearchResult`, `Anything`, `Composite`).
6. Pipe codes MUST be `snake_case` (`[a-z][a-z0-9_]*`).
7. `refines` and `structure` MUST NOT both be set on the same concept.

## Stage 3: Concept Field Validation

For each field in a concept's `structure`:

1. `description` MUST be present.
2. If `type` is omitted, `choices` MUST be non-empty.
3. `type = "dict"` requires both `key_type` and `value_type`.
4. `type = "concept"` requires `concept_ref` and forbids `default_value`.
5. `type = "list"` with `item_type = "concept"` requires `item_concept_ref`.
6. `concept_ref` MUST NOT be set unless `type = "concept"`.
7. `item_concept_ref` MUST NOT be set unless `item_type = "concept"`.
8. `default_value` type MUST match the declared `type`.
9. If `choices` is set and `default_value` is present, `default_value` MUST be in `choices`.
10. Field names MUST NOT start with `_`.

## Stage 4: Pipe Type-Specific Validation

Each concrete pipe type has specific rules. A typeless `[pipe.<code>]` section is valid only when it is a contract-only signature containing `description`, optional `inputs`, required `output`, optional `signature_for` (when present, one of the concrete `PipeType` values), and no implementation fields.

**PipeLLM:**

- All prompt and system_prompt variables MUST have matching inputs.
- All inputs MUST be referenced in prompt or system_prompt.

**PipeStructure:**

- `inputs` MUST contain exactly one entry.
- The single input concept MUST be `Text` or a concept that refines `Text`.
- `output` MUST NOT be `Text` and MUST NOT be a concept that refines `Text`.
- `output` MAY use multiplicity (`Foo`, `Foo[]`, `Foo[N]`).

**PipeFunc:**

- `function_name` MUST be present and non-empty.

**PipeImgGen:**

- `prompt` MUST be present.
- All prompt variables MUST have matching inputs.

**PipeExtract:**

- `inputs` MUST contain exactly one entry.
- `output` MUST be `"Page[]"`.

**PipeSearch:**

- `prompt` MUST be present.
- All prompt variables MUST have matching inputs.
- `output` MUST be `SearchResult` or a concept that refines `SearchResult`.

**PipeCompose:**

- Exactly one of `template` or `construct` MUST be present.
- `output` MUST NOT use multiplicity brackets (`[]` or `[N]`).
- All template/construct variables MUST have matching inputs.

**PipeSequence:**

- `steps` MUST have at least one entry.
- `nb_output` and `multiple_output` MUST NOT both be set on the same step.
- `batch_over` and `batch_as` MUST either both be present or both be absent.
- `batch_over` and `batch_as` MUST NOT be the same value.

**PipeParallel:**

- `branches` MUST have at least one entry.
- `output` MUST be `Composite` or a structured concept.
- `output` MUST NOT use multiplicity brackets (`[]` or `[N]`).
- For structured output, required fields MUST be produced by matching branch `result` names and branch output concepts MUST be compatible with the corresponding fields.

**Optionality:**

- Presence markers (`?` and `!`) MAY appear only on pipe `inputs` and `output`.
- Presence markers MUST NOT be combined with multiplicity brackets.
- `!` MUST NOT appear on `output`.
- A `PipeCondition` that can resolve to `continue` MUST declare an optional (`?`) output.
- A template-rendering pipe MUST guard references to declared-optional inputs.
- A maybe-absent `PipeParallel` branch MUST NOT feed a required structured output field.

**PipeCondition:**

- Exactly one of `expression_template` or `expression` MUST be present.
- `outcomes` MUST have at least one entry.

**PipeBatch:**

- `input_list_name` MUST be in `inputs`.
- `input_item_name` MUST NOT be empty.
- `input_item_name` MUST NOT equal `input_list_name`.
- `input_item_name` MUST NOT equal any key in `inputs`.

## Stage 5: Reference Validation (Bundle-Level)

Within a single bundle:

- Bare concept references MUST resolve to: a native concept, a concept in the current bundle, or a concept in the same domain (same package).
- Bare pipe references MUST resolve to: a pipe in the current bundle, or a pipe in the same domain (same package).
- Domain-qualified references MUST resolve within the current package.
- Cross-package references (`->` syntax) are deferred to package-level validation.

## Stage 6: Manifest Validation

For `METHODS.toml`:

1. `[package]` section MUST be present.
2. `name` MUST be present, `snake_case`, and 2–25 characters.
3. `address` MUST match the pattern `^[a-zA-Z0-9._-]+\.[a-zA-Z0-9._-]+/[a-zA-Z0-9._/-]+$`.
4. `version` MUST be valid semver.
5. `description` MUST NOT be empty.
6. `main_pipe`, if present, MUST be a valid `snake_case` pipe code.
7. All dependency aliases MUST be unique and `snake_case`.
8. All dependency addresses MUST match the hostname/path pattern.
9. All dependency version constraints MUST be valid.
10. Domain paths in `[exports]` MUST be valid domain codes and MUST NOT use reserved domains (`native`, `mthds`, `pipelex`).
11. All pipe codes in `[exports]` MUST be valid `snake_case`.

## Stage 7: Package-Level Validation

After loading all bundles and resolving dependencies:

1. Bundles MUST NOT declare a domain starting with a reserved segment.
2. Cross-package references MUST reference known dependency aliases.
3. Cross-package pipe references MUST target pipes exported by the dependency — diagnosed at validation time, never silently filtered at load time.
4. Exported pipes MUST exist in the scanned bundles.
5. Same-domain concept and pipe code collisions across bundles (within one package) are errors.

## Stage 8: Lock File Validation

For `methods.lock`:

1. Each entry's `version` MUST be valid semver.
2. Each entry's `hash` MUST match `sha256:[0-9a-f]{64}`.
3. Each entry's `fingerprint` MUST be a 64-character lowercase hex digest.
4. Each entry's `source` MUST start with `https://` and end with `.git`.
5. Each entry's `commit` MUST be a 40-character lowercase hex digest.
