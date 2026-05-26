---
name: BRANCHING_AND_PR_CREATION
description: >-
  Detailed instructions for branching, local code quality validation, git commits,
  and creating structured, high-quality pull requests using the GitHub CLI (gh).
---

# Branching and PR Creation

This skill defines the standard workflow for creating branches, committing changes, validating code quality locally, and creating structured pull requests (PRs) in the `review-classification` repository.

## Prerequisites

1.  **Git**: Installed and configured.
2.  **GitHub CLI (`gh`)**: Installed and authenticated to the target repository.
3.  **`uv`**: Installed and on PATH for running tests and linters.
4.  **`pre-commit`**: Installed and set up (run `uv run pre-commit install` if not already done).

## Workflows

### 1. Branch Naming & Creation

Always create a new branch for your work, branching off the latest `main` branch.

- **Naming Conventions**: Use descriptive names prefixed by the type of work:
  - `feat/` or `feature/` for new features (e.g., `feat/add-html-report`)
  - `fix/` for bug fixes (e.g., `fix/sqlite-handling`)
  - `perf/` for performance optimizations (e.g., `perf/db-bulk-writes`)
  - `refactor/` for code refactoring (e.g., `refactor/rename-helpers`)
  - `docs/` for documentation updates (e.g., `docs/pypi-instructions`)
  - `chore/` for maintenance and setup tasks (e.g., `chore/dependency-bump`)

- **Creation Workflow**:
  ```bash
  # Step 1: Switch to main branch
  git checkout main
  # Step 2: Fetch and pull the latest changes
  git fetch origin && git pull origin main
  # Step 3: Create and switch to the new branch
  git checkout -b <type>/<description>
  ```

### 2. Local Validation (Before Committing/Pushing)

Before pushing any changes or creating a PR, you MUST ensure that all local validation checks pass. This keeps the CI pipeline green and ensures code consistency.

-   **Step 2.1: Formatting and Linting (Ruff)**
    Check and auto-fix lint errors and formatting.
    ```bash
    uv run ruff check --fix
    uv run ruff format
    ```

-   **Step 2.2: Strict Type Checking (Mypy)**
    Ensure there are no typing errors.
    ```bash
    uv run mypy src tests
    ```

-   **Step 2.3: Unit Testing (Pytest)**
    Run the unit test suite (excluding slow integration tests by default).
    ```bash
    uv run pytest -m "not integration"
    ```

-   **Step 2.4: Integration Testing (Pytest - Optional but Recommended)**
    If your changes affect database, network, or end-to-end functionality, run the integration tests.
    ```bash
    uv run pytest
    ```

### 3. Git Commits

Follow the **Conventional Commits** format for commit messages. Keep commits focused and atomic.

- **Format**: `<type>(<scope>): <short description>`
  - Example: `feat(cli): add typer-based cli with repository parser`
  - Example: `fix(db): handle transaction rollback on insertion failure`
- **Steps**:
  ```bash
  # Stage files
  git add <files>
  # Commit with message
  git commit -m "feat(cli): add typer-based cli with repository parser"
  ```

### 4. PR Creation

Create the pull request using the GitHub CLI (`gh`). The PR body must be rich and detailed, matching the project standards.

> [!IMPORTANT]
> To prevent the `gh` CLI command from blocking/hanging in interactive mode, always pass the title and body explicitly using arguments or use the `--fill` flag.

- **PR Creation Command**:
  ```bash
  gh pr create --title "<title>" --body "<body>"
  ```

- **PR Body Template**:
  The body should follow this structure:
  ```markdown
  ## Summary

  [Provide a concise explanation of what this PR does and why.]

  ## Changes

  ### [Component/Module Name, e.g., CLI]
  - **file_name.py**: [Brief summary of modifications in this file]
  - **another_file.py**: [Brief summary of modifications in this file]

  ## Testing

  - [ ] Linting checks passed (`uv run ruff check`) ✅
  - [ ] Formatting checks passed (`uv run ruff format`) ✅
  - [ ] Strict type checks passed (`uv run mypy src tests`) ✅
  - [ ] Unit tests passed (`uv run pytest -m "not integration"`) ✅
  - [ ] Integration tests passed (`uv run pytest`) ✅

  ## Usage Examples

  ```bash
  # Provide commands to demonstrate/test the new functionality
  review-classify owner/repo --verbose
  ```

  ## Next Steps

  - [Describe any follow-up tasks, unresolved questions, or future improvements.]
  ```

## Common Mistakes & Solutions

- **Mistake**: PR creation command hangs.
  - **Solution**: Avoid running `gh pr create` without arguments. Always provide `--title` and `--body` (or `--body-file` / `--fill`) to skip interactive prompts.
- **Mistake**: Pushing code with typing errors or failing tests.
  - **Solution**: Always run the **Local Validation** steps before pushing.
- **Mistake**: Branch name has no category prefix.
  - **Solution**: Rename the branch locally using `git branch -m <new-name>` and delete the incorrect remote branch if pushed.
