# PR outliers

This document describes an approach to find pull requests (PRs)
merged within a date range and identify which ones are outliers based
on review time and qualitative review data.

## Tools and environment

- Language: Python
- Dependency manager: `uv`
- Linter: `ruff`
- Static type checker: `mypy`
- CI/CD: GitHub Actions
- Pre-commit / CI checks: run `ruff` and `mypy` as pre-commit hooks
  and in the pipeline for each PR

## Goals

- Classify PRs that were merged within a specified date range.
- Identify outlier PR reviews.
- Cache PR data to a local SQLite database.
- Handle GitHub rate limiting with a backoff/wait mechanism.
- Request multiple PRs concurrently.
- Use Claude code as an AI assistant.
- Use MCP agents for the local GitHub and the local SQLite repo.

## Outlier definition

An outlier review is a PR that may need more attention. Examples of
outlier conditions include:

- A PR that is reviewed unusually quickly.
- A PR with a large number of changes.
- A PR with high complexity.
- A PR with no comments.
- A PR that contains code changes but no unit tests.

Outliers should be identified automatically based on the criteria
available from GitHub PR review data.

## Z-score calculation

- Use Z-score calculation to identify statistical outliers for
  numeric metrics (for example, review time or number of changes).

## Additional work

- Allow specifying the period of classification by a date range that
  excludes the measurement period for PR reviews.
- Support running against a GitHub organization.
- Support running against specific repositories using the
  `org/repo` form from the command line and a configuration file.

## Model classification

- Investigate using AI (LLMs) to classify PRs as outliers in addition
  to traditional statistical methods.
- Explore using Z-score identified outliers as training data for an
  LLM or boutique model.
- Research other existing tools and approaches in this space to learn
  from.

## New requirements 20260308

### Step 1 — Fetch PR data with improved CLI argument names

- Replace the current `start` and `end` CLI arguments with more
  descriptive names that reflect their roles (for example:
  `collate-start`, `collate-end`).
- Discuss and decide on clear, consistent naming for the fetch
  command arguments across the CLI.

### Step 2 — Add a new CLI command to classify PRs

- Add a dedicated `classify` command that operates on previously
  fetched data.
- Discuss the preferred naming for the classify date arguments
  (for example: `classify-start`, `classify-end`).

### Step 3 — Defer printing results until the end of the workflow

- Do not print per-repo results as they are produced.
- After all repositories have been processed, print results for
  repos that could be classified.
- For repositories that could not be classified (insufficient data or
  other issues), print a single summary line explaining the reason.

### Step 4 — Add CLI argument to select only PRs not merged back into
### the primary branch

- Add a flag (for example, `--exclude-primary-merged` or
  `--only-non-primary-merged`) to include only PRs that were not
  merged back into the primary branch in the classification output.
- This helps focus on PRs that may have been abandoned or need
  attention.

<!-- End of reformatted document -->
