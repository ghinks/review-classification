# Review Classification

A CLI tool to identify pull request outliers in GitHub repositories using Z-score analysis. Helps engineering teams spot unusual PRs — by size, review duration, comment activity, or code churn — against a stable historical baseline.

## Features

- **Fetch & Store**: retrieve PR data from GitHub (with rate-limit handling) and store it in a local SQLite database.
- **Outlier Detection**: Z-score analysis across multiple metrics — additions, deletions, changed files, comments, review duration, code churn, and comment density.
- **Baseline window**: define a historical measurement period so recent PRs are evaluated against an independent baseline rather than skewing their own statistics.
- **Flexible output**: view results as a terminal table or export to JSON/CSV.

## Installation

### Homebrew (macOS / Linux)

Install via the project's dedicated [Homebrew tap](https://github.com/ghinks/homebrew-review-classification):

```bash
brew install ghinks/review-classification
```

Homebrew automatically taps `ghinks/review-classification` and installs the formula in one step. After installation the `review-classify` command is on your `PATH`.

### From source with uv

**Prerequisites**: Python 3.12+, [uv](https://github.com/astral-sh/uv)

```bash
git clone https://github.com/ghinks/review-classification.git
cd review-classification
uv sync
```

### From PyPI with pipx

```bash
pipx install review-classification
```

## Usage

The tool works in two steps: **fetch** data, then **detect-outliers**.

### 1. Configure GitHub Token

```bash
export GITHUB_TOKEN=your_token_here
```

Without a token the GitHub API rate limit is very low.

### 2. `fetch` — retrieve and store PR data

```bash
# Fetch PRs merged in the last 30 days (default)
uv run review-classify fetch owner/repo

# Fetch PRs within a specific date range
uv run review-classify fetch owner/repo --start 2024-01-01 --end 2024-06-30

# Clear existing data before fetching
uv run review-classify fetch owner/repo --reset-db --start 2024-01-01
```

| Option | Description |
| --- | --- |
| `--start` / `-s` | Start date for PR range (YYYY-MM-DD). Defaults to 30 days ago. |
| `--end` / `-e` | End date for PR range (YYYY-MM-DD). |
| `--reset-db` | Delete all stored data before fetching. |
| `--verbose` / `-v` | Print progress details. |

### 3. `detect-outliers` — find unusual PRs

```bash
# Detect outliers across all stored PRs
uv run review-classify detect-outliers owner/repo

# Stricter threshold (fewer, more extreme outliers)
uv run review-classify detect-outliers owner/repo --threshold 3.0

# Export to JSON
uv run review-classify detect-outliers owner/repo --format json > outliers.json
```

| Option | Description |
| --- | --- |
| `--threshold` / `-t` | Z-score threshold for flagging an outlier. Default: `2.0`. |
| `--min-samples` | Minimum number of PRs required for analysis. Default: `30`. |
| `--format` / `-f` | Output format: `table` (default), `json`, or `csv`. |
| `--classify-start` | Start of the baseline measurement window (YYYY-MM-DD). |
| `--classify-end` | End of the baseline measurement window (YYYY-MM-DD). |
| `--verbose` / `-v` | Print progress details. |

#### Baseline window (`--classify-start` / `--classify-end`)

By default all stored PRs feed both the baseline statistics and the outlier evaluation. This is problematic: an unusually large PR inflates the mean and standard deviation it is measured against, masking itself as normal.

Use `--classify-start` and `--classify-end` to define a historical baseline window. Statistics are computed from PRs merged **within** that window; only PRs merged **after** `--classify-end` are evaluated and reported.

```
[--classify-start ────────── --classify-end]   >classify-end
         ↑                         ↑                 ↑
   baseline start            baseline end     PRs evaluated here
```

```bash
# Use Jan–Jun 2024 as the baseline; evaluate PRs merged after 2024-06-30
uv run review-classify detect-outliers owner/repo \
  --classify-start 2024-01-01 \
  --classify-end   2024-06-30

# Same, with stricter threshold and JSON output
uv run review-classify detect-outliers owner/repo \
  --classify-start 2024-01-01 \
  --classify-end   2024-06-30 \
  --threshold 2.5 \
  --format json > outliers.json
```

### End-to-end example

```bash
# 1. Fetch a full year of history as the baseline
uv run review-classify fetch owner/repo \
  --start 2024-01-01 --end 2024-12-31

# 2. Evaluate PRs from January 2025 against that baseline
uv run review-classify detect-outliers owner/repo \
  --classify-start 2024-01-01 \
  --classify-end   2024-12-31 \
  --format table
```

## Development

### Setup

```bash
uv sync --group dev
```

### Running Tests

```bash
uv run pytest
```

### Linting & Formatting

```bash
# Run ruff (lint + format) and mypy via pre-commit
uv run pre-commit run --all-files
```
