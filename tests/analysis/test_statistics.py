"""Tests for statistical analysis functions."""

import pytest

from review_classification.analysis.statistics import (
    InsufficientDataError,
    RepositoryStats,
    compute_mean_std,
    compute_repository_stats,
    compute_z_score,
    is_outlier,
)


def test_compute_mean_std_normal_case() -> None:
    """Test mean and standard deviation calculation with normal data."""
    values = [1.0, 2.0, 3.0, 4.0, 5.0]
    mean, std = compute_mean_std(values)

    assert mean == pytest.approx(3.0)
    assert std == pytest.approx(1.58, abs=0.01)


def test_compute_mean_std_two_values() -> None:
    """Test with minimum valid number of values."""
    values = [10.0, 20.0]
    mean, std = compute_mean_std(values)

    assert mean == pytest.approx(15.0)
    # Sample std with n-1 denominator
    assert std == pytest.approx(7.07, abs=0.01)


def test_compute_mean_std_insufficient_data() -> None:
    """Test that single value raises InsufficientDataError."""
    with pytest.raises(InsufficientDataError, match="at least 2 values"):
        compute_mean_std([1.0])


def test_compute_mean_std_empty() -> None:
    """Test that empty list raises InsufficientDataError."""
    with pytest.raises(InsufficientDataError, match="at least 2 values"):
        compute_mean_std([])


def test_compute_mean_std_identical_values() -> None:
    """Test with all identical values (zero variance)."""
    values = [5.0, 5.0, 5.0, 5.0]
    mean, std = compute_mean_std(values)

    assert mean == pytest.approx(5.0)
    assert std == pytest.approx(0.0)


def test_compute_z_score_positive() -> None:
    """Test z-score calculation for value above mean."""
    z = compute_z_score(5.0, mean=3.0, std_dev=2.0)
    assert z == pytest.approx(1.0)


def test_compute_z_score_negative() -> None:
    """Test z-score calculation for value below mean."""
    z = compute_z_score(1.0, mean=3.0, std_dev=2.0)
    assert z == pytest.approx(-1.0)


def test_compute_z_score_at_mean() -> None:
    """Test z-score calculation for value at mean."""
    z = compute_z_score(3.0, mean=3.0, std_dev=2.0)
    assert z == pytest.approx(0.0)


def test_compute_z_score_zero_std_dev() -> None:
    """Test that zero standard deviation returns z-score of 0."""
    z = compute_z_score(5.0, mean=5.0, std_dev=0.0)
    assert z == 0.0


def test_compute_z_score_large_value() -> None:
    """Test z-score with extreme outlier value."""
    z = compute_z_score(100.0, mean=10.0, std_dev=5.0)
    assert z == pytest.approx(18.0)


def test_is_outlier_true_positive() -> None:
    """Test outlier detection for positive z-score above threshold."""
    assert is_outlier(2.5, threshold=2.0) is True


def test_is_outlier_true_negative() -> None:
    """Test outlier detection for negative z-score below threshold."""
    assert is_outlier(-2.5, threshold=2.0) is True


def test_is_outlier_false() -> None:
    """Test outlier detection for z-score within threshold."""
    assert is_outlier(1.5, threshold=2.0) is False


def test_is_outlier_at_threshold() -> None:
    """Test outlier detection at exact threshold value."""
    assert is_outlier(2.0, threshold=2.0) is False
    assert is_outlier(2.0001, threshold=2.0) is True


def test_is_outlier_custom_threshold() -> None:
    """Test outlier detection with custom threshold."""
    assert is_outlier(2.5, threshold=3.0) is False
    assert is_outlier(3.5, threshold=3.0) is True


def test_compute_repository_stats_normal_case() -> None:
    """Test repository statistics computation with sufficient data."""
    values = [float(i) for i in range(30, 60)]  # 30 values
    stats = compute_repository_stats(values, min_sample_size=30)

    assert stats.count == 30
    assert stats.mean == pytest.approx(44.5)
    assert stats.std_dev > 0


def test_compute_repository_stats_with_none_values() -> None:
    """Test that None values are filtered out correctly."""
    values: list[float | None] = [1.0, 2.0, None, 3.0, None, 4.0, 5.0]
    values.extend([float(i) for i in range(6, 31)])  # Total 30 non-None values

    stats = compute_repository_stats(values, min_sample_size=30)

    assert stats.count == 30


def test_compute_repository_stats_insufficient_data() -> None:
    """Test that insufficient data raises error."""
    values = [float(i) for i in range(20)]  # Only 20 values

    with pytest.raises(InsufficientDataError, match="at least 30 samples"):
        compute_repository_stats(values, min_sample_size=30)


def test_compute_repository_stats_insufficient_after_filtering() -> None:
    """Test that insufficient non-None values raises error."""
    values: list[float | None] = [1.0, 2.0, 3.0]
    values.extend([None] * 50)  # Only 3 non-None values

    with pytest.raises(InsufficientDataError, match="at least 30 samples"):
        compute_repository_stats(values, min_sample_size=30)


def test_compute_repository_stats_custom_min_size() -> None:
    """Test repository statistics with custom minimum sample size."""
    values = [float(i) for i in range(10)]
    stats = compute_repository_stats(values, min_sample_size=5)

    assert stats.count == 10
    assert stats.mean == pytest.approx(4.5)


def test_repository_stats_dataclass() -> None:
    """Test RepositoryStats dataclass creation and attributes."""
    stats = RepositoryStats(mean=10.5, std_dev=2.3, count=50)

    assert stats.mean == 10.5
    assert stats.std_dev == 2.3
    assert stats.count == 50


def test_insufficient_data_error_message() -> None:
    """Test that InsufficientDataError has correct message."""
    try:
        raise InsufficientDataError("Test error message")
    except InsufficientDataError as e:
        assert str(e) == "Test error message"
