---
name: release
description: Prepare a new release for the MTHDS project. Bumps version in pyproject.toml, updates CHANGELOG.md, manages the release/vX.Y.Z branch, validates docs build, and commits. Use when the user says "release", "prepare a release", "bump version", "new version", or "cut a release".
---

# Release Workflow

Guides the user through preparing a new MTHDS release in 7 interactive steps. Every step requires explicit user confirmation before proceeding.

## Step 1 — Gather State

Read the following and present a summary:

1. Current version from `pyproject.toml` (`version = "X.Y.Z"`)
2. Latest entry in `CHANGELOG.md`
3. Current git branch (`git branch --show-current`)
4. Working tree status (`git status --short`)

If the working tree is dirty, **warn the user** and ask whether to continue or abort.

## Step 2 — Determine Target Version

Calculate the three semver bump options from the current version:

- **Patch**: `X.Y.Z+1`
- **Minor**: `X.Y+1.0`
- **Major**: `X+1.0.0`

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

## Step 5 — Update CHANGELOG.md

The changelog entry **must** match the CI grep pattern: `## [vX.Y.Z] -`

Check if `CHANGELOG.md` already contains a `## [v{TARGET_VERSION}] -` entry.

- **If missing**: run `git log main..HEAD --oneline` (or `git log --oneline -20` if on `main`) to review recent commits. Draft a changelog entry from those commits and propose it to the user for approval. Insert the approved entry at the top of the changelog (after the `# Changelog` heading) formatted as:

```markdown
## [v{TARGET_VERSION}] - {TODAY'S DATE in YYYY-MM-DD}

- Item one
- Item two
```

The user may accept, edit, or rewrite the proposed entry.

- **If exists**: show the existing entry and ask the user whether to keep it or edit it.

## Step 6 — Validate Docs Build

Run:

```bash
make docs-check
```

- **On success**: report and continue.
- **On failure**: show the errors and ask the user how to proceed (fix issues, skip validation, or abort).

## Step 7 — Review & Commit

Present a full summary:

- Target version: `v{TARGET_VERSION}`
- Branch: `release/v{TARGET_VERSION}`
- Files changed: `pyproject.toml`, `CHANGELOG.md`
- Changelog entry preview

Ask the user to confirm. On confirmation:

1. Stage **only** `pyproject.toml` and `CHANGELOG.md` — never use `git add .` or `git add -A`.
2. Commit with message: `Bump version to {TARGET_VERSION} and update changelog`
3. Show the commit result.

Then offer (but do not automatically execute):

- **Push** the branch to origin (`git push -u origin release/v{TARGET_VERSION}`)
- **Create a PR** to `main` using `gh pr create`

Wait for explicit user approval before pushing or creating a PR.

## Rules

- Never use `git add .` or `git add -A` — only stage `pyproject.toml` and `CHANGELOG.md`.
- Never push or create PRs without explicit user approval.
- The `v` prefix appears in branch names and changelog headers, but **not** in `pyproject.toml`.
- Always use today's date for new changelog entries (format: `YYYY-MM-DD`).
- If any step fails or the user wants to abort, stop immediately — do not continue the workflow.
