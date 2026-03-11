"""Output formatting for outlier detection results."""

import json
from dataclasses import dataclass, field
from typing import Literal

from ..analysis.outlier_detector import OutlierResult


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


def _format_combined_table(repo_results: list[RepoClassifyResult]) -> str:
    """Render a single markdown table ordered by repository name."""
    header = (
        "| Repository | PR # | Merged | Author | Max \\|Z\\| "
        "| Outlier Features | Title |"
    )
    separator = "|---|---|---|---|---|---|---|"

    rows: list[str] = []
    for repo in repo_results:
        if not repo.success:
            note = _escape_md(repo.error or "Could not be classified")
            rows.append(f"| `{repo.repo_name}` | — | — | — | — | {note} | — |")
            continue

        outliers = sorted(
            (r for r in repo.results if r.is_outlier),
            key=lambda x: x.merged_at if x.merged_at else "",
            reverse=True,
        )
        for o in outliers:
            merged = o.merged_at.strftime("%Y-%m-%d") if o.merged_at else "—"
            features = _escape_md(", ".join(o.outlier_features))
            title = _escape_md(o.title)
            author = _escape_md(o.author)
            rows.append(
                f"| `{repo.repo_name}` | #{o.pr_number} | {merged} | "
                f"{author} | {o.max_abs_z_score:.2f} | {features} | {title} |"
            )

    lines = [header, separator, *rows, ""]

    # Summary
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


def _escape_md(text: str) -> str:
    """Escape markdown table special characters."""
    return text.replace("|", "\\|")


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
