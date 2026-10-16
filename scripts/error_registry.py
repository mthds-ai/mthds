#!/usr/bin/env python3
"""The MTHDS core error registry: load it, check it, and write its JSON snapshot.

The registry is authored once, as data, in docs/spec/openapi/mthds-error-registry.yaml,
beside the protocol's OpenAPI document. Everything else is derived from it: the JSON
snapshot that clients vendor (mthds-error-registry.json, written by `write` and compared
by `check`), and the one page per code that the mkdocs hook scripts/error_registry_pages.py
generates at build time.

    python scripts/error_registry.py check   # run by `make spec-check`, so by `make docs-check`
    python scripts/error_registry.py write   # `make errors`: regenerate the snapshot

`check` refuses, each with the place it found the fault:

* an entry or a document the JSON Schema refuses, an entry with a member missing included;
* a duplicate key in the YAML, which a YAML loader would otherwise keep silently;
* a code given twice, a code whose family is not declared, a family no code uses;
* an extension prefix given twice, or one named like a core family;
* a template naming a parameter the code does not declare, or one a reader may not see;
* a reference to a page the documentation does not hold;
* a closed list of the schema that differs from the OpenAPI document's;
* a typed parameter of the OpenAPI document's ProblemParams typed otherwise here;
* a problem document shown in the documentation that disagrees with its code's entry;
* a snapshot that is not what `write` would produce.
"""

from __future__ import annotations

import json
import re
import string
import sys
from pathlib import Path
from typing import Any, Iterator

import yaml
from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
SPEC_DIR = DOCS / "spec" / "openapi"
REGISTRY_PATH = SPEC_DIR / "mthds-error-registry.yaml"
SCHEMA_PATH = SPEC_DIR / "mthds-error-registry.schema.json"
SNAPSHOT_PATH = SPEC_DIR / "mthds-error-registry.json"
OPENAPI_PATH = SPEC_DIR / "mthds-protocol.openapi.yaml"

CATCH_ALL = "runtime.unexpected"
SHA256_PATTERN = "^[0-9a-f]{64}$"

# The generated pages, as paths from the documentation's root (see scripts/error_registry_pages.py).
PAGES_DIR = "errors"
INDEX_PAGE = f"{PAGES_DIR}/index.md"


def rel(path: Path) -> str:
    return str(path.relative_to(ROOT))


class UniqueKeyLoader(yaml.SafeLoader):
    """A safe loader that refuses a mapping holding the same key twice."""


def _construct_unique_mapping(loader: UniqueKeyLoader, node: yaml.MappingNode, deep: bool = False) -> dict:
    seen: set[Any] = set()
    for key_node, _value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in seen:
            raise yaml.constructor.ConstructorError(
                None, None, f"duplicate key {key!r}", key_node.start_mark
            )
        seen.add(key)
    return loader.construct_mapping(node, deep=deep)


UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_unique_mapping
)


def load_yaml(path: Path) -> Any:
    with path.open(encoding="utf-8") as stream:
        return yaml.load(stream, Loader=UniqueKeyLoader)


def load_registry(path: Path = REGISTRY_PATH) -> dict:
    return load_yaml(path)


def load_schema(path: Path = SCHEMA_PATH) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def type_uri(registry: dict, code: str) -> str:
    """The type URI of a code: its registry's base URL, a slash, then the whole code."""
    return f"{registry['base_url']}/{code}"


def family_of(code: str) -> str:
    """A code's family is the code without its last segment."""
    return code.rsplit(".", 1)[0]


def page_path(code: str) -> str:
    """The page of a core code, from the documentation's root: one directory per segment but the last.

    `input.missing` is `errors/input/missing.md`, served at `/<version>/errors/input/missing/`. A
    page is never named after the whole code, because the site's host answers a URL whose last
    segment has a dot, such as `errors/input.missing/`, by redirecting it to the same URL without
    its trailing slash, where the page's relative links no longer resolve. vercel.json redirects
    the type URI, `https://mthds.ai/errors/<family>.<name>`, to `/latest/errors/<family>/<name>/`.
    """
    return f"{PAGES_DIR}/{code.replace('.', '/')}.md"


def entries_by_code(registry: dict) -> dict[str, dict]:
    return {entry["code"]: entry for entry in registry.get("codes", [])}


def placeholders(template: str) -> list[str]:
    """The parameter names a template names; raises ValueError on a malformed template."""
    names = []
    for _literal, field, spec, conversion in string.Formatter().parse(template):
        if field is None:
            continue
        if not re.fullmatch(r"[a-z][a-z0-9_]*", field):
            raise ValueError(f"placeholder {{{field}}} is not a parameter name")
        if spec or conversion:
            raise ValueError(f"placeholder {{{field}}} carries a format specification")
        names.append(field)
    return names


def render(template: str, params: dict[str, Any]) -> str:
    """Render a template: a list is written as its items joined by a comma and a space."""
    values = {
        name: ", ".join(str(item) for item in value) if isinstance(value, list) else value
        for name, value in params.items()
    }
    return template.format(**values)


# --- the checks -----------------------------------------------------------------------


def schema_errors(registry: Any, schema: dict, where: str) -> list[str]:
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors = []
    for error in sorted(validator.iter_errors(registry), key=lambda found: [str(part) for part in found.absolute_path]):
        parts = [str(part) for part in error.absolute_path]
        if len(parts) >= 2 and parts[0] == "codes":
            # Name the entry by its code rather than by its index, when it has one.
            entry = registry["codes"][int(parts[1])]
            if isinstance(entry, dict) and isinstance(entry.get("code"), str):
                parts[1] = entry["code"]
        path = "/".join(parts) or "(root)"
        message = error.message
        if error.schema is False:
            # A member the schema forbids in this case, such as a status on a warning. The
            # error points at the object holding it, so find the member by its value.
            holder: Any = registry
            for part in error.absolute_path:
                holder = holder[part]
            members = [key for key, value in holder.items() if value is error.instance] if isinstance(holder, dict) else []
            message = f"the member {', '.join(members) or repr(error.instance)} is not allowed here"
        errors.append(f"{where}: {path}: {message}")
    return errors


def semantic_errors(registry: dict, where: str) -> list[str]:
    """The rules a JSON Schema cannot state. Run only on a document the schema accepts."""
    errors: list[str] = []
    prefix = registry.get("prefix")
    families = [family["family"] for family in registry["families"]]
    used_families: set[str] = set()

    for family in sorted({name for name in families if families.count(name) > 1}):
        errors.append(f"{where}: the family {family} is declared twice")
    if prefix is not None:
        for family in families:
            if not family.startswith(f"{prefix}."):
                errors.append(f"{where}: the family {family} does not start with the prefix {prefix}")

    seen_codes: set[str] = set()
    for entry in registry["codes"]:
        code = entry["code"]
        here = f"{where}: {code}"
        if code in seen_codes:
            errors.append(f"{here}: the code is declared twice")
        seen_codes.add(code)
        if prefix is not None and not code.startswith(f"{prefix}."):
            errors.append(f"{here}: the code does not start with the registry's prefix {prefix}")
        family = family_of(code)
        used_families.add(family)
        if family not in families:
            errors.append(f"{here}: its family {family} is not declared under families")
        errors.extend(template_errors(entry, here))
        for reference in entry.get("see", []):
            page = reference["href"].split("#", 1)[0]
            if not (DOCS / page).is_file():
                errors.append(f"{here}: see names {page}, which the documentation does not hold")

    for family in families:
        if family not in used_families:
            errors.append(f"{where}: the family {family} is declared but no code belongs to it")

    if prefix is None:
        errors.extend(core_errors(registry, families, where))
    return errors


def template_errors(entry: dict, here: str) -> list[str]:
    """Templates name declared parameters, and only those the reader of each may see.

    A parameter declared optional may be absent, so no template names it. An operator-only
    parameter never reaches a caller, so only the actor's step of an operator code, which
    whoever runs the runtime reads, may name one.
    """
    errors = []
    params = entry["params"]
    templates = [
        ("detail", entry["detail"], False),
        ("steps.actor.detail", entry["steps"]["actor"]["detail"], entry["domain"] == "operator"),
        ("steps.other.detail", entry["steps"]["other"]["detail"], False),
    ]
    for name, template, operator_reads in templates:
        try:
            names = placeholders(template)
        except ValueError as error:
            errors.append(f"{here}: {name}: {error}")
            continue
        for param in names:
            declared = params.get(param)
            if declared is None:
                errors.append(f"{here}: {name} names {{{param}}}, which the code does not declare")
            elif declared.get("optional"):
                errors.append(f"{here}: {name} names {{{param}}}, which is optional and may be absent")
            elif declared.get("operator_only") and not operator_reads:
                errors.append(
                    f"{here}: {name} names the operator-only {{{param}}}, which a caller may read"
                )
    return errors


def core_errors(registry: dict, families: list[str], where: str) -> list[str]:
    errors = []
    prefixes = [entry["prefix"] for entry in registry["extension_prefixes"]]
    for prefix in sorted({name for name in prefixes if prefixes.count(name) > 1}):
        errors.append(f"{where}: the extension prefix {prefix} is registered twice")
    for prefix in prefixes:
        if prefix in families:
            errors.append(f"{where}: the extension prefix {prefix} is the name of a core family")
    catch_all = entries_by_code(registry).get(CATCH_ALL)
    if catch_all is None:
        errors.append(f"{where}: the catch-all code {CATCH_ALL} is missing")
    elif not (
        catch_all["retry"] == "no"
        and catch_all["steps"]["actor"]["kind"] == "report"
        and catch_all["steps"]["other"]["kind"] == "report"
    ):
        errors.append(f"{where}: the catch-all code {CATCH_ALL} must have retry no and the step report")
    return errors


def openapi_errors(registry: dict, schema: dict, openapi: dict) -> list[str]:
    """The registry's closed lists and typed parameters agree with the OpenAPI document."""
    errors = []
    components = openapi["components"]["schemas"]
    pairs = [("domain", "ProblemDomain"), ("retry", "RetryVerdict"), ("stepKind", "StepKind")]
    for definition, component in pairs:
        ours = schema["$defs"][definition]["enum"]
        theirs = components[component]["enum"]
        if ours != theirs:
            errors.append(
                f"{rel(SCHEMA_PATH)}: $defs/{definition} lists {ours}, but {rel(OPENAPI_PATH)} "
                f"lists {theirs} as {component}"
            )
    typed = components["ProblemParams"].get("properties", {})
    owners = {
        name: [entry["code"] for entry in registry["codes"] if name in entry["params"]] for name in typed
    }
    for name, property_schema in typed.items():
        if not owners[name]:
            errors.append(
                f"{rel(OPENAPI_PATH)}: ProblemParams types {name}, which no core code declares"
            )
        for code in owners[name]:
            declared = entries_by_code(registry)[code]["params"][name]
            if param_json_schema(declared) != strip_description(property_schema):
                errors.append(
                    f"{rel(OPENAPI_PATH)}: ProblemParams types {name} as "
                    f"{strip_description(property_schema)}, but {code} declares "
                    f"{param_json_schema(declared)}"
                )
    return errors


def strip_description(schema: dict) -> dict:
    return {key: value for key, value in schema.items() if key != "description"}


def param_json_schema(param: dict) -> dict:
    """The JSON Schema a parameter's declared type stands for."""
    kind = param["type"]
    if kind == "list":
        return {"type": "array", "items": param_json_schema(param["items"])}
    if kind == "enum":
        return {"type": "string", "enum": list(param["values"])}
    return {
        "identifier": {"type": "string"},
        "caller_text": {"type": "string"},
        "sha256": {"type": "string", "pattern": SHA256_PATTERN},
        "integer": {"type": "integer"},
        "bytes": {"type": "integer", "minimum": 0},
        "seconds": {"type": "number", "minimum": 0},
    }[kind]


def json_examples(path: Path) -> Iterator[tuple[int, Any]]:
    """Each ```json block of a page that parses, with the line its fence opens on."""
    lines = path.read_text(encoding="utf-8").splitlines()
    index = 0
    while index < len(lines):
        if lines[index].strip() == "```json":
            start = index
            index += 1
            body = []
            while index < len(lines) and lines[index].strip() != "```":
                body.append(lines[index])
                index += 1
            try:
                yield start + 1, json.loads("\n".join(body))
            except json.JSONDecodeError:
                pass
        index += 1


def example_errors(registry: dict) -> list[str]:
    """A problem document the documentation shows agrees with the entry of its code."""
    errors = []
    entries = entries_by_code(registry)
    families = {family["family"] for family in registry["families"]}

    def check(node: Any, where: str, is_item: bool) -> None:
        if isinstance(node, list):
            for item in node:
                check(item, where, is_item)
            return
        if not isinstance(node, dict):
            return
        code = node.get("code")
        # A code of exactly two segments is a core code by its shape, so one whose family the
        # registry does not declare is refused rather than skipped, as a misspelt family would be.
        if isinstance(code, str) and re.fullmatch(r"[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*", code):
            errors.extend(problem_errors(node, code, entries.get(code), where, is_item))
        for key, value in node.items():
            check(value, where, is_item or key in ("errors", "warnings"))

    def problem_errors(node: dict, code: str, entry: dict | None, where: str, is_item: bool) -> list[str]:
        if entry is None:
            if family_of(code) not in families:
                return [
                    f"{where}: the example uses {code}, whose family {family_of(code)} the registry does not declare"
                ]
            return [f"{where}: the example uses {code}, which the registry does not declare"]
        found = []
        expected = {"title": entry["title"], "domain": entry["domain"], "retry": entry["retry"]}
        expected["type"] = type_uri(registry, code)
        if "status" in entry:
            expected["status"] = entry["status"]
        for member, value in expected.items():
            if member in node and node[member] != value:
                found.append(f"{where}: {code}'s {member} is {node[member]!r}, but its entry says {value!r}")
        step = node.get("next_step")
        if isinstance(step, dict) and "kind" in step:
            kinds = {entry["steps"]["actor"]["kind"], entry["steps"]["other"]["kind"]}
            if step["kind"] not in kinds:
                found.append(f"{where}: {code}'s next_step.kind is {step['kind']!r}, not one its entry declares")
        params = node.get("params")
        if isinstance(params, dict):
            for name in params:
                if name not in entry["params"]:
                    found.append(f"{where}: {code}'s params carry {name}, which its entry does not declare")
        return found

    for path in sorted(DOCS.rglob("*.md")):
        if path.name == "changelog.md":
            continue
        for line, document in json_examples(path):
            check(document, f"{rel(path)}:{line}", False)
    return errors


def snapshot_text(registry: dict) -> str:
    return json.dumps(registry, indent=2, ensure_ascii=False) + "\n"


def snapshot_errors(registry: dict) -> list[str]:
    if not SNAPSHOT_PATH.is_file():
        return [f"{rel(SNAPSHOT_PATH)} does not exist: run `make errors` to write it"]
    if SNAPSHOT_PATH.read_text(encoding="utf-8") != snapshot_text(registry):
        return [
            f"{rel(SNAPSHOT_PATH)} is not the snapshot of {rel(REGISTRY_PATH)}: "
            f"run `make errors` to regenerate it, and never edit it by hand"
        ]
    return []


def registry_errors(registry: Any, schema: dict, where: str) -> list[str]:
    """The checks a registry document must pass on its own: the schema, then the rest."""
    errors = schema_errors(registry, schema, where)
    if errors:
        return errors
    return semantic_errors(registry, where)


def check() -> list[str]:
    where = rel(REGISTRY_PATH)
    try:
        registry = load_registry()
    except yaml.YAMLError as error:
        return [f"{where}: {error}"]
    schema = load_schema()
    Draft202012Validator.check_schema(schema)
    errors = registry_errors(registry, schema, where)
    if errors:
        return errors
    errors.extend(openapi_errors(registry, schema, load_yaml(OPENAPI_PATH)))
    errors.extend(example_errors(registry))
    errors.extend(snapshot_errors(registry))
    return errors


def main(argv: list[str]) -> int:
    command = argv[1] if len(argv) > 1 else "check"
    if command == "write":
        registry = load_registry()
        errors = registry_errors(registry, load_schema(), rel(REGISTRY_PATH))
        if errors:
            print("The error registry is invalid, so no snapshot was written:\n", file=sys.stderr)
            for error in errors:
                print(f"  - {error}", file=sys.stderr)
            return 1
        SNAPSHOT_PATH.write_text(snapshot_text(registry), encoding="utf-8")
        print(f"Wrote {rel(SNAPSHOT_PATH)} ({len(registry['codes'])} codes)")
        return 0
    if command == "check":
        errors = check()
        if errors:
            print("Error registry check FAILED:\n", file=sys.stderr)
            for error in errors:
                print(f"  - {error}", file=sys.stderr)
            print("", file=sys.stderr)
            return 1
        registry = load_registry()
        prefixes = len(registry["extension_prefixes"])
        print(
            f"Error registry {registry['version']}: {len(registry['codes'])} codes in "
            f"{len(registry['families'])} families, {prefixes} extension "
            f"{'prefix' if prefixes == 1 else 'prefixes'} — consistent"
        )
        return 0
    print(f"usage: {argv[0]} check|write", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
