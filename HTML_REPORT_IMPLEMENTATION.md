# HTML Report Implementation Plan

**Scope**: Add `--format html` option to the `classify` command to generate a standalone, interactive HTML report.

**Estimated effort**: 4–6 hours  
**Dependencies**: Jinja2 (already in project) + minimal HTML/CSS/JavaScript

---

## Overview

When users run:

```bash
review-classify classify --repo owner/repo --format html > report.html
```

They get a professional, self-contained HTML file with:
- Summary statistics
- Per-repository outlier tables with GitHub links
- Distribution histograms for key metrics
- No server required; opens in any browser

---

## Design Decisions

### 1. **Jinja2 for Templating**
- Already a dependency (used in pyproject.toml or environment)
- Easy to maintain and extend
- Separates presentation logic from Python code

### 2. **Embedded Charts**
Use **Chart.js** (CDN-hosted) for histograms:
- Lightweight, no build step required
- Renders interactively in the browser
- Minimal JavaScript; charts are JSON data + Chart.js config

Alternative: SVG histograms (pure HTML, no dependencies, but less interactive)

### 3. **Standalone Output**
- Single HTML file (no separate CSS/JS files)
- Inline CSS for styling
- CDN-loaded Chart.js library (one external dependency, unavoidable)
- Graceful fallback if CDN unavailable (text-only fallback tables)

### 4. **No Output Parameter Needed**
Output flows to stdout (like JSON/CSV). Users redirect to file:
```bash
review-classify classify --repo owner/repo --format html > report.html
```

This keeps the interface consistent.

---

## Implementation Steps

### Step 1: Create HTML Report Module (`src/review_classification/cli/html_report.py`)

**Responsibilities**:
- Take `list[RepoClassifyResult]` as input
- Render Jinja2 template with data
- Return HTML string

**Key functions**:

```python
def generate_html_report(
    repo_results: list[RepoClassifyResult],
) -> str:
    """Generate standalone HTML report from classification results."""
    # Prepare data for template
    data = _prepare_template_data(repo_results)
    
    # Render template
    template = _get_template()
    html = template.render(data)
    
    return html


def _prepare_template_data(repo_results: list[RepoClassifyResult]) -> dict:
    """Transform RepoClassifyResult into template-friendly format."""
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "total_repos": len(repo_results),
        "successful_repos": len([r for r in repo_results if r.success]),
        "failed_repos": len([r for r in repo_results if not r.success]),
        "total_prs": sum(r.total_prs for r in repo_results if r.success),
        "total_outliers": sum(
            sum(1 for result in r.results if result.is_outlier)
            for r in repo_results if r.success
        ),
        "repositories": [_format_repo(r) for r in repo_results if r.success],
        "failed_repositories": [r for r in repo_results if not r.success],
        "metric_distributions": _compute_distributions(repo_results),
    }


def _format_repo(repo: RepoClassifyResult) -> dict:
    """Format a single repository for the template."""
    outliers = [r for r in repo.results if r.is_outlier]
    return {
        "name": repo.repo_name,
        "total_prs": repo.total_prs,
        "outlier_count": len(outliers),
        "outlier_percent": (len(outliers) / repo.total_prs * 100) if repo.total_prs > 0 else 0,
        "outliers": [_format_outlier(o) for o in sorted(
            outliers, key=lambda x: x.max_abs_z_score, reverse=True
        )],
    }


def _format_outlier(outlier: OutlierResult) -> dict:
    """Format a single outlier for the template."""
    return {
        "pr_number": outlier.pr_number,
        "title": outlier.title,
        "author": outlier.author,
        "merged_at": outlier.merged_at.strftime("%Y-%m-%d") if outlier.merged_at else "—",
        "max_z_score": f"{outlier.max_abs_z_score:.2f}",
        "outlier_features": ", ".join(outlier.outlier_features),
        "z_scores": outlier.z_scores,
        # Add more as needed
    }


def _compute_distributions(repo_results: list[RepoClassifyResult]) -> dict:
    """Compute metric distributions for histograms."""
    # Aggregate metrics across all PRs in all repos
    metrics = {
        "additions": [],
        "deletions": [],
        "changed_files": [],
        "review_duration": [],
        "code_churn": [],
        "total_comments": [],
    }
    
    for repo in repo_results:
        if not repo.success:
            continue
        for result in repo.results:
            metrics["additions"].append(result.additions or 0)  # From PR object
            # ... collect other metrics
    
    # Convert to histogram buckets for Chart.js
    return {
        key: _bucket_data(values)
        for key, values in metrics.items()
    }


def _bucket_data(values: list[float], num_buckets: int = 10) -> dict:
    """Convert a list of values into histogram buckets for Chart.js."""
    if not values:
        return {"labels": [], "counts": []}
    
    min_val = min(values)
    max_val = max(values)
    bucket_size = (max_val - min_val + 1) / num_buckets
    
    buckets = [0] * num_buckets
    for v in values:
        idx = min(int((v - min_val) / bucket_size), num_buckets - 1)
        buckets[idx] += 1
    
    labels = [
        f"{int(min_val + i * bucket_size)}–{int(min_val + (i + 1) * bucket_size)}"
        for i in range(num_buckets)
    ]
    
    return {"labels": labels, "counts": buckets}


def _get_template() -> jinja2.Template:
    """Load and return the HTML template."""
    template_str = _TEMPLATE_HTML  # Defined below
    return jinja2.Template(template_str)


_TEMPLATE_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PR Outlier Report</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: #f7fafc;
            color: #1a202c;
            line-height: 1.6;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 2rem;
        }
        header {
            background: white;
            border-bottom: 2px solid #e2e8f0;
            padding: 2rem;
            margin: -2rem -2rem 2rem -2rem;
        }
        h1 {
            font-size: 2rem;
            margin-bottom: 0.5rem;
        }
        .subtitle {
            color: #718096;
            font-size: 0.95rem;
        }
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
            margin-top: 2rem;
        }
        .stat-card {
            background: white;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            padding: 1.5rem;
            text-align: center;
        }
        .stat-value {
            font-size: 2rem;
            font-weight: bold;
            color: #2d3748;
        }
        .stat-label {
            color: #718096;
            font-size: 0.9rem;
            margin-top: 0.5rem;
        }
        .section {
            background: white;
            border-radius: 8px;
            padding: 2rem;
            margin-bottom: 2rem;
            border: 1px solid #e2e8f0;
        }
        .section h2 {
            font-size: 1.5rem;
            margin-bottom: 1.5rem;
            padding-bottom: 0.75rem;
            border-bottom: 1px solid #e2e8f0;
        }
        .repo-section {
            margin-bottom: 2rem;
        }
        .repo-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1rem;
        }
        .repo-name {
            font-family: monospace;
            font-size: 1.1rem;
            font-weight: bold;
            color: #2d3748;
        }
        .repo-stats {
            display: flex;
            gap: 2rem;
            font-size: 0.95rem;
        }
        .repo-stats span {
            color: #4a5568;
        }
        .outlier-count {
            background: #fed7d7;
            color: #c53030;
            padding: 0.25rem 0.75rem;
            border-radius: 4px;
            font-weight: bold;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 1rem;
        }
        th {
            background: #f7fafc;
            text-align: left;
            padding: 0.75rem;
            font-weight: 600;
            border-bottom: 2px solid #e2e8f0;
            font-size: 0.9rem;
        }
        td {
            padding: 0.75rem;
            border-bottom: 1px solid #e2e8f0;
        }
        tr:hover {
            background: #f7fafc;
        }
        .pr-number {
            font-family: monospace;
            color: #0066cc;
            text-decoration: none;
        }
        .pr-number:hover {
            text-decoration: underline;
        }
        .z-score {
            font-weight: bold;
            color: #c53030;
        }
        .chart-container {
            position: relative;
            height: 300px;
            margin-bottom: 2rem;
        }
        .chart-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
            gap: 2rem;
        }
        .chart-wrapper {
            background: white;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            padding: 1.5rem;
        }
        .chart-title {
            font-size: 1rem;
            font-weight: 600;
            margin-bottom: 1rem;
            color: #2d3748;
        }
        .error-box {
            background: #fed7d7;
            border: 1px solid #fc8181;
            color: #c53030;
            padding: 1rem;
            border-radius: 8px;
            margin-bottom: 1rem;
        }
        footer {
            text-align: center;
            color: #718096;
            font-size: 0.9rem;
            margin-top: 3rem;
            padding-top: 2rem;
            border-top: 1px solid #e2e8f0;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>📊 PR Outlier Report</h1>
            <p class="subtitle">Generated {{ generated_at }}</p>
            
            <div class="stats">
                <div class="stat-card">
                    <div class="stat-value">{{ total_repos }}</div>
                    <div class="stat-label">Repositories</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{{ total_prs }}</div>
                    <div class="stat-label">Total PRs Analyzed</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value" style="color: #c53030;">{{ total_outliers }}</div>
                    <div class="stat-label">Outliers Found</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">
                        {% if total_prs > 0 %}
                            {{ (total_outliers / total_prs * 100)|round(1) }}%
                        {% else %}
                            0%
                        {% endif %}
                    </div>
                    <div class="stat-label">Outlier Rate</div>
                </div>
            </div>
        </header>

        <!-- Distribution Histograms -->
        {% if metric_distributions %}
        <div class="section">
            <h2>Metric Distributions</h2>
            <p style="color: #718096; margin-bottom: 1.5rem;">Overview of PR metrics across all repositories.</p>
            <div class="chart-grid">
                {% for metric_name, distribution in metric_distributions.items() %}
                <div class="chart-wrapper">
                    <div class="chart-title">{{ metric_name|replace('_', ' ')|title }}</div>
                    <div class="chart-container">
                        <canvas id="chart-{{ metric_name }}"></canvas>
                    </div>
                </div>
                {% endfor %}
            </div>
        </div>
        {% endif %}

        <!-- Per-Repository Results -->
        <div class="section">
            <h2>Results by Repository</h2>
            
            {% if failed_repositories %}
            <div style="margin-bottom: 2rem;">
                <h3 style="font-size: 1.1rem; margin-bottom: 1rem; color: #c53030;">Failed Repositories</h3>
                {% for repo in failed_repositories %}
                <div class="error-box">
                    <strong>{{ repo.repo_name }}</strong>: {{ repo.error }}
                </div>
                {% endfor %}
            </div>
            {% endif %}

            {% for repo in repositories %}
            <div class="repo-section">
                <div class="repo-header">
                    <span class="repo-name">📦 {{ repo.name }}</span>
                    <div class="repo-stats">
                        <span><strong>{{ repo.total_prs }}</strong> PRs</span>
                        <span><strong class="outlier-count">{{ repo.outlier_count }} outlier{% if repo.outlier_count != 1 %}s{% endif %}</strong></span>
                        <span>{{ repo.outlier_percent|round(1) }}% flagged</span>
                    </div>
                </div>

                {% if repo.outliers %}
                <table>
                    <thead>
                        <tr>
                            <th>PR #</th>
                            <th>Author</th>
                            <th>Title</th>
                            <th>Merged</th>
                            <th>Max Z-Score</th>
                            <th>Outlier Features</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for outlier in repo.outliers %}
                        <tr>
                            <td>
                                <a href="https://github.com/{{ repo.name }}/pull/{{ outlier.pr_number }}" 
                                   class="pr-number" target="_blank">
                                   #{{ outlier.pr_number }}
                                </a>
                            </td>
                            <td>{{ outlier.author }}</td>
                            <td>{{ outlier.title }}</td>
                            <td>{{ outlier.merged_at }}</td>
                            <td><span class="z-score">{{ outlier.max_z_score }}</span></td>
                            <td>{{ outlier.outlier_features }}</td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
                {% else %}
                <p style="color: #718096;">No outliers found.</p>
                {% endif %}
            </div>
            {% endfor %}
        </div>

        <footer>
            <p>Generated by <a href="https://github.com/ghinks/review-classification" style="color: #0066cc; text-decoration: none;">review-classification</a></p>
        </footer>
    </div>

    <script>
        // Chart.js configuration for each metric histogram
        const chartConfigs = {
            {% for metric_name, distribution in metric_distributions.items() %}
            "{{ metric_name }}": {
                type: 'bar',
                data: {
                    labels: {{ distribution.labels | tojson }},
                    datasets: [{
                        label: '{{ metric_name|replace("_", " ")|title }}',
                        data: {{ distribution.counts | tojson }},
                        backgroundColor: 'rgba(59, 130, 246, 0.5)',
                        borderColor: 'rgba(59, 130, 246, 1)',
                        borderWidth: 1,
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: false }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            title: { display: true, text: 'Count' }
                        }
                    }
                }
            },
            {% endfor %}
        };

        // Render all charts
        Object.keys(chartConfigs).forEach(metricName => {
            const ctx = document.getElementById(`chart-${ metricName }`);
            if (ctx) {
                new Chart(ctx, chartConfigs[metricName]);
            }
        });
    </script>
</body>
</html>
"""
```

---

### Step 2: Update `output.py` to Include HTML Format

Modify `format_combined_results()`:

```python
def format_combined_results(
    repo_results: list[RepoClassifyResult],
    format_type: Literal["table", "json", "csv", "html"] = "table",
) -> str:
    """Format classification results for one or more repositories."""
    sorted_repos = sorted(repo_results, key=lambda r: r.repo_name)

    if format_type == "json":
        return _format_combined_json(sorted_repos)
    elif format_type == "csv":
        return _format_combined_csv(sorted_repos)
    elif format_type == "html":
        from .html_report import generate_html_report
        return generate_html_report(sorted_repos)
    else:
        return _format_combined_table(sorted_repos)
```

---

### Step 3: Update CLI to Accept `html` Format

Modify the `classify` command in `app.py`:

```python
output_format: Annotated[
    str,
    typer.Option(
        "--format", 
        "-f", 
        help="Output format: table, json, csv, or html"
    ),
] = "table",
```

Add validation:

```python
if output_format not in ["table", "json", "csv", "html"]:
    typer.echo(f"Invalid format: {output_format}", err=True)
    raise typer.Exit(code=1)
```

---

### Step 4: Add Tests

Create `tests/cli/test_html_output.py`:

```python
def test_html_report_generation():
    """Test that HTML report is valid HTML."""
    from review_classification.cli.html_report import generate_html_report
    from review_classification.cli.output import RepoClassifyResult
    from review_classification.analysis.outlier_detector import OutlierResult
    from datetime import datetime, UTC
    
    outlier = OutlierResult(
        pr_id=1,
        pr_number=42,
        title="Fix: large refactor",
        author="alice",
        merged_at=datetime.now(UTC),
        is_outlier=True,
        outlier_features=["additions"],
        max_abs_z_score=2.5,
        z_scores={"additions": 2.5},
    )
    
    result = RepoClassifyResult(
        repo_name="owner/repo",
        results=[outlier],
        total_prs=100,
    )
    
    html = generate_html_report([result])
    
    assert "<!DOCTYPE html>" in html
    assert "owner/repo" in html
    assert "#42" in html
    assert "alice" in html
    assert "Fix: large refactor" in html
```

---

## File Structure

```
src/review_classification/cli/
├── __init__.py
├── app.py           (modify: update --format option, add validation)
├── config.py
├── output.py        (modify: add html case to format_combined_results)
├── parser.py
└── html_report.py   (NEW: ~300 lines)

tests/cli/
├── __init__.py
├── test_config.py
├── test_parser.py
└── test_html_output.py  (NEW)
```

---

## Example Usage

```bash
# Generate and save HTML report
review-classify classify --repo owner/repo --format html > outliers.html

# View in browser (macOS)
open outliers.html

# Or redirect with redirection operator
review-classify classify --org my-org --format html --threshold 2.5 > report.html
```

Output: A self-contained, professional HTML file that opens in any browser. No server required.

---

## Future Enhancements

1. **Interactive sorting/filtering** in the table (DataTables.js)
2. **Per-metric histograms** with better bucketing
3. **Z-score distribution chart** showing outlier threshold visually
4. **Dark mode toggle** via CSS variables
5. **Export as PDF** (requires headless browser or library)
6. **Embed GitHub avatars** for authors (requires additional API call)

---

## Dependencies Check

```bash
# Check if jinja2 is already a dependency
pip show jinja2
```

If not already present, add to `pyproject.toml`:
```toml
[project]
dependencies = [
    "jinja2>=3.0",
    # ... existing deps
]
```

Chart.js is loaded from CDN, so no additional package installation needed.

---

## Success Criteria

- ✅ `--format html` option is available in `classify` command
- ✅ HTML output is valid HTML5 and renders in modern browsers
- ✅ Report includes summary stats, outlier tables, and distribution charts
- ✅ PR links are clickable and point to GitHub
- ✅ Report is standalone (no external dependencies beyond CDN)
- ✅ Tests pass for HTML generation
- ✅ Documentation updated with HTML format option
