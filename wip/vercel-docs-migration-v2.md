# Vercel Migration for MkDocs + mike Docs Sites

This document records the completed migration of `mthds.ai` from GitHub Pages to Vercel, and serves as a replication guide for migrating any MkDocs + mike versioned docs site.

---

## 1. Before: GitHub Pages Architecture

### Stack

MkDocs Material + mike versioning, deployed to GitHub Pages via the `gh-pages` branch.

### Deployment flow (pre-migration)

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

### Source of truth for key settings (pre-migration)

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

### Redirect layers (all client-side)

1. **Root `index.html`** -- `<meta http-equiv="refresh" content="0;url=/latest/">` (meta-refresh)
2. **Root `404.html`** -- JS logic: unversioned paths -> `/latest/...`, invalid versions -> `/latest/404.html`
3. **mike `redirect.html`** -- JS `window.location.replace()` for version alias redirects

None of these were real HTTP redirects. Search engines saw 200 status codes with JS/meta-refresh, not 301/308.

### SEO setup (pre-migration)

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

---

## 3. Architecture: Local mike Build + Vercel Deploy

Mike continues to manage versioned doc builds. Instead of pushing to gh-pages as the deployment mechanism:

1. Mike runs in CI, committing to the local gh-pages branch (no push to remote)
2. The gh-pages branch content is extracted into a flat `site-output/` directory
3. Root assets (robots.txt, sitemap, etc.) are generated into that same directory
4. The directory is deployed to Vercel as a static site
5. gh-pages is pushed to remote as a historical record (not on the critical deployment path)

### Why local-only mike builds

Mike is designed around a branch-based publishing model: it accumulates versioned builds as commits on `gh-pages`. GitHub Pages serves directly from that branch. This model doesn't map to Vercel, which deploys directory snapshots.

If mike pushes to remote gh-pages *and then* CI checks out that branch to build the Vercel deployment, there's a race: the push modifies the remote ref while the checkout reads it. Keeping mike local-only eliminates this. The local gh-pages branch is the working state; the remote copy is a backup pushed after the Vercel deploy succeeds.

### Why keep mike at all

Mike handles version accumulation: each deploy adds a new version directory while preserving all previous ones. Without mike, we'd need a custom script to assemble multi-version output from scratch. Mike does this correctly and is already integrated.

The `alias_type: copy` setting means `/latest/` contains real files (not redirects), which is ideal for Vercel -- the canonical URL serves content directly with no redirect chain.

### Why not a catch-all redirect for unversioned paths

Vercel evaluates redirects before checking the filesystem. A catch-all like `/:path((?!latest|pre-release|0\\.).*) -> /latest/:path` would intercept root-level static files (`/robots.txt`, `/sitemap.xml`, `/llms.txt`, `/mthds_schema.json`, `/versions.json`), redirecting them to `/latest/robots.txt` etc. -- which either don't exist or are the wrong files.

Working around this requires negative lookaheads for every root file, creating a brittle rule that breaks whenever a new root file is added.

Instead: explicit redirects only (`/`, `/index.html`, and known legacy paths like `/know-how-graph/`). Unversioned deep links were never canonical (all public URLs use `/latest/` prefix), so they 404 cleanly. If analytics later reveal specific unversioned URLs with significant traffic, add them as individual redirect rules.

### Trailing slash handling

`trailingSlash: true` is set in `vercel.json`. This ensures all directory paths get trailing slashes via 308 redirect, which is required for MkDocs' relative asset paths to resolve correctly.

**Versioned directory workaround:** Vercel treats the dot in semver directory names (`0.3.8`) as a file extension (`.8`) and strips the trailing slash instead of adding it (`/0.3.8/` -> 308 -> `/0.3.8`). This breaks relative asset paths on versioned root pages. Fix: during `docs-assemble-site`, a `<base href="/VERSION/">` tag is injected into each versioned root `index.html`. This makes the browser resolve all relative URLs from the correct base, even at the slashless URL. Only the root `index.html` of each version needs this -- deep pages like `/0.3.8/language/bundles/` work correctly because the last path segment has no dot.

### Why the root index.html must be deleted

Mike generates a root `index.html` (via `mike set-default`) that contains a JS redirect to `/latest/`. When this file exists in `site-output/`, Vercel serves it as the directory index for `/` -- the `vercel.json` 301 redirect for `/` never fires. The `docs-assemble-site` target explicitly deletes this file (`rm -f site-output/index.html`) so that Vercel's redirect rules take over.

---

## 4. vercel.json -- Routing & Headers

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
    },
    {
      "source": "/know-how-graph/",
      "destination": "/latest/know-how-graph/",
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
| `buildCommand` | `null` | Pre-built static files; Vercel should not run any build |
| `outputDirectory` | `site-output` | The directory CI populates with the full static site |
| `cleanUrls` | `false` | MkDocs generates explicit `index.html` files; don't strip `.html` extensions |
| `trailingSlash` | `true` | Required for MkDocs relative asset paths. Dotted version directories are handled by `<base>` tag injection (see section 3) |

### Redirect rules

| Source | Destination | Code | Purpose |
|--------|-------------|------|---------|
| `/` | `/latest/` | 301 | Main entrypoint -- replaces meta-refresh `index.html` |
| `/index.html` | `/latest/` | 301 | Direct file access to root index |
| `/know-how-graph/` | `/latest/know-how-graph/` | 301 | Legacy path from before versioned docs existed |

Only explicit redirects. No catch-all. Vercel's redirect evaluation runs before filesystem checks, so keeping the redirect set minimal avoids intercepting static files. Legacy paths are added individually as needed.

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

## 5. Makefile Targets

### robots.txt definition

```makefile
define ROOT_ROBOTS_TXT
User-agent: *
Allow: /latest/
Allow: /sitemap.xml
Allow: /llms.txt
Allow: /llms-full.txt
Disallow: /0.
Disallow: /pre-release/
Disallow: /404.html

Sitemap: https://mthds.ai/sitemap.xml
endef
export ROOT_ROBOTS_TXT
```

### Documentation targets

```makefile
# Build versioned docs with mike (local gh-pages only, no push)
docs-build-versioned: env
	$(call PRINT_TITLE,Building versioned docs with mike -- local gh-pages only)
	$(VENV_MIKE) deploy --update-aliases --alias-type copy $(DOCS_VERSION) latest
	$(VENV_MIKE) set-default latest

# Extract gh-pages content and assemble root assets into site-output/
docs-assemble-site:
	$(call PRINT_TITLE,Assembling site output from gh-pages + root assets)
	@rm -rf site-output; \
	TMPDIR=$$(mktemp -d); \
	trap "cd '$(CURDIR)'; git worktree remove '$$TMPDIR' 2>/dev/null || true; rm -rf '$$TMPDIR'" EXIT; \
	git worktree add "$$TMPDIR" gh-pages && \
	cp -a "$$TMPDIR/." site-output/ && \
	rm -rf site-output/.git && \
	rm -f site-output/index.html && \
	cp docs/404.html site-output/404.html && \
	cp docs/mthds_schema.json site-output/mthds_schema.json && \
	echo "$$ROOT_ROBOTS_TXT" > site-output/robots.txt && \
	if [ -f site-output/latest/sitemap.xml ]; then \
		sed 's|<loc>https://mthds.ai/[^/]*/|<loc>https://mthds.ai/latest/|g' \
			site-output/latest/sitemap.xml > site-output/sitemap.xml; \
	fi && \
	if [ -f site-output/latest/llms.txt ]; then cp site-output/latest/llms.txt site-output/llms.txt; fi && \
	if [ -f site-output/latest/llms-full.txt ]; then cp site-output/latest/llms-full.txt site-output/llms-full.txt; fi && \
	rm -f site-output/CNAME && \
	for dir in site-output/[0-9]*.[0-9]*.[0-9]*/; do \
		version=$$(basename "$$dir"); \
		if [ -f "$$dir/index.html" ]; then \
			sed 's|<head>|<head>\n<base href="/'"$$version"'/">|' "$$dir/index.html" > "$$dir/index.html.tmp" && \
			mv "$$dir/index.html.tmp" "$$dir/index.html"; \
		fi; \
	done && \
	echo "Site output ready in site-output/"

# Full pipeline: build versioned + assemble (for local dev)
docs-build-site: docs-build-versioned docs-assemble-site
	@echo "Complete site ready in site-output/. Run 'vercel dev' to preview locally."

# Prune old versions listed in versions-to-delete.txt (local gh-pages)
docs-prune: env
	$(call PRINT_TITLE,Pruning versions listed in versions-to-delete.txt)
	@bash scripts/docs-prune.sh versions-to-delete.txt $(VENV_MIKE)

# Delete a specific version from local gh-pages
docs-delete: env
	@if [ -z "$(VERSION)" ]; then echo "ERROR: VERSION is required. Usage: make docs-delete VERSION='x.y.z x.y.z ...'"; exit 1; fi
	$(call PRINT_TITLE,Deleting documentation versions: $(VERSION))
	$(VENV_MIKE) delete $(VERSION)
```

### What `docs-assemble-site` does step by step

1. Removes any previous `site-output/` directory
2. Creates a temp directory and attaches it as a git worktree from the `gh-pages` branch
3. Copies all gh-pages content into `site-output/` (preserving file attributes)
4. Removes `.git` metadata from the copy
5. **Deletes the root `index.html`** -- mike's JS redirect; must not exist or Vercel's 301 redirect for `/` won't fire
6. Copies root assets from `docs/`: `404.html`, `mthds_schema.json`
7. Writes `robots.txt` from the `ROOT_ROBOTS_TXT` Makefile variable
8. Generates root `sitemap.xml` by rewriting `latest/sitemap.xml` URLs to use `/latest/` prefix
9. Copies `llms.txt` and `llms-full.txt` from `latest/` to root
10. Removes `CNAME` file (Vercel manages domains via its dashboard)
11. Injects `<base href="/VERSION/">` into each versioned root `index.html` (workaround for Vercel's trailing-slash behavior on dotted directory names)
12. Cleans up the temp worktree via the `trap`

### Removed targets

The following old targets were removed during the migration:

- `docs-deploy-stable` -- pushed to gh-pages + set aliases + deployed root assets (replaced by the build/assemble/deploy pipeline)
- `docs-deploy-specific-version` -- pushed a tagged version (replaced by `docs-deploy` for local use)
- `docs-deploy-root` -- deployed root assets to gh-pages (replaced by `docs-assemble-site`)

---

## 6. Version Pruning

A declarative system for removing old documentation versions from the gh-pages branch.

### versions-to-delete.txt

A simple text file listing versions to remove. One version per line. Comments with `#`, blank lines ignored.

```
# Versions to prune from gh-pages during CI
0.3.5
0.3.6
```

### scripts/docs-prune.sh

```bash
#!/usr/bin/env bash
# Delete documentation versions listed in versions-to-delete.txt from local gh-pages.
# Skips versions that don't exist. Does NOT push — CI handles that.
set -euo pipefail

PRUNE_FILE="${1:?Usage: docs-prune.sh <versions-to-delete.txt> <mike-binary>}"
MIKE="${2:?Usage: docs-prune.sh <versions-to-delete.txt> <mike-binary>}"

if [ ! -f "$PRUNE_FILE" ]; then
    echo "No prune file found at $PRUNE_FILE — nothing to do."
    exit 0
fi

# Read existing versions once
if ! EXISTING=$("$MIKE" list 2>&1); then
    echo "mike list failed (no gh-pages branch yet?) — nothing to prune."
    exit 0
fi

PRUNED=0
while IFS= read -r version || [ -n "$version" ]; do
    # Skip empty lines and comments
    version=$(echo "$version" | xargs)
    [[ -z "$version" || "$version" == \#* ]] && continue

    escaped=$(printf '%s\n' "$version" | sed 's/[.[\*^$()+?{|\\]/\\&/g')
    if echo "$EXISTING" | grep -Eq "^${escaped}( |$)"; then
        echo "Deleting version: $version"
        "$MIKE" delete "$version"
        PRUNED=$((PRUNED + 1))
    else
        echo "Skipping $version (not found in gh-pages)"
    fi
done < "$PRUNE_FILE"

if [ "$PRUNED" -gt 0 ]; then
    echo "Pruned $PRUNED version(s) from gh-pages."
else
    echo "No versions to prune."
fi
```

### Integration

- CI runs `make docs-prune` **before** `make docs-build-versioned`, so the new build doesn't include deleted versions
- The script is idempotent: versions already absent are silently skipped
- The prune file is committed to git and included in the CI workflow trigger paths, so adding a version to delete triggers a redeploy
- The script does not push -- CI handles `git push origin gh-pages` after the Vercel deploy succeeds

---

## 7. CI Workflow

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
      - "vercel.json"
      - "versions-to-delete.txt"
      - ".github/workflows/docs-deploy.yml"
  workflow_dispatch:

permissions:
  contents: write

jobs:
  deploy:
    runs-on: ubuntu-latest
    env:
      VERCEL_ORG_ID: ${{ secrets.VERCEL_ORG_ID }}
      VERCEL_PROJECT_ID: ${{ secrets.VERCEL_PROJECT_ID }}
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

      - name: Prune old documentation versions
        run: make docs-prune

      - name: Build versioned docs with mike
        run: make docs-build-versioned

      - name: Assemble site output
        run: make docs-assemble-site

      - name: Check deployment size
        run: |
          SIZE=$(du -sm site-output/ | cut -f1)
          FILES=$(find site-output/ -type f | wc -l | tr -d ' ')
          echo "Site output: ${SIZE} MB, ${FILES} files"
          if [ "$SIZE" -gt 80 ]; then
            echo "::warning::Site output is ${SIZE} MB (Vercel Hobby limit: 100 MB compressed). Consider pruning old versions."
          fi
          if [ "$FILES" -gt 12000 ]; then
            echo "::warning::Site output has ${FILES} files (Vercel limit: 15,000). Consider pruning old versions."
          fi

      - name: Install Vercel CLI
        run: npm install -g vercel@50.37.3

      - name: Deploy to Vercel
        run: vercel deploy --prod
        env:
          VERCEL_TOKEN: ${{ secrets.VERCEL_TOKEN }}

      - name: Push gh-pages branch
        run: git push origin gh-pages

  github-release:
    name: Create GitHub Release
    needs: deploy
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Extract version
        id: get_version
        run: |
          VERSION=$(grep -m 1 'version = ' pyproject.toml | cut -d '"' -f 2)
          echo "VERSION=$VERSION" >> $GITHUB_ENV
          echo "Detected version: $VERSION"

      - name: Check if release already exists
        id: check_release
        env:
          GITHUB_TOKEN: ${{ github.token }}
        run: |
          if gh release view "v$VERSION" --repo "$GITHUB_REPOSITORY" > /dev/null 2>&1; then
            echo "Release v$VERSION already exists, skipping."
            echo "EXISTS=true" >> $GITHUB_ENV
          else
            echo "Release v$VERSION does not exist, will create."
            echo "EXISTS=false" >> $GITHUB_ENV
          fi

      - name: Extract changelog notes
        if: env.EXISTS == 'false'
        run: |
          VERSION="${{ env.VERSION }}"
          echo "Extracting changelog for version v$VERSION"

          START_LINE=$(grep -n "## \[v$VERSION\] - " CHANGELOG.md | cut -d: -f1)

          if [ -z "$START_LINE" ]; then
            echo "Warning: No changelog entry found for version v$VERSION"
            echo "CHANGELOG_NOTES=" >> $GITHUB_ENV
            exit 0
          fi

          NEXT_VERSION_LINE=$(tail -n +$((START_LINE + 1)) CHANGELOG.md | grep -n "^## \[v.*\] - " | head -1 | cut -d: -f1)

          if [ -z "$NEXT_VERSION_LINE" ]; then
            CHANGELOG_CONTENT=$(tail -n +$START_LINE CHANGELOG.md)
          else
            END_LINE=$((START_LINE + NEXT_VERSION_LINE - 1))
            CHANGELOG_CONTENT=$(sed -n "$START_LINE,$((END_LINE - 1))p" CHANGELOG.md)
          fi

          HEADER_LINE=$(echo "$CHANGELOG_CONTENT" | head -1)
          CONTENT_LINES=$(echo "$CHANGELOG_CONTENT" | tail -n +2 | sed '/^$/d' | sed 's/^[[:space:]]*//' | sed 's/[[:space:]]*$//')

          CHANGELOG_CONTENT=$(printf "%s\n\n%s" "$HEADER_LINE" "$CONTENT_LINES")

          echo "CHANGELOG_NOTES<<EOF" >> $GITHUB_ENV
          echo "$CHANGELOG_CONTENT" >> $GITHUB_ENV
          echo "EOF" >> $GITHUB_ENV

      - name: Create GitHub Release
        if: env.EXISTS == 'false'
        env:
          GITHUB_TOKEN: ${{ github.token }}
        run: |
          if [ -n "$CHANGELOG_NOTES" ]; then
            gh release create "v$VERSION" \
              --repo "$GITHUB_REPOSITORY" \
              --title "v$VERSION" \
              --notes "$CHANGELOG_NOTES"
          else
            gh release create "v$VERSION" \
              --repo "$GITHUB_REPOSITORY" \
              --title "v$VERSION" \
              --generate-notes \
              --notes "Release v$VERSION"
          fi
```

### Key design choices

**`fetch-depth: 0`** -- mike needs access to the `gh-pages` branch to read existing versions. Shallow clones break this.

**Prune before build** -- `docs-prune` runs before `docs-build-versioned` so the new build doesn't include versions marked for deletion.

**Separate build and assemble steps** -- `docs-build-versioned` runs mike (commits to local gh-pages). `docs-assemble-site` extracts that content and adds root assets. Separating them makes each step independently testable and the failure mode clear.

**Deployment size check** -- After assembly, the workflow checks that the output is within Vercel Hobby plan limits (100 MB compressed, 15K files). Warning thresholds are set at 80 MB and 12K files to give advance notice.

**Vercel deploy before gh-pages push** -- The Vercel deployment is the critical path. The gh-pages push happens after because its only purpose is persisting mike's version accumulation for the next CI run. If the Vercel deploy fails, we don't push (no state change). If it succeeds but gh-pages push fails, the site is live and the push can be retried.

**`VERCEL_TOKEN` scoped to the deploy step** -- Principle of least privilege. Only the step that needs the token has it in its environment.

**Vercel CLI pinned to a specific version** -- `vercel@50.37.3`. Prevents CI breakage from unexpected CLI updates.

**Three secrets required:**

- `VERCEL_ORG_ID` -- Vercel organization identifier
- `VERCEL_PROJECT_ID` -- Vercel project identifier
- `VERCEL_TOKEN` -- Vercel API token for CLI authentication

---

## 8. 404 Page

The root 404 page (`docs/404.html`) is a standalone HTML file -- not part of the MkDocs build. It is copied into `site-output/404.html` by `docs-assemble-site`. Vercel serves it with a proper HTTP 404 status code for all unmatched routes.

This is distinct from `docs/overrides/404.html`, which is the MkDocs Material template override for versioned paths (e.g. `/latest/nonexistent/`).

```html
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta name="robots" content="noindex, nofollow">
    <link rel="canonical" href="https://mthds.ai/latest/">
    <title>Page not found | MTHDS Documentation</title>
    <style>
        :root {
            --bg: #f5f5f5;
            --panel: #ffffff;
            --text: #1a1a1a;
            --muted: #666666;
            --accent: #333333;
            --accent-hover: #000000;
            --shadow: rgba(0, 0, 0, 0.08);
        }

        @media (prefers-color-scheme: dark) {
            :root {
                --bg: #1a1a1a;
                --panel: #2a2a2a;
                --text: #f0f0f0;
                --muted: #999999;
                --accent: #cccccc;
                --accent-hover: #ffffff;
                --shadow: rgba(0, 0, 0, 0.35);
            }
        }

        * { box-sizing: border-box; }

        body {
            margin: 0;
            min-height: 100vh;
            display: grid;
            place-items: center;
            padding: 24px;
            background: var(--bg);
            color: var(--text);
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        }

        main {
            max-width: 720px;
            padding: 32px;
            border-radius: 18px;
            background: var(--panel);
            box-shadow: 0 24px 80px var(--shadow);
        }

        h1 { margin: 0 0 12px; font-size: clamp(2rem, 4vw, 2.8rem); line-height: 1.1; }
        p { margin: 0 0 12px; color: var(--muted); line-height: 1.6; }
        a { color: var(--accent); text-decoration: none; }
        a:hover { color: var(--accent-hover); }
        .actions { margin-top: 20px; }
        .button {
            display: inline-block;
            padding: 12px 18px;
            border-radius: 999px;
            background: var(--accent);
            color: var(--bg);
            font-weight: 600;
        }
        .button:hover { color: var(--bg); background: var(--accent-hover); }
    </style>
</head>
<body>
    <main>
        <h1>Page not found</h1>
        <p>The page you requested does not exist in this documentation version.</p>
        <p>The page may have been moved or removed. Try starting from the documentation homepage.</p>
        <div class="actions">
            <a class="button" href="/latest/">Go to the latest docs</a>
        </div>
    </main>
</body>
</html>
```

Key properties:

- `noindex, nofollow` meta tag -- prevents indexation
- Canonical points to `/latest/` -- safe fallback
- Dark mode via `prefers-color-scheme` -- works without JS
- No JS redirect logic -- all redirects are in `vercel.json`
- Grayscale palette -- doesn't depend on the MkDocs theme CSS

---

## 9. SEO Architecture

### Existing setup (preserved through migration)

**Canonical tags** -- All pages have `<link rel="canonical" href="https://mthds.ai/latest/...">` hardcoded in `main.html`. This correctly points all versions to `/latest/`, preventing duplicate content.

**Duplicate content between aliases** -- `/latest/` and `/0.4.0/` contain identical files (copy mode), but canonical tags point to `/latest/`, robots.txt disallows `/0.*`, and the sitemap only contains `/latest/` URLs. The `X-Robots-Tag` headers via Vercel reinforce this.

**Sitemap** -- Root `sitemap.xml` is rewritten to only contain `/latest/` URLs. No version-specific URLs leak.

**robots.txt** -- Correctly allows only `/latest/`, `/sitemap.xml`, and LLM files. Blocks all versioned paths.

**404 pages** -- Both have `noindex, nofollow`. No indexable 404 content.

**Redirect template** -- Mike's `redirect.html` has `noindex, follow` -- passes link equity without being indexed.

### Issues that Vercel resolved

**No real HTTP redirects (critical)** -- All redirects were client-side (meta-refresh or JS). Search engines could index the redirect page itself (200 status), not pass full link equity through JS redirects, or show the wrong URL in results. Vercel redirects return proper 301 status codes.

**Root index.html served with 200 (moderate)** -- Google could index `mthds.ai/` as a separate page from `mthds.ai/latest/`. A 301 redirect is cleaner than relying solely on the canonical tag.

**404 pages returned 200 (moderate)** -- GitHub Pages served `404.html` with 200 status for missing paths. Google reported "soft 404" warnings in Search Console. Vercel serves custom 404 pages with proper 404 status.

**Trailing slash inconsistency (fixed)** -- `trailingSlash: true` normalizes all paths to have trailing slashes via 308 redirect. Versioned directories are handled by `<base>` tag injection (see section 3).

### Version indexation policy

Index only `/latest/`. A single indexed version eliminates all duplicate content risk.

| Version | Indexed | Crawled | Canonical |
|---------|---------|---------|-----------|
| `/latest/` | Yes | Yes | Self |
| `/pre-release/` | No | No | N/A |
| `/0.x.y/` | No | Link-follow only | `/latest/` |

---

## 10. File Changes Summary

### Created

| File | Purpose |
|------|---------|
| `vercel.json` | Redirects, headers, deploy config |
| `scripts/docs-prune.sh` | Version pruning script |
| `versions-to-delete.txt` | Declarative list of versions to prune |

### Modified

| File | Change |
|------|--------|
| `.github/workflows/docs-deploy.yml` | Replaced GitHub Pages deploy with Vercel deploy pipeline |
| `Makefile` | Added `docs-build-versioned`, `docs-assemble-site`, `docs-build-site`, `docs-prune`, `docs-delete`; removed `docs-deploy-stable`, `docs-deploy-specific-version`, `docs-deploy-root` |
| `docs/404.html` | Removed JS redirect logic, kept as pure styled 404 page |
| `.gitignore` | Added `site-output/`, `.vercel/`, `.vercel`, `.env*.local` |
| `docs/CLAUDE.md` | Updated to document Vercel deployment architecture |

### Removed

| File | Why |
|------|-----|
| `docs/CNAME` | Vercel manages custom domains via its dashboard; a CNAME file in the output can confuse Vercel's domain resolution |

### Unchanged

| File | Why it stays |
|------|-------------|
| `mkdocs.yml` | No MkDocs config changes needed. `site_url`, mike plugin settings, `canonical_version` all correct as-is |
| `docs/overrides/main.html` | Canonical tag logic (`https://mthds.ai/latest/`) is correct for Vercel |
| `docs/overrides/redirect.html` | Mike's redirect template. With `alias_type: copy` these are rarely generated, but the template is correct if they are |
| `docs/overrides/404.html` | MkDocs-built 404 for versioned paths. Correct and unaffected |

---

## 11. Deployment Size & Limits

### Current estimate

Each version's docs output is approximately 15-25 MB (HTML, CSS, JS, images). With copy-mode aliases, `latest/` and the current version (e.g. `0.4.0/`) are duplicates. Current total with 3-4 versions: approximately 60-100 MB.

### Vercel limits

- **Hobby plan:** 100 MB compressed upload size, 15,000 files per deployment
- **Pro plan:** 1 GB compressed, 15,000 files

### CI size check

The CI workflow checks the assembled site after `docs-assemble-site`:

```bash
SIZE=$(du -sm site-output/ | cut -f1)
FILES=$(find site-output/ -type f | wc -l | tr -d ' ')
echo "Site output: ${SIZE} MB, ${FILES} files"
if [ "$SIZE" -gt 80 ]; then
  echo "::warning::Site output is ${SIZE} MB (Vercel Hobby limit: 100 MB compressed). Consider pruning old versions."
fi
if [ "$FILES" -gt 12000 ]; then
  echo "::warning::Site output has ${FILES} files (Vercel limit: 15,000). Consider pruning old versions."
fi
```

Warning thresholds (80 MB, 12K files) are intentionally below the hard limits to give advance notice.

### Mitigation

If deployment size approaches limits:

1. Add old versions to `versions-to-delete.txt` (keep only latest + 1-2 previous)
2. Use `.vercelignore` to exclude unnecessary files from old versions
3. Upgrade to Vercel Pro if the project warrants it

---

## 12. Replication Guide

Step-by-step instructions for migrating another MkDocs + mike site from GitHub Pages to Vercel. Site-specific values are marked with `{PLACEHOLDER}`.

### Prerequisites

- Vercel account (Hobby plan is sufficient for most docs sites)
- Vercel CLI installed: `npm install -g vercel@50.37.3`
- Existing MkDocs + mike setup with a `gh-pages` branch
- GitHub Actions (or similar CI) already deploying to GitHub Pages

### Step 1: Create Vercel project

1. In the Vercel dashboard, create a new project. **Do not connect a git repo** -- CI deploys via CLI.
2. Run `vercel link` in the repo root to connect the local project.
3. Note `VERCEL_ORG_ID` and `VERCEL_PROJECT_ID` from `.vercel/project.json`.

### Step 2: Create `vercel.json`

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
      "destination": "/{DEFAULT_VERSION}/",
      "statusCode": 301
    },
    {
      "source": "/index.html",
      "destination": "/{DEFAULT_VERSION}/",
      "statusCode": 301
    }
  ],

  "headers": [
    {
      "source": "/{DEFAULT_VERSION}/(.*)",
      "headers": [
        { "key": "X-Robots-Tag", "value": "index, follow" },
        { "key": "Cache-Control", "value": "public, max-age=3600, s-maxage=86400" }
      ]
    },
    {
      "source": "/{OLD_VERSION_PATTERN}(.*)",
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

Key settings:

- `buildCommand: null` -- Vercel should not build anything; you deploy pre-built files
- `outputDirectory: "site-output"` -- the directory your CI populates
- `cleanUrls: false` -- MkDocs generates explicit `index.html` files
- `trailingSlash: true` -- required for MkDocs relative asset paths

Add legacy redirects as individual rules if you have known old URLs with traffic.

### Step 3: Add Makefile targets

Add three targets to your Makefile:

1. **`docs-build-versioned`** -- runs mike without `--push` (local gh-pages only)
2. **`docs-assemble-site`** -- extracts gh-pages via temp worktree into `site-output/`, adds root assets, deletes mike's root `index.html`, injects `<base>` tags for dotted version directories
3. **`docs-build-site`** -- combines the above two for local dev

Critical implementation details for `docs-assemble-site`:

- **Use a temp directory for the worktree**, not `site-output` directly. Using `git worktree add site-output gh-pages` leaves a worktree reference that breaks subsequent runs. Use `mktemp -d` -> worktree -> `cp -a` -> cleanup via `trap`.
- **Delete the root `index.html`** -- mike's `set-default` generates a JS redirect; if this file exists, Vercel serves it instead of firing the `vercel.json` redirect.
- **Rewrite sitemap URLs** to use the canonical version prefix. The sed pattern must match full absolute URLs (e.g. `https://{DOMAIN}/VERSION/`) because MkDocs generates absolute URLs when `site_url` is set.
- **Inject `<base href>` tags** into versioned root `index.html` files for directories with dots in their names (e.g. `0.4.0/`). Vercel misidentifies the dot as a file extension and strips the trailing slash.
- **Remove `CNAME`** -- Vercel manages domains via its dashboard.

See section 5 for the complete implementation.

### Step 4: Version pruning (optional)

Create `scripts/docs-prune.sh` and `versions-to-delete.txt`. See section 6 for the complete implementation.

### Step 5: Simplify 404.html

Remove all JS redirect logic from your root `404.html`. Keep it as a pure styled page with `noindex, nofollow` meta tag. Vercel serves it with proper 404 status.

See section 8 for the complete implementation.

### Step 6: Update `.gitignore`

Add:

```
site-output/
.vercel/
.vercel
.env*.local
```

### Step 7: Remove `docs/CNAME`

Delete the CNAME file. Vercel manages custom domains via its dashboard. A CNAME file in the output directory can confuse Vercel's domain resolution.

### Step 8: Create CI workflow

Replace your GitHub Pages deploy steps with:

1. `make docs-check` (strict build validation)
2. `make docs-prune` (prune old versions)
3. `make docs-build-versioned` (mike -> local gh-pages)
4. `make docs-assemble-site` (gh-pages -> site-output/)
5. Size/file-count check with warnings
6. `npm install -g vercel@{PINNED_VERSION}`
7. `vercel deploy --prod` (with `VERCEL_TOKEN` as step-level env)
8. `git push origin gh-pages` (persist version accumulation)

Critical: `fetch-depth: 0` on checkout -- mike needs full history and the gh-pages branch.

See section 7 for the complete workflow.

### Step 9: Add GitHub secrets

Add these three secrets to your GitHub repo (Settings -> Secrets and variables -> Actions):

- `VERCEL_ORG_ID` -- from Vercel dashboard: Settings -> General -> "Vercel ID"
- `VERCEL_PROJECT_ID` -- from project settings: Settings -> General -> "Project ID"
- `VERCEL_TOKEN` -- from Vercel account settings: Settings -> Tokens -> Create

### Step 10: Local validation

```bash
make docs-build-site
vercel dev
```

Verify:

- All pages render correctly
- `/` redirects to `/{DEFAULT_VERSION}/` with 301
- Missing pages return 404 status (not 200)
- Root files served: `/robots.txt`, `/sitemap.xml`

### Step 11: Preview deploy

```bash
vercel deploy  # no --prod
```

Verify on the preview URL:

- 301 redirects work
- `trailingSlash` works (308 on paths without trailing slash)
- `X-Robots-Tag` headers correct per version path
- Security headers present
- Version selector works in MkDocs UI
- Run Lighthouse, save as baseline

### Step 12: DNS cutover

1. Lower DNS TTL to 60s (at least 24h before cutover)
2. In Vercel dashboard: add your custom domain to the project
3. Update DNS records (A record -> `76.76.21.21` or CNAME -> `cname.vercel-dns.com`)
4. Verify TLS provisioned by Vercel
5. Merge workflow changes to main (triggers first Vercel production deploy)
6. Verify production site

### Step 13: Post-migration monitoring (1-2 weeks)

- Monitor Google Search Console for crawl errors
- Verify no soft 404 warnings
- Check canonical pages are being indexed
- Confirm old version pages are not indexed
- Run Lighthouse, compare with preview baseline
- Restore DNS TTL to normal (3600s)
- Disable GitHub Pages in repo settings (gh-pages branch remains as mike's version accumulator)

---

## 13. Gotchas & Lessons Learned

### trailingSlash + dotted directory names

Vercel's `trailingSlash: true` normally adds a trailing slash via 308 redirect. But for directories with dots in their names (e.g. `0.3.8/`), Vercel interprets the dot as a file extension and **strips** the trailing slash instead. This breaks MkDocs relative asset paths on the versioned root page.

**Fix:** Inject `<base href="/VERSION/">` into each versioned root `index.html` during site assembly. This makes the browser resolve relative URLs from the correct base regardless of whether the URL has a trailing slash.

### Root index.html must be deleted

Mike's `set-default` command generates a root `index.html` with a JS redirect. If this file exists in `site-output/`, Vercel serves it as the directory index for `/` -- the `vercel.json` 301 redirect for `/` **never fires**. The assembly step must explicitly delete it.

### Sitemap URL rewrite pattern

MkDocs generates absolute URLs in sitemaps when `site_url` is set. The sed pattern must match the full URL including the domain and version prefix:

```bash
# Correct: matches absolute URLs with any version prefix
sed 's|<loc>https://mthds.ai/[^/]*/|<loc>https://mthds.ai/latest/|g'

# Wrong: only matches relative paths (won't match MkDocs output)
sed 's|<loc>/|<loc>/latest/|g'
```

### Worktree cleanup

Using `git worktree add site-output gh-pages` directly creates a worktree reference in `.git/worktrees/`. If `site-output/` is later deleted (e.g. by `rm -rf site-output`), the stale worktree reference causes git errors on the next run. Solution: use a temp directory for the worktree, copy out what you need, and clean up via `trap`.

### Vercel CLI version pinning

Pin the Vercel CLI version in CI (e.g. `vercel@50.37.3`). The CLI is updated frequently, and breaking changes in the deploy command or config handling can silently break CI.

### VERCEL_TOKEN scope

Pass `VERCEL_TOKEN` as a step-level env var (only on the deploy step), not job-level. Principle of least privilege -- other steps don't need it, and limiting exposure reduces the blast radius if any step is compromised.

### Vercel header patterns use path-to-regexp, not regex

In `vercel.json` header `source` patterns, `.` is a **literal dot** (not a regex wildcard). `/0.(.*)` correctly matches paths starting with `/0.` without needing to escape the dot. This is different from regex-based systems.

---

## 14. Future: Version Path Rules for v1.0+

When the standard reaches v1.0, the following version-specific patterns need updating:

- **`vercel.json`**: Header pattern `/0.(.*)` only matches `0.x` version paths. Add pattern for `1.x` (and future major versions) to apply `X-Robots-Tag: noindex, follow`.
- **`Makefile` `ROOT_ROBOTS_TXT`**: `Disallow: /0.` only blocks `0.x` paths. Add `Disallow: /1.` (or generalize the pattern).
- **Indexation policy review**: Reconsider indexing the current major version alongside `/latest/` once the standard matures.

---

## Rollback

Rollback is Vercel-only. GitHub Pages is decommissioned after migration.

- **Bad deployment (< 1 min):** Promote any previous deployment in the Vercel dashboard. No DNS change, no CI run needed.
- **Bad config:** Revert commit in git, push to main, CI redeploys. Or promote a previous deployment while fixing.
