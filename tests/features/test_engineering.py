"""Tests for feature engineering."""

from datetime import UTC, datetime

import pytest

from review_classification.features.engineering import (
    compute_features,
    create_pr_features,
)
from review_classification.sqlite.models import PullRequest


def test_compute_features_complete_pr() -> None:
    """Test feature computation for a complete merged PR."""
    pr = PullRequest(
        id=1,
        repository_name="test/repo",
        number=1,
        title="Test PR",
        author="user",
        created_at=datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC),
        merged_at=datetime(2024, 1, 2, 12, 0, 0, tzinfo=UTC),
        additions=100,
        deletions=50,
        changed_files=5,
        comments=10,
        review_comments=5,
        state="closed",
        url="http://test.com",
    )

    features = compute_features(pr)

    assert features["code_churn"] == 150
    assert features["total_comments"] == 15
    assert features["review_duration_hours"] == pytest.approx(24.0)
    assert features["comment_density_per_file"] == pytest.approx(3.0)
    assert features["comment_density_per_line"] == pytest.approx(0.1)


def test_compute_features_unmerged_pr() -> None:
    """Test feature computation for an unmerged PR."""
    pr = PullRequest(
        id=1,
        repository_name="test/repo",
        number=1,
        title="Test PR",
        author="user",
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        merged_at=None,
        additions=100,
        deletions=50,
        changed_files=5,
        comments=0,
        review_comments=0,
        state="open",
        url="http://test.com",
    )

    features = compute_features(pr)

    assert features["review_duration_hours"] is None
    assert features["code_churn"] == 150


def test_compute_features_zero_files() -> None:
    """Test feature computation when there are no changed files."""
    pr = PullRequest(
        id=1,
        repository_name="test/repo",
        number=1,
        title="Test PR",
        author="user",
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        merged_at=datetime(2024, 1, 2, tzinfo=UTC),
        additions=0,
        deletions=0,
        changed_files=0,
        comments=5,
        review_comments=0,
        state="closed",
        url="http://test.com",
    )

    features = compute_features(pr)

    assert features["comment_density_per_file"] is None
    assert features["comment_density_per_line"] is None
    assert features["code_churn"] == 0


def test_compute_features_zero_churn() -> None:
    """Test feature computation when there is no code churn but files changed."""
    pr = PullRequest(
        id=1,
        repository_name="test/repo",
        number=1,
        title="Test PR",
        author="user",
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        merged_at=datetime(2024, 1, 2, tzinfo=UTC),
        additions=0,
        deletions=0,
        changed_files=3,
        comments=6,
        review_comments=0,
        state="closed",
        url="http://test.com",
    )

    features = compute_features(pr)

    assert features["comment_density_per_file"] == pytest.approx(2.0)
    assert features["comment_density_per_line"] is None
    assert features["code_churn"] == 0


def test_create_pr_features_success() -> None:
    """Test creating PRFeatures model from PullRequest."""
    pr = PullRequest(
        id=42,
        repository_name="test/repo",
        number=1,
        title="Test PR",
        author="user",
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        merged_at=datetime(2024, 1, 2, tzinfo=UTC),
        additions=100,
        deletions=50,
        changed_files=5,
        comments=10,
        review_comments=5,
        state="closed",
        url="http://test.com",
    )

    pr_features = create_pr_features(pr)

    assert pr_features.pull_request_id == 42
    assert pr_features.code_churn == 150
    assert pr_features.total_comments == 15


def test_create_pr_features_no_id() -> None:
    """Test that creating PRFeatures without PR id raises ValueError."""
    pr = PullRequest(
        id=None,
        repository_name="test/repo",
        number=1,
        title="Test PR",
        author="user",
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        merged_at=datetime(2024, 1, 2, tzinfo=UTC),
        additions=100,
        deletions=50,
        changed_files=5,
        comments=10,
        review_comments=5,
        state="closed",
        url="http://test.com",
    )

    with pytest.raises(ValueError, match="PullRequest must have an id"):
        create_pr_features(pr)


def test_compute_features_short_review_time() -> None:
    """Test feature computation for a PR with very short review time."""
    pr = PullRequest(
        id=1,
        repository_name="test/repo",
        number=1,
        title="Test PR",
        author="user",
        created_at=datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC),
        merged_at=datetime(2024, 1, 1, 12, 30, 0, tzinfo=UTC),
        additions=1000,
        deletions=500,
        changed_files=50,
        comments=0,
        review_comments=0,
        state="closed",
        url="http://test.com",
    )

    features = compute_features(pr)

    # 30 minutes = 0.5 hours
    assert features["review_duration_hours"] == pytest.approx(0.5)
    # Large PR with no comments
    assert features["comment_density_per_file"] == pytest.approx(0.0)
    assert features["comment_density_per_line"] == pytest.approx(0.0)
