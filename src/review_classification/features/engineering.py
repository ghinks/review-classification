"""Feature engineering for PR analysis."""

from typing import TypedDict

from ..sqlite.models import PRFeatures, PullRequest


class ComputedFeatures(TypedDict):
    """Type-safe dictionary for computed features."""

    review_duration_hours: float | None
    code_churn: int
    comment_density_per_file: float | None
    comment_density_per_line: float | None
    total_comments: int


def compute_features(pr: PullRequest) -> ComputedFeatures:
    """Compute engineered features from a PullRequest.

    Args:
        pr: PullRequest model instance

    Returns:
        ComputedFeatures dictionary with all computed values

    Edge cases:
        - review_duration_hours is None if merged_at is None
        - comment_density_per_file is None if changed_files == 0
        - comment_density_per_line is None if code_churn == 0
    """
    # Review duration
    review_duration_hours = None
    if pr.merged_at is not None:
        delta = pr.merged_at - pr.created_at
        review_duration_hours = delta.total_seconds() / 3600.0

    # Code churn
    code_churn = pr.additions + pr.deletions

    # Total comments
    total_comments = pr.comments + pr.review_comments

    # Comment density per file
    comment_density_per_file = None
    if pr.changed_files > 0:
        comment_density_per_file = total_comments / pr.changed_files

    # Comment density per line
    comment_density_per_line = None
    if code_churn > 0:
        comment_density_per_line = total_comments / code_churn

    return ComputedFeatures(
        review_duration_hours=review_duration_hours,
        code_churn=code_churn,
        comment_density_per_file=comment_density_per_file,
        comment_density_per_line=comment_density_per_line,
        total_comments=total_comments,
    )


def create_pr_features(pr: PullRequest) -> PRFeatures:
    """Create a PRFeatures model from a PullRequest.

    Args:
        pr: PullRequest with valid id

    Returns:
        PRFeatures model ready to save

    Raises:
        ValueError: If pr.id is None
    """
    if pr.id is None:
        msg = "PullRequest must have an id to create features"
        raise ValueError(msg)

    features = compute_features(pr)

    return PRFeatures(pull_request_id=pr.id, **features)
