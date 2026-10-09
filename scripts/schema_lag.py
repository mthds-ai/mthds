#!/usr/bin/env python3
"""Report the documentation's `.mthds` examples that the published schema copy rejects.

`docs/mthds_schema.json` is what mthds.ai serves at `/mthds_schema.json`, and editors and
`plxt` hold `.mthds` files to it. It is not written here: it is the schema a pipelex release
generates, copied in by the workspace's `mthds-schema-sync` skill once that release exists.
So a standard that changes an operator or a native moves ahead of the copy, and the merge to
`main` publishes the two out of step, with nothing saying so.

This script measures that gap where both sides meet, in the documentation's own examples. It
reads every `toml` code block under `docs/` that holds a bundle or a part of one, validates
each pipe and concept it declares against the schema copy, and prints, in Markdown, the ones
the copy rejects and why. A rejected example means that the copy predates the change the
example shows, or that the example is wrong; a person reads which.

It sees one direction only. A copy stricter than the standard shows here, as an example it
rejects; a standard stricter than the copy does not, since every example obeys both the old
rule and the new one while the copy goes on accepting what the standard now rejects. So an
empty report does not mean the copy describes the standard, and the release play reads the
release's own changes beside it.

It is a report, not a gate, and it exits 0 whatever it finds: the copy follows a pipelex
release that may only come after the standard is cut, so the release reports the window
rather than waiting for it to close (`.claude/skills/release/SKILL.md`, Particulars). It exits
1 only when it cannot produce a report: the schema copy is unreadable, or no example was
found, which would mean the extraction below no longer matches how the pages are written.

What is checked:

* A block is a bundle example when its top level declares `domain`, `concept` or `pipe`.
  Manifests, lock files and excerpts of a pipe's fields are not, and are skipped. A block
  that is not valid TOML is skipped too, since some fences show something that is not a file.
* A fragment declaring no `domain` is checked as if it did, since it shows part of a bundle
  whose header is elsewhere.
* A pipe or concept whose every value is a table is an excerpt: the block shows only a
  sub-table, such as `[pipe.judge_is_urgent.criteria]`, of an entity declared in full
  elsewhere, and it is skipped.

The verdict on each pipe and concept is always the whole schema's. The reason printed beside
a rejection comes from the blueprint its kind names, when the schema has one, because that
reason is more precise than the one the whole schema gives.

Run with `make schema-lag`.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any, NamedTuple, cast

from jsonschema.exceptions import SchemaError, ValidationError, best_match
from jsonschema.protocols import Validator
from jsonschema.validators import validator_for

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
SCHEMA = DOCS / "mthds_schema.json"

# A fenced `toml` block, its indentation captured so that a block nested in a list item, a
# content tab or an admonition is closed only by a fence at the same depth.
TOML_FENCE = re.compile(r"^([ \t]*)```toml[^\n]*\n(.*?)^\1```", re.DOTALL | re.MULTILINE)

BUNDLE_KEYS = ("domain", "concept", "pipe")
ENTITY_SECTIONS = ("concept", "pipe")
PLACEHOLDER_DOMAIN = "example"

# A validator's message opens with the value it judged; past this length, that rendering
# drowns the message and is replaced by "the value".
LONGEST_RENDERED_VALUE = 40

JSON_TYPE_NAMES = {
    "object": "a table",
    "array": "an array",
    "string": "a string",
    "integer": "an integer",
    "number": "a number",
    "boolean": "a boolean",
    "null": "nothing",
}


class Example(NamedTuple):
    """A bundle, or part of one, shown in a `toml` code block."""

    page: Path
    line: int
    document: dict[str, Any]


class Rejection(NamedTuple):
    """One thing an example declares that the schema copy rejects, with the reasons why."""

    example: Example
    subject: str
    reasons: list[str]


class SchemaCopy(NamedTuple):
    """The schema copy, with a validator for the whole of it."""

    document: dict[str, Any]
    validator: Validator

    def definition_validator(self, name: str) -> Validator | None:
        """A validator for one of the schema's definitions, or None if it has none of that name."""
        definitions = self.document.get("definitions", {})
        if name not in definitions:
            return None
        wrapper = {"$ref": f"#/definitions/{name}", "definitions": definitions}
        return type(self.validator)(wrapper)

    def knows_pipe_type(self, pipe_type: str) -> bool:
        """Whether the schema's enumeration of pipe types names this one, True when it has none."""
        known = self.document.get("definitions", {}).get("PipeType", {}).get("enum")
        return known is None or pipe_type in known


def load_schema() -> SchemaCopy:
    document = json.loads(SCHEMA.read_text(encoding="utf-8"))
    validator_class = validator_for(document)
    validator_class.check_schema(document)
    return SchemaCopy(document=document, validator=validator_class(document))


def find_examples() -> list[Example]:
    examples: list[Example] = []
    for page in sorted(DOCS.rglob("*.md")):
        text = page.read_text(encoding="utf-8")
        for match in TOML_FENCE.finditer(text):
            indent, body = match.groups()
            if indent:
                body = "\n".join(line.removeprefix(indent) for line in body.split("\n"))
            try:
                document = tomllib.loads(body)
            except tomllib.TOMLDecodeError:
                continue
            if not any(key in document for key in BUNDLE_KEYS):
                continue
            line = text.count("\n", 0, match.start()) + 1
            examples.append(Example(page=page.relative_to(ROOT), line=line, document=document))
    return examples


def is_excerpt(body: object) -> bool:
    """A pipe or concept table of nothing but sub-tables shows part of one declared elsewhere."""
    if not isinstance(body, dict):
        return False
    values = list(cast(dict[str, Any], body).values())
    return bool(values) and all(isinstance(value, dict) for value in values)


def pipe_type_of(body: object) -> str | None:
    """The `type` a pipe table declares, or None when it declares no string there."""
    if not isinstance(body, dict):
        return None
    pipe_type = cast(dict[str, Any], body).get("type")
    return pipe_type if isinstance(pipe_type, str) else None


def check_example(*, example: Example, schema: SchemaCopy) -> list[Rejection]:
    header = dict(example.document)
    header.setdefault("domain", PLACEHOLDER_DOMAIN)
    entities: list[tuple[str, str, Any]] = []
    for section in ENTITY_SECTIONS:
        table = header.get(section)
        if not isinstance(table, dict):
            # Anything but a table stays in the header, where the whole schema judges it.
            continue
        del header[section]
        for code, body in cast(dict[str, Any], table).items():
            if not is_excerpt(body):
                entities.append((section, code, body))

    rejections: list[Rejection] = []
    header_errors = list(schema.validator.iter_errors(header))
    if header_errors:
        rejections.append(
            Rejection(
                example=example,
                subject="the bundle header",
                reasons=explain_all(header_errors, skip=0),
            )
        )
    for section, code, body in entities:
        bundle = {"domain": PLACEHOLDER_DOMAIN, section: {code: body}}
        if schema.validator.is_valid(bundle):
            continue
        reasons = entity_reasons(section=section, body=body, bundle=bundle, schema=schema)
        rejections.append(
            Rejection(
                example=example,
                subject=describe_entity(section=section, code=code, body=body),
                reasons=reasons,
            )
        )
    return rejections


def entity_reasons(
    *, section: str, body: Any, bundle: dict[str, Any], schema: SchemaCopy
) -> list[str]:
    """Why the schema rejects a pipe or a concept the whole schema has already rejected."""
    preamble: list[str] = []
    definition: str
    if section == "concept":
        definition = "ConceptBlueprint"
    else:
        pipe_type = pipe_type_of(body)
        if pipe_type is None:
            # A pipe with no `type` is the contract-only signature, the one blueprint without it.
            preamble = ["declares no `type`, so the schema reads it as a pipe signature"]
            definition = "PipeSignatureBlueprint"
        elif not schema.knows_pipe_type(pipe_type):
            return [f"the schema knows no pipe type `{pipe_type}`"]
        else:
            definition = f"{pipe_type}Blueprint"
    validator = schema.definition_validator(definition)
    if validator is not None:
        errors = list(validator.iter_errors(body))
        if errors:
            return preamble + explain_all(errors, skip=0)
    # No blueprint explains it, so say what the whole schema said, from inside the entity.
    return explain_all(list(schema.validator.iter_errors(bundle)), skip=2)


def describe_entity(*, section: str, code: str, body: Any) -> str:
    pipe_type = pipe_type_of(body)
    if section == "pipe" and pipe_type is not None:
        return f"pipe `{code}` (`{pipe_type}`)"
    return f"{section} `{code}`"


def explain_all(errors: Sequence[ValidationError], *, skip: int) -> list[str]:
    reasons: list[str] = []
    for error in sorted(errors, key=lambda each: [str(part) for part in each.absolute_path]):
        reason = explain(error, skip=skip)
        if reason not in reasons:
            reasons.append(reason)
    return reasons


def explain(error: ValidationError, *, skip: int) -> str:
    """One readable sentence for a validation error, prefixed with where it sits."""
    if error.validator in ("anyOf", "oneOf") and not is_choice_of_required(error) and error.context:
        return explain(branch_error(error), skip=skip)
    where = render_path(list(error.absolute_path)[skip:])
    what = describe_error(error)
    return f"`{where}` {what}" if where else what


# jsonschema types an error's instance, rule and schema loosely; these read them as plain values.
def instance_of(error: ValidationError) -> object:
    return cast(object, error.instance)


def rule_of(error: ValidationError) -> object:
    return cast(object, error.validator_value)


def as_table(value: object) -> dict[str, Any] | None:
    return cast(dict[str, Any], value) if isinstance(value, dict) else None


def as_list(value: object) -> list[Any] | None:
    return cast(list[Any], value) if isinstance(value, list) else None


def branch_error(error: ValidationError) -> ValidationError:
    """The error to explain an `anyOf` or `oneOf` by, from a branch meant for a value of its kind.

    A pydantic field is typically `anyOf` its real shape and `null`, and `best_match` alone prefers
    the shallower error, which is the `null` branch's complaint that the value is not empty. The
    branches whose declared type the value does not even have are set aside first.
    """
    branches = as_list(rule_of(error)) or []
    plausible: list[ValidationError] = []
    for child in error.context:
        index = child.relative_schema_path[0] if child.relative_schema_path else None
        branch: object = (
            branches[index] if isinstance(index, int) and index < len(branches) else None
        )
        if has_declared_type(instance_of(error), branch):
            plausible.append(child)
    return cast(ValidationError, best_match(plausible or error.context))


def has_declared_type(instance: object, branch: object) -> bool:
    """Whether a value has the type a schema branch declares, True when it declares none."""
    table = as_table(branch)
    if table is None or "type" not in table:
        return True
    declared = as_list(table["type"]) or [table["type"]]
    return any(is_json_type(instance, str(each)) for each in declared)


def is_json_type(instance: object, json_type: str) -> bool:
    if json_type == "object":
        return isinstance(instance, dict)
    if json_type == "array":
        return isinstance(instance, list)
    if json_type == "string":
        return isinstance(instance, str)
    if json_type == "boolean":
        return isinstance(instance, bool)
    if json_type == "integer":
        return isinstance(instance, int) and not isinstance(instance, bool)
    if json_type == "number":
        return isinstance(instance, (int, float)) and not isinstance(instance, bool)
    if json_type == "null":
        return instance is None
    return True


def required_choices(error: ValidationError) -> list[str] | None:
    """The fields of a `oneOf` whose branches each only require a field, or None for other rules."""
    if error.validator != "oneOf":
        return None
    branches = as_list(rule_of(error))
    if not branches:
        return None
    names: list[str] = []
    for branch in branches:
        table = as_table(branch)
        required = (
            as_list(table.get("required"))
            if table is not None and set(table) == {"required"}
            else None
        )
        if required is None:
            return None
        names.extend(str(name) for name in required)
    return names


def is_choice_of_required(error: ValidationError) -> bool:
    return required_choices(error) is not None


def describe_error(error: ValidationError) -> str:
    instance = instance_of(error)
    table = as_table(instance)
    choices = required_choices(error)
    if choices is not None:
        present = [name for name in choices if table is not None and name in table]
        if len(present) > 1:
            declared = join_names(present, word="and")
            return f"declares {declared}, where the schema accepts only one of them"
        return f"declares none of {join_names(choices, word='or')}, where the schema requires one"
    if error.validator == "additionalProperties" and table is not None:
        unexpected = unexpected_keys(
            table=table, subschema=as_table(cast(object, error.schema)) or {}
        )
        if unexpected:
            verb = "is not a field" if len(unexpected) == 1 else "are not fields"
            return (
                f"declares {join_names(unexpected, word='and')}, which {verb} the schema knows here"
            )
    if error.validator == "required" and table is not None:
        missing = [str(name) for name in as_list(rule_of(error)) or [] if name not in table]
        if missing:
            return f"lacks {join_names(missing, word='and')}, which the schema requires"
    if error.validator == "type":
        expected = as_list(rule_of(error)) or [rule_of(error)]
        names = [JSON_TYPE_NAMES.get(str(each), str(each)) for each in expected]
        return f"is {kind_of(instance)}, where the schema expects {' or '.join(names)}"
    if error.validator == "enum":
        return f"is `{instance}`, which is not one of the values the schema allows"
    return shorten(error)


def unexpected_keys(*, table: dict[str, Any], subschema: dict[str, Any]) -> list[str]:
    declared = as_table(subschema.get("properties")) or {}
    patterns = [str(pattern) for pattern in as_table(subschema.get("patternProperties")) or {}]
    return [
        key
        for key in table
        if key not in declared and not any(re.search(pattern, key) for pattern in patterns)
    ]


def kind_of(instance: object) -> str:
    if isinstance(instance, bool):
        return "a boolean"
    if isinstance(instance, dict):
        return "a table"
    if isinstance(instance, list):
        return "an array"
    if isinstance(instance, str):
        return "a string"
    if isinstance(instance, int):
        return "an integer"
    if isinstance(instance, float):
        return "a number"
    return "nothing" if instance is None else type(instance).__name__


def shorten(error: ValidationError) -> str:
    """The validator's own message, without the long rendering of the value it opens with."""
    message = error.message
    rendered = repr(instance_of(error))
    if message.startswith(rendered) and len(rendered) > LONGEST_RENDERED_VALUE:
        message = "the value" + message[len(rendered) :]
    return f"fails the schema's `{error.validator}` rule: {message}"


def render_path(parts: Sequence[str | int]) -> str:
    rendered = ""
    for part in parts:
        if isinstance(part, int):
            rendered += f"[{part}]"
        else:
            rendered += f".{part}" if rendered else str(part)
    return rendered


def join_names(names: Sequence[str], *, word: str) -> str:
    quoted = [f"`{name}`" for name in names]
    if len(quoted) <= 1:
        return "".join(quoted)
    return f"{', '.join(quoted[:-1])} {word} {quoted[-1]}"


def counted(count: int, noun: str) -> str:
    return f"{count} {noun}" if count == 1 else f"{count} {noun}s"


def cell(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ")


def render_report(
    *, examples: list[Example], rejections: list[Rejection], schema: SchemaCopy
) -> str:
    schema_path = SCHEMA.relative_to(ROOT)
    rejected = {(rejection.example.page, rejection.example.line) for rejection in rejections}
    pages = {example.page for example in examples}
    lines: list[str] = []
    if rejections:
        lines.append(
            f"## The schema copy rejects {len(rejected)} of the documentation's "
            f"{counted(len(examples), 'bundle example')}"
        )
    else:
        lines.append(
            "## The schema copy accepts every bundle example in the documentation, "
            f"{counted(len(examples), 'bundle example')}"
        )
    lines.append("")
    summary = (
        f"Checked `{schema_path}` against the bundle examples in "
        f"{counted(len(pages), 'page')} of `docs/`."
    )
    comment = schema.document.get("$comment")
    if isinstance(comment, str) and comment:
        summary += f" The copy's `$comment` reads: {comment}"
    lines.append(summary)
    if not rejections:
        lines.extend(
            [
                "",
                "That does not mean the copy describes the standard. This check sees only what "
                "the copy rejects, so a rule the standard tightened, which every example obeys "
                "and the copy goes on accepting, never shows here. Compare the copy with the "
                "release's changes to what a bundle may declare as well.",
            ]
        )
        return "\n".join(lines) + "\n"
    lines.extend(
        [
            "",
            "| Example | Declares | Why the schema copy rejects it |",
            "| --- | --- | --- |",
        ]
    )
    for rejection in rejections:
        where = f"`{rejection.example.page}:{rejection.example.line}`"
        lines.append(
            f"| {where} | {cell(rejection.subject)} | {cell('; '.join(rejection.reasons))} |"
        )
    lines.extend(
        [
            "",
            "Any tool validating `.mthds` files against this copy flags each of these, and "
            "mthds.ai serves the copy once it is released, which is where the editor extension "
            "and `plxt` take theirs from. Either the copy predates the change the example "
            "shows, since it is the schema a pipelex release generates and the workspace's "
            "`mthds-schema-sync` skill brings it in once a release implements the change, or "
            "the example is wrong. A release goes ahead all the same, and says so in its "
            "changelog entry and its pull request.",
            "",
            "The table cannot list a rule the standard tightened, which every example obeys and "
            "the copy goes on accepting. Compare the copy with the release's changes to what a "
            "bundle may declare for those.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    try:
        schema = load_schema()
    except (OSError, json.JSONDecodeError, SchemaError) as exc:
        # The root of the command: no report can be produced without the schema copy.
        print(f"Cannot read the schema copy {SCHEMA.relative_to(ROOT)}: {exc}", file=sys.stderr)
        return 1
    examples = find_examples()
    if not examples:
        print(
            "Found no bundle example in any `toml` code block under docs/, so the extraction no "
            "longer matches how the pages are written. Fix scripts/schema_lag.py before "
            "trusting its report.",
            file=sys.stderr,
        )
        return 1
    rejections: list[Rejection] = []
    for example in examples:
        rejections.extend(check_example(example=example, schema=schema))
    print(render_report(examples=examples, rejections=rejections, schema=schema), end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
