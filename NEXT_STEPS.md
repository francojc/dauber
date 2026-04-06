# dauber — Setup Next Steps

Pick up this session from `~/.local/cli/dauber` and execute in order.

## 1. Rename package directory

```bash
mv src/easel src/dauber
```

## 2. Bulk rename all `easel` references

```bash
find src/ tests/ -name "*.py" -exec sed -i 's/easel/dauber/g' {} +
sed -i 's/easel/dauber/g' pyproject.toml flake.nix README.md CHANGELOG.md
```

## 3. Update `pyproject.toml`

Replace the `[project]` block with:

```toml
[project]
name = "dauber"
version = "0.1.8"
description = "Command-line interface for the Canvas LMS API"
readme = "README.md"
license = "MIT"
authors = [
  { name = "Jerid Francom", email = "francojc@wfu.edu" },
]
keywords = ["canvas", "lms", "cli", "grading", "courses", "academic", "teaching"]
classifiers = [
  "Development Status :: 4 - Beta",
  "Environment :: Console",
  "Intended Audience :: Education",
  "License :: OSI Approved :: MIT License",
  "Programming Language :: Python :: 3",
  "Programming Language :: Python :: 3.11",
  "Programming Language :: Python :: 3.12",
  "Topic :: Education",
  "Topic :: Utilities",
]
requires-python = ">=3.11"
```

And add after the `[project]` block (before `[project.scripts]`):

```toml
[project.urls]
Homepage = "https://github.com/francojc/dauber"
Repository = "https://github.com/francojc/dauber"
Changelog = "https://github.com/francojc/dauber/blob/main/CHANGELOG.md"
```

And update the scripts and hatch target:

```toml
[project.scripts]
dauber = "dauber.cli.app:main"

[tool.hatch.build.targets.wheel]
packages = ["src/dauber"]
```

## 4. Create `LICENSE`

Create `LICENSE` at repo root with MIT text (year 2025, name Jerid Francom).

## 5. Create `justfile`

```just
# justfile — dauber development workflow
# Requires: just, nix (with flakes), uv
# Entry point: `nix develop` (or direnv with `use flake .`) then `just <recipe>`

default:
  @just --list

# ── Setup ──────────────────────────────────────────────────────────────────────

# Install all dependencies and editable package into .venv
setup:
  uv sync
  @echo "Run 'uv run dauber --help' to verify."

# Install dauber as a tool (production-style, not editable)
install:
  uv tool install .

# Install dauber as an editable tool (changes take effect immediately)
install-dev:
  uv tool install --editable .

# ── Development ────────────────────────────────────────────────────────────────

# Run dauber (pass args after --: just run -- courses list)
run *args:
  uv run dauber {{ args }}

# Open a Python REPL with dauber on the path
repl:
  uv run python

# ── Code quality ───────────────────────────────────────────────────────────────

# Format source files with ruff
fmt:
  uv run ruff format src/ tests/

# Lint source files with ruff (auto-fix safe issues)
lint:
  uv run ruff check --fix src/ tests/

# Check formatting and lint without modifying files (CI-safe)
check:
  uv run ruff format --check src/ tests/
  uv run ruff check src/ tests/

# Run pyright type checks
types:
  uv run pyright src/

# Run all code quality checks (fmt + lint + types)
qa: check types

# ── Testing ────────────────────────────────────────────────────────────────────

# Run the full test suite
test:
  uv run pytest

# Run tests with verbose output
test-v:
  uv run pytest -v

# Run only unit tests (exclude integration)
test-unit:
  uv run pytest tests/ -m "not integration"

# Run tests with coverage report
cov:
  uv run pytest --cov=src/dauber --cov-report=term-missing

# Run tests for a single module (e.g.: just test-mod test_courses)
test-mod mod:
  uv run pytest tests/{{ mod }}.py -v

# ── Build & release ────────────────────────────────────────────────────────────

# Build a distributable wheel and sdist
build:
  uv build

# Publish to PyPI (requires UV_PUBLISH_TOKEN env var)
publish:
  uv publish

# Tag and create a GitHub Release (triggers CI publish to PyPI)
release:
  #!/usr/bin/env bash
  set -euo pipefail
  version=$(grep '^version' pyproject.toml | head -1 | sed 's/.*= *"\(.*\)"/\1/')
  tag="v${version}"
  echo "Releasing ${tag}..."
  git tag "${tag}"
  git push origin "${tag}"
  gh release create "${tag}" --title "${tag}" --generate-notes
  echo "Done — CI will publish to PyPI automatically."

# ── Nix ────────────────────────────────────────────────────────────────────────

# Update flake.lock to latest nixpkgs
update:
  nix flake update

# ── Utilities ──────────────────────────────────────────────────────────────────

# Remove build artifacts and caches
clean:
  rm -rf dist/ build/ .pytest_cache/ .ruff_cache/ .pyright/ htmlcov/ coverage.xml
  find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
  find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
  @echo "Cleaned."

# Wipe and reinstall the .venv (useful after dependency conflicts)
reset: clean
  rm -rf .venv
  uv sync
  @echo "Environment reset."

# Show all installed package versions
deps:
  uv pip list

# Run dauber doctor to check connectivity and credentials
doctor:
  uv run dauber doctor

# Run dauber init to configure credentials interactively
init:
  uv run dauber init
```

## 6. Create `.github/workflows/ci.yml`

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
  release:
    types: [published]

jobs:
  lint:
    name: Lint
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
        with:
          enable-cache: true
      - run: uv sync --group dev
      - run: uv run ruff format --check src/ tests/
      - run: uv run ruff check src/ tests/

  typecheck:
    name: Type check
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
        with:
          enable-cache: true
      - run: uv sync --group dev
      - run: uv run pyright src/

  test:
    name: Test (Python ${{ matrix.python-version }})
    runs-on: ubuntu-latest
    strategy:
      fail-fast: false
      matrix:
        python-version: ["3.11", "3.12"]
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
        with:
          enable-cache: true
          python-version: ${{ matrix.python-version }}
      - run: uv sync --group dev
      - run: uv run pytest --tb=short -q

  build:
    name: Build
    runs-on: ubuntu-latest
    needs: [lint, typecheck, test]
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
        with:
          enable-cache: true
      - run: uv build
      - name: Check wheel installs and --version works
        run: |
          uv tool install dist/*.whl
          dauber --version
      - uses: actions/upload-artifact@v4
        with:
          name: dist
          path: dist/

  publish:
    name: Publish to PyPI
    runs-on: ubuntu-latest
    needs: [build]
    if: github.event_name == 'release'
    environment: pypi
    permissions:
      id-token: write
    steps:
      - uses: actions/download-artifact@v4
        with:
          name: dist
          path: dist/
      - uses: astral-sh/setup-uv@v5
      - run: uv publish --trusted-publishing always
```

## 7. Add badges to `README.md`

Add after the `# dauber` heading:

```markdown
[![CI](https://github.com/francojc/dauber/actions/workflows/ci.yml/badge.svg)](https://github.com/francojc/dauber/actions/workflows/ci.yml)
[![PyPI version](https://img.shields.io/pypi/v/dauber)](https://pypi.org/project/dauber/)
[![Python versions](https://img.shields.io/pypi/pyversions/dauber)](https://pypi.org/project/dauber/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
```

## 8. Verify, build, commit, push

```bash
uv run dauber --help          # confirm CLI works
uv run pytest --tb=short -q   # confirm tests pass
uv build                      # confirm wheel + sdist build
git add -A
git commit -m "chore(publish): rename to dauber; add PyPI metadata, CI, justfile"
git push
```

## 9. First publish

```bash
just publish   # uses UV_PUBLISH_TOKEN from shell env
```

## 10. PyPI trusted publisher (for future CI auto-publish)

Go to: https://pypi.org/manage/account/publishing/
Add trusted publisher:
- Owner: francojc
- Repo: dauber
- Workflow: ci.yml
- Environment: pypi

## 11. Future releases

```bash
# bump version in pyproject.toml + update CHANGELOG.md, then:
git commit -am "chore(release): bump version to vX.Y.Z"
git push
just release
```
