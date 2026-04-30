# Review Classification

A CLI tool to identify pull request outliers in GitHub repositories using Z-score analysis. Helps engineering teams spot unusual PRs — by size, review duration, comment activity, or code churn — against a stable historical baseline.

## Features

- **Fetch & Store**: retrieve PR data from GitHub (with rate-limit handling) and store it in a local SQLite database.
- **Classify**: Z-score analysis across multiple metrics — additions, deletions, changed files, comments, review duration, code churn, and comment density.
- **Baseline window**: define a historical measurement period so recent PRs are evaluated against an independent baseline rather than skewing their own statistics.
- **Primary-branch filter**: focus analysis on PRs that were not merged into the primary branch (e.g. feature-to-feature or abandoned branches).
- **Flexible output**: view results as a terminal table or export to JSON/CSV.
- **Deferred output**: when processing multiple repositories, results for all repos are printed together after all processing completes, with a summary of any repos that could not be classified.

## Installation

**Prerequisites**: Python 3.12+

### From PyPI (recommended)

```bash
pip install review-classification
```

Or, if you use [uv](https://github.com/astral-sh/uv):

```bash
uv tool install review-classification
```

Once installed, the `review-classify` command is available in your terminal.

### From source (development)

**Prerequisites**: [uv](https://github.com/astral-sh/uv)

```bash
git clone https://github.com/ghinks/review-classification.git
cd review-classification
uv sync
```

When running from source, prefix all commands with `uv run` (e.g., `uv run review-classify fetch ...`).

## Usage

The tool has two commands: **fetch** and **classify**.

> **Note**: Examples below use `uv run review-classify` (source installs). If you installed from PyPI, omit the `uv run` prefix and call `review-classify` directly.

### 1. Configure GitHub Token

```bash
export GITHUB_TOKEN=your_token_here
```

Without a token the GitHub API rate limit is very low.

### 2. `fetch` — retrieve and store PR data

```bash
# Fetch PRs created in the last 30 days (default) for a specific repo
uv run review-classify fetch --repo owner/repo

# Fetch PRs for an entire organization
uv run review-classify fetch --org your-org

# Fetch PRs within a specific date range
uv run review-classify fetch --repo owner/repo \
  --collate-start 2024-01-01 --collate-end 2024-06-30

# Clear existing data before fetching
uv run review-classify fetch --repo owner/repo \
  --reset-db --collate-start 2024-01-01

# Run fetching using a TOML configuration file
uv run review-classify fetch --config config.toml
```

| Option | Description |
| --- | --- |
| `--repo` / `-r` | GitHub repository (owner/repo). Can be specified multiple times. |
| `--org` / `-o` | GitHub organization. Fetches all repositories in the org. Can be specified multiple times. |
| `--config` / `-c` | Path to a TOML config file defining multiple repositories/organizations. |
| `--collate-start` | Start date for PR collation range (YYYY-MM-DD). Defaults to 30 days ago. |
| `--collate-end` | End date for PR collation range (YYYY-MM-DD). |
| `--reset-db` | Delete all stored data before fetching. |
| `--verbose` / `-v` | Print progress details. |

### 3. `classify` — find unusual PRs

Operates on data already fetched with `fetch`. Results for all repositories are printed together after all repos have been processed.

```bash
# Classify all stored PRs for a repo
uv run review-classify classify --repo owner/repo

# Classify PRs for an entire organization
uv run review-classify classify --org your-org

# Stricter threshold (fewer, more extreme outliers)
uv run review-classify classify --repo owner/repo --threshold 3.0

# Export to JSON
uv run review-classify classify --repo owner/repo --format json > outliers.json

# Exclude PRs merged into the primary branch (main/master)
uv run review-classify classify --repo owner/repo --exclude-primary-merged
```

| Option | Description |
| --- | --- |
| `--repo` / `-r` | GitHub repository (owner/repo). Can be specified multiple times. |
| `--org` / `-o` | GitHub organization. Fetches all repositories in the org. Can be specified multiple times. |
| `--config` / `-c` | Path to a TOML config file defining multiple repositories/organizations. |
| `--threshold` / `-t` | Z-score threshold for flagging an outlier. Default: `2.0`. |
| `--min-samples` | Minimum number of PRs required for analysis. Default: `30`. |
| `--format` / `-f` | Output format: `table` (default), `json`, or `csv`. |
| `--start` | Start of the classification window (YYYY-MM-DD). |
| `--end` | End of the classification window (YYYY-MM-DD). |
| `--exclude-primary-merged` | Exclude PRs whose base branch is `main` or `master`. |
| `--verbose` / `-v` | Print progress details. |

#### Classification window (`--start` / `--end`)

By default all stored PRs feed both the baseline statistics and the outlier evaluation. This is problematic: an unusually large PR inflates the mean and standard deviation it is measured against, masking itself as normal.

Use `--start` and `--end` to define a historical baseline window. Statistics are computed from PRs merged **within** that window; only PRs merged **after** `--end` are evaluated and reported.

```
[--start ──────────────── --end]   >end
      ↑                     ↑          ↑
baseline start         baseline end  PRs evaluated here
```

```bash
# Use Jan–Jun 2024 as the baseline; evaluate PRs merged after 2024-06-30
uv run review-classify classify --repo owner/repo \
  --start 2024-01-01 \
  --end   2024-06-30

# Same, with stricter threshold and JSON output
uv run review-classify classify --repo owner/repo \
  --start 2024-01-01 \
  --end   2024-06-30 \
  --threshold 2.5 \
  --format json > outliers.json
```

#### Excluding primary-branch PRs (`--exclude-primary-merged`)

Pass `--exclude-primary-merged` to restrict analysis to PRs that were **not** merged into `main` or `master`. This is useful for focusing on PRs targeting feature branches, release branches, or PRs that may have been abandoned.

```bash
uv run review-classify classify --repo owner/repo --exclude-primary-merged
```

### Per-repository analysis

Outlier detection is always **scoped to a single repository**. When you target multiple repositories (via `--org`, multiple `--repo` flags, or a config file), each repository is analysed independently:

1. **Baseline statistics** — mean and standard deviation for every metric are computed from that repository's own merged PRs (optionally restricted to the classification window).
2. **Z-scores** — each PR is scored against its own repository's statistics, not a cross-repository pool.
3. **Isolation** — a PR in `owner/repo-a` is never compared against PRs from `owner/repo-b`.

This means thresholds adapt to each project's natural pace and size.

```
repo-a  ──►  stats(repo-a)  ──►  z-scores(repo-a PRs)
repo-b  ──►  stats(repo-b)  ──►  z-scores(repo-b PRs)
             (independent)
```

### Deferred output

When processing multiple repositories, per-repo results are **not** printed as they are produced. Instead:

- After all repositories have been processed, results for every successfully classified repo are printed.
- Repositories that could not be classified (insufficient data, no PRs found, etc.) are listed in a summary block on stderr at the end.

### End-to-end example

```bash
# Fetch the data you want to analyze
uv run review-classify fetch --repo owner/repo \
  --collate-start 2024-01-01 --collate-end 2024-12-31

# Classify against a historical baseline window
uv run review-classify classify --repo owner/repo \
  --start 2024-01-01 \
  --end   2024-12-31 \
  --format table
```

## Configuration file

`fetch` and `classify` both accept `--config <file.toml>` as an alternative to passing `--repo` / `--org` flags. The file is TOML and supports three sections:

| Section | Purpose |
| --- | --- |
| `[defaults]` | Global values applied to every entry that does not set its own |
| `[[repositories]]` | One entry per `owner/repo` to target |
| `[[organizations]]` | One entry per GitHub org; fetches all repos in that org |

### Full example

```toml
# config.toml

[defaults]
collate_start = "2024-01-01"
collate_end   = "2024-12-31"
threshold     = 2.0
min_samples   = 30
start         = "2024-01-01"
end           = "2024-06-30"

# Individual repositories ─────────────────────────────────────────────────────

[[repositories]]
name = "owner/repo-a"
# inherits all [defaults]

[[repositories]]
name          = "owner/repo-b"
collate_start = "2024-06-01"   # overrides [defaults] collate_start
threshold     = 2.5            # stricter outlier threshold for this repo
start         = "2024-06-01"
end           = "2024-09-30"

# Organizations ───────────────────────────────────────────────────────────────

[[organizations]]
name = "my-org"
# inherits all [defaults]
exclude_repos = ["my-org/archived-repo", "my-org/fork-only"]

[[organizations]]
name          = "another-org"
collate_start = "2024-03-01"
min_samples   = 20
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

Run the full test suite:

```bash
uv run pytest
```

Run **unit tests only** (excludes integration tests that call the real GitHub API):

```bash
uv run pytest -m "not integration"
```

Run **integration tests only** (requires a valid `GITHUB_TOKEN` or an authenticated `gh` CLI session):

```bash
uv run pytest -m integration
```

#### Running individual integration tests

Integration tests live in `tests/test_integration.py`. They are marked `@pytest.mark.integration` and target the `expressjs/express` repository as a real-world fixture.

**`test_fetch_examples_integration`** — four parametrised variants of the `fetch` command. Run all four at once:

```bash
uv run pytest tests/test_integration.py::test_fetch_examples_integration
```

Or run a single variant by its explicit ID:

```bash
# Variant 1 — fetch with default date range (no explicit collate window)
uv run pytest "tests/test_integration.py::test_fetch_examples_integration[fetch-default]"

# Variant 2 — fetch with explicit --collate-start / --collate-end
uv run pytest "tests/test_integration.py::test_fetch_examples_integration[fetch-with-dates]"

# Variant 3 — fetch with --reset-db and explicit date range
uv run pytest "tests/test_integration.py::test_fetch_examples_integration[fetch-reset-db]"

# Variant 4 — fetch using a --config TOML file
uv run pytest "tests/test_integration.py::test_fetch_examples_integration[fetch-config]"
```

**`test_classify_example_table_output`** — classify with default table output:

```bash
uv run pytest tests/test_integration.py::test_classify_example_table_output
```

**`test_classify_example_stricter_threshold`** — classify with `--threshold 3.0`:

```bash
uv run pytest tests/test_integration.py::test_classify_example_stricter_threshold
```

**`test_classify_example_json_output`** — classify with `--format json` and validates the JSON payload:

```bash
uv run pytest tests/test_integration.py::test_classify_example_json_output
```

**`test_classify_example_exclude_primary_merged`** — classify with `--exclude-primary-merged`:

```bash
uv run pytest tests/test_integration.py::test_classify_example_exclude_primary_merged
```

### Linting & Formatting

```bash
# Run ruff (lint + format) and mypy via pre-commit
uv run pre-commit run --all-files
```
