---
status: draft
item: L-260829-eddd6e
---

# Version gate — deferred follow-ups

Deferrals from the round-1 review of PR #63 (*spec: write the MTHDS versioning rule and cut the standard at 2.0.0*), which introduced `scripts/check_versions.py` and wired it into `make docs-check`, `changelog-check` and `version-check`. Both items below were confirmed against the code and deliberately not fixed in that PR; the reasoning is recorded here so a later session does not re-derive it.

## `changelog-check` accepts preparation mode on a pull request to `main`

Reported by the local Codex reviewer against `.github/workflows/changelog-check.yml:34-35`.

`check_versions.py` treats two states as legal: *preparing* (a `## [Unreleased]` heading announcing the next cut, with `pyproject.toml` still at the previous release) and *released*. On a pull request to `main` that still carries `[Unreleased]`, the check passes in preparation mode without ever comparing `pyproject.toml` against the standard version the documentation states. The current tree is exactly that shape — project version `0.10.0`, standard `2.0.0` — and `changelog-check`'s own grep passes too, because it looks for a heading matching `pyproject.toml`'s version and `v0.10.0` is present. Were such a merge to land, `docs-deploy` would publish documents stating standard `2.0.0` under the mike version directory `/0.10.0/`, since `DOCS_VERSION` comes from `pyproject.toml` (`Makefile:19`).

Deferred because the path is foreclosed by process rather than by code, and closing it costs more than the residual risk:

- `main` is only advanced by `release/vX.Y.Z` pull requests; a `dev → main` merge is not a sanctioned flow in this repo.
- `version-check.yml` deliberately skips any source branch that is not a release branch — that guard was added by this same PR.
- On a genuine release pull request the existing `changelog-check` grep already fails when `[Unreleased]` was not converted, because no `## [vX.Y.Z] -` heading matches the bumped `pyproject.toml`.

The remedy would be a released-only mode on `check_versions.py` (a flag that rejects preparation state) wired into the gates that run on `main`. Worth doing if a non-release merge to `main` ever becomes a real workflow, or if the release cut moves out of the `/release` skill.

## The readings registry is maintained by hand

Reported by the local cubic reviewer against `scripts/check_versions.py:38`.

`STANDARD_READINGS` and `PROTOCOL_READINGS` validate only the sites registered in them, so a new page that states either version escapes the gate entirely unless its author also adds a reading. The guarantee the check advertises — every written copy of a number agrees — therefore rests on the same discipline whose failure produced the `1.0.0` that sat still for six months.

Deferred because this is the design as documented, not an oversight. `CLAUDE.md` carries the rule (*"Never restate the number in a new page without adding a reading to `scripts/check_versions.py`"*), and `.claude/skills/release/SKILL.md` names the two tables as the authority on which files state a version. The obvious automatic alternative — scanning the tree for anything semver-shaped and demanding it be registered — is unworkable here: `docs/` is full of unrelated `1.0.0` literals in constraint-syntax tables, dependency examples and package-version samples, so such a scan is mostly noise.

The open question is whether a narrower check earns its keep: for instance, flagging only the phrases that state *this* standard's version ("the current MTHDS standard version is", "is at version") wherever they appear outside the registry. Revisit with a concrete pattern in hand, not before.
