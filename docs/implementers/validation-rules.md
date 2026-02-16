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
5. Concept codes MUST NOT match any native concept code (`Dynamic`, `Text`, `Image`, `Document`, `Html`, `TextAndImages`, `Number`, `ImgGenPrompt`, `Page`, `JSON`, `Anything`).
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

Each pipe type has specific rules:

**PipeLLM:**

- All prompt and system_prompt variables MUST have matching inputs.
- All inputs MUST be referenced in prompt or system_prompt.

**PipeFunc:**

- `function_name` MUST be present and non-empty.

**PipeImgGen:**

- `prompt` MUST be present.
- All prompt variables MUST have matching inputs.

**PipeExtract:**

- `inputs` MUST contain exactly one entry.
- `output` MUST be `"Page[]"`.

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

- At least one of `add_each_output` or `combined_output` MUST be set.

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
2. `address` MUST match the pattern `^[a-zA-Z0-9._-]+\.[a-zA-Z0-9._-]+/[a-zA-Z0-9._/-]+$`.
3. `version` MUST be valid semver.
4. `description` MUST NOT be empty.
5. All dependency aliases MUST be unique and `snake_case`.
6. All dependency addresses MUST match the hostname/path pattern.
7. All dependency version constraints MUST be valid.
8. Domain paths in `[exports]` MUST be valid domain codes.
9. Domain paths in `[exports]` MUST NOT use reserved domains (`native`, `mthds`, `pipelex`).
10. All pipe codes in `[exports]` MUST be valid `snake_case`.

## Stage 7: Package-Level Validation

After loading all bundles and resolving dependencies:

1. Bundles MUST NOT declare a domain starting with a reserved segment.
2. Cross-package references MUST reference known dependency aliases.
3. Cross-package pipe references MUST target exported pipes.
4. Exported pipes MUST exist in the scanned bundles.
5. Same-domain concept and pipe code collisions across bundles are errors.

## Stage 8: Lock File Validation

For `methods.lock`:

1. Each entry's `version` MUST be valid semver.
2. Each entry's `hash` MUST match `sha256:[0-9a-f]{64}`.
3. Each entry's `source` MUST start with `https://`.

## Stage 9: Publish Validation

The `mthds pkg publish` command runs 15 checks across seven categories. These are advisory (for distribution readiness) rather than mandatory for loading:

| # | Category | Check | Level |
|---|----------|-------|-------|
| 1 | Manifest | `METHODS.toml` exists and parses | Error |
| 2 | Manifest | Authors are specified | Warning |
| 3 | Manifest | License is specified | Warning |
| 4 | Manifest | `mthds_version` constraint is parseable | Error |
| 5 | Manifest | `mthds_version` is satisfiable by current standard version | Warning |
| 6 | Bundle | At least one `.mthds` file exists | Error |
| 7 | Bundle | All bundles parse without error | Error |
| 8 | Export | Every exported pipe exists in the scanned bundles | Error |
| 9 | Visibility | Cross-domain pipe references respect export rules | Error |
| 10 | Visibility | Bundles do not use reserved domains | Error |
| 11 | Visibility | Cross-package references use known dependency aliases | Error |
| 12 | Dependency | No wildcard (`*`) version constraints | Warning |
| 13 | Lock file | `methods.lock` exists for packages with remote dependencies | Error |
| 14 | Lock file | Lock file includes all remote dependency addresses | Warning |
| 15 | Git | Working directory is clean; version tag does not already exist | Warning/Error |
