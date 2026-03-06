# Review Classification

A CLI tool to identify pull request outliers in GitHub repositories using Z-score analysis. Helps engineering teams spot unusual PRs — by size, review duration, comment activity, or code churn — against a stable historical baseline.

## Features

- **Fetch & Store**: retrieve PR data from GitHub (with rate-limit handling) and store it in a local SQLite database.
- **Outlier Detection**: Z-score analysis across multiple metrics — additions, deletions, changed files, comments, review duration, code churn, and comment density.
- **Baseline window**: define a historical measurement period so recent PRs are evaluated against an independent baseline rather than skewing their own statistics.
- **Flexible output**: view results as a terminal table or export to JSON/CSV.

## Installation

**Prerequisites**: Python 3.12+, [uv](https://github.com/astral-sh/uv)

```bash
git clone https://github.com/ghinks/review-classification.git
cd review-classification
uv sync
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
# Fetch PRs merged in the last 30 days (default) for a specific repo
uv run review-classify fetch --repo owner/repo

# Fetch PRs for an entire organization
uv run review-classify fetch --org your-org

# Fetch PRs within a specific date range
uv run review-classify fetch --repo owner/repo --start 2024-01-01 --end 2024-06-30

# Clear existing data before fetching
uv run review-classify fetch --repo owner/repo --reset-db --start 2024-01-01

# Run fetching using a TOML configuration file
uv run review-classify fetch --config config.toml
```

| Option | Description |
| --- | --- |
| `--repo` / `-r` | GitHub repository (owner/repo). Can be specified multiple times. |
| `--org` / `-o` | GitHub organization. Fetches all repositories in the org. Can be specified multiple times. |
| `--config` / `-c` | Path to a TOML config file defining multiple repositories/organizations. |
| `--start` / `-s` | Start date for PR range (YYYY-MM-DD). Defaults to 30 days ago. |
| `--end` / `-e` | End date for PR range (YYYY-MM-DD). |
| `--reset-db` | Delete all stored data before fetching. |
| `--verbose` / `-v` | Print progress details. |

### 3. `detect-outliers` — find unusual PRs

```bash
# Detect outliers across all stored PRs for a repo
uv run review-classify detect-outliers --repo owner/repo

# Detect outliers for an entire organization
uv run review-classify detect-outliers --org your-org

# Stricter threshold (fewer, more extreme outliers)
uv run review-classify detect-outliers --repo owner/repo --threshold 3.0

# Export to JSON
uv run review-classify detect-outliers --repo owner/repo --format json > outliers.json
```

| Option | Description |
| --- | --- |
| `--repo` / `-r` | GitHub repository (owner/repo). Can be specified multiple times. |
| `--org` / `-o` | GitHub organization. Fetches all repositories in the org. Can be specified multiple times. |
| `--config` / `-c` | Path to a TOML config file defining multiple repositories/organizations. |
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
uv run review-classify detect-outliers --repo owner/repo \
  --classify-start 2024-01-01 \
  --classify-end   2024-06-30

# Same, with stricter threshold and JSON output
uv run review-classify detect-outliers --repo owner/repo \
  --classify-start 2024-01-01 \
  --classify-end   2024-06-30 \
  --threshold 2.5 \
  --format json > outliers.json
```

#### Per-repository analysis

Outlier detection is always **scoped to a single repository**. When you target multiple repositories (via `--org`, multiple `--repo` flags, or a config file), each repository is analysed independently:

1. **Baseline statistics** — mean and standard deviation for every metric are computed from that repository's own merged PRs (optionally restricted to the baseline window).
2. **Z-scores** — each PR is scored against its own repository's statistics, not a cross-repository pool.
3. **Isolation** — a PR in `owner/repo-a` is never compared against PRs from `owner/repo-b`.

This means thresholds adapt to each project's natural pace and size. A large PR in a small, infrequently-updated repository is judged against that repository's history, not the (potentially very different) norms of a busier sibling repository in the same organisation.

```
repo-a  ──►  stats(repo-a)  ──►  z-scores(repo-a PRs)
repo-b  ──►  stats(repo-b)  ──►  z-scores(repo-b PRs)
             (independent)
```

### End-to-end example

```bash
# 1. Fetch a full year of history as the baseline
uv run review-classify fetch --repo owner/repo \
  --start 2024-01-01 --end 2024-12-31

# 2. Evaluate PRs from January 2025 against that baseline
uv run review-classify detect-outliers --repo owner/repo \
  --classify-start 2024-01-01 \
  --classify-end   2024-12-31 \
  --format table
```

## Configuration file

Both `fetch` and `detect-outliers` accept `--config <file.toml>` as an alternative to passing `--repo` / `--org` flags. The file is TOML and supports three sections:

| Section | Purpose |
| --- | --- |
| `[defaults]` | Global values applied to every entry that does not set its own |
| `[[repositories]]` | One entry per `owner/repo` to target |
| `[[organizations]]` | One entry per GitHub org; fetches all repos in that org |

### Full example

```toml
# config.toml

[defaults]
start           = "2024-01-01"
end             = "2024-12-31"
threshold       = 2.0
min_samples     = 30
classify_start  = "2024-01-01"
classify_end    = "2024-06-30"

# Individual repositories ─────────────────────────────────────────────────────

[[repositories]]
name = "owner/repo-a"
# inherits all [defaults]

[[repositories]]
name           = "owner/repo-b"
start          = "2024-06-01"   # overrides [defaults] start
threshold      = 2.5            # stricter outlier threshold for this repo
classify_start = "2024-06-01"
classify_end   = "2024-09-30"

# Organizations ───────────────────────────────────────────────────────────────

[[organizations]]
name = "my-org"
# inherits all [defaults]
exclude_repos = ["my-org/archived-repo", "my-org/fork-only"]

[[organizations]]
name        = "another-org"
start       = "2024-03-01"
min_samples = 20
```

### Key rules

- At least one `[[repositories]]` or `[[organizations]]` entry is required.
- `[defaults]` is optional; omitting it uses the built-in defaults (`threshold = 2.0`, `min_samples = 30`).
- Per-entry values always take precedence over `[defaults]`.
- `exclude_repos` (organizations only) is a list of `owner/repo` strings to skip.

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
