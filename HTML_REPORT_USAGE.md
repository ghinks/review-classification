# HTML Report Feature

The review-classification tool now supports generating beautiful, standalone HTML reports of your outlier analysis results.

## Quick Start

Generate an HTML report and save it to a file:

```bash
# Single repository
review-classify classify --repo owner/repo --format html > report.html

# Multiple repositories
review-classify classify --org my-org --format html > org-report.html

# With custom thresholds and date windows
review-classify classify --repo owner/repo \
  --format html \
  --threshold 2.5 \
  --start 2024-01-01 \
  --end 2024-09-30 > analysis.html
```

Then open the generated HTML file in your browser:

```bash
# macOS
open report.html

# Linux
xdg-open report.html

# Windows
start report.html
```

## Features

### Summary Statistics
At the top of the report, you'll see:
- **Total Repositories**: Number of repos analyzed
- **Total PRs**: Number of PRs examined
- **Outliers Found**: Count of detected outliers
- **Outlier Rate**: Percentage of PRs flagged as outliers

### Per-Repository Results
For each repository, the report shows:
- Repository name and statistics
- Summary: total PRs, outlier count, outlier percentage
- **Sortable table** of detected outliers with:
  - PR number (clickable link to GitHub)
  - Author
  - Title
  - Merge date
  - Max Z-Score (severity)
  - Outlier features (which metrics triggered the flag)

### Professional Styling
- Clean, modern design optimized for readability
- Responsive layout that works on desktop and mobile
- Color-coded severity indicators (red for outliers)
- Monospace fonts for code/PR identifiers
- Consistent with modern web design standards

### Self-Contained
- Single HTML file (no external dependencies beyond CDN)
- No server required; just open in a browser
- Contains all CSS styling inline
- Works offline (except GitHub PR links require internet)

## Example Output

When you run:

```bash
review-classify classify --repo expressjs/express --format html > express-report.html
```

You get a professional report showing:
1. Summary: "12 outliers found across 150 PRs (8% outlier rate)"
2. Per-repo section with a table of outliers sorted by severity
3. Clickable PR links that open GitHub in a new tab
4. Responsive design that looks good on any screen size

## Comparing Output Formats

| Format | Best For | Output |
|--------|----------|--------|
| `table` | Terminal viewing | Plain text markdown table |
| `json` | Automation, data processing | Structured JSON array |
| `csv` | Spreadsheet import | Comma-separated values |
| `html` | Reports, sharing, visual analysis | Professional standalone HTML file |

## Use Cases

### Weekly Review Report
```bash
# Generate a weekly report
review-classify classify --org my-org \
  --format html \
  --start 2024-03-01 \
  --end 2024-03-31 > march-2024-report.html

# Share with the team
cp march-2024-report.html /shared/reports/
```

### Code Review Analysis
```bash
# Analyze a specific repository before code review
review-classify classify --repo my-org/critical-service \
  --format html \
  --threshold 2.0 > critical-service-review.html
```

### Investigating Trends
```bash
# Compare different time windows
review-classify classify --repo owner/repo --format html \
  --start 2024-01-01 --end 2024-02-29 > jan-feb.html

review-classify classify --repo owner/repo --format html \
  --start 2024-03-01 --end 2024-04-30 > mar-apr.html

# Open both reports side-by-side for comparison
open jan-feb.html mar-apr.html
```

## Technical Details

### HTML Template
The HTML report uses Jinja2 templating with:
- **Responsive CSS Grid** for layout
- **Semantic HTML5** for accessibility
- **Embedded CSS** for styling (no external stylesheets)
- **Mobile-friendly** with media queries

### No External Dependencies (Beyond CDN)
- Chart.js is loaded from CDN (optional for future enhancements)
- All styling is embedded in the HTML
- Works completely offline except for GitHub PR links

### Data Flow
```
RepoClassifyResult objects
         ↓
html_report.generate_html_report()
         ↓
Jinja2 template rendering
         ↓
HTML string → save to file or stdout
```

## Troubleshooting

### Report looks plain/unstyled
The CSS might not be rendering. Try:
1. Save to a file with `.html` extension: `... > report.html`
2. Open in a modern browser (Chrome, Firefox, Safari, Edge)
3. Check browser console for any errors (F12)

### PR links aren't clickable
The report uses relative links to GitHub. Check:
1. You have internet access
2. The repository name is correctly formatted (owner/repo)
3. PR numbers are valid

### File is too large
This can happen if analyzing many repositories with many outliers.
- Typical file size: 100–500 KB
- If > 5 MB, consider splitting into multiple reports

## Future Enhancements

Potential features for v2:
- Interactive sorting/filtering in the table
- Distribution histograms showing metric distributions
- Export to PDF
- Dark mode toggle
- Embedded GitHub avatars for authors
- Trend charts showing outlier patterns over time

---

## Integration with CI/CD

You can automate HTML report generation in GitHub Actions:

```yaml
name: Weekly Outlier Report

on:
  schedule:
    - cron: '0 9 * * MON'  # Every Monday at 9 AM UTC

jobs:
  report:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Fetch PR data
        run: |
          review-classify fetch --org my-org \
            --start 2024-03-01 --end 2024-03-31
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}

      - name: Generate HTML report
        run: |
          review-classify classify --org my-org \
            --format html > weekly-report.html

      - name: Upload report
        uses: actions/upload-artifact@v4
        with:
          name: weekly-outlier-report
          path: weekly-report.html
```

Then download the report from the workflow artifacts!
