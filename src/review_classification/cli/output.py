"""Output formatting for outlier detection results."""

import json
from typing import Literal

from ..analysis.outlier_detector import OutlierResult


def format_outlier_results(
    results: list[OutlierResult],
    format_type: Literal["table", "json", "csv"] = "table",
) -> str:
    """Format outlier detection results.

    Args:
        results: List of OutlierResult from detection
        format_type: Output format (table, json, or csv)

    Returns:
        Formatted string output
    """
    outliers = [r for r in results if r.is_outlier]

    if format_type == "json":
        return _format_json(outliers)
    elif format_type == "csv":
        return _format_csv(outliers)
    else:
        return _format_table(outliers, total_prs=len(results))


def _format_table(outliers: list[OutlierResult], total_prs: int) -> str:
    """Format as ASCII table."""
    if not outliers:
        return f"No outliers detected out of {total_prs} PRs analyzed."

    lines = []
    lines.append("\nOutlier Pull Requests (ordered by most recently merged)")
    lines.append("=" * 150)
    lines.append(
        f"{'PR #':<8} {'Merged':<12} {'Author':<20} {'Max |Z|':<10} "
        f"{'Outlier Features':<30} {'Title':<70}"
    )
    lines.append("-" * 150)

    # Sort by merged_at descending (most recent first)
    sorted_outliers = sorted(
        outliers,
        key=lambda x: x.merged_at if x.merged_at else "",
        reverse=True,
    )

    for outlier in sorted_outliers:
        features_str = ", ".join(outlier.outlier_features)
        if len(features_str) > 28:
            features_str = features_str[:25] + "..."

        # Format merge date
        merged_date = (
            outlier.merged_at.strftime("%Y-%m-%d") if outlier.merged_at else "N/A"
        )

        # Truncate author and title if too long
        author = outlier.author[:18] if len(outlier.author) > 18 else outlier.author
        title = outlier.title[:68] if len(outlier.title) > 68 else outlier.title

        lines.append(
            f"#{outlier.pr_number:<7} {merged_date:<12} {author:<20} "
            f"{outlier.max_abs_z_score:<10.2f} {features_str:<30} {title}"
        )

    lines.append("-" * 150)
    lines.append(
        f"Total outliers: {len(outliers)} out of {total_prs} PRs "
        f"({len(outliers) / total_prs * 100:.1f}%)"
    )

    return "\n".join(lines)


def _format_json(outliers: list[OutlierResult]) -> str:
    """Format as JSON."""
    # Sort by merged_at descending (most recent first)
    sorted_outliers = sorted(
        outliers,
        key=lambda x: x.merged_at if x.merged_at else "",
        reverse=True,
    )

    data = [
        {
            "pr_number": o.pr_number,
            "title": o.title,
            "author": o.author,
            "merged_at": o.merged_at.isoformat() if o.merged_at else None,
            "is_outlier": o.is_outlier,
            "max_abs_z_score": o.max_abs_z_score,
            "outlier_features": o.outlier_features,
            "z_scores": {k: v for k, v in o.z_scores.items() if v is not None},
        }
        for o in sorted_outliers
    ]
    return json.dumps(data, indent=2)


def _format_csv(outliers: list[OutlierResult]) -> str:
    """Format as CSV."""
    lines = ["pr_number,merged_at,author,title,max_abs_z_score,outlier_features"]

    # Sort by merged_at descending (most recent first)
    sorted_outliers = sorted(
        outliers,
        key=lambda x: x.merged_at if x.merged_at else "",
        reverse=True,
    )

    for outlier in sorted_outliers:
        features_str = ";".join(outlier.outlier_features)
        merged_date = outlier.merged_at.isoformat() if outlier.merged_at else ""
        # Escape fields that might contain commas
        title = f'"{outlier.title}"' if "," in outlier.title else outlier.title
        author = f'"{outlier.author}"' if "," in outlier.author else outlier.author
        lines.append(
            f"{outlier.pr_number},{merged_date},{author},{title},"
            f"{outlier.max_abs_z_score:.4f},{features_str}"
        )

    return "\n".join(lines)
