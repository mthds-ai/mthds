# Contributing to MTHDS

Thank you for your interest in contributing to the MTHDS specification site. Whether you're clarifying a concept, proposing new content, or fixing an error, your input helps make the standard more accessible to everyone.

Everyone interacting in our community spaces is expected to follow the [Code of Conduct](CODE_OF_CONDUCT.md). Please review it before getting started.

## How to contribute

There are several ways to help improve this site:

- **Content**: New pages, tutorials, examples, and guides that help explain or illustrate the standard
- **Fixes**: Typos, broken links, unclear explanations
- **Structure**: Navigation improvements, better organization
- **Style**: CSS tweaks, theme customization

## Requirements

- Python >= 3.10
- uv >= 0.7.2

## Local setup

1. Fork & clone the repository
2. Run `make install` to set up the virtualenv and install dependencies
3. Run `make docs` to serve the site locally at `http://127.0.0.1:8000`
4. Edit files in the `docs/` directory — changes will auto-reload in your browser

The site is built on the Python version that `.python-version` names at the repository root, and the documentation workflows read the same file. `make install` builds `.venv` on that version, and the next `make install`, which `make docs-check` also runs, moves an environment built on another Python to it. To try another version, run `PYTHON_VERSION=3.12 make install`; the next plain `make install` returns the environment to the pinned version.

## Contribution process

1. Fork the repository
2. Clone it locally
3. Install dependencies: `make install`
4. Serve the site locally: `make docs`
5. Create a branch with the format `username/category/short-description` where category is one of: `content`, `fix`, `structure`, or `style`
6. Make and commit your changes
7. Push your local branch to your fork
8. Open a PR with a clear title and description
9. Respond to feedback if required
