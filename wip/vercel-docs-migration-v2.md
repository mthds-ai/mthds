# Vercel Migration for mthds.ai Docs Site

## 1. Current Architecture

### Stack

MkDocs Material + mike versioning, deployed to GitHub Pages via the `gh-pages` branch.

### Deployment flow

```
Push to main (docs/**, mkdocs.yml, pyproject.toml)
  -> GitHub Actions (docs-deploy.yml)
  -> make docs-check (strict build)
  -> make docs-deploy-stable
    -> mike deploy --push --update-aliases --alias-type copy $VERSION latest
    -> mike set-default --push latest
    -> make docs-deploy-root (404.html, robots.txt, index.html, sitemap.xml, mthds_schema.json, llms.txt)
  -> gh-pages branch serves via GitHub Pages
```

### Version structure on gh-pages

```
gh-pages/
  latest/          <- copy-alias of current stable (e.g. 0.4.0)
  pre-release/     <- copy-alias of dev version
  0.4.0/           <- specific version
  0.3.7/           <- previous versions (older ones pruned)
  index.html       <- meta-refresh redirect to /latest/
  404.html         <- JS redirect logic (unversioned -> /latest/...)
  robots.txt       <- allows /latest/ only
  sitemap.xml      <- rewritten from latest/sitemap.xml
  mthds_schema.json
  llms.txt
  llms-full.txt
  versions.json    <- mike version registry
  CNAME            <- mthds.ai
```

### Source of truth for key settings

| Setting | Location | Value |
|---------|----------|-------|
| site_url | mkdocs.yml | `https://mthds.ai/` (bare domain) |
| canonical_version | mkdocs.yml (mike plugin) | `latest` |
| canonical URLs | docs/overrides/main.html | Hardcoded to `https://mthds.ai/latest/` |
| alias_type | mkdocs.yml (mike plugin) | `copy` |
| redirect_template | mkdocs.yml (mike plugin) | `docs/overrides/redirect.html` |
| version aliases | Makefile (docs-deploy-stable) | `latest`, `pre-release` |
| robots.txt | Makefile (ROOT_ROBOTS_TXT) | Inline heredoc |
| root index.html | Makefile (ROOT_INDEX_HTML) | Inline heredoc |
| sitemap | Makefile (docs-deploy-root) | sed rewrite of latest/sitemap.xml |
| domain | docs/CNAME | `mthds.ai` |

### Current redirect layers (all client-side)

1. **Root `index.html`** -- `<meta http-equiv="refresh" content="0;url=/latest/">` (meta-refresh)
2. **Root `404.html`** -- JS logic: unversioned paths -> `/latest/...`, invalid versions -> `/latest/404.html`
3. **mike `redirect.html`** -- JS `window.location.replace()` for version alias redirects

None of these are real HTTP redirects. Search engines see 200 status codes with JS/meta-refresh, not 301/308.

### Current SEO setup

- Canonical tags: hardcoded to `https://mthds.ai/latest/` on all pages (good)
- OG/Twitter/JSON-LD: all reference `/latest/` URLs (good)
- robots.txt: allows `/latest/` only, disallows `/0.*` and `/pre-release/` (good)
- sitemap.xml: root copy with URLs normalized to `/latest/` (good)
- 404 pages: `noindex, nofollow` on both (good)
- Redirect template: `noindex, follow` (good -- passes link equity)

---

## 2. Why Vercel

| Factor | GitHub Pages | Vercel |
|--------|-------------|--------|
| HTTP redirects | Not supported (JS/meta-refresh only) | Native 301/308 in `vercel.json` |
| Custom headers | Not supported | Full control via `vercel.json` |
| Trailing slash control | No control | Configurable |
| Root 404 behavior | Serves `404.html` with 200 status | Proper 404 status + custom page |
| X-Robots-Tag headers | Not possible | Supported |
| Cache-Control | No control | Full control |
| Deploy model | Branch-based (gh-pages) | Directory upload |

The core SEO problem -- needing real HTTP redirects -- is directly solved by Vercel. All three JS/meta-refresh redirect layers become proper 301s. The 404 soft-200 problem also disappears.

We already use Vercel for other projects, so infrastructure conventions are established.

---

## 3. Design Decision: Local mike build + Vercel deploy

### Architecture

Mike continues to manage versioned doc builds. But instead of pushing to gh-pages as the deployment mechanism, we:

1. Run mike locally in CI (commit to local gh-pages branch, no push to remote)
2. Extract the gh-pages branch content into a flat output directory
3. Generate root assets (robots.txt, sitemap, etc.) into that same directory
4. Deploy the directory to Vercel as a static site
5. Push gh-pages to remote as a historical record (not on the critical deployment path)

### Why local-only mike builds

Mike is designed around a branch-based publishing model: it accumulates versioned builds as commits on `gh-pages`. GitHub Pages serves directly from that branch. This model doesn't map to Vercel, which deploys directory snapshots.

If mike pushes to remote gh-pages *and then* CI checks out that branch to build the Vercel deployment, there's a race: the push modifies the remote ref while the checkout reads it. Keeping mike local-only eliminates this. The local gh-pages branch is the working state; the remote copy is a backup pushed after the Vercel deploy succeeds.

### Why keep mike at all

Mike handles version accumulation: each deploy adds a new version directory while preserving all previous ones. Without mike, we'd need a custom script to assemble multi-version output from scratch. Mike does this correctly and is already integrated.

The `alias_type: copy` setting means `/latest/` contains real files (not redirects), which is ideal for Vercel -- the canonical URL serves content directly with no redirect chain.

### Why not a catch-all redirect for unversioned paths

The current `404.html` has JS that redirects unversioned paths (e.g. `/language/bundles/`) to `/latest/language/bundles/`. It's tempting to replicate this with a Vercel catch-all redirect. However:

**Vercel evaluates redirects before checking the filesystem.** A catch-all like `/:path((?!latest|pre-release|0\\.).*) -> /latest/:path` would intercept root-level static files (`/robots.txt`, `/sitemap.xml`, `/llms.txt`, `/mthds_schema.json`, `/versions.json`), redirecting them to `/latest/robots.txt` etc. -- which either don't exist or are the wrong files.

Working around this requires negative lookaheads for every root file, creating a brittle rule that breaks whenever a new root file is added.

Instead: use explicit redirects only (`/` and `/index.html`). Unversioned deep links were never canonical (all public URLs use `/latest/` prefix), so they can 404 cleanly. If analytics later reveal specific unversioned URLs with significant traffic, add them as individual redirect rules.

### Trailing slash handling

MkDocs generates `page/index.html` files, expecting URLs with trailing slashes (`/page/`). Setting `trailingSlash: true` in Vercel normalizes this: `/latest/language/bundles` becomes `/latest/language/bundles/` via 308 redirect.

Vercel applies trailing slash normalization only to paths without file extensions. Root files like `/robots.txt` and `/sitemap.xml` are unaffected.

---

## 4. Proposed `vercel.json`

```json
{
  "$schema": "https://openapi.vercel.sh/vercel.json",
  "buildCommand": null,
  "outputDirectory": "site-output",
  "cleanUrls": false,
  "trailingSlash": true,

  "redirects": [
    {
      "source": "/",
      "destination": "/latest/",
      "statusCode": 301
    },
    {
      "source": "/index.html",
      "destination": "/latest/",
      "statusCode": 301
    }
  ],

  "headers": [
    {
      "source": "/latest/(.*)",
      "headers": [
        { "key": "X-Robots-Tag", "value": "index, follow" },
        { "key": "Cache-Control", "value": "public, max-age=3600, s-maxage=86400" }
      ]
    },
    {
      "source": "/pre-release/(.*)",
      "headers": [
        { "key": "X-Robots-Tag", "value": "noindex, nofollow" }
      ]
    },
    {
      "source": "/0.(.*)",
      "headers": [
        { "key": "X-Robots-Tag", "value": "noindex, follow" }
      ]
    },
    {
      "source": "/(.*)",
      "headers": [
        { "key": "X-Content-Type-Options", "value": "nosniff" },
        { "key": "X-Frame-Options", "value": "DENY" },
        { "key": "Referrer-Policy", "value": "strict-origin-when-cross-origin" }
      ]
    }
  ]
}
```

### Config rationale

| Setting | Value | Why |
|---------|-------|-----|
| `buildCommand` | `null` | We deploy pre-built static files; Vercel should not run any build |
| `outputDirectory` | `site-output` | The directory CI populates with the full static site |
| `cleanUrls` | `false` | MkDocs generates explicit `index.html` files; don't strip `.html` extensions |
| `trailingSlash` | `true` | MkDocs expects trailing slashes on directory URLs; normalizes `/page` -> `/page/` |

### Redirect rules

| Source | Destination | Code | Purpose |
|--------|-------------|------|---------|
| `/` | `/latest/` | 301 | Main entrypoint -- replaces meta-refresh `index.html` |
| `/index.html` | `/latest/` | 301 | Direct file access to root index |

Only two explicit redirects. No catch-all. Vercel's redirect evaluation runs before filesystem checks, so keeping the redirect set minimal avoids intercepting static files.

### Header rules

| Path pattern | Headers | Purpose |
|-------------|---------|---------|
| `/latest/(.*)` | `X-Robots-Tag: index, follow` + `Cache-Control` | Canonical docs: indexable, cached 1h client / 24h edge |
| `/pre-release/(.*)` | `X-Robots-Tag: noindex, nofollow` | Dev docs: fully hidden from search |
| `/0.(.*)` | `X-Robots-Tag: noindex, follow` | Archived versions: not indexed, but link equity flows |
| `/(.*)` | Security headers | Baseline security on all responses |

The `X-Robots-Tag` headers reinforce what robots.txt and canonical tags already do. Belt-and-suspenders: if any single signal is missed by a crawler, the others still prevent indexation of non-canonical content.

Note: Vercel header `source` patterns use path-to-regexp syntax where `.` is a literal dot (not a regex wildcard). `/0.(.*)` correctly matches paths starting with `/0.` (version directories like `/0.4.0/`).

### Directly served paths (no redirect needed)

| Path | Content |
|------|---------|
| `/latest/**` | Current stable docs (full MkDocs site) |
| `/pre-release/**` | Development docs |
| `/0.x.y/**` | Archived version docs |
| `/robots.txt` | Crawler directives |
| `/sitemap.xml` | URL index for search engines |
| `/mthds_schema.json` | JSON Schema asset |
| `/llms.txt`, `/llms-full.txt` | LLM-friendly content index |
| `/versions.json` | Mike version registry |
| `/404.html` | Custom 404 page (served with proper 404 status by Vercel) |

---

## 5. CI Workflow

### GitHub Actions: `docs-deploy.yml`

```yaml
name: Deploy Documentation

on:
  push:
    branches: [main]
    paths:
      - "docs/**"
      - "mkdocs.yml"
      - "pyproject.toml"
      - ".github/workflows/docs-deploy.yml"
      - "vercel.json"
  workflow_dispatch:

permissions:
  contents: write

env:
  VERCEL_ORG_ID: ${{ secrets.VERCEL_ORG_ID }}
  VERCEL_PROJECT_ID: ${{ secrets.VERCEL_PROJECT_ID }}

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0  # mike needs full history + gh-pages branch

      - uses: astral-sh/setup-uv@v5

      - uses: actions/setup-python@v5
        with:
          python-version: "3.13"

      - name: Install dependencies
        run: make install

      - name: Add venv to PATH
        run: echo "${{ github.workspace }}/.venv/bin" >> $GITHUB_PATH

      - name: Validate docs build
        run: make docs-check

      - name: Configure git
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"

      # Step 1: mike builds versioned docs into local gh-pages branch (no push)
      - name: Build versioned docs with mike
        run: make docs-build-versioned

      # Step 2: Extract gh-pages content + generate root assets into site-output/
      - name: Assemble site output
        run: make docs-assemble-site

      # Step 3: Deploy to Vercel
      - name: Install Vercel CLI
        run: npm install -g vercel

      - name: Deploy to Vercel
        run: vercel deploy --prod --token=${{ secrets.VERCEL_TOKEN }}

      # Step 4: Push gh-pages so the next CI run has all accumulated versions
      - name: Push gh-pages branch
        run: git push origin gh-pages

  github-release:
    needs: deploy
    runs-on: ubuntu-latest
    if: github.event_name == 'push'
    steps:
      # ... unchanged from current workflow
```

### Key design choices

**`fetch-depth: 0`** -- mike needs access to the `gh-pages` branch to read existing versions. Shallow clones break this.

**Separate build and assemble steps** -- `docs-build-versioned` runs mike (commits to local gh-pages). `docs-assemble-site` extracts that content and adds root assets. Separating them makes each step independently testable and the failure mode clear.

**Vercel deploy before gh-pages push** -- The Vercel deployment is the critical path. The gh-pages push happens after because its only purpose is persisting mike's version accumulation for the next CI run. If the Vercel deploy fails, we don't push (no state change). If it succeeds but gh-pages push fails, the site is live and the push can be retried.

**Three secrets required:**
- `VERCEL_ORG_ID` -- Vercel organization identifier
- `VERCEL_PROJECT_ID` -- Vercel project identifier
- `VERCEL_TOKEN` -- Vercel API token for CLI authentication

---

## 6. Makefile Changes

### New targets

```makefile
# Build versioned docs with mike (local only, no push)
docs-build-versioned: env
	$(call PRINT_TITLE,"Building versioned docs with mike")
	$(VENV_MIKE) deploy --update-aliases --alias-type copy $(DOCS_VERSION) latest
	$(VENV_MIKE) set-default latest

# Extract gh-pages content and assemble root assets into site-output/
docs-assemble-site:
	$(call PRINT_TITLE,"Assembling site output")
	rm -rf site-output
	git worktree add site-output gh-pages
	rm -rf site-output/.git
	# Root assets
	cp docs/404.html site-output/404.html
	cp docs/mthds_schema.json site-output/mthds_schema.json
	@echo '$(subst $(newline),\n,$(ROOT_ROBOTS_TXT))' > site-output/robots.txt
	@echo '$(subst $(newline),\n,$(ROOT_INDEX_HTML))' > site-output/index.html
	@if [ -f site-output/latest/sitemap.xml ]; then \
		sed 's|<loc>/|<loc>/latest/|g' site-output/latest/sitemap.xml > site-output/sitemap.xml; \
	fi
	@if [ -f site-output/latest/llms.txt ]; then \
		cp site-output/latest/llms.txt site-output/llms.txt; \
	fi
	@if [ -f site-output/latest/llms-full.txt ]; then \
		cp site-output/latest/llms-full.txt site-output/llms-full.txt; \
	fi
	# Remove CNAME -- Vercel manages domains via its dashboard
	rm -f site-output/CNAME
	@echo "Site output ready in site-output/"

# Full pipeline: build + assemble (for local testing)
docs-build-site: docs-build-versioned docs-assemble-site
	@echo "Complete site ready in site-output/. Run 'vercel dev' to preview locally."
```

### What changes in existing targets

| Target | Change |
|--------|--------|
| `docs-deploy-stable` | **Keep as-is** for any manual GitHub Pages deploy. Not used by CI. |
| `docs-deploy-root` | **Keep as-is** for the same reason. |
| `docs-build-versioned` | **New** -- mike without `--push` |
| `docs-assemble-site` | **New** -- extracts gh-pages + root assets into `site-output/` |
| `docs-build-site` | **New** -- combines the above two for local dev |

The existing targets remain for backward compatibility and as a fallback if we need to redeploy to GitHub Pages during the transition.

---

## 7. File Changes

| File | Change | Details |
|------|--------|---------|
| `vercel.json` | **Create** | Redirects, headers, deploy config (section 4) |
| `.github/workflows/docs-deploy.yml` | **Modify** | Replace GitHub Pages deploy with Vercel deploy (section 5) |
| `Makefile` | **Modify** | Add `docs-build-versioned`, `docs-assemble-site`, `docs-build-site` targets (section 6) |
| `docs/404.html` | **Simplify** | Remove JS redirect logic, keep as a pure styled 404 page (section 8) |
| `.gitignore` | **Modify** | Add `site-output/` and `.vercel/` |
| `docs/CNAME` | **Remove** | Vercel manages custom domains via its dashboard; a CNAME file in the output directory can confuse Vercel's domain resolution |

### Files that do NOT change

| File | Why it stays |
|------|-------------|
| `mkdocs.yml` | No MkDocs config changes needed. `site_url`, mike plugin settings, canonical_version all remain correct. |
| `docs/overrides/main.html` | Canonical tag logic (`https://mthds.ai/latest/`) is correct for Vercel. |
| `docs/overrides/redirect.html` | Mike's redirect template. With `alias_type: copy` these are rarely generated, but the template is correct if they are. |
| `docs/overrides/404.html` | MkDocs-built 404 for versioned paths. Correct and unaffected. |
| Root `index.html` (in Makefile) | Still generated into `site-output/` as a fallback. The `vercel.json` redirect takes precedence (`/` -> `/latest/` via 301). If the redirect somehow fails, the meta-refresh in index.html still works. |

---

## 8. Simplified 404.html

The current `docs/404.html` has JS that detects version prefixes and redirects unversioned paths to `/latest/`. With Vercel:

- The root redirect (`/` -> `/latest/`) is handled by `vercel.json`
- Unversioned deep links (e.g. `/language/bundles/`) return a proper 404 status -- which is correct, since these URLs were never canonical
- The version-detection JS becomes unnecessary

The simplified 404 keeps the styling and messaging but drops the JS redirect logic. Vercel serves it with a real HTTP 404 status code (not 200).

---

## 9. SEO Analysis

### Current state: mostly excellent

The existing SEO architecture is well done. Specific findings:

**Canonical tags** -- All pages have `<link rel="canonical" href="https://mthds.ai/latest/...">` hardcoded in `main.html`. This correctly points all versions to `/latest/`, preventing duplicate content.

**Duplicate content between aliases** -- `/latest/` and `/0.4.0/` contain identical files (copy mode), but canonical tags point to `/latest/`, robots.txt disallows `/0.*`, and the sitemap only contains `/latest/` URLs. Adding `X-Robots-Tag` headers via Vercel reinforces this.

**Sitemap** -- Root `sitemap.xml` is rewritten to only contain `/latest/` URLs. No version-specific URLs leak.

**robots.txt** -- Correctly allows only `/latest/`, `/sitemap.xml`, and LLM files. Blocks all versioned paths.

**404 pages** -- Both have `noindex, nofollow`. No indexable 404 content.

**Redirect template** -- Mike's `redirect.html` has `noindex, follow` -- passes link equity without being indexed.

### Issues that Vercel resolves

**No real HTTP redirects (critical)** -- All redirects are client-side (meta-refresh or JS). Search engines may index the redirect page itself (200 status), not pass full link equity through JS redirects, or show the wrong URL in results. Vercel redirects return proper 301 status codes.

**Root index.html served with 200 (moderate)** -- Google may index `mthds.ai/` as a separate page from `mthds.ai/latest/`. A 301 redirect is cleaner than relying solely on the canonical tag.

**404 pages return 200 (moderate)** -- GitHub Pages serves `404.html` with 200 status for missing paths. Google may report "soft 404" warnings in Search Console. Vercel serves custom 404 pages with proper 404 status.

**Trailing slash inconsistency (low)** -- GitHub Pages doesn't enforce trailing slashes: `/page` and `/page/` both work, creating potential duplicate URLs. `trailingSlash: true` normalizes this via 308 redirect.

### Version indexation policy

Index only `/latest/`. MTHDS is a young standard (v0.4.0) with no meaningful audience searching for old version docs. A single indexed version eliminates all duplicate content risk. When the standard matures (v1.0+), reconsider indexing the current major version alongside `/latest/`.

| Version | Indexed | Crawled | Canonical |
|---------|---------|---------|-----------|
| `/latest/` | Yes | Yes | Self |
| `/pre-release/` | No | No | N/A |
| `/0.x.y/` | No | Link-follow only | `/latest/` |

### Subdomain question

Keep docs on `mthds.ai` (apex domain). The site IS the docs -- there's no separate marketing site. A subdomain would split domain authority, change established URLs, and break inbound links.

---

## 10. Migration Plan

### Phase 1: Prepare (no user-visible changes)

1. Create a Vercel project for `mthds.ai` in the Vercel dashboard
2. Add secrets to the GitHub repo: `VERCEL_ORG_ID`, `VERCEL_PROJECT_ID`, `VERCEL_TOKEN`
3. Add `vercel.json` to the repo
4. Add Makefile targets (`docs-build-versioned`, `docs-assemble-site`, `docs-build-site`)
5. Add `site-output/` and `.vercel/` to `.gitignore`
6. Simplify `docs/404.html` (remove JS redirect logic)
7. Test locally: `make docs-build-site && vercel dev`

### Phase 2: Validate on preview domain

1. Deploy to Vercel preview (not production domain): `vercel deploy` (no `--prod`)
2. Verify on the preview URL (e.g. `mthds-xyz.vercel.app`):
   - All pages render correctly
   - `/` redirects to `/latest/` with 301 status
   - `/index.html` redirects to `/latest/` with 301 status
   - Missing pages return 404 status (not 200)
   - `X-Robots-Tag` headers are present and correct
   - `trailingSlash` works: `/latest/language/bundles` -> `/latest/language/bundles/`
   - Root files served: `/robots.txt`, `/sitemap.xml`, `/llms.txt`, `/mthds_schema.json`
   - Version selector works in the MkDocs UI
3. Run Lighthouse on the preview URL, save as pre-migration baseline

### Phase 3: DNS cutover

1. Lower DNS TTL to 60s (at least 24h before cutover)
2. In Vercel dashboard: add `mthds.ai` as a custom domain to the project
3. Update DNS records:
   - If apex domain: `A` record -> `76.76.21.21`
   - If using CNAME: `CNAME` -> `cname.vercel-dns.com`
4. Vercel auto-provisions TLS via Let's Encrypt
5. Update the GitHub Actions workflow to deploy to Vercel (merge the workflow changes)
6. Remove `docs/CNAME` from the repo

### Phase 4: Post-migration (1-2 weeks)

1. Monitor Google Search Console for crawl errors
2. Verify no soft 404 warnings
3. Check that `/latest/` pages are being indexed
4. Confirm old version pages are not indexed
5. Run Lighthouse again, compare with Phase 2 baseline
6. Restore DNS TTL to normal (3600s)
7. Disable GitHub Pages in repo settings (stop serving from `gh-pages`)
8. The `gh-pages` branch remains as mike's version accumulator -- each CI run fetches it, adds the new version locally, deploys to Vercel, then pushes the updated branch back. It is no longer a deployment target.

### Rollback plan

Rollback is Vercel-only. GitHub Pages is decommissioned after migration.

**Bad deployment (< 1 min):** Vercel maintains a history of every deployment. In the Vercel dashboard, any previous deployment can be promoted to production instantly. No DNS change, no CI run needed.

**Bad config (vercel.json regression):** Revert the commit in git, push to main, CI redeploys. Alternatively, promote a previous Vercel deployment while fixing the config.

---

## 11. Deployment Size and Limits

### Current estimate

Each version's docs output is approximately 15-25 MB (HTML, CSS, JS, images). With copy-mode aliases, `latest/` and the current version (e.g. `0.4.0/`) are duplicates. Current total with ~3-4 versions: approximately 60-100 MB.

### Vercel limits

- **Hobby plan:** 100 MB compressed upload size, 15,000 files per deployment
- **Pro plan:** 1 GB compressed, 15,000 files

The current site fits within Hobby limits. As versions accumulate, aggressive pruning of old versions becomes necessary. The existing workflow already prunes old versions in mike; this practice should continue.

### Mitigation

If deployment size approaches limits:

1. Prune old versions more aggressively (keep only latest + 1-2 previous)
2. Use `.vercelignore` to exclude unnecessary files from old versions
3. Upgrade to Vercel Pro if the project warrants it

---

## 12. Open Questions Answered

> Are docs deployed from a dedicated branch, artifact, or folder today?

**Dedicated branch.** Mike pushes to `gh-pages`, GitHub Pages serves from that branch.

> Is mike being used in a standard way or with custom scripts?

**Standard mike with customizations.** The core `mike deploy` / `mike set-default` usage is standard. The `docs-deploy-root` Makefile target that deploys root assets (404, robots, sitemap, etc.) via git worktree is custom and not part of mike itself.

> What are the actual public docs URLs today?

- `https://mthds.ai/` -> meta-refresh redirect to `/latest/`
- `https://mthds.ai/latest/` -> current stable docs
- `https://mthds.ai/latest/language/bundles/` -> example content page
- `https://mthds.ai/0.4.0/` -> specific version (same content as latest currently)
- `https://mthds.ai/pre-release/` -> development version (if deployed)

> Which URLs must continue to resolve for backward compatibility?

- `https://mthds.ai/latest/**` -- all current docs pages
- `https://mthds.ai/` -- root (redirect to latest)
- `https://mthds.ai/sitemap.xml`
- `https://mthds.ai/robots.txt`
- `https://mthds.ai/llms.txt`, `https://mthds.ai/llms-full.txt`
- `https://mthds.ai/mthds_schema.json`
- Versioned URLs (e.g. `https://mthds.ai/0.3.7/...`) -- continue to serve archived content

> Is the default version `latest`, `stable`, or something else?

**`latest`.** Set via `mike set-default latest`.

> Do we want search engines indexing only default/stable, all supported, or all except archived?

**Only `/latest/`.** This is already the setup and the correct strategy for a young standard.

> Are there existing SEO issues visible in the config?

Yes -- the critical one is no real HTTP redirects (all are JS/meta-refresh returning 200). Secondary: 404 pages return 200 status, trailing slash inconsistency. All resolved by the Vercel migration.

> Would we benefit from a dedicated docs subdomain?

**No.** The site IS the docs. A subdomain would split domain authority and break existing URLs.
