# Documentation Site Architecture

This file documents non-obvious architectural decisions for the docs site (`mthds.ai`). Read this before modifying anything under `docs/`.

## Site Architecture Overview

- MkDocs Material with `mike` versioning, published at `mthds.ai`
- `site_url` is `https://mthds.ai/` (bare domain) — mike adds the `/latest/` prefix to sitemap URLs without doubling
- Canonical URLs are hardcoded to `https://mthds.ai/latest/` in the `site_meta` block override in `main.html`
- Deployed to Vercel as pre-built static files (previously GitHub Pages)
- Custom domain `mthds.ai` configured in Vercel dashboard
- Theme overrides live in `docs/overrides/`

## The Two 404 Pages (critical — do not conflate)

There are two distinct 404 pages serving different purposes:

1. **`docs/404.html`** — Standalone root-level 404 page served by Vercel for all unmatched routes. Copied to `/404.html` in `site-output/` by `docs-assemble-site`. Has its own styling (grayscale palette, dark mode via `prefers-color-scheme`). **NOT** part of the MkDocs build. Vercel serves it with a proper HTTP 404 status code.

2. **`docs/overrides/404.html`** — MkDocs Material template override. Controls the versioned `site/404.html` rendered by MkDocs. Extends `main.html`. Must include both SEO tags (`noindex`, canonical) AND visible user-facing content (heading + link back to `/latest/`).

There must be **NO** `docs/404.md` — a Markdown 404 would be treated as content, appear in the sitemap, and create an indexable `/latest/404/` URL.

## SEO Architecture

- **`docs/overrides/main.html`** — Overrides the `site_meta` block to hardcode canonical URLs to `https://mthds.ai/latest/` (since `site_url` is the bare domain). Also owns OG tags (`og:type`, `og:site_name`, `og:locale`), Twitter cards, and JSON-LD for all pages. Uses `canonical_latest` variable for all URL references. Conditionally emits `og:type=website` + WebSite JSON-LD on the homepage, and `og:type=article` + TechArticle JSON-LD on all other pages. Organization JSON-LD appears on every page. Also loads Vercel Web Analytics in the `extrahead` block, which `overrides/404.html`'s empty `extrahead` suppresses on the 404 page; it stores nothing in the browser and needs no consent. PostHog is not here: it sits behind the consent banner, described under "Analytics and Cookie Consent". Vercel Web Analytics requires Web Analytics to be enabled in the Vercel project dashboard — the `/_vercel/insights/script.js` route is served by Vercel's edge only then.
- **`docs/overrides/404.html`** — Extends `main.html`, adds `noindex/nofollow` + canonical back to `/latest/`. Must also render visible content.
- **`docs/.meta.yml`** — Default frontmatter for all pages via `meta-manager` plugin (description, keywords).
- Per-page `description` frontmatter in individual `.md` files overrides the default.

## Analytics and Cookie Consent

PostHog stores an identifier in the browser, so it starts only after the visitor accepts analytics in Material's consent banner. Everything is Material's own mechanism; there is no consent plugin and no banner of our own.

- **`extra.consent` in `mkdocs.yml`** renders the banner, with accept, reject and manage actions and two purposes: `analytics` (labelled PostHog) and `github`, which Material adds because `repo_url` is on GitHub and which gates its fetch of the repository's star and fork counts. The choice is stored in `localStorage` under `__consent`, and every choice reloads the page.
- **`extra.analytics.provider: posthog`** makes Material include `docs/overrides/partials/integrations/analytics/posthog.html` in every page's head and call the `__md_analytics()` it defines only when the stored choice has `analytics: true`. Without consent, PostHog's code is never fetched. Session recording is disabled in `posthog.init`, since the privacy policy describes page-view analytics only.
- **The same partial clears PostHog's leftovers** on every page load without analytics consent: the `ph_<key>_posthog` cookie on the host and each parent domain, and every `localStorage` and `sessionStorage` key starting with `ph_<key>_` or `ph_debug`. That covers a withdrawal, since the page reloads after it, and visitors from before the banner existed. The names match what pipelex.com clears.
- **The same partial keeps the banner from presenting a purpose as already chosen.** Material ticks every box of the "Manage settings" panel until a choice is stored, and "Accept" stores whatever is ticked. The partial unticks the boxes on a first visit, and a capture-phase `submit` listener on the document ticks them all when "Accept" is pressed with the panel closed, so that "Accept" means accept all, after an earlier rejection too. Both depend on the names in Material's `partials/consent.html` (the form `consent`, the toggle `__settings`), so a Material upgrade that renames them breaks this silently: check the banner by hand after one.
- **`extra.scope: /`** makes one choice cover every version. Material prefixes its `localStorage` keys with the version's base URL by default, which would ask a visitor again on each version; the palette and the selected content tabs share the site-wide key too.
- **The footer** (`copyright` in `mkdocs.yml`) links the privacy policy on pipelex.com, which covers mthds.ai, and `#__consent`, which reopens the banner.
- **`docs/stylesheets/general.css` restyles the banner's buttons**, because Material colours them with `--md-primary-fg-color`, which this palette makes the header's near-white, so the outlined "Manage settings" would be invisible. Accept and Reject are filled alike, so that refusing is as easy as accepting.
- **`docs/overrides/404.html`** replaces Material's `analytics` block with the partial alone, without Material's caller, so the banner behaves the same on the 404 page but PostHog never starts there.

## `site_url` Is the Bare Domain

`site_url` is set to `https://mthds.ai/` (bare domain, no `/latest/`). This prevents double-path bugs in the sitemap: MkDocs generates URLs relative to `site_url`, then mike adds the version prefix. If `site_url` included `/latest/`, mike would create `/latest/latest/page/` URLs.

Canonical URLs are hardcoded to include `/latest/` via the `site_meta` block override in `main.html`, so they point to real pages. OG URLs and JSON-LD also use the hardcoded `canonical_latest` variable.

## robots.txt and sitemap.xml

- **`Makefile` `ROOT_ROBOTS_TXT`** — The authoritative robots.txt assembled into `site-output/` by `docs-assemble-site`. Allows `/latest/`, `/sitemap.xml` and the two `llms` files, and disallows every retained version's numbered directory, `/pre-release/` and `/404.html` by name. The current version's directory is a duplicate of `/latest/`; the older retained ones are superseded standards that nobody should reach from a search result. It carries no blanket `Disallow: /`, so a directory is only excluded if it is listed — and robots.txt has no numeric wildcard, so the exclusion is written per major release line (`/0.`, `/2.`). Every line the retention keeps needs a `Disallow` here **and** a matching `noindex, follow` header block in `vercel.json`; miss either and that version ships as an indexable duplicate of `/latest/`. `make docs-retention` prints the lines that must be covered, and a line the retention no longer keeps has both its entries removed in the same commit. Points `Sitemap:` to the root `https://mthds.ai/sitemap.xml`.
- **Root `sitemap.xml`** — Generated by `docs-assemble-site` from `latest/sitemap.xml` via sed rewrite to ensure all URLs use `/latest/` paths. This root copy is what Google crawls (the versioned copy inside `/latest/` is not rewritten by mike).
- There is no `docs/robots.txt` inside the versioned site. If one is added, note that crawlers would ignore it (RFC 9309: only domain-root robots.txt is authoritative).

## Mike Redirect Template

**`docs/overrides/redirect.html`** — Custom template used by the `mike` plugin for version alias redirects. Contains full OG/Twitter metadata and `noindex, follow` so redirects pass link equity without being indexed. Referenced in `mkdocs.yml` via `redirect_template: docs/overrides/redirect.html`.

## Deployment

Deployed to Vercel as pre-built static files. The build pipeline:

1. `make docs-prune` — retires the versions the site no longer serves from the local `gh-pages` branch, and removes any directory `versions.json` no longer names (no push)
2. `make docs-build-versioned` — mike builds versioned docs into local `gh-pages` branch (no push)
3. `make docs-assemble-site` — extracts `gh-pages` content via temp worktree into `site-output/`, adds root assets (`404.html`, `robots.txt`, `sitemap.xml`, `mthds_schema.json`, `llms.txt`, `llms-full.txt`), and drops mike's root `index.html` and the `CNAME`, since Vercel owns the root redirect and the domain
4. `vercel deploy --prod` — deploys `site-output/` to Vercel
5. `git push origin gh-pages` — pushes the pruned branch for the next CI run

The `gh-pages` branch is mike's version store (not a deployment target). Each CI run fetches it, prunes it down to what the site still serves, adds the version being deployed, deploys to Vercel, then pushes back.

**The site serves the current standard, the release before it, and whatever is pinned, never anything below the floor.** The current version appears under its own number and under the `latest` alias mike copies from it. The first two are derived and nobody maintains them: `scripts/docs_retention.py` reads the version from `pyproject.toml` and ranks the published set by semver, so each release retires its predecessor's predecessor on its own. A pin is the editorial exception — `[tool.mthds.docs] retain` in `pyproject.toml` names an older version, at or above the floor, that the site keeps answering for however many releases have passed since. An empty pin list is a correct state, and a pin naming a version that is no longer published is reported rather than ignored. `[tool.mthds.docs] floor` names the oldest version the site serves and overrides the rest: every published version below it is retired, the release before the current one included, and a pin below it stops the deploy. It stands at `6.0.0`, the first version built with the cookie consent banner, because every version before it starts PostHog without asking; a version being deployed below the floor is kept with a note, which is how `dev` answers until the release lifts the version past it. `make docs-retention` prints what the next deploy would keep and retire, reading the published set from `origin/gh-pages` without creating a local branch or touching the working tree.

A retired version stops resolving the moment `vercel deploy --prod` promotes the new production deployment, which is the step before the `gh-pages` push and does not depend on it. **Retiring is not reversible from the site**: `gh-pages` is a store rather than what is served, so republishing a retired version means checking its tag out, assembling the site and deploying it to Vercel by hand — and the next run of the workflow retires it again unless it has been pinned first. That is why the `/release` skill puts the question before the release rather than after it. The deployment path refuses rather than guesses: it will not prune on a version number it cannot read, nor on a pin list it cannot parse, and it fails the deploy rather than pass for a quiet no-op if mike cannot list the branch.

Because the push is the last step, a deploy whose push fails leaves production pruned and the store unpruned — and what is lost is the version that was just deployed, which never reached the store at all. The versions that run retired are not republished: pruning is the first step of every run, so the next one retires them again before the site is assembled. But a later release reads a store that has never seen the version whose push failed, takes an older release as "the release published before it", and the site silently skips a standard. That is why a failed push is worth re-running, and it is worth re-running before the next release rather than after it.

**`docs/mthds_schema.json` is what `mthds.ai/mthds_schema.json` serves**, copied to the site root by `docs-assemble-site`. It is the schema generated by a `pipelex` release, copied in by the workspace's `mthds-schema-sync` skill; nothing in this repository fetches it, so a refresh is a reviewed change to the committed file like any other. Because the standard is usually cut before the `pipelex` release implementing it, the copy can lag the standard being published, and `make schema-lag` lists the documentation's examples it rejects. That list shows a copy stricter than the standard and never a standard stricter than the copy, since every example obeys a tightened rule too, so the `/release` skill reads the release's own changes beside it and carries what both readings find into the release's changelog entry and pull request rather than waiting for the sync, and `docs/tooling/json-schema.md` tells readers that the hosted schema can lag.

Redirects (`/` and `/index.html` to `/latest/`) and `X-Robots-Tag` headers are configured in `vercel.json`.

## Search Configuration

The search plugin uses `separator: '[\s\-\.]+'` to properly tokenize hyphenated and dotted identifiers like `mthds-agent`, `METHODS.toml`, `domain.Name`.

## MkDocs Plugins

- `mike` — versioning with copy-based aliases
- `search` — site search with custom separator for dotted/hyphenated terms
- `privacy` — downloads external assets locally (GDPR) and adds `target: _blank` to external links
- `meta-manager` — applies `docs/.meta.yml` defaults to all pages
- `glightbox` — image lightbox
- `llmstxt-md` — generates `llms.txt` for LLM-friendly content
- `neoteroi.mkdocsoad` — renders OpenAPI documents into pages via `OAD` include tags (the protocol page's route reference; the `info` partial is suppressed via `docs/templates/oad/` so the rendered output has no duplicate H1)

## Common Mistakes to Avoid

- Do NOT create `docs/404.md` — it poisons the sitemap with an indexable `/latest/404/` URL
- Do NOT delete `docs/overrides/404.html` — it controls the versioned 404 page
- Do NOT put 404-specific SEO tags in `main.html` — that's `overrides/404.html`'s job
- Do NOT change `site_url` to include `/latest/` — mike would create double-path URLs like `/latest/latest/page/` in the sitemap
- When adding pages, update BOTH the `nav:` section AND the `llmstxt-md` plugin `sections:` in `mkdocs.yml`
