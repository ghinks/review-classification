"""Outlier detection using z-scores."""

import json
from dataclasses import dataclass
from datetime import datetime

from sqlmodel import Session, select

from ..sqlite.models import PRFeatures, PROutlierScore, PullRequest
from .statistics import (
    InsufficientDataError,
    compute_repository_stats,
    compute_z_score,
    is_outlier,
)


@dataclass
class OutlierResult:
    """Result of outlier detection for a single PR."""

    pr_id: int
    pr_number: int
    title: str
    author: str
    merged_at: datetime | None
    is_outlier: bool
    outlier_features: list[str]
    max_abs_z_score: float
    z_scores: dict[str, float | None]


def calculate_repository_statistics(
    session: Session,
    repository_name: str,
    min_sample_size: int = 30,
) -> tuple[dict[str, dict[str, float]], int]:
    """Calculate statistics for all metrics in a repository.

    Args:
        session: Database session
        repository_name: Repository to analyze
        min_sample_size: Minimum PRs needed for analysis

    Returns:
        Tuple of (metric_stats, sample_count) where metric_stats is a dict
        mapping metric names to {'mean': float, 'std_dev': float}

    Raises:
        InsufficientDataError: If repository has insufficient merged PRs
    """
    # Fetch all merged PRs for this repository
    statement = select(PullRequest).where(
        PullRequest.repository_name == repository_name,
        PullRequest.merged_at.is_not(None),  # type: ignore[union-attr]
    )
    prs = list(session.exec(statement).all())

    if len(prs) < min_sample_size:
        msg = (
            f"Repository {repository_name} has only {len(prs)} merged PRs, "
            f"need at least {min_sample_size}"
        )
        raise InsufficientDataError(msg)

    # Fetch all features for these PRs
    pr_ids = [pr.id for pr in prs if pr.id is not None]
    feature_statement = select(PRFeatures).where(
        PRFeatures.pull_request_id.in_(pr_ids)  # type: ignore[attr-defined]
    )
    features_list = list(session.exec(feature_statement).all())
    features_map = {f.pull_request_id: f for f in features_list}

    # Collect values for each metric
    raw_metrics: dict[str, list[float | None]] = {
        "additions": [float(pr.additions) for pr in prs],
        "deletions": [float(pr.deletions) for pr in prs],
        "changed_files": [float(pr.changed_files) for pr in prs],
        "comments": [float(pr.comments) for pr in prs],
        "review_comments": [float(pr.review_comments) for pr in prs],
    }

    feature_metrics: dict[str, list[float | None]] = {
        "review_duration_hours": [
            features_map[pr.id].review_duration_hours
            for pr in prs
            if pr.id in features_map
        ],
        "code_churn": [
            float(features_map[pr.id].code_churn) for pr in prs if pr.id in features_map
        ],
        "comment_density_per_file": [
            features_map[pr.id].comment_density_per_file
            for pr in prs
            if pr.id in features_map
        ],
        "comment_density_per_line": [
            features_map[pr.id].comment_density_per_line
            for pr in prs
            if pr.id in features_map
        ],
    }

    # Compute statistics for each metric
    stats: dict[str, dict[str, float]] = {}

    all_metrics: dict[str, list[float | None]] = {**raw_metrics, **feature_metrics}
    for metric_name, values in all_metrics.items():
        try:
            repo_stats = compute_repository_stats(
                values, min_sample_size=min_sample_size
            )
            stats[metric_name] = {
                "mean": repo_stats.mean,
                "std_dev": repo_stats.std_dev,
            }
        except InsufficientDataError:
            # Some features may have many None values
            stats[metric_name] = {"mean": 0.0, "std_dev": 0.0}

    return stats, len(prs)


def detect_outliers_for_pr(
    pr: PullRequest,
    features: PRFeatures,
    stats: dict[str, dict[str, float]],
    threshold: float = 2.0,
) -> OutlierResult:
    """Detect if a PR is an outlier based on z-scores.

    Args:
        pr: PullRequest to analyze
        features: Computed features for the PR
        stats: Repository statistics
        threshold: Z-score threshold for outlier detection

    Returns:
        OutlierResult with z-scores and outlier status
    """
    z_scores: dict[str, float | None] = {}
    outlier_features: list[str] = []

    # Compute z-scores for raw metrics
    raw_metric_map = {
        "additions": float(pr.additions),
        "deletions": float(pr.deletions),
        "changed_files": float(pr.changed_files),
        "comments": float(pr.comments),
        "review_comments": float(pr.review_comments),
    }

    for metric_name, value in raw_metric_map.items():
        if metric_name in stats:
            z = compute_z_score(
                value,
                stats[metric_name]["mean"],
                stats[metric_name]["std_dev"],
            )
            z_scores[f"z_{metric_name}"] = z
            if is_outlier(z, threshold):
                outlier_features.append(metric_name)

    # Compute z-scores for engineered features
    feature_map: dict[str, float | None] = {
        "review_duration_hours": features.review_duration_hours,
        "code_churn": float(features.code_churn),
        "comment_density_per_file": features.comment_density_per_file,
        "comment_density_per_line": features.comment_density_per_line,
    }

    for metric_name, value in feature_map.items():  # type: ignore[assignment]
        if value is not None and metric_name in stats:
            z = compute_z_score(
                value,
                stats[metric_name]["mean"],
                stats[metric_name]["std_dev"],
            )
            z_scores[f"z_{metric_name}"] = z
            if is_outlier(z, threshold):
                outlier_features.append(metric_name)
        else:
            z_scores[f"z_{metric_name}"] = None

    # Determine overall outlier status
    valid_z_scores = [abs(z) for z in z_scores.values() if z is not None]
    max_abs_z = max(valid_z_scores) if valid_z_scores else 0.0
    is_outlier_pr = len(outlier_features) > 0

    return OutlierResult(
        pr_id=pr.id if pr.id is not None else 0,
        pr_number=pr.number,
        title=pr.title,
        author=pr.author,
        merged_at=pr.merged_at,
        is_outlier=is_outlier_pr,
        outlier_features=outlier_features,
        max_abs_z_score=max_abs_z,
        z_scores=z_scores,
    )


def detect_outliers_for_repository(
    session: Session,
    repository_name: str,
    min_sample_size: int = 30,
    threshold: float = 2.0,
) -> list[OutlierResult]:
    """Detect outliers for all PRs in a repository.

    Args:
        session: Database session
        repository_name: Repository to analyze
        min_sample_size: Minimum PRs needed for analysis
        threshold: Z-score threshold for outlier detection

    Returns:
        List of OutlierResult for each PR

    Raises:
        InsufficientDataError: If repository has insufficient data
    """
    # Calculate repository statistics
    stats, _ = calculate_repository_statistics(
        session, repository_name, min_sample_size
    )

    # Fetch all PRs and features
    statement = select(PullRequest).where(
        PullRequest.repository_name == repository_name,
        PullRequest.merged_at.is_not(None),  # type: ignore[union-attr]
    )
    prs = list(session.exec(statement).all())

    pr_ids = [pr.id for pr in prs if pr.id is not None]
    feature_statement = select(PRFeatures).where(
        PRFeatures.pull_request_id.in_(pr_ids)  # type: ignore[attr-defined]
    )
    features_map = {f.pull_request_id: f for f in session.exec(feature_statement).all()}

    # Detect outliers for each PR
    results: list[OutlierResult] = []
    for pr in prs:
        if pr.id in features_map:
            result = detect_outliers_for_pr(pr, features_map[pr.id], stats, threshold)
            results.append(result)

    return results


def save_outlier_scores(
    session: Session,
    repository_name: str,
    results: list[OutlierResult],
    sample_size: int,
) -> None:
    """Save outlier detection results to database.

    Args:
        session: Database session
        repository_name: Repository name
        results: List of OutlierResult from detection
        sample_size: Number of PRs used for statistics
    """
    for result in results:
        # Check if outlier score already exists
        existing_statement = select(PROutlierScore).where(
            PROutlierScore.pull_request_id == result.pr_id
        )
        existing = session.exec(existing_statement).first()

        outlier_score = PROutlierScore(
            pull_request_id=result.pr_id,
            repository_name=repository_name,
            z_additions=result.z_scores.get("z_additions"),
            z_deletions=result.z_scores.get("z_deletions"),
            z_changed_files=result.z_scores.get("z_changed_files"),
            z_comments=result.z_scores.get("z_comments"),
            z_review_comments=result.z_scores.get("z_review_comments"),
            z_review_duration=result.z_scores.get("z_review_duration_hours"),
            z_code_churn=result.z_scores.get("z_code_churn"),
            z_comment_density_per_file=result.z_scores.get(
                "z_comment_density_per_file"
            ),
            z_comment_density_per_line=result.z_scores.get(
                "z_comment_density_per_line"
            ),
            is_outlier=result.is_outlier,
            outlier_features=(
                json.dumps(result.outlier_features) if result.outlier_features else None
            ),
            max_abs_z_score=result.max_abs_z_score,
            sample_size=sample_size,
        )

        if existing:
            # Update existing record
            outlier_score.id = existing.id
            for key, value in outlier_score.model_dump(exclude={"id"}).items():
                setattr(existing, key, value)
            session.add(existing)
        else:
            # Create new record
            session.add(outlier_score)

    session.commit()
