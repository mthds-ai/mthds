#!/usr/bin/env python3
"""Decide which published documentation versions the specification site keeps.

Three things are retained, and only three:

* the version being deployed, which is what `/latest/` is copied from;
* the release published before it, so the standard the world was reading yesterday
  does not stop resolving the day a new one lands;
* every version named in `[tool.mthds.docs] retain` in pyproject.toml.

The first two are derived and need no maintenance. A pin is an editorial decision that
mthds.ai still answers for an older standard — taken at release time, written down, and
reviewed like any other change. An empty pin list is a correct state, and a pin naming a
version that is no longer published is reported rather than quietly ignored.

A pin is satisfied by anything the site can still serve — a version the index names, or a
directory that outlived the index, which is the only way left to hold on to one. A pin that
answers to nothing stops the deploy rather than warning, because it is a typo about to
retire what it was written to protect; so does an index that names nothing beside a branch
that still carries versions, and so does a deploy of a version older than one already
published, which would retire the current standard and repoint `/latest/` at the older one.

Reads mike's `list --json` — or the `versions.json` it writes, which has the same shape — on
stdin, and takes the branch's top-level directories with `--directories`, so that it decides
the sweep as well as the retirement and the two cannot disagree. Prints the versions to
retire, one per line, or with `--orphans` the directories to remove. `--explain` prints the
whole plan for a person instead. No mode changes anything.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import NoReturn, cast

ROOT = Path(__file__).resolve().parent.parent

# The one definition of a version number in the deployment path. The prune script reads no
# version number itself — it hands this script the directories it found and is told which
# to remove — so there is no second copy here to drift from this one.
VERSION_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)(?:-([0-9A-Za-z.-]+))?(?:\+[0-9A-Za-z.-]+)?$")


def order(version: str) -> tuple[int, int, int, int, str] | None:
    """Sort key placing a prerelease below the release it leads to, or None if unreadable."""
    match = VERSION_RE.match(version)
    if not match:
        return None
    major, minor, patch, prerelease = match.groups()
    return (int(major), int(minor), int(patch), 0 if prerelease else 1, prerelease or "")


def rank(version: str) -> tuple[int, int, int, int, str]:
    """`order` for sorting a set already known to be readable."""
    return order(version) or (0, 0, 0, 0, "")


def die(message: str) -> NoReturn:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def dig(value: object, *keys: str) -> object:
    """Walk nested tables, returning None the moment the path stops existing."""
    for key in keys:
        if not isinstance(value, dict):
            return None
        value = cast("dict[str, object]", value).get(key)
    return value


def read_pins(pyproject: Path) -> list[str]:
    """Read `[tool.mthds.docs] retain` from pyproject.toml."""
    try:
        text = pyproject.read_text(encoding="utf-8")
    except OSError as exc:
        die(f"cannot read {pyproject}: {exc}")

    try:
        import tomllib
    except ModuleNotFoundError:
        return _pins_without_tomllib(text, pyproject)

    try:
        data = tomllib.loads(text)
    except Exception as exc:  # Any parse failure at all is a reason not to prune.
        die(f"cannot parse {pyproject}: {exc}")
    pins = dig(data, "tool", "mthds", "docs", "retain")
    if pins is None:
        return []
    if not isinstance(pins, list) or not all(isinstance(pin, str) for pin in cast("list[object]", pins)):
        die(f"`[tool.mthds.docs] retain` in {pyproject} must be a list of version strings")
    return cast("list[str]", pins)


def _pins_without_tomllib(text: str, source: Path) -> list[str]:
    """Read the pin list on a Python too old for tomllib, which arrived in 3.11.

    Deliberately narrow: it understands the one table and the one array this project
    writes and refuses anything else rather than guess. Refusing is safe, because the
    caller treats a failure here as a reason not to prune at all, while guessing wrong
    would silently delete a version somebody decided to keep.
    """
    table = re.search(r"^\[tool\.mthds\.docs\]\s*$(.*?)(?=^\[|\Z)", text, re.M | re.S)
    if not table:
        return []
    array = re.search(r"^\s*retain\s*=\s*\[(.*?)\]", table.group(1), re.M | re.S)
    if not array:
        return []
    items = re.sub(r"#[^\n]*", "", array.group(1))
    if re.sub(r'"[^"]*"', "", items).strip(" ,\n\t\r"):
        die(
            f"cannot read `retain` in {source} on Python {sys.version_info.major}."
            f"{sys.version_info.minor}; write it as a list of double-quoted version "
            f"strings, or run this on Python 3.11 or newer"
        )
    return re.findall(r'"([^"]*)"', items)


def read_published() -> list[str]:
    raw = sys.stdin.read().strip()
    if not raw:
        return []
    try:
        entries: object = json.loads(raw)
    except json.JSONDecodeError as exc:
        die(f"the version listing on stdin is not JSON: {exc}")
    if not isinstance(entries, list):
        die("the version listing on stdin is not a JSON list")
    published: list[str] = []
    for entry in cast("list[object]", entries):
        version = dig(entry, "version")
        if not isinstance(version, str):
            die("the version listing on stdin has an entry with no `version` string")
        published.append(version)
    return published


def plan(
    deploying: str,
    published: list[str],
    pins: list[str],
    directories: list[str],
) -> tuple[dict[str, str], list[str], list[str], list[str]]:
    """Return what is kept and why, what is retired, what is swept, and the notes."""
    notes: list[str] = []

    # Only version-shaped directories are ever candidates for the sweep. Every directory on
    # the branch is mike's, so in principle anything the index does not name is stale — but
    # this deletes from the published site unattended, and a directory arriving by some
    # route nobody has thought of yet should survive to be looked at rather than vanish.
    version_dirs = [name for name in directories if order(name)]

    # An index that names nothing, beside a branch that still carries versions, is a store
    # this script cannot read. Sweeping on it would delete every version the site serves and
    # report success — the silent shape this whole path exists to refuse — so stop instead.
    if not published and version_dirs:
        die(
            "the version index names nothing, yet the branch carries "
            f"{', '.join(sorted(version_dirs, key=rank, reverse=True))} — refusing to prune "
            "a store that cannot be read"
        )

    # Deploying something older than what is already published would retire the current
    # standard, and the step after this one repoints /latest/ at the older version. Neither
    # is recoverable from the site, so hand it back rather than guess which was meant.
    newer = sorted((v for v in published if order(v) and rank(v) > rank(deploying)), key=rank, reverse=True)
    if newer:
        die(
            f"{', '.join(newer)} is published and newer than {deploying} — refusing to prune, "
            "because this deploy would retire the current standard and repoint /latest/ at an "
            "older one"
        )

    keep: dict[str, str] = {deploying: "the version being deployed"}

    # Newest first by semver, so 0.10.0 outranks 0.9.0 the way a string sort would not.
    older = sorted((v for v in published if v != deploying and order(v)), key=rank, reverse=True)
    if older:
        keep.setdefault(older[0], "the release published before it")

    # A pin is satisfied by anything the site can still serve: a version the index names, or
    # a directory that outlived the index, which is the only way left to hold on to one.
    for pin in pins:
        if pin == deploying:
            notes.append(f"{pin} is pinned and is also the version being deployed — the pin adds nothing.")
            keep.setdefault(pin, "pinned in pyproject.toml")
        elif pin in published:
            keep.setdefault(pin, "pinned in pyproject.toml")
        elif pin in version_dirs:
            notes.append(
                f"{pin} is pinned and is served, but versions.json does not name it, so the "
                "version selector does not offer it."
            )
            keep.setdefault(pin, "pinned in pyproject.toml")
        elif published or version_dirs:
            # A pin is the one safeguard against an irreversible retirement, so a pin that
            # answers to nothing is a typo about to retire what it was written to protect.
            die(
                f"{pin} is pinned in pyproject.toml, but nothing published and nothing on the "
                "branch answers to it — refusing to prune on a pin that protects nothing"
            )
        else:
            notes.append(f"{pin} is pinned, but nothing is published yet — the pin applies once something is.")

    # A published name that cannot be read is not ours to delete unattended.
    for version in published:
        if order(version) is None:
            keep.setdefault(version, "kept because its name is not a version number")
            notes.append(f"{version} is published under a name that is not a version number, and is kept.")

    retired = sorted((v for v in published if v not in keep), key=rank, reverse=True)
    orphans = sorted((d for d in version_dirs if d not in keep and d not in published), key=rank, reverse=True)
    return keep, retired, orphans, notes


def crawl_lines(kept: list[str]) -> list[str]:
    """The release lines the crawl policy has to name, one entry per major."""
    majors = {version.split(".")[0] for version in kept if order(version)}
    return [f"/{major}." for major in sorted(majors, key=int)]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("deploying", help="the version being deployed")
    parser.add_argument("--explain", action="store_true", help="print the plan for a person, not a list")
    parser.add_argument("--directories", default="", help="the branch's top-level directories, whitespace separated")
    parser.add_argument("--orphans", action="store_true", help="print the directories to sweep, not the versions to retire")
    parser.add_argument("--pyproject", type=Path, default=ROOT / "pyproject.toml")
    args = parser.parse_args()

    if order(args.deploying) is None:
        die(f"refusing to prune — '{args.deploying}' is not a version number")

    keep, retired, orphans, notes = plan(
        args.deploying,
        read_published(),
        read_pins(args.pyproject),
        args.directories.split(),
    )

    if not args.explain:
        for note in notes:
            print(f"note: {note}", file=sys.stderr)
        print("\n".join(orphans if args.orphans else retired))
        return

    print(f"Documentation retention for {args.deploying}\n")
    print("Kept:")
    for version in sorted(keep, key=rank, reverse=True):
        print(f"  {version:<10} {keep[version]}")
    print()
    if retired:
        print("Retired by the next deploy:")
        print(f"  {' '.join(retired)}\n")
    else:
        print("Retired by the next deploy:\n  nothing — every published version is retained.\n")
    if orphans:
        print("Also removed, because versions.json does not name them — the site serves these")
        print("today, and the version selector does not offer them:")
        print(f"  {' '.join(orphans)}\n")
    if retired or orphans:
        print("Retiring is not reversible from the site: republishing one of those means")
        print("checking its tag out, assembling the site and deploying it by hand. A version")
        print("to keep goes in `[tool.mthds.docs] retain` in pyproject.toml.\n")
    for note in notes:
        print(f"note: {note}")
    if notes:
        print()
    print("Crawl policy must name these release lines — a `Disallow:` in the Makefile's")
    print("ROOT_ROBOTS_TXT and a matching `noindex, follow` block in vercel.json:")
    print(f"  {'  '.join(crawl_lines(list(keep)))}")


if __name__ == "__main__":
    main()
