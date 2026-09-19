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

Reads mike's `list --json` — or the `versions.json` it writes, which has the same shape —
on stdin, and prints the versions to retire, one per line. `--explain` prints the whole
plan for a person instead. Neither mode changes anything.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import NoReturn, cast

ROOT = Path(__file__).resolve().parent.parent

# The one definition of a version number in the deployment path: the prune script defers
# to it rather than carrying a second copy that could drift from this one.
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


def plan(deploying: str, published: list[str], pins: list[str]) -> tuple[dict[str, str], list[str], list[str]]:
    """Return what is kept and why, what is retired, and the notes worth printing."""
    notes: list[str] = []
    keep: dict[str, str] = {deploying: "the version being deployed"}

    # Newest first by semver, so 0.10.0 outranks 0.9.0 the way a string sort would not.
    ranked = sorted(
        (version for version in published if version != deploying and order(version)),
        key=rank,
        reverse=True,
    )
    if ranked:
        keep.setdefault(ranked[0], "the release published before it")

    for pin in pins:
        if pin == deploying:
            notes.append(f"{pin} is pinned and is also the version being deployed — the pin adds nothing.")
        elif pin not in published:
            notes.append(f"{pin} is pinned but is not published — nothing to retain under that number.")
        keep.setdefault(pin, "pinned in pyproject.toml")

    # A directory whose name cannot be read is not ours to delete unattended.
    for version in published:
        if order(version) is None:
            keep.setdefault(version, "kept because its name is not a version number")
            notes.append(f"{version} is published under a name that is not a version number, and is kept.")

    retired = sorted((version for version in published if version not in keep), key=rank, reverse=True)
    return keep, retired, notes


def crawl_lines(kept: list[str]) -> list[str]:
    """The release lines the crawl policy has to name, one entry per major."""
    majors = {version.split(".")[0] for version in kept if order(version)}
    return [f"/{major}." for major in sorted(majors, key=int)]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("deploying", help="the version being deployed")
    parser.add_argument("--explain", action="store_true", help="print the plan for a person, not the retire list")
    parser.add_argument("--pyproject", type=Path, default=ROOT / "pyproject.toml")
    args = parser.parse_args()

    if order(args.deploying) is None:
        die(f"refusing to prune — '{args.deploying}' is not a version number")

    keep, retired, notes = plan(args.deploying, read_published(), read_pins(args.pyproject))

    if not args.explain:
        for note in notes:
            print(f"note: {note}", file=sys.stderr)
        print("\n".join(retired))
        return

    print(f"Documentation retention for {args.deploying}\n")
    print("Kept:")
    for version in sorted(keep, key=rank, reverse=True):
        print(f"  {version:<10} {keep[version]}")
    print()
    if retired:
        print("Retired by the next deploy:")
        print(f"  {' '.join(retired)}\n")
        print("Retiring is not reversible from the site: republishing one of those means")
        print("checking its tag out, assembling the site and deploying it by hand.\n")
    else:
        print("Retired by the next deploy:\n  nothing — every published version is retained.\n")
    for note in notes:
        print(f"note: {note}")
    if notes:
        print()
    print("Crawl policy must name these release lines — a `Disallow:` in the Makefile's")
    print("ROOT_ROBOTS_TXT and a matching `noindex, follow` block in vercel.json:")
    print(f"  {'  '.join(crawl_lines(list(keep)))}")


if __name__ == "__main__":
    main()
