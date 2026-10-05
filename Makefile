PYTHON ?= python

.PHONY: format check test

format:
	$(PYTHON) -m ruff check src tests --select I --fix
	$(PYTHON) -m black src tests

check:
	$(PYTHON) -m black --check src tests
	$(PYTHON) -m ruff check src tests

test:
	$(PYTHON) -m pytest -q
