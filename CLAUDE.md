# MTHDS Site

This is the documentation site for the MTHDS open standard.

## Project Setup

- **Framework**: MkDocs with Material theme, versioned with mike
- **Python env**: `.venv` (managed by uv)
- **Build/serve**: `make docs` (serve locally), `make docs-check` (strict build)
- **Install deps**: `make install`

## Editorial Rules (from docs-strategy.md)

### Tone and Voice

- **Standard-focused**: Write "MTHDS defines..." not "We built..."
- **Example-led**: Every concept introduced with a concrete `.mthds` or `METHODS.toml` snippet first, explanation second
- **No marketing speak**: No superlatives, no hype, no feature comparisons positioning MTHDS as "better"
- **Active voice, imperative for instructions**: "Create a file named `method.mthds`."
- **Third-person for implementations**: "A compliant runtime must validate..." / "The reference implementation (Pipelex) handles this by..."

### The Pipelex Boundary

Pipelex is the maintainer and reference implementation. It appears ONLY in:

- The footer (already in `overrides/main.html`)
- The About section (as maintainer and reference implementation)
- "For Implementers" section (with "reference implementation" framing)
- The Tooling section (the VS Code extension is named "Pipelex", `plxt` is distributed with Pipelex)

Pipelex does NOT appear in: the landing page, the Language section, the Package System section, the Specification, the CLI Reference, or the Guides.

### Terminology (must be consistent across all pages)

- **bundle**: A `.mthds` file (not "file" or "module")
- **concept code**: The identifier for a concept (e.g., `JokeIdea`)
- **pipe code**: The identifier for a pipe (e.g., `generate_joke`)
- **domain code**: The identifier for a domain (e.g., `jokes`)
- **bare reference**: Unqualified name resolved within the bundle
- **domain-qualified**: `domain.Name` syntax
- **package-qualified**: `alias->domain.Name` syntax

### Technical Constants (verified against codebase)

- `MTHDS_STANDARD_VERSION` = `"1.0.0"` (not `"0.2.0"` from the design doc)
- `RESERVED_DOMAINS` = `{"native", "mthds", "pipelex"}`
- `NATIVE_PACKAGE_ADDRESS` = `"__native__"`
- Native concepts: 11 (Dynamic, Text, Image, Document, Html, TextAndImages, Number, ImgGenPrompt, Page, JSON, Anything)
- Pipe types: 5 operators (PipeLLM, PipeFunc, PipeImgGen, PipeExtract, PipeCompose) + 4 controllers (PipeBatch, PipeCondition, PipeParallel, PipeSequence)
- Concept field types: 8 (text, list, dict, integer, boolean, number, date, concept)
- Template categories: 7 (basic, expression, html, markdown, mermaid, llm_prompt, img_gen_prompt)

## MkDocs Configuration — Available Features

The `mkdocs.yml` configures specific plugins and markdown extensions. Use these features when writing pages — but do not use features that are NOT configured.

### Markdown Extensions (available)

| Extension | What it enables | Syntax example |
|-----------|----------------|----------------|
| `admonition` | Callout boxes | `!!! note "Title"` / `!!! tip` / `!!! warning` |
| `pymdownx.details` | Collapsible admonitions | `??? note "Click to expand"` / `???+ note "Open by default"` |
| `pymdownx.tabbed` | Content tabs | `=== "Tab 1"` / `=== "Tab 2"` (with `alternate_style: true`) |
| `attr_list` | CSS classes & attributes on elements | `{ .md-grid .cards }`, `{ .annotate }` |
| `md_in_html` | Markdown inside HTML blocks | `<div markdown>` ... `</div>` |
| `pymdownx.highlight` | Code syntax highlighting (Pygments) | ` ```toml ` / ` ```python ` / ` ```bash ` |
| `pymdownx.superfences` | Fenced code blocks + **mermaid diagrams** | ` ```mermaid ` for diagrams |
| `pymdownx.snippets` | File includes | `--8<-- "CONTRIBUTING.md"` (base path: repo root) |
| `pymdownx.blocks.caption` | Figure captions | `/// caption` blocks |
| `pymdownx.emoji` | Emoji via twemoji | `:material-check:`, `:octicons-alert-16:` |
| `meta` | YAML front matter | `title:`, `description:` at top of page |
| `sane_lists` | Stricter list parsing | Requires consistent indentation |

### Extensions NOT configured (do not use)

- `pymdownx.tasklist` — no checkbox lists
- `pymdownx.arithmatex` — no math/LaTeX

### Plugins (available)

| Plugin | What it does |
|--------|-------------|
| `search` | Full-text search |
| `meta-manager` | Default metadata from `.meta.yml` files |
| `glightbox` | Lightbox for images (click to zoom) |
| `privacy` | Downloads external assets locally (GDPR) and applies `links_attr_map` (e.g., `target: _blank` on external links) |
| `llmstxt-md` | Generates `llms.txt` for LLM-friendly content — nav sections must be updated when adding pages |

### Theme Features (from `mkdocs.yml` theme config)

- `navigation.tabs` + `navigation.tabs.sticky` — top-level nav sections render as tabs
- `navigation.sections` — left sidebar groups pages under section headers
- `navigation.footer` — prev/next links in footer
- `navigation.top` — back-to-top button
- `content.code.copy` — copy button on code blocks

### MkDocs Markdown Rules

- Always add a blank line before any bullet lists or numbered lists
- Use `toml` as the code block language for `.mthds` and `METHODS.toml` snippets
- Use Material grid cards syntax (`attr_list` + `md_in_html`) for the landing page entry points
- Mermaid diagrams use ` ```mermaid ` fenced blocks (supported via `superfences` custom fence)
- File includes use `--8<-- "path"` syntax (base path is repo root, `check_paths: true` is on — missing files will fail the build)
- Ensure all internal links use relative paths between docs pages
- After making changes, always run `make docs-check` to verify the build passes with `--strict`
- When adding or moving pages, update BOTH the `nav:` section AND the `llmstxt-md` plugin `sections:` in `mkdocs.yml`
- `make docs-check` runs `mkdocs build --strict` — any warning (broken links, missing nav targets) becomes a build error

## General Rules

- **Do not reinvent the wheel.** Before writing custom JS, CSS, or template overrides, always search for an existing MkDocs plugin or Material theme feature that solves the problem. Only write custom code if no plugin or built-in option exists.

## Existing Files (do not overwrite)

These files already exist and should not be replaced:

- `docs/404.html`, `docs/404.md` — custom 404 page
- `docs/CNAME` — domain configuration
- `docs/images/favicon-32.png` — favicon
- `docs/overrides/main.html` — OpenGraph meta tags
- `docs/stylesheets/general.css` — custom color theme
- `docs/stylesheets/mermaid.css` — mermaid diagram styles
- `docs/.meta.yml` — default metadata
- `docs/changelog.md`, `docs/license.md` — existing content pages
- `docs/contributing.md` — repo contribution guide (uses snippet include `--8<-- "CONTRIBUTING.md"`)
- `docs/about/contributing.md` — contributing to the MTHDS *standard* (standalone content, different purpose)

