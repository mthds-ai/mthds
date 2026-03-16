ifeq ($(wildcard .env),.env)
include .env
export
endif
VIRTUAL_ENV := $(CURDIR)/.venv
PROJECT_NAME := $(shell grep '^name = ' pyproject.toml | sed -E 's/name = "(.*)"/\1/')

# The "?" is used to make the variable optional, so that it can be overridden by the user.
PYTHON_VERSION ?= 3.13
VENV_PYTHON := $(VIRTUAL_ENV)/bin/python
VENV_MKDOCS := $(VIRTUAL_ENV)/bin/mkdocs
VENV_MIKE := $(VIRTUAL_ENV)/bin/mike
SCHEMA_URL := https://pipelex-config.s3.amazonaws.com/mthds_schema_latest.json

UV_MIN_VERSION = $(shell grep -m1 'required-version' pyproject.toml | sed -E 's/.*= *"([^<>=, ]+).*/\1/')

# Extract version from pyproject.toml for docs deployment
DOCS_VERSION := $(shell grep -m1 '^version = ' pyproject.toml | sed -E 's/version = "(.*)"/\1/')

define PRINT_TITLE
    $(eval PROJECT_PART := [$(PROJECT_NAME)])
    $(eval TARGET_PART := ($@))
    $(eval MESSAGE_PART := $(1))
    $(if $(MESSAGE_PART),\
        $(eval FULL_TITLE := === $(PROJECT_PART) ===== $(TARGET_PART) ====== $(MESSAGE_PART) ),\
        $(eval FULL_TITLE := === $(PROJECT_PART) ===== $(TARGET_PART) ====== )\
    )
    $(eval TITLE_LENGTH := $(shell echo -n "$(FULL_TITLE)" | wc -c | tr -d ' '))
    $(eval PADDING_LENGTH := $(shell echo $$((126 - $(TITLE_LENGTH)))))
    $(eval PADDING := $(shell printf '%*s' $(PADDING_LENGTH) '' | tr ' ' '='))
    $(eval PADDED_TITLE := $(FULL_TITLE)$(PADDING))
    @echo ""
    @echo "$(PADDED_TITLE)"
endef

define ROOT_ROBOTS_TXT
User-agent: *
Allow: /latest/
Allow: /sitemap.xml
Disallow: /

Sitemap: https://mthds.ai/sitemap.xml
endef
export ROOT_ROBOTS_TXT

define ROOT_INDEX_HTML
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta http-equiv="refresh" content="0;url=/latest/">
<link rel="canonical" href="https://mthds.ai/latest/">
<title>MTHDS</title>
<style>
    body {
        margin: 0;
        min-height: 100vh;
        display: flex;
        align-items: center;
        justify-content: center;
        background: #1a1a1a;
        color: #d4d4d4;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }
    a { color: #e5e5e5; text-decoration: none; }
</style>
</head>
<body>
<p>Redirecting to <a href="/latest/">MTHDS Documentation</a>&#8230;</p>
</body>
</html>
endef
export ROOT_INDEX_HTML

define HELP
Manage $(PROJECT_NAME) located in $(CURDIR).
Usage:

make env                              - Create python virtual env
make lock                             - Refresh uv.lock without updating anything
make install                          - Create local virtualenv & install all dependencies
make update                           - Upgrade dependencies via uv

make docs                             - Serve documentation locally with mkdocs
make docs-check                       - Check documentation build with mkdocs
make docs-serve-versioned             - Serve versioned docs locally with mike
make docs-list                        - List deployed documentation versions
make docs-deploy VERSION=x.y.z       - Deploy docs as version x.y.z (local, no push)
make docs-deploy-stable               - Deploy stable docs with 'latest' alias (CI only)
make docs-deploy-specific-version     - Deploy docs for the current version with 'pre-release' alias (CI only)
make docs-deploy-root                 - Deploy root assets (404, robots.txt, index redirect, JSON Schema) to gh-pages
make docs-delete VERSION=x.y.z       - Delete a deployed documentation version

make cleanenv                         - Remove virtual env
make cleanderived                     - Remove mkdocs build output
make cleanall                         - Remove all -> cleanenv + cleanderived
make reinstall                        - Reinstall dependencies

make update-schema                    - Download latest JSON Schema from S3
make up                               - Shorthand -> update-schema

make li                               - Shorthand -> lock install

endef
export HELP

.PHONY: \
	all help env env-verbose lock install update \
	cleanderived cleanenv cleanall reinstall ri \
	docs docs-check docs-serve-versioned docs-list \
	docs-deploy docs-deploy-stable docs-deploy-specific-version docs-deploy-root docs-delete \
	update-schema up \
	li check-uv check-uv-verbose

all help:
	@echo "$$HELP"


##########################################################################################
### SETUP
##########################################################################################

check-uv:
	@command -v uv >/dev/null 2>&1 || { \
		echo "uv not found – installing latest …"; \
		curl -LsSf https://astral.sh/uv/install.sh | sh; \
	}
	@uv self update >/dev/null 2>&1 || true

check-uv-verbose:
	$(call PRINT_TITLE,"Ensuring uv ≥ $(UV_MIN_VERSION)")
	@command -v uv >/dev/null 2>&1 || { \
		echo "uv not found – installing latest …"; \
		curl -LsSf https://astral.sh/uv/install.sh | sh; \
	}
	@uv self update >/dev/null 2>&1 || true

env: check-uv
	@if [ ! -d $(VIRTUAL_ENV) ]; then \
		echo "Creating Python virtual env in \`${VIRTUAL_ENV}\`"; \
		uv venv $(VIRTUAL_ENV) --python $(PYTHON_VERSION); \
	fi

env-verbose: check-uv-verbose
	$(call PRINT_TITLE,"Creating virtual environment")
	@if [ ! -d $(VIRTUAL_ENV) ]; then \
		echo "Creating Python virtual env in \`${VIRTUAL_ENV}\`"; \
		uv venv $(VIRTUAL_ENV) --python $(PYTHON_VERSION); \
	else \
		echo "Python virtual env already exists in \`${VIRTUAL_ENV}\`"; \
	fi

install: env-verbose
	$(call PRINT_TITLE,"Installing dependencies")
	@. $(VIRTUAL_ENV)/bin/activate && \
	uv sync && \
	echo "Installed dependencies in ${VIRTUAL_ENV}";

lock: env
	$(call PRINT_TITLE,"Resolving dependencies without update")
	@uv lock && \
	echo "uv lock without update";

update: env-verbose
	$(call PRINT_TITLE,"Updating all dependencies")
	@uv lock --upgrade && \
	uv sync && \
	echo "Updated dependencies in ${VIRTUAL_ENV}";


##############################################################################################
############################      Cleaning                        ############################
##############################################################################################

cleanderived:
	$(call PRINT_TITLE,"Erasing derived files and directories")
	@find . -type d -name 'site' -maxdepth 1 -exec rm -rf {} + && \
	echo "Cleaned up derived files and directories";

cleanenv:
	$(call PRINT_TITLE,"Erasing virtual environment")
	@find . -type d -wholename './.venv' -exec rm -rf {} + && \
	echo "Cleaned up virtual env";

reinstall: cleanenv install
	@echo "Reinstalled dependencies";

ri: reinstall
	@echo "> done: ri = reinstall"

cleanall: cleanderived cleanenv
	@echo "Cleaned up all derived files and directories";


##########################################################################################
### DOCUMENTATION
##########################################################################################

docs: env
	$(call PRINT_TITLE,"Serving documentation with mkdocs")
	$(VENV_MKDOCS) serve -a 127.0.0.1:8000 -f "$(CURDIR)/mkdocs.yml" --watch "$(CURDIR)/docs" -s

docs-check: env
	$(call PRINT_TITLE,"Checking documentation build with mkdocs")
	$(VENV_MKDOCS) build --strict

docs-serve-versioned: env
	$(call PRINT_TITLE,"Serving versioned documentation with mike")
	$(VENV_MIKE) serve

docs-list: env
	$(call PRINT_TITLE,"Listing deployed documentation versions")
	$(VENV_MIKE) list

docs-deploy: env
	$(call PRINT_TITLE,"Deploying documentation version $(if $(VERSION),$(VERSION),$(DOCS_VERSION))")
	$(VENV_MIKE) deploy $(if $(VERSION),$(VERSION),$(DOCS_VERSION))

docs-deploy-stable: env
	$(call PRINT_TITLE,"Deploying stable documentation $(DOCS_VERSION) with latest alias")
	$(VENV_MIKE) deploy --push --update-aliases --alias-type copy $(DOCS_VERSION) latest
	$(VENV_MIKE) set-default --push latest
	$(MAKE) docs-deploy-root

docs-deploy-specific-version: env
	$(call PRINT_TITLE,"Deploying documentation $(DOCS_VERSION) with pre-release alias")
	$(VENV_MIKE) deploy --push --update-aliases --alias-type copy $(DOCS_VERSION) pre-release
	$(MAKE) docs-deploy-root

docs-deploy-root:
	$(call PRINT_TITLE,"Deploying root assets to gh-pages: 404 + robots.txt + index redirect + JSON Schema")
	@git fetch origin gh-pages:gh-pages 2>/dev/null || true; \
	TMPDIR=$$(mktemp -d); \
	trap "cd '$(CURDIR)'; git worktree remove '$$TMPDIR' 2>/dev/null || true; rm -rf '$$TMPDIR'" EXIT; \
	git worktree add "$$TMPDIR" gh-pages && \
	cp docs/404.html "$$TMPDIR/404.html" && \
	cp docs/mthds_schema.json "$$TMPDIR/mthds_schema.json" && \
	echo "$$ROOT_ROBOTS_TXT" > "$$TMPDIR/robots.txt" && \
	echo "$$ROOT_INDEX_HTML" > "$$TMPDIR/index.html" && \
	if [ -f "$$TMPDIR/latest/sitemap.xml" ]; then \
		sed 's|<loc>https://mthds.ai/[^/]*/|<loc>https://mthds.ai/latest/|g' \
			"$$TMPDIR/latest/sitemap.xml" > "$$TMPDIR/sitemap.xml"; \
	fi && \
	cd "$$TMPDIR" && \
	git add 404.html robots.txt index.html mthds_schema.json && \
	if [ -f sitemap.xml ]; then git add sitemap.xml; fi && \
	(git diff --cached --quiet || git commit -m "Update root assets (404.html, robots.txt, index.html, sitemap.xml, mthds_schema.json)") && \
	git push origin gh-pages

docs-delete: env
	@if [ -z "$(VERSION)" ]; then echo "ERROR: VERSION is required. Usage: make docs-delete VERSION=x.y.z"; exit 1; fi
	$(call PRINT_TITLE,"Deleting documentation version $(VERSION)")
	$(VENV_MIKE) delete --push $(VERSION)


##########################################################################################
### SHORTHANDS
##########################################################################################

update-schema:
	$(call PRINT_TITLE,"Downloading latest JSON Schema")
	curl -fSL "$(SCHEMA_URL)" -o "$(CURDIR)/docs/mthds_schema.json"

up: update-schema
	@echo "> done: update-schema"

li: lock install
	@echo "> done: lock install"
