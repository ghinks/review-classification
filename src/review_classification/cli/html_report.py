"""HTML report generation for outlier detection results."""

import importlib.resources
from datetime import UTC, datetime

import jinja2

from .output import RepoClassifyResult


def generate_html_report(repo_results: list[RepoClassifyResult]) -> str:
    """Generate a standalone HTML report from classification results.

    Args:
        repo_results: List of repository classification results

    Returns:
        HTML string ready to be written to a file
    """
    data = _prepare_template_data(repo_results)
    template = _get_template()
    return template.render(**data)


def _prepare_template_data(repo_results: list[RepoClassifyResult]) -> dict:
    """Transform RepoClassifyResult into template-friendly format."""
    successful_repos = [r for r in repo_results if r.success]
    failed_repos = [r for r in repo_results if not r.success]

    total_prs = sum(r.total_prs for r in successful_repos)
    total_outliers = sum(
        sum(1 for result in r.results if result.is_outlier) for r in successful_repos
    )

    return {
        "generated_at": datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC"),
        "total_repos": len(repo_results),
        "successful_repos": len(successful_repos),
        "failed_repos": len(failed_repos),
        "total_prs": total_prs,
        "total_outliers": total_outliers,
        "outlier_rate": (total_outliers / total_prs * 100) if total_prs > 0 else 0,
        "repositories": [_format_repo(r) for r in successful_repos],
        "failed_repositories": failed_repos,
    }


def _format_repo(repo: RepoClassifyResult) -> dict:
    """Format a single repository for the template."""
    outliers = sorted(
        (r for r in repo.results if r.is_outlier),
        key=lambda x: x.max_abs_z_score,
        reverse=True,
    )
    return {
        "name": repo.repo_name,
        "total_prs": repo.total_prs,
        "outlier_count": len(outliers),
        "outlier_percent": (
            len(outliers) / repo.total_prs * 100 if repo.total_prs > 0 else 0
        ),
        "outliers": [_format_outlier(repo.repo_name, o) for o in outliers],
    }


def _format_outlier(repo_name: str, outlier) -> dict:  # noqa: ANN001
    """Format a single outlier for the template."""
    return {
        "pr_number": outlier.pr_number,
        "pr_url": f"https://github.com/{repo_name}/pull/{outlier.pr_number}",
        "title": outlier.title,
        "author": outlier.author,
        "merged_at": (
            outlier.merged_at.strftime("%Y-%m-%d") if outlier.merged_at else "—"
        ),
        "max_z_score": f"{outlier.max_abs_z_score:.2f}",
        "outlier_features": ", ".join(outlier.outlier_features),
    }


def _get_template() -> jinja2.Template:
    """Load and return the HTML template from the bundled report.html file."""
    template_text = (
        importlib.resources.files("review_classification.cli")
        .joinpath("report.html")
        .read_text(encoding="utf-8")
    )
    env = jinja2.Environment(autoescape=True)
    return env.from_string(template_text)
