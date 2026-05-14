# Quick Start: HTML Reports

## One-Minute Summary

Generate a beautiful HTML report of your PR outliers:

```bash
# Generate report
review-classify classify --repo owner/repo --format html > report.html

# Open in browser
open report.html  # macOS
xdg-open report.html  # Linux
start report.html  # Windows
```

That's it! You get a professional report with:
- Summary statistics
- Clickable GitHub PR links
- Color-coded outlier severity
- Responsive design (works on mobile)

---

## Common Commands

### Single Repository
```bash
review-classify classify --repo owner/repo --format html > report.html
```

### Entire Organization
```bash
review-classify classify --org my-org --format html > org-report.html
```

### Custom Date Range
```bash
review-classify classify --repo owner/repo \
  --format html \
  --start 2024-01-01 \
  --end 2024-09-30 > q3-report.html
```

### Stricter Threshold (Fewer Outliers)
```bash
review-classify classify --repo owner/repo \
  --format html \
  --threshold 3.0 > strict-report.html
```

### Multiple Options Combined
```bash
review-classify classify --org my-org \
  --format html \
  --threshold 2.5 \
  --min-samples 20 \
  --start 2024-03-01 \
  --end 2024-03-31 > march-report.html
```

---

## Understanding the Report

### Header Statistics
- **Repositories**: Count of repos analyzed
- **Total PRs**: Count of PRs examined
- **Outliers Found**: Red number = outliers detected
- **Outlier Rate**: Percentage of PRs flagged

### Per-Repository Section
For each repo:
| Column | Meaning |
|--------|---------|
| PR # | Pull request number (clickable GitHub link) |
| Author | Person who authored the PR |
| Title | PR title/description |
| Merged | Date the PR was merged |
| Max Z-Score | Outlier severity (2.0+ is outlier) |
| Outlier Features | Metrics that triggered the flag |

---

## Tips & Tricks

### Save Reports Over Time
```bash
# Create reports directory
mkdir -p reports

# Generate weekly reports
for week in {01..52}; do
  review-classify classify --org my-org --format html \
    > reports/week-${week}.html
done

# Compare reports visually
open reports/week-*.html
```

### Email to Team
```bash
# Generate report
review-classify classify --org my-org --format html > report.html

# Email it
mail -s "Weekly Outlier Report" team@example.com < <(cat report.html)
```

### Version Control
```bash
# Track report over time
git add reports/
git commit -m "Weekly outlier report"
git push
```

### CI/CD Integration
```bash
# Generate as part of your build
review-classify fetch --org my-org
review-classify classify --org my-org --format html > report.html

# Upload as artifact
cp report.html build-artifacts/
```

---

## FAQ

**Q: The report is blank/unstyled**  
A: Make sure you saved it with `.html` extension and opened it in a modern browser (Chrome, Firefox, Safari, Edge).

**Q: Can I edit the HTML?**  
A: Yes! The HTML is a standard file you can edit. CSS styling is embedded, so you can customize colors and fonts.

**Q: How large are the files?**  
A: Typical reports are 100–500 KB. Very large organizations might generate 1–5 MB files.

**Q: Can I automate report generation?**  
A: Yes! Use cron jobs or CI/CD workflows to generate reports on a schedule.

**Q: What if I have many outliers?**  
A: The table will be large but still readable. Consider using narrower date ranges for longer analysis.

---

## File Structure

Each report contains:

```
report.html (100-500 KB)
├── HTML structure
├── Embedded CSS styling
├── Summary statistics
├── Per-repository sections
│   ├── Outlier count
│   ├── Outlier table
│   └── GitHub PR links
└── Footer
```

No external files needed—just one HTML file!

---

## Next Steps

1. **Generate your first report**: `review-classify classify --repo owner/repo --format html > report.html`
2. **Open it**: `open report.html`
3. **Share it**: Send the HTML file to your team
4. **Automate it**: Set up a cron job or GitHub Action to generate weekly reports

---

For more details, see:
- **HTML_REPORT_USAGE.md** — Complete feature documentation
- **IMPLEMENTATION_SUMMARY.md** — Technical implementation details
- **README.md** — General project documentation
