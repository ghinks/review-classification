"""Output formatting for outlier detection results."""

import json
from dataclasses import dataclass, field
from typing import Literal

from ..analysis.outlier_detector import OutlierResult

# Per-column maximum display widths (characters before truncation)
_MAX_AUTHOR = 20
_MAX_FEATURES = 40
_MAX_TITLE = 50
_MAX_NOTE = 65  # error/note text in the features cell


@dataclass
class RepoClassifyResult:
    """Classification results for a single repository."""

    repo_name: str
    results: list[OutlierResult] = field(default_factory=list)
    total_prs: int = 0
    error: str | None = None

    @property
    def success(self) -> bool:
        return self.error is None


def format_combined_results(
    repo_results: list[RepoClassifyResult],
    format_type: Literal["table", "json", "csv"] = "table",
) -> str:
    """Format classification results for one or more repositories.

    Args:
        repo_results: Results for each repository, in any order.
        format_type: Output format (table, json, or csv).

    Returns:
        Formatted string output.
    """
    sorted_repos = sorted(repo_results, key=lambda r: r.repo_name)

    if format_type == "json":
        return _format_combined_json(sorted_repos)
    elif format_type == "csv":
        return _format_combined_csv(sorted_repos)
    else:
        return _format_combined_table(sorted_repos)


# ---------------------------------------------------------------------------
# Table helpers
# ---------------------------------------------------------------------------


def _truncate(text: str, max_len: int) -> str:
    """Truncate text to max_len, appending … if shortened."""
    return text if len(text) <= max_len else text[: max_len - 1] + "\u2026"


def _fmt_row(cells: list[str], widths: list[int]) -> str:
    """Render one markdown table row with cells padded to column widths."""
    padded = (cell.ljust(widths[i]) for i, cell in enumerate(cells))
    return "| " + " | ".join(padded) + " |"


def _separator(widths: list[int]) -> str:
    """Render the markdown header-separator row."""
    return "|" + "|".join("-" * (w + 2) for w in widths) + "|"


# ---------------------------------------------------------------------------
# Table output
# ---------------------------------------------------------------------------


def _format_combined_table(repo_results: list[RepoClassifyResult]) -> str:
    """Render a single padded markdown/plain-text table ordered by repository.

    Each cell is padded to the maximum width in its column so the table
    aligns in both a terminal and a markdown renderer.
    """
    headers = [
        "Repository",
        "PR #",
        "Merged",
        "Author",
        "Max Z",
        "Outlier Features",
        "Title",
    ]

    # Build raw cell data for every row
    rows: list[list[str]] = []
    for repo in repo_results:
        if not repo.success:
            note = _truncate(repo.error or "Could not be classified", _MAX_NOTE)
            rows.append([f"`{repo.repo_name}`", "—", "—", "—", "—", note, "—"])
            continue

        outliers = sorted(
            (r for r in repo.results if r.is_outlier),
            key=lambda x: x.merged_at if x.merged_at else "",
            reverse=True,
        )
        for o in outliers:
            merged = o.merged_at.strftime("%Y-%m-%d") if o.merged_at else "—"
            rows.append(
                [
                    f"`{repo.repo_name}`",
                    f"#{o.pr_number}",
                    merged,
                    _truncate(o.author, _MAX_AUTHOR),
                    f"{o.max_abs_z_score:.2f}",
                    _truncate(", ".join(o.outlier_features), _MAX_FEATURES),
                    _truncate(o.title, _MAX_TITLE),
                ]
            )

    # Column widths = max(header width, max cell width in that column)
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(cell))

    lines: list[str] = [
        _fmt_row(headers, widths),
        _separator(widths),
        *(_fmt_row(row, widths) for row in rows),
        "",
    ]

    # Summary footer
    successful = [r for r in repo_results if r.success]
    failed = [r for r in repo_results if not r.success]
    total_outliers = sum(
        sum(1 for r in repo.results if r.is_outlier) for repo in successful
    )
    total_prs = sum(r.total_prs for r in successful)

    if successful:
        lines.append(
            f"**{total_outliers} outlier(s)** found across {total_prs} PRs "
            f"in {len(successful)} classified repo(s)."
        )
    if failed:
        lines.append(f"**{len(failed)} repo(s)** could not be classified (see above).")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# JSON output
# ---------------------------------------------------------------------------


def _format_combined_json(repo_results: list[RepoClassifyResult]) -> str:
    """Format as a JSON array of outlier records, each tagged with repository."""
    records = []
    for repo in repo_results:
        if not repo.success:
            continue
        for o in sorted(
            (r for r in repo.results if r.is_outlier),
            key=lambda x: x.merged_at if x.merged_at else "",
            reverse=True,
        ):
            records.append(
                {
                    "repository": repo.repo_name,
                    "pr_number": o.pr_number,
                    "title": o.title,
                    "author": o.author,
                    "merged_at": o.merged_at.isoformat() if o.merged_at else None,
                    "is_outlier": o.is_outlier,
                    "max_abs_z_score": o.max_abs_z_score,
                    "outlier_features": o.outlier_features,
                    "z_scores": {k: v for k, v in o.z_scores.items() if v is not None},
                }
            )
    return json.dumps(records, indent=2)


# ---------------------------------------------------------------------------
# CSV output
# ---------------------------------------------------------------------------


def _format_combined_csv(repo_results: list[RepoClassifyResult]) -> str:
    """Format as CSV with a leading repository column."""
    lines = [
        "repository,pr_number,merged_at,author,title,max_abs_z_score,outlier_features"
    ]
    for repo in repo_results:
        if not repo.success:
            continue
        for o in sorted(
            (r for r in repo.results if r.is_outlier),
            key=lambda x: x.merged_at if x.merged_at else "",
            reverse=True,
        ):
            features_str = ";".join(o.outlier_features)
            merged_date = o.merged_at.isoformat() if o.merged_at else ""
            title = f'"{o.title}"' if "," in o.title else o.title
            author = f'"{o.author}"' if "," in o.author else o.author
            repo_col = (
                f'"{repo.repo_name}"' if "," in repo.repo_name else repo.repo_name
            )
            lines.append(
                f"{repo_col},{o.pr_number},{merged_date},{author},{title},"
                f"{o.max_abs_z_score:.4f},{features_str}"
            )
    return "\n".join(lines)
