# Documentation Site Architecture

This file documents non-obvious architectural decisions for the docs site (`mthds.ai`). Read this before modifying anything under `docs/`.

## Site Architecture Overview

- MkDocs Material with `mike` versioning, published at `mthds.ai`
- `site_url` is `https://mthds.ai/latest/` — all canonical URLs and sitemap entries include `/latest/`
- Custom domain via `docs/CNAME` (value: `mthds.ai`)
- Theme overrides live in `docs/overrides/`

## The Two 404 Pages (critical — do not conflate)

There are two distinct 404 pages serving different purposes:

1. **`docs/404.html`** — Standalone root-level fallback for GitHub Pages. Copied to `/404.html` on `gh-pages` by `docs-deploy-root`. Contains JS redirect logic (unversioned URLs → `/latest/...`). Has its own styling (grayscale palette, dark mode via `prefers-color-scheme`). **NOT** part of the MkDocs build.

2. **`docs/overrides/404.html`** — MkDocs Material template override. Controls the versioned `site/404.html` rendered by MkDocs. Extends `main.html`. Must include both SEO tags (`noindex`, canonical) AND visible user-facing content (heading + link back to `/latest/`).

There must be **NO** `docs/404.md` — a Markdown 404 would be treated as content, appear in the sitemap, and create an indexable `/latest/404/` URL.

## SEO Architecture

- **`docs/overrides/main.html`** — Owns OG tags (`og:type`, `og:site_name`, `og:locale`), Twitter cards, and JSON-LD for all pages. Uses null-safe `page.meta` access. Conditionally emits `og:type=website` + WebSite JSON-LD on the homepage, and `og:type=article` + TechArticle JSON-LD on all other pages. Organization JSON-LD appears on every page. Also contains the PostHog analytics snippet.
- **`docs/overrides/404.html`** — Extends `main.html`, adds `noindex/nofollow` + canonical back to `/latest/`. Must also render visible content.
- **`docs/.meta.yml`** — Default frontmatter for all pages via `meta-manager` plugin (description, keywords).
- Per-page `description` frontmatter in individual `.md` files overrides the default.

## `site_url` Must Include `/latest/`

With mike versioning, actual pages live at `mthds.ai/latest/...`. Setting `site_url: https://mthds.ai/latest/` ensures the sitemap, canonical URLs, and OG URLs all point to real pages instead of URLs that 404 and redirect.

## robots.txt: Two Files, Different Purposes

- **`Makefile` `ROOT_ROBOTS_TXT`** — The authoritative robots.txt deployed to domain root by `docs-deploy-root`. Allows only `/latest/`, disallows everything else, points sitemap to `/latest/sitemap.xml`.
- There is no `docs/robots.txt` inside the versioned site. If one is added, note that crawlers would ignore it (RFC 9309: only domain-root robots.txt is authoritative).

## Mike Redirect Template

**`docs/overrides/redirect.html`** — Custom template used by the `mike` plugin for version alias redirects. Contains full OG/Twitter metadata and `noindex, follow` so redirects pass link equity without being indexed. Referenced in `mkdocs.yml` via `redirect_template: docs/overrides/redirect.html`.

## Deployment (`docs-deploy-root`)

The `docs-deploy-root` Makefile target deploys root assets (`404.html`, `robots.txt`, `index.html`, `mthds_schema.json`) directly to the `gh-pages` branch via a temporary git worktree.

- Called automatically after `docs-deploy-stable` and `docs-deploy-specific-version`
- The root `index.html` is a meta-refresh redirect to `/latest/`

## Search Configuration

The search plugin uses `separator: '[\s\-\.]+'` to properly tokenize hyphenated and dotted identifiers like `mthds-agent`, `METHODS.toml`, `domain.Name`.

## MkDocs Plugins

- `mike` — versioning with copy-based aliases
- `search` — site search with custom separator for dotted/hyphenated terms
- `privacy` — downloads external assets locally (GDPR) and adds `target: _blank` to external links
- `meta-manager` — applies `docs/.meta.yml` defaults to all pages
- `glightbox` — image lightbox
- `llmstxt-md` — generates `llms.txt` for LLM-friendly content

## Common Mistakes to Avoid

- Do NOT create `docs/404.md` — it poisons the sitemap with an indexable `/latest/404/` URL
- Do NOT delete `docs/overrides/404.html` — it controls the versioned 404 page
- Do NOT put 404-specific SEO tags in `main.html` — that's `overrides/404.html`'s job
- Do NOT change `site_url` to omit `/latest/` — the sitemap would point to URLs that 404
- When adding pages, update BOTH the `nav:` section AND the `llmstxt-md` plugin `sections:` in `mkdocs.yml`
