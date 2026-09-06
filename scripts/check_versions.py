#!/usr/bin/env python3
"""Check that the MTHDS standard and protocol versions agree everywhere they are written.

The standard version and the release version of this specification are one number
(docs/spec/versioning.md), so every place that states either must state the same one.
The protocol version moves on its own cadence, but it too is written in several files
and they must not disagree — a "v0.1" sitting beside a "0.6.0" example is what this
check exists to catch.

Two states are legal:

* A release is being prepared. CHANGELOG.md carries `## [Unreleased]` announcing the
  version it will cut; the version in pyproject.toml is still the previous release and
  is not compared against the standard version.
* No release is being prepared. The topmost changelog heading, pyproject.toml, and the
  versioning page all state the same standard version.

Run with `make version-check`; `make docs-check` runs it first.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

VERSIONING_PAGE = "docs/spec/versioning.md"
PROTOCOL_PAGE = "docs/spec/protocol.md"
OPENAPI_DOC = "docs/spec/openapi/mthds-protocol.openapi.yaml"
CHANGELOG = "CHANGELOG.md"
PYPROJECT = "pyproject.toml"
CLAUDE_MD = "CLAUDE.md"

SEMVER = r"\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.\-]+)?"

# Each reading is (label, file, compiled pattern with one capture group).
STANDARD_READINGS = [
    (
        "the versioning page's version table",
        VERSIONING_PAGE,
        rf"\|\s*\*\*Standard version\*\*\s*\|.*?\|\s*`({SEMVER})`\s*\|",
    ),
    (
        "the manifest specification's current-version statement",
        "docs/spec/manifest-format.md",
        rf"The current MTHDS standard version is `({SEMVER})`",
    ),
    (
        "the manifest guide's field table",
        "docs/packages/manifest.md",
        rf"MTHDS standard version constraint\. The current standard version is `({SEMVER})`",
    ),
    (
        "the roadmap",
        "docs/about/roadmap.md",
        rf"The MTHDS standard is at version `({SEMVER})`",
    ),
    (
        "the agent guide's MTHDS_STANDARD_VERSION constant",
        CLAUDE_MD,
        rf'`MTHDS_STANDARD_VERSION` = `"({SEMVER})"`',
    ),
    # The `mthds_version` constraint in each example manifest. A reader who follows the
    # documentation copies these verbatim, so they must name the standard the guide was
    # written against — which means they move with every cut, like any other reading.
    (
        "the manifest specification's example manifest",
        "docs/spec/manifest-format.md",
        rf'^mthds_version = ">=({SEMVER})"',
    ),
    (
        "the manifest guide's example manifest",
        "docs/packages/manifest.md",
        rf'^mthds_version = ">=({SEMVER})"',
    ),
    (
        "the package-creation guide's example manifest",
        "docs/guides/create-package.md",
        rf'^mthds_version = ">=({SEMVER})"',
    ),
]

# Deliberately NOT readings: the versions `docs/spec/native-concepts.md` and
# `docs/spec/intent-hints.md` pin their sets at. Each is the standard version in which that
# set last changed, so it lags the current standard version by design and comparing the two
# would be wrong. See docs/spec/versioning.md, "The Pinned Native Set Under One Number".
PROTOCOL_READINGS = [
    (
        "the versioning page's version table",
        VERSIONING_PAGE,
        rf"\|\s*\*\*Protocol version\*\*\s*\|.*?\|\s*`({SEMVER})`\s*\|",
    ),
    (
        "the OpenAPI document's info.version",
        OPENAPI_DOC,
        rf"^info:\n(?:.*\n)*?  version:\s*({SEMVER})\s*$",
    ),
    (
        "the /version response example",
        PROTOCOL_PAGE,
        rf'"protocol_version":\s*"({SEMVER})"',
    ),
    (
        "the agent guide's PROTOCOL_VERSION constant",
        CLAUDE_MD,
        rf'`PROTOCOL_VERSION` = `"({SEMVER})"`',
    ),
]


def read(rel: str) -> str:
    path = ROOT / rel
    if not path.is_file():
        fail(f"{rel} does not exist")
        return ""
    return path.read_text(encoding="utf-8")


errors: list[str] = []


def fail(message: str) -> None:
    errors.append(message)


def extract(label: str, rel: str, pattern: str) -> str | None:
    match = re.search(pattern, read(rel), re.MULTILINE)
    if match is None:
        fail(f"{rel}: could not read a version from {label} (pattern: {pattern})")
        return None
    return match.group(1)


def agree(kind: str, readings: list[tuple[str, str, str]]) -> str | None:
    """Every reading of one number must give the same value."""
    found = {}
    for label, rel, pattern in readings:
        value = extract(label, rel, pattern)
        if value is not None:
            found.setdefault(value, []).append(f"{rel} ({label})")
    if not found:
        return None
    if len(found) > 1:
        lines = [f"The {kind} version does not agree across the documentation:"]
        for value, sites in sorted(found.items()):
            for site in sites:
                lines.append(f"    {value:<12} {site}")
        fail("\n".join(lines))
        return None
    return next(iter(found))


def check_conformance_statement(protocol_version: str) -> None:
    """`protocol.md` states conformance as a MAJOR.MINOR line, not a full semver."""
    major_minor = ".".join(protocol_version.split(".")[:2])
    text = read(PROTOCOL_PAGE)
    match = re.search(r"implements MTHDS Protocol v(\d+\.\d+)", text)
    if match is None:
        fail(f"{PROTOCOL_PAGE}: no 'implements MTHDS Protocol vX.Y' conformance statement found")
    elif match.group(1) != major_minor:
        fail(
            f"{PROTOCOL_PAGE}: the conformance statement says 'implements MTHDS Protocol "
            f"v{match.group(1)}' but the protocol version is {protocol_version} "
            f"(expected v{major_minor})"
        )


def main() -> int:
    standard = agree("standard", STANDARD_READINGS)
    protocol = agree("protocol", PROTOCOL_READINGS)

    if protocol is not None:
        check_conformance_statement(protocol)

    changelog = read(CHANGELOG)
    release_version = extract("the project version", PYPROJECT, rf'^version = "({SEMVER})"')

    unreleased = re.search(
        rf"^## \[Unreleased\]\s*\n\s*\n\*\*Next release: v({SEMVER}) · MTHDS standard "
        rf"({SEMVER}) · MTHDS Protocol ({SEMVER})\*\*",
        changelog,
        re.MULTILINE,
    )
    released = re.search(
        rf"^## \[v({SEMVER})\] - \d{{4}}-\d{{2}}-\d{{2}}\s*\n\s*\n\*\*MTHDS standard "
        rf"({SEMVER}) · MTHDS Protocol ({SEMVER})\*\*",
        changelog,
        re.MULTILINE,
    )

    if re.search(r"^## \[Unreleased\]", changelog, re.MULTILINE) and unreleased is None:
        fail(
            f"{CHANGELOG}: the [Unreleased] heading must be followed by a blank line and "
            f"'**Next release: vX.Y.Z · MTHDS standard X.Y.Z · MTHDS Protocol A.B.C**' "
            f"(see {VERSIONING_PAGE}, 'The Changelog Contract')"
        )

    if unreleased is not None:
        next_version, next_standard, next_protocol = unreleased.groups()
        if next_version != next_standard:
            fail(
                f"{CHANGELOG}: [Unreleased] announces release v{next_version} carrying "
                f"standard {next_standard}; the standard version is the release version, "
                f"so they must be the same number"
            )
        if standard is not None and next_standard != standard:
            fail(
                f"{CHANGELOG}: [Unreleased] announces standard {next_standard}, but the "
                f"documentation states {standard}"
            )
        if protocol is not None and next_protocol != protocol:
            fail(
                f"{CHANGELOG}: [Unreleased] announces protocol {next_protocol}, but the "
                f"documentation states {protocol}"
            )
    elif released is not None:
        heading_version, heading_standard, heading_protocol = released.groups()
        topmost = re.search(r"^## \[", changelog, re.MULTILINE)
        if topmost is not None and topmost.start() != released.start():
            fail(
                f"{CHANGELOG}: the topmost heading is not the one carrying "
                f"'**MTHDS standard X.Y.Z · MTHDS Protocol A.B.C**' — v{heading_version} "
                f"was read instead. Every heading from v2.0.0 onward names the versions it "
                f"carries (see {VERSIONING_PAGE}, 'The Changelog Contract')"
            )
        if heading_version != heading_standard:
            fail(
                f"{CHANGELOG}: heading v{heading_version} carries standard {heading_standard}; "
                f"the standard version is the release version, so they must be the same number"
            )
        if release_version is not None and release_version != heading_version:
            fail(
                f"{PYPROJECT} is at {release_version} but the top changelog heading is "
                f"v{heading_version}"
            )
        if standard is not None and heading_standard != standard:
            fail(
                f"{CHANGELOG}: the released heading carries standard {heading_standard}, but "
                f"the documentation states {standard}"
            )
        if protocol is not None and heading_protocol != protocol:
            fail(
                f"{CHANGELOG}: the released heading carries protocol {heading_protocol}, but "
                f"the documentation states {protocol}"
            )
    else:
        fail(
            f"{CHANGELOG}: no [Unreleased] section and no released heading carrying "
            f"'**MTHDS standard X.Y.Z · MTHDS Protocol A.B.C**' — every heading from v2.0.0 "
            f"onward names the versions it carries (see {VERSIONING_PAGE})"
        )

    if errors:
        print("Version consistency check FAILED:\n", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        print("", file=sys.stderr)
        return 1

    state = "preparing" if unreleased is not None else "released"
    print(f"MTHDS standard {standard} · MTHDS Protocol {protocol} — consistent ({state})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
