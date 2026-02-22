"""Integration tests for outlier detection."""

from collections.abc import Generator
from datetime import UTC, datetime

import pytest
from sqlalchemy.engine import Engine
from sqlmodel import Session, create_engine

from review_classification.analysis.outlier_detector import (
    detect_outliers_for_repository,
    save_outlier_scores,
)
from review_classification.analysis.statistics import InsufficientDataError
from review_classification.features.engineering import create_pr_features
from review_classification.sqlite.models import PROutlierScore, PullRequest


@pytest.fixture
def test_engine() -> Engine:
    """Create a test database engine using an in-memory SQLite database."""
    from sqlmodel import SQLModel

    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    return engine


@pytest.fixture
def test_session(test_engine: Engine) -> Generator[Session, None, None]:
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


def test_outlier_detection_with_classify_date_range(test_session: Session) -> None:
    """Test that classify window is used as baseline and PRs after it are evaluated."""
    repo_name = "test/classify-range-repo"

    # Create 50 baseline PRs in Jan 2024 — these form the measurement window
    for i in range(50):
        pr = PullRequest(
            repository_name=repo_name,
            number=i,
            title=f"Baseline PR {i}",
            author="user",
            created_at=datetime(2024, 1, i % 28 + 1, 10, 0, tzinfo=UTC),
            merged_at=datetime(2024, 1, i % 28 + 1, 12, 0, tzinfo=UTC),
            additions=90 + (i % 20),  # Varies 90-109, mean ~99, std_dev ~5.8
            deletions=45 + (i % 10),
            changed_files=4 + (i % 3),
            comments=1 + (i % 3),
            review_comments=2 + (i % 3),
            state="closed",
            url=f"http://test.com/baseline/{i}",
        )
        test_session.add(pr)

    # Create 4 normal PRs in Feb 2024 — these are after classify_end, so evaluated
    for i in range(4):
        pr = PullRequest(
            repository_name=repo_name,
            number=100 + i,
            title=f"Feb PR {i}",
            author="user",
            created_at=datetime(2024, 2, i + 1, 10, 0, tzinfo=UTC),
            merged_at=datetime(2024, 2, i + 1, 12, 0, tzinfo=UTC),
            additions=95 + i,
            deletions=48,
            changed_files=5,
            comments=2,
            review_comments=3,
            state="closed",
            url=f"http://test.com/feb/{i}",
        )
        test_session.add(pr)

    # Create 1 extreme PR in Feb 2024 — after classify_end, should be flagged
    outlier_pr = PullRequest(
        repository_name=repo_name,
        number=999,
        title="Extreme Feb PR",
        author="user",
        created_at=datetime(2024, 2, 10, 10, 0, tzinfo=UTC),
        merged_at=datetime(2024, 2, 10, 12, 0, tzinfo=UTC),
        additions=10000,
        deletions=5000,
        changed_files=500,
        comments=100,
        review_comments=50,
        state="closed",
        url="http://test.com/feb/extreme",
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

    # classify window = Jan 2024 (used for stats); PRs after Jan 31 are evaluated
    classify_start = datetime(2024, 1, 1, tzinfo=UTC)
    classify_end = datetime(2024, 1, 31, 23, 59, 59, tzinfo=UTC)

    results = detect_outliers_for_repository(
        test_session,
        repo_name,
        min_sample_size=30,
        classify_start=classify_start,
        classify_end=classify_end,
    )

    # Only Feb PRs (after classify_end) should be in results
    assert len(results) == 5
    assert all(r.pr_number >= 100 for r in results)

    # Baseline Jan PRs should not be present
    assert not any(r.pr_number < 100 for r in results)

    # Extreme Feb PR should be flagged as outlier against the Jan baseline
    extreme = next((r for r in results if r.pr_number == 999), None)
    assert extreme is not None
    assert extreme.is_outlier is True
    assert "additions" in extreme.outlier_features


def test_classify_window_is_baseline_for_stats(test_session: Session) -> None:
    """Test that the classification window defines the baseline used for statistics.

    50 PRs in Jan 2023 form the classify window (baseline: mean≈98.5, std_dev≈5.74).
    30 PRs in Jan 2024 (additions=115) come after classify_end and are evaluated.

    With the window: z ≈ (115-98.5)/5.74 ≈ 2.87 → outlier.
    Without the window (all 80 PRs for stats): mean≈104.7, std_dev≈9.2,
      z ≈ (115-104.7)/9.2 ≈ 1.12 → not an outlier.

    This verifies that the classify window controls which PRs feed the baseline.
    """
    repo_name = "test/window-stats-repo"

    # 50 PRs in Jan 2023 — the baseline measurement window
    for i in range(50):
        pr = PullRequest(
            repository_name=repo_name,
            number=i,
            title=f"Baseline PR {i}",
            author="user",
            created_at=datetime(2023, 1, i % 28 + 1, i % 24, 0, tzinfo=UTC),
            merged_at=datetime(2023, 1, i % 28 + 1, (i % 24 + 2) % 24, 0, tzinfo=UTC),
            additions=90 + (i % 20),  # mean≈98.5, std_dev≈5.74
            deletions=50,
            changed_files=5,
            comments=2,
            review_comments=3,
            state="closed",
            url=f"http://test.com/base/{i}",
        )
        test_session.add(pr)

    # 30 PRs in Jan 2024 — after classify_end, so these are evaluated for outliers
    # additions=115 is above threshold vs Jan 2023 baseline (z≈2.87) but not vs
    # the combined 80-PR pool (z≈1.12)
    for i in range(30):
        pr = PullRequest(
            repository_name=repo_name,
            number=100 + i,
            title=f"Classify PR {i}",
            author="user",
            created_at=datetime(2024, 1, i % 28 + 1, i % 24, 0, tzinfo=UTC),
            merged_at=datetime(2024, 1, i % 28 + 1, (i % 24 + 2) % 24, 0, tzinfo=UTC),
            additions=115,
            deletions=50,
            changed_files=5,
            comments=2,
            review_comments=3,
            state="closed",
            url=f"http://test.com/classify/{i}",
        )
        test_session.add(pr)

    test_session.commit()

    from sqlmodel import select

    all_prs = list(test_session.exec(select(PullRequest)).all())
    for pr in all_prs:
        if pr.id is not None:
            features = create_pr_features(pr)
            test_session.add(features)
    test_session.commit()

    # classify window = Jan 2023; PRs after Jan 31 2023 are evaluated
    classify_start = datetime(2023, 1, 1, tzinfo=UTC)
    classify_end = datetime(2023, 1, 31, 23, 59, 59, tzinfo=UTC)

    results_with_window = detect_outliers_for_repository(
        test_session,
        repo_name,
        min_sample_size=30,
        classify_start=classify_start,
        classify_end=classify_end,
    )

    # All 30 Jan-2024 PRs should be in results (after classify_end)
    assert len(results_with_window) == 30
    assert all(r.pr_number >= 100 for r in results_with_window)

    # With clean Jan-2023 baseline, additions=115 is a clear outlier (z≈2.87)
    pr_with_window = next(r for r in results_with_window if r.pr_number == 100)
    assert pr_with_window.is_outlier is True

    # Without window: all 80 PRs used for stats — the Jan-2024 PRs dilute the baseline
    results_no_window = detect_outliers_for_repository(
        test_session,
        repo_name,
        min_sample_size=30,
    )
    pr_no_window = next(r for r in results_no_window if r.pr_number == 100)

    # z_additions should be higher with the clean baseline than the diluted one
    z_with = abs(pr_with_window.z_scores.get("z_additions") or 0.0)
    z_without = abs(pr_no_window.z_scores.get("z_additions") or 0.0)
    assert z_with > z_without, (
        f"Clean baseline (z={z_with:.2f}) should give higher z_additions "
        f"than diluted baseline (z={z_without:.2f})"
    )


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
