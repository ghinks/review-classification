"""Integration tests for outlier detection."""

from datetime import UTC, datetime

import pytest
from sqlmodel import Session, create_engine

from review_classification.analysis.outlier_detector import (
    detect_outliers_for_repository,
    save_outlier_scores,
)
from review_classification.analysis.statistics import InsufficientDataError
from review_classification.features.engineering import create_pr_features
from review_classification.sqlite.models import PROutlierScore, PullRequest


@pytest.fixture
def test_engine():
    """Create a test database engine using an in-memory SQLite database."""
    from sqlmodel import SQLModel

    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    return engine


@pytest.fixture
def test_session(test_engine):
    """Create a test database session."""
    with Session(test_engine) as session:
        yield session


def test_outlier_detection_with_extreme_pr(test_session: Session) -> None:
    """Test outlier detection identifies an extreme PR correctly."""
    repo_name = "test/outlier-repo"

    # Create 50 normal PRs
    for i in range(50):
        pr = PullRequest(
            repository_name=repo_name,
            number=i,
            title=f"PR {i}",
            author="user",
            created_at=datetime(2024, 1, 1, 12, i % 24, tzinfo=UTC),
            merged_at=datetime(2024, 1, 1, 14, i % 24, tzinfo=UTC),
            additions=100,
            deletions=50,
            changed_files=5,
            comments=2,
            review_comments=3,
            state="closed",
            url=f"http://test.com/{i}",
        )
        test_session.add(pr)

    # Create 1 extreme outlier PR
    outlier_pr = PullRequest(
        repository_name=repo_name,
        number=999,
        title="Outlier PR",
        author="user",
        created_at=datetime(2024, 1, 1, 12, 0, tzinfo=UTC),
        merged_at=datetime(2024, 1, 1, 13, 0, tzinfo=UTC),
        additions=10000,  # Extreme value
        deletions=5000,  # Extreme value
        changed_files=500,  # Extreme value
        comments=100,
        review_comments=50,
        state="closed",
        url="http://test.com/999",
    )
    test_session.add(outlier_pr)
    test_session.commit()

    # Compute features for all PRs
    from sqlmodel import select

    all_prs = list(test_session.exec(select(PullRequest)).all())
    for pr in all_prs:
        if pr.id is not None:
            features = create_pr_features(pr)
            test_session.add(features)
    test_session.commit()

    # Detect outliers
    results = detect_outliers_for_repository(
        test_session, repo_name, min_sample_size=30
    )

    # Verify outlier detected
    outliers = [r for r in results if r.is_outlier]
    assert len(outliers) > 0

    # Verify extreme PR is detected
    extreme_result = next((r for r in results if r.pr_number == 999), None)
    assert extreme_result is not None
    assert extreme_result.is_outlier is True
    assert "additions" in extreme_result.outlier_features


def test_outlier_detection_saves_to_database(test_session: Session) -> None:
    """Test that outlier scores are saved correctly to database."""
    repo_name = "test/save-repo"

    # Create 30 PRs
    for i in range(30):
        pr = PullRequest(
            repository_name=repo_name,
            number=i,
            title=f"PR {i}",
            author="user",
            created_at=datetime(2024, 1, 1, tzinfo=UTC),
            merged_at=datetime(2024, 1, 2, tzinfo=UTC),
            additions=100,
            deletions=50,
            changed_files=5,
            comments=2,
            review_comments=3,
            state="closed",
            url=f"http://test.com/{i}",
        )
        test_session.add(pr)
    test_session.commit()

    # Compute features
    from sqlmodel import select

    all_prs = list(test_session.exec(select(PullRequest)).all())
    for pr in all_prs:
        if pr.id is not None:
            features = create_pr_features(pr)
            test_session.add(features)
    test_session.commit()

    # Detect and save outliers
    results = detect_outliers_for_repository(test_session, repo_name)
    save_outlier_scores(test_session, repo_name, results, sample_size=30)

    # Verify saved to database
    saved_scores = list(test_session.exec(select(PROutlierScore)).all())
    assert len(saved_scores) == 30


def test_insufficient_data_error_raised(test_session: Session) -> None:
    """Test that InsufficientDataError is raised with too few PRs."""
    repo_name = "test/small-repo"

    # Create only 5 PRs (less than min_sample_size)
    for i in range(5):
        pr = PullRequest(
            repository_name=repo_name,
            number=i,
            title=f"PR {i}",
            author="user",
            created_at=datetime(2024, 1, 1, tzinfo=UTC),
            merged_at=datetime(2024, 1, 2, tzinfo=UTC),
            additions=100,
            deletions=50,
            changed_files=5,
            comments=2,
            review_comments=3,
            state="closed",
            url=f"http://test.com/{i}",
        )
        test_session.add(pr)
    test_session.commit()

    # Should raise InsufficientDataError
    with pytest.raises(InsufficientDataError, match="at least 30"):
        detect_outliers_for_repository(test_session, repo_name, min_sample_size=30)


def test_normal_distribution_few_outliers(test_session: Session) -> None:
    """Test that normal distribution produces expected outlier rate."""
    repo_name = "test/normal-repo"

    # Create 100 PRs with similar values (normal distribution)
    import random

    random.seed(42)  # For reproducibility

    for i in range(100):
        pr = PullRequest(
            repository_name=repo_name,
            number=i,
            title=f"PR {i}",
            author="user",
            created_at=datetime(2024, 1, 1, 12, 0, tzinfo=UTC),
            merged_at=datetime(2024, 1, 1, 14, 0, tzinfo=UTC),
            additions=random.randint(80, 120),
            deletions=random.randint(40, 60),
            changed_files=random.randint(4, 6),
            comments=random.randint(1, 3),
            review_comments=random.randint(2, 4),
            state="closed",
            url=f"http://test.com/{i}",
        )
        test_session.add(pr)
    test_session.commit()

    # Compute features
    from sqlmodel import select

    all_prs = list(test_session.exec(select(PullRequest)).all())
    for pr in all_prs:
        if pr.id is not None:
            features = create_pr_features(pr)
            test_session.add(features)
    test_session.commit()

    # Detect outliers
    results = detect_outliers_for_repository(test_session, repo_name)

    # With normal distribution and threshold=2, expect ~5% outliers
    outliers = [r for r in results if r.is_outlier]
    outlier_rate = len(outliers) / len(results)

    # Should be close to 5% but allow some variance due to randomness
    assert 0.0 <= outlier_rate <= 0.15  # Between 0% and 15%
