"""MkDocs hook: one page per code of the MTHDS core error registry, and their index.

The registry is data, authored in docs/spec/openapi/mthds-error-registry.yaml, so its pages are
generated at build time rather than written by hand: `errors/index.md`, which the navigation
lists, and `errors/<code>.md` for each code, which it does not. Under the site's directory URLs
a code's page is served at `/<version>/errors/<code>/`, and vercel.json redirects the type URI,
`https://mthds.ai/errors/<code>`, to its `/latest/` copy.

The hook refuses to build from a registry that `scripts/error_registry.py` would refuse, and
warns, which `--strict` turns into a failure, when the committed JSON snapshot has drifted.
Links in the generated pages are checked by MkDocs like any other page's.
"""

from __future__ import annotations

import json
import logging
import re

from mkdocs.config.defaults import MkDocsConfig
from mkdocs.exceptions import PluginError
from mkdocs.plugins import event_priority
from mkdocs.structure.files import File, Files, InclusionLevel

import error_registry as registry_module

log = logging.getLogger("mkdocs.hooks.error_registry_pages")

PAGES_DIR = "errors"
SPEC_PAGE = "../spec/error-registry.md"
PROTOCOL_PAGE = "../spec/protocol.md"
SNAPSHOT_LINK = "../spec/openapi/mthds-error-registry.json"

# Who acts, per domain, in the words of the protocol's domain table.
DOMAIN_ACTORS = {
    "input": "the caller, by changing the request or its inputs",
    "method": "the method's author, by changing the method",
    "account": "the account's owner",
    "operator": "whoever runs the runtime",
    "runtime": "nobody beforehand: wait, retry or report",
}

RETRY_MEANINGS = {
    "no": "repeating the operation fails the same way",
    "yes": "repeating the operation may succeed, after `retry_after` seconds when the problem gives it",
    "outcome_unknown": "the operation may already have taken effect, so its outcome is learned before anything is repeated",
}

RAISED_AS = {
    "problem": "a problem document, the body of an HTTP response or kept in a run's record",
    "warning": "an item of a validate verdict's `warnings`, which never makes a method invalid",
    "client": "an error a client detects itself, never received from a runner",
}


@event_priority(100)  # before llmstxt-md reads the file list for its sections
def on_files(files: Files, *, config: MkDocsConfig) -> Files:
    registry = registry_module.load_registry()
    where = registry_module.rel(registry_module.REGISTRY_PATH)
    errors = registry_module.registry_errors(registry, registry_module.load_schema(), where)
    if errors:
        listing = "\n".join(f"  - {error}" for error in errors)
        raise PluginError(f"The error registry is invalid, so its pages cannot be built:\n{listing}")
    for drift in registry_module.snapshot_errors(registry):
        log.warning(drift)

    files.append(File.generated(config, f"{PAGES_DIR}/index.md", content=index_page(registry)))
    for entry in registry["codes"]:
        files.append(
            File.generated(
                config,
                f"{PAGES_DIR}/{entry['code']}.md",
                content=code_page(registry, entry),
                inclusion=InclusionLevel.NOT_IN_NAV,
            )
        )
    return files


# --- rendering ------------------------------------------------------------------------


def front_matter(title: str, description: str) -> str:
    # A JSON string is a valid YAML double-quoted scalar.
    return f"---\ntitle: {json.dumps(title)}\ndescription: {json.dumps(description, ensure_ascii=False)}\n---\n\n"


def cell(text: str) -> str:
    """Text made safe for one cell of a Markdown table."""
    return text.replace("|", "\\|").replace("\n", " ")


def show_template(template: str) -> str:
    """A template as a page shows it: each placeholder as code, a doubled brace as one."""
    shown = re.sub(r"(?<!\{)\{([a-z][a-z0-9_]*)\}(?!\})", r"`{\1}`", template)
    return shown.replace("{{", "{").replace("}}", "}")


def param_type(param: dict) -> str:
    kind = param["type"]
    if kind == "list":
        return f"list of {param_type(param['items'])}"
    if kind == "enum":
        return "one of " + ", ".join(f"`{value}`" for value in param["values"])
    return f"`{kind}`"


def status_cell(entry: dict) -> str:
    if "status" in entry:
        return f"`{entry['status']}`"
    return f"none ({entry['raised_as']})"


def page_link(code: str) -> str:
    return f"[`{code}`]({code}.md)"


def index_page(registry: dict) -> str:
    entries = registry["codes"]
    lines = [
        front_matter(
            "Error Codes",
            "Every code of the MTHDS core error registry, with its title, domain, retry verdict and HTTP status, each linking to its page.",
        ),
        "# Error Codes\n",
        "Every code of the MTHDS core error registry has a page here, at the URL a problem's `type` names: "
        f"`{registry['base_url']}/<code>`. Each page says what its code means, who must act and what to do, "
        "and gives the code's steps, parameters and templates. "
        f"The [Error Registry]({SPEC_PAGE}) page describes the registry itself, and the "
        f"[HTTP Runner Protocol]({PROTOCOL_PAGE}#errors) how a problem document carries a code.\n",
        f"These pages are generated from the registry's data, which is published with every release of the standard as "
        f"[`mthds-error-registry.json`]({SNAPSHOT_LINK}). This is version `{registry['version']}` of the registry.\n",
        "## Extension prefixes\n",
        "A code that is not a core code starts with a registered prefix, and its page is published by the prefix's owner, "
        "under the base URL the prefix is registered with.\n",
        "| Prefix | Owner | Base URL |",
        "|---|---|---|",
    ]
    for prefix in registry["extension_prefixes"]:
        lines.append(f"| `{prefix['prefix']}.` | {cell(prefix['owner'])} | <{prefix['base_url']}> |")
    lines.append("")
    for family in registry["families"]:
        name = family["family"]
        members = [entry for entry in entries if registry_module.family_of(entry["code"]) == name]
        lines.append(f"## {name}\n")
        lines.append(f"{family['description']}\n")
        lines.append("| Code | Title | Domain | Retry | Status |")
        lines.append("|---|---|---|---|---|")
        for entry in members:
            lines.append(
                f"| {page_link(entry['code'])} | {cell(entry['title'])} | `{entry['domain']}` "
                f"| `{entry['retry']}` | {status_cell(entry)} |"
            )
        lines.append("")
    return "\n".join(lines)


def code_page(registry: dict, entry: dict) -> str:
    code = entry["code"]
    family = registry_module.family_of(code)
    family_description = next(item["description"] for item in registry["families"] if item["family"] == family)
    domain = entry["domain"]
    lines = [
        front_matter(code, f"{entry['title']}: what the MTHDS error code {code} means, who must act and what to do."),
        f"# {code}\n",
        f"**{entry['title']}**\n",
        "| | |",
        "|---|---|",
        f"| Type | `{registry_module.type_uri(registry, code)}` |",
        f"| Family | [`{family}`](index.md#{family}): {cell(family_description)} |",
        f"| [Domain]({PROTOCOL_PAGE}#domain-who-must-act) | `{domain}`: {DOMAIN_ACTORS[domain]} acts |",
        f"| [Retry]({PROTOCOL_PAGE}#retry) | `{entry['retry']}`: {RETRY_MEANINGS[entry['retry']]} |",
        f"| HTTP status | {status_cell(entry)} |",
        f"| Raised as | {RAISED_AS[entry['raised_as']]} |",
        "",
        "## What it means\n",
        f"{entry['meaning']}\n",
        "## What to do\n",
        f"{entry['what_to_do']}\n",
        "## Next steps\n",
        f"A problem carries the [step]({PROTOCOL_PAGE}#next-steps) aimed at whoever reads it: the first when its reader is "
        f"the domain's actor, {DOMAIN_ACTORS[domain]}, and the second for any other reader.\n",
        "| Reader | Kind | Detail |",
        "|---|---|---|",
        f"| The domain's actor | `{entry['steps']['actor']['kind']}` | {cell(show_template(entry['steps']['actor']['detail']))} |",
        f"| Any other reader | `{entry['steps']['other']['kind']}` | {cell(show_template(entry['steps']['other']['detail']))} |",
        "",
        "## Detail\n",
        "The problem's `detail` is written from this template, filled with the occurrence's parameters:\n",
        f"> {show_template(entry['detail'])}\n",
        "## Parameters\n",
    ]
    params = entry["params"]
    if not params:
        lines.append("This code declares no parameters, so its problems carry no `params`.\n")
    else:
        flagged = any(param.get("optional") or param.get("operator_only") for param in params.values())
        if flagged:
            lines.append(
                "A parameter is present on every occurrence of the code unless it is marked optional, and one "
                "marked operator-only reaches only whoever runs the runtime, never a caller.\n"
            )
        else:
            lines.append("Every parameter is present on every occurrence of the code.\n")
        lines.append("| Name | Type | Description |")
        lines.append("|---|---|---|")
        for name, param in params.items():
            marks = []
            if param.get("optional"):
                marks.append("optional")
            if param.get("operator_only"):
                marks.append("operator-only")
            mark = f" ({', '.join(marks)})" if marks else ""
            lines.append(f"| `{name}` | {param_type(param)}{mark} | {cell(param['description'])} |")
        lines.append("")
    lines.append("## See also\n")
    for reference in entry.get("see", []):
        lines.append(f"- [{reference['title']}](../{reference['href']})")
    lines.append(f"- [Error Registry]({SPEC_PAGE}), which describes the members of this page")
    lines.append("- [Error Codes](index.md), every code of the core registry")
    lines.append("")
    return "\n".join(lines)
