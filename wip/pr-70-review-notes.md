# PR #70 review notes — deferred items

Deferred findings from the `/rev` round-1 triage of [PR #70](https://github.com/mthds-ai/mthds/pull/70) (`feature/Docs-site-past-vercel`), at bar `open`. Everything else that pass confirmed was fixed in the PR itself.

## The orphan sweep dies if `gh-pages` is already checked out somewhere

**Where:** `scripts/docs-prune.sh`, the sweep's `git worktree add --quiet "$SWEEP" "$BRANCH"`.

**Reporter:** `code-review` (level `low`).

**The issue.** The sweep removes directories `versions.json` does not name by adding a temporary worktree on the branch and committing a `git rm` there. `git worktree add` refuses a branch that is already checked out — in another worktree, or as the current `HEAD` — with `fatal: '<branch>' is already checked out`. The prune then exits non-zero under `set -e`, after `mike delete` has already rewritten the index and removed directories on the local branch.

**Why deferred.** The failure is loud and it fails closed. The prune is the first step of the deploy job, so a non-zero exit there stops the job before `docs-assemble-site`, before `vercel deploy --prod` and before `git push origin gh-pages`: production is untouched, the store on `origin` is untouched, and the only casualty is a local branch state that the CI runner discards. Nothing ships in a half-pruned state, which is the property that matters.

Reaching it also takes an unusual local state. CI checks out `main` and never checks `gh-pages` out; mike operates on the branch through the index without a worktree. `docs-assemble-site` does take a worktree on `gh-pages`, but it runs after the prune and removes it on an `EXIT` trap. So the reachable case is a developer whose earlier `make docs-assemble-site` was interrupted hard enough to leave the worktree behind, or who has `gh-pages` checked out by hand — and in both, git's own message names the problem precisely.

**What a fix would look like**, if this ever bites someone: check `git worktree list` for the branch before adding, and either reuse that worktree or fail with a message naming `git worktree prune` rather than letting git's own error surface mid-prune. Note that `docs-assemble-site` has carried the same pattern since the Vercel migration, so a fix belongs to both or neither.

## Not deferred, recorded here because the reasoning outlives the pull request

cubic raised the absence of a changelog entry (P3), flagging itself that `CHANGELOG.md` is outside this diff. The substance is real — the deploy stops serving `/0.4.0/` through `/0.9.0/`, and inbound links to them break — but an `## [Unreleased]` entry here would have to announce a standard version, and `scripts/check_versions.py` requires that version to agree with every documentation reading. Opening one would mean restamping the standard across the docs for a change that is normatively inert, which claims a specification release this pull request is not making.

The durable fix went into `.claude/skills/release/SKILL.md` instead: the release entry names what that release stops serving, at the moment a release is actually being cut and the version is moving anyway.
