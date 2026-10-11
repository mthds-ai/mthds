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

- `@?note` shorthand in fields that run shorthand preprocessing: `PipeLLM.prompt`, `PipeLLM.system_prompt`, `PipeImgGen.prompt`, `PipeImgGen.negative_prompt`, `PipeSearch.prompt`, `PipeJudge.prompt`, every PipeJudge question, and `PipeCompose.template`. It renders content only when present.
- Raw Jinja2 `{% if note %}...{% endif %}` blocks for Jinja2-rendered fields, including fields where shorthand preprocessing does not run.
- Inline conditionals such as `{{ note.text if note else "" }}`.

Unguarded optional references are validation errors.

Being optional does not exempt an input from being read: `PipeLLM`, `PipeImgGen`, `PipeSearch`, `PipeJudge` and `PipeCompose` reject a declared input they never read, whether it is optional or not. A guarded reference such as `@?note` counts as a read.

## Controllers Under Absence

- `PipeSequence` propagates skipped outputs through later steps. If the final output can be absent, the sequence output must be declared `?`.
- `PipeCondition` with a `continue` outcome resolves its output as absent; such outputs must be declared `?`.
- `PipeParallel` omits absent components from `Composite` outputs, absorbs absent branches into non-required structured fields, and rejects maybe-absent branches feeding required fields.
- `PipeBatch` compacts absent branch results out of the output list.
- A [binding step](pipes-controllers.md#binding-steps) in a `PipeSequence` lifts when its root is absent, and records an absence when its path reaches nothing, as described below.

## Absence Through a Binding Step

A binding step reads a field of a value, and the data may not hold that field. The step introduces no new kind of absence: like a pipe's output, a single result is either a value or a recorded absence, and a list result is never absent.

```toml
[concept.Delivery]
description = "A parcel delivery"

[concept.Delivery.structure]
address = { type = "text", description = "The delivery address", required = true }
note    = { type = "text", description = "A note the sender left for the courier" }

[pipe.brief_courier]
type        = "PipeSequence"
description = "Write the courier's briefing for a delivery"
inputs      = { delivery = "Delivery" }
output      = "Text"
steps = [
    { from = "delivery.address", result = "address" },
    { from = "delivery.note", result = "courier_note" },
    { pipe = "write_briefing", result = "briefing" },
]

[pipe.write_briefing]
type        = "PipeLLM"
description = "Write a short briefing for the courier"
inputs      = { address = "Text", courier_note = "Text?" }
output      = "Text"
prompt      = """
Write a one-paragraph briefing for a courier delivering to $address.

@?courier_note
"""
```

`note` is not required, so `courier_note` may be absent: for a delivery with no note, the binding records an absence whose provenance names `note` as the segment that held nothing. `write_briefing` declares the input optional and guards the read with `@?`, so it runs either way. Had it declared `courier_note = "Text"`, it would be skipped when the note is missing, and the sequence, whose output it produces, would have to declare its output `Text?`. `address` is required, so its binding is never absent.

The rules:

- **An absent root lifts the step.** The root is read like a plain input. When it is absent, the binding step is skipped and a single result is recorded as a skipped absence, with provenance pointing to the root's absence. A list result is an empty list instead, since a plural slot is never absent.
- **A path reaching nothing records an absence.** When the result is a single value and a segment holds nothing, at the leaf or at any segment before it, the result is a recorded absence whose provenance names that segment. This is not an error.
- **A list result is never absent.** When the path crosses a list, an item that holds nothing contributes nothing, and the result is a shorter list, or an empty one.
- **Statically,** a single result may be absent when its root may be, or when its path walks a field that is not `required` and has no `default_value`. Structure fields default to `required = false`, so most single-value bindings may be absent unless the concept marks the field required.

From there the usual rules apply: a plain consumer lifts, an optional consumer runs and guards the read, and a maybe-absent result reaching the sequence's output requires the output to be declared `?`.

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

A binding step's absences are reported with the diagnostics above. Its own faults are `binding_step_invalid`, for a malformed binding step or one placed in a `PipeParallel` branch, and `binding_path_unresolved`, for a path the declared structures cannot walk; both are specified in [Binding Steps](../spec/mthds-format.md#validation-surface).
