---
name: release
description: Prepare a new release for the MTHDS project. Bumps version in pyproject.toml, syncs uv.lock, updates CHANGELOG.md, manages the release/vX.Y.Z branch, validates docs build, and commits. Use when the user says "release", "prepare a release", "bump version", "new version", or "cut a release".
---

# Release Workflow

Guides the user through preparing a new MTHDS release in 8 interactive steps. Every step requires explicit user confirmation before proceeding.

## Step 1 — Gather State

Read the following and present a summary:

1. Current version from `pyproject.toml` (`version = "X.Y.Z"`)
2. Latest entry in `CHANGELOG.md`
3. Current git branch (`git branch --show-current`)
4. Working tree status (`git status --short`)

If the working tree is dirty, **warn the user** and ask whether to continue or abort.

## Step 2 — Determine Target Version

**First, read the `## [Unreleased]` section of `CHANGELOG.md`.** If it carries a `**Next release: vX.Y.Z · …**` line, that version is already decided — the release version *is* the MTHDS standard version (see `docs/spec/versioning.md`), and the accumulated entries were written against it. Propose it as the default and only offer the calculated alternatives if the user wants to override.

Otherwise, calculate the three semver bump options from the current version:

- **Patch**: `X.Y.Z+1` — nothing normative changed (a clarification, a corrected example, a new guide).
- **Minor**: `X.Y+1.0` — an additive change to the standard (a new native concept, a new pipe type, a new optional key).
- **Major**: `X+1.0.0` — a breaking change to the standard.

Present these options to the user using `AskUserQuestion`. If the current branch already looks like `release/vA.B.C` and the version in `pyproject.toml` was already bumped, offer a **"Keep current (A.B.C)"** option.

Store the chosen version as `TARGET_VERSION` (no `v` prefix, e.g. `0.0.4`).

## Step 3 — Branch Management

The release branch **must** be named `release/v{TARGET_VERSION}` (CI regex: `^release/v[0-9]+\.[0-9]+\.[0-9]+$`).

- If already on the correct branch: inform the user and continue.
- If on `main` or another branch: confirm with the user, then create and switch to `release/v{TARGET_VERSION}`.
- If on a *different* release branch: warn the user and ask how to proceed.

## Step 4 — Update Version in pyproject.toml

Edit the `version = "..."` line in `pyproject.toml` to `version = "{TARGET_VERSION}"`.

- If the version already matches: inform the user and skip.
- Otherwise: use the Edit tool to make the change, then show the diff.

The version in pyproject.toml must **not** have a `v` prefix (e.g. `0.0.4`, not `v0.0.4`).

## Step 5 — Sync uv.lock

After updating `pyproject.toml`, regenerate the lock file so it reflects `TARGET_VERSION`:

```bash
uv lock
```

Verify the output confirms the version was updated (e.g. `Updated mthds vX.Y.Z -> v{TARGET_VERSION}`).

- **If the lock file was already in sync**: inform the user and continue.
- **On failure**: show the error and ask the user how to proceed.

## Step 6 — Update CHANGELOG.md

The changelog entry **must** match the CI grep pattern: `## [vX.Y.Z] -`

Every released heading carries the two versions it ships, on the line below it — this is the contract in `docs/spec/versioning.md`, and `scripts/check_versions.py` enforces it:

```markdown
## [v{TARGET_VERSION}] - {TODAY'S DATE in YYYY-MM-DD}

**MTHDS standard {TARGET_VERSION} · MTHDS Protocol {PROTOCOL_VERSION}**
```

The standard version always equals `{TARGET_VERSION}`. Read `{PROTOCOL_VERSION}` from the versioning page's version table — it moves on its own cadence and usually does not change.

- **If `## [Unreleased]` exists**: this is the normal case. Convert it in place — replace the `## [Unreleased]` heading with `## [v{TARGET_VERSION}] - {TODAY'S DATE}`, and replace its `**Next release: …**` line with the `**MTHDS standard … · MTHDS Protocol …**` line above. Keep the accumulated entries; show them to the user and ask whether to keep, edit, or rewrite.
- **If `## [v{TARGET_VERSION}] -` already exists**: show the existing entry and ask the user whether to keep it or edit it. Add the version line if it is missing.
- **If neither exists**: run `git log main..HEAD --oneline` (or `git log --oneline -20` if on `main`) to review recent commits. Draft an entry from those commits, in the format above, and propose it to the user for approval.

Do **not** retrofit version lines onto headings published before `v2.0.0`.

## Step 7 — Validate Docs Build

Run:

```bash
make docs-check
```

This runs `make version-check` first, which fails if the standard version stated across the documentation, the version in `pyproject.toml`, and the version the changelog heading carries do not all agree. A failure here means a page still names the previous standard version — fix the page, do not skip the check.

- **On success**: report and continue.
- **On failure**: show the errors and ask the user how to proceed (fix issues, skip validation, or abort).

## Step 8 — Review & Commit

Present a full summary:

- Target version: `v{TARGET_VERSION}`
- Branch: `release/v{TARGET_VERSION}`
- Files changed: `pyproject.toml`, `uv.lock`, `CHANGELOG.md`
- Changelog entry preview

Ask the user to confirm. On confirmation:

1. Stage **only** `pyproject.toml`, `uv.lock`, and `CHANGELOG.md` — never use `git add .` or `git add -A`.
2. Commit with message: `Bump version to {TARGET_VERSION} and update changelog`
3. Show the commit result.

Then offer (but do not automatically execute):

- **Push** the branch to origin (`git push -u origin release/v{TARGET_VERSION}`)
- **Create a PR** to `main` using `gh pr create`

Wait for explicit user approval before pushing or creating a PR.

## Rules

- Never use `git add .` or `git add -A` — only stage `pyproject.toml`, `uv.lock`, and `CHANGELOG.md`.
- Never push or create PRs without explicit user approval.
- The `v` prefix appears in branch names and changelog headers, but **not** in `pyproject.toml`.
- Always use today's date for new changelog entries (format: `YYYY-MM-DD`).
- If any step fails or the user wants to abort, stop immediately — do not continue the workflow.
