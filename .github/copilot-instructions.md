# Repository instructions for GitHub Copilot

Trust these instructions first and only search the repository when the information here is missing or clearly outdated.

## Project overview

This repository is a small Python 3.12 CLI application that identifies unusual pull requests using GitHub review data and Z-score analysis. The published command is `review-classify`, and the main package lives in `src/review_classification`.

## Working conventions

- Use `uv` for dependency management, running commands, and building packages.
- Keep changes aligned with the existing Typer-based CLI, SQLModel-based persistence, and pytest test suite.
- Prefer extending existing modules over introducing new top-level patterns or dependencies.
- Preserve current user-facing CLI behavior and option names unless the task explicitly requires a change.

## Key paths

- `pyproject.toml`: project metadata, dependencies, Ruff, mypy, pytest, and the `review-classify` entry point.
- `src/review_classification/main.py`: CLI entry point.
- `src/review_classification/cli/`: command wiring, parsing, config, and output formatting.
- `src/review_classification/analysis/`: outlier detection and analysis logic.
- `src/review_classification/sqlite/` and `src/review_classification/queries/`: local SQLite storage and query logic.
- `tests/`: unit and integration tests.
- `.github/workflows/ci.yml`: CI runs Ruff, mypy, and pytest.

## Setup and validation

Bootstrap with:

```bash
uv sync --group dev
```

Use these commands when changing code:

```bash
uv run pytest -m "not integration"
uv run pre-commit run --all-files
```

Use the full suite when appropriate:

```bash
uv run pytest
```

Integration tests require a valid `GITHUB_TOKEN` or an authenticated `gh` CLI session because they call the real GitHub API.

## Running the CLI

```bash
uv run review-classify --help
uv run review-classify fetch --repo owner/repo
uv run review-classify classify --repo owner/repo
```

You can also run the module directly with:

```bash
uv run -m review_classification.main
```

## Behavior to preserve

- Classification is repository-scoped; do not mix baselines across repositories.
- Multi-repository classification output is deferred until all repositories finish processing.
- Repositories that cannot be classified should produce a concise summary reason instead of partial per-repo output.
