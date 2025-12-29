"""Tests for main module."""

from review_classification.main import main


def test_main_import() -> None:
    """Test that main function is callable."""
    assert callable(main)
