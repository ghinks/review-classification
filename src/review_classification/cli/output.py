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
    lines.append("\nOutlier Pull Requests")
    lines.append("=" * 100)
    lines.append(f"{'PR #':<10} {'Max |Z|':<12} {'Outlier Features':<78}")
    lines.append("-" * 100)

    for outlier in sorted(outliers, key=lambda x: x.max_abs_z_score, reverse=True):
        features_str = ", ".join(outlier.outlier_features)
        if len(features_str) > 75:
            features_str = features_str[:72] + "..."
        lines.append(
            f"#{outlier.pr_number:<9} {outlier.max_abs_z_score:<12.2f} {features_str}"
        )

    lines.append("-" * 100)
    lines.append(
        f"Total outliers: {len(outliers)} out of {total_prs} PRs "
        f"({len(outliers) / total_prs * 100:.1f}%)"
    )

    return "\n".join(lines)


def _format_json(outliers: list[OutlierResult]) -> str:
    """Format as JSON."""
    data = [
        {
            "pr_number": o.pr_number,
            "is_outlier": o.is_outlier,
            "max_abs_z_score": o.max_abs_z_score,
            "outlier_features": o.outlier_features,
            "z_scores": {k: v for k, v in o.z_scores.items() if v is not None},
        }
        for o in outliers
    ]
    return json.dumps(data, indent=2)


def _format_csv(outliers: list[OutlierResult]) -> str:
    """Format as CSV."""
    lines = ["pr_number,max_abs_z_score,outlier_features"]

    for outlier in outliers:
        features_str = ";".join(outlier.outlier_features)
        lines.append(
            f"{outlier.pr_number},{outlier.max_abs_z_score:.4f},{features_str}"
        )

    return "\n".join(lines)
