# Makefile for pyfian

.PHONY: help clean build docs test

help:
	@echo "Available targets:"
	@echo "  build     - Build the project (install dependencies)"
	@echo "  clean     - Remove build, coverage, and Python cache files"
	@echo "  docs      - Build documentation using Sphinx"
	@echo "  test      - Run tests using pytest"
	@echo "  coverage  - Run tests with coverage and generate HTML report"

build:
	poetry install

clean:
ifeq (,$(findstring Windows_NT,$(OS)))
	rm -rf htmlcov docs/_build
	find . -type d -name '__pycache__' -exec rm -rf {} +
	find . -type f -name '*.pyc' -delete
else
	rmdir /S /Q htmlcov
	rmdir /S /Q docs\_build
	for /r %%d in (__pycache__) do rmdir /S /Q "%%d"
	for /r %%f in (*.pyc) do del /F /Q "%%f"
endif

# Build documentation
# Assumes Sphinx is set up in docs/
docs:
	cd docs && make html

test:
	poetry run pytest

coverage:
	poetry run pytest --cov=pyfian --cov-report=html tests/
	@echo "Coverage HTML report generated in htmlcov/index.html"
