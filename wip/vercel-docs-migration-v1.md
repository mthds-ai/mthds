# Vercel Migration for mthds.ai Docs Site

## 1. Current Architecture Summary

### Stack
MkDocs Material + mike versioning, deployed to GitHub Pages via `gh-pages` branch.

### Deployment flow
```
Push to main (docs/**, mkdocs.yml, pyproject.toml)
  → GitHub Actions (docs-deploy.yml)
  → make docs-check (strict build)
  → make docs-deploy-stable
    → mike deploy --push --update-aliases --alias-type copy $VERSION latest
    → mike set-default --push latest
    → make docs-deploy-root (404.html, robots.txt, index.html, sitemap.xml, mthds_schema.json, llms.txt)
  → gh-pages branch serves via GitHub Pages
```

### Version structure on gh-pages
```
gh-pages/
├── latest/          ← copy-alias of current stable (e.g. 0.4.0)
├── pre-release/     ← copy-alias of dev version
├── 0.4.0/           ← specific version
├── 0.3.7/           ← previous versions (older ones pruned)
├── index.html       ← meta-refresh redirect to /latest/
├── 404.html         ← JS redirect logic (unversioned → /latest/…)
├── robots.txt       ← allows /latest/ only
├── sitemap.xml      ← rewritten from latest/sitemap.xml
├── mthds_schema.json
├── llms.txt
├── llms-full.txt
├── versions.json    ← mike version registry
└── CNAME            ← mthds.ai
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

1. **Root `index.html`** — `<meta http-equiv="refresh" content="0;url=/latest/">` (meta-refresh)
2. **Root `404.html`** — JS logic: unversioned paths → `/latest/…`, invalid versions → `/latest/404.html`
3. **mike `redirect.html`** — JS `window.location.replace()` for version alias redirects (e.g. when `latest` resolves to `0.4.0`)

None of these are real HTTP redirects. Search engines see 200 status codes with JS/meta-refresh, not 301/308.

### SEO setup

- Canonical tags: hardcoded to `https://mthds.ai/latest/` on all pages (good)
- OG/Twitter/JSON-LD: all reference `/latest/` URLs (good)
- robots.txt: allows `/latest/` only, disallows `/0.*` and `/pre-release/` (good)
- sitemap.xml: root copy with URLs normalized to `/latest/` (good)
- 404 pages: `noindex, nofollow` on both (good)
- Redirect template: `noindex, follow` (good — passes link equity)

---

## 2. Recommendation: Vercel Is a Good Fit

**Yes, migrating to Vercel is recommended.**

### Why

| Factor | GitHub Pages | Vercel |
|--------|-------------|--------|
| HTTP redirects | Not supported (JS/meta-refresh only) | Native 301/308 in `vercel.json` |
| Custom headers | Not supported | Full control via `vercel.json` |
| Trailing slash control | No control | Configurable |
| Root 404 behavior | Serves `404.html` with 200 status | Proper 404 status + custom page |
| X-Robots-Tag headers | Not possible | Supported |
| Cache-Control | No control | Full control |
| Edge routing | None | Rewrites, redirects, headers |
| Deploy model | Branch-based (gh-pages) | Build output / directory upload |

The core SEO problem — needing real HTTP redirects — is directly solved by Vercel. All three JS/meta-refresh redirect layers become proper 301s.

### Mike compatibility assessment

Mike's `gh-pages` branch model does not map directly to Vercel. Mike is designed to accumulate versioned builds on a single long-lived branch. Vercel deploys a directory snapshot per deployment.

**Solution:** Keep mike for building versioned output, but change the deploy step:
1. Mike builds into `gh-pages` branch (or a local directory)
2. CI checks out the `gh-pages` content into a flat directory
3. That directory is deployed to Vercel as a static site
4. `vercel.json` handles all redirects server-side

This preserves the entire existing mike workflow while gaining Vercel's routing capabilities.

### What about mike's alias redirects?

Mike generates `redirect.html` files for version aliases when `alias_type: redirect` is used. But this repo uses `alias_type: copy`, which physically copies all files — no redirects needed for alias resolution. The `redirect.html` template is only used when mike itself creates redirect pages (e.g. if someone navigates to `/latest/` and mike redirects to `/0.4.0/`). With `copy` mode, `/latest/` contains the actual files, so this is not an issue.

The one edge case: mike's version selector dropdown may link to the canonical version number (e.g. `/0.4.0/`) instead of `/latest/`. With Vercel, we could optionally add a rewrite so `/0.4.0/` serves the same content as `/latest/` without a redirect, or leave it as-is (both directories contain the same files due to copy mode).

---

## 3. Deployment Design Options

### Option A — Minimal Migration (Recommended)

Keep MkDocs + mike exactly as-is. Build static output in CI. Deploy the `gh-pages` content to Vercel. Add redirects in `vercel.json`.

**Implementation:**
1. Add `vercel.json` to the repo
2. New/modified GitHub Actions workflow:
   - Keep mike building to `gh-pages` branch (or build locally)
   - Check out `gh-pages` content into a directory
   - Deploy that directory to Vercel via `vercel deploy --prod`
3. Remove CNAME file (Vercel manages domains via its dashboard)
4. Simplify root 404.html and root index.html (JS redirect logic replaced by vercel.json)
5. Update DNS to point `mthds.ai` at Vercel

**Effort:** Low-medium (1-2 days)
**SEO quality:** Excellent — real 301 redirects, proper X-Robots-Tag headers, correct 404 status codes
**Maintainability:** High — `vercel.json` is declarative and version-controlled
**Operational risk:** Low — can run both in parallel during transition
**Workflow disruption:** Minimal — mike workflow unchanged, only deploy target changes

### Option B — Adjusted mike workflow

Keep MkDocs, change how mike artifacts are assembled. Instead of mike pushing to `gh-pages`, have mike build all versions into a local output directory, then deploy that.

**Implementation:**
1. Use `mike deploy --no-push` to build locally
2. Assemble all version directories into a single output directory
3. Deploy that directory to Vercel

**Effort:** Medium
**SEO quality:** Excellent
**Maintainability:** Medium — custom assembly script
**Operational risk:** Medium — changes mike's core workflow
**Workflow disruption:** Moderate — `docs-deploy-stable` needs rewriting

### Option C — Simplify version serving

Drop mike aliases. Publish only explicitly versioned paths. Use Vercel redirects for `/latest/` → `/0.4.0/`.

**Implementation:**
1. Use plain `mkdocs build` per version
2. Each version goes to its own directory
3. `vercel.json` redirects `/latest/` → current version

**Effort:** High
**SEO quality:** Good (but redirect on every page load for `/latest/`)
**Maintainability:** Low long-term maintenance of mike, but higher initial effort
**Operational risk:** High — fundamental workflow change
**Workflow disruption:** High — complete rewrite of deployment

### Recommendation: Option A

Option A is the right choice. It's the lowest-risk path, preserves the existing workflow, and solves the SEO problem completely.

---

## 4. Proposed Implementation

### 4.1. `vercel.json`

```json
{
  "$schema": "https://openapi.vercel.sh/vercel.json",
  "buildCommand": null,
  "outputDirectory": "gh-pages-output",
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
        { "key": "X-Robots-Tag", "value": "index, follow" }
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

**Notes:**
- `buildCommand: null` — we don't want Vercel to build anything; we deploy pre-built static files
- `outputDirectory: "gh-pages-output"` — the directory we populate from gh-pages content
- `cleanUrls: false` — MkDocs generates explicit `index.html` files, don't strip extensions
- `trailingSlash: true` — MkDocs expects trailing slashes on directory URLs
- Root redirect: 301 from `/` to `/latest/` replaces the meta-refresh `index.html`
- X-Robots-Tag headers: belt-and-suspenders with the existing robots.txt and canonical tags
- Old versions get `noindex, follow` — not indexed but link equity still flows
- Pre-release gets `noindex, nofollow` — completely hidden from search

### 4.2. GitHub Actions workflow changes

Replace the current `docs-deploy.yml` with a two-step process:

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
          fetch-depth: 0

      - uses: astral-sh/setup-uv@v5

      - uses: actions/setup-python@v5
        with:
          python-version: "3.13"

      - name: Install dependencies
        run: make install

      - name: Add venv to PATH
        run: echo "${{ github.workspace }}/.venv/bin" >> $GITHUB_PATH

      - name: Check documentation build
        run: make docs-check

      - name: Configure git
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"

      # Mike still builds to gh-pages branch (preserves version history)
      - name: Deploy to gh-pages with mike
        run: make docs-deploy-stable

      # Extract gh-pages content for Vercel deployment
      - name: Prepare Vercel output
        run: |
          git worktree add gh-pages-output gh-pages
          # Remove git metadata from the output directory
          rm -rf gh-pages-output/.git

      # Deploy to Vercel
      - name: Install Vercel CLI
        run: npm install -g vercel

      - name: Deploy to Vercel
        run: vercel deploy --prod --token=${{ secrets.VERCEL_TOKEN }}

  github-release:
    # ... (unchanged from current workflow)
```

**Key changes:**
- Mike still pushes to `gh-pages` (preserves version history, allows rollback)
- After mike finishes, we check out `gh-pages` into `gh-pages-output/`
- Vercel CLI deploys that directory using `vercel.json` config
- Requires three secrets: `VERCEL_ORG_ID`, `VERCEL_PROJECT_ID`, `VERCEL_TOKEN`

### 4.3. Makefile changes

Add a new target for local Vercel preview:

```makefile
docs-vercel-preview: env
	$(call PRINT_TITLE,"Building docs for Vercel preview")
	# Build with mike (no push)
	$(VENV_MIKE) deploy $(DOCS_VERSION) latest --alias-type copy
	# Extract gh-pages content
	git worktree add gh-pages-output gh-pages 2>/dev/null || true
	@echo "Output ready in gh-pages-output/. Run 'vercel dev' to preview."
```

The existing Makefile targets (`docs-deploy-stable`, `docs-deploy-root`, etc.) remain unchanged — they still work for the mike side of the workflow.

### 4.4. Simplify root assets

With Vercel handling redirects, the root `index.html` and `404.html` can be simplified:

#### Root `index.html` (in Makefile ROOT_INDEX_HTML)

The meta-refresh redirect is no longer needed since `vercel.json` handles `/` → `/latest/` with a 301. However, we should keep a minimal `index.html` as a fallback for direct file access. The existing content-rich version is fine — it just stops being the primary redirect mechanism.

**Recommendation:** Keep the existing `index.html` as-is for now. The `vercel.json` redirect takes precedence (redirects are evaluated before static files on Vercel). If the redirect somehow fails, the meta-refresh still works as a fallback.

#### Root `404.html`

The JS redirect logic in `docs/404.html` currently handles:
1. Unversioned URLs → `/latest/…`
2. Invalid version paths → `/latest/404.html`

With Vercel, we can handle case 1 with a catch-all redirect in `vercel.json`:

```json
{
  "source": "/:path((?!latest|pre-release|0\\.).*)",
  "destination": "/latest/:path",
  "statusCode": 301
}
```

This redirects any path that doesn't start with `latest/`, `pre-release/`, or `0.` to `/latest/…`.

**Recommendation:** Add this catch-all redirect to `vercel.json` and simplify `docs/404.html` to be a pure 404 page (styling + "page not found" message, no JS redirect logic). The JS version detection code becomes unnecessary.

### 4.5. Files to modify

| File | Change |
|------|--------|
| `vercel.json` | **New** — redirects, headers, deploy config |
| `.github/workflows/docs-deploy.yml` | Add Vercel deploy step after mike |
| `docs/404.html` | Simplify — remove JS redirect logic, keep as pure 404 page |
| `Makefile` | Optional: add `docs-vercel-preview` target |
| `docs/CNAME` | **Remove** — Vercel manages domains via dashboard, CNAME file would confuse it |
| `.gitignore` | Add `gh-pages-output/` and `.vercel/` |

### 4.6. DNS changes (manual)

1. In Vercel dashboard: add `mthds.ai` as a custom domain to the project
2. In DNS provider: change `mthds.ai` records from GitHub Pages IPs to Vercel's:
   - If apex domain: `A` record → `76.76.21.21`
   - If using CNAME: `CNAME` → `cname.vercel-dns.com`
3. Vercel auto-provisions TLS via Let's Encrypt

---

## 5. Redirect Strategy

### Permanent redirects (301)

| Source | Destination | Reason |
|--------|-------------|--------|
| `/` | `/latest/` | Main entrypoint |
| `/index.html` | `/latest/` | Direct file access |
| `/:path` (not versioned) | `/latest/:path` | Legacy unversioned URLs |

### Directly served paths (no redirect)

| Path pattern | Content |
|-------------|---------|
| `/latest/**` | Current stable docs (full MkDocs site) |
| `/pre-release/**` | Development docs |
| `/0.x.y/**` | Archived version docs |
| `/robots.txt` | Crawler directives |
| `/sitemap.xml` | URL index for search engines |
| `/mthds_schema.json` | JSON Schema asset |
| `/llms.txt`, `/llms-full.txt` | LLM-friendly content index |
| `/versions.json` | Mike version registry |

### Version alias behavior

`/latest/` serves the actual files (copy mode), not a redirect. This is correct for SEO — the canonical URL serves content directly, no redirect chain.

### What NOT to redirect

- `/latest/` should NOT redirect to `/0.4.0/` — it IS the content. The copy-alias means `/latest/` and `/0.4.0/` have identical files. This is fine because:
  - Only `/latest/` is in the sitemap
  - Only `/latest/` is canonicalized
  - Old version paths are `noindex` via robots.txt and X-Robots-Tag
  - Google will index `/latest/` as the canonical, ignore `/0.4.0/`

---

## 6. SEO Analysis and Recommendations

### Current SEO state: mostly excellent

The existing setup is well-architected for SEO. Specific findings:

#### Canonical tags ✅ Good
All pages have `<link rel="canonical" href="https://mthds.ai/latest/...">` hardcoded in `main.html`. This correctly points all versions to the `/latest/` canonical, preventing duplicate content issues.

#### Duplicate content between aliases ✅ Handled
`/latest/` and `/0.4.0/` contain identical files (copy mode), but:
- Canonical tags point to `/latest/`
- robots.txt disallows `/0.*`
- Sitemap only contains `/latest/` URLs
This is sufficient. Adding X-Robots-Tag headers via Vercel is belt-and-suspenders reinforcement.

#### Sitemap ✅ Good
Root `sitemap.xml` is rewritten to only contain `/latest/` URLs. No version-specific URLs leak into the sitemap.

#### robots.txt ✅ Good
Correctly allows only `/latest/`, `/sitemap.xml`, and LLM files. Blocks all versioned paths.

#### 404 pages ✅ Good
Both 404 pages have `noindex, nofollow`. No `docs/404.md` exists (which would create an indexable page).

#### Redirect template ✅ Good
Mike's `redirect.html` has `noindex, follow` — passes link equity without being indexed.

### Issues found

#### Issue 1: No real HTTP redirects ❌ Critical
This is the core problem. All redirects are client-side (meta-refresh or JS). Search engines may:
- Index the redirect page itself (200 status) instead of following the redirect
- Not pass full link equity through JS redirects
- Show the wrong URL in search results

**Fix:** Vercel `vercel.json` redirects (301 status codes).

#### Issue 2: Root index.html served with 200 status ⚠️ Moderate
The root `index.html` (meta-refresh to `/latest/`) is served with HTTP 200. Google may index `mthds.ai/` as a separate page from `mthds.ai/latest/`, creating a duplicate. The canonical tag mitigates this, but a real 301 redirect is cleaner.

**Fix:** Vercel redirect `/` → `/latest/` (301).

#### Issue 3: 404 pages return 200 status ⚠️ Moderate
GitHub Pages serves `404.html` with a 200 status code for missing paths. This means:
- Search engines may index 404 pages as real content (soft 404 problem)
- Google Search Console may report "soft 404" warnings

**Fix:** Vercel serves custom 404 pages with proper 404 status codes.

#### Issue 4: Trailing slash inconsistency ⚠️ Low
MkDocs generates `page/index.html` files, expecting `/page/` (trailing slash) URLs. GitHub Pages doesn't enforce this — `/page` and `/page/` both work, creating potential duplicate URLs.

**Fix:** `trailingSlash: true` in `vercel.json` normalizes all URLs to trailing-slash form.

#### Issue 5: No cache headers ℹ️ Cosmetic
GitHub Pages sets minimal cache headers. Static assets (CSS, JS, images) would benefit from longer cache times.

**Fix:** Add `Cache-Control` headers in `vercel.json` for static assets if desired.

### Version indexation recommendation

**Index only `/latest/`.** This is already the setup. The rationale:

- MTHDS is a young standard (v0.4.0). There's no meaningful audience searching for old version docs.
- Having a single indexed version eliminates all duplicate content risk.
- When the standard matures (v1.0+), reconsider indexing the current major version alongside `/latest/`.

**Specific policy:**
| Version | Indexed? | Crawled? | Canonical points to |
|---------|----------|----------|---------------------|
| `/latest/` | Yes | Yes | Self |
| `/pre-release/` | No | No | N/A |
| `/0.x.y/` | No | Link-follow only | `/latest/` |
| Archived versions | No | No | `/latest/` |

### Should docs live on a subdomain?

**No.** Keep docs on `mthds.ai` (apex domain). Reasons:
- The site IS the docs — there's no separate marketing site at `mthds.ai`
- A subdomain (`docs.mthds.ai`) would split domain authority
- The current URL structure (`mthds.ai/latest/…`) is clean and established
- Changing to a subdomain would break all existing inbound links

---

## 7. Migration Checklist

### Pre-migration
- [ ] Create Vercel project for `mthds.ai`
- [ ] Add secrets to GitHub repo: `VERCEL_ORG_ID`, `VERCEL_PROJECT_ID`, `VERCEL_TOKEN`
- [ ] Test deployment to a preview URL (not production domain)
- [ ] Verify all pages render correctly on Vercel preview
- [ ] Verify redirects work as expected
- [ ] Verify 404 pages return proper status codes

### Migration
- [ ] Add `vercel.json` to repo
- [ ] Update `.github/workflows/docs-deploy.yml`
- [ ] Simplify `docs/404.html` (remove JS redirect logic)
- [ ] Remove `docs/CNAME`
- [ ] Add `gh-pages-output/` and `.vercel/` to `.gitignore`
- [ ] Optional: add `docs-vercel-preview` Makefile target
- [ ] Switch DNS from GitHub Pages to Vercel
- [ ] Verify in Google Search Console that crawling works

### Post-migration
- [ ] Monitor Google Search Console for crawl errors (1-2 weeks)
- [ ] Verify no soft 404 warnings
- [ ] Check that `/latest/` pages are being indexed
- [ ] Confirm old version pages are not indexed
- [ ] Optional: disable GitHub Pages in repo settings (keep gh-pages branch for history)

---

## 8. Open Questions — Answered

> Are docs deployed from a dedicated branch, artifact, or folder today?

**Dedicated branch.** Mike pushes to `gh-pages`, GitHub Pages serves from that branch.

> Is mike being used in a standard way or with custom scripts?

**Standard mike with customizations.** The core `mike deploy` / `mike set-default` usage is standard. Custom additions: `docs-deploy-root` Makefile target that deploys root assets (404, robots, sitemap, etc.) via git worktree — this is not part of mike itself.

> What are the actual public docs URLs today?

- `https://mthds.ai/` → meta-refresh redirect to `/latest/`
- `https://mthds.ai/latest/` → current stable docs
- `https://mthds.ai/latest/language/bundles/` → example content page
- `https://mthds.ai/0.4.0/` → specific version (same content as latest currently)
- `https://mthds.ai/pre-release/` → development version (if deployed)

> Which URLs must continue to resolve for backward compatibility?

- `https://mthds.ai/latest/**` — all current docs pages
- `https://mthds.ai/` — root (redirect to latest)
- `https://mthds.ai/sitemap.xml`
- `https://mthds.ai/robots.txt`
- `https://mthds.ai/llms.txt`
- `https://mthds.ai/mthds_schema.json`
- Any versioned URLs that have been shared (e.g. `https://mthds.ai/0.3.7/...`) — these should continue to serve their archived content

> Is the default version currently latest, stable, or something else?

**`latest`.** Set via `mike set-default --push latest` in `docs-deploy-stable`.

> Do we want search engines indexing only default/stable, all supported, or all except archived?

**Only `/latest/`.** This is already the setup and the correct strategy for a young standard.

> Are there existing SEO issues already visible in the config?

Yes — see "Issues found" in section 6. The critical one is no real HTTP redirects. The others are moderate (200 status on redirects and 404s, trailing slash inconsistency).

> Would we benefit from keeping docs on a dedicated docs subdomain?

**No.** See rationale in section 6.

---

## 9. Risks and Follow-up Work

### Risks
- **DNS propagation:** Switching from GitHub Pages to Vercel involves DNS changes. TTL should be lowered in advance. There may be a brief period where some users see the old GitHub Pages site.
- **Mike version accumulation:** Over time, the gh-pages branch accumulates version directories. Each Vercel deployment uploads all of them. If this becomes large, consider pruning old versions more aggressively.
- **Vercel build limits:** Free tier has limits on deployments per day (100) and bandwidth. The docs site is small, so this shouldn't be an issue, but monitor.

### Follow-up work
- **Search Console verification:** After migration, verify the Vercel-hosted site in Google Search Console and monitor for crawl issues.
- **Legacy URL audit:** If any external sites link to `mthds.ai/0.x.y/` paths, those will still serve content (just with noindex). If any link to unversioned paths like `mthds.ai/language/bundles/`, the catch-all redirect will handle them.
- **Performance baseline:** Take a Lighthouse snapshot before and after migration to verify no regressions.
- **Consider `_redirects` or edge middleware:** If the redirect rules grow complex in the future, Vercel edge middleware offers more flexibility than `vercel.json`. Not needed now.
