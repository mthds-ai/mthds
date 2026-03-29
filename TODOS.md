# Vercel Migration for mthds.ai Docs

Migration from GitHub Pages to Vercel for proper HTTP redirects, 404 status codes, and SEO control.

---

## Phase 1: Code Changes (no user-visible changes)

### Vercel config

- [x] Create `vercel.json` with redirects (`/` and `/index.html` -> `/latest/`), X-Robots-Tag headers, security headers, `trailingSlash: true`, `cleanUrls: false`, `buildCommand: null`, `outputDirectory: site-output`

### Makefile

- [x] Add `docs-build-versioned` target -- mike deploy without `--push` (local gh-pages only)
- [x] Add `docs-assemble-site` target -- extract gh-pages into `site-output/`, generate root assets (robots.txt, sitemap.xml, index.html, 404.html, llms.txt, llms-full.txt, mthds_schema.json), remove CNAME
- [x] Add `docs-build-site` target -- combines the above two for local dev
- [x] Remove old deploy targets (`docs-deploy-stable`, `docs-deploy-specific-version`, `docs-deploy-root`)

### CI workflow

- [x] Modify `.github/workflows/docs-deploy.yml`: replace GitHub Pages deploy with Vercel deploy (build versioned -> assemble site -> size/file-count check -> `vercel deploy --prod` -> push gh-pages for version accumulation)
- [x] Add `vercel.json` to workflow trigger paths
- [x] Pin Vercel CLI version (`vercel@50.37.3`)

### Other file changes

- [x] Simplify `docs/404.html` -- remove JS redirect logic, keep as pure styled 404 page
- [x] Add `site-output/` and `.vercel/` to `.gitignore`
- [x] Remove `docs/CNAME`
- [x] Update `docs/CLAUDE.md` to reflect Vercel deployment architecture

### Files that must NOT change

- `mkdocs.yml` -- site_url, mike plugin settings, canonical_version all correct as-is
- `docs/overrides/main.html` -- canonical tag logic correct for Vercel
- `docs/overrides/redirect.html` -- mike redirect template, correct if generated
- `docs/overrides/404.html` -- MkDocs-built 404 for versioned paths, unaffected

---

## Phase 2: Local Validation

### Prerequisites

- [x] Install Vercel CLI: `npm install -g vercel@50.37.3`
- [x] Create Vercel project in dashboard (don't connect a git repo -- CI deploys via CLI)
- [x] Run `vercel link` in repo root to connect local project to Vercel

### Build and verify

- [x] Run `make docs-build-site` successfully
- [ ] Run `vercel dev` and verify locally:
  - [x] All pages render correctly
  - [x] `/` redirects to `/latest/` with 301
  - [x] `/index.html` redirects to `/latest/` with 301
  - [x] Missing pages return 404 status (not 200)
  - [x] Unversioned deep links (e.g. `/language/bundles/`) return 404 (not redirect)
  - [x] Root files served directly: `/robots.txt`, `/sitemap.xml`, `/llms.txt`, `/mthds_schema.json`

---

## Phase 3: Vercel Preview Validation

### Vercel project setup

- [x] Grab `VERCEL_ORG_ID` from Vercel dashboard: Settings > General > "Vercel ID"
- [x] Grab `VERCEL_PROJECT_ID` from project settings: Settings > General > "Project ID"
- [x] Create `VERCEL_TOKEN` in Vercel account settings: Settings > Tokens > Create
- [x] Add all 3 as GitHub repo secrets: repo Settings > Secrets and variables > Actions

### Deploy and verify on preview URL

- [x] Deploy to Vercel preview: `vercel deploy` (no `--prod`)
- [ ] Verify on preview URL (`mthds-xyz.vercel.app`):
  - [x] All pages render correctly with full CSS/JS
  - [x] 301 redirects work (`/` -> `/latest/`, `/index.html` -> `/latest/`)
  - [x] `trailingSlash: true` works: `/latest` -> 308 -> `/latest/`, `/latest/language/bundles` -> 308 -> `/latest/language/bundles/`
  - [x] Versioned root pages render correctly (`/0.3.8` served via `<base>` tag after Vercel strips trailing slash)
  - [x] 404 status on missing pages (not soft 200), with `noindex` meta tag
  - [x] `X-Robots-Tag` headers correct: `/latest/` = `index, follow`, `/0.*` = `noindex, follow`, `/pre-release/` = `noindex, nofollow`
  - [x] Security headers present (`X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`)
  - [x] Version selector works in MkDocs UI
  - [x] Canonical tags: all pages point to `/latest/` equivalent, old versions canonical to `/latest/`
  - [x] Sitemap: only `/latest/` URLs, all with trailing slashes
  - [x] robots.txt: `Allow: /latest/`, `Disallow: /0.`, `Disallow: /pre-release/`
  - [x] OG tags complete on `/latest/` (type, title, description, image with dimensions, url)
  - [x] Meta descriptions present and distinct per page
  - [x] Schema.org structured data (Organization + WebSite JSON-LD)
  - [x] No redirect chains (single hop max)
  - [x] Internal links all use trailing slashes
  - [ ] Cache-Control headers on `/latest/` paths (vercel dev overrides; verify in production)
- [ ] Run Lighthouse, save as baseline

---

## Phase 4: DNS Cutover

- [ ] Lower DNS TTL to 60s (at least 24h before cutover)
- [ ] In Vercel dashboard: add `mthds.ai` as custom domain
- [ ] Update DNS records (A record -> `76.76.21.21` or CNAME -> `cname.vercel-dns.com`)
- [ ] Verify TLS provisioned by Vercel
- [ ] Merge workflow changes to main (triggers first Vercel production deploy)
- [ ] Verify production site works on `mthds.ai`

---

## Phase 5: Post-Migration (1-2 weeks)

- [ ] Monitor Google Search Console for crawl errors
- [ ] Verify no soft 404 warnings
- [ ] Check `/latest/` pages are being indexed
- [ ] Confirm old version pages are not indexed
- [ ] Run Lighthouse, compare with Phase 3 baseline
- [ ] Restore DNS TTL to normal (3600s)
- [ ] Disable GitHub Pages in repo settings (gh-pages branch remains as mike's version accumulator, no longer a deployment target)

---

## Rollback

Rollback is Vercel-only. GitHub Pages is decommissioned after migration.

- **Bad deployment:** Promote any previous deployment in Vercel dashboard (< 1 min, no DNS change)
- **Bad config:** Revert commit in git, push to main, CI redeploys. Or promote previous deployment while fixing.

---

## Deployment Size

Current estimate: ~60-100 MB (3-4 versions with copy-mode aliases). Vercel Hobby limit: 100 MB compressed, 15k files.

If size grows:

- Prune old versions more aggressively (keep latest + 1-2 previous)
- Use `.vercelignore` to trim old version assets
- Upgrade to Vercel Pro (1 GB limit)

---

## Future: Version Path Rules for v1.0+

When MTHDS reaches v1.0, the following version-specific patterns need updating:

- `vercel.json`: Header pattern `/0.(.*)` only matches `0.x` version paths. Add pattern for `1.x` (and future major versions) to apply `X-Robots-Tag: noindex, follow`.
- `Makefile` `ROOT_ROBOTS_TXT`: `Disallow: /0.` only blocks `0.x` paths. Add `Disallow: /1.` (or generalize the pattern).
- Review the indexation policy: the design doc (section 9) suggests reconsidering indexing the current major version alongside `/latest/` once the standard matures.
