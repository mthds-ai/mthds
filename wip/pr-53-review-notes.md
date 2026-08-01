# PR #53 review notes — deferred items

Deferred findings from the review-agent triage of [PR #53](https://github.com/mthds-ai/mthds/pull/53) (`chore/pipelex-0.41.0-sweep`). Everything else surfaced in that pass was fixed in the PR itself.

## `make update-schema` silently downgrades the committed schema

**Where:** `Makefile:14` (`SCHEMA_URL`) and `Makefile:272-277` (`update-schema`, alias `up`).

**Reporter:** none — found while verifying the changelog rationale of PR #53.

**The issue.** The target unconditionally overwrites the committed schema with whatever the S3 object currently holds:

```make
SCHEMA_URL := https://pipelex-config.s3.amazonaws.com/mthds_schema_latest.json

update-schema:
	curl -fSL "$(SCHEMA_URL)" -o "$(CURDIR)/docs/mthds_schema.json"
```

That object was verified on 2026-07-30 to still serve `Generated from PipelexBundleBlueprint v0.27.0`. The committed copy is now at v0.41.0. So running `make update-schema` (or `make up`) today **reverts the schema by fourteen minor releases**, silently undoing PR #53 — including the `datetime` and `time` field types that a `.mthds` author can legitimately declare. The regression would show up only as an editor/validation false negative, which is exactly the failure mode PR #53 set out to close.

The root cause is structural, not a typo: the S3 object has **no automated producer**. Per the `mthds-schema-sync` skill, publishing it is a manual, outward-facing step, so the "latest" object drifts behind the released pipelex whenever nobody runs it. A refresh target that trusts that object without checking is a footgun for anyone who reasonably assumes `update-schema` moves forward.

**Why deferred.** Two reasons, both judgment calls that a PR-review pass shouldn't settle unilaterally:

1. The real remedy is to **republish `mthds_schema_latest.json` from `pipelex/derived/mthds_schema.json`** — an outward-facing action ("latest released" for *every* consumer, including `vscode-pipelex` via `mthds.ai`) that needs an explicit decision and AWS credentials. It is out of scope for a docs PR.
2. Whether the target should additionally carry a **defensive guard** is a design question — it changes the contract of a command people may deliberately use to roll backward.

**Recommendation.** Do the S3 republish first (that alone removes today's hazard). Then consider a guard in the target: fetch to a temp file, parse the `$comment` version out of both it and the committed copy, and refuse to write when the fetched version is older — with an explicit `--force`-style escape hatch for a deliberate rollback. Per the workspace convention, that logic belongs in `scripts/update-schema.sh` invoked by the Make target, not inline in Makefile syntax.

**Open question for the owner:** should `update-schema` be version-guarded, or should the repo instead drop the S3 hop entirely and copy from a pinned released `pipelex` (which is what PR #53 did by hand, and what the `mthds-schema-sync` skill prescribes when the released chain is stale)?
