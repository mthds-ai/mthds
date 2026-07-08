---
description: "Declare values that may legitimately be absent with MTHDS presence markers, recorded absences, lifting, and validation checks."
---

# Optionality

Optionality lets a method say that a value may legitimately be absent. This is different from a failed pipe, a missing field, or a silent `null`: absence is a declared part of the pipe contract and is carried through the run as data.

## Presence Markers

A concept reference in a pipe's `inputs` or `output` can carry a presence marker:

| Declaration | Meaning |
|-------------|---------|
| `note = "Note"` | Plain. The value is required by this pipe. If it is absent at run time, the pipe is skipped and absence propagates. |
| `note = "Note?"` | Optional. The pipe runs even when the value is absent and must handle that case. On an output, the pipe may produce a recorded absence instead of a value. |
| `note = "Note!"` | Force. Inputs only. The pipe asserts the value must be present; an absent value fails the run loudly. |

Markers apply only to pipe `inputs` and `output`. They do not apply to concept definitions, `refines`, or structure fields.

## Grammar Rules

- Presence markers come after the concept reference: `Concept?`, `domain.Concept!`.
- Markers never combine with multiplicity. `Concept[]?`, `Concept[3]?`, and `Concept[]!` are invalid because plural slots use an empty list when no items are produced.
- Outputs accept only `?`. `Concept!` is invalid on `output` because a pipe cannot force its own result into existence.

## Runtime Behavior

When a pipe is about to run and an input slot is absent:

1. A plain input skips the pipe. The pipe's output is recorded as a skipped absence, with provenance pointing to the upstream absence.
2. An optional input lets the pipe run. Template-rendering pipes must guard optional references.
3. A force input fails the run with an explicit absence error and provenance.

A completed pipe always resolves its declared output: either a value or a recorded absence. If a method's main output is absent, the run is still successful and the result carries an explicit absence document rather than an empty or missing output.

## Guarding Templates

Templates that reference optional inputs must guard those references. Valid guard forms include:

- `@?note` shorthand, which renders the content only when present.
- `{% if note %}...{% endif %}` blocks.
- Inline conditionals such as `{{ note.text if note else "" }}`.

Unguarded optional references are validation errors.

## Controllers Under Absence

- `PipeSequence` propagates skipped outputs through later steps. If the final output can be absent, the sequence output must be declared `?`.
- `PipeCondition` with a `continue` outcome resolves its output as absent; such outputs must be declared `?`.
- `PipeParallel` omits absent components from `Composite` outputs, absorbs absent branches into non-required structured fields, and rejects maybe-absent branches feeding required fields.
- `PipeBatch` compacts absent branch results out of the output list.

## Validation Surface

Compliant runtimes should surface optionality problems with structured diagnostics:

| Error | Meaning |
|-------|---------|
| `optional_marker_invalid` | Invalid marker grammar, such as a marker on a plural reference or `!` on output. |
| `optional_not_handled` | A maybe-absent value escapes through a non-optional boundary. |
| `optional_output_required` | A `PipeCondition` can continue without producing a value but its output is not `?`. |
| `optional_input_unguarded` | A template reads an optional input without a guard. |
| `optional_branch_required_field` | A maybe-absent `PipeParallel` branch feeds a required structured field. |

Valid reports may also include `liftable_pipes`, listing pipes that may be skipped at run time, and advisory `warnings` such as redundant force markers.

