#!make
VERSION := $(shell grep '__version__' src/xdist_scheduling_exclusive/__about__.py | cut -d '"' -f2)
export VERSION
unexport CONDA_PREFIX  # if conda is installed, it will mess with the virtual env

.HELP: version ## Show the current version
version:
	echo ${VERSION}

.HELP: ver-bug ## Bump the version for a bug
ver-bug:
	bash ./scripts/verup.sh bug

.HELP: ver-feature ## Bump the version for a feature
ver-feature:
	bash ./scripts/verup.sh feature

.HELP: ver-release ## Bump the version for a release
ver-release:
	bash ./scripts/verup.sh release

.HELP: reqs  ## Upgrade requirements including pre-commit
reqs:
	pre-commit autoupdate
	bash ./scripts/compile_requirements.sh
	uv pip install -r requirements.dev.txt

.PHONY: docs # mark as phony so it always runs even we have a docs folder
.HELP: docs  ## Docs preview English
docs:
	./scripts/docstrings.sh
	open -a "Google Chrome" http://127.0.0.1:8000/xdist-scheduling-exclusive/
	mkdocs serve -f docs/mkdocs-en.yml

.HELP: docs-ru  ## Docs preview Russian
docs-ru:
	./scripts/docstrings.sh
	open -a "Google Chrome" http://127.0.0.1:8000/xdist-scheduling-exclusive/
	mkdocs serve -f docs/mkdocs-ru.yml

.HELP: help  ## Display this message
help:
	@grep -E \
		'^.HELP: .*?## .*$$' $(MAKEFILE_LIST) | \
		sort | \
		awk 'BEGIN {FS = ".HELP: |## "}; {printf "\033[36m%-19s\033[0m %s\n", $$2, $$3}'
