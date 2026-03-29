**Handoff: evaluate and implement Vercel hosting for our MkDocs + mike docs site**

We currently host a documentation website built with **MkDocs** and **mike** on **GitHub Pages**. This is creating SEO problems because GitHub Pages does not give us robust server-side redirect control, so URL migrations and legacy paths are hard to manage cleanly.

We want to explore moving the docs deployment to **Vercel**, since we already run several web apps there.

## Goal

Assess whether Vercel is a good fit for our current docs architecture, and if yes, propose and/or implement the cleanest deployment pattern that preserves:

* our current **MkDocs + mike** workflow
* **versioned docs**
* correct handling of **canonical URLs**
* proper **HTTP redirects** for SEO
* compatibility with our existing repo and CI/CD setup

## What to investigate

### 1. Current architecture and deployment flow

Please inspect the codebase and current deployment setup and summarize:

* how MkDocs is configured
* how `mike` is used today
* where the generated static files end up
* whether versioned docs are published under paths like `/latest/`, `/stable/`, `/vX.Y/`, etc.
* whether the default docs version is implemented via redirect, alias, copied files, or index generation
* whether GitHub Actions or another CI pipeline currently performs the deploy

Please identify the current source of truth for:

* version aliases
* canonical base URL
* sitemap generation
* robots settings
* any custom redirect workaround already in place

### 2. Vercel compatibility of the current mike strategy

We need to determine whether the current mike-generated output can be deployed to Vercel as a static site with minimal changes, or whether the workflow should be adjusted.

Questions to answer:

* Is the current output already suitable for a standard static deployment on Vercel?
* Does `mike` assume a GitHub Pages branch-based publishing model that we should replace?
* Can we switch to generating the final static artifact in CI and deploy that artifact directly to Vercel?
* Are there any issues with how mike handles version aliases that would interact poorly with Vercel routing?

### 3. Redirect strategy on Vercel

This is the core SEO reason for exploring the migration.

Please determine the best redirect mechanism for our setup:

* `vercel.json` redirects
* Next.js-style config if relevant
* edge middleware or other Vercel routing features only if necessary

We want the simplest maintainable option.

Please identify:

* which redirects should be **permanent** (`301`/`308`)
* which paths should remain directly served
* whether “latest” or “stable” should be a redirect or a rewritten alias
* whether legacy GitHub Pages URLs or previous docs paths need to be preserved

If possible, produce a proposed redirect map from the current structure.

### 4. SEO implications

Please review the docs setup for SEO-sensitive issues, especially around versioning. We want recommendations specific to our codebase, not generic advice.

Please check:

* canonical tags for each version
* whether old version pages should self-canonicalize or point elsewhere
* duplicate content risks between aliased versions
* sitemap correctness
* robots behavior for deprecated or duplicate versions
* trailing slash consistency
* whether version landing pages create indexation problems

We need a recommendation for which docs versions should be indexable.

### 5. Deployment design options

Please evaluate these options and recommend one:

**Option A — minimal migration**

* keep MkDocs + mike
* build static output in CI
* deploy to Vercel
* add redirects in `vercel.json`

**Option B — adjusted mike workflow**

* keep MkDocs
* keep versioning semantics
* change how mike artifacts are assembled/published to better fit Vercel

**Option C — simplify version serving**

* reduce reliance on aliases/indirection
* publish explicit versioned paths
* use redirects only for stable entrypoints like `/docs` or `/latest`

For each option, please note:

* implementation effort
* SEO quality
* maintainability
* operational risk
* how much it disrupts the current workflow

## Constraints / preferences

* We already use **Vercel** elsewhere, so reuse of existing conventions is a plus.
* We prefer a solution that is **simple and explicit**, rather than clever.
* We want **real HTTP redirects**, not JS/meta-refresh workarounds.
* We do **not** want to break existing inbound links.
* We should preserve the benefits of versioned docs unless there is a strong reason to change them.

## Deliverables requested

Please provide:

1. A short summary of the current docs deployment architecture
2. A recommendation on whether Vercel is a good fit
3. The best deployment design for this repo
4. Any required code/config changes
5. A proposed redirect strategy
6. Any SEO risks or follow-up work we should plan

If you can implement, please do so in a safe, reviewable way and explain the changes.

## Open questions to resolve from the repo

Please answer these based on what you find:

* Are docs deployed from a dedicated branch, artifact, or folder today?
* Is `mike` being used in a standard way or with custom scripts?
* What are the actual public docs URLs today?
* Which URLs must continue to resolve for backward compatibility?
* Is the default version currently `latest`, `stable`, or something else?
* Do we want search engines indexing:

  * only the default/stable docs,
  * all supported versions,
  * or all versions except archived ones?
* Are there existing SEO issues already visible in the config, such as duplicate canonicals, missing sitemap config, or inconsistent slashes?
* Would we benefit from keeping the docs on a dedicated docs subdomain in Vercel?

## Working assumptions unless the repo suggests otherwise

Use these assumptions as defaults, but adapt if the codebase shows something different:

* Keep **MkDocs + mike**
* Deploy the built static site directly to **Vercel**
* Use **Vercel redirects** for permanent legacy-path handling
* Prefer a single canonical public URL structure
* Keep versioned docs under explicit paths
* Make only the intended canonical/default entrypoint discoverable and avoid duplicate alias indexation
