ifeq ($(wildcard .env),.env)
include .env
export
endif
VIRTUAL_ENV := $(CURDIR)/.venv
export PATH := $(VIRTUAL_ENV)/bin:$(PATH)
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
    $(eval TARGET_PART := $@)
    $(eval MESSAGE_PART := $(1))
    $(if $(MESSAGE_PART),\
        $(eval FULL_TITLE := === $(PROJECT_PART) ===== $(TARGET_PART) ====== $(MESSAGE_PART) ),\
        $(eval FULL_TITLE := === $(PROJECT_PART) ===== $(TARGET_PART) ====== )\
    )
    $(eval TITLE_LENGTH := $(shell printf '%s' '$(FULL_TITLE)' | wc -c | tr -d ' '))
    $(eval PADDING_LENGTH := $(shell echo $$((126 - $(TITLE_LENGTH)))))
    $(eval PADDING := $(shell printf '%*s' $(PADDING_LENGTH) '' | tr ' ' '='))
    $(eval PADDED_TITLE := $(FULL_TITLE)$(PADDING))
    @echo ""
    @echo '$(PADDED_TITLE)'
endef

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
make docs-build-versioned             - Build versioned docs with mike (local gh-pages only, no push)
make docs-assemble-site               - Extract gh-pages content + root assets into site-output/
make docs-build-site                  - Full pipeline: build versioned + assemble (for local dev)
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
	docs-deploy docs-build-versioned docs-assemble-site docs-build-site docs-delete \
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
	$(call PRINT_TITLE,Ensuring uv >= $(UV_MIN_VERSION))
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
	$(call PRINT_TITLE,Creating virtual environment)
	@if [ ! -d $(VIRTUAL_ENV) ]; then \
		echo "Creating Python virtual env in \`${VIRTUAL_ENV}\`"; \
		uv venv $(VIRTUAL_ENV) --python $(PYTHON_VERSION); \
	else \
		echo "Python virtual env already exists in \`${VIRTUAL_ENV}\`"; \
	fi

install: env-verbose
	$(call PRINT_TITLE,Installing dependencies)
	@. $(VIRTUAL_ENV)/bin/activate && \
	uv sync && \
	echo "Installed dependencies in ${VIRTUAL_ENV}";

lock: env
	$(call PRINT_TITLE,Resolving dependencies without update)
	@uv lock && \
	echo "uv lock without update";

update: env-verbose
	$(call PRINT_TITLE,Updating all dependencies)
	@uv lock --upgrade && \
	uv sync && \
	echo "Updated dependencies in ${VIRTUAL_ENV}";


##############################################################################################
############################      Cleaning                        ############################
##############################################################################################

cleanderived:
	$(call PRINT_TITLE,Erasing derived files and directories)
	@find . -type d -name 'site' -maxdepth 1 -exec rm -rf {} + && \
	echo "Cleaned up derived files and directories";

cleanenv:
	$(call PRINT_TITLE,Erasing virtual environment)
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
	$(call PRINT_TITLE,Serving documentation with mkdocs)
	$(VENV_MKDOCS) serve -a 127.0.0.1:8000 -f "$(CURDIR)/mkdocs.yml" --watch "$(CURDIR)/docs" -s

docs-check: env
	$(call PRINT_TITLE,Checking documentation build with mkdocs)
	$(VENV_MKDOCS) build --strict

docs-serve-versioned: env
	$(call PRINT_TITLE,Serving versioned documentation with mike)
	$(VENV_MIKE) serve

docs-list: env
	$(call PRINT_TITLE,Listing deployed documentation versions)
	$(VENV_MIKE) list

docs-deploy: env
	$(call PRINT_TITLE,Deploying documentation version $(if $(VERSION),$(VERSION),$(DOCS_VERSION)))
	$(VENV_MIKE) deploy $(if $(VERSION),$(VERSION),$(DOCS_VERSION))

docs-build-versioned: env
	$(call PRINT_TITLE,Building versioned docs with mike -- local gh-pages only)
	$(VENV_MIKE) deploy --update-aliases --alias-type copy $(DOCS_VERSION) latest
	$(VENV_MIKE) set-default latest

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
	echo "Site output ready in site-output/"

docs-build-site: docs-build-versioned docs-assemble-site
	@echo "Complete site ready in site-output/. Run 'vercel dev' to preview locally."

docs-delete: env
	@if [ -z "$(VERSION)" ]; then echo "ERROR: VERSION is required. Usage: make docs-delete VERSION='x.y.z x.y.z ...'"; exit 1; fi
	$(call PRINT_TITLE,Deleting documentation versions: $(VERSION))
	$(VENV_MIKE) delete --push $(VERSION)


##########################################################################################
### SHORTHANDS
##########################################################################################

update-schema:
	$(call PRINT_TITLE,Downloading latest JSON Schema)
	curl -fSL "$(SCHEMA_URL)" -o "$(CURDIR)/docs/mthds_schema.json"

up: update-schema
	@echo "> done: update-schema"

li: lock install
	@echo "> done: lock install"
