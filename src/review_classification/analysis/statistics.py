"""Statistical analysis functions for outlier detection."""

import math
from collections.abc import Sequence
from dataclasses import dataclass


@dataclass
class RepositoryStats:
    """Statistics for a single metric across a repository."""

    mean: float
    std_dev: float
    count: int


class InsufficientDataError(Exception):
    """Raised when there's insufficient data for statistical analysis."""

    pass


def compute_mean_std(values: Sequence[float]) -> tuple[float, float]:
    """Compute mean and standard deviation.

    Args:
        values: Sequence of numeric values

    Returns:
        Tuple of (mean, std_dev)

    Raises:
        InsufficientDataError: If values has fewer than 2 elements
    """
    if len(values) < 2:
        msg = f"Need at least 2 values for statistics, got {len(values)}"
        raise InsufficientDataError(msg)

    n = len(values)
    mean = sum(values) / n

    # Sample standard deviation (n-1 denominator)
    variance = sum((x - mean) ** 2 for x in values) / (n - 1)
    std_dev = math.sqrt(variance)

    return mean, std_dev


def compute_z_score(value: float, mean: float, std_dev: float) -> float:
    """Compute z-score for a value.

    Args:
        value: The value to compute z-score for
        mean: Population mean
        std_dev: Population standard deviation

    Returns:
        Z-score

    Note:
        Returns 0.0 if std_dev is 0 (all values identical)
    """
    if std_dev == 0:
        return 0.0
    return (value - mean) / std_dev


def is_outlier(z_score: float, threshold: float = 2.0) -> bool:
    """Determine if a z-score indicates an outlier.

    Args:
        z_score: The z-score to check
        threshold: Absolute z-score threshold (default 2.0 for 95% CI)

    Returns:
        True if |z_score| > threshold
    """
    return abs(z_score) > threshold


def compute_repository_stats(
    values: Sequence[float | None],
    min_sample_size: int = 30,
) -> RepositoryStats:
    """Compute statistics for a repository metric.

    Args:
        values: Sequence of values (None values are filtered out)
        min_sample_size: Minimum number of samples required

    Returns:
        RepositoryStats with mean, std_dev, and count

    Raises:
        InsufficientDataError: If fewer than min_sample_size non-None values
    """
    # Filter out None values
    valid_values = [v for v in values if v is not None]

    if len(valid_values) < min_sample_size:
        msg = (
            f"Need at least {min_sample_size} samples for reliable statistics, "
            f"got {len(valid_values)}"
        )
        raise InsufficientDataError(msg)

    mean, std_dev = compute_mean_std(valid_values)

    return RepositoryStats(
        mean=mean,
        std_dev=std_dev,
        count=len(valid_values),
    )
