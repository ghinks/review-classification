# Review Classification

A CLI tool to identify pull request outliers in GitHub repositories based on review time, size, and qualitative metrics. This tool helps engineering teams understand review patterns and identify unusual PRs that might need attention.

## Features

*   **Fetch & Store**: efficiently retrieve PR data from GitHub (handling rate limits) and store locally in a SQLite database.
*   **Outlier Detection**: Detect statistical outliers using Z-score analysis on multiple metrics (review duration, size, comments, etc.).
*   **Analysis**: Calculate rich features like code churn, comment density, and review speed.
*   **Flexible Output**: view results in the terminal as tables, or export to JSON/CSV for further analysis.

## Installation

**Prerequisites**:
*   Python 3.12 or higher
*   [uv](https://github.com/astral-sh/uv) (recommended for dependency management)

### Setup

1.  Clone the repository:
    ```bash
    git clone https://github.com/ghinks/review-classification.git
    cd review-classification
    ```

2.  Install dependencies:
    ```bash
    uv sync
    ```

## Usage

### 1. Configure GitHub Token

To avoid rate limits, you must set a GitHub personal access token:

```bash
export GITHUB_TOKEN=your_token_here
```

### 2. Classify (Fetch Data)

The `classify` command fetches PR data from a repository and stores it locally.

```bash
# Fetch all PRs
uv run review-classify classify owner/repo

(default start date is 30 days ago)

# Fetch PRs within a specific date range
uv run review-classify classify owner/repo --start 2023-01-01 --end 2023-12-31

# Reset the local database before fetching
uv run review-classify classify owner/repo --reset-db
```

### 3. Detect Outliers

The `detect-outliers` command analyzes the stored data to find unusual PRs.

```bash
# Basic outlier detection (default threshold: 2.0)
uv run review-classify detect-outliers owner/repo

# rigorous detection (higher threshold)
uv run review-classify detect-outliers owner/repo --threshold 3.0

# Export results to JSON
uv run review-classify detect-outliers owner/repo --format json > outliers.json
```

## Development

### Setup

Install dev dependencies:
```bash
uv sync --group dev
```

### Running Tests

Run the test suite with pytest:
```bash
uv run pytest
```

### Linting & Formatting

This project uses `ruff` for linting and formatting and `mypy` for static type checking.

```bash
# Run pre-commit hooks on all files
uv run pre-commit run --all-files
```
